"""
Unit tests for sync/reconciler.py's build_sold_vehicles_report, using
small inline dataframes -- focused specifically on the RecovR
duplicate-VIN correctness fix, not full-pipeline scenarios (see
test_regression.py for those).
"""

import unittest
import pandas as pd

from lotsync.sync.reconciler import build_sold_vehicles_report


def _empty_keyper():
    return pd.DataFrame(columns=["identifier_type", "identifier_value"])


class TestBuildSoldVehiclesReport(unittest.TestCase):
    def test_duplicate_recovr_vin_prefers_paired_yes_regardless_of_row_order(self):
        sold = pd.DataFrame([{"Stock #": "K1", "VIN #": "VIN0000000000001",
                               "Sold Date": "Jan 1 2026", "Year Make Model": "2024 Test"}])
        # Paired=No appears BEFORE Paired=Yes for the same VIN -- a
        # naive last-occurrence-wins dict would still get this one
        # right by luck; the real test is the reversed order below.
        recovr = pd.DataFrame([
            {"VIN": "VIN0000000000001", "Paired": "No"},
            {"VIN": "VIN0000000000001", "Paired": "Yes"},
        ])
        result = build_sold_vehicles_report(sold, _empty_keyper(), recovr)
        self.assertEqual(result.iloc[0]["recovr_status"], "still_paired")
        self.assertEqual(result.iloc[0]["overall_status"], "needs_removal")

    def test_duplicate_recovr_vin_yes_first_then_no_still_resolves_to_paired(self):
        # This is the order that would break a naive last-occurrence
        # dict -- Yes comes first, No comes second, and the correct
        # answer is still "still_paired" since at least one row says so.
        sold = pd.DataFrame([{"Stock #": "K1", "VIN #": "VIN0000000000001",
                               "Sold Date": "Jan 1 2026", "Year Make Model": "2024 Test"}])
        recovr = pd.DataFrame([
            {"VIN": "VIN0000000000001", "Paired": "Yes"},
            {"VIN": "VIN0000000000001", "Paired": "No"},
        ])
        result = build_sold_vehicles_report(sold, _empty_keyper(), recovr)
        self.assertEqual(result.iloc[0]["recovr_status"], "still_paired")

    def test_no_recovr_record_at_all_is_not_found(self):
        sold = pd.DataFrame([{"Stock #": "K1", "VIN #": "VIN0000000000009",
                               "Sold Date": "Jan 1 2026", "Year Make Model": "2024 Test"}])
        recovr = pd.DataFrame(columns=["VIN", "Paired"])
        result = build_sold_vehicles_report(sold, _empty_keyper(), recovr)
        self.assertEqual(result.iloc[0]["recovr_status"], "not_found")
        self.assertEqual(result.iloc[0]["overall_status"], "sale_complete")


if __name__ == "__main__":
    unittest.main()
