"""
Minimal repository layer for Phase 2, Slice 1 -- a migration runner
plus upsert/insert functions. Deliberately thin: no ORM, no query
helpers beyond what Slice 1 needs writing data, applying the same
"no speculative schema" discipline to code as IMPLEMENTATION_PLAN.md
applies to the schema itself. Reading this data back for dashboard-
shaped questions is Slice 7's concern (a future queries/ module), not
this one's.
"""

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
    """
    if not fields:
        conn.execute("INSERT OR IGNORE INTO vehicle (vin) VALUES (?)", (vin,))
        conn.commit()
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
    conn.commit()


def insert_event(conn: sqlite3.Connection, vin: str, event_type: str, source: str,
                  observed_at: str = None, summary: str = None, detail_fields: dict = None,
                  sync_run_id: str = None, actor_employee_id: str = None,
                  dealership_id: str = None) -> int:
    """
    Always inserts a new row -- Slice 1 has no change-detection yet
    (that's Slice 3's diff-before-write pattern). Running the same
    input twice produces two Events; this is known, accepted, and
    temporary noisiness, not a bug -- see IMPLEMENTATION_PLAN.md Slice 3.
    """
    if observed_at is None:
        observed_at = datetime.datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO event (vin, event_type, source, sync_run_id, actor_employee_id, "
        "dealership_id, observed_at, summary, detail_fields) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (vin, event_type, source, sync_run_id, actor_employee_id, dealership_id,
         observed_at, summary, json.dumps(detail_fields) if detail_fields is not None else None),
    )
    conn.commit()
    return cur.lastrowid
