"""
Sprint 04 -- the QA dealership's expected-outcome assertions.

Runs dev_seed's two-day standing seed against connect(":memory:") --
which the engine layer maps to a throwaway SQLite database or a
disposable per-connection PostgreSQL schema, so this entire module
runs identically under both CI persistence jobs with zero
engine-specific fixtures -- and enforces dev_seed/expected.py
(the machine-readable form of SYNTHETIC_QA_MATRIX.md) scenario by
scenario.

Three test classes, three fresh databases:

  QAStandingSeedTest      the standing dealership after Day 1 + Day 2
  QARerunIdempotencyTest  replaying Day 2 on top of the standing seed
  QAMissingSourceDayTest  family M -- partial-upload sync days

The standing-seed class seeds ONCE in setUpClass and every test method
is read-only against it -- the seed is the expensive fixture and the
assertions are pure queries, the same reason the pipeline's own
regression tests share fixture loads.
"""

import unittest

from lotsync.database.repository import connect
from lotsync.dev_seed import expected
from lotsync.dev_seed.scenarios import VEHICLES
from lotsync.dev_seed.seeder import run_qa_seed, run_single_day
from lotsync.queries.dashboard import (
    inventory_health_percentage, task_counts_by_department,
)
from lotsync.queries.vehicles import get_vehicle_detail, list_vehicles


def _tasks_by_vin(conn, commitment_standing=None):
    where = ""
    params = ()
    if commitment_standing is not None:
        where = "WHERE commitment_standing = ?"
        params = (commitment_standing,)
    rows = conn.execute(
        f"SELECT vin, task_type, commitment_standing FROM task {where}", params
    ).fetchall()
    by_vin = {}
    for vin, task_type, standing in rows:
        by_vin.setdefault(vin, []).append((task_type, standing))
    return by_vin


def _count(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


class QAStandingSeedTest(unittest.TestCase):
    """The standing QA dealership -- SYNTHETIC_QA_MATRIX.md's roster."""

    @classmethod
    def setUpClass(cls):
        cls.conn = connect(":memory:")
        cls.summaries = run_qa_seed(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    # -- roster identity ---------------------------------------------------

    def test_vehicle_roster_is_exactly_the_matrix_roster(self):
        db_vins = {row[0] for row in self.conn.execute("SELECT vin FROM vehicle")}
        matrix_vins = {vin for vin, _stock, _name in VEHICLES.values()}
        self.assertEqual(db_vins, matrix_vins,
                         "standing vehicles must be exactly the 34 matrix vehicles")
        self.assertEqual(len(db_vins), expected.TOTALS["vehicles"])

    def test_standing_totals(self):
        totals = expected.TOTALS
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM vehicle"), totals["vehicles"])
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM task"), totals["tasks_total"])
        self.assertEqual(
            _count(self.conn, "SELECT COUNT(*) FROM task WHERE commitment_standing = 'outstanding'"),
            totals["tasks_outstanding"])
        self.assertEqual(
            _count(self.conn, "SELECT COUNT(*) FROM task WHERE commitment_standing = 'honored'"),
            totals["tasks_honored"])
        self.assertEqual(
            _count(self.conn, "SELECT COUNT(*) FROM task WHERE commitment_standing = 'moot'"),
            totals["tasks_moot"])
        self.assertEqual(
            _count(self.conn, "SELECT COUNT(*) FROM recommendation WHERE status = 'open'"),
            totals["recommendations_open"])
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM pending_identity"),
                         totals["pending_identities"])
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM sync_run"), totals["sync_runs"])
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM event"), totals["events"])

    def test_qa_access_identity_seeded(self):
        # Sprint 05: the QA dealership's organization/dealership rows
        # exist after every seed (idempotently), with the governed
        # parent link -- memberships deliberately absent (they bind to
        # per-environment Supabase Auth user IDs; see the seeder).
        rows = self.conn.execute(
            "SELECT d.dealership_id, d.name, d.organization_id, o.name "
            "FROM dealership d JOIN organization o "
            "ON o.organization_id = d.organization_id").fetchall()
        self.assertEqual(rows, [
            ("qa-motors", "DealerDOH QA Motors", "qa-auto-group",
             "DealerDOH QA Auto Group"),
        ])
        self.assertEqual(
            _count(self.conn, "SELECT COUNT(*) FROM organization"),
            expected.TOTALS["organizations"])
        self.assertEqual(
            _count(self.conn, "SELECT COUNT(*) FROM user_membership"),
            expected.TOTALS["user_memberships"])

    def test_all_sync_runs_complete(self):
        statuses = {row[0] for row in self.conn.execute("SELECT status FROM sync_run")}
        self.assertEqual(statuses, {"complete"})
        per_source = dict(self.conn.execute(
            "SELECT source, COUNT(*) FROM sync_run GROUP BY source"))
        self.assertEqual(per_source, {
            "keyper": 2, "tekion": 2, "mdd": 2, "recovr": 2, "rapidrecon": 2,
        })

    # -- tasks: scenario-level, exhaustive ---------------------------------

    def test_open_tasks_per_scenario_exactly_match_matrix(self):
        open_by_vin = _tasks_by_vin(self.conn, "outstanding")
        for scenario_id, (vin, _stock, _name) in VEHICLES.items():
            expected_types = sorted(expected.OPEN_TASKS.get(scenario_id, []))
            actual_types = sorted(t for t, _s in open_by_vin.get(vin, []))
            self.assertEqual(
                actual_types, expected_types,
                f"{scenario_id}: open tasks diverge from SYNTHETIC_QA_MATRIX.md")

    def test_open_task_totals_by_type(self):
        rows = dict(self.conn.execute(
            "SELECT task_type, COUNT(*) FROM task "
            "WHERE commitment_standing = 'outstanding' GROUP BY task_type"))
        self.assertEqual(rows, expected.OPEN_TASK_TOTALS_BY_TYPE)

    def test_terminal_tasks_honored_and_moot(self):
        for scenario_id, (task_type, standing) in expected.TERMINAL_TASKS.items():
            vin = expected.vin_of(scenario_id)
            rows = self.conn.execute(
                "SELECT commitment_standing, completed_at FROM task "
                "WHERE vin = ? AND task_type = ?", (vin, task_type)).fetchall()
            self.assertEqual(len(rows), 1, f"{scenario_id}: expected exactly one {task_type}")
            self.assertEqual(rows[0][0], standing, f"{scenario_id}: wrong terminal standing")
            self.assertIsNotNone(rows[0][1], f"{scenario_id}: terminal task must set completed_at")

    def test_no_task_ever_references_an_unknown_vehicle(self):
        matrix_vins = {vin for vin, _s, _n in VEHICLES.values()}
        task_vins = {row[0] for row in self.conn.execute("SELECT DISTINCT vin FROM task")}
        self.assertTrue(task_vins <= matrix_vins)

    # -- recommendations ----------------------------------------------------

    def test_key_out_aging_recommendations(self):
        rows = self.conn.execute(
            "SELECT vin, severity, status, rule_source, title FROM recommendation"
        ).fetchall()
        self.assertEqual(len(rows), len(expected.RECOMMENDATION_SCENARIOS))
        expected_vins = {expected.vin_of(s) for s in expected.RECOMMENDATION_SCENARIOS}
        self.assertEqual({r[0] for r in rows}, expected_vins)
        for vin, severity, status, rule_source, title in rows:
            self.assertEqual(severity, "High")
            self.assertEqual(status, "open")
            self.assertEqual(rule_source, "key_out_aging")
            self.assertIn("Likely Sold, Verify to Remove from OMS", title,
                          "recommendation must carry the most-severe bucket label")

    # -- sold visibility (family I) -----------------------------------------

    def test_sold_vehicles_hidden_by_default_but_fully_reachable(self):
        sold_vins = {expected.vin_of(s) for s in expected.SOLD_SCENARIOS}
        default_vins = {v["vin"] for v in list_vehicles(self.conn)}
        all_vins = {v["vin"] for v in list_vehicles(self.conn, include_sold=True)}

        self.assertEqual(len(default_vins), expected.TOTALS["active_vehicles"])
        self.assertEqual(all_vins - default_vins, sold_vins)
        self.assertEqual(len(all_vins), expected.TOTALS["vehicles"])

        # A sold vehicle keeps its full detail/timeline (never deleted).
        detail = get_vehicle_detail(self.conn, expected.vin_of("QA-SOLD-001"))
        self.assertIsNotNone(detail)
        self.assertEqual(detail["tekion_status"], "Sold")
        self.assertGreater(len(detail["timeline"]), 0)
        self.assertEqual(detail["open_task_count"], 0)

    def test_open_task_count_surfaces_in_vehicle_list(self):
        by_vin = {v["vin"]: v for v in list_vehicles(self.conn)}
        multi = by_vin[expected.vin_of("QA-MULTI-001")]
        self.assertEqual(multi["open_task_count"], 2)
        base = by_vin[expected.vin_of("QA-BASE-001")]
        self.assertEqual(base["open_task_count"], 0)

    # -- events: dedup / chronology (families N, O) --------------------------

    def test_event_counts_per_scenario_prove_dedup(self):
        rows = self.conn.execute(
            "SELECT vin, event_type, COUNT(*) FROM event GROUP BY vin, event_type"
        ).fetchall()
        actual = {}
        for vin, event_type, count in rows:
            actual.setdefault(vin, {})[event_type] = count
        for scenario_id, (vin, _stock, _name) in VEHICLES.items():
            self.assertEqual(
                actual.get(vin, {}), expected.EVENTS[scenario_id],
                f"{scenario_id}: standing event counts diverge (dedup regression?)")

    def test_keyper_event_time_only_on_out_events(self):
        # QA-KEY-000's In -> Out transition: the In event must carry no
        # event_time (Keyper's checkout column is unconfirmed for In
        # rows -- see _persist_keyper_observation), the Out event must
        # carry the checkout timestamp, which is the reference date.
        vin = expected.vin_of("QA-KEY-000")
        rows = self.conn.execute(
            "SELECT event_time, summary FROM event "
            "WHERE vin = ? AND event_type = 'keyper_observed' ORDER BY event_id",
            (vin,)).fetchall()
        self.assertEqual(len(rows), 2)
        in_event, out_event = rows[0], rows[1]
        self.assertIsNone(in_event[0], "In events must not claim an event_time")
        self.assertEqual(out_event[0], "2026-07-21T00:00:00")

    def test_source_claimed_event_time_vs_observed_at(self):
        # tekion_sold carries the sold date as event_time; observed_at
        # is the pipeline's own wall clock -- strictly later than any
        # QA calendar date by construction.
        vin = expected.vin_of("QA-SOLD-002")
        (event_time, observed_at) = self.conn.execute(
            "SELECT event_time, observed_at FROM event "
            "WHERE vin = ? AND event_type = 'tekion_sold'", (vin,)).fetchone()
        self.assertEqual(event_time, "2026-07-20T00:00:00")
        self.assertGreater(observed_at, event_time)

    def test_rapidrecon_freshness_updated_by_day2_even_without_new_event(self):
        (day2_rapidrecon_run,) = self.conn.execute(
            "SELECT MAX(sync_run_id) FROM sync_run WHERE source = 'rapidrecon'"
        ).fetchone()
        rows = self.conn.execute(
            "SELECT vin, last_sync_run_id FROM event_freshness "
            "WHERE event_type = 'rapidrecon_observed'").fetchall()
        expected_vins = {expected.vin_of(s)
                         for s in expected.RAPIDRECON_FRESHNESS_SCENARIOS}
        self.assertEqual({r[0] for r in rows}, expected_vins)
        for vin, last_run in rows:
            self.assertEqual(
                str(last_run), str(day2_rapidrecon_run),
                f"{expected.scenario_of(vin)}: Day 2 must reconfirm freshness "
                "even when the unchanged observation writes no Event")

    # -- pending identity (family Q) -----------------------------------------

    def test_pending_identities_and_promotion(self):
        rows = self.conn.execute(
            "SELECT raw_identifier, identifier_type, status, resolved_vin "
            "FROM pending_identity").fetchall()
        actual = {r[0]: (r[1], r[2], r[3]) for r in rows}
        self.assertEqual(set(actual), set(expected.PENDING_IDENTITIES))
        for raw, (id_type, status, resolved_scenario) in expected.PENDING_IDENTITIES.items():
            got_type, got_status, got_vin = actual[raw]
            self.assertEqual(got_type, id_type, f"pending '{raw}': wrong identifier_type")
            self.assertEqual(got_status, status, f"pending '{raw}': wrong status")
            if resolved_scenario is None:
                self.assertIsNone(got_vin)
            else:
                self.assertEqual(got_vin, expected.vin_of(resolved_scenario))

    def test_non_vehicle_key_left_no_trace(self):
        for table, column in (("pending_identity", "raw_identifier"),
                              ("vehicle", "vin")):
            (count,) = self.conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?",
                ("%GOLF%",)).fetchone()
            self.assertEqual(count, 0, "GOLF CART is a facility key, never data")

    # -- per-scenario status probes ------------------------------------------

    def test_mdd_store_filter_divergence_persists_but_generates_nothing(self):
        # QA-MDD-003: other-store MDD row -> observation recorded,
        # zero tasks (the divergence is governed, not accidental).
        vin = expected.vin_of("QA-MDD-003")
        (mdd_status,) = self.conn.execute(
            "SELECT mdd_status FROM vehicle WHERE vin = ?", (vin,)).fetchone()
        self.assertEqual(mdd_status, "not_paired")

    def test_recovr_fragment_resolved_in_persist_path(self):
        vin = expected.vin_of("QA-RECOVR-005")
        (recovr_status,) = self.conn.execute(
            "SELECT recovr_status FROM vehicle WHERE vin = ?", (vin,)).fetchone()
        self.assertEqual(recovr_status, "not_paired")

    def test_conflict_vehicle_cache_resolves_to_sold(self):
        vin = expected.vin_of("QA-CONFLICT-001")
        (tekion_status,) = self.conn.execute(
            "SELECT tekion_status FROM vehicle WHERE vin = ?", (vin,)).fetchone()
        self.assertEqual(tekion_status, "Sold",
                         "sold list is walked last by design -- Sold wins the cache")

    # -- dashboard aggregates -------------------------------------------------

    def test_dashboard_aggregates_over_qa_dealership(self):
        counts = task_counts_by_department(self.conn)
        self.assertEqual(counts, {"Unassigned": expected.TOTALS["tasks_outstanding"]},
                         "auto-generated tasks carry no invented department")
        health = inventory_health_percentage(self.conn)
        self.assertEqual(health["total_vehicles"], expected.TOTALS["vehicles"])
        self.assertEqual(
            health["healthy_vehicles"],
            expected.TOTALS["vehicles"] - expected.TOTALS["vehicles_with_open_tasks"])

    # -- the seed run's own summaries ------------------------------------------

    def test_seed_day_summaries(self):
        day1, day2 = self.summaries
        self.assertEqual(day1["warnings"], [])
        self.assertEqual(day2["warnings"], [])
        # Day 1 creates 17 of the 18 tasks and QA-KEY-030's
        # recommendation; Day 2 adds exactly QA-KEY-003's
        # threshold-crossing task and QA-KEY-025's boundary
        # recommendation.
        self.assertEqual(day1["tasks_generated"], 17)
        self.assertEqual(day2["tasks_generated"], 1)
        self.assertEqual(day1["recommendations_generated"], 1)
        self.assertEqual(day2["recommendations_generated"], 1)
        # 34 vehicles + the RecovR 6-char fragment, which is counted as
        # its own distinct raw identifier at this summary level.
        self.assertEqual(day1["vehicles_processed"], 35)
        self.assertEqual(day2["vehicles_processed"], 35)
        # Day 1: 888555 (ambiguous) + 9755 + #QA-ODD; Day 2: 888555
        # resolves, the two structural exceptions remain.
        self.assertEqual(day1["exceptions_found"], 3)
        self.assertEqual(day2["exceptions_found"], 2)


class QARerunIdempotencyTest(unittest.TestCase):
    """
    Replaying Day 2 over the standing seed must change nothing --
    except QA-CONFLICT-002's documented re-fire (an internally
    contradictory sold export re-asserts both its claims every run;
    persist_tekion_observations' accepted limitation). Asserting the
    +2 keeps the limitation visible instead of letting it drift.
    """

    @classmethod
    def setUpClass(cls):
        cls.conn = connect(":memory:")
        run_qa_seed(cls.conn)
        cls.before = cls._snapshot(cls.conn)
        run_single_day(cls.conn, 2)
        cls.after = cls._snapshot(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    @staticmethod
    def _snapshot(conn):
        return {
            "tasks": conn.execute(
                "SELECT vin, task_type, commitment_standing FROM task "
                "ORDER BY task_id").fetchall(),
            "recommendations": conn.execute(
                "SELECT vin, status FROM recommendation ORDER BY recommendation_id"
            ).fetchall(),
            "pending": conn.execute(
                "SELECT raw_identifier, status FROM pending_identity "
                "ORDER BY raw_identifier").fetchall(),
            "events_total": _count(conn, "SELECT COUNT(*) FROM event"),
            "conflict_sold_events": _count(
                conn, "SELECT COUNT(*) FROM event WHERE vin = ? AND event_type = 'tekion_sold'",
                (expected.vin_of("QA-CONFLICT-002"),)),
            "vehicles": _count(conn, "SELECT COUNT(*) FROM vehicle"),
            "sync_runs": _count(conn, "SELECT COUNT(*) FROM sync_run"),
        }

    def test_tasks_recommendations_pending_vehicles_unchanged(self):
        self.assertEqual(self.after["tasks"], self.before["tasks"])
        self.assertEqual(self.after["recommendations"], self.before["recommendations"])
        self.assertEqual(self.after["pending"], self.before["pending"])
        self.assertEqual(self.after["vehicles"], self.before["vehicles"])

    def test_only_the_documented_refire_adds_events(self):
        self.assertEqual(
            self.after["conflict_sold_events"],
            self.before["conflict_sold_events"] + 2,
            "QA-CONFLICT-002 re-fires its two contradictory claims per replay")
        self.assertEqual(
            self.after["events_total"], self.before["events_total"] + 2,
            "no other scenario may add an event on an unchanged replay")

    def test_replay_added_one_sync_run_per_source(self):
        self.assertEqual(self.after["sync_runs"], self.before["sync_runs"] + 5)


class QAMissingSourceDayTest(unittest.TestCase):
    """
    Family M -- a required source missing from a sync is silence, not
    a zero-claim: no SyncRun row, no catastrophic reinterpretation of
    standing state, and RecovR-related generation refuses to run
    without Keyper evidence (with an explicit warning).
    """

    @classmethod
    def setUpClass(cls):
        cls.conn = connect(":memory:")
        run_qa_seed(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def _task_rows(self):
        return self.conn.execute(
            "SELECT vin, task_type, commitment_standing FROM task ORDER BY task_id"
        ).fetchall()

    def test_sync_without_keyper_warns_and_touches_nothing(self):
        tasks_before = self._task_rows()
        events_before = _count(self.conn, "SELECT COUNT(*) FROM event")
        conflict_vin = expected.vin_of("QA-CONFLICT-002")
        conflict_before = _count(
            self.conn, "SELECT COUNT(*) FROM event WHERE vin = ?", (conflict_vin,))
        runs_before = dict(self.conn.execute(
            "SELECT source, COUNT(*) FROM sync_run GROUP BY source"))

        summary = run_single_day(
            self.conn, 2,
            sources=("tekion", "sold", "mdd", "recovr", "rapidrecon"))

        self.assertEqual(len(summary["warnings"]), 1)
        self.assertIn("Keyper", summary["warnings"][0])
        self.assertEqual(summary["tasks_generated"], 0)

        runs_after = dict(self.conn.execute(
            "SELECT source, COUNT(*) FROM sync_run GROUP BY source"))
        self.assertEqual(runs_after["keyper"], runs_before["keyper"],
                         "a source not uploaded gets NO SyncRun row")
        for source in ("tekion", "mdd", "recovr", "rapidrecon"):
            self.assertEqual(runs_after[source], runs_before[source] + 1)

        self.assertEqual(self._task_rows(), tasks_before,
                         "standing tasks must survive a Keyper-less sync untouched")
        # Unchanged replay adds only QA-CONFLICT-002's documented
        # re-fire -- missing Keyper must not fabricate or drop events.
        events_after = _count(self.conn, "SELECT COUNT(*) FROM event")
        conflict_after = _count(
            self.conn, "SELECT COUNT(*) FROM event WHERE vin = ?", (conflict_vin,))
        self.assertEqual(conflict_after, conflict_before + 2)
        self.assertEqual(events_after, events_before + 2)

    def test_keyper_only_sync_is_a_quiet_no_op_against_standing_state(self):
        tasks_before = self._task_rows()
        events_before = _count(self.conn, "SELECT COUNT(*) FROM event")
        vehicles_before = _count(self.conn, "SELECT COUNT(*) FROM vehicle")
        runs_before = _count(self.conn, "SELECT COUNT(*) FROM sync_run")

        summary = run_single_day(self.conn, 2, sources=("keyper",))

        # Keyper WAS uploaded -- no missing-Keyper warning; with no
        # Tekion evidence this run, nothing matches, so nothing is
        # persisted, generated, or destroyed.
        self.assertEqual(summary["warnings"], [])
        self.assertEqual(summary["tasks_generated"], 0)
        self.assertEqual(self._task_rows(), tasks_before)
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM event"), events_before)
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM vehicle"), vehicles_before)
        self.assertEqual(_count(self.conn, "SELECT COUNT(*) FROM sync_run"), runs_before + 1,
                         "exactly one SyncRun -- the one source actually uploaded")


if __name__ == "__main__":
    unittest.main()
