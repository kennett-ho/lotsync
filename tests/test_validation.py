"""
Unit tests for rules/validation.py using small inline dataframes rather
than the full fixture set -- these are narrow, mechanical checks of
find_tekion_sync_conflicts, not full-pipeline scenarios.
"""

import unittest
import pandas as pd

from lotsync.rules.validation import find_tekion_sync_conflicts


class TestFindTekionSyncConflicts(unittest.TestCase):
    def test_sold_and_still_stocked_in_flagged(self):
        sold = pd.DataFrame([{"Stock #": "K1OLD", "VIN #": "VIN0000000000001", "Sold Date": "Jan 1 2026"}])
        master = pd.DataFrame([{"Stock #": "K1NEW", "VIN #": "VIN0000000000001", "Stocked In Date": "Feb 1 2026"}])
        result = find_tekion_sync_conflicts(master, sold)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["conflict_type"], "sold_but_still_stocked_in")

    def test_first_occurrence_preserved_for_duplicate_vin_in_both_sets(self):
        # Regression guard: a naive dict comprehension keeps the LAST
        # matching row for a duplicate key; this must keep the FIRST,
        # matching the original .iloc[0] behavior.
        sold = pd.DataFrame([
            {"Stock #": "FIRST", "VIN #": "VIN0000000000002", "Sold Date": "Jan 1 2026"},
            {"Stock #": "SECOND", "VIN #": "VIN0000000000002", "Sold Date": "Jan 2 2026"},
        ])
        master = pd.DataFrame([{"Stock #": "K2", "VIN #": "VIN0000000000002", "Stocked In Date": "Feb 1 2026"}])
        result = find_tekion_sync_conflicts(master, sold)
        conflict = result[result["conflict_type"] == "sold_but_still_stocked_in"].iloc[0]
        self.assertEqual(conflict["sold_stock"], "FIRST")

    def test_no_overlap_produces_no_conflicts(self):
        sold = pd.DataFrame([{"Stock #": "K1", "VIN #": "AAA", "Sold Date": "Jan 1 2026"}])
        master = pd.DataFrame([{"Stock #": "K2", "VIN #": "BBB", "Stocked In Date": "Feb 1 2026"}])
        result = find_tekion_sync_conflicts(master, sold)
        self.assertEqual(len(result), 0)

    def test_deterministic_across_repeated_calls(self):
        # Regression guard for the hash-randomization row-order bug
        # found during the Phase 1 module split -- running this twice
        # with multiple overlapping VINs must produce identical order.
        sold = pd.DataFrame([
            {"Stock #": f"K{i}OLD", "VIN #": f"VIN{i:014d}", "Sold Date": "Jan 1 2026"}
            for i in range(10)
        ])
        master = pd.DataFrame([
            {"Stock #": f"K{i}NEW", "VIN #": f"VIN{i:014d}", "Stocked In Date": "Feb 1 2026"}
            for i in range(10)
        ])
        result_a = find_tekion_sync_conflicts(master, sold)
        result_b = find_tekion_sync_conflicts(master, sold)
        self.assertEqual(list(result_a["vin"]), list(result_b["vin"]))
        self.assertEqual(list(result_a["vin"]), sorted(result_a["vin"]))


if __name__ == "__main__":
    unittest.main()
