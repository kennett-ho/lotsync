"""
PHASE 2 SCAFFOLDING -- not yet used. See models/vehicle.py for context.

Added during the Pre-Sprint 4 design review (see DATA_MODEL.md's
TaskExecutionEvent entry and DECISION_FRAMEWORK.md's "Ontology,
Architecture, Invariants, and Reasoning Tools" section). Append-only
log of a Task's execution progress, independent of `commitment_standing`
(see models/task.py) -- a mutable execution-status field failed the
same test PendingIdentity already failed once: consecutive transitions
carry real information a terminal snapshot destroys (e.g.
"started -> blocked -> resumed -> completed" tells a materially
different story than "started -> completed", even though both end the
same way).

Task completion is itself a manual assertion, not a direct status
write, per VISION.md's existing "manual input is an assertion, not an
override" principle -- a human recording `completed` here is
provisional until corroborated by the relevant source's next sync.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskExecutionEvent:
    task_execution_event_id: Optional[int] = None
    task_id: Optional[str] = None
    transition_type: Optional[str] = None   # "started" / "blocked" / "resumed" / "completed"
    actor_employee_id: Optional[str] = None  # nullable -- who made this transition
    note: Optional[str] = None              # free text, optional
    observed_at: Optional[str] = None
