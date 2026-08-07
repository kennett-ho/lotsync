"""
Phase 3, Sprint 2 verification -- queries/vehicles.py. list_vehicles()
(the Vehicles List screen's data) and get_vehicle_detail() (this
sprint's named reference implementation for how a detail page
aggregates Vehicle + Tasks + Recommendations + Timeline + Connected
Systems without duplicating any of those four queries).
"""

import unittest

from lotsync.database.repository import (
    connect, upsert_vehicle, insert_task, insert_recommendation, insert_event,
    sync_run,
)
from lotsync.queries.vehicles import list_vehicles, get_vehicle_detail


class ListVehiclesTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def test_empty_dataset_returns_empty_list(self):
        self.assertEqual(list_vehicles(self.conn), [])

    def test_returns_vehicle_fields_and_zero_open_task_count(self):
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", year=2023, make="Honda",
                        model="Accord", tekion_status="Stocked In")
        self.conn.commit()

        vehicles = list_vehicles(self.conn)
        self.assertEqual(len(vehicles), 1)
        v = vehicles[0]
        self.assertEqual(v["vin"], "VIN1")
        self.assertEqual(v["stock_number"], "A48291")
        self.assertEqual(v["tekion_status"], "Stocked In")
        self.assertEqual(v["open_task_count"], 0)

    def test_returns_display_name(self):
        # Phase 3, Sprint 5 addition -- see api/dtos.py's VehicleDTO
        # docstring for why this is a distinct field from year/make/model,
        # not derived from them.
        upsert_vehicle(self.conn, "VIN1", display_name="2023 Honda Accord")
        self.conn.commit()
        self.assertEqual(list_vehicles(self.conn)[0]["display_name"], "2023 Honda Accord")

    def test_open_task_count_reflects_only_outstanding_tasks(self):
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        task_id = insert_task(self.conn, "VIN1", "install_recovr_device")
        insert_task(self.conn, "VIN1", "install_mdd_beacon")
        self.conn.commit()

        vehicles = list_vehicles(self.conn)
        self.assertEqual(vehicles[0]["open_task_count"], 2)

        from lotsync.database.repository import honor_task
        honor_task(self.conn, task_id)
        self.conn.commit()

        vehicles = list_vehicles(self.conn)
        self.assertEqual(vehicles[0]["open_task_count"], 1)

    def test_ordered_by_vin(self):
        upsert_vehicle(self.conn, "VIN2")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        vehicles = list_vehicles(self.conn)
        self.assertEqual([v["vin"] for v in vehicles], ["VIN1", "VIN2"])

    def test_sold_vehicle_excluded_by_default(self):
        upsert_vehicle(self.conn, "VIN1", tekion_status="Stocked In")
        upsert_vehicle(self.conn, "VIN2", tekion_status="Sold")
        self.conn.commit()
        vehicles = list_vehicles(self.conn)
        self.assertEqual([v["vin"] for v in vehicles], ["VIN1"])

    def test_sold_vehicle_included_with_include_sold_true(self):
        upsert_vehicle(self.conn, "VIN1", tekion_status="Stocked In")
        upsert_vehicle(self.conn, "VIN2", tekion_status="Sold")
        self.conn.commit()
        vehicles = list_vehicles(self.conn, include_sold=True)
        self.assertEqual([v["vin"] for v in vehicles], ["VIN1", "VIN2"])

    def test_vehicle_with_no_tekion_status_still_shown_by_default(self):
        # A RecovR/Keyper-only match (no Tekion record at all) is
        # NULL, not 'Sold' -- must not be caught by the sold exclusion.
        # See list_vehicles' docstring on why this is IS NOT, not !=.
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        vehicles = list_vehicles(self.conn)
        self.assertEqual([v["vin"] for v in vehicles], ["VIN1"])


class GetVehicleDetailTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

    def test_missing_vehicle_returns_none(self):
        self.assertIsNone(get_vehicle_detail(self.conn, "NO-SUCH-VIN"))

    def test_vehicle_with_no_related_data_has_empty_collections(self):
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", year=2023, make="Honda", model="Accord")
        self.conn.commit()

        detail = get_vehicle_detail(self.conn, "VIN1")
        self.assertEqual(detail["vin"], "VIN1")
        self.assertEqual(detail["stock_number"], "A48291")
        self.assertEqual(detail["open_task_count"], 0)
        self.assertEqual(detail["tasks"], [])
        self.assertEqual(detail["recommendations"], [])
        self.assertEqual(detail["timeline"], [])
        self.assertEqual(detail["connected_systems"], {})

    def test_full_aggregation_across_all_four_collections(self):
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", year=2023, make="Honda", model="Accord")
        upsert_vehicle(self.conn, "VIN2", stock_number="B93021")
        self.conn.commit()

        insert_task(self.conn, "VIN1", "install_recovr_device")
        insert_recommendation(self.conn, "VIN1", "High", "RecovR missing", "42 days", "recovr_missing")
        insert_event(self.conn, "VIN1", "keys_checked_out", "keyper", summary="Keys checked out by Sales")
        # A second vehicle's data must never leak into VIN1's detail.
        insert_task(self.conn, "VIN2", "install_mdd_beacon")
        insert_recommendation(self.conn, "VIN2", "Low", "t", "d", "some_rule")
        insert_event(self.conn, "VIN2", "appeared_in_tekion", "tekion")
        self.conn.commit()

        with sync_run(self.conn, "recovr", records_processed=1):
            pass

        detail = get_vehicle_detail(self.conn, "VIN1")

        self.assertEqual(detail["open_task_count"], 1)
        self.assertEqual(len(detail["tasks"]), 1)
        self.assertEqual(detail["tasks"][0]["task_type"], "install_recovr_device")
        self.assertEqual(detail["tasks"][0]["vin"], "VIN1")

        self.assertEqual(len(detail["recommendations"]), 1)
        self.assertEqual(detail["recommendations"][0]["title"], "RecovR missing")

        self.assertEqual(len(detail["timeline"]), 1)
        self.assertEqual(detail["timeline"][0]["summary"], "Keys checked out by Sales")

        # connected_systems is the global per-source view, not
        # vehicle-scoped -- API_CONTRACTS.md's own documented shape.
        self.assertIn("recovr", detail["connected_systems"])
        self.assertEqual(detail["connected_systems"]["recovr"]["status"], "complete")

    def test_returns_display_name(self):
        upsert_vehicle(self.conn, "VIN1", display_name="2023 Honda Accord")
        self.conn.commit()
        self.assertEqual(get_vehicle_detail(self.conn, "VIN1")["display_name"], "2023 Honda Accord")

    def test_sold_vehicle_still_reachable_by_vin(self):
        # get_vehicle_detail is a direct-VIN lookup, not routed through
        # list_vehicles -- a sold vehicle dropping out of the default
        # list must not make it unreachable here.
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", tekion_status="Sold")
        self.conn.commit()
        detail = get_vehicle_detail(self.conn, "VIN1")
        self.assertEqual(detail["vin"], "VIN1")
        self.assertEqual(detail["tekion_status"], "Sold")

    def test_nested_task_and_recommendation_still_carry_their_own_vehicle_summary(self):
        # get_vehicle_detail returns the complete, undecorated data --
        # queries/vehicles.py's own docstring is explicit that trimming
        # the redundant nested `vehicle` field is the api/ layer's job,
        # not this function's. Confirms that division of responsibility
        # holds at the query layer.
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291")
        self.conn.commit()
        insert_task(self.conn, "VIN1", "install_recovr_device")
        self.conn.commit()

        detail = get_vehicle_detail(self.conn, "VIN1")
        self.assertIn("vehicle", detail["tasks"][0])
        self.assertEqual(detail["tasks"][0]["vehicle"]["vin"], "VIN1")


if __name__ == "__main__":
    unittest.main()
