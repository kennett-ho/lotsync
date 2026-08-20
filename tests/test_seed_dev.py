"""
Sprint 02 -- seed_dev.py, the disposable synthetic development
database seeder.

Every test here runs seed_dev.py as a SUBPROCESS, not an import: the
lotsync config modules read their env vars at import time, and this
test process has already imported them with different values. A fresh
interpreter per run is the only honest way to test env-driven startup
behavior. PYTHONPATH is set the same way the suite itself is run
(repo parent directory -- the checkout is named `lotsync`).
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SEED = os.path.join(_REPO_ROOT, "seed_dev.py")


def _run_seed(extra_env, args=()):
    env = os.environ.copy()
    env.pop("ENVIRONMENT", None)  # start each case from a clean slate
    # Sprint 03: these subprocess tests exercise the SQLite seeding
    # path deterministically regardless of which engine the *suite* is
    # running under -- otherwise a postgres-mode suite would have the
    # seed subprocess write into the shared runtime database. The
    # postgres seeding path has its own guardrails in seed_dev.py and
    # is exercised operationally against the disposable dev database.
    env["DATABASE_ENGINE"] = "sqlite"
    env.pop("DATABASE_URL", None)
    env["PYTHONPATH"] = os.path.dirname(_REPO_ROOT)
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, _SEED, *args],
        capture_output=True, text=True, env=env, cwd=_REPO_ROOT, timeout=300,
    )


class SeedGuardrailTest(unittest.TestCase):
    def test_refuses_when_environment_is_production(self):
        result = _run_seed({"ENVIRONMENT": "production"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to run", result.stderr)
        self.assertIn("production", result.stderr)

    def test_refuses_production_database_path(self):
        result = _run_seed({"LOTSYNC_DB_PATH": "/var/data/lotsync.db"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to run", result.stderr)
        self.assertIn("/var/data/lotsync.db", result.stderr)

    def test_refuses_production_path_with_backslashes(self):
        result = _run_seed({"LOTSYNC_DB_PATH": r"\var\data\lotsync.db"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to run", result.stderr)


class PostgresResetGuardTest(unittest.TestCase):
    """Sprint 13 (finding F1): the destructive PostgreSQL --reset drops
    every application table from whatever DATABASE_URL names, so it fails
    CLOSED -- it proceeds only when ENVIRONMENT positively names a
    development environment, not merely when it is not the literal
    'production'. Unit-tested directly (the guard reads env at call time,
    not import time) so no live PostgreSQL is needed -- the guard runs
    before any connection is opened."""

    def _refuse(self, environment, *, resetting=True, engine="postgres"):
        import importlib
        from unittest import mock
        seed_dev = importlib.import_module("lotsync.seed_dev")
        env = {} if environment is None else {"ENVIRONMENT": environment}
        with mock.patch.dict(os.environ, env, clear=False):
            if environment is None:
                os.environ.pop("ENVIRONMENT", None)
            return seed_dev.refuse_if_production(
                None, resetting=resetting, engine=engine)

    def test_refuses_postgres_reset_when_environment_unset(self):
        with self.assertRaises(SystemExit) as cm:
            self._refuse(None)
        self.assertIn("does not explicitly name a development environment", str(cm.exception))

    def test_refuses_postgres_reset_for_ambiguous_environment(self):
        for value in ("prod", "staging", "prd", "live", "qa"):
            with self.assertRaises(SystemExit, msg=value):
                self._refuse(value)

    def test_refuses_postgres_reset_for_production(self):
        with self.assertRaises(SystemExit):
            self._refuse("production")

    def test_allows_postgres_reset_for_development_environments(self):
        # ENVIRONMENT explicitly naming dev passes the guard (it returns
        # None; the missing-DSN failure would come later, past this guard).
        for value in ("development", "local", "test", "DEVELOPMENT"):
            self.assertIsNone(self._refuse(value), value)

    def test_non_reset_postgres_is_not_gated_by_this_check(self):
        # A non-destructive run (no --reset) does not require the dev
        # affirmation -- only the table-dropping path fails closed.
        self.assertIsNone(self._refuse(None, resetting=False))


class SeedRunTest(unittest.TestCase):
    def test_seeds_a_synthetic_database_from_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "dev-seed.db")
            result = _run_seed({
                "LOTSYNC_DB_PATH": db_path,
                "LOTSYNC_OUT_DIR": os.path.join(tmp, "outputs"),
            })
            self.assertEqual(
                result.returncode, 0,
                f"seed failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("seed_dev complete", result.stdout)

            conn = sqlite3.connect(db_path)
            try:
                vehicles = conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()[0]
                sync_runs = conn.execute("SELECT COUNT(*) FROM sync_run").fetchone()[0]
                migrations = conn.execute(
                    "SELECT COUNT(*) FROM schema_migrations"
                ).fetchone()[0]
            finally:
                conn.close()

            self.assertGreater(vehicles, 0, "seed produced no vehicles")
            self.assertGreaterEqual(
                sync_runs, 5, "expected one sync_run per persisted source"
            )
            # Pinned to the repo's real migration count on purpose --
            # a new migration must consciously bump this (the same
            # drift guard tools/migrate_sqlite_to_postgres.py's
            # EXPECTED_SCHEMA_VERSION carries). Sprint 10: 9 -> 10
            # (0010_report_baseline).
            self.assertEqual(migrations, 10, "seed DB should be at migration 0010")


class ResetDropListDriftGuardTest(unittest.TestCase):
    """Sprint 10 closeout: seed_dev's postgres --reset drops exactly
    _APP_TABLES -- a list that MUST cover every business table the
    migrations create, or a reset silently leaves stale rows behind
    (exactly what happened when 0010's report_baseline landed without
    being added here: DROP ... CASCADE tolerated the dangling FK and
    CREATE TABLE IF NOT EXISTS kept the survivor, so nothing failed).
    The migrate tool's TABLE_ORDER is the maintained census of
    business tables, so pin the two lists together: every TABLE_ORDER
    table must be in _APP_TABLES. A new migration that updates one
    list but not the other now fails here instead of corrupting the
    next reseed."""

    def test_every_migrated_business_table_is_dropped_by_reset(self):
        import importlib.util

        def load(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        seed = load("seed_dev_module", _SEED)
        tool = load("migrate_tool_module",
                    os.path.join(_REPO_ROOT, "tools", "migrate_sqlite_to_postgres.py"))
        missing = [t for t in tool.TABLE_ORDER if t not in seed._APP_TABLES]
        self.assertEqual(missing, [],
                         "tables the migrations create but --reset would not drop")
        self.assertIn("schema_migrations", seed._APP_TABLES,
                      "reset must also drop the migration bookkeeping")


if __name__ == "__main__":
    unittest.main()
