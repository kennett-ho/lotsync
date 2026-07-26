"""
Minimal repository layer for Phase 2, Slice 1 -- a migration runner
plus upsert/insert functions. Deliberately thin: no ORM, no query
helpers beyond what Slice 1 needs writing data, applying the same
"no speculative schema" discipline to code as IMPLEMENTATION_PLAN.md
applies to the schema itself. Reading this data back for dashboard-
shaped questions is Slice 7's concern (a future queries/ module), not
this one's.
"""

import contextlib
import datetime
import glob
import json
import os
import sqlite3

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")

# Overridable via LOTSYNC_DB_PATH; defaults to a repo-relative location,
# same convention as config/settings.py and utils/file_resolution.py.
DEFAULT_DB_PATH = os.environ.get("LOTSYNC_DB_PATH", os.path.join(_REPO_ROOT, "data", "lotsync.db"))


def _pending_migrations(conn, migrations_dir):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    pending = []
    for path in sorted(glob.glob(os.path.join(migrations_dir, "*.sql"))):
        version = int(os.path.basename(path).split("_", 1)[0])
        if version not in applied:
            pending.append((version, path))
    return pending


def apply_migrations(conn, migrations_dir: str = _MIGRATIONS_DIR):
    """
    Applies any not-yet-applied numbered .sql files in migrations_dir,
    in order, recording each in schema_migrations so re-running this
    is a no-op. See IMPLEMENTATION_PLAN.md's Migration Strategy risk
    note for why numbered files were chosen from day one.
    """
    for version, path in _pending_migrations(conn, migrations_dir):
        with open(path, "r") as fh:
            conn.executescript(fh.read())
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, datetime.datetime.now().isoformat()),
        )
    conn.commit()


def connect(db_path: str = None) -> sqlite3.Connection:
    """
    Opens a SQLite connection and ensures all migrations are applied
    before returning it -- the only entry point that should be used to
    get a LotSync database connection, so schema is always current.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    apply_migrations(conn)
    return conn


def upsert_vehicle(conn: sqlite3.Connection, vin: str, **fields):
    """
    Partial upsert -- only the columns passed in `fields` are set or
    updated; any other column already on the row is left untouched.
    This is what lets Slice 1 (Keyper only) and later slices (Tekion,
    MDD, RecovR, RapidRecon) each update their own slice of a Vehicle
    row without clobbering what another source already wrote -- see
    ARCHITECTURE.md, "Why Vehicle is meant to be the core object."

    Does NOT commit (Slice 1-3 behavior; changed in Slice 4) -- the
    caller is responsible for committing once its whole batch of writes
    succeeds, or rolling back on failure. See sync_run() below for why:
    a SyncRun's "complete"/"failed" status is only meaningful if a
    single transaction spans everything that source wrote this run.
    """
    if not fields:
        conn.execute("INSERT OR IGNORE INTO vehicle (vin) VALUES (?)", (vin,))
        return

    columns = list(fields.keys())
    insert_cols = ", ".join(["vin"] + columns)
    placeholders = ", ".join(["?"] * (len(columns) + 1))
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in columns)

    conn.execute(
        f"INSERT INTO vehicle ({insert_cols}) VALUES ({placeholders}) "
        f"ON CONFLICT(vin) DO UPDATE SET {update_clause}",
        [vin] + [fields[c] for c in columns],
    )


def get_last_event_detail_fields(conn: sqlite3.Connection, vin: str, event_type: str):
    """
    Returns the detail_fields dict of the most recently written Event
    for this (vin, event_type), or None if none exists yet -- the
    correct basis for Slice 3's diff-before-write decision. NOT
    vehicle's current-state field: that field is a plain cache that can
    be overwritten within the same run by a sibling observation writing
    the same field (e.g. Tekion's master-list and sold-list writes both
    target tekion_status -- see reconciler.py's persist_tekion_observations
    docstring for the idempotency bug this caused when diffing was
    compared against the cache instead). Comparing against the last
    matching Event keeps each distinct kind of claim compared against
    its own history, independent of whatever else touched the shared
    cache in between.
    """
    row = conn.execute(
        "SELECT detail_fields FROM event WHERE vin = ? AND event_type = ? "
        "ORDER BY event_id DESC LIMIT 1",
        (vin, event_type),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return json.loads(row[0])


def get_pending_identity(conn: sqlite3.Connection, source: str, raw_identifier: str):
    """
    Looks up a pending_identity row by its upsert key. Returns a dict of
    its columns, or None if no such row exists. Used by Slice 3's
    promotion logic to check whether a Keyper identifier that just
    resolved was previously sitting unresolved -- see
    resolve_pending_identity below and DATA_MODEL.md's PendingIdentity
    entry ("Resolution is explicitly out of scope for this model's
    introduction... belongs alongside Slice 3").
    """
    row = conn.execute(
        "SELECT pending_identity_id, source, raw_identifier, identifier_type, status, "
        "first_observed_at, last_observed_at, resolved_vin, resolved_at "
        "FROM pending_identity WHERE source = ? AND raw_identifier = ?",
        (source, raw_identifier),
    ).fetchone()
    if row is None:
        return None
    columns = ["pending_identity_id", "source", "raw_identifier", "identifier_type", "status",
               "first_observed_at", "last_observed_at", "resolved_vin", "resolved_at"]
    return dict(zip(columns, row))


def resolve_pending_identity(conn: sqlite3.Connection, source: str, raw_identifier: str,
                              resolved_vin: str, resolved_at: str = None):
    """
    Marks a pending_identity row resolved -- the first genuine state
    transition in the system (DATA_MODEL.md, IMPLEMENTATION_PLAN.md
    Slice 3). Only ever moves a row from 'pending' to 'resolved'; the
    WHERE clause's status = 'pending' guard means calling this twice for
    the same identifier (e.g. if it were ever mistakenly called again)
    is a harmless no-op on the second call, not a second transition --
    consistent with DECISION_FRAMEWORK.md's "history is immutable"
    principle: resolution happens once, and re-observing an
    already-resolved identifier is not a new fact.

    Caller is responsible for upserting the Vehicle row first -- by the
    time this runs, resolved_vin must already reference a real Vehicle
    (see migrations/0002_pending_identity.sql's comment on why
    resolved_vin has no FK constraint declared).

    Does NOT commit -- see upsert_vehicle's docstring; Slice 4 moved
    commit responsibility to the caller's whole-batch boundary.
    """
    if resolved_at is None:
        resolved_at = datetime.datetime.now().isoformat()
    conn.execute(
        "UPDATE pending_identity SET status = 'resolved', resolved_vin = ?, resolved_at = ? "
        "WHERE source = ? AND raw_identifier = ? AND status = 'pending'",
        (resolved_vin, resolved_at, source, raw_identifier),
    )


def upsert_pending_identity(conn: sqlite3.Connection, source: str, raw_identifier: str,
                             identifier_type: str, observed_at: str = None):
    """
    Records (or re-records) an observation that couldn't be resolved to
    a VIN -- see DATA_MODEL.md's PendingIdentity entry and
    database/migrations/0002_pending_identity.sql. Keyed by
    (source, raw_identifier), NOT insert-every-run like insert_event:
    the same still-unresolved key observed on a later sync updates
    last_observed_at on the existing row rather than creating a second
    row for the same physical item. first_observed_at is set only once,
    on the row's first insert -- SQLite's ON CONFLICT DO UPDATE simply
    omits it from the update clause, so it's untouched on repeat calls.

    Does NOT commit -- see upsert_vehicle's docstring; Slice 4 moved
    commit responsibility to the caller's whole-batch boundary.
    """
    if observed_at is None:
        observed_at = datetime.datetime.now().isoformat()
    conn.execute(
        "INSERT INTO pending_identity "
        "(source, raw_identifier, identifier_type, status, first_observed_at, last_observed_at) "
        "VALUES (?, ?, ?, 'pending', ?, ?) "
        "ON CONFLICT(source, raw_identifier) DO UPDATE SET "
        "last_observed_at = excluded.last_observed_at, "
        "identifier_type = excluded.identifier_type",
        (source, raw_identifier, identifier_type, observed_at, observed_at),
    )


def insert_event(conn: sqlite3.Connection, vin: str, event_type: str, source: str,
                  observed_at: str = None, summary: str = None, detail_fields: dict = None,
                  sync_run_id: str = None, actor_employee_id: str = None,
                  dealership_id: str = None) -> int:
    """
    Always inserts a new row -- diff-before-write (whether an Event
    should be written at all) is the caller's decision, made in
    sync/reconciler.py before calling this (see IMPLEMENTATION_PLAN.md
    Slice 3).

    Does NOT commit -- see upsert_vehicle's docstring; Slice 4 moved
    commit responsibility to the caller's whole-batch boundary.
    """
    if observed_at is None:
        observed_at = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO event (vin, event_type, source, sync_run_id, actor_employee_id, "
        "dealership_id, observed_at, summary, detail_fields) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (vin, event_type, source, sync_run_id, actor_employee_id, dealership_id,
         observed_at, summary, json.dumps(detail_fields) if detail_fields is not None else None),
    )
    return cur.lastrowid


def start_sync_run(conn: sqlite3.Connection, source: str, dealership_id: str = None,
                    started_at: str = None) -> int:
    """
    Creates a SyncRun row with status='in_progress' and commits it
    immediately -- this row's existence must be durable the moment a
    source's processing begins, independent of whatever that source's
    writes go on to do (see sync_run() below). Returns the new
    sync_run_id.

    Note for anyone comparing this value against event.sync_run_id in
    Python: event.sync_run_id is a TEXT-affinity column (unchanged since
    Slice 1, to preserve the free-form string sync_run_id convention
    Slices 1-3's tests already rely on), while this table's sync_run_id
    is a real INTEGER PK. SQLite's own type-affinity rules correctly
    treat "1" and 1 as equal inside a query, but a Python-side set of
    one column's values will NOT equal a Python-side set of the other's
    -- always compare via SQL (e.g. `... NOT IN (SELECT sync_run_id
    FROM sync_run)`), not by pulling both into Python first. See
    tests/test_database_slice4.py's orphan-check test for a worked
    example of this exact pitfall.
    """
    if started_at is None:
        started_at = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO sync_run (source, dealership_id, started_at, status) "
        "VALUES (?, ?, ?, 'in_progress')",
        (source, dealership_id, started_at),
    )
    conn.commit()
    return cur.lastrowid


def complete_sync_run(conn: sqlite3.Connection, sync_run_id: int,
                       records_processed: int = None, completed_at: str = None):
    """
    Marks a SyncRun 'complete' and commits -- called by sync_run() only
    after the source's own writes are already pending in this same,
    still-open transaction, so this single commit() durably persists
    BOTH that source's writes AND this status update together. See
    sync_run()'s docstring for the transactional contract this depends on.
    """
    if completed_at is None:
        completed_at = datetime.datetime.now().isoformat()
    conn.execute(
        "UPDATE sync_run SET status = 'complete', completed_at = ?, records_processed = ? "
        "WHERE sync_run_id = ?",
        (completed_at, records_processed, sync_run_id),
    )
    conn.commit()


def fail_sync_run(conn: sqlite3.Connection, sync_run_id: int, completed_at: str = None):
    """
    Marks a SyncRun 'failed' and commits. Called by sync_run() only
    AFTER conn.rollback() has already discarded that source's own
    pending writes -- so this commit only ever persists the failure
    marker itself, never any of the failed attempt's partial writes.
    """
    if completed_at is None:
        completed_at = datetime.datetime.now().isoformat()
    conn.execute(
        "UPDATE sync_run SET status = 'failed', completed_at = ? WHERE sync_run_id = ?",
        (completed_at, sync_run_id),
    )
    conn.commit()


@contextlib.contextmanager
def sync_run(conn: sqlite3.Connection, source: str, records_processed: int = None,
              dealership_id: str = None):
    """
    Wraps one source's persistence pass in a real transaction, per the
    Sprint 3 kickoff decision to give SyncRun a clean semantic contract:
    'complete' means every write this source made during this run
    committed successfully; 'failed' means NONE of them did -- never a
    partially-committed run wearing either label. This is why
    upsert_vehicle/insert_event/upsert_pending_identity/
    resolve_pending_identity stopped committing individually as of this
    slice -- a SyncRun's transaction boundary has to span all of a
    source's writes for this contract to hold.

    Usage:
        with sync_run(db_conn, "recovr", records_processed=len(recovr_df)) as run_id:
            persist_recovr_observations(recovr_df, db_conn=db_conn, sync_run_id=run_id)

    On success: commits everything the block wrote, then marks the
    SyncRun 'complete'. On any exception: rolls back everything the
    block wrote (so nothing from the failed attempt persists), marks
    the SyncRun 'failed', then re-raises -- this slice only strengthens
    the transactional/provenance guarantee, it doesn't change whether a
    write failure should stop the pipeline (an orthogonal question, not
    part of Slice 4's scope; see SPRINT_3_REVIEW.md).
    """
    sync_run_id = start_sync_run(conn, source=source, dealership_id=dealership_id)
    try:
        yield sync_run_id
    except Exception:
        conn.rollback()
        fail_sync_run(conn, sync_run_id)
        raise
    else:
        conn.commit()
        complete_sync_run(conn, sync_run_id, records_processed=records_processed)
