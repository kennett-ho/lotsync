"""
Phase 2, Slice 7 verification -- queries/dashboard.py. See
IMPLEMENTATION_PLAN.md's Slice 7 and queries/__init__.py's module
docstring for the read-only, no-new-stored-state boundary this
respects.

Runs the full, realistic pipeline (all 5 sources + Slice 5/6 task and
recommendation generation) against the standard synthetic fixtures,
the same way main.py actually orchestrates it, then asserts each query
function's output against hand-computed expected values -- per
IMPLEMENTATION_PLAN.md's Slice 7 success criteria ("Query results
match hand-computed expected values for fixture scenarios").
"""

import os
import time
import unittest

from lotsync.config.settings import load_settings, load_day_out_buckets
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.importers.mdd import load_mdd_not_paired
from lotsync.importers.recovr import load_recovr_full
from lotsync.importers.rapidrecon import load_rapidrecon
from lotsync.sync.reconciler import (
    reconcile_keyper_tekion, persist_tekion_observations, persist_mdd_observations,
    persist_recovr_observations, persist_rapidrecon_observations, generate_install_tasks,
    generate_key_out_aging_recommendations,
)
from lotsync.database.repository import connect, sync_run, cancel_task
from lotsync.queries.dashboard import (
    connected_systems_status, recent_activity_feed,
    task_counts_by_department, inventory_health_percentage,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")


def _run_full_pipeline(conn):
    """Mirrors main.py's real orchestration end to end, including Slice 5/6 generation."""
    settings = load_settings(CONFIG)
    day_out_buckets = load_day_out_buckets(CONFIG)
    keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    mdd_df = load_mdd_not_paired(os.path.join(FIXTURES, "mdd_not_paired.csv"))
    recovr_df = load_recovr_full(os.path.join(FIXTURES, "recovr.csv"))
    rapidrecon_df = load_rapidrecon(os.path.join(FIXTURES, "rapidrecon.csv"))

    with sync_run(conn, "keyper", records_processed=len(keyper_df)) as run_id:
        fully_verified, key_out_aging, _, _, _ = reconcile_keyper_tekion(
            keyper_df, tekion_df, sold_df, settings["sync_date"], day_out_buckets,
            db_conn=conn, sync_run_id=run_id,
        )
    with sync_run(conn, "tekion", records_processed=len(tekion_df) + len(sold_df)) as run_id:
        persist_tekion_observations(tekion_df, sold_df, db_conn=conn, sync_run_id=run_id)
    with sync_run(conn, "mdd", records_processed=len(mdd_df)) as run_id:
        persist_mdd_observations(mdd_df, db_conn=conn, sync_run_id=run_id)
    with sync_run(conn, "recovr", records_processed=len(recovr_df)) as run_id:
        persist_recovr_observations(recovr_df, db_conn=conn, sync_run_id=run_id)
    with sync_run(conn, "rapidrecon", records_processed=len(rapidrecon_df)) as run_id:
        persist_rapidrecon_observations(rapidrecon_df, db_conn=conn, sync_run_id=run_id)

    # Sprint 3.8: fully_verified/key_out_aging now threaded through --
    # main.py's real orchestration always has real Keyper data (see
    # generate_install_tasks' docstring), and this helper's whole point
    # is mirroring main.py end to end.
    generate_install_tasks(tekion_df, sold_df, mdd_df, recovr_df, settings["store_name"], db_conn=conn,
                            fully_verified_df=fully_verified, key_out_aging_df=key_out_aging)
    generate_key_out_aging_recommendations(key_out_aging, day_out_buckets, db_conn=conn)


class ConnectedSystemsStatusTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        _run_full_pipeline(self.conn)

    def test_returns_one_entry_per_source(self):
        status = connected_systems_status(self.conn)
        self.assertEqual(set(status.keys()), {"keyper", "tekion", "mdd", "recovr", "rapidrecon"})

    def test_every_source_reports_complete(self):
        status = connected_systems_status(self.conn)
        for source, info in status.items():
            self.assertEqual(info["status"], "complete", f"{source} did not complete cleanly")

    def test_records_processed_matches_input_row_counts(self):
        # Read directly off the fixture CSVs, not recomputed from the
        # function under test -- same discipline as every other slice's
        # fixture-count assertions.
        status = connected_systems_status(self.conn)
        self.assertEqual(status["mdd"]["records_processed"], 2)
        self.assertEqual(status["recovr"]["records_processed"], 3)
        self.assertEqual(status["rapidrecon"]["records_processed"], 2)

    def test_reflects_the_most_recent_sync_run_not_the_first(self):
        # Run the pipeline a second time and confirm the panel shows
        # the LATEST run's timing, not the original one.
        first_status = connected_systems_status(self.conn)
        first_keyper_started = first_status["keyper"]["started_at"]

        _run_full_pipeline(self.conn)

        second_status = connected_systems_status(self.conn)
        self.assertNotEqual(second_status["keyper"]["started_at"], first_keyper_started)
        self.assertEqual(second_status["keyper"]["status"], "complete")

    def test_unknown_source_absent(self):
        status = connected_systems_status(self.conn)
        self.assertNotIn("some_source_that_never_ran", status)


class RecentActivityFeedTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        _run_full_pipeline(self.conn)

    def test_returns_events_newest_first(self):
        feed = recent_activity_feed(self.conn, limit=1000)
        event_ids = [row["event_id"] for row in feed]
        self.assertEqual(event_ids, sorted(event_ids, reverse=True))

    def test_respects_limit(self):
        feed = recent_activity_feed(self.conn, limit=3)
        self.assertEqual(len(feed), 3)

    def test_each_row_has_a_display_ready_summary(self):
        feed = recent_activity_feed(self.conn, limit=5)
        for row in feed:
            self.assertIsInstance(row["summary"], str)
            self.assertTrue(len(row["summary"]) > 0)

    def test_total_feed_length_matches_total_event_count(self):
        (total,) = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()
        feed = recent_activity_feed(self.conn, limit=total + 100)
        self.assertEqual(len(feed), total)

    def test_embedded_vehicle_summary_includes_display_name(self):
        # Regression test: confirms display_name survives the full, real
        # pipeline (importer -> persist_tekion_observations -> query),
        # not just the isolated unit tested in test_database_slice2.py.
        # 1TESTVIN000000001 / K30001 is tekion_master.csv's first row,
        # "Year Make Model" = "2024 Test Sedan".
        feed = recent_activity_feed(self.conn, vin="1TESTVIN000000001", limit=1000)
        tekion_rows = [row for row in feed if row["event_type"] == "tekion_observed"]
        self.assertTrue(tekion_rows, "fixture must have produced a tekion_observed Event for this VIN")
        self.assertEqual(tekion_rows[0]["vehicle"]["display_name"], "2024 Test Sedan")


class RecentActivityFeedVinFilterTest(unittest.TestCase):
    """
    Phase 3, Sprint 2 addition: the same function, scoped to one
    vehicle, is what VehicleDetailDTO's Timeline reuses (see
    queries/vehicles.py's get_vehicle_detail) instead of a second,
    near-duplicate query.
    """

    def setUp(self):
        self.conn = connect(":memory:")
        _run_full_pipeline(self.conn)

    def test_vin_filter_returns_only_that_vehicles_events(self):
        (some_vin,) = self.conn.execute("SELECT vin FROM vehicle LIMIT 1").fetchone()
        feed = recent_activity_feed(self.conn, limit=1000, vin=some_vin)
        self.assertTrue(len(feed) > 0)
        for row in feed:
            self.assertEqual(row["vin"], some_vin)

    def test_vin_filter_excludes_other_vehicles_events(self):
        (some_vin,) = self.conn.execute("SELECT vin FROM vehicle LIMIT 1").fetchone()
        scoped_feed = recent_activity_feed(self.conn, limit=1000, vin=some_vin)
        global_feed = recent_activity_feed(self.conn, limit=1000)
        self.assertLess(len(scoped_feed), len(global_feed))

    def test_unknown_vin_returns_empty_list_not_an_error(self):
        feed = recent_activity_feed(self.conn, limit=1000, vin="NO-SUCH-VIN")
        self.assertEqual(feed, [])

    def test_omitting_vin_preserves_original_global_behavior(self):
        # Regression guard: the default (vin=None) must remain
        # byte-for-byte the same query every existing caller relies on.
        with_default = recent_activity_feed(self.conn, limit=1000)
        explicit_none = recent_activity_feed(self.conn, limit=1000, vin=None)
        self.assertEqual(with_default, explicit_none)


class TaskCountsByDepartmentTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        _run_full_pipeline(self.conn)

    def test_ungrouped_install_tasks_land_in_unassigned(self):
        # Slice 5's generate_install_tasks deliberately never populates
        # department (see that function's docstring) -- confirms this
        # query surfaces that gap honestly rather than hiding it.
        counts = task_counts_by_department(self.conn)
        self.assertEqual(counts, {"Unassigned": 3})

    def test_defaults_to_outstanding_only(self):
        # Cancel one of the three outstanding tasks -- it must drop out
        # of the default (outstanding-only) count.
        task_id = self.conn.execute(
            "SELECT task_id FROM task ORDER BY task_id LIMIT 1"
        ).fetchone()[0]
        cancel_task(self.conn, task_id, ratified_by="emp1")
        self.conn.commit()

        counts = task_counts_by_department(self.conn)
        self.assertEqual(counts, {"Unassigned": 2})

    def test_explicit_commitment_standing_overrides_default(self):
        task_id = self.conn.execute(
            "SELECT task_id FROM task ORDER BY task_id LIMIT 1"
        ).fetchone()[0]
        cancel_task(self.conn, task_id, ratified_by="emp1")
        self.conn.commit()

        cancelled_counts = task_counts_by_department(self.conn, commitment_standing="cancelled")
        self.assertEqual(cancelled_counts, {"Unassigned": 1})

    def test_a_populated_department_is_grouped_by_its_own_label(self):
        self.conn.execute(
            "INSERT INTO task (vin, task_type, department, created_at) VALUES (?, ?, ?, ?)",
            ("1TESTVIN000000001", "some_other_task", "Lot Ops", "2026-07-26T00:00:00"),
        )
        self.conn.commit()
        counts = task_counts_by_department(self.conn)
        self.assertEqual(counts, {"Unassigned": 3, "Lot Ops": 1})


class InventoryHealthPercentageTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        _run_full_pipeline(self.conn)

    def test_health_percentage_matches_hand_computed_value(self):
        # 17 known vehicles total (fixture-wide union across all 5
        # sources, per test_database_slice2.py's own count); 3 have an
        # outstanding install Task -- 14/17 healthy.
        result = inventory_health_percentage(self.conn)
        self.assertEqual(result["total_vehicles"], 17)
        self.assertEqual(result["healthy_vehicles"], 14)
        self.assertAlmostEqual(result["health_percentage"], round(100 * 14 / 17, 2))

    def test_honoring_a_task_improves_health(self):
        from lotsync.database.repository import honor_task
        task_id = self.conn.execute(
            "SELECT task_id FROM task ORDER BY task_id LIMIT 1"
        ).fetchone()[0]
        honor_task(self.conn, task_id)
        self.conn.commit()

        result = inventory_health_percentage(self.conn)
        self.assertEqual(result["healthy_vehicles"], 15)

    def test_a_vehicle_with_two_outstanding_tasks_only_counts_once_as_unhealthy(self):
        self.conn.execute(
            "INSERT INTO task (vin, task_type, created_at) VALUES (?, ?, ?)",
            ("1TESTVIN000000001", "another_task_type", "2026-07-26T00:00:00"),
        )
        self.conn.commit()
        result = inventory_health_percentage(self.conn)
        # Still 3 unhealthy vehicles (1TESTVIN000000001 already had one
        # outstanding Task) -- COUNT(DISTINCT vin) must not double-count.
        self.assertEqual(result["healthy_vehicles"], 14)

    def test_no_vehicles_returns_none_percentage_not_a_division_error(self):
        empty_conn = connect(":memory:")
        result = inventory_health_percentage(empty_conn)
        self.assertEqual(result["total_vehicles"], 0)
        self.assertIsNone(result["health_percentage"])


class PerformanceAtScaleTest(unittest.TestCase):
    """
    IMPLEMENTATION_PLAN.md Slice 7's named risk: query performance at
    realistic data volumes -- "thousands of vehicles, the scale already
    seen in real exports" (Technical Risks: "34K-row Sold history,
    ~2,000 Keyper records"). Not optimizing prematurely -- just
    confirming none of the four query functions falls over at this
    scale. Bulk-inserted directly via SQL rather than through
    insert_task/insert_event one row at a time -- this is test-data
    volume generation, not something exercising those functions'
    behavior, which is already covered elsewhere.
    """

    VEHICLE_COUNT = 3000
    EVENTS_PER_VEHICLE = 4

    def setUp(self):
        self.conn = connect(":memory:")

        vehicles = [(f"VIN{i:07d}",) for i in range(self.VEHICLE_COUNT)]
        self.conn.executemany("INSERT INTO vehicle (vin) VALUES (?)", vehicles)

        events = []
        for i in range(self.VEHICLE_COUNT):
            vin = f"VIN{i:07d}"
            for j in range(self.EVENTS_PER_VEHICLE):
                events.append((
                    vin, "keyper_observed", "keyper", None, None, None,
                    f"2026-01-{(j % 28) + 1:02d}T00:00:00", f"Event {j} for {vin}", None,
                ))
        self.conn.executemany(
            "INSERT INTO event (vin, event_type, source, sync_run_id, actor_employee_id, "
            "dealership_id, observed_at, summary, detail_fields) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            events,
        )

        # One outstanding Task per 10 vehicles.
        tasks = [
            (f"VIN{i:07d}", "install_recovr_device", "outstanding", "not_started", "2026-01-01T00:00:00")
            for i in range(0, self.VEHICLE_COUNT, 10)
        ]
        self.unhealthy_count = len(tasks)
        self.conn.executemany(
            "INSERT INTO task (vin, task_type, commitment_standing, execution_status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            tasks,
        )

        for source in ("keyper", "tekion", "mdd", "recovr", "rapidrecon"):
            self.conn.execute(
                "INSERT INTO sync_run (source, started_at, completed_at, records_processed, status) "
                "VALUES (?, ?, ?, ?, 'complete')",
                (source, "2026-01-01T00:00:00", "2026-01-01T00:05:00", self.VEHICLE_COUNT),
            )
        self.conn.commit()

    def test_all_four_queries_complete_within_budget(self):
        budget_seconds = 2.0

        for label, fn in [
            ("connected_systems_status", lambda: connected_systems_status(self.conn)),
            ("recent_activity_feed", lambda: recent_activity_feed(self.conn, limit=50)),
            ("task_counts_by_department", lambda: task_counts_by_department(self.conn)),
            ("inventory_health_percentage", lambda: inventory_health_percentage(self.conn)),
        ]:
            start = time.perf_counter()
            fn()
            elapsed = time.perf_counter() - start
            self.assertLess(elapsed, budget_seconds, f"{label} took {elapsed:.3f}s, over the {budget_seconds}s budget")

    def test_results_remain_correct_at_scale(self):
        health = inventory_health_percentage(self.conn)
        self.assertEqual(health["total_vehicles"], self.VEHICLE_COUNT)
        self.assertEqual(health["healthy_vehicles"], self.VEHICLE_COUNT - self.unhealthy_count)

        feed = recent_activity_feed(self.conn, limit=50)
        self.assertEqual(len(feed), 50)

        status = connected_systems_status(self.conn)
        self.assertEqual(len(status), 5)

        counts = task_counts_by_department(self.conn)
        self.assertEqual(counts, {"Unassigned": self.unhealthy_count})


if __name__ == "__main__":
    unittest.main()
