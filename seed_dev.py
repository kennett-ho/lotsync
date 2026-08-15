"""
seed_dev.py -- disposable synthetic development database seeder.

Sprint 02 (DealerDOH development environment foundation): boots a
development deployment with clearly-synthetic data by running the
existing, unmodified reconciliation pipeline (main.py) over the
checked-in synthetic fixtures the test suite already uses
(tests/fixtures/synthetic/). No new data shape is invented here --
if the pipeline's behavior changes, the seed changes with it, and the
seeded database can never drift from what the tests already exercise.

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

On the Render development service, chain this before uvicorn in the
start command. The free tier's filesystem is ephemeral, so every
deploy/restart reseeds from scratch -- deliberate: the development
database is disposable by design.

Determinism note: record content is fully determined by the fixtures;
"today"-relative values (sync date, aging buckets) follow
tests/fixtures/synthetic/test_config.xlsx's Settings sheet, same as
the test suite.
"""

import argparse
import os
import sqlite3
import sys

# The one path this script must never write to. Kept as a literal, not
# an import from config, so the guardrail can run before any lotsync
# module (and its import-time env reading) is touched.
PRODUCTION_DB_PATH = "/var/data/lotsync.db"

_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_FIXTURES = os.path.join(_REPO_ROOT, "tests", "fixtures", "synthetic")


def resolve_env():
    """
    The paths the pipeline will run with: anything already set in the
    environment wins (a deployment configures itself); everything else
    falls back to seed-specific defaults that cannot collide with a
    developer's real local data.
    """
    return {
        "LOTSYNC_DB_PATH": os.environ.get("LOTSYNC_DB_PATH")
            or os.path.join(_REPO_ROOT, "data", "dealerdoh-dev-seed.db"),
        "LOTSYNC_UPLOADS_DIR": os.environ.get("LOTSYNC_UPLOADS_DIR") or _FIXTURES,
        "LOTSYNC_CONFIG_PATH": os.environ.get("LOTSYNC_CONFIG_PATH")
            or os.path.join(_FIXTURES, "test_config.xlsx"),
        "LOTSYNC_OUT_DIR": os.environ.get("LOTSYNC_OUT_DIR")
            or os.path.join(_REPO_ROOT, "data", "outputs-dev-seed"),
    }


def refuse_if_production(db_path: str) -> None:
    if os.environ.get("ENVIRONMENT", "").strip().lower() == "production":
        sys.exit(
            "seed_dev.py: refusing to run -- ENVIRONMENT=production. "
            "This seeder is for development environments only."
        )
    if os.path.normpath(db_path).replace("\\", "/") == PRODUCTION_DB_PATH:
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

    env = resolve_env()
    db_path = env["LOTSYNC_DB_PATH"]
    refuse_if_production(db_path)

    if args.reset and os.path.exists(db_path):
        os.remove(db_path)
        print(f"seed_dev: removed existing dev database {db_path}")

    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs(env["LOTSYNC_OUT_DIR"], exist_ok=True)
    os.environ.update(env)

    # Import only AFTER the environment is final: config/settings.py,
    # utils/file_resolution.py, and database/repository.py all read
    # their env vars at import time (module-level constants).
    try:
        from lotsync.main import main as run_pipeline
    except ImportError:
        # Local convenience: the repo checkout is named "lotsync", so
        # its parent directory on sys.path satisfies the `from
        # lotsync.x import y` convention (see README.md / render.yaml).
        sys.path.insert(0, os.path.dirname(_REPO_ROOT))
        from lotsync.main import main as run_pipeline

    run_pipeline()

    conn = sqlite3.connect(db_path)
    try:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("vehicle", "event", "task", "recommendation", "sync_run")
        }
    finally:
        conn.close()

    print(
        "\nseed_dev complete (synthetic data only): "
        + ", ".join(f"{table}={count}" for table, count in counts.items())
        + f"\n  database: {db_path}"
    )


if __name__ == "__main__":
    main()
