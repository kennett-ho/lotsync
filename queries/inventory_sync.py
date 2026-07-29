"""
Phase 3, Sprint 4 -- read models for the Inventory Sync page. Same
"read-only, no new stored state" discipline as queries/dashboard.py: both
functions here select from tables Phase 2/Sprint 4 already write
(`pending_identity`, `sync_run`), nothing new is computed and stored.
"""

import sqlite3


def list_pending_identities(conn: sqlite3.Connection, status: str = "pending") -> list:
    """
    The Inventory Sync page's Exceptions panel data source -- real,
    persisted PendingIdentity rows (already written by
    reconcile_keyper_tekion's unresolved-identity branches), not the
    frontend mockup's fabricated assignable-workflow shape. Matches
    API_CONTRACTS.md's PendingIdentityDTO field-for-field.
    """
    rows = conn.execute(
        "SELECT pending_identity_id, source, raw_identifier, identifier_type, status, "
        "first_observed_at, last_observed_at, resolved_vin, resolved_at "
        "FROM pending_identity WHERE status = ? ORDER BY pending_identity_id DESC",
        (status,),
    ).fetchall()
    columns = ["pending_identity_id", "source", "raw_identifier", "identifier_type", "status",
               "first_observed_at", "last_observed_at", "resolved_vin", "resolved_at"]
    return [dict(zip(columns, row)) for row in rows]


def sync_run_history(conn: sqlite3.Connection, limit: int = 20) -> list:
    """
    Groups `sync_run` rows into "sync batches" by shared `started_at` --
    sync/pipeline.py's run_inventory_sync stamps every source it
    processes in one request with the same started_at value (via
    sync_run()'s Sprint-4 started_at passthrough), so "which SyncRun rows
    belong to the same sync request" is a derived read, not a stored
    batch_id (DATA_MODEL.md's SyncRun stays exactly as documented --
    "one execution of the pipeline against one source").

    Returns, newest batch first: [{started_at, overall_status,
    sources: [{sync_run_id, source, status, records_processed}, ...]}].
    overall_status is "failed" if any source in the batch failed, else
    "in_progress" if any is still running, else "complete" -- the same
    "worst status wins" reasoning a person scanning a run list would
    apply by eye.

    Deliberately does NOT reconstruct per-batch exception/task/
    recommendation counts -- no column ties a `task`/`recommendation` row
    back to the sync_run/batch that produced it (generate_install_tasks
    and generate_key_out_aging_recommendations are derived computations,
    not per-source imports -- see their own docstrings in
    sync/reconciler.py for why they're deliberately not wrapped in
    sync_run()). Only the just-completed run's own response
    (SyncSummaryDTO, returned directly by POST /inventory-sync/run) carries
    that full summary; history entries show what's reliably derivable
    from `sync_run` alone. Stated here plainly rather than approximated.
    """
    rows = conn.execute(
        "SELECT sync_run_id, source, status, started_at, completed_at, records_processed "
        "FROM sync_run ORDER BY sync_run_id DESC"
    ).fetchall()

    batches = {}
    order = []
    for sync_run_id, source, status, started_at, completed_at, records_processed in rows:
        if started_at not in batches:
            batches[started_at] = []
            order.append(started_at)
        batches[started_at].append({
            "sync_run_id": sync_run_id, "source": source, "status": status,
            "started_at": started_at, "completed_at": completed_at,
            "records_processed": records_processed,
        })

    def _overall_status(sources: list) -> str:
        statuses = {s["status"] for s in sources}
        if "failed" in statuses:
            return "failed"
        if "in_progress" in statuses:
            return "in_progress"
        return "complete"

    result = []
    for started_at in order[:limit]:
        sources = batches[started_at]
        result.append({
            "started_at": started_at,
            "overall_status": _overall_status(sources),
            "sources": sources,
        })
    return result
