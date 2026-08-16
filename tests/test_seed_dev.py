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
            self.assertEqual(migrations, 9, "seed DB should be at migration 0009")


if __name__ == "__main__":
    unittest.main()
