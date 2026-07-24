"""
PHASE 2 SCAFFOLDING -- not yet used. See models/vehicle.py for context.

Represents a single observed change for a vehicle across sync runs
(e.g. "appeared in Tekion," "sold," "key checked out"). This is the
piece that would let the system distinguish "flagged for the first
time" from "flagged for the third sync in a row" -- see README.md,
"Known limitations: No memory between runs."

REVISED after the frontend discovery review (see ARCHITECTURE.md):
the original shape here was a raw field diff ("recovr_status changed
from No to Yes"). The Vehicle Detail mockup's Timeline needs more than
that -- narrative, structured entries like "Keys checked out by Sales
-- Checked out to James Miller, 6hrs14min outstanding, typically
<2hrs." A bare field diff can't produce that on its own. `summary` and
`detail_fields` exist to carry the narrative and the structured data
that supports it, separately -- summary for display, detail_fields for
anything downstream logic needs to reason about (e.g. duration
comparisons against a typical baseline).
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Event:
    # Surrogate primary key -- added during Phase 2 Sprint 1 schema work.
    # Event has no natural unique key (a vehicle can have many events
    # over time), unlike Vehicle (vin) or Task (task_id); this dataclass's
    # original shape overlooked that. See DATA_MODEL.md.
    event_id: Optional[int] = None
    vin: Optional[str] = None
    event_type: Optional[str] = None      # e.g. "appeared_in_tekion", "sold", "keys_checked_out", "dealer_transfer"
    source: Optional[str] = None          # e.g. "tekion", "keyper", "mdd", "recovr", "rapidrecon", "lot"
    sync_run_id: Optional[str] = None     # which sync detected this -- see models/sync_run.py
    actor_employee_id: Optional[str] = None  # nullable -- system-detected events have no actor
    # Captured at write time, NOT derived from Vehicle.current_dealership_id
    # -- a vehicle transferring stores later shouldn't retroactively
    # change where a past event appears to have happened. This is what
    # keeps the Timeline historically accurate across a dealer_transfer.
    dealership_id: Optional[str] = None
    observed_at: Optional[str] = None
    summary: Optional[str] = None         # human-readable, for the Timeline display
    detail_fields: dict = field(default_factory=dict)  # structured data behind the summary
