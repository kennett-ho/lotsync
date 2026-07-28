"""
Phase 3, Sprint 1 verification -- Employee repository primitives. See
DATA_MODEL.md's Employee entry and
database/migrations/0006_employee_dealership.sql for the shape, the
real FOREIGN KEY to Dealership, and the reasoning behind
upsert_employee's explicit existence-check branching (not a blind reuse
of upsert_vehicle's single-statement form).
"""

import sqlite3
import unittest

from lotsync.database.repository import (
    connect, upsert_employee, get_employee, upsert_dealership,
)


class EmployeeCreationTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def test_creating_without_name_raises(self):
        with self.assertRaises(ValueError):
            upsert_employee(self.conn, "emp-0142", role="Lot Attendant")

    def test_get_nonexistent_employee_returns_none(self):
        self.assertIsNone(get_employee(self.conn, "does-not-exist"))

    def test_create_with_name_only(self):
        upsert_employee(self.conn, "emp-0142", name="Marcus Torres")
        row = get_employee(self.conn, "emp-0142")
        self.assertEqual(row["employee_id"], "emp-0142")
        self.assertEqual(row["name"], "Marcus Torres")
        self.assertIsNone(row["role"])
        self.assertIsNone(row["department"])
        self.assertIsNone(row["dealership_id"])
        self.assertIsNone(row["status"])

    def test_create_with_all_fields(self):
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia")
        upsert_employee(
            self.conn, "emp-0142", name="Marcus Torres", role="Lot Attendant",
            department="Lot Operations", dealership_id="mark-kia", status="Available",
        )
        row = get_employee(self.conn, "emp-0142")
        self.assertEqual(row["role"], "Lot Attendant")
        self.assertEqual(row["department"], "Lot Operations")
        self.assertEqual(row["dealership_id"], "mark-kia")
        self.assertEqual(row["status"], "Available")


class EmployeePartialUpdateTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_employee(self.conn, "emp-0142", name="Marcus Torres", status="Available")

    def test_update_status_only_does_not_touch_name(self):
        upsert_employee(self.conn, "emp-0142", status="Installing")
        row = get_employee(self.conn, "emp-0142")
        self.assertEqual(row["name"], "Marcus Torres")
        self.assertEqual(row["status"], "Installing")

    def test_independent_calls_accumulate_like_vehicle(self):
        upsert_employee(self.conn, "emp-0142", role="Lot Attendant")
        upsert_employee(self.conn, "emp-0142", department="Lot Operations")
        row = get_employee(self.conn, "emp-0142")
        self.assertEqual(row["name"], "Marcus Torres")
        self.assertEqual(row["role"], "Lot Attendant")
        self.assertEqual(row["department"], "Lot Operations")
        self.assertEqual(row["status"], "Available")

    def test_empty_fields_on_existing_row_is_a_no_op(self):
        upsert_employee(self.conn, "emp-0142")
        row = get_employee(self.conn, "emp-0142")
        self.assertEqual(row["name"], "Marcus Torres")


class EmployeeDealershipRelationshipTest(unittest.TestCase):
    """
    DATA_MODEL.md: dealership_id is a "home/primary assignment, not a
    hard [business] constraint" -- real staff cross sister-store lines.
    That is distinct from referential integrity: a populated
    dealership_id must still name a real Dealership row. Confirmed here
    against a real, enforced FOREIGN KEY, not merely documented intent.
    """

    def setUp(self):
        self.conn = connect(":memory:")

    def test_employee_without_dealership_id_is_valid(self):
        # "Unassigned" home dealership is a real, valid state -- no
        # different in spirit from Task.assigned_employee_id's own
        # documented nullability.
        upsert_employee(self.conn, "emp-0142", name="Marcus Torres")
        row = get_employee(self.conn, "emp-0142")
        self.assertIsNone(row["dealership_id"])

    def test_dealership_id_referencing_unknown_dealership_raises(self):
        with self.assertRaises(sqlite3.IntegrityError):
            upsert_employee(self.conn, "emp-0142", name="Marcus Torres", dealership_id="does-not-exist")

    def test_dealership_id_referencing_real_dealership_succeeds(self):
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia")
        upsert_employee(self.conn, "emp-0142", name="Marcus Torres", dealership_id="mark-kia")
        row = get_employee(self.conn, "emp-0142")
        self.assertEqual(row["dealership_id"], "mark-kia")

    def test_employee_can_cross_sister_store_lines(self):
        # Real Keyper data already shows staff working across sister
        # stores (ARCHITECTURE.md, models/employee.py) -- home
        # dealership_id changing later is a normal update, not a
        # constraint violation.
        upsert_dealership(self.conn, "mark-kia", name="Mark Kia")
        upsert_dealership(self.conn, "mark-mazda", name="Mark Mazda")
        upsert_employee(self.conn, "emp-0142", name="Marcus Torres", dealership_id="mark-kia")
        upsert_employee(self.conn, "emp-0142", dealership_id="mark-mazda")
        row = get_employee(self.conn, "emp-0142")
        self.assertEqual(row["dealership_id"], "mark-mazda")


if __name__ == "__main__":
    unittest.main()
