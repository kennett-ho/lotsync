"""
Phase 2, Slice 7 -- dashboard data layer. See queries/__init__.py for
the module's overall boundary (read-only, no new stored state).

Purpose per IMPLEMENTATION_PLAN.md: validate that everything built in
Slices 1-6 can actually answer the real questions a dashboard needs,
before any web framework, API, or UI investment happens. Every
function here takes an open sqlite3.Connection and returns plain
dict/list data -- no HTTP, no serialization framework, matching the
plan's explicit "Output is inspectable data (dict/JSON-shaped), no HTTP
server."
"""

import sqlite3


def connected_systems_status(conn: sqlite3.Connection) -> dict:
    """
    "Connected Systems" panel (ARCHITECTURE.md's frontend-discovery
    section): per-source last-sync status, timing, and record count --
    a derived view over SyncRun grouped by source, per the already-
    documented decision NOT to build a separate SystemStatus model
    (DATA_MODEL.md, to avoid two sources of truth that can drift).

    Returns {source: {status, started_at, completed_at,
    records_processed}}, one entry per source that has ever run,
    reflecting its MOST RECENT SyncRun. Reads every SyncRun row in
    insertion order and lets a later row for the same source overwrite
    an earlier one in the result dict -- sync_run_id is a true
    autoincrement sequence, so ascending order is exactly chronological
    order, with no separate MAX()/subquery needed.
    """
    rows = conn.execute(
        "SELECT source, status, started_at, completed_at, records_processed "
        "FROM sync_run ORDER BY sync_run_id"
    ).fetchall()
    status_by_source = {}
    for source, status, started_at, completed_at, records_processed in rows:
        status_by_source[source] = {
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at,
            "records_processed": records_processed,
        }
    return status_by_source


def recent_activity_feed(conn: sqlite3.Connection, limit: int = 20) -> list:
    """
    Live-activity-style recent-Events feed (IMPLEMENTATION_PLAN.md
    Slice 7). The most recent `limit` Events across all vehicles,
    newest first -- ordered by event_id (a true autoincrement sequence)
    rather than observed_at (a plain string column with no uniqueness
    or index guarantee), so ties resolve deterministically.

    Returns a list of dicts: event_id, vin, event_type, source,
    summary, observed_at. summary is the Timeline-ready display text
    already produced when the Event was written (ARCHITECTURE.md,
    "Event needed a richer shape") -- this function does not
    reconstruct or reformat it.
    """
    rows = conn.execute(
        "SELECT event_id, vin, event_type, source, summary, observed_at "
        "FROM event ORDER BY event_id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    columns = ["event_id", "vin", "event_type", "source", "summary", "observed_at"]
    return [dict(zip(columns, row)) for row in rows]


def task_counts_by_department(conn: sqlite3.Connection, commitment_standing: str = "outstanding") -> dict:
    """
    Task counts by department (IMPLEMENTATION_PLAN.md Slice 7). Defaults
    to `commitment_standing='outstanding'` -- the natural dashboard
    question is "how much work does each department currently have,"
    not a historical count including already-discharged Tasks; pass a
    different value explicitly if a caller wants that instead.

    Groups by whatever `Task.department` value is actually present,
    including NULL -- returned under the key "Unassigned". This is
    deliberately NOT papered over: Slice 5's auto-generated install
    Tasks never populated `department` (avoiding an unconfirmed
    task-type-to-department mapping invented without real dealership
    input -- see generate_install_tasks' docstring), so an honest
    dashboard reflects that gap as data, rather than this query
    guessing a department on their behalf.
    """
    rows = conn.execute(
        "SELECT department, COUNT(*) FROM task WHERE commitment_standing = ? GROUP BY department",
        (commitment_standing,),
    ).fetchall()
    counts = {}
    for department, count in rows:
        label = department if department is not None else "Unassigned"
        counts[label] = count
    return counts


def inventory_health_percentage(conn: sqlite3.Connection) -> dict:
    """
    Inventory health percentage (IMPLEMENTATION_PLAN.md Slice 7).
    Neither IMPLEMENTATION_PLAN.md nor DATA_MODEL.md defines this term
    precisely -- resolved here as a deliberate, documented
    implementation decision rather than left ambiguous: the percentage
    of currently-known Vehicles with ZERO outstanding Tasks.

    This reuses Task state (Slices 5-6's own output, which already
    reused the existing CSV-report business rules) rather than
    recomputing "is this vehicle okay" a second time from raw
    tekion_status/keyper_status/mdd_status/recovr_status fields --
    doing the latter would duplicate business logic that already lives
    in rules/aging.py, rules/inventory.py, and sync/reconciler.py's
    report-building functions, exactly what every prior slice in this
    sprint was built to avoid.

    Returns {healthy_vehicles, total_vehicles, health_percentage}.
    health_percentage is None (not 0 or 100) when there are no known
    vehicles at all -- a percentage of zero vehicles isn't a
    meaningful health signal either way.
    """
    (total_vehicles,) = conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()
    if total_vehicles == 0:
        return {"healthy_vehicles": 0, "total_vehicles": 0, "health_percentage": None}

    (vehicles_with_outstanding_tasks,) = conn.execute(
        "SELECT COUNT(DISTINCT vin) FROM task WHERE commitment_standing = 'outstanding'"
    ).fetchone()
    healthy_vehicles = total_vehicles - vehicles_with_outstanding_tasks
    return {
        "healthy_vehicles": healthy_vehicles,
        "total_vehicles": total_vehicles,
        "health_percentage": round(100.0 * healthy_vehicles / total_vehicles, 2),
    }
