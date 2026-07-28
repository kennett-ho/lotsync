"""
Phase 3, Sprint 2 -- Task reads. Same module boundary as
queries/dashboard.py (read-only, no new stored state, no HTTP, no
serialization framework -- see queries/__init__.py). Every function
here takes an open sqlite3.Connection and returns plain dict/list data;
translating that into API_CONTRACTS.md's TaskDTO shape is the api/
package's job, not this one's.

list_tasks() is the single query behind two different consumers: the
Tasks screen (called with no `vin` filter) and VehicleDetailDTO's
`tasks` collection (called with `vin` set to one vehicle) -- per this
sprint's own instruction not to duplicate queries, this is one function
at two scopes, not two functions.
"""

import sqlite3


def list_tasks(
    conn: sqlite3.Connection,
    vin: str = None,
    department: str = None,
    priority: str = None,
    commitment_standing: str = None,
    assigned_employee_id: str = None,
) -> list:
    """
    Returns Task rows, each joined with a lightweight Vehicle summary
    (matching API_CONTRACTS.md's VehicleSummaryDTO fields exactly --
    vin, stock_number, year, make, model) so a Task list never requires
    a separate per-row Vehicle lookup. The join is INNER, not LEFT --
    safe because task.vin carries a real FOREIGN KEY to vehicle
    (migrations/0004_task.sql), so an orphaned Task cannot exist.

    Ordered by task_id descending (a true autoincrement sequence, not
    created_at) for the same determinism reason
    queries/dashboard.py's recent_activity_feed already orders by
    event_id rather than observed_at.

    All filters are optional and combine with AND; omitting all of them
    returns every Task. `vin` scopes this to one vehicle's Tasks (the
    VehicleDetailDTO case); the rest are the filters the Tasks screen's
    sidebar already wants (FRONTEND_BACKEND_RECONCILIATION.md).
    """
    conditions = []
    params = []
    if vin is not None:
        conditions.append("t.vin = ?")
        params.append(vin)
    if department is not None:
        conditions.append("t.department = ?")
        params.append(department)
    if priority is not None:
        conditions.append("t.priority = ?")
        params.append(priority)
    if commitment_standing is not None:
        conditions.append("t.commitment_standing = ?")
        params.append(commitment_standing)
    if assigned_employee_id is not None:
        conditions.append("t.assigned_employee_id = ?")
        params.append(assigned_employee_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = conn.execute(
        f"""
        SELECT t.task_id, t.vin, t.dealership_id, t.task_type, t.department, t.priority,
               t.commitment_standing, t.execution_status, t.assigned_employee_id,
               t.ratified_by, t.ratification_type, t.escalated_from_task_id, t.reason,
               t.created_at, t.completed_at,
               v.stock_number, v.year, v.make, v.model
        FROM task t
        JOIN vehicle v ON v.vin = t.vin
        {where_clause}
        ORDER BY t.task_id DESC
        """,
        params,
    ).fetchall()

    columns = [
        "task_id", "vin", "dealership_id", "task_type", "department", "priority",
        "commitment_standing", "execution_status", "assigned_employee_id",
        "ratified_by", "ratification_type", "escalated_from_task_id", "reason",
        "created_at", "completed_at",
        "stock_number", "year", "make", "model",
    ]
    results = []
    for row in rows:
        record = dict(zip(columns, row))
        vehicle_summary = {
            "vin": record["vin"],
            "stock_number": record.pop("stock_number"),
            "year": record.pop("year"),
            "make": record.pop("make"),
            "model": record.pop("model"),
        }
        record["vehicle"] = vehicle_summary
        results.append(record)
    return results
