"""
GET /tasks -- API_CONTRACTS.md's TaskDTO list. Filters mirror the real
backend columns; see queries/tasks.py's list_tasks.

GET /tasks/work-order -- the printable Daily Work Order PDF (the Tasks
page's "Export Work Order" button). Deliberately thin, same convention
as every other router in this package: fetch today's outstanding tasks
via the existing query, read the dealership's configured store name,
and hand both to reports/work_order.py, which owns the actual PDF
layout. No reportlab code, no task-display/grouping logic, lives here.
"""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Response

from lotsync.api.dependencies import get_db
from lotsync.api.dtos import TaskDTO
from lotsync.config.settings import load_settings
from lotsync.queries.tasks import list_tasks
from lotsync.reports.work_order import build_work_order, work_order_filename

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


# Registered before any future /tasks/{task_id}-shaped route would be --
# FastAPI matches routes in registration order, and "work-order" would
# otherwise be swallowed as a path parameter by a dynamic route defined
# earlier. Nothing dynamic exists on this prefix yet, but worth stating
# explicitly so a later addition doesn't silently shadow this one.
@router.get("/tasks/work-order")
def get_tasks_work_order(conn: sqlite3.Connection = Depends(get_db)) -> Response:
    tasks = list_tasks(conn, commitment_standing="outstanding")
    store_name = load_settings()["store_name"]
    result = build_work_order(tasks, store_name=store_name)
    filename = work_order_filename()
    return Response(
        content=result.pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
