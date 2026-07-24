"""
Unit tests for rules/inventory.py -- business classification of what
KIND of vehicle a stock number represents.
"""

import unittest

from lotsync.rules.inventory import is_new_car_stock, is_damaged_repair_stock


class TestIsNewCarStock(unittest.TestCase):
    def test_bare_k_plus_digits_is_new_car(self):
        self.assertTrue(is_new_car_stock("K30707"))
        self.assertTrue(is_new_car_stock("k30707"))  # case-insensitive

    def test_letter_prefix_variants_are_not_new_car(self):
        self.assertFalse(is_new_car_stock("KB1641"))
        self.assertFalse(is_new_car_stock("KT3514"))
        self.assertFalse(is_new_car_stock("KP12185"))

    def test_k_plus_digits_plus_suffix_is_not_new_car(self):
        # This is the exact ambiguity that prompted this function:
        # K22848SL and K30707A both start with a bare "K" + digits,
        # but the trailing letters mean they're trades, not new-car
        # orders.
        self.assertFalse(is_new_car_stock("K22848SL"))
        self.assertFalse(is_new_car_stock("K30707A"))

    def test_damaged_repair_suffix_is_not_new_car(self):
        self.assertFalse(is_new_car_stock("K30707DM"))


class TestIsDamagedRepairStock(unittest.TestCase):
    def test_dm_suffix_is_damaged(self):
        self.assertTrue(is_damaged_repair_stock("K30707DM"))
        self.assertTrue(is_damaged_repair_stock("k30707dm"))  # case-insensitive

    def test_bare_new_car_is_not_damaged(self):
        self.assertFalse(is_damaged_repair_stock("K30707"))

    def test_trade_suffix_is_not_damaged(self):
        self.assertFalse(is_damaged_repair_stock("K22848SL"))

    def test_dm_not_at_end_is_not_damaged(self):
        # Guards against a false positive if "DM" ever appears as part
        # of a longer, unrelated suffix rather than the actual marker.
        self.assertFalse(is_damaged_repair_stock("K30707DMX"))


if __name__ == "__main__":
    unittest.main()
