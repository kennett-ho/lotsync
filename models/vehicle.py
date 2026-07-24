"""
PHASE 2 SCAFFOLDING -- not yet wired into the reconciliation engine.

sync/reconciler.py currently builds report-shaped dicts directly from
source dataframes; it does not construct or update Vehicle objects.
This class exists so the shape of the eventual canonical model is
decided and visible, without forcing a rewrite of working reconciliation
logic in the same change that reorganized the project into modules.

When Phase 2 happens, sync/reconciler.py's functions get restructured
to build one Vehicle per VIN, populate its per-source status fields as
each source is processed, and the existing report-shaped output
(fully_verified, key_out_aging, etc.) becomes a rendering step over a
collection of Vehicle objects rather than the thing reconciliation
directly produces. See ARCHITECTURE.md, "How reconciliation flows
through the system."
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Vehicle:
    vin: Optional[str] = None
    stock_number: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    new_or_used: Optional[str] = None

    # Mutable current attribute, NOT part of Vehicle identity -- a
    # vehicle transferring between sister dealerships (Mark Kia <->
    # Mark Mazda <-> Mark Mitsubishi) stays the same Vehicle. See
    # DATA_MODEL.md "Tenant vs Dealership" for why this was decided
    # explicitly rather than left implicit. Historical dealership at
    # the time of a past event lives on that Event, not here -- this
    # field only ever reflects "right now."
    current_dealership_id: Optional[str] = None

    tekion_status: Optional[str] = None       # e.g. "Stocked In", "Sold"
    keyper_status: Optional[str] = None       # e.g. "In", "Out", None (no key)
    mdd_status: Optional[str] = None          # e.g. "paired", "not_paired", "unknown"
    recovr_status: Optional[str] = None       # e.g. "paired", "not_paired", "unknown"

    inventory_state: Optional[str] = None     # the eventual state-machine label
    pending_tasks: list = field(default_factory=list)
    history: list = field(default_factory=list)
