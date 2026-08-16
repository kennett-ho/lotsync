"""
Sprint 07 -- tests for tools/migrate_sqlite_to_postgres.py, the
production SQLite -> PostgreSQL migration tool, and its rehearsal
dataset generator.

These run ONLY under the PostgreSQL engine (CI's "Backend tests
(PostgreSQL)" job, or any environment with DATABASE_ENGINE=postgres
and DATABASE_URL set) and self-skip under SQLite, mirroring the
existing engine-specific-skip convention. Each test gets a private,
dropped-after schema on the target server via a search_path-scoped
DSN, so nothing here ever touches shared data.

The tool is exercised through its REAL CLI (subprocess): exit codes,
refusal messages, and the JSON report are the operator contract the
production cutover depends on, so that is what these tests pin down.
The small-scale deterministic fixture (~120 vehicles) keeps this fast
enough for every CI push; the full ~4,700-vehicle rehearsal is the
operator-run procedure documented in PRODUCTION_MIGRATION_REHEARSAL.md,
deliberately not part of CI.
"""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

from lotsync.database import engine as db_engine

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOL = os.path.join(_REPO, "tools", "migrate_sqlite_to_postgres.py")
_GENERATOR = os.path.join(_REPO, "tools", "generate_rehearsal_dataset.py")

_ON_POSTGRES = (db_engine.get_engine() == "postgres"
                and bool(os.environ.get("DATABASE_URL", "").strip()))


def _scoped_dsn(schema: str) -> str:
    """The base DATABASE_URL, scoped so every unqualified statement the
    tool runs lands in `schema` (psycopg passes options to the server;
    %3D is '=' -- the separator inside the options value)."""
    base = os.environ["DATABASE_URL"]
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}options=-csearch_path%3D{schema}"


def _run_tool(args, dsn: str):
    env = dict(os.environ)
    env["MIGRATE_DEST_DSN"] = dsn
    env["PYTHONPATH"] = os.path.dirname(_REPO)
    proc = subprocess.run(
        [sys.executable, _TOOL, *args],
        capture_output=True, text=True, env=env, timeout=300,
        stdin=subprocess.DEVNULL)
    return proc


@unittest.skipIf(not _ON_POSTGRES,
                 "migration-tool tests need DATABASE_ENGINE=postgres "
                 "and DATABASE_URL (the PostgreSQL CI job)")
class MigrationToolTest(unittest.TestCase):
    """One generated source fixture per class; one schema per test."""

    @classmethod
    def setUpClass(cls):
        import psycopg

        cls.tmp = tempfile.TemporaryDirectory()
        cls.source = os.path.join(cls.tmp.name, "fixture.db")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.dirname(_REPO)
        env.pop("DATABASE_ENGINE", None)  # generator requires sqlite
        gen = subprocess.run(
            [sys.executable, _GENERATOR, "--out", cls.source,
             "--scale", "small"],
            capture_output=True, text=True, env=env, timeout=300)
        assert gen.returncode == 0, gen.stderr
        cls.manifest = json.loads(gen.stdout)
        cls.admin = psycopg.connect(os.environ["DATABASE_URL"],
                                    prepare_threshold=None, autocommit=True)

    @classmethod
    def tearDownClass(cls):
        cls.admin.close()
        cls.tmp.cleanup()

    def setUp(self):
        self.schema = "migtest_" + uuid.uuid4().hex[:12]
        self.admin.execute(f'CREATE SCHEMA "{self.schema}"')
        self.dsn = _scoped_dsn(self.schema)

    def tearDown(self):
        self.admin.execute(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE')

    def _connect_dest(self):
        import psycopg

        conn = psycopg.connect(self.dsn, prepare_threshold=None)
        return conn

    # ---- the operator contract ---------------------------------------

    def test_happy_path_exact_counts_and_report(self):
        report_path = os.path.join(self.tmp.name, f"{self.schema}.json")
        proc = _run_tool(["--source", self.source, "--execute",
                          "--report", report_path], self.dsn)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.load(open(report_path))
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["failures"], [])
        src = sqlite3.connect(f"file:{self.source}?mode=ro", uri=True)
        with self._connect_dest() as dest:
            for table, n in self.manifest["counts"].items():
                got = dest.execute(
                    f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                self.assertEqual(got, n, table)
            # exact ID preservation, both ends of a sparse table
            for q in ("SELECT MIN(event_id), MAX(event_id) FROM event",
                      "SELECT MIN(task_id), MAX(task_id) FROM task"):
                self.assertEqual(dest.execute(q).fetchone(),
                                 src.execute(q).fetchone())
        src.close()

    def test_sparse_sequence_reset_next_id_continues_high_water(self):
        proc = _run_tool(["--source", self.source, "--execute"], self.dsn)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        seqs = self.manifest["sqlite_sequence"]
        with self._connect_dest() as dest:
            # The generator deletes tail events, so sqlite_sequence.seq
            # (228 at small scale) exceeds MAX(event_id) (213). A new
            # insert must continue from the high-water mark, exactly as
            # SQLite would -- the production pending_identity lesson.
            row = dest.execute(
                "INSERT INTO event (vin, event_type, source, observed_at) "
                "SELECT vin, 'seq_probe', 'test', '2026-08-16T00:00:00' "
                "FROM vehicle LIMIT 1 RETURNING event_id").fetchone()
            self.assertEqual(row[0], seqs["event"] + 1)
            row = dest.execute(
                "INSERT INTO pending_identity (source, raw_identifier, "
                "identifier_type, status, first_observed_at, "
                "last_observed_at) VALUES ('test','X','stock_number',"
                "'pending','2026-08-16','2026-08-16') "
                "RETURNING pending_identity_id").fetchone()
            self.assertEqual(row[0], seqs["pending_identity"] + 1)

    def test_dry_run_is_default_and_writes_nothing(self):
        proc = _run_tool(["--source", self.source], self.dsn)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("DRY RUN", proc.stdout)
        with self._connect_dest() as dest:
            n = dest.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s", (self.schema,)).fetchone()[0]
        self.assertEqual(n, 0, "dry run must not create tables")

    def test_nonempty_destination_refused_then_wipe_recovers(self):
        first = _run_tool(["--source", self.source, "--execute"], self.dsn)
        self.assertEqual(first.returncode, 0)
        again = _run_tool(["--source", self.source, "--execute"], self.dsn)
        self.assertEqual(again.returncode, 3, again.stdout)
        self.assertIn("already contains rows", again.stdout)
        wiped = _run_tool(["--source", self.source, "--execute",
                           "--wipe-destination"], self.dsn)
        self.assertEqual(wiped.returncode, 0, wiped.stdout + wiped.stderr)

    def test_validation_catches_tampered_destination(self):
        proc = _run_tool(["--source", self.source, "--execute"], self.dsn)
        self.assertEqual(proc.returncode, 0)
        with self._connect_dest() as dest:
            dest.execute("DELETE FROM event WHERE event_id = "
                         "(SELECT MIN(event_id) FROM event)")
            dest.commit()
        check = _run_tool(["--source", self.source, "--validate-only"],
                          self.dsn)
        self.assertEqual(check.returncode, 2, check.stdout)
        self.assertIn("VALIDATION FAILED", check.stdout)
        self.assertIn("count", check.stdout)

    def test_malformed_source_refused(self):
        bogus = os.path.join(self.tmp.name, "not-a-db.txt")
        with open(bogus, "w") as fh:
            fh.write("this is not a sqlite database\n" * 100)
        proc = _run_tool(["--source", bogus, "--execute"], self.dsn)
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("REFUSED", proc.stdout)

    def test_missing_source_refused(self):
        proc = _run_tool(["--source", os.path.join(self.tmp.name, "no.db"),
                          "--execute"], self.dsn)
        self.assertEqual(proc.returncode, 3, proc.stdout)

    def test_remote_destination_refused_without_production_ceremony(self):
        # Guard must fire BEFORE any connection attempt -- a
        # non-resolvable host proves it (no timeout, immediate refusal).
        proc = _run_tool(
            ["--source", self.source, "--execute"],
            "postgresql://user@db.example-remote.invalid:5432/prod")
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("not local", proc.stdout)
        # And non-interactively, even the flag cannot proceed:
        proc = _run_tool(
            ["--source", self.source, "--execute",
             "--i-am-migrating-production"],
            "postgresql://user@db.example-remote.invalid:5432/prod")
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("REFUSED", proc.stdout)

    def test_missing_dsn_env_refused(self):
        env = dict(os.environ)
        env.pop("MIGRATE_DEST_DSN", None)
        env["PYTHONPATH"] = os.path.dirname(_REPO)
        proc = subprocess.run(
            [sys.executable, _TOOL, "--source", self.source, "--execute"],
            capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("MIGRATE_DEST_DSN", proc.stdout)


@unittest.skipIf(not _ON_POSTGRES,
                 "generator determinism is asserted alongside the "
                 "postgres tool tests to keep the sqlite job unchanged")
class GeneratorDeterminismTest(unittest.TestCase):
    def test_same_seed_same_counts_and_sequences(self):
        with tempfile.TemporaryDirectory() as tmp:
            outs = []
            for name in ("a.db", "b.db"):
                env = dict(os.environ)
                env["PYTHONPATH"] = os.path.dirname(_REPO)
                env.pop("DATABASE_ENGINE", None)
                proc = subprocess.run(
                    [sys.executable, _GENERATOR, "--out",
                     os.path.join(tmp, name), "--scale", "small"],
                    capture_output=True, text=True, env=env, timeout=300)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                outs.append(json.loads(proc.stdout))
            self.assertEqual(outs[0]["counts"], outs[1]["counts"])
            self.assertEqual(outs[0]["sqlite_sequence"],
                             outs[1]["sqlite_sequence"])
            self.assertEqual(outs[0]["max_ids"], outs[1]["max_ids"])


if __name__ == "__main__":
    unittest.main()
