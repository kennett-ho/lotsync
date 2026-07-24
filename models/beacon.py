"""
PHASE 2 SCAFFOLDING -- not yet used. See models/vehicle.py for context.

Represents a single MDD beacon or RecovR device, separate from the
Vehicle it's (or isn't) attached to. Splitting this out matters once
"Duplicate beacon" detection is built (see original architecture doc,
Milestone 1 Reconciliation list) -- that needs to reason about a
device independent of any one vehicle, e.g. the same beacon appearing
assigned to two different VINs.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Beacon:
    device_id: Optional[str] = None
    device_type: Optional[str] = None    # "mdd" or "recovr"
    vin: Optional[str] = None            # currently assigned vehicle, if any
    paired: Optional[bool] = None
    battery_level: Optional[str] = None
