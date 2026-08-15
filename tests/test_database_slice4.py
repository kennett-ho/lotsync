"""
Phase 2, Slice 4 verification -- see IMPLEMENTATION_PLAN.md.

SyncRun provenance, plus the Sprint 3 kickoff decision to give it real
transactional semantics: 'complete' means every write a source made
during a run committed successfully; 'failed' means none of them did.
Uses the same synthetic fixtures as the other Phase 2 test files.
"""

import os
import unittest

from lotsync.config.settings import load_settings, load_day_out_buckets
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.importers.mdd import load_mdd_not_paired
from lotsync.importers.recovr import load_recovr_full
from lotsync.importers.rapidrecon import load_rapidrecon
from lotsync.sync.reconciler import (
    reconcile_keyper_tekion, persist_tekion_observations,
    persist_mdd_observations, persist_recovr_observations,
    persist_rapidrecon_observations,
)
from lotsync.database.repository import connect, sync_run, upsert_vehicle, insert_event

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")


def _load_inputs():
    settings = load_settings(CONFIG)
    day_out_buckets = load_day_out_buckets(CONFIG)
    keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    mdd_df = load_mdd_not_paired(os.path.join(FIXTURES, "mdd_not_paired.csv"))
    recovr_df = load_recovr_full(os.path.join(FIXTURES, "recovr.csv"))
    rapidrecon_df = load_rapidrecon(os.path.join(FIXTURES, "rapidrecon.csv"))
    return keyper_df, tekion_df, sold_df, mdd_df, recovr_df, rapidrecon_df, settings["sync_date"], day_out_buckets


def _run_full_pipeline_with_sync_runs(conn, keyper_df, tekion_df, sold_df, mdd_df,
                                       recovr_df, rapidrecon_df, sync_date, buckets):
    # Mirrors main.py's real orchestration -- one sync_run() per source.
    with sync_run(conn, "keyper", records_processed=len(keyper_df)) as run_id:
        reconcile_keyper_tekion(
            keyper_df, tekion_df, sold_df, sync_date, buckets,
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


class SyncRunProvenanceTest(unittest.TestCase):
    """
    IMPLEMENTATION_PLAN.md Slice 4 Definition of Done: one SyncRun row
    per source with correct counts; every Event has a valid sync_run_id;
    zero orphaned Events.
    """

    def setUp(self):
        (self.keyper_df, self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
         self.rapidrecon_df, self.sync_date, self.buckets) = _load_inputs()
        self.conn = connect(":memory:")

    def test_one_sync_run_per_source_with_correct_records_processed(self):
        _run_full_pipeline_with_sync_runs(
            self.conn, self.keyper_df, self.tekion_df, self.sold_df,
            self.mdd_df, self.recovr_df, self.rapidrecon_df, self.sync_date, self.buckets,
        )
        rows = dict(self.conn.execute("SELECT source, records_processed FROM sync_run"))
        self.assertEqual(rows, {
            "keyper": len(self.keyper_df),
            "tekion": len(self.tekion_df) + len(self.sold_df),
            "mdd": len(self.mdd_df),
            "recovr": len(self.recovr_df),
            "rapidrecon": len(self.rapidrecon_df),
        })

    def test_every_sync_run_marked_complete_on_a_clean_run(self):
        _run_full_pipeline_with_sync_runs(
            self.conn, self.keyper_df, self.tekion_df, self.sold_df,
            self.mdd_df, self.recovr_df, self.rapidrecon_df, self.sync_date, self.buckets,
        )
        statuses = {row[0] for row in self.conn.execute("SELECT status FROM sync_run")}
        self.assertEqual(statuses, {"complete"})

    def test_every_event_has_a_valid_sync_run_id_no_orphans(self):
        # IMPLEMENTATION_PLAN.md Success Metrics: "No orphaned Events, an
        # explicit assertion in tests" -- proven at the application level
        # here rather than via a hard schema FK; see
        # migrations/0003_sync_run.sql for why no FK is declared.
        #
        # The orphan check is done via a single SQL query, not by pulling
        # both ID sets into Python and comparing them there: event.sync_run_id
        # is a TEXT-affinity column (declared in migrations/0001_initial.sql,
        # unchanged to preserve Slices 1-3's free-form string calling
        # convention) while sync_run.sync_run_id is a real INTEGER PK --
        # SQLite stores the same value written by start_sync_run() as '1'
        # (text) in one column and 1 (integer) in the other, so a
        # Python-side set comparison sees them as different objects even
        # though SQLite's own type-affinity rules correctly treat them as
        # equal inside a query (verified directly: `sync_run_id NOT IN
        # (SELECT sync_run_id FROM sync_run)` returns 0 rows).
        _run_full_pipeline_with_sync_runs(
            self.conn, self.keyper_df, self.tekion_df, self.sold_df,
            self.mdd_df, self.recovr_df, self.rapidrecon_df, self.sync_date, self.buckets,
        )
        (null_sync_run_id_count,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE sync_run_id IS NULL"
        ).fetchone()
        self.assertEqual(null_sync_run_id_count, 0, "every Event must carry a sync_run_id")

        # Sprint 03: CAST makes the TEXT-vs-INTEGER comparison explicit
        # and portable. SQLite's type affinity used to coerce this
        # silently; PostgreSQL refuses to compare text against integer
        # at all. Same question, same answer, now honest about types.
        (orphan_count,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE sync_run_id NOT IN "
            "(SELECT CAST(sync_run_id AS TEXT) FROM sync_run)"
        ).fetchone()
        self.assertEqual(orphan_count, 0, "orphaned Events found with sync_run_ids not in sync_run")

    def test_completed_at_and_started_at_are_set_on_completion(self):
        _run_full_pipeline_with_sync_runs(
            self.conn, self.keyper_df, self.tekion_df, self.sold_df,
            self.mdd_df, self.recovr_df, self.rapidrecon_df, self.sync_date, self.buckets,
        )
        rows = self.conn.execute("SELECT started_at, completed_at FROM sync_run").fetchall()
        self.assertTrue(all(started is not None and completed is not None for started, completed in rows))


class TransactionalIntegrityTest(unittest.TestCase):
    """
    Sprint 3 kickoff decision: SyncRun's transaction boundary must span
    ALL of a source's writes -- 'complete' iff everything committed,
    'failed' iff nothing did. Exercises sync_run() directly against
    repository primitives rather than through business-logic functions,
    to isolate the transactional contract itself from reconciliation
    logic.
    """

    def setUp(self):
        self.conn = connect(":memory:")

    def test_successful_block_commits_everything_and_marks_complete(self):
        with sync_run(self.conn, "keyper", records_processed=1) as run_id:
            upsert_vehicle(self.conn, "VIN1", keyper_status="In")
            insert_event(self.conn, vin="VIN1", event_type="keyper_observed", source="keyper",
                         sync_run_id=run_id, summary="test")

        (vehicle_count,) = self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
        (event_count,) = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()
        self.assertEqual(vehicle_count, 1)
        self.assertEqual(event_count, 1)

        status, records_processed = self.conn.execute(
            "SELECT status, records_processed FROM sync_run"
        ).fetchone()
        self.assertEqual(status, "complete")
        self.assertEqual(records_processed, 1)

    def test_failed_block_commits_nothing_and_marks_sync_run_failed(self):
        with self.assertRaises(RuntimeError):
            with sync_run(self.conn, "keyper", records_processed=5) as run_id:
                upsert_vehicle(self.conn, "VIN1", keyper_status="In")
                insert_event(self.conn, vin="VIN1", event_type="keyper_observed", source="keyper",
                             sync_run_id=run_id, summary="should not survive")
                raise RuntimeError("simulated failure mid-source")

        (vehicle_count,) = self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
        (event_count,) = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()
        self.assertEqual(vehicle_count, 0, "no partial writes from a failed run may persist")
        self.assertEqual(event_count, 0, "no partial writes from a failed run may persist")

        status, completed_at = self.conn.execute(
            "SELECT status, completed_at FROM sync_run"
        ).fetchone()
        self.assertEqual(status, "failed")
        self.assertIsNotNone(completed_at)

    def test_exception_propagates_after_marking_failed(self):
        # sync_run() must not swallow the exception -- Slice 4 only
        # strengthens the provenance/transactional guarantee, it doesn't
        # change whether a write failure should stop the pipeline.
        with self.assertRaises(ValueError):
            with sync_run(self.conn, "mdd", records_processed=1):
                raise ValueError("boom")

    def test_a_prior_successful_run_survives_a_later_failed_run(self):
        with sync_run(self.conn, "keyper", records_processed=1) as run_id:
            upsert_vehicle(self.conn, "VIN1", keyper_status="In")
            insert_event(self.conn, vin="VIN1", event_type="keyper_observed", source="keyper",
                         sync_run_id=run_id, summary="first, successful run")

        with self.assertRaises(RuntimeError):
            with sync_run(self.conn, "tekion", records_processed=1):
                upsert_vehicle(self.conn, "VIN2", tekion_status="Stocked In")
                raise RuntimeError("simulated failure on the second run")

        vins = {row[0] for row in self.conn.execute("SELECT vin FROM vehicle")}
        self.assertEqual(vins, {"VIN1"}, "an unrelated prior committed run must survive a later rollback")

        statuses = dict(self.conn.execute("SELECT source, status FROM sync_run"))
        self.assertEqual(statuses, {"keyper": "complete", "tekion": "failed"})


if __name__ == "__main__":
    unittest.main()
