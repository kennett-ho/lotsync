"""
GET /dashboard -- composes queries/dashboard.py's four existing, already
-tested Slice 7 functions into API_CONTRACTS.md's DashboardSummaryDTO.
No new business logic; this is a pure translation layer.
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


@router.get("/dashboard", response_model=DashboardSummaryDTO)
def get_dashboard(conn: sqlite3.Connection = Depends(get_db)) -> DashboardSummaryDTO:
    return DashboardSummaryDTO(
        connected_systems=connected_systems_status(conn),
        task_counts_by_department=task_counts_by_department(conn),
        inventory_health=inventory_health_percentage(conn),
        recent_activity=recent_activity_feed(conn),
    )
