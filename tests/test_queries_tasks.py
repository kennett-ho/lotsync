"""
Phase 3, Sprint 2 verification -- queries/tasks.py.
"""

import unittest

from lotsync.database.repository import connect, upsert_vehicle, insert_task, cancel_task
from lotsync.queries.tasks import list_tasks


class ListTasksTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", display_name="2023 Honda Accord",
                        year=2023, make="Honda", model="Accord")
        upsert_vehicle(self.conn, "VIN2", stock_number="B93021", display_name="2022 Ford F-150",
                        year=2022, make="Ford", model="F-150")
        self.conn.commit()

    def test_empty_dataset_returns_empty_list(self):
        self.assertEqual(list_tasks(self.conn), [])

    def test_returns_a_task_with_embedded_vehicle_summary(self):
        insert_task(self.conn, "VIN1", "install_recovr_device", department="Inventory", priority="High")
        self.conn.commit()

        tasks = list_tasks(self.conn)
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        self.assertEqual(task["vin"], "VIN1")
        self.assertEqual(task["task_type"], "install_recovr_device")
        self.assertEqual(task["commitment_standing"], "outstanding")
        self.assertEqual(task["execution_status"], "not_started")
        self.assertEqual(task["vehicle"], {
            "vin": "VIN1", "stock_number": "A48291", "display_name": "2023 Honda Accord",
            "year": 2023, "make": "Honda", "model": "Accord",
        })
        # Vehicle summary fields must not leak as top-level Task fields.
        self.assertNotIn("stock_number", task)
        self.assertNotIn("make", task)

    def test_ordered_newest_first(self):
        first_id = insert_task(self.conn, "VIN1", "install_recovr_device")
        second_id = insert_task(self.conn, "VIN2", "install_mdd_beacon")
        self.conn.commit()
        tasks = list_tasks(self.conn)
        self.assertEqual([t["task_id"] for t in tasks], [second_id, first_id])

    def test_vin_filter_scopes_to_one_vehicle(self):
        insert_task(self.conn, "VIN1", "install_recovr_device")
        insert_task(self.conn, "VIN2", "install_mdd_beacon")
        self.conn.commit()

        tasks = list_tasks(self.conn, vin="VIN1")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["vin"], "VIN1")

    def test_department_filter(self):
        insert_task(self.conn, "VIN1", "install_recovr_device", department="Inventory")
        insert_task(self.conn, "VIN2", "install_mdd_beacon", department="Lot Ops")
        self.conn.commit()

        tasks = list_tasks(self.conn, department="Inventory")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["department"], "Inventory")

    def test_commitment_standing_filter_excludes_discharged_tasks(self):
        task_id = insert_task(self.conn, "VIN1", "install_recovr_device")
        self.conn.commit()
        cancel_task(self.conn, task_id, ratified_by="emp1")
        self.conn.commit()

        outstanding = list_tasks(self.conn, commitment_standing="outstanding")
        cancelled = list_tasks(self.conn, commitment_standing="cancelled")
        self.assertEqual(outstanding, [])
        self.assertEqual(len(cancelled), 1)

    def test_assigned_employee_id_filter(self):
        insert_task(self.conn, "VIN1", "install_recovr_device")
        self.conn.commit()
        self.conn.execute("UPDATE task SET assigned_employee_id = 'emp-1' WHERE vin = 'VIN1'")
        self.conn.commit()

        tasks = list_tasks(self.conn, assigned_employee_id="emp-1")
        self.assertEqual(len(tasks), 1)
        tasks_other = list_tasks(self.conn, assigned_employee_id="emp-2")
        self.assertEqual(tasks_other, [])

    def test_filters_combine_with_and(self):
        insert_task(self.conn, "VIN1", "install_recovr_device", department="Inventory", priority="High")
        insert_task(self.conn, "VIN1", "install_mdd_beacon", department="Inventory", priority="Low")
        self.conn.commit()

        tasks = list_tasks(self.conn, department="Inventory", priority="High")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["task_type"], "install_recovr_device")


if __name__ == "__main__":
    unittest.main()
