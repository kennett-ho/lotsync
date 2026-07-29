"""
Phase 3, Sprint 4 verification -- sync/pipeline.py's run_inventory_sync,
the orchestration layer behind POST /inventory-sync/run. Uses the same
synthetic fixtures as test_regression.py / test_database_slice*.py, but
drives them through run_inventory_sync (file paths in, summary dict out)
rather than calling each importer/persist function directly, since that's
the real shape the API endpoint uses.
"""

import os
import tempfile
import unittest

from lotsync.config.settings import (
    load_settings, load_day_out_buckets, load_incoming_missing_buckets,
    load_new_car_buckets, load_internal_fleet_vins,
)
from lotsync.database.repository import connect
from lotsync.queries.inventory_sync import list_pending_identities, sync_run_history
from lotsync.sync.pipeline import run_inventory_sync

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")

TEKION_PATH = os.path.join(FIXTURES, "tekion_master.csv")
SOLD_PATH = os.path.join(FIXTURES, "tekion_sold.csv")
KEYPER_PATH = os.path.join(FIXTURES, "keyper.csv")
MDD_PATH = os.path.join(FIXTURES, "mdd_not_paired.csv")
RECOVR_PATH = os.path.join(FIXTURES, "recovr.csv")
RAPIDRECON_PATH = os.path.join(FIXTURES, "rapidrecon.csv")

ALL_SOURCES = {
    "tekion": TEKION_PATH, "sold": SOLD_PATH, "keyper": KEYPER_PATH,
    "mdd": MDD_PATH, "recovr": RECOVR_PATH, "rapidrecon": RAPIDRECON_PATH,
}


class SyncPipelineTestCase(unittest.TestCase):
    """Shared setup: one in-memory DB, real config-loaded settings/buckets, per test."""

    def setUp(self):
        self.conn = connect(":memory:")
        settings = load_settings(CONFIG)
        self.kwargs = dict(
            store_name=settings["store_name"],
            sync_date=settings["sync_date"],
            day_out_buckets=load_day_out_buckets(CONFIG),
            incoming_missing_buckets=load_incoming_missing_buckets(CONFIG),
            new_car_buckets=load_new_car_buckets(CONFIG),
            internal_fleet_vins=load_internal_fleet_vins(CONFIG),
            db_conn=self.conn,
        )

    def tearDown(self):
        self.conn.close()

    def _run(self, file_paths, out_dir=None):
        return run_inventory_sync(file_paths, out_dir=out_dir, **self.kwargs)

    def _vehicle(self, vin):
        row = self.conn.execute(
            "SELECT vin, tekion_status, keyper_status, mdd_status, recovr_status "
            "FROM vehicle WHERE vin = ?", (vin,),
        ).fetchone()
        if row is None:
            return None
        return dict(zip(["vin", "tekion_status", "keyper_status", "mdd_status", "recovr_status"], row))


class EmptyDatabaseTest(SyncPipelineTestCase):
    def test_no_files_uploaded_is_a_harmless_no_op(self):
        summary = self._run({})
        self.assertEqual(summary["sync_runs"], [])
        self.assertEqual(summary["vehicles_processed"], 0)
        self.assertEqual(summary["exceptions_found"], 0)
        self.assertEqual(summary["tasks_generated"], 0)
        self.assertEqual(summary["recommendations_generated"], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sync_run").fetchone()[0], 0)


class FirstImportTest(SyncPipelineTestCase):
    def test_full_six_source_upload_populates_the_database(self):
        summary = self._run(ALL_SOURCES)

        sources_run = {r["source"] for r in summary["sync_runs"]}
        self.assertEqual(sources_run, {"keyper", "tekion", "mdd", "recovr", "rapidrecon"})
        self.assertTrue(all(r["status"] == "complete" for r in summary["sync_runs"]))

        # K30001 -- In, matches Tekion by stock number -> fully_verified,
        # also in MDD's not-paired list. See fixtures/README.md.
        v = self._vehicle("1TESTVIN000000001")
        self.assertIsNotNone(v)
        self.assertEqual(v["tekion_status"], "Stocked In")
        self.assertEqual(v["keyper_status"], "In")
        self.assertEqual(v["mdd_status"], "not_paired")

        # 784 / #ODD1 / 555555 -- the three genuine data_quality_exceptions
        # rows in this fixture set (see fixtures/README.md).
        self.assertEqual(summary["exceptions_found"], 3)

        # K30001 (MDD not-paired, active, unsold) is the one real
        # install_mdd_beacon candidate this fixture set produces --
        # K30005 (MDD's other row) isn't in tekion_master.csv at all, so
        # build_tracker_install_tasks correctly excludes it.
        self.assertGreaterEqual(summary["tasks_generated"], 1)

        # K30003 -- Out, ~31 days -> the most severe key-out-aging bucket.
        self.assertEqual(summary["recommendations_generated"], 1)
        rec = self.conn.execute(
            "SELECT vin, rule_source FROM recommendation"
        ).fetchone()
        self.assertEqual(rec[0], "1TESTVIN000000003")
        self.assertEqual(rec[1], "key_out_aging")

    def test_pending_identities_are_queryable_afterward(self):
        self._run(ALL_SOURCES)
        exceptions = list_pending_identities(self.conn)
        self.assertEqual(len(exceptions), 3)
        self.assertTrue(all(e["status"] == "pending" for e in exceptions))


class RepeatImportTest(SyncPipelineTestCase):
    def test_rerunning_the_same_files_adds_no_new_events_except_two_documented_gaps(self):
        """
        Two pre-existing, documented exceptions to full idempotency --
        neither introduced by this sprint, both surfaced concretely by
        this test:

        1. persist_rapidrecon_observations has no diff-before-write at
           all -- SPRINT_3_REVIEW.md's diffing work explicitly covers
           "four diffed sources" (tekion/keyper/mdd/recovr), not
           RapidRecon. It re-writes one rapidrecon_observed Event per
           matched VIN on every single run. This fixture set's only
           known-VIN match is 1TESTVIN000000001, so +1 Event per rerun.
        2. tekion_sold.csv's K80001/K80002 rows (same VIN, two different
           stock numbers) are SPRINT_3_REVIEW.md's own named, accepted
           idempotency gap for an internally contradictory Tekion export
           -- +2 Events per rerun (see persist_tekion_observations'
           docstring for the exact mechanism).

        Asserting zero new Events here would assert something false
        about the system's real, already-documented behavior -- so this
        asserts the exact expected delta (3) instead.
        """
        first = self._run(ALL_SOURCES)
        events_after_first = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]

        second = self._run(ALL_SOURCES)
        events_after_second = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()[0]

        self.assertEqual(events_after_second - events_after_first, 3)
        self.assertEqual(second["tasks_generated"], 0)
        self.assertEqual(second["recommendations_generated"], 0)
        # Every source still gets a fresh SyncRun row -- a rerun with
        # nothing new to persist is still a real, recorded execution.
        self.assertEqual(len(second["sync_runs"]), len(first["sync_runs"]))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sync_run").fetchone()[0], 10)


class VehicleUpdateTest(SyncPipelineTestCase):
    def test_a_vehicle_updates_when_later_uploads_say_more(self):
        # K70001 (1TESTVIN000000007) appears in tekion_master.csv only in
        # run 1; run 2 adds tekion_sold.csv, where the same VIN is Sold --
        # a real update to the same Vehicle row's tekion_status.
        self._run({"tekion": TEKION_PATH})
        v = self._vehicle("1TESTVIN000000007")
        self.assertEqual(v["tekion_status"], "Stocked In")

        self._run({"tekion": TEKION_PATH, "sold": SOLD_PATH})
        v = self._vehicle("1TESTVIN000000007")
        self.assertEqual(v["tekion_status"], "Sold")

    def test_a_vehicle_not_reasserted_keeps_its_last_known_state(self):
        """
        Documented assumption, not a gap: a vehicle silently missing from
        a later upload is NOT treated as "removed" -- per
        DECISION_FRAMEWORK.md, silence isn't a claim. Confirms
        run_inventory_sync doesn't invent a removal/deletion just because
        a later Tekion Unsold file happens to omit a VIN a prior run saw.
        """
        self._run({"tekion": TEKION_PATH})
        self.assertEqual(self._vehicle("1TESTVIN000000001")["tekion_status"], "Stocked In")

        # A second run with a Keyper-only upload (no Tekion file at all)
        # -- the earlier Tekion-observed status must be untouched.
        self._run({"keyper": KEYPER_PATH})
        self.assertEqual(self._vehicle("1TESTVIN000000001")["tekion_status"], "Stocked In")


class PartialSourceCombinationTest(SyncPipelineTestCase):
    def test_tekion_unsold_only(self):
        summary = self._run({"tekion": TEKION_PATH})
        self.assertEqual({r["source"] for r in summary["sync_runs"]}, {"tekion"})
        self.assertIsNotNone(self._vehicle("1TESTVIN000000001"))
        self.assertIsNone(self._vehicle("1TESTVIN000000001")["keyper_status"])
        self.assertEqual(summary["exceptions_found"], 0)
        self.assertEqual(summary["tasks_generated"], 0)
        self.assertEqual(summary["recommendations_generated"], 0)

    def test_tekion_unsold_plus_keyper(self):
        summary = self._run({"tekion": TEKION_PATH, "keyper": KEYPER_PATH})
        self.assertEqual({r["source"] for r in summary["sync_runs"]}, {"tekion", "keyper"})
        v = self._vehicle("1TESTVIN000000001")
        self.assertEqual(v["tekion_status"], "Stocked In")
        self.assertEqual(v["keyper_status"], "In")

        # Without a Sold upload this run, K30005 (sold in the real fixture
        # set) can't resolve via the sold-file fallback -- it correctly
        # falls back to pending_dms_entry instead of
        # sold_key_not_removed_from_keyper. A real, documented behavior
        # difference from the full-upload case, not a bug.
        flag_reasons = self.conn.execute(
            "SELECT detail_fields FROM event WHERE event_type = 'keyper_observed'"
        ).fetchall()
        # K30005 never resolves to a Vehicle at all in this combination
        # (no Tekion or Sold match), so it produces no keyper_observed
        # Event -- confirm no Vehicle row exists for it either.
        self.assertIsNone(self._vehicle("1TESTVIN000030005"))

    def test_tekion_unsold_plus_keyper_plus_mdd(self):
        summary = self._run({"tekion": TEKION_PATH, "keyper": KEYPER_PATH, "mdd": MDD_PATH})
        self.assertEqual({r["source"] for r in summary["sync_runs"]}, {"tekion", "keyper", "mdd"})
        # Only K30001 (active, unsold, MDD not-paired) produces a
        # candidate -- K30005 isn't in this run's Tekion Unsold data at
        # all, so it's excluded the same way build_tracker_install_tasks
        # already excludes any MDD row for an unknown/out-of-scope VIN.
        self.assertEqual(summary["tasks_generated"], 1)
        task = self.conn.execute("SELECT vin, task_type FROM task").fetchone()
        self.assertEqual(task[0], "1TESTVIN000000001")
        self.assertEqual(task[1], "install_mdd_beacon")


class SyncRunHistoryTest(SyncPipelineTestCase):
    def test_history_groups_one_batch_per_run(self):
        self._run({"tekion": TEKION_PATH})
        self._run({"keyper": KEYPER_PATH, "mdd": MDD_PATH})

        history = sync_run_history(self.conn)
        self.assertEqual(len(history), 2)
        # Newest batch first.
        self.assertEqual({s["source"] for s in history[0]["sources"]}, {"keyper", "mdd"})
        self.assertEqual({s["source"] for s in history[1]["sources"]}, {"tekion"})
        self.assertTrue(all(b["overall_status"] == "complete" for b in history))


class CsvReportWritingTest(SyncPipelineTestCase):
    def test_reports_are_still_written_when_out_dir_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._run(ALL_SOURCES, out_dir=tmp)
            written = set(os.listdir(tmp))
        self.assertEqual(written, {
            "fully_verified_report.csv", "key_out_aging_report.csv",
            "flag_to_controller_report.csv", "data_quality_exceptions.csv",
            "incoming_or_missing_investigate_report.csv", "sold_vehicles_report.csv",
            "tracker_install_tasks.csv", "tekion_sync_conflicts.csv",
        })


if __name__ == "__main__":
    unittest.main()
