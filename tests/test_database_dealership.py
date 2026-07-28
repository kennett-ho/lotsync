"""
Phase 3, Sprint 1 verification -- Dealership repository primitives. See
DATA_MODEL.md's Dealership entry and
database/migrations/0006_employee_dealership.sql for the shape and the
reasoning behind upsert_dealership's explicit existence-check branching
(not a blind reuse of upsert_vehicle's single-statement form).
"""

import sqlite3
import unittest

from lotsync.database.repository import connect, upsert_dealership, get_dealership


class DealershipCreationTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def test_creating_without_name_raises(self):
        with self.assertRaises(ValueError):
            upsert_dealership(self.conn, "mark-kia", brand="Kia")

    def test_get_nonexistent_dealership_returns_none(self):
        self.assertIsNone(get_dealership(self.conn, "does-not-exist"))

    def test_create_with_name_only(self):
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia")
        row = get_dealership(self.conn, "mark-kia")
        self.assertEqual(row["dealership_id"], "mark-kia")
        self.assertEqual(row["name"], "Mark Kia")
        self.assertIsNone(row["brand"])

    def test_create_with_name_and_brand(self):
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia", brand="Kia")
        row = get_dealership(self.conn, "mark-kia")
        self.assertEqual(row["brand"], "Kia")

    def test_empty_fields_on_nonexistent_row_raises(self):
        # Mirrors the "cannot create without a name" guard -- an empty
        # fields dict has no name either.
        with self.assertRaises(ValueError):
            upsert_dealership(self.conn, "mark-kia")


class DealershipPartialUpdateTest(unittest.TestCase):
    """
    The behavior this sprint's own review names as the reason
    upsert_vehicle's single-statement shape could NOT be reused as-is:
    an update touching only one column must not require repeating
    `name`, and must not raise even though `name` is NOT NULL and is
    not part of this call's `fields`.
    """

    def setUp(self):
        self.conn = connect(":memory:")
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia")

    def test_update_brand_only_does_not_touch_name(self):
        upsert_dealership(self.conn, "mark-kia", brand="Kia")
        row = get_dealership(self.conn, "mark-kia")
        self.assertEqual(row["name"], "Mark Kia")
        self.assertEqual(row["brand"], "Kia")

    def test_update_name_only(self):
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia (renamed)")
        row = get_dealership(self.conn, "mark-kia")
        self.assertEqual(row["name"], "Mark Kia (renamed)")

    def test_empty_fields_on_existing_row_is_a_no_op(self):
        upsert_dealership(self.conn, "mark-kia", brand="Kia")
        upsert_dealership(self.conn, "mark-kia")
        row = get_dealership(self.conn, "mark-kia")
        self.assertEqual(row["name"], "Mark Kia")
        self.assertEqual(row["brand"], "Kia")

    def test_repeated_updates_from_independent_calls_accumulate(self):
        # Mirrors Vehicle's own multi-source-incremental-write pattern
        # (DATA_MODEL.md) -- two independent callers, each touching a
        # different column, must not clobber each other.
        upsert_dealership(self.conn, "mark-kia", brand="Kia")
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia")
        row = get_dealership(self.conn, "mark-kia")
        self.assertEqual(row["name"], "Mark Kia")
        self.assertEqual(row["brand"], "Kia")


if __name__ == "__main__":
    unittest.main()
