"""
Sprint 13 (Rail H) -- security response headers and the environment-gated
API documentation decision.

The headers are added by api/app.py's middleware to EVERY response (the
success path, the 404, and the generic 500), so a refactor that drops
them fails here. The docs gating is verified two ways: enabled in the
test environment (in-process), and disabled under ENVIRONMENT=production
in a fresh interpreter (subprocess -- docs_url is fixed at app
construction/import time, the same reason test_seed_dev.py uses
subprocesses for env-driven startup behavior).
"""

import os
import subprocess
import sys
import unittest

from fastapi.testclient import TestClient

from lotsync.api.app import app, _SECURITY_HEADERS
from lotsync.api.dependencies import get_db
from lotsync.database.repository import connect

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SecurityHeadersTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.conn.close()

    def _assert_all_headers(self, resp, where):
        for name, value in _SECURITY_HEADERS.items():
            self.assertEqual(resp.headers.get(name), value,
                             f"{name} missing/wrong on {where}")

    def test_expected_header_values(self):
        # The policy itself -- pinned so a weakening edit is visible.
        self.assertEqual(_SECURITY_HEADERS["X-Content-Type-Options"], "nosniff")
        self.assertEqual(_SECURITY_HEADERS["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", _SECURITY_HEADERS["Content-Security-Policy"])
        self.assertEqual(_SECURITY_HEADERS["Referrer-Policy"], "no-referrer")
        self.assertEqual(_SECURITY_HEADERS["Cache-Control"], "no-store")

    def test_headers_on_success_response(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self._assert_all_headers(resp, "GET /health")

    def test_headers_on_404(self):
        resp = self.client.get("/no-such-route")
        self.assertEqual(resp.status_code, 404)
        self._assert_all_headers(resp, "404")

    def test_headers_on_internal_error(self):
        # Force the generic 500 path (the middleware's except branch) and
        # confirm it, too, carries the security headers.
        def boom():
            raise RuntimeError("boom")
            yield  # pragma: no cover

        app.dependency_overrides[get_db] = boom
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 500)
        self._assert_all_headers(resp, "500")
        # And still no traceback / internals in the body.
        self.assertEqual(resp.json()["detail"]["code"], "INTERNAL_ERROR")


class ApiDocsGatingTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.conn.close()

    def test_docs_available_in_non_production(self):
        # The suite runs outside "production", so the explorer + schema
        # are available (integration convenience in DEV/local/test).
        for path in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_docs_disabled_under_production_environment(self):
        # Fresh interpreter: docs_url/openapi_url are fixed when the app
        # is constructed, so this must be a clean import with the env set.
        probe = (
            "from lotsync.api.app import app;"
            "print('DOCS', app.docs_url, app.redoc_url, app.openapi_url)"
        )
        env = os.environ.copy()
        env["ENVIRONMENT"] = "production"
        env["PYTHONPATH"] = os.path.dirname(_REPO_ROOT)
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True, text=True, env=env, cwd=_REPO_ROOT, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DOCS None None None", result.stdout,
                      "ENVIRONMENT=production must disable /docs, /redoc, /openapi.json")


if __name__ == "__main__":
    unittest.main()
