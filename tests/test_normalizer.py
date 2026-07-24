"""
Unit tests for sync/normalizer.py -- pure functions, no I/O, no
fixtures needed. These pin down the identifier-classification rules
that took several rounds of real-data debugging to get right (see
ARCHITECTURE.md): Keyper has no VIN column, Tekion's Stock # sometimes
IS a VIN fragment, and Tekion occasionally assigns short numeric
placeholder stock numbers.
"""

import unittest

from lotsync.sync.normalizer import (
    last6, stock_prefix, classify_keyper_identifier, classify_tekion_stock,
)


class TestLast6(unittest.TestCase):
    def test_normal_vin(self):
        self.assertEqual(last6("AAAAAAAAAAA234567"), "234567")

    def test_exact_length_six(self):
        self.assertEqual(last6("123456"), "123456")

    def test_shorter_than_six_returned_as_is(self):
        self.assertEqual(last6("123"), "123")


class TestStockPrefix(unittest.TestCase):
    def test_simple_prefix(self):
        self.assertEqual(stock_prefix("K1001"), "K")

    def test_multi_letter_prefix(self):
        self.assertEqual(stock_prefix("KB1234A"), "KB")

    def test_no_letters_returns_empty(self):
        self.assertEqual(stock_prefix("123456"), "")

    def test_lowercase_normalized_to_upper(self):
        self.assertEqual(stock_prefix("k1001"), "K")


class TestClassifyKeyperIdentifier(unittest.TestCase):
    def test_non_vehicle_key(self):
        self.assertEqual(classify_keyper_identifier("GOLF CART"), ("non_vehicle", None))

    def test_six_digit_numeric_is_last6_vin(self):
        self.assertEqual(classify_keyper_identifier("123456"), ("last6_vin", "123456"))

    def test_three_digit_numeric_is_placeholder(self):
        self.assertEqual(
            classify_keyper_identifier("797"),
            ("tekion_auto_generated_stock_number", "797"),
        )

    def test_letter_prefixed_is_stock_number_and_uppercased(self):
        self.assertEqual(classify_keyper_identifier("k22848sl"), ("stock_number", "K22848SL"))

    def test_unrecognized_format(self):
        itype, _ = classify_keyper_identifier("!!!weird!!!")
        self.assertEqual(itype, "unrecognized")


class TestClassifyTekionStock(unittest.TestCase):
    def test_letter_prefixed_stock_number(self):
        self.assertEqual(
            classify_tekion_stock("K30707", "AAAAAAAAAAA234567"),
            ("stock_number", "K30707"),
        )

    def test_numeric_stock_matching_vin_last6_is_last6_type(self):
        # Real regression case: Tekion sometimes uses the VIN's last 6
        # digits directly as the stock number, no letter prefix.
        self.assertEqual(
            classify_tekion_stock("123456", "AAAAAAAAAAA123456"),
            ("last6_vin", "123456"),
        )

    def test_numeric_stock_not_matching_vin_is_placeholder(self):
        # Real regression case: confirmed against actual Tekion auto-
        # generated placeholders (784, 797, 802) that don't correspond
        # to the VIN at all.
        self.assertEqual(
            classify_tekion_stock("94", "1HGCR2F55FA201205"),
            ("tekion_auto_generated_stock_number", "94"),
        )


if __name__ == "__main__":
    unittest.main()
