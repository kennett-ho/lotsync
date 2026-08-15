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

from lotsync.database import engine as db_engine

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "migrations")
# Sprint 03: the PostgreSQL dialect of the same 8 numbered migrations
# (identical intent/ordering; only dialect-required syntax differs --
# see database/migrations_postgres/README note in each file header).
_MIGRATIONS_DIR_POSTGRES = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "migrations_postgres"
)

# Engine-neutral integrity-violation exception surface (Sprint 03) --
# sqlite3 raises sqlite3.IntegrityError, psycopg raises its own
# IntegrityError subclass; callers/tests asserting on constraint
# violations should catch THIS, not either driver's class directly.
try:  # pragma: no cover - psycopg present in dev/CI, absent nowhere we test
    import psycopg as _psycopg

    IntegrityError = (sqlite3.IntegrityError, _psycopg.IntegrityError)
except ImportError:  # pragma: no cover
    IntegrityError = sqlite3.IntegrityError

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

    check_same_thread=False, added during Phase 3, Sprint 2: FastAPI's
    request-handling model (api/dependencies.py's get_db) can execute a
    sync route's dependency-and-handler chain on a worker-pool thread
    different from wherever the caller happens to be, and this
    project's own tests override that same dependency with a single
    shared connection across several TestClient calls within one test
    (see tests/test_api_routes.py) -- both are "used on a different
    thread than it was created on, sequentially," never two threads
    touching the same connection at the same instant. sqlite3's
    same-thread check guards against genuine concurrent access, which
    this doesn't introduce (every real request still opens and closes
    its own connection, per get_db's generator) -- it otherwise just
    rejects a safe, sequential handoff. No behavior changes for any
    existing single-threaded caller (main.py, every test in this
    project through Phase 2) -- this flag is a no-op until something
    actually crosses a thread boundary.
    """
    # Sprint 03: engine dispatch. Explicit configuration only --
    # DATABASE_ENGINE=postgres opts in (DealerDOH DEV); everything
    # else, including production, takes the unchanged SQLite path
    # below. The returned object satisfies the same connection
    # contract either way (execute with `?` placeholders, tuple rows,
    # commit/rollback/close), so no caller changes.
    if db_engine.get_engine() == "postgres":
        conn = db_engine.connect_postgres(db_path)
        if db_path == ":memory:":
            # Fresh private schema (test isolation): always migrate.
            apply_migrations(conn, _MIGRATIONS_DIR_POSTGRES)
        elif not db_engine.runtime_migrations_verified():
            # Runtime database: verify/apply once per process, not on
            # every pooled per-request connection.
            apply_migrations(conn, _MIGRATIONS_DIR_POSTGRES)
            db_engine.mark_runtime_migrations_verified()
        return conn

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    dirname = os.path.dirname(db_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
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
        # Sprint 03: was SQLite's `INSERT OR IGNORE`; `ON CONFLICT DO
        # NOTHING` is the same semantics in syntax both engines share.
        conn.execute("INSERT INTO vehicle (vin) VALUES (?) ON CONFLICT (vin) DO NOTHING", (vin,))
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


def upsert_event_freshness(conn: sqlite3.Connection, vin: str, event_type: str, source: str,
                            sync_run_id: str = None, observed_at: str = None):
    """
    Sprint 3.7 addition -- records "as of when was (vin, event_type)
    last reconfirmed," independent of whether that reconfirmation wrote
    a new Event. See migrations/0008_event_fidelity.sql for why this
    table exists: without it, a source's diff-before-write correctly
    suppressing a repeated identical observation also silently erases
    the only record that the observation happened at all, which is a
    real audit-capability loss, not just an unrecorded formality --
    "how long has it actually been since RapidRecon last confirmed this
    vehicle is still WHOLESALE" becomes unanswerable per vehicle.

    Deliberately a plain upsert (mutable), not an insert -- this is
    current-state metadata sitting next to history, not part of it
    (DECISION_FRAMEWORK.md's "current state is always a derived read"
    category). Call this on every observation, whether or not it
    resulted in a new Event -- see
    sync/reconciler.py's _insert_event_if_changed, the one intended
    caller.

    Does NOT commit -- same whole-batch-transaction convention as
    upsert_vehicle/insert_event.
    """
    if observed_at is None:
        observed_at = datetime.datetime.now().isoformat()
    # str() on sync_run_id: same TEXT-column reasoning as insert_event.
    conn.execute(
        "INSERT INTO event_freshness (vin, event_type, source, last_observed_at, last_sync_run_id) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(vin, event_type) DO UPDATE SET "
        "source = excluded.source, last_observed_at = excluded.last_observed_at, "
        "last_sync_run_id = excluded.last_sync_run_id",
        (vin, event_type, source, observed_at,
         str(sync_run_id) if sync_run_id is not None else None),
    )


def get_event_freshness(conn: sqlite3.Connection, vin: str, event_type: str):
    """
    Returns {"source", "last_observed_at", "last_sync_run_id"} for this
    (vin, event_type), or None if it's never been observed. Read-side
    counterpart to upsert_event_freshness above -- not yet wired into
    any API route or report this sprint (no demonstrated UI need for it
    yet, per DECISION_FRAMEWORK.md's "don't build ahead of a
    demonstrated workflow"); exists so the data this sprint starts
    recording is actually queryable, not stranded.
    """
    row = conn.execute(
        "SELECT source, last_observed_at, last_sync_run_id FROM event_freshness "
        "WHERE vin = ? AND event_type = ?",
        (vin, event_type),
    ).fetchone()
    if row is None:
        return None
    return {"source": row[0], "last_observed_at": row[1], "last_sync_run_id": row[2]}


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
                  dealership_id: str = None, event_time: str = None) -> int:
    """
    Always inserts a new row -- diff-before-write (whether an Event
    should be written at all) is the caller's decision, made in
    sync/reconciler.py before calling this (see IMPLEMENTATION_PLAN.md
    Slice 3).

    event_time (Sprint 3.7 addition) vs. observed_at: two deliberately
    separate concepts, not one field doing double duty. observed_at is
    unchanged -- always populated, always "when LotSync's sync learned
    about this" (the audit trail). event_time is the source's own
    claimed timestamp for when the thing actually happened, and stays
    NULL when no source provided one with a confirmed meaning -- see
    migrations/0008_event_fidelity.sql and each persist_* function in
    sync/reconciler.py for exactly which events populate it and why.
    Never inferred or guessed here -- this function just stores
    whatever the caller already decided.

    Does NOT commit -- see upsert_vehicle's docstring; Slice 4 moved
    commit responsibility to the caller's whole-batch boundary.
    """
    if observed_at is None:
        observed_at = datetime.datetime.now().isoformat()
    # sync_run_id lands in a TEXT column (the opaque provenance tag --
    # see start_sync_run's docstring). SQLite's TEXT affinity was
    # already storing integer run ids as their string form ('5', not
    # 5); the explicit str() makes that same result engine-independent
    # instead of relying on SQLite's implicit coercion (PostgreSQL
    # refuses an integer parameter for a text column outright).
    cur = conn.execute(
        "INSERT INTO event (vin, event_type, source, sync_run_id, actor_employee_id, "
        "dealership_id, observed_at, summary, detail_fields, event_time) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING event_id",
        (vin, event_type, source, str(sync_run_id) if sync_run_id is not None else None,
         actor_employee_id, dealership_id,
         observed_at, summary, json.dumps(detail_fields) if detail_fields is not None else None,
         event_time),
    )
    return cur.fetchone()[0]


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
        "VALUES (?, ?, ?, 'in_progress') RETURNING sync_run_id",
        (source, dealership_id, started_at),
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


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
              dealership_id: str = None, started_at: str = None):
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

    started_at (Phase 3, Sprint 4 addition): optional passthrough to
    start_sync_run, which already accepted this parameter -- this wrapper
    just didn't expose it. Lets a multi-source caller (sync/pipeline.py's
    run_inventory_sync) stamp every source's SyncRun in one request with
    the same timestamp, so "which SyncRun rows belong to the same sync
    request" is answerable as a derived read (group by started_at)
    without a new batch_id column -- see DATA_MODEL.md's SyncRun entry,
    unchanged by this. Omitted (None), this is byte-for-byte the same
    default behavior every existing caller (main.py, every prior test)
    already gets.
    """
    sync_run_id = start_sync_run(conn, source=source, dealership_id=dealership_id,
                                  started_at=started_at)
    try:
        yield sync_run_id
    except Exception:
        conn.rollback()
        fail_sync_run(conn, sync_run_id)
        raise
    else:
        conn.commit()
        complete_sync_run(conn, sync_run_id, records_processed=records_processed)


# ---------------------------------------------------------------------------
# Phase 2, Sprint 4 (Slice 5) -- Task / TaskExecutionEvent.
#
# See DATA_MODEL.md's Task and TaskExecutionEvent entries,
# DECISION_FRAMEWORK.md's "Ontology, Architecture, Invariants, and
# Reasoning Tools" section, and SPRINT_4_CHECKLIST.md for the full
# reasoning behind this shape. Summary: commitment_standing and
# execution_status are independent axes -- a Task's discharge (Reality:
# honored/moot; Intent: cancelled/superseded) is a separate question
# from its execution progress (an append-only log in
# task_execution_event, cached onto task.execution_status).
# ---------------------------------------------------------------------------

_EXECUTION_STATUS_BY_TRANSITION = {
    "started": "in_progress",
    "resumed": "in_progress",
    "blocked": "blocked",
    "completed": "completed",
}


def insert_task(conn: sqlite3.Connection, vin: str, task_type: str, dealership_id: str = None,
                 department: str = None, priority: str = None, reason: str = None,
                 created_at: str = None, ratified_by: str = None, ratification_type: str = None) -> int:
    """
    Creates a new Task, always `commitment_standing='outstanding'` and
    `execution_status='not_started'` (the migration's column defaults --
    not passed explicitly here, so there's exactly one place, the
    schema, that says what a brand-new Task's starting state is).
    Callers deciding whether a Task is even needed (e.g. "is there
    already an outstanding install_recovr_device Task for this VIN?")
    must check get_open_task() themselves first -- this function always
    inserts, the same "caller decides, this just writes" division of
    responsibility as insert_event.

    ratified_by/ratification_type are optional here (Slice 6 addition):
    an auto-generated install Task (Slice 5) has no ratification at
    creation -- nobody decided it should exist, the reconciliation
    engine just observed a gap and recorded it -- so those stay NULL by
    default, same as before. A Task created by converting a
    Recommendation DOES have ratification at creation time (a human
    reviewed the Recommendation and decided to act on it) -- see
    convert_recommendation_to_task, which is why this needed to become
    a creation-time parameter rather than only a discharge-time one.
    """
    if created_at is None:
        created_at = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO task (vin, dealership_id, task_type, department, priority, reason, created_at, "
        "ratified_by, ratification_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING task_id",
        (vin, dealership_id, task_type, department, priority, reason, created_at,
         ratified_by, ratification_type),
    )
    return cur.fetchone()[0]


def get_open_task(conn: sqlite3.Connection, vin: str, task_type: str):
    """
    Returns the dict of an outstanding Task for this (vin, task_type),
    or None. This is the idempotency check callers use before
    insert_task -- a VIN that still needs the same install every sync
    must get exactly one outstanding Task for it, not a fresh row every
    run (the same "don't re-create what's already open" discipline
    Slice 3's diffing already applies to Events).
    """
    row = conn.execute(
        "SELECT task_id, vin, dealership_id, task_type, department, priority, "
        "commitment_standing, execution_status, assigned_employee_id, ratified_by, "
        "ratification_type, escalated_from_task_id, reason, created_at, completed_at "
        "FROM task WHERE vin = ? AND task_type = ? AND commitment_standing = 'outstanding'",
        (vin, task_type),
    ).fetchone()
    if row is None:
        return None
    columns = ["task_id", "vin", "dealership_id", "task_type", "department", "priority",
               "commitment_standing", "execution_status", "assigned_employee_id", "ratified_by",
               "ratification_type", "escalated_from_task_id", "reason", "created_at", "completed_at"]
    return dict(zip(columns, row))


def get_task(conn: sqlite3.Connection, task_id: int):
    """Same shape as get_open_task, looked up by task_id directly regardless of standing."""
    row = conn.execute(
        "SELECT task_id, vin, dealership_id, task_type, department, priority, "
        "commitment_standing, execution_status, assigned_employee_id, ratified_by, "
        "ratification_type, escalated_from_task_id, reason, created_at, completed_at "
        "FROM task WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    columns = ["task_id", "vin", "dealership_id", "task_type", "department", "priority",
               "commitment_standing", "execution_status", "assigned_employee_id", "ratified_by",
               "ratification_type", "escalated_from_task_id", "reason", "created_at", "completed_at"]
    return dict(zip(columns, row))


def _discharge_task(conn: sqlite3.Connection, task_id: int, standing: str,
                     ratified_by: str = None, ratification_type: str = None,
                     completed_at: str = None):
    """
    Shared internal primitive -- sets commitment_standing to a terminal
    value. Only ever moves a task OUT of 'outstanding'; the WHERE
    clause's guard means discharging an already-terminal task twice is
    a harmless no-op, not a second transition, the same immutability
    discipline resolve_pending_identity already applies. ratified_by/
    ratification_type are only overwritten when explicitly supplied
    (Reality-discharge via honor_task/moot_task doesn't pass them --
    nothing "ratifies" a fact the world reported; Intent-discharge via
    cancel_task/escalate_task always does, since Intent requires a
    legitimate authority acting).
    """
    if completed_at is None:
        completed_at = datetime.datetime.now().isoformat()
    if ratified_by is not None or ratification_type is not None:
        conn.execute(
            "UPDATE task SET commitment_standing = ?, completed_at = ?, "
            "ratified_by = ?, ratification_type = ? "
            "WHERE task_id = ? AND commitment_standing = 'outstanding'",
            (standing, completed_at, ratified_by, ratification_type, task_id),
        )
    else:
        conn.execute(
            "UPDATE task SET commitment_standing = ?, completed_at = ? "
            "WHERE task_id = ? AND commitment_standing = 'outstanding'",
            (standing, completed_at, task_id),
        )


def honor_task(conn: sqlite3.Connection, task_id: int, completed_at: str = None):
    """
    Reality-discharge: the condition that created this Task was
    satisfied, confirmed by a claim from the relevant source (e.g.
    RecovR's diff shows this VIN flipped to paired). No ratified_by --
    nothing is ratifying anything here; the world simply confirmed it.
    """
    _discharge_task(conn, task_id, "honored", completed_at=completed_at)


def moot_task(conn: sqlite3.Connection, task_id: int, completed_at: str = None):
    """
    Reality-discharge: the condition became irrelevant before being
    satisfied (e.g. the vehicle sold before its RecovR install
    happened). Same no-ratification reasoning as honor_task -- this is
    the world changing, not an organizational decision.
    """
    _discharge_task(conn, task_id, "moot", completed_at=completed_at)


def cancel_task(conn: sqlite3.Connection, task_id: int, ratified_by: str,
                 ratification_type: str = "human", completed_at: str = None):
    """
    Intent-discharge: the organization decided not to pursue this
    commitment, independent of anything the world reported. Always
    requires ratified_by -- Intent-discharge, unlike Reality-discharge,
    requires a legitimate authority actually deciding (DECISION_FRAMEWORK.md:
    "authority is independent from provenance").
    """
    _discharge_task(conn, task_id, "cancelled",
                     ratified_by=ratified_by, ratification_type=ratification_type,
                     completed_at=completed_at)


def escalate_task(conn: sqlite3.Connection, task_id: int, new_task_type: str,
                   ratified_by: str, ratification_type: str = "human",
                   department: str = None, priority: str = None, reason: str = None,
                   completed_at: str = None, created_at: str = None) -> int:
    """
    Intent-discharge (Superseded) plus escalation: the existing task_id
    is superseded (not simply cancelled -- it's being replaced by
    something, not abandoned) and a new Task is created in its place
    with escalated_from_task_id pointing back at it. Reuses the parent's
    vin/dealership_id; department/priority/reason can be overridden for
    the new Task since an escalation often needs a different priority
    or department than its parent.

    Per SPRINT_4_CHECKLIST.md's Moot-evaluation note: nothing here
    makes the new Task inherit the parent's disposition automatically --
    the new Task starts 'outstanding' like any other and must be
    evaluated on its own condition. escalated_from_task_id exists so
    that evaluation CAN look at the parent's status when relevant, not
    so it automatically cascades one onto the other.
    """
    parent = get_task(conn, task_id)
    if parent is None:
        raise ValueError(f"cannot escalate unknown task_id={task_id}")

    _discharge_task(conn, task_id, "superseded",
                     ratified_by=ratified_by, ratification_type=ratification_type,
                     completed_at=completed_at)

    if created_at is None:
        created_at = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO task (vin, dealership_id, task_type, department, priority, "
        "ratified_by, ratification_type, escalated_from_task_id, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING task_id",
        (parent["vin"], parent["dealership_id"], new_task_type,
         department if department is not None else parent["department"],
         priority if priority is not None else parent["priority"],
         ratified_by, ratification_type, task_id, reason, created_at),
    )
    return cur.fetchone()[0]


def insert_task_execution_event(conn: sqlite3.Connection, task_id: int, transition_type: str,
                                 actor_employee_id: str = None, note: str = None,
                                 observed_at: str = None) -> int:
    """
    Appends to the execution log AND updates task.execution_status to
    match -- this is the one place both happen together, which is what
    makes execution_status a plain cache rather than an independently
    writable field (per SPRINT_4_CHECKLIST.md: "not independently
    writable"). Always inserts a new log row, same append-only
    discipline as insert_event -- consecutive transitions
    (started -> blocked -> resumed -> completed) are the whole point;
    collapsing them into one mutable field would destroy exactly the
    information TaskExecutionEvent exists to keep (see DATA_MODEL.md).
    """
    if observed_at is None:
        observed_at = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO task_execution_event (task_id, transition_type, actor_employee_id, note, observed_at) "
        "VALUES (?, ?, ?, ?, ?) RETURNING task_execution_event_id",
        (task_id, transition_type, actor_employee_id, note, observed_at),
    )
    new_id = cur.fetchone()[0]
    execution_status = _EXECUTION_STATUS_BY_TRANSITION.get(transition_type, transition_type)
    conn.execute(
        "UPDATE task SET execution_status = ? WHERE task_id = ?",
        (execution_status, task_id),
    )
    return new_id


def assert_task_completed(conn: sqlite3.Connection, task_id: int, actor_employee_id: str,
                           note: str = None, observed_at: str = None) -> int:
    """
    The human-facing entry point for "I finished this Task" -- a thin,
    semantically-named wrapper over insert_task_execution_event(...,
    transition_type='completed'). Deliberately does NOT touch
    commitment_standing: per VISION.md's "manual input is an assertion,
    not an override," a human's claim of completion is provisional
    until the relevant source corroborates it on its own next sync (see
    persist_recovr_observations' honor_task hook, unchanged by this
    function) -- or the Task surfaces a disagreement instead of either
    side silently winning (see this function's caller-facing docstring
    in SPRINT_4_CHECKLIST.md's "Completion handling" item). A Task left
    with execution_status='completed' and commitment_standing still
    'outstanding' IS that surfaced disagreement -- both claims stay
    visible and untouched in their own logs, not collapsed into one.
    """
    return insert_task_execution_event(
        conn, task_id, "completed", actor_employee_id=actor_employee_id,
        note=note, observed_at=observed_at,
    )


# ---------------------------------------------------------------------------
# Phase 2, Sprint 4, Slice 6 -- Recommendation.
#
# See DATA_MODEL.md's Recommendation entry. Deliberately distinct from
# Task -- an Interpretation (DECISION_FRAMEWORK.md's ontology), not a
# Commitment, until a human converts it. Rule-driven, reusing the same
# rules/aging.py functions the CSV reports already use.
# ---------------------------------------------------------------------------

_RECOMMENDATION_COLUMNS = ["recommendation_id", "vin", "severity", "title", "detail", "rule_source",
                           "status", "resulting_task_id", "created_at", "resolved_at"]


def insert_recommendation(conn: sqlite3.Connection, vin: str, severity: str, title: str, detail: str,
                           rule_source: str, created_at: str = None) -> int:
    """
    Creates a new Recommendation, always status='open' (the migration's
    column default). Callers must check get_open_recommendation() (or,
    for the dismissed-reopening decision, get_latest_recommendation())
    themselves first -- this function always inserts, same division of
    responsibility as insert_task/insert_event.
    """
    if created_at is None:
        created_at = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO recommendation (vin, severity, title, detail, rule_source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?) RETURNING recommendation_id",
        (vin, severity, title, detail, rule_source, created_at),
    )
    return cur.fetchone()[0]


def get_open_recommendation(conn: sqlite3.Connection, vin: str, rule_source: str):
    """Returns the dict of an open Recommendation for this (vin, rule_source), or None."""
    row = conn.execute(
        f"SELECT {', '.join(_RECOMMENDATION_COLUMNS)} FROM recommendation "
        "WHERE vin = ? AND rule_source = ? AND status = 'open'",
        (vin, rule_source),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(_RECOMMENDATION_COLUMNS, row))


def get_latest_recommendation(conn: sqlite3.Connection, vin: str, rule_source: str):
    """
    Returns the dict of the most recently created Recommendation for
    this (vin, rule_source), regardless of status, or None if none
    exists yet. This is the basis for the "should a dismissed
    Recommendation reappear" decision -- see
    sync/reconciler.py's generate_key_out_aging_recommendations for how
    its resolved_at is compared against Event history to decide whether
    the underlying vehicle state has genuinely changed since dismissal.
    """
    row = conn.execute(
        f"SELECT {', '.join(_RECOMMENDATION_COLUMNS)} FROM recommendation "
        "WHERE vin = ? AND rule_source = ? ORDER BY recommendation_id DESC LIMIT 1",
        (vin, rule_source),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(_RECOMMENDATION_COLUMNS, row))


def get_recommendation(conn: sqlite3.Connection, recommendation_id: int):
    """Same shape as get_open_recommendation/get_latest_recommendation, looked up by id directly."""
    row = conn.execute(
        f"SELECT {', '.join(_RECOMMENDATION_COLUMNS)} FROM recommendation WHERE recommendation_id = ?",
        (recommendation_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(_RECOMMENDATION_COLUMNS, row))


def dismiss_recommendation(conn: sqlite3.Connection, recommendation_id: int, resolved_at: str = None):
    """
    Marks a Recommendation dismissed. Only ever moves it OUT of 'open';
    the WHERE guard means dismissing an already-resolved Recommendation
    twice is a harmless no-op, not a second transition -- same
    immutability discipline as _discharge_task/resolve_pending_identity.
    No ratification recorded here -- DATA_MODEL.md's Recommendation has
    no ratified_by field (unlike Task); dismissing one is a lighter-
    weight action than committing to or discharging a Task, and no
    real workflow has asked for authority-tracking on a dismiss.
    """
    if resolved_at is None:
        resolved_at = datetime.datetime.now().isoformat()
    conn.execute(
        "UPDATE recommendation SET status = 'dismissed', resolved_at = ? "
        "WHERE recommendation_id = ? AND status = 'open'",
        (resolved_at, recommendation_id),
    )


def convert_recommendation_to_task(conn: sqlite3.Connection, recommendation_id: int, task_type: str,
                                    ratified_by: str, ratification_type: str = "human",
                                    department: str = None, priority: str = None,
                                    reason: str = None, created_at: str = None,
                                    resolved_at: str = None) -> int:
    """
    The Interpretation-to-Ratification-to-Commitment path
    (DECISION_FRAMEWORK.md's Architecture section): converting a
    Recommendation into a Task is itself an act of ratification -- a
    human reviewed the Recommendation and decided to act, which is why
    ratified_by is a REQUIRED parameter here (unlike Slice 5's
    auto-generated install Tasks, which have no ratification at
    creation). Only ever converts a Recommendation once -- the WHERE
    guard on the UPDATE means calling this twice for an already-
    converted Recommendation raises (see below) rather than silently
    creating a second Task.
    """
    rec = get_recommendation(conn, recommendation_id)
    if rec is None:
        raise ValueError(f"cannot convert unknown recommendation_id={recommendation_id}")
    if rec["status"] != "open":
        raise ValueError(
            f"cannot convert recommendation_id={recommendation_id} -- "
            f"status is '{rec['status']}', not 'open'"
        )

    task_id = insert_task(
        conn, rec["vin"], task_type, department=department, priority=priority,
        reason=reason if reason is not None else rec["detail"], created_at=created_at,
        ratified_by=ratified_by, ratification_type=ratification_type,
    )

    if resolved_at is None:
        resolved_at = datetime.datetime.now().isoformat()
    conn.execute(
        "UPDATE recommendation SET status = 'converted_to_task', resulting_task_id = ?, resolved_at = ? "
        "WHERE recommendation_id = ? AND status = 'open'",
        (task_id, resolved_at, recommendation_id),
    )
    return task_id


# ---------------------------------------------------------------------------
# Phase 3, Sprint 1 -- Employee / Dealership.
#
# See DATA_MODEL.md's Employee and Dealership entries and
# migrations/0006_employee_dealership.sql for the full reasoning. Both
# are reference entities with a natural key (employee_id, dealership_id)
# and no discharge/status-transition lifecycle of their own -- unlike
# Task or Recommendation, there is no "invalid transition" to guard
# against here, so the *intent* is to reuse upsert_vehicle's partial-
# upsert shape: a Dealership's brand can be filled in by one source and
# an Employee's status updated by another, independently, the same way
# Vehicle's per-source status fields already accumulate incrementally
# across separate importer passes.
#
# The *implementation* deliberately does NOT reuse upsert_vehicle's
# single "INSERT ... ON CONFLICT DO UPDATE" statement shape, though --
# confirmed empirically (not assumed) that SQLite evaluates a table's
# NOT NULL constraints against the attempted INSERT row before conflict
# resolution ever redirects to the UPDATE branch. Vehicle has no NOT
# NULL column besides its own primary key, so upsert_vehicle's
# single-statement form never hits this. Dealership and Employee both
# have a NOT NULL `name` (migrations/0006_employee_dealership.sql) --
# a single ON CONFLICT DO UPDATE statement that omits `name` (e.g. a
# call that only wants to update `status`) raises IntegrityError even
# when the row already exists and already has a valid name. Reusing
# upsert_vehicle's shape here as-is would silently break the exact
# partial-update behavior it's supposed to provide. Both functions below
# branch explicitly on whether the row already exists instead: a genuine
# UPDATE statement for existing rows (no INSERT attempted at all, so no
# NOT NULL check on omitted columns), and an explicit, named ValueError
# for the one real invalid case an existence branch newly makes
# possible -- creating a row for the first time without a name.
# ---------------------------------------------------------------------------


def upsert_dealership(conn: sqlite3.Connection, dealership_id: str, **fields):
    """
    Partial upsert -- only the columns passed in `fields` are set or
    updated on an existing row; any other column already there is left
    untouched, same end result as upsert_vehicle. See the module-level
    comment above for why this is implemented as an explicit
    existence-check-then-branch rather than upsert_vehicle's single
    statement. Creating a new Dealership for the first time requires
    `name` in `fields` -- raises ValueError otherwise, since the schema
    can't hold a nameless row and there's no demonstrated need (unlike
    Vehicle's bare-vin placeholder, which Keyper's resolve-first-
    populate-later workflow genuinely requires) for one here.
    """
    existing = get_dealership(conn, dealership_id)

    if existing is None:
        if not fields.get("name"):
            raise ValueError(f"cannot create dealership_id={dealership_id!r} without a name")
        columns = list(fields.keys())
        insert_cols = ", ".join(["dealership_id"] + columns)
        placeholders = ", ".join(["?"] * (len(columns) + 1))
        conn.execute(
            f"INSERT INTO dealership ({insert_cols}) VALUES ({placeholders})",
            [dealership_id] + [fields[c] for c in columns],
        )
        return

    if not fields:
        return
    update_clause = ", ".join(f"{c} = ?" for c in fields)
    conn.execute(
        f"UPDATE dealership SET {update_clause} WHERE dealership_id = ?",
        list(fields.values()) + [dealership_id],
    )


def get_dealership(conn: sqlite3.Connection, dealership_id: str):
    """Returns the dict of a Dealership's columns, or None if no such row exists."""
    row = conn.execute(
        "SELECT dealership_id, name, brand FROM dealership WHERE dealership_id = ?",
        (dealership_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(["dealership_id", "name", "brand"], row))


def upsert_employee(conn: sqlite3.Connection, employee_id: str, **fields):
    """
    Partial upsert, same shape and same reasoning as upsert_dealership
    above (see the module-level comment for why this branches on
    existence instead of reusing upsert_vehicle's single-statement
    form). Creating a new Employee for the first time requires `name`
    in `fields` -- raises ValueError otherwise. `dealership_id`, if
    passed, must reference an existing Dealership row (a real FOREIGN
    KEY, per migrations/0006_employee_dealership.sql, enforced by
    SQLite itself since connect() turns on `PRAGMA foreign_keys`) --
    callers upserting an Employee's home dealership must
    upsert_dealership() first, the same ordering
    convert_recommendation_to_task already requires between a
    Recommendation and the Task it produces.
    """
    existing = get_employee(conn, employee_id)

    if existing is None:
        if not fields.get("name"):
            raise ValueError(f"cannot create employee_id={employee_id!r} without a name")
        columns = list(fields.keys())
        insert_cols = ", ".join(["employee_id"] + columns)
        placeholders = ", ".join(["?"] * (len(columns) + 1))
        conn.execute(
            f"INSERT INTO employee ({insert_cols}) VALUES ({placeholders})",
            [employee_id] + [fields[c] for c in columns],
        )
        return

    if not fields:
        return
    update_clause = ", ".join(f"{c} = ?" for c in fields)
    conn.execute(
        f"UPDATE employee SET {update_clause} WHERE employee_id = ?",
        list(fields.values()) + [employee_id],
    )


def get_employee(conn: sqlite3.Connection, employee_id: str):
    """Returns the dict of an Employee's columns, or None if no such row exists."""
    row = conn.execute(
        "SELECT employee_id, name, role, department, dealership_id, status "
        "FROM employee WHERE employee_id = ?",
        (employee_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(["employee_id", "name", "role", "department", "dealership_id", "status"], row))
