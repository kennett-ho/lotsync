"""
Phase 3, Sprint 2 -- Recommendation reads. Same module boundary and
same "one function, two scopes" reasoning as queries/tasks.py's
list_tasks: list_recommendations() backs both the Recommendations
screen (no `vin` filter) and VehicleDetailDTO's `recommendations`
collection (`vin` set to one vehicle).
"""

import sqlite3


def list_recommendations(conn: sqlite3.Connection, vin: str = None, status: str = None) -> list:
    """
    Returns Recommendation rows, each joined with a lightweight Vehicle
    summary (API_CONTRACTS.md's VehicleSummaryDTO fields), same
    INNER-join reasoning as list_tasks -- recommendation.vin carries a
    real FOREIGN KEY to vehicle (migrations/0005_recommendation.sql).

    Ordered by recommendation_id descending, same determinism reasoning
    as list_tasks/recent_activity_feed.
    """
    conditions = []
    params = []
    if vin is not None:
        conditions.append("r.vin = ?")
        params.append(vin)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = conn.execute(
        f"""
        SELECT r.recommendation_id, r.vin, r.severity, r.title, r.detail, r.rule_source,
               r.status, r.resulting_task_id, r.created_at, r.resolved_at,
               v.stock_number, v.display_name, v.year, v.make, v.model
        FROM recommendation r
        JOIN vehicle v ON v.vin = r.vin
        {where_clause}
        ORDER BY r.recommendation_id DESC
        """,
        params,
    ).fetchall()

    columns = [
        "recommendation_id", "vin", "severity", "title", "detail", "rule_source",
        "status", "resulting_task_id", "created_at", "resolved_at",
        "stock_number", "display_name", "year", "make", "model",
    ]
    results = []
    for row in rows:
        record = dict(zip(columns, row))
        vehicle_summary = {
            "vin": record["vin"],
            "stock_number": record.pop("stock_number"),
            "display_name": record.pop("display_name"),
            "year": record.pop("year"),
            "make": record.pop("make"),
            "model": record.pop("model"),
        }
        record["vehicle"] = vehicle_summary
        results.append(record)
    return results
