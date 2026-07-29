"""
Phase 2, Slice 2 verification -- see IMPLEMENTATION_PLAN.md.

Extends Slice 1's write path (Keyper only) to full source coverage
plus PendingIdentity capture for Keyper's unresolved-identity
population. Uses the same synthetic fixtures as test_regression.py /
test_database_slice1.py.
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
from lotsync.database.repository import connect

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")

# The fixture's known unresolved-identity Keyper records -- read
# directly off keyper.csv / tests/fixtures/README.md, not recomputed
# from the reconciler under test.
EXPECTED_PENDING_IDENTITIES = {
    ("keyper", "784"): "tekion_auto_generated_stock_number",
    ("keyper", "#ODD1"): "unrecognized",
    ("keyper", "555555"): "ambiguous_last6_vin_multiple_matches",
}


def _load_inputs():
    settings = load_settings(CONFIG)
    day_out_buckets = load_day_out_buckets(CONFIG)
    keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    return keyper_df, tekion_df, sold_df, settings["sync_date"], day_out_buckets


class PendingIdentityCaptureTest(unittest.TestCase):
    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = _load_inputs()
        self.conn = connect(":memory:")

    def _run(self, sync_run_id="test-run-1"):
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id=sync_run_id,
        )

    def test_unresolved_identity_records_are_captured_not_dropped(self):
        self._run()
        rows = {
            (source, raw_identifier): identifier_type
            for source, raw_identifier, identifier_type in self.conn.execute(
                "SELECT source, raw_identifier, identifier_type FROM pending_identity"
            )
        }
        self.assertEqual(rows, EXPECTED_PENDING_IDENTITIES)

    def test_pending_identity_count_matches_data_quality_exceptions(self):
        # Mirrors this slice's Definition of Done: PendingIdentity count
        # matches data_quality_exceptions.csv's applicable rows -- 3 in
        # this fixture (see tests/fixtures/README.md).
        self._run()
        (count,) = self.conn.execute("SELECT COUNT(*) FROM pending_identity").fetchone()
        self.assertEqual(count, 3)

    def test_captured_rows_start_pending_with_no_resolution(self):
        self._run()
        statuses = {row[0] for row in self.conn.execute("SELECT status FROM pending_identity")}
        self.assertEqual(statuses, {"pending"})
        unresolved = self.conn.execute(
            "SELECT resolved_vin, resolved_at FROM pending_identity"
        ).fetchall()
        self.assertTrue(all(vin is None and at is None for vin, at in unresolved))

    def test_rerun_upserts_by_identifier_not_insert_duplicate_rows(self):
        # Validates the design decision from Sprint 2's kickoff: a
        # PendingIdentity is upserted, keyed by (source, raw_identifier),
        # NOT inserted fresh every run like Event -- otherwise this
        # slice's Definition of Done (count matches
        # data_quality_exceptions.csv) would silently break after a
        # second run.
        self._run(sync_run_id="test-run-1")
        (count_after_first,) = self.conn.execute("SELECT COUNT(*) FROM pending_identity").fetchone()
        first_observed = dict(
            self.conn.execute("SELECT raw_identifier, first_observed_at FROM pending_identity")
        )

        self._run(sync_run_id="test-run-2")
        (count_after_second,) = self.conn.execute("SELECT COUNT(*) FROM pending_identity").fetchone()
        second_observed = dict(
            self.conn.execute("SELECT raw_identifier, first_observed_at FROM pending_identity")
        )

        self.assertEqual(count_after_first, 3)
        self.assertEqual(count_after_second, 3, "rerun must upsert, not duplicate, pending_identity rows")
        self.assertEqual(first_observed, second_observed, "first_observed_at must not change on re-observation")

    def test_pending_identity_write_does_not_change_report_output(self):
        # Same pure-addition guarantee as Slice 1, specifically for the
        # exceptions report this population also appears in.
        without_db = reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
        )
        with_db = reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        import pandas as pd
        pd.testing.assert_frame_equal(without_db[3], with_db[3])  # exceptions is index 3


class TekionWritePathTest(unittest.TestCase):
    """
    persist_tekion_observations -- independent of Keyper. tekion_master
    has 14 distinct VINs, tekion_sold has 4 distinct VINs (K80001/
    K80002 share one), and exactly one VIN (K70001 / 1TESTVIN000000007)
    appears in BOTH -- union is 17, not 18. Counts read directly off
    the fixture CSVs, not recomputed from the function under test.
    """

    def setUp(self):
        _, self.tekion_df, self.sold_df, _, _ = _load_inputs()
        self.conn = connect(":memory:")

    def test_vehicle_count_matches_union_of_tekion_and_sold_vins(self):
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        (count,) = self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
        self.assertEqual(count, 17)

    def test_master_list_status_persisted_for_unsold_vehicle(self):
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        (status,) = self.conn.execute(
            "SELECT tekion_status FROM vehicle WHERE vin = ?", ("1TESTVIN000050001",)
        ).fetchone()
        self.assertEqual(status, "Stocked In")

    def test_sold_status_wins_for_vehicle_in_both_master_and_sold(self):
        # 1TESTVIN000000007 (K70001) is the sync-conflict fixture VIN --
        # present in both tekion_master (Stocked In) and tekion_sold
        # (Sold). Vehicle is a current-state cache, not history, so the
        # persisted status should reflect Sold -- the Master/Unsold
        # observation is still preserved as its own Event, just not as
        # current state.
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        (status,) = self.conn.execute(
            "SELECT tekion_status FROM vehicle WHERE vin = ?", ("1TESTVIN000000007",)
        ).fetchone()
        self.assertEqual(status, "Sold")
        (event_count,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin = ?", ("1TESTVIN000000007",)
        ).fetchone()
        self.assertEqual(event_count, 2, "both the Master/Unsold and Sold observations must be preserved as Events")

    def test_duplicate_sold_vin_last_row_wins_for_stock_number_both_events_preserved(self):
        # K80001 then K80002, same VIN -- last write (K80002) wins for
        # the current-state stock_number; both are still preserved as
        # separate Events.
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        (stock,) = self.conn.execute(
            "SELECT stock_number FROM vehicle WHERE vin = ?", ("1TESTVIN000080001",)
        ).fetchone()
        self.assertEqual(stock, "K80002")
        (event_count,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin = ?", ("1TESTVIN000080001",)
        ).fetchone()
        self.assertEqual(event_count, 2)

    def test_no_op_when_db_conn_omitted(self):
        # Must not raise, and must not require a connection.
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=None)

    def test_does_not_mutate_input_dataframes(self):
        import pandas as pd
        tekion_before = self.tekion_df.copy(deep=True)
        sold_before = self.sold_df.copy(deep=True)
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        pd.testing.assert_frame_equal(self.tekion_df, tekion_before)
        pd.testing.assert_frame_equal(self.sold_df, sold_before)

    def test_master_list_display_name_persisted_verbatim(self):
        # Regression test for a real gap: Tekion's "Year Make Model"
        # column was never persisted anywhere -- confirmed against a
        # real 4,312-vehicle dealership database (0 vehicles had it
        # populated) before this fix. Copied verbatim, not parsed.
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        (display_name,) = self.conn.execute(
            "SELECT display_name FROM vehicle WHERE vin = ?", ("1TESTVIN000050001",)
        ).fetchone()
        self.assertEqual(display_name, "2026 New Car")

    def test_sold_display_name_wins_for_vehicle_in_both_master_and_sold(self):
        # Same "current-state cache, sold wins" rule display_name shares
        # with tekion_status/stock_number (see
        # test_sold_status_wins_for_vehicle_in_both_master_and_sold
        # above) -- exercised with deliberately different text between
        # the two rows, since every real fixture VIN happens to share
        # identical "Year Make Model" text across its master/sold rows.
        import pandas as pd
        tekion_df = pd.DataFrame([{
            "Stock #": "K90010", "VIN #": "1TESTVIN000090010", "Status": "Stocked In",
            "Year Make Model": "2024 Master List Text", "Stocked In Date": "Jul 1 2026",
            "is_internal_fleet": False,
        }])
        sold_df = pd.DataFrame([{
            "Stock #": "K90010", "VIN #": "1TESTVIN000090010", "Status": "Sold",
            "Year Make Model": "2024 Sold List Text", "Sold Date": "Jul 2 2026",
        }])
        persist_tekion_observations(tekion_df, sold_df, db_conn=self.conn)
        (display_name,) = self.conn.execute(
            "SELECT display_name FROM vehicle WHERE vin = ?", ("1TESTVIN000090010",)
        ).fetchone()
        self.assertEqual(display_name, "2024 Sold List Text")

    def test_display_name_change_alone_updates_cache_without_new_event(self):
        # display_name is deliberately NOT part of the diff key that
        # decides whether a new Event fires (see
        # persist_tekion_observations' docstring) -- a rerun with an
        # unchanged status/stock but a corrected description must still
        # update the cached current value, without generating a second,
        # spurious Event the way a real status/stock change would.
        import pandas as pd
        base_row = {
            "Stock #": "K90020", "VIN #": "1TESTVIN000090020", "Status": "Stocked In",
            "Stocked In Date": "Jul 1 2026", "is_internal_fleet": False,
        }
        first_run = pd.DataFrame([{**base_row, "Year Make Model": "2024 Original Text"}])
        persist_tekion_observations(first_run, self.sold_df.iloc[0:0], db_conn=self.conn)

        second_run = pd.DataFrame([{**base_row, "Year Make Model": "2024 Corrected Text"}])
        persist_tekion_observations(second_run, self.sold_df.iloc[0:0], db_conn=self.conn)

        (display_name,) = self.conn.execute(
            "SELECT display_name FROM vehicle WHERE vin = ?", ("1TESTVIN000090020",)
        ).fetchone()
        self.assertEqual(display_name, "2024 Corrected Text")
        (event_count,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin = ?", ("1TESTVIN000090020",)
        ).fetchone()
        self.assertEqual(event_count, 1, "an unchanged status/stock must not generate a second Event "
                                          "just because the free-text description changed")


class MddWritePathTest(unittest.TestCase):
    """
    persist_mdd_observations -- only annotates VINs already known as a
    Vehicle (from Tekion's write path, run first in setUp, same as
    main.py's real ordering). mdd_not_paired.csv has two rows:
    1TESTVIN000000001 (K30001, active) and 1TESTVIN000030005 (K30005,
    sold) -- both already known from tekion_master/tekion_sold.
    """

    def setUp(self):
        _, self.tekion_df, self.sold_df, _, _ = _load_inputs()
        self.mdd_df = load_mdd_not_paired(os.path.join(FIXTURES, "mdd_not_paired.csv"))
        self.conn = connect(":memory:")
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)

    def test_mdd_status_persisted_for_known_vins(self):
        persist_mdd_observations(self.mdd_df, db_conn=self.conn)
        statuses = dict(self.conn.execute(
            "SELECT vin, mdd_status FROM vehicle WHERE vin IN (?, ?)",
            ("1TESTVIN000000001", "1TESTVIN000030005"),
        ))
        self.assertEqual(statuses["1TESTVIN000000001"], "not_paired")
        self.assertEqual(statuses["1TESTVIN000030005"], "not_paired")

    def test_mdd_status_stays_null_for_vehicles_not_in_not_paired_file(self):
        # A vehicle known from Tekion but absent from MDD's not-paired
        # list must stay NULL (unknown), never inferred as "paired" --
        # MDD only ever supplies an exception list, not a full feed.
        persist_mdd_observations(self.mdd_df, db_conn=self.conn)
        (status,) = self.conn.execute(
            "SELECT mdd_status FROM vehicle WHERE vin = ?", ("1TESTVIN000000002",)
        ).fetchone()
        self.assertIsNone(status)

    def test_unknown_vin_is_skipped_not_created(self):
        import pandas as pd
        extra_row = pd.DataFrame([{"vin": "1TESTVIN999999999", "stock": "K99999",
                                    "year": 2024, "make": "Ghost", "model": "Car",
                                    "Dealership": "Mark Kia", "Geofence": "Not Paired"}])
        mdd_with_unknown = pd.concat([self.mdd_df, extra_row], ignore_index=True)
        persist_mdd_observations(mdd_with_unknown, db_conn=self.conn)
        row = self.conn.execute(
            "SELECT * FROM vehicle WHERE vin = ?", ("1TESTVIN999999999",)
        ).fetchone()
        self.assertIsNone(row, "MDD alone must never create a new Vehicle row")

    def test_no_op_when_db_conn_omitted(self):
        persist_mdd_observations(self.mdd_df, db_conn=None)


class RecovrWritePathTest(unittest.TestCase):
    """
    persist_recovr_observations -- same known-Vehicle-only restraint as
    MDD, plus fragment resolution. recovr.csv has: 1TESTVIN000000002
    (K30002, Paired=No), 1TESTVIN000090001 (K90001, sold, Paired=Yes),
    and "050001" (a short fragment that resolves uniquely to K50001's
    full VIN, Paired=No).
    """

    def setUp(self):
        _, self.tekion_df, self.sold_df, _, _ = _load_inputs()
        self.recovr_df = load_recovr_full(os.path.join(FIXTURES, "recovr.csv"))
        self.conn = connect(":memory:")
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)

    def test_not_paired_status_persisted(self):
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)
        (status,) = self.conn.execute(
            "SELECT recovr_status FROM vehicle WHERE vin = ?", ("1TESTVIN000000002",)
        ).fetchone()
        self.assertEqual(status, "not_paired")

    def test_paired_status_persisted_for_sold_vehicle_too(self):
        # Raw source fact, not a business exclusion -- sold vehicles
        # are still recorded here (build_sold_vehicles_report already
        # independently reads RecovR status for exactly this VIN for
        # its own report purposes).
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)
        (status,) = self.conn.execute(
            "SELECT recovr_status FROM vehicle WHERE vin = ?", ("1TESTVIN000090001",)
        ).fetchone()
        self.assertEqual(status, "paired")

    def test_short_fragment_resolves_via_unique_last6_match(self):
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)
        (status,) = self.conn.execute(
            "SELECT recovr_status FROM vehicle WHERE vin = ?", ("1TESTVIN000050001",)
        ).fetchone()
        self.assertEqual(status, "not_paired")

    def test_unknown_vin_is_skipped_not_created(self):
        import pandas as pd
        extra_row = pd.DataFrame([{"VIN": "1TESTVIN999999999", "Stock Number": "K99999",
                                    "Paired": "Yes", "Year": 2024, "Make": "Ghost", "Model": "Car"}])
        recovr_with_unknown = pd.concat([self.recovr_df, extra_row], ignore_index=True)
        persist_recovr_observations(recovr_with_unknown, db_conn=self.conn)
        row = self.conn.execute(
            "SELECT * FROM vehicle WHERE vin = ?", ("1TESTVIN999999999",)
        ).fetchone()
        self.assertIsNone(row, "RecovR alone must never create a new Vehicle row")

    def test_no_op_when_db_conn_omitted(self):
        persist_recovr_observations(self.recovr_df, db_conn=None)


class RapidReconWritePathTest(unittest.TestCase):
    """
    persist_rapidrecon_observations -- Event-only (no Vehicle status
    field), existing-Vehicle-only (never creates a new one). See
    tests/fixtures/synthetic/rapidrecon.csv: one VIN already known from
    Keyper/Tekion (1TESTVIN000000001), one that isn't
    (1TESTVIN999999999).
    """

    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = _load_inputs()
        self.rapidrecon_df = load_rapidrecon(os.path.join(FIXTURES, "rapidrecon.csv"))
        self.conn = connect(":memory:")
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)

    def test_event_written_for_known_vin(self):
        persist_rapidrecon_observations(self.rapidrecon_df, db_conn=self.conn)
        rows = self.conn.execute(
            "SELECT event_type, source, summary FROM event "
            "WHERE vin = ? AND source = 'rapidrecon'", ("1TESTVIN000000001",)
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "rapidrecon_observed")

    def test_no_vehicle_status_field_set_by_rapidrecon(self):
        # Assumption 1 from Sprint 2's kickoff: no new/derived status
        # field is set on Vehicle from RapidRecon data. inventory_state
        # is the only plausibly-relevant column and must stay untouched.
        persist_rapidrecon_observations(self.rapidrecon_df, db_conn=self.conn)
        (inventory_state,) = self.conn.execute(
            "SELECT inventory_state FROM vehicle WHERE vin = ?", ("1TESTVIN000000001",)
        ).fetchone()
        self.assertIsNone(inventory_state)

    def test_unknown_vin_is_skipped_not_created(self):
        persist_rapidrecon_observations(self.rapidrecon_df, db_conn=self.conn)
        row = self.conn.execute(
            "SELECT * FROM vehicle WHERE vin = ?", ("1TESTVIN999999999",)
        ).fetchone()
        self.assertIsNone(row, "RapidRecon alone must never create a new Vehicle row")
        event_row = self.conn.execute(
            "SELECT * FROM event WHERE vin = ?", ("1TESTVIN999999999",)
        ).fetchone()
        self.assertIsNone(event_row, "no Event should be written for an unresolvable VIN either")

    def test_no_op_when_db_conn_omitted(self):
        persist_rapidrecon_observations(self.rapidrecon_df, db_conn=None)


class CrossSourceIdentityTest(unittest.TestCase):
    """
    IMPLEMENTATION_PLAN.md's Technical Risks section, named explicitly:
    "a regression test explicitly asserts that the same VIN observed
    from two different sources in one run never creates two Vehicle
    rows." Runs the full realistic pipeline -- all five sources, one
    connection, one run -- the way main.py actually does it, not just
    each write path in isolation.

    1TESTVIN000000001 (K30001) is the strongest case in this fixture
    set: observed by Keyper (fully_verified), Tekion (master list), MDD
    (not-paired), AND RapidRecon (its fixture deliberately reuses this
    VIN) in a single run -- four sources, not two.
    """

    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = _load_inputs()
        self.mdd_df = load_mdd_not_paired(os.path.join(FIXTURES, "mdd_not_paired.csv"))
        self.recovr_df = load_recovr_full(os.path.join(FIXTURES, "recovr.csv"))
        self.rapidrecon_df = load_rapidrecon(os.path.join(FIXTURES, "rapidrecon.csv"))
        self.conn = connect(":memory:")

        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="test-run-1",
        )
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn)
        persist_mdd_observations(self.mdd_df, db_conn=self.conn)
        persist_recovr_observations(self.recovr_df, db_conn=self.conn)
        persist_rapidrecon_observations(self.rapidrecon_df, db_conn=self.conn)

    def test_vehicle_count_is_union_not_sum_across_all_five_sources(self):
        (count,) = self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
        self.assertEqual(count, 17, "union of all sources' VINs, not one row per source touch")

    def test_no_vin_ever_has_more_than_one_row(self):
        rows = self.conn.execute(
            "SELECT vin, COUNT(*) FROM vehicle GROUP BY vin HAVING COUNT(*) > 1"
        ).fetchall()
        self.assertEqual(rows, [], f"duplicate Vehicle rows found for: {rows}")

    def test_vin_touched_by_three_sources_merges_correctly_into_one_row(self):
        # 1TESTVIN000000001: Keyper (In), Tekion (Stocked In), MDD (not_paired).
        row = self.conn.execute(
            "SELECT keyper_status, tekion_status, mdd_status, recovr_status "
            "FROM vehicle WHERE vin = ?", ("1TESTVIN000000001",)
        ).fetchone()
        self.assertEqual(row, ("In", "Stocked In", "not_paired", None))

    def test_events_from_all_four_sources_preserved_for_shared_vin(self):
        # The merge above must not have dropped any source's Event --
        # partial upsert only touches Vehicle's current-state columns;
        # Event history is append-only and independent per source.
        sources = {row[0] for row in self.conn.execute(
            "SELECT source FROM event WHERE vin = ?", ("1TESTVIN000000001",)
        )}
        self.assertEqual(sources, {"keyper", "tekion", "mdd", "rapidrecon"})


if __name__ == "__main__":
    unittest.main()
