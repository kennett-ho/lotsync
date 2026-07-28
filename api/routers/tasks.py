"""GET /tasks -- API_CONTRACTS.md's TaskDTO list. Filters mirror the real backend columns; see queries/tasks.py's list_tasks."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends

from lotsync.api.dependencies import get_db
from lotsync.api.dtos import TaskDTO
from lotsync.queries.tasks import list_tasks

router = APIRouter()


@router.get("/tasks", response_model=list[TaskDTO])
def get_tasks(
    department: Optional[str] = None,
    priority: Optional[str] = None,
    commitment_standing: Optional[str] = None,
    assigned_employee_id: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> list:
    return list_tasks(
        conn,
        department=department,
        priority=priority,
        commitment_standing=commitment_standing,
        assigned_employee_id=assigned_employee_id,
    )
