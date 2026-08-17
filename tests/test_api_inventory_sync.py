"""
Phase 3, Sprint 4 verification -- api/routers/inventory_sync.py. Uses
FastAPI's TestClient, following tests/test_api_routes.py's
ApiTestCase pattern (an in-memory DB, wired in via get_db's dependency
override). Uploads go to a temporary directory for the duration of each
test (the router's UPLOADS_DIR module attribute is overridden directly --
see ApiTestCase.setUp), never the real data/api_uploads/.

Sprint 10 (Rail D) additions: the /validate preview endpoint's
zero-mutation contract, /run's own revalidation (a caller who skips
the preview hits the same boundary), the warning-acknowledgement +
fingerprint gating, baseline recording, and the end-to-end
suspicious-count flow. Unit-level boundary behavior lives in
tests/test_ingestion_validation.py; these tests prove the HTTP
surface enforces it.
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from lotsync.api.app import app
from lotsync.api.dependencies import get_db
from lotsync.api.routers import inventory_sync
from lotsync.database.repository import connect

from tests.test_ingestion_validation import write_tekion_csv

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
ADVERSARIAL = os.path.join(os.path.dirname(__file__), "fixtures", "ingestion")
TEKION_PATH = os.path.join(FIXTURES, "tekion_master.csv")
SOLD_PATH = os.path.join(FIXTURES, "tekion_sold.csv")
KEYPER_PATH = os.path.join(FIXTURES, "keyper.csv")
TEKION_HEADERS_ONLY = os.path.join(ADVERSARIAL, "tekion_headers_only.csv")
MDD_HEADERS_ONLY = os.path.join(ADVERSARIAL, "mdd_headers_only.csv")


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self._open_files = []

        # UPLOADS_DIR/OUT_DIR are computed once at module import time
        # (same convention as utils/file_resolution.py's UPLOADS_DIR and
        # config/settings.py's CONFIG_PATH) -- setting an env var this
        # late wouldn't retroactively change them, so both module
        # attributes are overridden directly instead, restored in
        # tearDown. Without this, a real end-to-end test run would write
        # into this repo's actual data/api_uploads/ and data/outputs/.
        self._tmp = tempfile.TemporaryDirectory()
        self._prev_uploads_dir = inventory_sync.UPLOADS_DIR
        self._prev_out_dir = inventory_sync.OUT_DIR
        inventory_sync.UPLOADS_DIR = os.path.join(self._tmp.name, "uploads")
        inventory_sync.OUT_DIR = os.path.join(self._tmp.name, "outputs")
        os.makedirs(inventory_sync.OUT_DIR, exist_ok=True)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.conn.close()
        inventory_sync.UPLOADS_DIR = self._prev_uploads_dir
        inventory_sync.OUT_DIR = self._prev_out_dir
        # Close handles BEFORE removing the temp tree -- Windows
        # refuses to delete a file something still holds open
        # (Sprint 10: generated fixtures now live under _tmp too).
        for f in self._open_files:
            f.close()
        self._tmp.cleanup()

    def _files(self, **named_paths):
        """Builds TestClient's `files=` dict, keyed by the router's field names."""
        files = {}
        for name, path in named_paths.items():
            handle = open(path, "rb")
            self._open_files.append(handle)
            files[name] = (os.path.basename(path), handle, "text/csv")
        return files

    MUTATION_TABLES = ("vehicle", "event", "sync_run", "task", "recommendation",
                       "pending_identity", "report_baseline")

    def _mutation_counts(self) -> dict:
        """Snapshot of everything a sync can mutate: operational table
        counts AND the report CSVs in OUT_DIR (name -> mtime)."""
        state = {t: self.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in self.MUTATION_TABLES}
        state["__reports__"] = {
            name: os.path.getmtime(os.path.join(inventory_sync.OUT_DIR, name))
            for name in sorted(os.listdir(inventory_sync.OUT_DIR))
        }
        return state

    def assert_zero_mutation(self, before: dict):
        """No DB table changed AND no operational report CSV was
        written or rewritten since `before` was captured."""
        self.assertEqual(self._mutation_counts(), before)


class RunSyncEndpointTest(ApiTestCase):
    def test_no_files_returns_422(self):
        resp = self.client.post("/inventory-sync/run")
        self.assertEqual(resp.status_code, 422)

    def test_successful_upload_returns_sync_summary(self):
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=TEKION_PATH, keyper=KEYPER_PATH),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual({r["source"] for r in body["sync_runs"]}, {"tekion", "keyper"})
        self.assertIn("triggered_at", body)
        self.assertGreaterEqual(body["vehicles_processed"], 1)

        # Reflected via the existing, unchanged read endpoint -- confirms
        # this write path and Sprint 2's read API agree on the same data.
        vehicles = self.client.get("/vehicles").json()
        self.assertTrue(any(v["vin"] == "1TESTVIN000000001" for v in vehicles))

    def test_malicious_filename_cannot_escape_the_upload_directory(self):
        """Regression test for PRE_DEPLOYMENT_REVIEW.md's Critical finding:
        a crafted client-supplied filename (path traversal) must never
        influence where the uploaded file is written on disk."""
        handle = open(TEKION_PATH, "rb")
        self._open_files.append(handle)
        files = {"tekion_unsold": ("../../../../evil.csv", handle, "text/csv")}
        resp = self.client.post("/inventory-sync/run", files=files)
        self.assertEqual(resp.status_code, 200)

        written = [
            os.path.join(root, name)
            for root, _dirs, names in os.walk(inventory_sync.UPLOADS_DIR)
            for name in names
        ]
        self.assertTrue(written, "expected at least one file written under UPLOADS_DIR")
        for path in written:
            self.assertEqual(
                os.path.commonpath([inventory_sync.UPLOADS_DIR, path]),
                os.path.normpath(inventory_sync.UPLOADS_DIR),
            )
        self.assertTrue(any(os.path.basename(p) == "tekion.csv" for p in written))
        self.assertFalse(any("evil.csv" in p for p in written))

    def test_wrong_file_in_a_slot_fails_validation_before_persisting(self):
        # Keyper's own export dropped into the Tekion Unsold slot.
        # Pre-Sprint-10 this was caught as missing required columns;
        # the Sprint 10 classifier goes further and names what the
        # file actually IS (structured 422 -- see
        # api/routers/inventory_sync.py's _reject).
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=KEYPER_PATH),
        )
        self.assertEqual(resp.status_code, 422)
        detail = resp.json()["detail"]
        self.assertEqual(detail["code"], "REPORT_VALIDATION_FAILED")
        report = detail["validation"]["reports"][0]
        self.assertEqual(report["slot"], "tekion")
        self.assertEqual(report["status"], "rejected")
        self.assertEqual(report["detected"]["contract_id"], "keyper_full_inventory")
        self.assertIn("WRONG_REPORT_TYPE", [i["code"] for i in report["issues"]])
        self.assertIn("Tekion Unsold", report["issues"][0]["message"])
        # Nothing persisted -- a bad file in one slot fails the whole request.
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sync_run").fetchone()[0], 0)


class ValidateEndpointTest(ApiTestCase):
    """Sprint 10: POST /inventory-sync/validate -- the pre-sync
    preview. Always 200 with the full per-report result (rejections
    included -- it is a preview, not a gate), and NEVER mutates."""

    def test_no_files_returns_422(self):
        resp = self.client.post("/inventory-sync/validate")
        self.assertEqual(resp.status_code, 422)

    def test_happy_set_reports_ready_with_fingerprints(self):
        before = self._mutation_counts()
        resp = self.client.post(
            "/inventory-sync/validate",
            files=self._files(tekion_unsold=TEKION_PATH, keyper=KEYPER_PATH),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ready")
        self.assertFalse(body["requires_acknowledgement"])
        self.assertTrue(body["fingerprint"])
        self.assertEqual({r["slot"] for r in body["reports"]}, {"tekion", "keyper"})
        for report in body["reports"]:
            self.assertEqual(report["status"], "ready")
            self.assertTrue(report["fingerprint"])
        self.assert_zero_mutation(before)

    def test_rejected_report_is_described_not_executed(self):
        before = self._mutation_counts()
        resp = self.client.post(
            "/inventory-sync/validate",
            files=self._files(tekion_unsold=TEKION_HEADERS_ONLY),
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "rejected")
        self.assertEqual(body["reports"][0]["stats"]["total_rows"], 0)
        self.assertIn("NO_DATA_ROWS",
                      [i["code"] for i in body["reports"][0]["issues"]])
        self.assert_zero_mutation(before)

    def test_uploaded_bytes_are_deleted_after_the_preview(self):
        self.client.post(
            "/inventory-sync/validate",
            files=self._files(tekion_unsold=TEKION_PATH),
        )
        leftovers = [
            os.path.join(root, name)
            for root, _dirs, names in os.walk(inventory_sync.UPLOADS_DIR)
            for name in names
        ]
        self.assertEqual(leftovers, [])


class RunRevalidationTest(ApiTestCase):
    """Sprint 10 phase 18: /run recomputes the entire boundary itself.
    Skipping the preview, replacing files after previewing, or
    asserting acknowledgement blind all fail closed -- and a
    validation failure leaves ZERO operational mutation."""

    def _validate(self, **named_paths) -> dict:
        resp = self.client.post("/inventory-sync/validate", files=self._files(**named_paths))
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def test_empty_authoritative_snapshot_is_rejected_with_zero_mutation(self):
        before = self._mutation_counts()
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=TEKION_HEADERS_ONLY, keyper=KEYPER_PATH),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["detail"]["code"], "REPORT_VALIDATION_FAILED")
        self.assert_zero_mutation(before)

    def test_warning_without_acknowledgement_is_409_with_zero_mutation(self):
        before = self._mutation_counts()
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(mdd=MDD_HEADERS_ONLY),
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "WARNINGS_NOT_ACKNOWLEDGED")
        self.assert_zero_mutation(before)

    def test_blind_acknowledgement_without_fingerprint_fails_closed(self):
        # "Client lies about warning state": asserting the box was
        # ticked without proving WHICH bytes were reviewed.
        before = self._mutation_counts()
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(mdd=MDD_HEADERS_ONLY),
            data={"acknowledge_warnings": "true"},
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "STALE_VALIDATION")
        self.assert_zero_mutation(before)

    def test_stale_fingerprint_after_file_swap_fails_closed(self):
        validation = self._validate(mdd=MDD_HEADERS_ONLY)
        # Swap direction 1: previewed the WARNING file, but the run
        # carries a CLEAN file. No warnings exist at run time, so the
        # fingerprint is irrelevant and the run proceeds -- fingerprints
        # only bind acknowledgements, they are not a general freshness
        # check.
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(mdd=os.path.join(FIXTURES, "mdd_not_paired.csv")),
            data={"acknowledge_warnings": "true",
                  "validation_fingerprint": validation["fingerprint"]},
        )
        self.assertEqual(resp.status_code, 200)
        before = self._mutation_counts()
        clean = self._validate(mdd=os.path.join(FIXTURES, "mdd_not_paired.csv"))
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(mdd=MDD_HEADERS_ONLY),
            data={"acknowledge_warnings": "true",
                  "validation_fingerprint": clean["fingerprint"]},
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "STALE_VALIDATION")
        self.assert_zero_mutation(before)

    def test_acknowledged_warning_with_matching_fingerprint_runs(self):
        validation = self._validate(mdd=MDD_HEADERS_ONLY)
        self.assertTrue(validation["requires_acknowledgement"])
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(mdd=MDD_HEADERS_ONLY),
            data={"acknowledge_warnings": "true",
                  "validation_fingerprint": validation["fingerprint"]},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # The acknowledged zero is recorded AS a zero -- a human said
        # "every vehicle is paired" and the run reflects exactly that.
        self.assertEqual([r["source"] for r in body["sync_runs"]], ["mdd"])
        self.assertEqual(body["sync_runs"][0]["records_processed"], 0)

    def test_successful_run_records_scoped_baselines(self):
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=TEKION_PATH, tekion_sold=SOLD_PATH),
        )
        self.assertEqual(resp.status_code, 200)
        rows = self.conn.execute(
            "SELECT vendor, report_type, valid_rows FROM report_baseline "
            "ORDER BY report_type"
        ).fetchall()
        # BOTH Tekion report types get their own baseline row -- the
        # scoping sync_run.records_processed (one combined 'tekion'
        # number) could never provide.
        self.assertEqual([(v, rt) for v, rt, _ in rows],
                         [("tekion", "current_inventory"), ("tekion", "sold_inventory")])
        self.assertTrue(all(count > 0 for _, _, count in rows))

    def test_suspicious_count_flow_end_to_end(self):
        # Generated under the test case's own temp tree (cleaned after
        # handles close -- see tearDown's ordering note).
        big = os.path.join(self._tmp.name, "big.csv")
        small = os.path.join(self._tmp.name, "small.csv")
        write_tekion_csv(big, 40)
        write_tekion_csv(small, 20)

        # Run 1 (40 rows) establishes the baseline.
        resp = self.client.post("/inventory-sync/run",
                                 files=self._files(tekion_unsold=big))
        self.assertEqual(resp.status_code, 200)

        # Run 2 (20 rows, -50%) must NOT process silently.
        resp = self.client.post("/inventory-sync/run",
                                 files=self._files(tekion_unsold=small))
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertEqual(detail["code"], "WARNINGS_NOT_ACKNOWLEDGED")
        report = detail["validation"]["reports"][0]
        self.assertIn("SUSPICIOUS_COUNT_DROP",
                      [i["code"] for i in report["issues"]])
        self.assertEqual(report["baseline"]["previous_rows"], 40)
        self.assertEqual(report["baseline"]["change"], -20)

        # Preview + explicit acknowledgement processes it, and the
        # baseline moves to 20.
        validation = self._validate(tekion_unsold=small)
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=small),
            data={"acknowledge_warnings": "true",
                  "validation_fingerprint": validation["fingerprint"]},
        )
        self.assertEqual(resp.status_code, 200)
        latest = self.conn.execute(
            "SELECT valid_rows FROM report_baseline "
            "WHERE report_type = 'current_inventory' "
            "ORDER BY report_baseline_id DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(latest[0], 20)

    def test_missing_keyper_still_warns_in_the_summary(self):
        # Phase 23: the pre-existing missing-evidence semantics are
        # untouched -- a sync without Keyper skips RecovR-dependent
        # task generation AND says so.
        resp = self.client.post("/inventory-sync/run",
                                 files=self._files(tekion_unsold=TEKION_PATH))
        self.assertEqual(resp.status_code, 200)
        warnings = resp.json()["warnings"]
        self.assertTrue(any("Keyper report was not provided" in w for w in warnings))


class HistoryAndExceptionsEndpointTest(ApiTestCase):
    def test_history_reflects_a_completed_run(self):
        self.client.post("/inventory-sync/run", files=self._files(tekion_unsold=TEKION_PATH))
        history = self.client.get("/inventory-sync/history").json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["sources"][0]["source"], "tekion")
        self.assertEqual(history[0]["overall_status"], "complete")

    def test_exceptions_reflects_pending_identities(self):
        self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=TEKION_PATH, keyper=KEYPER_PATH),
        )
        exceptions = self.client.get("/inventory-sync/exceptions").json()
        # 784 / #ODD1 / 555555 -- see tests/fixtures/README.md.
        self.assertEqual(len(exceptions), 3)
        self.assertTrue(all(e["status"] == "pending" for e in exceptions))

    def test_empty_database_returns_empty_lists(self):
        self.assertEqual(self.client.get("/inventory-sync/history").json(), [])
        self.assertEqual(self.client.get("/inventory-sync/exceptions").json(), [])


if __name__ == "__main__":
    unittest.main()
