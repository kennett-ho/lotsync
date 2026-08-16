"""
SQLite -> PostgreSQL production migration tool (Sprint 07).

The operator tool PRODUCTION_MIGRATION_PLAN.md section 5 requires:
copies a LotSync/DealerDOH SQLite backup file into an empty PostgreSQL
database and validates the result exactly. Built and rehearsed in
Sprint 07 against disposable infrastructure; intended to be the
Release B import step in the production cutover, run from the operator
machine against the verified final backup -- never against a live
database file.

Design rules (from the plan):

- The SOURCE is a backup FILE, opened read-only (URI mode=ro). This
  tool never writes the source, and refuses to run against anything
  that is not an existing regular file.
- The DESTINATION DSN comes from an environment variable (default
  MIGRATE_DEST_DSN; override the name with --dest-dsn-env). DSNs are
  never accepted as command-line arguments and never printed.
- Non-local destinations require --i-am-migrating-production AND an
  interactively typed confirmation phrase. The guard runs BEFORE any
  connection is attempted.
- The default mode is a DRY RUN (preflight + destination inspection,
  no writes). --execute performs the migration. --validate-only
  re-runs validation against an already-migrated destination.
- A non-empty destination is refused unless --wipe-destination is
  given, which drops the known application tables (reverse-FK order)
  and re-applies migrations -- the documented recovery for an
  interrupted import.
- Any validation failure exits non-zero (2) with an explicit list of
  failures. Refusals/preconditions exit 3. Success exits 0.

Run from the repo root with the same convention as the test suite:

    PYTHONPATH=.. python tools/migrate_sqlite_to_postgres.py \
        --source <backup.db> [--execute] [--report out.json]
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
import urllib.parse

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.dirname(_REPO))  # lotsync.* import convention

from lotsync.database.repository import apply_migrations  # noqa: E402
from lotsync.database.engine import PostgresConnection  # noqa: E402

MIGRATIONS_POSTGRES_DIR = os.path.join(_REPO, "database", "migrations_postgres")

EXPECTED_SCHEMA_VERSION = 9

# FK-safe insert order (parents before children; task before its
# self-reference is handled by ordering rows on task_id ASC, since an
# escalated task always references an earlier task_id).
TABLE_ORDER = [
    "organization",
    "dealership",
    "employee",
    "vehicle",
    "sync_run",
    "event",
    "event_freshness",
    "pending_identity",
    "task",
    "task_execution_event",
    "recommendation",
    "user_membership",
]

# Identity (AUTOINCREMENT) tables and their PK columns -- sequences
# must be reset after explicit-ID inserts.
IDENTITY_PKS = {
    "event": "event_id",
    "pending_identity": "pending_identity_id",
    "sync_run": "sync_run_id",
    "task": "task_id",
    "task_execution_event": "task_execution_event_id",
    "recommendation": "recommendation_id",
    "user_membership": "membership_id",
}

# Deterministic per-row ORDER BY per table (PK), so batches and the
# task self-FK are ordered reproducibly.
ORDER_BY = {
    "organization": "organization_id",
    "dealership": "dealership_id",
    "employee": "employee_id",
    "vehicle": "vin",
    "sync_run": "sync_run_id",
    "event": "event_id",
    "event_freshness": "vin, event_type, source",
    "pending_identity": "pending_identity_id",
    "task": "task_id",
    "task_execution_event": "task_execution_event_id",
    "recommendation": "recommendation_id",
    "user_membership": "membership_id",
}

# Domain-invariant breakdowns compared exactly between source and
# destination (skipped automatically if the column is absent).
BREAKDOWNS = [
    ("vehicle", "tekion_status"),
    ("vehicle", "keyper_status"),
    ("vehicle", "mdd_status"),
    ("vehicle", "recovr_status"),
    ("task", "commitment_standing"),
    ("task", "execution_status"),
    ("task", "task_type"),
    ("recommendation", "status"),
    ("sync_run", "status"),
    ("sync_run", "source"),
    ("pending_identity", "status"),
    ("user_membership", "role"),
]

# Min/max timestamp columns compared exactly.
TIME_RANGES = [
    ("event", "observed_at"),
    ("event", "event_time"),
    ("sync_run", "started_at"),
    ("sync_run", "completed_at"),
    ("task", "created_at"),
]

BATCH_SIZE = 1000

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class Refusal(Exception):
    """Precondition/refusal -- exit 3, nothing was changed."""


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------
# Safety gates
# --------------------------------------------------------------------

def read_dsn(env_name: str) -> str:
    dsn = os.environ.get(env_name, "").strip()
    if not dsn:
        raise Refusal(
            f"Destination DSN environment variable {env_name!r} is not set. "
            "This tool never takes a DSN on the command line."
        )
    return dsn


def dsn_host(dsn: str) -> str:
    try:
        return urllib.parse.urlsplit(dsn).hostname or ""
    except ValueError:
        return ""


def enforce_target_guard(dsn: str, claims_production: bool) -> None:
    """Refuse non-local destinations without the explicit production
    ceremony. Runs before any connection attempt."""
    host = dsn_host(dsn)
    if host in _LOCAL_HOSTS:
        return
    if not claims_production:
        raise Refusal(
            f"Destination host {host!r} is not local. Migrating a remote "
            "database requires --i-am-migrating-production and an "
            "interactive typed confirmation. If this is a rehearsal, use "
            "a local disposable PostgreSQL instead."
        )
    if not sys.stdin.isatty():
        raise Refusal(
            "--i-am-migrating-production requires an interactive terminal "
            "for the typed confirmation. Refusing to run non-interactively "
            "against a remote destination."
        )
    phrase = "migrate production now"
    try:
        typed = input(
            f"Destination host: {host}\n"
            f"Type exactly '{phrase}' to proceed: "
        )
    except (EOFError, KeyboardInterrupt):
        # isatty() can report console-like stdin in captured/CI
        # contexts (found by this tool's own test suite on Windows) --
        # an unanswerable prompt must be a clean refusal, never a
        # traceback.
        raise Refusal(
            "No interactive confirmation available. Refusing to run "
            "against a remote destination."
        )
    if typed.strip() != phrase:
        raise Refusal("Confirmation phrase did not match. Nothing was done.")


def open_source(path: str) -> sqlite3.Connection:
    if not os.path.isfile(path):
        raise Refusal(f"Source {path!r} does not exist or is not a regular file.")
    uri = "file:" + path.replace("\\", "/") + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
    except sqlite3.Error as exc:
        raise Refusal(f"Source is not a readable SQLite database: {exc}")
    return conn


def connect_dest(dsn: str) -> PostgresConnection:
    import psycopg

    try:
        # connect_timeout: fail fast and loudly on an unreachable or
        # wrong destination instead of hanging the operator -- found by
        # Sprint 07's bad-DSN failure injection, which hung >2 minutes
        # without this.
        return PostgresConnection(
            psycopg.connect(dsn, prepare_threshold=None, connect_timeout=10))
    except Exception as exc:
        raise Refusal(
            "Cannot connect to the destination PostgreSQL "
            f"({type(exc).__name__}: {exc})"
        )


# --------------------------------------------------------------------
# Introspection helpers (both connections speak `execute(sql, params)`)
# --------------------------------------------------------------------

def sqlite_tables(src) -> list:
    return [r[0] for r in src.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def sqlite_columns(src, table: str) -> list:
    return [r[1] for r in src.execute(f"PRAGMA table_info([{table}])")]


def pg_tables(dest) -> list:
    return [r[0] for r in dest.execute(
        "SELECT tablename FROM pg_catalog.pg_tables "
        "WHERE schemaname = current_schema() ORDER BY tablename")]


def pg_columns(dest, table: str) -> list:
    return [r[0] for r in dest.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = ? "
        "ORDER BY ordinal_position", (table,))]


def pg_indexes(dest) -> set:
    return {r[0] for r in dest.execute(
        "SELECT indexname FROM pg_catalog.pg_indexes "
        "WHERE schemaname = current_schema()")}


def expected_from_migration_files():
    """Expected table and index names, parsed from the PostgreSQL
    migration files themselves -- one source of truth, no drift."""
    import re

    tables, indexes = set(), set()
    for name in sorted(os.listdir(MIGRATIONS_POSTGRES_DIR)):
        if not name.endswith(".sql"):
            continue
        with open(os.path.join(MIGRATIONS_POSTGRES_DIR, name)) as fh:
            # Strip `--` comments first: migration commentary
            # legitimately mentions DDL phrases in prose (found by this
            # tool's own validation failing closed during rehearsal).
            text = "\n".join(line.split("--", 1)[0] for line in fh)
        tables.update(re.findall(
            r"CREATE TABLE IF NOT EXISTS\s+(\w+)", text, re.IGNORECASE))
        indexes.update(re.findall(
            r"CREATE INDEX IF NOT EXISTS\s+(\w+)", text, re.IGNORECASE))
    tables.add("schema_migrations")
    return tables, indexes


def schema_version(conn) -> int:
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    except Exception:
        return 0
    return row[0] or 0


def count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def breakdown(conn, table: str, col: str) -> dict:
    return {
        ("<NULL>" if r[0] is None else str(r[0])): r[1]
        for r in conn.execute(
            f"SELECT {col}, COUNT(*) FROM {table} GROUP BY {col}")
    }


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------
# Migration steps
# --------------------------------------------------------------------

def preflight_source(src, path: str, report: dict) -> None:
    integ = src.execute("PRAGMA integrity_check").fetchone()[0]
    if integ != "ok":
        raise Refusal(f"Source integrity_check returned {integ!r}, not 'ok'.")
    ver = schema_version(src)
    if ver != EXPECTED_SCHEMA_VERSION:
        raise Refusal(
            f"Source schema version is {ver}, expected exactly "
            f"{EXPECTED_SCHEMA_VERSION}. The production final backup is "
            "taken AFTER Release A (which auto-applies migration 0009); "
            "a v{0} source means the wrong file or the wrong moment."
            .format(ver)
        )
    missing = [t for t in TABLE_ORDER if t not in sqlite_tables(src)]
    if missing:
        raise Refusal(f"Source is missing expected tables: {missing}")
    report["source"] = {
        "path": os.path.abspath(path),
        "size_bytes": os.path.getsize(path),
        "sha256": sha256_file(path),
        "integrity_check": integ,
        "schema_version": ver,
        "counts": {t: count(src, t) for t in TABLE_ORDER},
        "sqlite_sequence": {
            r[0]: r[1] for r in src.execute(
                "SELECT name, seq FROM sqlite_sequence")
        } if src.execute(
            "SELECT name FROM sqlite_master WHERE name='sqlite_sequence'"
        ).fetchone() else {},
    }


def dest_business_rows(dest) -> dict:
    present = set(pg_tables(dest))
    return {t: count(dest, t) for t in TABLE_ORDER if t in present}


def wipe_destination(dest) -> None:
    log("  wiping destination application tables (reverse-FK order) ...")
    for table in reversed(TABLE_ORDER):
        dest.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    dest.execute("DROP TABLE IF EXISTS schema_migrations CASCADE")
    dest.commit()


def apply_schema(dest) -> None:
    apply_migrations(dest, MIGRATIONS_POSTGRES_DIR)
    ver = schema_version(dest)
    if ver != EXPECTED_SCHEMA_VERSION:
        raise Refusal(
            f"Destination is at schema version {ver} after applying "
            f"migrations, expected {EXPECTED_SCHEMA_VERSION}."
        )


def copy_tables(src, dest, report: dict) -> None:
    copied = {}
    for table in TABLE_ORDER:
        src_cols = sqlite_columns(src, table)
        dst_cols = pg_columns(dest, table)
        if src_cols != dst_cols:
            # Order-insensitive but presence-exact: both engines were
            # created by parallel migration sets, so any difference is
            # a real schema divergence.
            if sorted(src_cols) != sorted(dst_cols):
                raise Refusal(
                    f"Column mismatch on {table}: source {src_cols} vs "
                    f"destination {dst_cols}"
                )
        cols = ", ".join(src_cols)
        placeholders = ", ".join(["?"] * len(src_cols))
        insert = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        n = 0
        rows = src.execute(
            f"SELECT {cols} FROM {table} ORDER BY {ORDER_BY[table]}")
        while True:
            batch = rows.fetchmany(BATCH_SIZE)
            if not batch:
                break
            dest.executemany(insert, batch)
            n += len(batch)
        copied[table] = n
        log(f"  copied {table:<24} {n:>7} rows")
    dest.commit()
    report["copied"] = copied


def reset_sequences(src, dest, report: dict) -> None:
    """setval(max(sqlite_sequence.seq, MAX(id))) per identity table --
    sequences do not advance on explicit-ID inserts, and sqlite's seq
    can legitimately exceed MAX(id) after deletions (the plan's
    pending_identity case)."""
    seq_rows = report["source"]["sqlite_sequence"]
    out = {}
    for table, pk in IDENTITY_PKS.items():
        max_id = src.execute(f"SELECT MAX({pk}) FROM {table}").fetchone()[0] or 0
        target = max(seq_rows.get(table, 0), max_id)
        if target < 1:
            out[table] = {"set_to": None, "note": "empty; identity default"}
            continue
        dest.execute(
            "SELECT setval(pg_get_serial_sequence(?, ?), ?, true)",
            (table, pk, target),
        )
        out[table] = {"set_to": target, "max_id": max_id,
                      "sqlite_seq": seq_rows.get(table, 0)}
    dest.commit()
    report["sequences"] = out


# --------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------

def _fail(failures, kind, detail):
    failures.append({"check": kind, "detail": detail})
    log(f"  FAIL  {kind}: {detail}")


def _ok(kind, detail=""):
    log(f"  ok    {kind}{(': ' + detail) if detail else ''}")


def validate(src, dest, report: dict, sample_vins: int) -> list:
    failures = []

    # ---- structural ------------------------------------------------
    exp_tables, exp_indexes = expected_from_migration_files()
    have_tables = set(pg_tables(dest))
    missing_t = exp_tables - have_tables
    if missing_t:
        _fail(failures, "tables", f"missing {sorted(missing_t)}")
    else:
        _ok("tables", f"{len(exp_tables)} present")

    have_indexes = pg_indexes(dest)
    missing_i = exp_indexes - have_indexes
    if missing_i:
        _fail(failures, "indexes", f"missing {sorted(missing_i)}")
    else:
        _ok("indexes", f"{len(exp_indexes)} present")

    versions = [r[0] for r in dest.execute(
        "SELECT version FROM schema_migrations ORDER BY version")]
    if versions != list(range(1, EXPECTED_SCHEMA_VERSION + 1)):
        _fail(failures, "schema_migrations", f"versions {versions}")
    else:
        _ok("schema_migrations", f"1..{EXPECTED_SCHEMA_VERSION}")

    seq_bad = 0
    for table, pk in IDENTITY_PKS.items():
        max_id = dest.execute(f"SELECT MAX({pk}) FROM {table}").fetchone()[0] or 0
        if max_id == 0:
            continue
        last = dest.execute(
            "SELECT last_value FROM pg_sequences "
            "WHERE schemaname || '.' || sequencename = "
            "pg_get_serial_sequence(?, ?)",
            (table, pk)).fetchone()
        if last is None or last[0] is None or last[0] < max_id:
            _fail(failures, "sequence",
                  f"{table}.{pk} sequence {last} < MAX(id) {max_id}")
            seq_bad += 1
    if not seq_bad:
        _ok("sequences", "all >= MAX(id)")

    # ---- exact counts ---------------------------------------------
    report["counts"] = {}
    count_bad = 0
    for table in TABLE_ORDER:
        s, d = count(src, table), count(dest, table)
        report["counts"][table] = {"source": s, "dest": d}
        if s != d:
            _fail(failures, "count", f"{table}: source {s} != destination {d}")
            count_bad += 1
    if not count_bad:
        _ok("counts", "all tables exact")

    # ---- domain invariants ----------------------------------------
    bd_bad = 0
    for table, col in BREAKDOWNS:
        if col not in sqlite_columns(src, table):
            continue
        s, d = breakdown(src, table, col), breakdown(dest, table, col)
        if s != d:
            _fail(failures, "breakdown", f"{table}.{col}: {s} != {d}")
            bd_bad += 1
    if not bd_bad:
        _ok("breakdowns", "status/type distributions exact")

    s = src.execute("SELECT COUNT(DISTINCT vin) FROM vehicle").fetchone()[0]
    d = dest.execute("SELECT COUNT(DISTINCT vin) FROM vehicle").fetchone()[0]
    if s != d:
        _fail(failures, "distinct-vins", f"{s} != {d}")

    orphan_checks = [
        ("event.vin", "SELECT COUNT(*) FROM event WHERE vin NOT IN "
                      "(SELECT vin FROM vehicle)"),
        ("task.vin", "SELECT COUNT(*) FROM task WHERE vin NOT IN "
                     "(SELECT vin FROM vehicle)"),
        ("recommendation.vin", "SELECT COUNT(*) FROM recommendation "
                               "WHERE vin NOT IN (SELECT vin FROM vehicle)"),
        ("event.sync_run_id", "SELECT COUNT(*) FROM event WHERE sync_run_id "
                              "IS NOT NULL AND sync_run_id NOT IN "
                              "(SELECT CAST(sync_run_id AS TEXT) FROM sync_run)"),
    ]
    orph_bad = 0
    for name, sql in orphan_checks:
        od = dest.execute(sql).fetchone()[0]
        osrc = src.execute(sql).fetchone()[0]
        if od != osrc:
            _fail(failures, "orphans", f"{name}: source {osrc} != dest {od}")
            orph_bad += 1
        elif od != 0:
            _ok("orphans", f"{name}: {od} (matches source -- pre-existing)")
    if not orph_bad:
        _ok("orphans", "all checks match source")

    tr_bad = 0
    for table, col in TIME_RANGES:
        if col not in sqlite_columns(src, table):
            continue
        q = f"SELECT MIN({col}), MAX({col}) FROM {table} WHERE {col} IS NOT NULL"
        if src.execute(q).fetchone() != dest.execute(q).fetchone():
            _fail(failures, "time-range", f"{table}.{col} min/max differ")
            tr_bad += 1
    if not tr_bad:
        _ok("time-ranges", "min/max exact")

    # ---- representative rows --------------------------------------
    vins = [r[0] for r in src.execute("SELECT vin FROM vehicle ORDER BY vin")]
    picks = []
    if vins:
        step = max(1, len(vins) // max(1, sample_vins))
        picks = vins[::step][:sample_vins]
    newest = src.execute(
        "SELECT vin FROM event ORDER BY event_id DESC LIMIT 1").fetchone()
    if newest and newest[0] not in picks:
        picks.append(newest[0])

    mismatched = 0
    for vin in picks:
        for table, key in (("vehicle", "vin"),):
            cols = ", ".join(sqlite_columns(src, table))
            q = f"SELECT {cols} FROM {table} WHERE {key} = ?"
            if src.execute(q, (vin,)).fetchone() != dest.execute(q, (vin,)).fetchone():
                _fail(failures, "row", f"vehicle {vin} differs")
                mismatched += 1
        for table in ("event", "task"):
            cols = ", ".join(sqlite_columns(src, table))
            q = (f"SELECT {cols} FROM {table} WHERE vin = ? "
                 f"ORDER BY {ORDER_BY[table]}")
            if (src.execute(q, (vin,)).fetchall()
                    != dest.execute(q, (vin,)).fetchall()):
                _fail(failures, "row", f"{table} rows for {vin} differ")
                mismatched += 1
    for table in ("sync_run", "pending_identity"):
        cols = ", ".join(sqlite_columns(src, table))
        q = f"SELECT {cols} FROM {table} ORDER BY {ORDER_BY[table]}"
        if src.execute(q).fetchall() != dest.execute(q).fetchall():
            _fail(failures, "row", f"{table} full-table compare differs")
            mismatched += 1
    if mismatched == 0:
        _ok("rows", f"{len(picks)} sampled VINs + sync_run + "
                    "pending_identity identical")
    report["sampled_vins"] = picks

    return failures


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Migrate a LotSync/DealerDOH SQLite backup into an "
                    "empty PostgreSQL database, then validate exactly.")
    ap.add_argument("--source", required=True,
                    help="Path to the SQLite BACKUP file (opened read-only)")
    ap.add_argument("--dest-dsn-env", default="MIGRATE_DEST_DSN",
                    help="Name of the env var holding the destination DSN "
                         "(default MIGRATE_DEST_DSN; DSNs are never CLI args)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true",
                      help="Perform the migration (default is a dry run)")
    mode.add_argument("--validate-only", action="store_true",
                      help="Only validate an already-migrated destination")
    ap.add_argument("--wipe-destination", action="store_true",
                    help="Drop existing application tables in the destination "
                         "first (recovery for an interrupted import)")
    ap.add_argument("--i-am-migrating-production", action="store_true",
                    help="Required for any non-local destination host; "
                         "prompts for a typed confirmation phrase")
    ap.add_argument("--sample-vins", type=int, default=10)
    ap.add_argument("--report", help="Write a JSON report to this path")
    args = ap.parse_args(argv)

    report = {"mode": ("validate-only" if args.validate_only
                       else "execute" if args.execute else "dry-run"),
              "timings_seconds": {}}
    timings = report["timings_seconds"]
    t_total = time.monotonic()

    try:
        dsn = read_dsn(args.dest_dsn_env)
        enforce_target_guard(dsn, args.i_am_migrating_production)

        log(f"[1/6] source preflight: {args.source}")
        t = time.monotonic()
        src = open_source(args.source)
        preflight_source(src, args.source, report)
        timings["source_preflight"] = round(time.monotonic() - t, 3)
        log(f"      integrity ok, schema v{report['source']['schema_version']}, "
            f"{sum(report['source']['counts'].values())} business rows, "
            f"sha256 {report['source']['sha256'][:12]}...")

        log(f"[2/6] destination connect (host: {dsn_host(dsn)})")
        dest = connect_dest(dsn)

        existing = dest_business_rows(dest)
        nonempty = {t_: n for t_, n in existing.items() if n > 0}

        if args.validate_only:
            log("[3-5/6] skipped (validate-only)")
        else:
            if nonempty and not args.wipe_destination:
                raise Refusal(
                    f"Destination already contains rows: {nonempty}. "
                    "Refusing to import into a non-empty database. If this "
                    "is a deliberate re-run after a failed import, pass "
                    "--wipe-destination."
                )
            if not args.execute:
                log("[3/6] DRY RUN -- no writes. Would apply migrations "
                    f"0001-000{EXPECTED_SCHEMA_VERSION}, copy "
                    f"{sum(report['source']['counts'].values())} rows into "
                    f"{len(TABLE_ORDER)} tables"
                    + (", after wiping existing tables"
                       if args.wipe_destination else "")
                    + ". Re-run with --execute to perform the migration.")
                report["dry_run_destination_state"] = existing
                _write_report(args.report, report, ok=True)
                return 0

            if args.wipe_destination and (nonempty or existing):
                t = time.monotonic()
                wipe_destination(dest)
                timings["wipe"] = round(time.monotonic() - t, 3)

            log("[3/6] applying PostgreSQL migrations 0001-000%d"
                % EXPECTED_SCHEMA_VERSION)
            t = time.monotonic()
            apply_schema(dest)
            timings["schema_migration"] = round(time.monotonic() - t, 3)

            post_schema_rows = {t_: n for t_, n in
                                dest_business_rows(dest).items() if n > 0}
            if post_schema_rows:
                raise Refusal(
                    f"Destination has rows after schema apply: "
                    f"{post_schema_rows} -- refusing to copy on top."
                )

            log("[4/6] copying tables (FK-safe order, IDs preserved)")
            t = time.monotonic()
            copy_tables(src, dest, report)
            timings["data_copy"] = round(time.monotonic() - t, 3)

            log("[5/6] resetting identity sequences")
            t = time.monotonic()
            reset_sequences(src, dest, report)
            timings["sequence_reset"] = round(time.monotonic() - t, 3)

        log("[6/6] validation (structural, counts, invariants, rows)")
        t = time.monotonic()
        failures = validate(src, dest, report, args.sample_vins)
        timings["validation"] = round(time.monotonic() - t, 3)
        timings["total"] = round(time.monotonic() - t_total, 3)

        report["failures"] = failures
        if failures:
            log(f"\nVALIDATION FAILED -- {len(failures)} failure(s):")
            for f in failures:
                log(f"  - {f['check']}: {f['detail']}")
            log("Destination must NOT be cut over. Keep the source "
                "authoritative and diagnose.")
            _write_report(args.report, report, ok=False)
            return 2

        log(f"\nMIGRATION VALID -- all checks passed in "
            f"{timings['total']}s total.")
        _write_report(args.report, report, ok=True)
        return 0

    except Refusal as exc:
        log(f"\nREFUSED: {exc}")
        report["refusal"] = str(exc)
        _write_report(args.report, report, ok=False)
        return 3
    finally:
        try:
            src.close()
        except Exception:
            pass
        try:
            dest.close()
        except Exception:
            pass


def _write_report(path, report, ok):
    report["result"] = "PASS" if ok else "FAIL"
    if path:
        with open(path, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        log(f"report written: {path}")


if __name__ == "__main__":
    sys.exit(main())
