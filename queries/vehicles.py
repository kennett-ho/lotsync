"""
Phase 3, Sprint 2 -- Vehicle reads. Same module boundary as
queries/dashboard.py. Two functions:

list_vehicles() -- the Vehicles List screen's data, matching
API_CONTRACTS.md's VehicleDTO shape (a flat per-vehicle summary plus
one computed field, open_task_count).

get_vehicle_detail() -- the single-Vehicle aggregate matching
API_CONTRACTS.md's VehicleDetailDTO, and this sprint's own named
reference implementation for how a detail page is assembled: it calls
list_tasks()/list_recommendations()/recent_activity_feed()/
connected_systems_status() directly, each already scoped or already
generic enough to answer this question, rather than writing a second,
vehicle-detail-specific version of any of them. This is deliberate --
see PHASE_3_SPRINT_2_REVIEW.md's Architecture Review for why "without
duplicating queries" was treated as a hard constraint here, not a
suggestion.
"""

import sqlite3

from lotsync.queries.dashboard import connected_systems_status, recent_activity_feed
from lotsync.queries.tasks import list_tasks
from lotsync.queries.recommendations import list_recommendations

_VEHICLE_COLUMNS = [
    "vin", "stock_number", "display_name", "year", "make", "model", "new_or_used",
    "current_dealership_id", "tekion_status", "keyper_status",
    "mdd_status", "recovr_status", "inventory_state",
]

# get_vehicle_detail's Timeline is scoped to one vehicle, whose event
# volume is a small fraction of the whole-fixture totals Slice 7
# already validated (3,000 vehicles / 12,000 events, sub-second) -- a
# generous ceiling here is effectively "no limit" for any one vehicle
# without changing recent_activity_feed's existing numeric-limit
# contract.
_VEHICLE_DETAIL_TIMELINE_LIMIT = 10000


def list_vehicles(conn: sqlite3.Connection, include_sold: bool = False) -> list:
    """
    Returns every known Vehicle, each with a computed `open_task_count`
    (the count of its outstanding Tasks) -- the same
    commitment_standing = 'outstanding' semantics
    queries/dashboard.py's inventory_health_percentage() already uses,
    exposed here per-vehicle instead of aggregated across all vehicles.

    No search/status filtering beyond include_sold is implemented here.
    Per API_CONTRACTS.md's Section 9 (Open Question #10), there is no
    canonical, backend-computed Vehicle operational-status enum yet --
    only the four flat per-source status fields plus the unpopulated
    `inventory_state` placeholder -- so there is nothing honest to
    filter server-side by "status" today. Search/filtering the frontend
    currently does client-side stays a client-side concern until that
    enum is actually designed.

    include_sold (default False): the default Vehicles List is the
    lot's active/scrolling inventory, not the full historical roster --
    a sold vehicle isn't gone, but it isn't something a lot attendant
    scrolls past every day either. Sold is identified by
    `tekion_status = 'Sold'`, the exact value
    persist_tekion_observations writes for a VIN present in Tekion's
    sold export (see sync/reconciler.py) -- the same field this
    codebase already treats as the authoritative current-state cache
    elsewhere, not a new status concept invented here. Filtered with
    `IS NOT 'Sold'` rather than `!= 'Sold'` so a vehicle with no Tekion
    record at all (`tekion_status IS NULL` -- e.g. RecovR/Keyper-only
    matches) is correctly treated as not-known-sold and still shown by
    default, instead of `!=`'s NULL-comparison silently dropping it.
    A sold vehicle is never deleted and stays fully reachable -- by
    direct VIN via get_vehicle_detail (unaffected by this filter), and
    in this same list whenever a caller passes include_sold=True -- see
    api/routers/vehicles.py's `include_sold` query param.
    """
    # Sprint 03: `IS DISTINCT FROM` replaces the original SQLite-only
    # `IS NOT 'Sold'` -- identical NULL-safe semantics (a vehicle with
    # no Tekion record at all still shows by default; see the docstring
    # above), in syntax both SQLite (3.39+) and PostgreSQL support.
    sold_filter = "" if include_sold else "WHERE v.tekion_status IS DISTINCT FROM 'Sold'"
    rows = conn.execute(
        f"""
        SELECT v.vin, v.stock_number, v.display_name, v.year, v.make, v.model, v.new_or_used,
               v.current_dealership_id, v.tekion_status, v.keyper_status,
               v.mdd_status, v.recovr_status, v.inventory_state,
               (SELECT COUNT(*) FROM task t
                WHERE t.vin = v.vin AND t.commitment_standing = 'outstanding') AS open_task_count
        FROM vehicle v
        {sold_filter}
        ORDER BY v.vin
        """
    ).fetchall()
    columns = _VEHICLE_COLUMNS + ["open_task_count"]
    return [dict(zip(columns, row)) for row in rows]


def get_vehicle_detail(conn: sqlite3.Connection, vin: str) -> dict:
    """
    Returns the single-Vehicle aggregate matching API_CONTRACTS.md's
    VehicleDetailDTO, or None if no Vehicle with this vin exists (the
    api/ layer is responsible for turning that into a 404, not this
    function -- this module stays HTTP-agnostic like every other
    queries/ module).

    `tasks`/`recommendations`/`timeline` entries each carry a nested
    `vehicle` sub-dict from their originating query (list_tasks/
    list_recommendations always embed one; recent_activity_feed's rows
    don't -- see below) -- the api/ layer, not this function, decides
    whether to keep or drop that nested vehicle reference when
    assembling VehicleDetailDTO (API_CONTRACTS.md documents it as
    omitted/null there, since it's redundant with the Vehicle this
    whole response is already about). This function returns the
    complete, undecorated data; presentation-level trimming belongs to
    the DTO layer, not the query layer.

    `connected_systems` reuses connected_systems_status() exactly as
    global, unfiltered per-source status -- API_CONTRACTS.md's own note
    on this: it's "not vehicle-owned, contextualized per vehicle," i.e.
    there is no separate per-vehicle sync status to compute.
    """
    row = conn.execute(
        f"SELECT {', '.join(_VEHICLE_COLUMNS)} FROM vehicle WHERE vin = ?",
        (vin,),
    ).fetchone()
    if row is None:
        return None

    vehicle = dict(zip(_VEHICLE_COLUMNS, row))
    (open_task_count,) = conn.execute(
        "SELECT COUNT(*) FROM task WHERE vin = ? AND commitment_standing = 'outstanding'",
        (vin,),
    ).fetchone()
    vehicle["open_task_count"] = open_task_count

    return {
        **vehicle,
        "tasks": list_tasks(conn, vin=vin),
        "recommendations": list_recommendations(conn, vin=vin),
        "timeline": recent_activity_feed(conn, vin=vin, limit=_VEHICLE_DETAIL_TIMELINE_LIMIT),
        "connected_systems": connected_systems_status(conn),
    }
