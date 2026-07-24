"""
PHASE 2 SCAFFOLDING -- not yet used. See models/vehicle.py for context.

Identified as load-bearing, not optional, during the frontend
discovery review (Figma Make mockups, see ARCHITECTURE.md "Frontend
discovery" section): nearly every Event and Task in the mockups has an
attributed actor -- checked in by, installed by, assigned to, moved
by. Event and Task can't carry that attribution without this existing.

dealership_id is a home/primary assignment, not a hard constraint.
Real data already shows this is messier in practice than a clean
one-employee-one-store model: the Keyper System-field discovery found
Kia-prefixed vehicles filed under Mitsubishi service roughly a quarter
of the time, almost certainly because service staff work across
sister-store lines. Modeled as a home assignment on purpose rather
than something enforced strictly -- solving precise cross-store
staffing isn't needed for Phase 2 and shouldn't be guessed at now.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Employee:
    employee_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None            # e.g. "Lot Manager", "Sales"
    department: Optional[str] = None      # e.g. "Inventory", "Controller", "Lot Ops"
    dealership_id: Optional[str] = None   # home/primary assignment -- see docstring
    status: Optional[str] = None          # e.g. "Available", "Installing", "Lunch"
