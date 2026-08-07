"""
Phase 3, Sprint 4 verification -- api/routers/inventory_sync.py. Uses
FastAPI's TestClient, following tests/test_api_routes.py's
ApiTestCase pattern (an in-memory DB, wired in via get_db's dependency
override). Uploads go to a temporary directory for the duration of each
test (the router's UPLOADS_DIR module attribute is overridden directly --
see ApiTestCase.setUp), never the real data/api_uploads/.
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from lotsync.api.app import app
from lotsync.api.dependencies import get_db
from lotsync.api.routers import inventory_sync
from lotsync.database.repository import connect

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
TEKION_PATH = os.path.join(FIXTURES, "tekion_master.csv")
SOLD_PATH = os.path.join(FIXTURES, "tekion_sold.csv")
KEYPER_PATH = os.path.join(FIXTURES, "keyper.csv")


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
        self._tmp.cleanup()
        for f in self._open_files:
            f.close()

    def _files(self, **named_paths):
        """Builds TestClient's `files=` dict, keyed by the router's field names."""
        files = {}
        for name, path in named_paths.items():
            handle = open(path, "rb")
            self._open_files.append(handle)
            files[name] = (os.path.basename(path), handle, "text/csv")
        return files


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
        # Keyper's own export dropped into the Tekion Unsold slot --
        # missing "Stock #"/"VIN #"/"Stocked In Date"/"Year Make Model".
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=KEYPER_PATH),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertIn("Tekion Unsold", resp.json()["detail"][0])
        # Nothing persisted -- a bad file in one slot fails the whole request.
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM vehicle").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM sync_run").fetchone()[0], 0)


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
