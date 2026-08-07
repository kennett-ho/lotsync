"""
Phase 3, Sprint 2 verification -- the FastAPI layer (api/app.py,
api/routers/*). Uses FastAPI's own TestClient, overriding get_db with
an in-memory connection the same way every other test already uses
connect(":memory:") directly -- see api/dependencies.py. This is the
first test file in this project needing a dependency beyond the
standard library (fastapi's own test utilities); see api/README.md's
"Testing" section for why that's a deliberate, narrow exception to
tests/README.md's "no external dependencies" note, not an abandonment
of it -- every query-layer/DTO-level test remains plain unittest.
"""

import unittest

from fastapi.testclient import TestClient

from lotsync.api.app import app
from lotsync.api.dependencies import get_db
from lotsync.database.repository import (
    connect, upsert_vehicle, insert_task, insert_recommendation, insert_event,
    sync_run, cancel_task, dismiss_recommendation,
)


class ApiTestCase(unittest.TestCase):
    """Shared setup: one in-memory DB per test, wired into the app via dependency override."""

    def setUp(self):
        self.conn = connect(":memory:")

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.conn.close()


class DashboardEndpointTest(ApiTestCase):
    def test_empty_dataset_returns_valid_zeroed_shape(self):
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["connected_systems"], {})
        self.assertEqual(body["task_counts_by_department"], {})
        self.assertEqual(
            body["inventory_health"],
            {"healthy_vehicles": 0, "total_vehicles": 0, "health_percentage": None},
        )
        self.assertEqual(body["recent_activity"], [])

    def test_composes_all_four_underlying_queries(self):
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291")
        self.conn.commit()
        insert_task(self.conn, "VIN1", "install_recovr_device", department="Inventory")
        insert_event(self.conn, "VIN1", "keys_checked_out", "keyper", summary="Keys checked out")
        self.conn.commit()
        with sync_run(self.conn, "recovr", records_processed=1):
            pass

        body = self.client.get("/dashboard").json()
        self.assertIn("recovr", body["connected_systems"])
        self.assertEqual(body["task_counts_by_department"], {"Inventory": 1})
        self.assertEqual(body["inventory_health"]["total_vehicles"], 1)
        self.assertEqual(len(body["recent_activity"]), 1)
        self.assertEqual(body["recent_activity"][0]["vehicle"]["vin"], "VIN1")


class VehiclesEndpointTest(ApiTestCase):
    def test_empty_dataset_returns_empty_list(self):
        resp = self.client.get("/vehicles")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_returns_vehicle_dto_shaped_rows(self):
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", year=2023, make="Honda", model="Accord")
        self.conn.commit()
        body = self.client.get("/vehicles").json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["vin"], "VIN1")
        self.assertEqual(body[0]["stock_number"], "A48291")
        self.assertEqual(body[0]["open_task_count"], 0)

    def test_default_excludes_sold_vehicles(self):
        upsert_vehicle(self.conn, "VIN1", tekion_status="Stocked In")
        upsert_vehicle(self.conn, "VIN2", tekion_status="Sold")
        self.conn.commit()
        body = self.client.get("/vehicles").json()
        self.assertEqual([v["vin"] for v in body], ["VIN1"])

    def test_include_sold_query_param_returns_full_roster(self):
        upsert_vehicle(self.conn, "VIN1", tekion_status="Stocked In")
        upsert_vehicle(self.conn, "VIN2", tekion_status="Sold")
        self.conn.commit()
        body = self.client.get("/vehicles?include_sold=true").json()
        self.assertEqual(sorted(v["vin"] for v in body), ["VIN1", "VIN2"])


class VehicleDetailEndpointTest(ApiTestCase):
    def test_missing_vehicle_returns_404(self):
        resp = self.client.get("/vehicles/NO-SUCH-VIN")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("NO-SUCH-VIN", resp.json()["detail"])

    def test_full_aggregation_matches_reference_implementation(self):
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", year=2023, make="Honda", model="Accord")
        self.conn.commit()
        insert_task(self.conn, "VIN1", "install_recovr_device")
        insert_recommendation(self.conn, "VIN1", "High", "RecovR missing", "42 days", "recovr_missing")
        insert_event(self.conn, "VIN1", "keys_checked_out", "keyper", summary="Keys checked out")
        self.conn.commit()
        with sync_run(self.conn, "recovr", records_processed=1):
            pass

        resp = self.client.get("/vehicles/VIN1")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["vin"], "VIN1")
        self.assertEqual(len(body["tasks"]), 1)
        self.assertEqual(len(body["recommendations"]), 1)
        self.assertEqual(len(body["timeline"]), 1)
        self.assertIn("recovr", body["connected_systems"])

    def test_a_second_vehicles_data_never_leaks_in(self):
        upsert_vehicle(self.conn, "VIN1")
        upsert_vehicle(self.conn, "VIN2")
        self.conn.commit()
        insert_task(self.conn, "VIN1", "install_recovr_device")
        insert_task(self.conn, "VIN2", "install_mdd_beacon")
        self.conn.commit()

        body = self.client.get("/vehicles/VIN1").json()
        self.assertEqual(len(body["tasks"]), 1)
        self.assertEqual(body["tasks"][0]["vin"], "VIN1")

    def test_nested_task_recommendation_and_timeline_omit_redundant_vehicle_field(self):
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291")
        self.conn.commit()
        insert_task(self.conn, "VIN1", "install_recovr_device")
        insert_recommendation(self.conn, "VIN1", "High", "t", "d", "rule_a")
        insert_event(self.conn, "VIN1", "keys_checked_out", "keyper", summary="s")
        self.conn.commit()

        body = self.client.get("/vehicles/VIN1").json()
        self.assertIsNone(body["tasks"][0]["vehicle"])
        self.assertIsNone(body["recommendations"][0]["vehicle"])
        self.assertIsNone(body["timeline"][0]["vehicle"])


class TasksEndpointTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", display_name="2023 Honda Accord",
                        year=2023, make="Honda", model="Accord")
        upsert_vehicle(self.conn, "VIN2", stock_number="B93021")
        self.conn.commit()

    def test_empty_dataset_returns_empty_list(self):
        self.assertEqual(self.client.get("/tasks").json(), [])

    def test_returns_task_with_embedded_vehicle_summary_and_both_status_axes(self):
        insert_task(self.conn, "VIN1", "install_recovr_device", department="Inventory", priority="High")
        self.conn.commit()

        body = self.client.get("/tasks").json()
        self.assertEqual(len(body), 1)
        # Both axes present and independent -- never collapsed into one field.
        self.assertEqual(body[0]["commitment_standing"], "outstanding")
        self.assertEqual(body[0]["execution_status"], "not_started")
        self.assertEqual(body[0]["vehicle"], {
            "vin": "VIN1", "stock_number": "A48291", "display_name": "2023 Honda Accord",
            "year": 2023, "make": "Honda", "model": "Accord",
        })

    def test_department_query_param_filters(self):
        insert_task(self.conn, "VIN1", "install_recovr_device", department="Inventory")
        insert_task(self.conn, "VIN2", "install_mdd_beacon", department="Lot Ops")
        self.conn.commit()

        body = self.client.get("/tasks", params={"department": "Inventory"}).json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["department"], "Inventory")

    def test_commitment_standing_query_param_filters_discharged_tasks(self):
        task_id = insert_task(self.conn, "VIN1", "install_recovr_device")
        self.conn.commit()
        cancel_task(self.conn, task_id, ratified_by="emp1")
        self.conn.commit()

        outstanding = self.client.get("/tasks", params={"commitment_standing": "outstanding"}).json()
        cancelled = self.client.get("/tasks", params={"commitment_standing": "cancelled"}).json()
        self.assertEqual(outstanding, [])
        self.assertEqual(len(cancelled), 1)


class RecommendationsEndpointTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291")
        self.conn.commit()

    def test_empty_dataset_returns_empty_list(self):
        self.assertEqual(self.client.get("/recommendations").json(), [])

    def test_returns_recommendation_with_embedded_vehicle_summary(self):
        insert_recommendation(self.conn, "VIN1", "High", "RecovR missing", "42 days", "recovr_missing")
        self.conn.commit()

        body = self.client.get("/recommendations").json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["status"], "open")
        self.assertEqual(body[0]["vehicle"]["vin"], "VIN1")

    def test_status_query_param_filters(self):
        rec_id = insert_recommendation(self.conn, "VIN1", "High", "t", "d", "rule_a")
        self.conn.commit()
        dismiss_recommendation(self.conn, rec_id)
        self.conn.commit()

        open_recs = self.client.get("/recommendations", params={"status": "open"}).json()
        dismissed_recs = self.client.get("/recommendations", params={"status": "dismissed"}).json()
        self.assertEqual(open_recs, [])
        self.assertEqual(len(dismissed_recs), 1)


class ActivityEndpointTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", year=2023, make="Honda", model="Accord")
        self.conn.commit()

    def test_empty_dataset_returns_empty_list(self):
        self.assertEqual(self.client.get("/activity").json(), [])

    def test_returns_activity_with_embedded_vehicle_summary(self):
        insert_event(self.conn, "VIN1", "keys_checked_out", "keyper", summary="Keys checked out by Sales")
        self.conn.commit()

        body = self.client.get("/activity").json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["summary"], "Keys checked out by Sales")
        self.assertEqual(body[0]["vehicle"]["vin"], "VIN1")

    def test_vin_query_param_filters(self):
        upsert_vehicle(self.conn, "VIN2")
        self.conn.commit()
        insert_event(self.conn, "VIN1", "keys_checked_out", "keyper")
        insert_event(self.conn, "VIN2", "appeared_in_tekion", "tekion")
        self.conn.commit()

        body = self.client.get("/activity", params={"vin": "VIN1"}).json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["vin"], "VIN1")

    def test_limit_query_param_respected(self):
        for i in range(5):
            insert_event(self.conn, "VIN1", "keys_checked_out", "keyper", summary=f"event {i}")
        self.conn.commit()

        body = self.client.get("/activity", params={"limit": 2}).json()
        self.assertEqual(len(body), 2)

    def test_detail_fields_round_trips_as_a_real_dict_not_a_json_string(self):
        insert_event(
            self.conn, "VIN1", "keys_checked_out", "keyper", summary="s",
            detail_fields={"duration_minutes": 374, "typical_minutes": 120},
        )
        self.conn.commit()

        body = self.client.get("/activity").json()
        self.assertEqual(body[0]["detail_fields"], {"duration_minutes": 374, "typical_minutes": 120})


class ReportsEndpointTest(ApiTestCase):
    def test_empty_dataset_returns_valid_zeroed_shape(self):
        resp = self.client.get("/reports")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["inventory_health"]["health_percentage"])

    def test_reuses_the_same_shape_as_dashboard_deliberately(self):
        # See api/routers/reports.py's docstring: no new DTO was
        # invented for Reports, per this sprint's explicit instruction
        # not to invent new DTOs.
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        insert_task(self.conn, "VIN1", "install_recovr_device", department="Lot Ops")
        self.conn.commit()

        dashboard_body = self.client.get("/dashboard").json()
        reports_body = self.client.get("/reports").json()
        self.assertEqual(set(dashboard_body.keys()), set(reports_body.keys()))
        self.assertEqual(reports_body["task_counts_by_department"], {"Lot Ops": 1})


if __name__ == "__main__":
    unittest.main()
