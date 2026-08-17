"""
seed_dev.py -- the DealerDOH DEV synthetic QA dealership seeder.

Sprint 02 established this as the development seeder (running main.py
over the unit-test fixtures); Sprint 04 upgraded it to seed the
standing QA dealership instead: dev_seed/'s deliberately constructed
scenario roster (SYNTHETIC_QA_MATRIX.md), replayed as two consecutive
sync days through sync/pipeline.py's run_inventory_sync -- the same
code path the Inventory Sync API drives. The principle is unchanged:
no data shape is invented at seed time; if pipeline behavior changes,
the seeded database changes with it, and tests/test_qa_dataset.py
asserts the expected outcomes on both persistence engines.

Safety guardrails (see .claude/workflows/data-migration.md -- the
default target is ALWAYS non-production):

- refuses to run when ENVIRONMENT=production
- refuses to run against the production database path
  (/var/data/lotsync.db -- see PRODUCTION_BASELINE.md)
- defaults to its own database file (data/dealerdoh-dev-seed.db) and
  its own output folder, NOT the app's defaults, so a developer's real
  local working database and generated reports are never touched by
  accident

Usage:

    PYTHONPATH=.. python seed_dev.py [--reset]

    --reset    delete the target dev database file first, so the seed
               starts from an empty schema (never allowed against the
               production path -- see guardrails above)

The deployed dev database (Supabase PostgreSQL) is persistent and is
NOT reseeded on boot -- running this script is an explicit operator
action (see DEV_QA_GUIDE.md's reseed procedure). Standing totals after
a reset+seed are exact and documented in SYNTHETIC_QA_MATRIX.md.

Determinism note: every date the business rules read (sync dates,
checkout dates, stocked-in dates, sold dates) is pinned relative to
dev_seed/scenarios.py's REFERENCE_DATE (2026-07-21) -- expected
outcomes never decay as the calendar advances. Only display-oriented
timestamps (observed_at, created_at, sync-run timing) are wall-clock.
"""

import argparse
import os
import sys

# The one path this script must never write to. Kept as a literal, not
# an import from config, so the guardrail can run before any lotsync
# module (and its import-time env reading) is touched.
PRODUCTION_DB_PATH = "/var/data/lotsync.db"

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# Sprint 03: everything the seed writes lives in these tables --
# --reset's postgres path drops exactly this set (plus the migration
# bookkeeping) so the next run starts from a clean, re-migrated schema.
#
# Sprint 10 closeout: report_baseline added (migrations/0010). It was
# missed when 0010 landed, and because the reset's DROP ... CASCADE
# tolerates the FK and 0010 is CREATE TABLE IF NOT EXISTS, the miss
# was SILENT: a reseed would have left stale baseline rows behind,
# and the next real sync would have compared against them (false
# suspicious-count warnings). tests/test_seed_dev.py now pins this
# list against tools/migrate_sqlite_to_postgres.py's TABLE_ORDER so
# the next migration cannot repeat the drift.
_APP_TABLES = (
    "report_baseline",
    "event_freshness", "task_execution_event", "recommendation", "task",
    "event", "pending_identity", "sync_run", "user_membership", "employee",
    "dealership", "organization", "vehicle", "schema_migrations",
)


def _engine() -> str:
    return os.environ.get("DATABASE_ENGINE", "sqlite").strip().lower()


def resolve_env():
    """
    The paths the pipeline will run with: anything already set in the
    environment wins (a deployment configures itself); everything else
    falls back to seed-specific defaults that cannot collide with a
    developer's real local data. LOTSYNC_DB_PATH is a SQLite concept --
    under DATABASE_ENGINE=postgres the target database comes from
    DATABASE_URL instead and no path default is invented here.
    """
    env = {
        "LOTSYNC_OUT_DIR": os.environ.get("LOTSYNC_OUT_DIR")
            or os.path.join(_REPO_ROOT, "data", "outputs-dev-seed"),
    }
    if _engine() == "sqlite":
        env["LOTSYNC_DB_PATH"] = (
            os.environ.get("LOTSYNC_DB_PATH")
            or os.path.join(_REPO_ROOT, "data", "dealerdoh-dev-seed.db")
        )
    return env


def refuse_if_production(db_path: str = None) -> None:
    if os.environ.get("ENVIRONMENT", "").strip().lower() == "production":
        sys.exit(
            "seed_dev.py: refusing to run -- ENVIRONMENT=production. "
            "This seeder is for development environments only."
        )
    if db_path is not None and os.path.normpath(db_path).replace("\\", "/") == PRODUCTION_DB_PATH:
        sys.exit(
            "seed_dev.py: refusing to run -- LOTSYNC_DB_PATH is the "
            f"production database path ({PRODUCTION_DB_PATH}). "
            "Seeding production is never allowed; see PRODUCTION_BASELINE.md."
        )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Seed a disposable synthetic DealerDOH development database."
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="delete the target dev database file before seeding",
    )
    args = parser.parse_args(argv)

    engine = _engine()
    env = resolve_env()
    db_path = env.get("LOTSYNC_DB_PATH")
    refuse_if_production(db_path)

    if args.reset:
        if engine == "sqlite":
            if db_path and os.path.exists(db_path):
                os.remove(db_path)
                print(f"seed_dev: removed existing dev database {db_path}")
        else:
            # PostgreSQL reset: drop the application tables (and the
            # migration bookkeeping) so connect() re-migrates a clean
            # schema. Development-only by construction -- the
            # ENVIRONMENT=production guard above has already run, and
            # production has no PostgreSQL database at all this sprint.
            _reset_postgres()

    if db_path:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    os.makedirs(env["LOTSYNC_OUT_DIR"], exist_ok=True)
    os.environ.update(env)

    # Import only AFTER the environment is final: config/settings.py,
    # utils/file_resolution.py, and database/repository.py all read
    # their env vars at import time (module-level constants).
    try:
        from lotsync.database.repository import connect as db_connect
    except ImportError:
        # Local convenience: the repo checkout is named "lotsync", so
        # its parent directory on sys.path satisfies the `from
        # lotsync.x import y` convention (see README.md / render.yaml).
        sys.path.insert(0, os.path.dirname(_REPO_ROOT))
        from lotsync.database.repository import connect as db_connect
    from lotsync.dev_seed.seeder import run_qa_seed

    # One connection for the whole seed, engine-dispatched -- never a
    # raw sqlite3.connect, which would be wrong (and empty) under
    # DATABASE_ENGINE=postgres.
    conn = db_connect(db_path if engine == "sqlite" else None)
    try:
        run_qa_seed(conn, out_dir=env["LOTSYNC_OUT_DIR"])
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("vehicle", "event", "task", "recommendation",
                          "pending_identity", "sync_run")
        }
    finally:
        conn.close()

    target = db_path if engine == "sqlite" else "PostgreSQL runtime database (DATABASE_URL; DSN not printed)"
    print(
        "\nseed_dev complete (synthetic data only): "
        + ", ".join(f"{table}={count}" for table, count in counts.items())
        + f"\n  engine: {engine}\n  database: {target}"
    )


def _reset_postgres() -> None:
    sys.path.insert(0, os.path.dirname(_REPO_ROOT))
    from lotsync.database import engine as db_engine

    conn = db_engine.connect_postgres(None)
    try:
        for table in _APP_TABLES:
            conn.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        conn.commit()
        print(f"seed_dev: dropped {len(_APP_TABLES)} application tables (postgres reset)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
