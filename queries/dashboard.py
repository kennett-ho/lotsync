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

import json
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
    reflecting its MOST RECENT SyncRun (sync_run_id is a true
    autoincrement sequence, so max id per source is exactly its latest
    run).

    Sprint 14 (Rail J): this used to read EVERY sync_run row and reduce
    in Python -- linear, unbounded growth on a hot path (/dashboard AND
    every /vehicles/{vin} call), measured at +6 ms per request by 5,000
    rows locally and worse over a network pooler. The aggregation now
    happens in SQL, so the transferred row count is bounded by the
    number of distinct sources regardless of history depth. Result
    keys keep the previous insertion order (each source's FIRST-ever
    run) so no consumer sees a reordered dict.
    """
    rows = conn.execute(
        "SELECT s.source, s.status, s.started_at, s.completed_at, s.records_processed "
        "FROM sync_run s "
        "JOIN (SELECT source, MAX(sync_run_id) AS latest_id, MIN(sync_run_id) AS first_id "
        "      FROM sync_run GROUP BY source) latest "
        "  ON latest.latest_id = s.sync_run_id "
        "ORDER BY latest.first_id"
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


def recent_activity_feed(conn: sqlite3.Connection, limit: int = 20, vin: str = None) -> list:
    """
    Live-activity-style recent-Events feed (IMPLEMENTATION_PLAN.md
    Slice 7). The most recent `limit` Events, newest first -- ordered
    by event_id (a true autoincrement sequence) rather than
    observed_at (a plain string column with no uniqueness or index
    guarantee), so ties resolve deterministically.

    Returns a list of dicts: event_id, vin, event_type, source,
    sync_run_id, actor_employee_id, dealership_id, observed_at,
    event_time (Sprint 3.7 addition -- the source's own claimed
    timestamp, nullable; see DATA_MODEL.md's Event entry and
    sync/reconciler.py's persist_* functions for which events populate
    it), summary,
    detail_fields (parsed back from JSON, same as
    database/repository.py's get_last_event_detail_fields already
    does -- never left as a raw JSON string), plus a nested `vehicle`
    summary (vin, stock_number, display_name, year, make, model). summary is the
    Timeline-ready display text already produced when the Event was
    written (ARCHITECTURE.md, "Event needed a richer shape") -- this
    function does not reconstruct or reformat it.

    Extended during Phase 3, Sprint 2 to select every Event column (the
    original Slice 7 version selected only six) and embed a Vehicle
    summary -- API_CONTRACTS.md's ActivityDTO explicitly wants the
    vehicle embedded specifically for this global feed, "since the
    whole point of this screen is seeing activity across vehicles."
    Purely additive relative to Slice 7's original shape -- every
    pre-existing key is unchanged, only new keys were added -- so every
    existing caller and test continues to work unmodified. The INNER
    join to `vehicle` is safe because event.vin carries a real FOREIGN
    KEY to vehicle (migrations/0001_initial.sql).

    `vin` is an optional filter, added the same sprint so
    `VehicleDetailDTO`'s Timeline (API_CONTRACTS.md) reuses this exact
    function scoped to one vehicle, instead of a second, near-duplicate
    query living in queries/vehicles.py -- the global Activity screen
    (vin=None, the original and still-default behavior) and a single
    vehicle's Timeline are the same question at a different scope, not
    two different questions.
    """
    base_query = (
        "SELECT e.event_id, e.vin, e.event_type, e.source, e.sync_run_id, "
        "e.actor_employee_id, e.dealership_id, e.observed_at, e.event_time, e.summary, e.detail_fields, "
        "v.stock_number, v.display_name, v.year, v.make, v.model "
        "FROM event e JOIN vehicle v ON v.vin = e.vin "
    )
    if vin is None:
        rows = conn.execute(
            base_query + "ORDER BY e.event_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    else:
        rows = conn.execute(
            base_query + "WHERE e.vin = ? ORDER BY e.event_id DESC LIMIT ?",
            (vin, limit),
        ).fetchall()

    columns = [
        "event_id", "vin", "event_type", "source", "sync_run_id",
        "actor_employee_id", "dealership_id", "observed_at", "event_time", "summary", "detail_fields",
        "stock_number", "display_name", "year", "make", "model",
    ]
    results = []
    for row in rows:
        record = dict(zip(columns, row))
        record["detail_fields"] = json.loads(record["detail_fields"]) if record["detail_fields"] else None
        record["vehicle"] = {
            "vin": record["vin"],
            "stock_number": record.pop("stock_number"),
            "display_name": record.pop("display_name"),
            "year": record.pop("year"),
            "make": record.pop("make"),
            "model": record.pop("model"),
        }
        results.append(record)
    return results


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
