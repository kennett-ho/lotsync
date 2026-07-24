"""
End-to-end regression test for the full reconciliation pipeline,
using synthetic fixtures (tests/fixtures/synthetic/) rather than real
dealership exports -- see the fixture files' generation notes for why
real customer data isn't checked in here.

This replaces the manual "run old script, run new package, diff every
CSV" verification performed by hand during the Phase 1 module split.
Run this any time reconciliation logic changes -- if these assertions
still pass, the specific behaviors they check are unchanged.

WHAT THIS DOES NOT COVER: this fixture set is small and hand-crafted
to exercise known edge cases. It is not a substitute for occasionally
re-running the full pipeline against real, current dealership exports
and spot-checking the results -- that's still worth doing periodically,
just not as an automated, committed test (see fixtures notes).
"""

import os
import unittest

from lotsync.config.settings import (
    load_settings, load_day_out_buckets, load_incoming_missing_buckets,
    load_new_car_buckets, load_internal_fleet_vins,
)
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.importers.mdd import load_mdd_not_paired
from lotsync.importers.recovr import load_recovr_full
from lotsync.sync.reconciler import (
    reconcile_keyper_tekion, build_incoming_or_missing_investigate,
    build_sold_vehicles_report, build_tracker_install_tasks,
)
from lotsync.rules.validation import find_tekion_sync_conflicts

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")


class ReconciliationRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings = load_settings(CONFIG)
        day_out_buckets = load_day_out_buckets(CONFIG)
        incoming_missing_buckets = load_incoming_missing_buckets(CONFIG)
        new_car_buckets = load_new_car_buckets(CONFIG)
        internal_fleet_vins = load_internal_fleet_vins(CONFIG)

        cls.keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
        cls.tekion_df = load_tekion(internal_fleet_vins, os.path.join(FIXTURES, "tekion_master.csv"))
        cls.sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
        cls.mdd_df = load_mdd_not_paired(os.path.join(FIXTURES, "mdd_not_paired.csv"))
        cls.recovr_df = load_recovr_full(os.path.join(FIXTURES, "recovr.csv"))

        (cls.fully_verified, cls.key_out_aging, cls.flag_to_controller,
         cls.exceptions, cls.matched_idx) = reconcile_keyper_tekion(
            cls.keyper_df, cls.tekion_df, cls.sold_df,
            settings["sync_date"], day_out_buckets)

        cls.incoming_or_missing = build_incoming_or_missing_investigate(
            cls.tekion_df, cls.matched_idx, settings["sync_date"],
            incoming_missing_buckets, new_car_buckets)
        cls.sold_report = build_sold_vehicles_report(cls.sold_df, cls.keyper_df, cls.recovr_df)
        cls.tracker_tasks = build_tracker_install_tasks(
            cls.tekion_df, cls.sold_df, cls.mdd_df, cls.recovr_df, settings["store_name"])
        cls.sync_conflicts = find_tekion_sync_conflicts(cls.tekion_df, cls.sold_df)

    def _lookup(self, df, key_col, key_val):
        rows = df[df[key_col] == key_val]
        self.assertEqual(len(rows), 1, f"expected exactly one row with {key_col}={key_val!r}")
        return rows.iloc[0]

    # --- fully_verified ---

    def test_in_key_matched_by_stock_number_is_fully_verified(self):
        self._lookup(self.fully_verified, "keyper_identifier", "K30001")

    def test_in_key_matched_via_last6_vin_is_fully_verified(self):
        row = self._lookup(self.fully_verified, "keyper_identifier", "099999")
        self.assertEqual(row["tekion_stock"], "K40001")

    def test_wrong_keyper_system_tag_still_matches_via_prefix(self):
        # Regression guard for the "System field isn't a reliable store
        # indicator" fix -- K30099 is tagged Mitsu-SVC in the fixture
        # but must still resolve against the Kia-prefixed Tekion set.
        self._lookup(self.fully_verified, "keyper_identifier", "K30099")

    # --- key_out_aging ---

    def test_key_out_short_duration_buckets_correctly(self):
        row = self._lookup(self.key_out_aging, "keyper_identifier", "K30002")
        self.assertEqual(row["aging_bucket"], "Should be here")

    def test_key_out_long_duration_buckets_as_likely_sold(self):
        row = self._lookup(self.key_out_aging, "keyper_identifier", "K30003")
        self.assertEqual(row["aging_bucket"], "Likely Sold, Verify to Remove from OMS")

    # --- flag_to_controller ---

    def test_sold_vehicle_key_not_removed_is_flagged_distinctly(self):
        # Not just "pending_dms_entry" -- this must resolve to the more
        # urgent, distinct reason.
        row = self._lookup(self.flag_to_controller, "keyper_identifier", "K30005")
        self.assertEqual(row["reason"], "sold_key_not_removed_from_keyper")

    def test_genuinely_unmatched_in_key_is_pending_dms_entry(self):
        row = self._lookup(self.flag_to_controller, "keyper_identifier", "K30006")
        self.assertEqual(row["reason"], "pending_dms_entry")

    def test_unmatched_out_key_gets_distinct_reason(self):
        row = self._lookup(self.flag_to_controller, "keyper_identifier", "K30007")
        self.assertEqual(row["reason"], "out_and_unmatched_no_tekion_record")

    # --- exceptions ---

    def test_auto_generated_placeholder_is_an_exception_not_a_match_attempt(self):
        row = self._lookup(self.exceptions, "keyper_identifier", "784")
        self.assertEqual(row["reason"], "tekion_auto_generated_stock_number")

    def test_unrecognized_format_is_an_exception(self):
        row = self._lookup(self.exceptions, "keyper_identifier", "#ODD1")
        self.assertEqual(row["reason"], "unrecognized")

    def test_ambiguous_last6_match_is_flagged_not_silently_guessed(self):
        row = self._lookup(self.exceptions, "keyper_identifier", "555555")
        self.assertEqual(row["reason"], "ambiguous_last6_vin_multiple_matches")

    # --- out of scope / filtered entirely ---

    def test_out_of_scope_store_prefix_appears_nowhere(self):
        for df in (self.fully_verified, self.key_out_aging,
                   self.flag_to_controller, self.exceptions):
            self.assertNotIn("ZZ00001", df["keyper_identifier"].values)

    def test_non_vehicle_key_appears_nowhere(self):
        for df in (self.fully_verified, self.key_out_aging,
                   self.flag_to_controller, self.exceptions):
            self.assertNotIn("GOLF CART", df["keyper_identifier"].values)

    # --- incoming_or_missing_investigate ---

    def test_bare_k_stock_classified_as_new_car(self):
        row = self._lookup(self.incoming_or_missing, "tekion_stock", "K50001")
        self.assertEqual(row["vehicle_type"], "New Car (Awaiting Dropoff)")
        self.assertEqual(row["priority"], "Awaiting Transport Dropoff")

    def test_new_car_past_window_is_investigate(self):
        row = self._lookup(self.incoming_or_missing, "tekion_stock", "K50002")
        self.assertEqual(row["priority"], "Investigate")

    def test_dm_suffix_classified_as_damaged_no_priority_bucket(self):
        row = self._lookup(self.incoming_or_missing, "tekion_stock", "K50003DM")
        self.assertEqual(row["vehicle_type"], "New (Damaged - In Repair)")
        self.assertEqual(row["priority"], "not yet timed - no repair-duration baseline set")

    def test_suffixed_stock_classified_as_trade_not_new_car(self):
        row = self._lookup(self.incoming_or_missing, "tekion_stock", "K50004A")
        self.assertEqual(row["vehicle_type"], "Trade/Other")
        self.assertEqual(row["priority"], "Within Normal Turnaround")

    def test_trade_past_window_is_overdue(self):
        row = self._lookup(self.incoming_or_missing, "tekion_stock", "K50005SL")
        self.assertIn("Overdue", row["priority"])

    def test_internal_fleet_vehicle_excluded_from_incoming_report(self):
        self.assertNotIn("K50006A", self.incoming_or_missing["tekion_stock"].values)

    def test_ambiguous_match_leaves_both_tekion_candidates_unmatched(self):
        # Since 555555 couldn't confidently resolve to either K60001 or
        # K60002, NEITHER should be marked as matched -- both should
        # still show up here as genuinely keyless.
        for stock in ("K60001", "K60002"):
            self._lookup(self.incoming_or_missing, "tekion_stock", stock)

    # --- sold_vehicles_report ---

    def test_sold_vehicle_with_active_key_needs_removal(self):
        row = self._lookup(self.sold_report, "stock", "K30005")
        self.assertEqual(row["overall_status"], "needs_removal")
        self.assertTrue(row["keyper_still_present"])

    def test_sold_vehicle_still_paired_in_recovr_needs_removal(self):
        row = self._lookup(self.sold_report, "stock", "K90001")
        self.assertEqual(row["overall_status"], "needs_removal")
        self.assertEqual(row["recovr_status"], "still_paired")

    def test_sold_vehicle_fully_clean_is_sale_complete(self):
        row = self._lookup(self.sold_report, "stock", "K80001")
        self.assertEqual(row["overall_status"], "sale_complete")

    # --- tracker_install_tasks ---

    def test_active_vehicle_missing_mdd_gets_install_task(self):
        tasks = self.tracker_tasks[self.tracker_tasks["stock"] == "K30001"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks.iloc[0]["source"], "MDD")

    def test_sold_vehicle_missing_mdd_is_excluded_from_install_tasks(self):
        # K30005 is sold -- must not generate an install task even
        # though it's in the MDD "not paired" export.
        self.assertNotIn("K30005", self.tracker_tasks["stock"].values)

    def test_active_vehicle_missing_recovr_gets_install_task(self):
        tasks = self.tracker_tasks[
            (self.tracker_tasks["source"] == "RecovR") &
            (self.tracker_tasks["vin"].str.endswith("000000002"))
        ]
        self.assertEqual(len(tasks), 1)

    def test_recovr_short_vin_fragment_resolves_via_last6_match(self):
        tasks = self.tracker_tasks[
            (self.tracker_tasks["source"] == "RecovR") &
            (self.tracker_tasks["vin"].str.endswith("000050001"))
        ]
        self.assertEqual(len(tasks), 1)

    # --- tekion_sync_conflicts ---

    def test_vin_sold_and_still_stocked_in_is_flagged(self):
        conflicts = self.sync_conflicts[self.sync_conflicts["conflict_type"] == "sold_but_still_stocked_in"]
        self.assertTrue(conflicts["vin"].str.endswith("000000007").any())

    def test_duplicate_sold_vin_is_flagged(self):
        conflicts = self.sync_conflicts[self.sync_conflicts["conflict_type"] == "duplicate_sold_vin"]
        self.assertTrue(conflicts["vin"].str.endswith("000080001").any())


if __name__ == "__main__":
    unittest.main()
