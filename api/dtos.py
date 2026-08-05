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
    # The best available human-readable name for UI display, decoupled
    # from which source or shape supplied it -- see VehicleDTO's own
    # display_name note for the full reasoning.
    display_name: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None


class VehicleDTO(BaseModel):
    """The Vehicles List screen's row shape."""
    vin: str
    stock_number: Optional[str] = None
    # Phase 3, Sprint 5 addition. The one field the UI should render for
    # "this vehicle's name," full stop -- not year/make/model joined
    # client-side. Today populated verbatim from Tekion's single
    # "Year Make Model" export column (no parsing into year/make/model:
    # there's no reliable, general way to split "Make" from "Model" out
    # of free text without a canonical-make lookup table -- see
    # migrations/0007_vehicle_display_name.sql). year/make/model stay
    # reserved for a source that genuinely supplies them structured
    # (MDD/RecovR today, a VIN decoder in a future phase); whenever one
    # of those populates display_name too, from whatever it actually
    # knows, this field's meaning doesn't change -- "best available
    # display name," regardless of source.
    display_name: Optional[str] = None
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
    # When LotSync's sync learned about this -- the audit trail, always
    # populated, unchanged by Sprint 3.7. NOT what the Timeline should
    # display when event_time is available -- see event_time below.
    observed_at: str
    # Sprint 3.7 addition. The source's own claimed timestamp for when
    # this actually happened -- what the Timeline should render, when
    # present. Nullable: most sources don't expose a per-observation
    # timestamp with a confirmed meaning (see DATA_MODEL.md's Event
    # entry and sync/reconciler.py's persist_* functions for exactly
    # which event_types populate this and why). Frontend fallback is
    # event_time ?? observed_at, never the reverse.
    event_time: Optional[str] = None
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


class PendingIdentityDTO(BaseModel):
    """
    An observation that couldn't be resolved to a known Vehicle's VIN at
    the time it was recorded -- API_CONTRACTS.md's already-documented
    shape, implemented here for the first time (Phase 3, Sprint 4). The
    Inventory Sync page's Exceptions panel is this DTO's list, not a
    fabricated assignable-workflow shape -- see
    queries/inventory_sync.py's list_pending_identities.
    """
    pending_identity_id: int
    source: str
    raw_identifier: str
    identifier_type: str
    status: str
    first_observed_at: str
    last_observed_at: str
    resolved_vin: Optional[str] = None
    resolved_at: Optional[str] = None


class SyncRunDTO(BaseModel):
    """One source's execution within a sync -- matches DATA_MODEL.md's SyncRun."""
    sync_run_id: int
    source: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    records_processed: Optional[int] = None


class SyncRunBatchDTO(BaseModel):
    """
    One entry in GET /inventory-sync/history -- every SyncRun sharing one
    started_at, a derived grouping (see queries/inventory_sync.py's
    sync_run_history for why this isn't a stored batch_id).
    """
    started_at: str
    overall_status: str
    sources: List[SyncRunDTO]


class SyncSummaryDTO(BaseModel):
    """
    POST /inventory-sync/run's response. Deliberately does not carry a
    single top-level "sync_run_id" -- SyncRun is real per-source
    granularity (see DATA_MODEL.md), so this instead exposes both
    identifiers a future write-path caller would actually need:
    triggered_at (the shared batch key every sync_run in this run was
    stamped with) and the full per-source sync_runs list, each with its
    own real sync_run_id.

    Sprint 3.8 (Friday MVP task-generation refinements) addition:
    warnings -- currently populated only when Keyper wasn't uploaded
    this run, since RecovR-related task generation requires Keyper as
    evidence and is skipped entirely rather than silently reporting
    tasks_generated as if nothing was wrong. See
    sync/reconciler.py's generate_install_tasks docstring. Defaults to
    an empty list so this stays backward compatible with any consumer
    that predates this field.
    """
    triggered_at: str
    sync_runs: List[SyncRunDTO]
    vehicles_processed: int
    exceptions_found: int
    tasks_generated: int
    recommendations_generated: int
    warnings: List[str] = []


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
