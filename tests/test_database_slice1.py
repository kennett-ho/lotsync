"""
Phase 2, Slice 1 verification -- see IMPLEMENTATION_PLAN.md.

Two things this slice promises, both checked here:
1. Pure addition: passing a database connection into
   reconcile_keyper_tekion() must not change any existing report output
   at all, byte-for-byte, versus not passing one.
2. A SQLite Vehicle/Event trail actually gets written, with row counts
   consistent with Keyper's import -- specifically, only for records
   that resolved to an actual VIN (fully_verified, key_out_aging, and
   the sold_key_not_removed_from_keyper case). Records with no
   resolvable VIN (pending_dms_entry, out_and_unmatched, and every
   data_quality_exceptions case) are deliberately excluded -- that
   population's handling is Slice 2's explicit decision to make, not
   this slice's.

Uses the same synthetic fixtures as test_regression.py -- see
tests/fixtures/README.md for what each row represents. The 6 expected
VINs below were read directly off keyper.csv/tekion_master.csv/
tekion_sold.csv, not inferred.
"""

import os
import tempfile
import unittest

import pandas as pd

from lotsync.config.settings import load_settings, load_day_out_buckets
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.sync.reconciler import reconcile_keyper_tekion
from lotsync.database.repository import connect, upsert_vehicle, insert_event

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")

# VINs that should end up in the DB -- every Keyper record that
# resolves to a real vehicle identity (fully_verified + key_out_aging
# + the one sold-key-not-removed case). Read directly off the fixture
# CSVs, not recomputed from the reconciler under test.
EXPECTED_VINS = {
    "1TESTVIN000000001",  # K30001 -- fully_verified
    "1TESTVIN000099999",  # 099999 -- fully_verified via last-6
    "1TESTVIN000000099",  # K30099 -- fully_verified via prefix, wrong System tag
    "1TESTVIN000000002",  # K30002 -- key_out_aging
    "1TESTVIN000000003",  # K30003 -- key_out_aging
    "1TESTVIN000030005",  # K30005 -- sold_key_not_removed_from_keyper
}


def _load_inputs():
    settings = load_settings(CONFIG)
    day_out_buckets = load_day_out_buckets(CONFIG)
    keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    return keyper_df, tekion_df, sold_df, settings["sync_date"], day_out_buckets


class ReconcileKeyperTekionPureAdditionTest(unittest.TestCase):
    """db_conn is opt-in -- passing one must not change report output."""

    def test_report_output_identical_with_and_without_db_conn(self):
        keyper_df, tekion_df, sold_df, sync_date, buckets = _load_inputs()

        without_db = reconcile_keyper_tekion(keyper_df, tekion_df, sold_df, sync_date, buckets)

        conn = connect(":memory:")
        with_db = reconcile_keyper_tekion(
            keyper_df, tekion_df, sold_df, sync_date, buckets,
            db_conn=conn, sync_run_id="test-run-1",
        )

        # matched_tekion_idx (a set, the 5th return value) compares directly;
        # the four DataFrames compare via assert_frame_equal.
        for i, (a, b) in enumerate(zip(without_db[:4], with_db[:4])):
            pd.testing.assert_frame_equal(a, b, check_like=False)
        self.assertEqual(without_db[4], with_db[4])


class KeyperWritePathTest(unittest.TestCase):
    """The actual Vehicle/Event trail this slice adds."""

    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = _load_inputs()
        self.conn = connect(":memory:")

    def test_vehicle_rows_match_only_vin_resolvable_keyper_records(self):
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        vins = {row[0] for row in self.conn.execute("SELECT vin FROM vehicle")}
        self.assertEqual(vins, EXPECTED_VINS)

    def test_event_count_matches_vehicle_count_on_first_run(self):
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        (vehicle_count,) = self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
        (event_count,) = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()
        self.assertEqual(vehicle_count, len(EXPECTED_VINS))
        self.assertEqual(event_count, len(EXPECTED_VINS))

    def test_keyper_status_persisted_correctly_for_in_and_out(self):
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        status = dict(self.conn.execute("SELECT vin, keyper_status FROM vehicle"))
        self.assertEqual(status["1TESTVIN000000001"], "In")     # K30001, In
        self.assertEqual(status["1TESTVIN000000002"], "Out")    # K30002, Out
        self.assertEqual(status["1TESTVIN000030005"], "In")     # K30005, sold but still In

    def test_no_vehicle_row_for_unresolvable_identity_records(self):
        # K30006 (pending_dms_entry), K30007 (out_and_unmatched), 784,
        # #ODD1, 555555 (all exceptions) never resolve to a VIN -- must
        # not appear in the DB at all. That population's handling is
        # Slice 2's explicit decision, not this slice's.
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        (vehicle_count,) = self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
        self.assertEqual(vehicle_count, 6, "unresolvable-identity Keyper records must not reach the DB yet")

    def test_no_db_activity_when_db_conn_omitted(self):
        # Sanity check on the opt-in default -- this doesn't touch a DB
        # at all, just confirms the call succeeds with its old signature.
        result = reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
        )
        self.assertEqual(len(result), 5)

    def test_rerunning_without_diffing_writes_duplicate_events_not_errors(self):
        # Slice 1 has no change-detection yet (that's Slice 3) -- running
        # the same input twice is expected to double the Event count
        # while Vehicle stays upserted to one row per VIN. This pins
        # down today's known, accepted behavior so Slice 3's introduction
        # of diffing is a deliberate, visible change to this test, not a
        # silent one.
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-2",
        )
        (vehicle_count,) = self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
        (event_count,) = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()
        self.assertEqual(vehicle_count, len(EXPECTED_VINS))
        self.assertEqual(event_count, 2 * len(EXPECTED_VINS))


class RepositoryMigrationTest(unittest.TestCase):
    def test_connecting_twice_to_same_file_is_idempotent(self):
        # Asserts against schema_migrations' count staying the SAME
        # across a reconnect, not a hardcoded literal -- the literal
        # migration count grows every slice that adds one (Slice 1: 1,
        # Slice 2: 2, ...), and hardcoding it here was itself a latent
        # fragility that this slice's new migration immediately exposed.
        # What this test actually needs to prove is "reconnecting
        # doesn't re-apply anything," which a stable count across two
        # connects demonstrates regardless of how many migrations exist.
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "lotsync_test.db")
            conn1 = connect(db_path)
            (applied_first,) = conn1.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
            self.assertGreaterEqual(applied_first, 1)
            conn1.close()
            conn2 = connect(db_path)  # must not error or re-apply anything
            try:
                (applied_second,) = conn2.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
                self.assertEqual(applied_second, applied_first)
            finally:
                # try/finally, not a bare close() after the assertion --
                # a failed assertion above must not leave the connection
                # open, or Windows locks the file and the tempdir cleanup
                # above fails with a PermissionError instead of showing
                # the actual test failure.
                conn2.close()

    def test_upsert_vehicle_partial_update_does_not_clobber_other_columns(self):
        conn = connect(":memory:")
        upsert_vehicle(conn, "VIN1", keyper_status="In")
        upsert_vehicle(conn, "VIN1", stock_number="K1")
        row = conn.execute(
            "SELECT keyper_status, stock_number FROM vehicle WHERE vin = ?", ("VIN1",)
        ).fetchone()
        self.assertEqual(row, ("In", "K1"))

    def test_insert_event_round_trips_detail_fields_as_json(self):
        conn = connect(":memory:")
        upsert_vehicle(conn, "VIN1", keyper_status="In")
        insert_event(conn, vin="VIN1", event_type="keyper_observed", source="keyper",
                     detail_fields={"keyper_status": "In", "days_out": None})
        import json
        (raw,) = conn.execute("SELECT detail_fields FROM event WHERE vin = ?", ("VIN1",)).fetchone()
        self.assertEqual(json.loads(raw), {"keyper_status": "In", "days_out": None})


if __name__ == "__main__":
    unittest.main()
