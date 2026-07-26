"""
PHASE 2 SCAFFOLDING -- not yet used. See models/vehicle.py for context.

Represents a single actionable item (install a tracker, replace tags,
investigate a discrepancy) that would eventually live on a Vehicle's
pending_tasks list and drive the lot-staff dashboard (Milestone 2).

REVISED after the frontend discovery review (see ARCHITECTURE.md):
clarified granularity. The dashboard mockup shows cards like "Install
RecovR Devices -- 6 tasks, 1 of 6 complete" -- that's a task-TYPE
group, not one Task with a count. Each of the 6 is its own Task, one
vehicle, one action; the dashboard aggregates by task_type for display.
Getting this wrong would break the dashboard's grouping logic later,
so it's decided now rather than left implicit.
REVISED again after the tenant/dealership architecture decision (see
DATA_MODEL.md): added dealership_id. Known, explicitly NOT solved
here: dealer-trade tasks ("Pending Pickup," "Accepted -- In Transit"
in the dashboard mockup) inherently span two dealerships -- a pickup
origin and a delivery destination -- which a single dealership_id
can't represent. Every Phase 2 task type (install a tracker, replace
a tag, investigate a discrepancy) is genuinely single-dealership, so
this isn't a Phase 2 blocker. It IS a known gap Phase 4 (Dealer
Trades, per PRODUCT.md) will need to revisit -- likely a specialized
task shape or a from/to pair, not yet designed. Written down here so
it's a planned revisit, not a surprise.

REVISED again ahead of Sprint 4 (Pre-Sprint 4 design review -- see
DATA_MODEL.md's Task entry, DECISION_FRAMEWORK.md's "Ontology,
Architecture, Invariants, and Reasoning Tools" section, and
SPRINT_4_DESIGN_REVIEW_SUMMARY.md). A Task is an operational
commitment, not a directive and not a Recommendation with a richer
status. The original three-value `status` couldn't honestly represent
a commitment discharged because it became moot, was cancelled, or was
superseded -- replaced by `commitment_standing` (Reality-discharged:
honored/moot; Intent-discharged: cancelled/superseded) and a separate,
derived `execution_status`, independent axes rather than one field.
Execution's own append-only history lives in TaskExecutionEvent (see
models/task_execution_event.py), not on this dataclass -- the same
reason Event exists separately from Vehicle. `ratified_by`/
`ratification_type` model authority explicitly (independent from
provenance -- a Recommendation converting to a Task is provenance, not
authority). `escalated_from_task_id` lets Moot-evaluation walk a
parent Task's status, not just this Task's own condition.

Known, unresolved gap carried into Sprint 4, not solved by this
revision: a dealership transfer is currently an implicit assumption for
install-type Tasks. Must be made explicit or explicitly excluded before
Sprint 4's discharge logic ships -- see SPRINT_4_CHECKLIST.md.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    task_id: Optional[str] = None
    vin: Optional[str] = None
    dealership_id: Optional[str] = None   # see docstring re: dealer-trade tasks, deferred to Phase 4
    task_type: Optional[str] = None       # e.g. "install_recovr_device" -- see rules/aging.py etc. for the vocabulary
    department: Optional[str] = None      # e.g. "Inventory", "Controller", "Lot Ops", "Dealer Trades"
    priority: Optional[str] = None        # e.g. "Critical", "High", "Medium", "Low"
    commitment_standing: Optional[str] = None  # "outstanding" / "honored" / "moot" / "cancelled" / "superseded"
    execution_status: Optional[str] = None     # derived cache -- "not_started" / "in_progress" / "blocked" / "completed"
    assigned_employee_id: Optional[str] = None  # nullable -- mockup shows "Unassigned" as a real state
    ratified_by: Optional[str] = None          # employee_id, or a standing-policy identifier
    ratification_type: Optional[str] = None    # "human" / "standing_policy"
    escalated_from_task_id: Optional[str] = None  # nullable -- FK to Task
    reason: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None    # set when commitment_standing reaches any terminal value, not only "complete"
