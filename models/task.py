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
    status: Optional[str] = None          # "not_started", "in_progress", "complete"
    assigned_employee_id: Optional[str] = None  # nullable -- mockup shows "Unassigned" as a real state
    reason: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
