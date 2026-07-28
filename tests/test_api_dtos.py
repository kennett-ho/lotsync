"""
Phase 3, Sprint 2 verification -- api/dtos.py, independent of any
query or HTTP layer. Confirms each DTO validates and serializes exactly
per API_CONTRACTS.md's field lists (snake_case, matching backend column
names verbatim), and that VehicleDetailDTO is genuinely a superset of
VehicleDTO (API_CONTRACTS.md's own stated relationship), not a sibling
that happens to look similar.
"""

import unittest

from lotsync.api.dtos import (
    ActivityDTO, ConnectedSystemStatusDTO, DashboardSummaryDTO, InventoryHealthDTO,
    RecommendationDTO, TaskDTO, VehicleDetailDTO, VehicleDTO, VehicleSummaryDTO,
)


class VehicleSummaryDTOTest(unittest.TestCase):
    def test_no_color_field_exists(self):
        # Corrected during this sprint's implementation -- the backend
        # Vehicle schema has no color column. Confirms the correction
        # actually took, not just documented in prose.
        summary = VehicleSummaryDTO(vin="VIN1", stock_number="A48291", year=2023, make="Honda", model="Accord")
        self.assertNotIn("color", summary.model_dump())

    def test_only_vin_is_required(self):
        summary = VehicleSummaryDTO(vin="VIN1")
        self.assertIsNone(summary.stock_number)
        self.assertIsNone(summary.year)


class TaskDTOTest(unittest.TestCase):
    def test_commitment_standing_and_execution_status_are_independent_fields(self):
        task = TaskDTO(
            task_id=1, vin="VIN1", task_type="install_recovr_device",
            commitment_standing="outstanding", execution_status="completed",
            created_at="2026-07-27T00:00:00",
        )
        # The exact "surfaced disagreement" case API_CONTRACTS.md names:
        # execution done, commitment not yet corroborated. Both must be
        # independently representable -- neither derived from the other.
        self.assertEqual(task.commitment_standing, "outstanding")
        self.assertEqual(task.execution_status, "completed")

    def test_no_single_status_field_exists(self):
        task = TaskDTO(
            task_id=1, vin="VIN1", task_type="install_recovr_device",
            commitment_standing="outstanding", execution_status="not_started",
            created_at="2026-07-27T00:00:00",
        )
        self.assertNotIn("status", task.model_dump())

    def test_vehicle_defaults_to_none(self):
        task = TaskDTO(
            task_id=1, vin="VIN1", task_type="install_recovr_device",
            commitment_standing="outstanding", execution_status="not_started",
            created_at="2026-07-27T00:00:00",
        )
        self.assertIsNone(task.vehicle)

    def test_embedded_vehicle_summary_validates(self):
        task = TaskDTO(
            task_id=1, vin="VIN1", task_type="install_recovr_device",
            commitment_standing="outstanding", execution_status="not_started",
            created_at="2026-07-27T00:00:00",
            vehicle=VehicleSummaryDTO(vin="VIN1", stock_number="A48291"),
        )
        self.assertEqual(task.vehicle.stock_number, "A48291")


class ActivityDTOTest(unittest.TestCase):
    def test_detail_fields_accepts_an_arbitrary_dict(self):
        # DATA_MODEL.md's own "unvalidated dict for now" note --
        # confirms this DTO doesn't reject a shape it hasn't seen before.
        event = ActivityDTO(
            event_id=1, vin="VIN1", event_type="keys_checked_out", source="keyper",
            observed_at="2026-07-27T00:00:00",
            detail_fields={"anything": "goes", "nested": {"a": 1}},
        )
        self.assertEqual(event.detail_fields["nested"]["a"], 1)

    def test_detail_fields_defaults_to_none(self):
        event = ActivityDTO(
            event_id=1, vin="VIN1", event_type="keys_checked_out", source="keyper",
            observed_at="2026-07-27T00:00:00",
        )
        self.assertIsNone(event.detail_fields)


class VehicleDetailDTOTest(unittest.TestCase):
    """API_CONTRACTS.md: "this DTO is a superset, not a sibling -- every field VehicleDTO has, this has, under the same name.\""""

    def test_is_a_subclass_of_vehicle_dto(self):
        self.assertTrue(issubclass(VehicleDetailDTO, VehicleDTO))

    def test_carries_every_vehicle_dto_field_plus_the_four_nested_collections(self):
        detail = VehicleDetailDTO(vin="VIN1")
        vehicle_fields = set(VehicleDTO.model_fields.keys())
        detail_fields = set(VehicleDetailDTO.model_fields.keys())
        self.assertTrue(vehicle_fields.issubset(detail_fields))
        self.assertEqual(
            detail_fields - vehicle_fields,
            {"tasks", "recommendations", "timeline", "connected_systems"},
        )

    def test_empty_collections_default_correctly(self):
        detail = VehicleDetailDTO(vin="VIN1")
        self.assertEqual(detail.tasks, [])
        self.assertEqual(detail.recommendations, [])
        self.assertEqual(detail.timeline, [])
        self.assertEqual(detail.connected_systems, {})


class DashboardSummaryDTOTest(unittest.TestCase):
    def test_no_vehicles_case_validates_with_none_health_percentage(self):
        summary = DashboardSummaryDTO(
            connected_systems={},
            task_counts_by_department={},
            inventory_health=InventoryHealthDTO(healthy_vehicles=0, total_vehicles=0, health_percentage=None),
            recent_activity=[],
        )
        self.assertIsNone(summary.inventory_health.health_percentage)

    def test_connected_systems_is_keyed_by_source(self):
        summary = DashboardSummaryDTO(
            connected_systems={
                "recovr": ConnectedSystemStatusDTO(status="complete", started_at="2026-07-27T07:02:00"),
            },
            task_counts_by_department={"Inventory": 3},
            inventory_health=InventoryHealthDTO(healthy_vehicles=1, total_vehicles=1, health_percentage=100.0),
            recent_activity=[],
        )
        self.assertEqual(summary.connected_systems["recovr"].status, "complete")


class RecommendationDTOTest(unittest.TestCase):
    def test_no_dealership_id_field_exists(self):
        # DATA_MODEL.md: Recommendation deliberately has no
        # dealership_id -- always derivable via vin. Confirms the DTO
        # didn't quietly add one back in.
        rec = RecommendationDTO(
            recommendation_id=1, vin="VIN1", rule_source="recovr_missing",
            status="open", created_at="2026-07-27T00:00:00",
        )
        self.assertNotIn("dealership_id", rec.model_dump())


if __name__ == "__main__":
    unittest.main()
