"""
Phase 3, Sprint 2 -- DTOs, implemented for the first time from
API_CONTRACTS.md's Section 3 exactly. Field names are snake_case,
matching the backend's own column names verbatim, per API_CONTRACTS.md's
Design Philosophy ("one name per concept, matching the name
DATA_MODEL.md already uses"). No field here was invented; every one is
either a real column (see database/migrations/*.sql) or a field
API_CONTRACTS.md already documented as computed
(VehicleDTO.open_task_count) or derived (the Connected Systems view).

One correction relative to the original API_CONTRACTS.md text, made
during this sprint's implementation and already reflected back into
that document: VehicleSummaryDTO does NOT carry a `color` field. The
`vehicle` table has no such column, and nothing populates one -- see
API_CONTRACTS.md's VehicleSummaryDTO section and
PHASE_3_SPRINT_2_REVIEW.md for where this was caught.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel


class VehicleSummaryDTO(BaseModel):
    """Embeddable projection of a Vehicle -- never fetched on its own."""
    vin: str
    stock_number: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None


class VehicleDTO(BaseModel):
    """The Vehicles List screen's row shape."""
    vin: str
    stock_number: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    new_or_used: Optional[str] = None
    current_dealership_id: Optional[str] = None
    tekion_status: Optional[str] = None
    keyper_status: Optional[str] = None
    mdd_status: Optional[str] = None
    recovr_status: Optional[str] = None
    inventory_state: Optional[str] = None
    open_task_count: int = 0


class TaskDTO(BaseModel):
    """
    commitment_standing and execution_status are two independent,
    always-read-only fields -- never collapsed into one "status."
    See API_CONTRACTS.md's TaskDTO section: this is the single most
    important rule in the whole contract to preserve.
    """
    task_id: int
    vin: str
    dealership_id: Optional[str] = None
    task_type: str
    department: Optional[str] = None
    priority: Optional[str] = None
    commitment_standing: str
    execution_status: str
    assigned_employee_id: Optional[str] = None
    ratified_by: Optional[str] = None
    ratification_type: Optional[str] = None
    escalated_from_task_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    vehicle: Optional[VehicleSummaryDTO] = None


class RecommendationDTO(BaseModel):
    recommendation_id: int
    vin: str
    severity: Optional[str] = None
    title: Optional[str] = None
    detail: Optional[str] = None
    rule_source: str
    status: str
    resulting_task_id: Optional[int] = None
    created_at: str
    resolved_at: Optional[str] = None
    vehicle: Optional[VehicleSummaryDTO] = None


class ActivityDTO(BaseModel):
    """
    `detail_fields` is intentionally left as an open dict, per
    DATA_MODEL.md's own "unvalidated dict for now -- accepted debt"
    note on Event -- not further typed here.
    """
    event_id: int
    vin: str
    event_type: str
    source: str
    sync_run_id: Optional[str] = None
    actor_employee_id: Optional[str] = None
    dealership_id: Optional[str] = None
    observed_at: str
    summary: Optional[str] = None
    detail_fields: Optional[dict] = None
    vehicle: Optional[VehicleSummaryDTO] = None


class ConnectedSystemStatusDTO(BaseModel):
    """One source's most recent SyncRun -- connected_systems_status()'s per-entry shape."""
    status: str
    started_at: str
    completed_at: Optional[str] = None
    records_processed: Optional[int] = None


class InventoryHealthDTO(BaseModel):
    healthy_vehicles: int
    total_vehicles: int
    health_percentage: Optional[float] = None


class DashboardSummaryDTO(BaseModel):
    """
    Composed directly from queries/dashboard.py's four existing
    functions -- see api/routers/dashboard.py. Also what GET /reports
    returns (see api/routers/reports.py's docstring for why this sprint
    deliberately reuses this DTO rather than inventing a
    Reports-specific one).
    """
    connected_systems: Dict[str, ConnectedSystemStatusDTO]
    task_counts_by_department: Dict[str, int]
    inventory_health: InventoryHealthDTO
    recent_activity: List[ActivityDTO]


class VehicleDetailDTO(VehicleDTO):
    """
    Superset of VehicleDTO, not a sibling -- API_CONTRACTS.md's own
    phrasing. Nested tasks/recommendations/timeline entries never carry
    their own `vehicle` field populated (always None) -- redundant with
    the Vehicle this whole response is already about. See
    api/routers/vehicles.py for where that stripping happens.
    """
    tasks: List[TaskDTO] = []
    recommendations: List[RecommendationDTO] = []
    timeline: List[ActivityDTO] = []
    connected_systems: Dict[str, ConnectedSystemStatusDTO] = {}
