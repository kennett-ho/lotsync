"""
PHASE 2 SCAFFOLDING -- not yet used. See models/vehicle.py for context.

Distinct from Task, on purpose -- identified during the frontend
discovery review. A Recommendation has its own lifecycle (shown or
dismissed) before it ever becomes a Task; collapsing the two into one
model would lose the dismiss/ignore path the mockups show explicitly
("Create Task" / "Dismiss" / "Assign" as separate actions on the same
card).

These are rule-driven, not ML-driven, for now -- deterministic
business rules over Vehicle state (Missing RecovR, Keys Out > N hours,
Inventory Age > 30 days, etc.), the same rules already living in
rules/aging.py and rules/inventory.py. "AI Recommendations" in the UI
is a display label, not a claim about how these are actually
generated; predictive/ML-based recommendations are explicitly deferred
per the frontend discovery review, not an architectural requirement now.

No dealership_id here, deliberately -- unlike Event (which needs its
own copy for historical accuracy across a dealer_transfer), a
Recommendation is always evaluated against a Vehicle's CURRENT state,
so its dealership is always "wherever the vehicle currently is,"
derivable via vin -> Vehicle.current_dealership_id. Adding a redundant
copy here would just be a second value that could drift from the
first for no benefit.

REVISED during Slice 6 implementation: added created_at/resolved_at
(see DATA_MODEL.md's Recommendation entry) -- needed to actually
implement "a dismissed Recommendation does not reappear unless the
underlying vehicle state genuinely changes again," which requires
knowing WHEN a Recommendation was dismissed, not just that it was.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Recommendation:
    recommendation_id: Optional[str] = None
    vin: Optional[str] = None
    severity: Optional[str] = None        # e.g. "Critical", "High", "Medium", "Low"
    title: Optional[str] = None           # e.g. "RecovR tracker missing -- 42 days untracked"
    detail: Optional[str] = None
    rule_source: Optional[str] = None     # which rule generated this, for traceability
    status: Optional[str] = None          # "open", "converted_to_task", "dismissed"
    resulting_task_id: Optional[str] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None     # set when status moves to converted_to_task or dismissed
