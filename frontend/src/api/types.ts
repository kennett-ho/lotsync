/**
 * Wire types for the LotSync FastAPI backend. Mirrors api/dtos.py and
 * API_CONTRACTS.md's Section 3 field-for-field -- snake_case throughout,
 * matching the backend's own column names verbatim (no frontend-side
 * translation layer, per API_CONTRACTS.md's Design Philosophy).
 *
 * This file is the only place backend response shapes are declared.
 * Do not redeclare a parallel interface in a dashboard component --
 * import from here so a backend field rename only needs updating once.
 */

export interface VehicleSummaryDTO {
  vin: string
  stock_number: string | null
  year: number | null
  make: string | null
  model: string | null
}

export interface VehicleDTO {
  vin: string
  stock_number: string | null
  year: number | null
  make: string | null
  model: string | null
  new_or_used: string | null
  current_dealership_id: string | null
  tekion_status: string | null
  keyper_status: string | null
  mdd_status: string | null
  recovr_status: string | null
  inventory_state: string | null
  open_task_count: number
}

/**
 * commitment_standing and execution_status are independent axes -- see
 * API_CONTRACTS.md's TaskDTO section. Never collapse these into one
 * "status" value anywhere in the frontend.
 */
export interface TaskDTO {
  task_id: number
  vin: string
  dealership_id: string | null
  task_type: string
  department: string | null
  priority: string | null
  commitment_standing: 'outstanding' | 'honored' | 'moot' | 'cancelled' | 'superseded'
  execution_status: 'not_started' | 'in_progress' | 'blocked' | 'completed'
  assigned_employee_id: string | null
  ratified_by: string | null
  ratification_type: string | null
  escalated_from_task_id: number | null
  reason: string | null
  created_at: string
  completed_at: string | null
  vehicle: VehicleSummaryDTO | null
}

export interface RecommendationDTO {
  recommendation_id: number
  vin: string
  severity: string | null
  title: string | null
  detail: string | null
  rule_source: string
  status: 'open' | 'converted_to_task' | 'dismissed'
  resulting_task_id: number | null
  created_at: string
  resolved_at: string | null
  vehicle: VehicleSummaryDTO | null
}

export interface ActivityDTO {
  event_id: number
  vin: string
  event_type: string
  source: string
  sync_run_id: string | null
  actor_employee_id: string | null
  dealership_id: string | null
  observed_at: string
  summary: string | null
  detail_fields: Record<string, unknown> | null
  vehicle: VehicleSummaryDTO | null
}

export interface ConnectedSystemStatusDTO {
  status: string
  started_at: string
  completed_at: string | null
  records_processed: number | null
}

export interface InventoryHealthDTO {
  healthy_vehicles: number
  total_vehicles: number
  health_percentage: number | null
}

export interface DashboardSummaryDTO {
  connected_systems: Record<string, ConnectedSystemStatusDTO>
  task_counts_by_department: Record<string, number>
  inventory_health: InventoryHealthDTO
  recent_activity: ActivityDTO[]
}

export interface VehicleDetailDTO extends VehicleDTO {
  tasks: TaskDTO[]
  recommendations: RecommendationDTO[]
  timeline: ActivityDTO[]
  connected_systems: Record<string, ConnectedSystemStatusDTO>
}

/**
 * An observation that couldn't be resolved to a known Vehicle's VIN --
 * the Inventory Sync page's Exceptions panel data source. See
 * API_CONTRACTS.md's PendingIdentityDTO section. Deliberately NOT the
 * mockup's assignable status/suggestedAction shape -- no backend for
 * that exists.
 */
export interface PendingIdentityDTO {
  pending_identity_id: number
  source: string
  raw_identifier: string
  identifier_type: string
  status: 'pending' | 'resolved'
  first_observed_at: string
  last_observed_at: string
  resolved_vin: string | null
  resolved_at: string | null
}

export interface SyncRunDTO {
  sync_run_id: number
  source: string
  status: string
  started_at: string
  completed_at: string | null
  records_processed: number | null
}

/** One entry in GET /inventory-sync/history -- a derived grouping, not a stored batch. */
export interface SyncRunBatchDTO {
  started_at: string
  overall_status: string
  sources: SyncRunDTO[]
}

/**
 * POST /inventory-sync/run's response. No single top-level sync_run_id --
 * SyncRun is real per-source granularity (see DATA_MODEL.md) -- so this
 * carries both triggered_at (the shared batch key) and the full
 * per-source sync_runs list. See api/dtos.py's SyncSummaryDTO.
 */
export interface SyncSummaryDTO {
  triggered_at: string
  sync_runs: SyncRunDTO[]
  vehicles_processed: number
  exceptions_found: number
  tasks_generated: number
  recommendations_generated: number
}
