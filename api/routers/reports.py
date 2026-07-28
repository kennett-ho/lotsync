"""
GET /reports -- "Only expose the operational summaries already
supported by the backend. No analytics. No historical trends. No
forecasting" (this sprint's own scope). What's actually backend-
supported today is exactly task_counts_by_department and
inventory_health_percentage -- per API_CONTRACTS.md's Section 4
(Read Models): "task_counts_by_department and inventory_health already
cover 2 of 7 [frontend Reports] tabs... the remaining tabs... are not
defined by this contract yet."

Deliberately returns the SAME DashboardSummaryDTO type as GET
/dashboard, rather than a new Reports-specific DTO -- API_CONTRACTS.md
Section 3 never defined one, and this sprint's instructions were
explicit: do not invent new DTOs. connected_systems and recent_activity
are included as a result even though the current frontend Reports tabs
don't display them -- harmless, and the honest alternative to either
inventing a new type or hand-waving two fields out of an existing one.
See PHASE_3_SPRINT_2_REVIEW.md's Architecture Review for this decision
stated in full.
"""

import sqlite3

from fastapi import APIRouter, Depends

from lotsync.api.dependencies import get_db
from lotsync.api.dtos import DashboardSummaryDTO
from lotsync.queries.dashboard import (
    connected_systems_status, recent_activity_feed,
    task_counts_by_department, inventory_health_percentage,
)

router = APIRouter()


@router.get("/reports", response_model=DashboardSummaryDTO)
def get_reports(conn: sqlite3.Connection = Depends(get_db)) -> DashboardSummaryDTO:
    return DashboardSummaryDTO(
        connected_systems=connected_systems_status(conn),
        task_counts_by_department=task_counts_by_department(conn),
        inventory_health=inventory_health_percentage(conn),
        recent_activity=recent_activity_feed(conn),
    )
