"""
Sprint 11 (Rails F+G) -- the backend observability boundary
(api/observability.py + api/app.py's middleware): request
correlation, structured-log schema, redaction, the severity policy,
Sentry behavior via a fake transport, and the telemetry-is-secondary
guarantee. No test here ever contacts a live vendor -- Sentry runs
against an in-process fake transport and PostHog is frontend-only
(its posture is pinned by tests/test_frontend_observability_config.py).
"""

import json
import logging
import os
import unittest
import uuid
from unittest import mock

from fastapi.testclient import TestClient

from lotsync.api import observability
from lotsync.api.app import app
from lotsync.api.dependencies import get_db
from lotsync.api.observability import _JsonFormatter
from lotsync.database.repository import connect

BOOM_PATH = "/_observability_test_boom"


class _LogCapture(logging.Handler):
    """Captures dealerdoh records as parsed JSON payloads."""

    def __init__(self):
        super().__init__()
        self.records = []
        self._formatter = _JsonFormatter()

    def emit(self, record):
        self.records.append(json.loads(self._formatter.format(record)))

    def events(self, name):
        return [r for r in self.records if r["event"] == name]


class ObservabilityTestCase(unittest.TestCase):
    """App + in-memory DB + captured dealerdoh log records, plus a
    TEST-ONLY exploding route (added per-test to the app and removed
    in teardown -- deliberately never a deployed/permanent crash
    endpoint)."""

    def setUp(self):
        self.conn = connect(":memory:")

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        # raise_server_exceptions=False so the middleware's own 500
        # response is what the client sees (as deployed).
        self.client = TestClient(app, raise_server_exceptions=False)

        async def _boom():
            raise RuntimeError("observability-test-explosion")

        app.add_api_route(BOOM_PATH, _boom, methods=["GET"])

        self.capture = _LogCapture()
        logging.getLogger("dealerdoh").addHandler(self.capture)

    def tearDown(self):
        logging.getLogger("dealerdoh").removeHandler(self.capture)
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", "") != BOOM_PATH
        ]
        app.dependency_overrides.clear()
        self.conn.close()


class RequestIdTest(ObservabilityTestCase):
    def test_every_response_carries_a_server_generated_request_id(self):
        resp = self.client.get("/health")
        rid = resp.headers.get("X-Request-ID")
        self.assertTrue(rid and len(rid) == 32)

    def test_request_ids_are_unique_per_request(self):
        ids = {self.client.get("/health").headers["X-Request-ID"] for _ in range(5)}
        self.assertEqual(len(ids), 5)

    def test_client_supplied_id_is_never_the_authority(self):
        forged = "attacker-chosen-id"
        resp = self.client.get("/health", headers={"X-Request-ID": forged})
        self.assertNotEqual(resp.headers["X-Request-ID"], forged)

    def test_request_id_propagates_into_the_log_record(self):
        resp = self.client.get("/health")
        record = self.capture.events("http_request")[-1]
        self.assertEqual(record["request_id"], resp.headers["X-Request-ID"])

    def test_unexpected_error_response_carries_the_request_id(self):
        resp = self.client.get(BOOM_PATH)
        self.assertEqual(resp.status_code, 500)
        detail = resp.json()["detail"]
        self.assertEqual(detail["code"], "INTERNAL_ERROR")
        self.assertEqual(detail["request_id"], resp.headers["X-Request-ID"])
        # No traceback/internal text in the response body.
        self.assertNotIn("RuntimeError", resp.text)
        self.assertNotIn("observability-test-explosion", resp.text)


class StructuredLogTest(ObservabilityTestCase):
    def test_request_record_schema(self):
        self.client.get("/health")
        record = self.capture.events("http_request")[-1]
        for field in ("timestamp", "level", "event", "environment", "release",
                      "service", "request_id", "route", "method", "status_code",
                      "duration_ms"):
            self.assertIn(field, record, field)
        self.assertEqual(record["service"], "dealerdoh-api")
        self.assertEqual(record["route"], "/health")
        self.assertEqual(record["method"], "GET")
        self.assertEqual(record["status_code"], 200)
        self.assertGreaterEqual(record["duration_ms"], 0)

    def test_routes_are_templates_never_raw_paths(self):
        # /vehicles/{vin} raw paths carry real VINs -- the record must
        # hold the TEMPLATE and the VIN must appear nowhere in it.
        vin = "1TESTVIN000000001"
        self.client.get(f"/vehicles/{vin}")
        record = self.capture.events("http_request")[-1]
        self.assertEqual(record["route"], "/vehicles/{vin}")
        self.assertNotIn(vin, json.dumps(record))

    def test_unmatched_paths_do_not_leak_the_raw_path(self):
        self.client.get("/no-such-route/SECRETVALUE123")
        record = self.capture.events("http_request")[-1]
        self.assertEqual(record["route"], "(unmatched)")
        self.assertNotIn("SECRETVALUE123", json.dumps(record))

    def test_unexpected_error_record_has_type_not_message(self):
        self.client.get(BOOM_PATH)
        record = self.capture.events("http_request")[-1]
        self.assertEqual(record["status_code"], 500)
        self.assertEqual(record["error_type"], "RuntimeError")
        # Exception MESSAGES can carry report data -- never logged.
        self.assertNotIn("observability-test-explosion", json.dumps(record))

    def test_log_event_never_raises(self):
        observability.log_event(logging.INFO, "unserializable",
                                 payload=object(), nested={"x": {object(): 1}})


class RedactionTest(unittest.TestCase):
    def test_sensitive_keys_are_redacted(self):
        redacted = observability.redact_mapping({
            "authorization": "Bearer abc", "Cookie": "s=1", "password": "p",
            "access_token": "t", "refresh_token": "t", "recovery_code": "r",
            "DATABASE_URL": "postgres://u:p@h/db", "sentry_auth_token": "x",
            "api_key": "k", "sb_secret": "s",
        })
        self.assertTrue(all(v == observability.REDACTED for v in redacted.values()),
                        redacted)

    def test_credential_shaped_values_are_redacted_regardless_of_key(self):
        redacted = observability.redact_mapping({
            "a": "Bearer eyJhbGciOi",
            "b": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "c": "sb_secret_abc123",
            "d": "postgresql://user:pass@host:5432/db",
        })
        self.assertTrue(all(v == observability.REDACTED for v in redacted.values()),
                        redacted)

    def test_safe_values_pass_through_and_nesting_works(self):
        redacted = observability.redact_mapping({
            "route": "/vehicles/{vin}", "count": 34,
            "nested": {"authorization": "x", "ok": "fine"},
            "list": [{"password": "p"}, "plain"],
        })
        self.assertEqual(redacted["route"], "/vehicles/{vin}")
        self.assertEqual(redacted["count"], 34)
        self.assertEqual(redacted["nested"]["authorization"], observability.REDACTED)
        self.assertEqual(redacted["nested"]["ok"], "fine")
        self.assertEqual(redacted["list"][0]["password"], observability.REDACTED)
        self.assertEqual(redacted["list"][1], "plain")

    def test_uploaded_report_content_never_reaches_validation_logs(self):
        # The ingestion events carry codes/counts only -- pin the
        # helper's field surface against a leak-shaped regression.
        from lotsync.api.routers.inventory_sync import _log_validation
        from lotsync.sync.ingestion import validate_report_set
        fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
        capture = _LogCapture()
        logging.getLogger("dealerdoh").addHandler(capture)
        try:
            validation = validate_report_set(
                {"tekion": os.path.join(fixtures, "tekion_master.csv")})
            _log_validation(validation, 1.0)
        finally:
            logging.getLogger("dealerdoh").removeHandler(capture)
        record = capture.events("inventory_validation_completed")[-1]
        serialized = json.dumps(record)
        self.assertNotIn("1TESTVIN", serialized)      # no VINs
        self.assertNotIn("tekion_master", serialized)  # no filenames
        self.assertIn("total_rows", serialized)


class SeverityPolicyTest(ObservabilityTestCase):
    def test_expected_4xx_are_not_error_level(self):
        self.client.get("/vehicles/NOPE17CHARACTERSX")   # 404
        self.client.post("/inventory-sync/run")           # 422 (no files)
        for record in self.capture.events("http_request"):
            self.assertEqual(record["level"], "INFO", record)

    def test_unexpected_500_is_error_level(self):
        self.client.get(BOOM_PATH)
        self.assertEqual(self.capture.events("http_request")[-1]["level"], "ERROR")


class EnvironmentReleaseTest(unittest.TestCase):
    def test_environment_mapping(self):
        cases = [
            ({"ENVIRONMENT": "development"}, "development"),
            ({"ENVIRONMENT": "production"}, "production"),
            ({"ENVIRONMENT": "", "GITHUB_ACTIONS": "true"}, "ci"),
            ({"ENVIRONMENT": "", "GITHUB_ACTIONS": ""}, "local"),
        ]
        for env, expected in cases:
            with mock.patch.dict(os.environ, env):
                self.assertEqual(observability.observability_environment(),
                                 expected, env)

    def test_release_prefers_explicit_then_render(self):
        original = observability._RELEASE_CACHE
        try:
            observability._RELEASE_CACHE = None
            with mock.patch.dict(os.environ, {"DEALERDOH_RELEASE": "abc123"}):
                self.assertEqual(observability.observability_release(), "abc123")
            observability._RELEASE_CACHE = None
            with mock.patch.dict(os.environ,
                                  {"DEALERDOH_RELEASE": "", "RENDER_GIT_COMMIT": "def456"}):
                self.assertEqual(observability.observability_release(), "def456")
        finally:
            observability._RELEASE_CACHE = original

    def test_release_is_cached_and_nonempty(self):
        self.assertTrue(observability.observability_release())


class HealthMetadataTest(ObservabilityTestCase):
    def test_health_reports_release_and_no_secrets(self):
        body = self.client.get("/health").json()
        self.assertIn("release", body)
        self.assertTrue(body["release"])
        serialized = json.dumps(body)
        for forbidden in ("postgres://", "postgresql://", "sb_secret", "DSN",
                          "SENTRY", "POSTHOG"):
            self.assertNotIn(forbidden, serialized)


class _FakeTransport:
    """Sentry transport double -- captures envelopes in-process; no
    network ever."""

    def __init__(self):
        self.events = []

    def capture_envelope(self, envelope):
        event = envelope.get_event()
        if event is not None:
            self.events.append(event)

    def flush(self, *a, **k):
        pass

    def kill(self):
        pass

    # attributes various sdk versions poke at
    parsed_dsn = None
    options = {}

    def record_lost_event(self, *a, **k):
        pass

    def is_healthy(self):
        return True


class SentryBackendTest(ObservabilityTestCase):
    """Capture behavior against the fake transport; disabled behavior
    without a DSN. Teardown always returns the process to
    Sentry-disabled."""

    def _enable_sentry(self):
        import sentry_sdk

        with mock.patch.dict(os.environ,
                              {"SENTRY_DSN": "https://key@o0.ingest.invalid/1"}):
            self.assertTrue(observability.init_backend_sentry())
        self.transport = _FakeTransport()
        sentry_sdk.get_client().transport = self.transport

    def tearDown(self):
        import sentry_sdk

        sentry_sdk.init(dsn="")  # disabled client
        observability._SENTRY_ENABLED = False
        super().tearDown()

    def test_disabled_without_dsn(self):
        with mock.patch.dict(os.environ, {"SENTRY_DSN": ""}):
            self.assertFalse(observability.init_backend_sentry())
        self.assertFalse(observability.sentry_enabled())
        self.assertEqual(observability.capture_unexpected(RuntimeError("x")), "")
        # And the app still works end to end -- telemetry is secondary.
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_unexpected_exception_is_captured_with_safe_context(self):
        self._enable_sentry()
        resp = self.client.get(BOOM_PATH, headers={"Authorization": "Bearer supersecrettoken"})
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(len(self.transport.events), 1)
        event = self.transport.events[0]
        self.assertEqual(event["tags"]["service"], "dealerdoh-api")
        self.assertEqual(event["tags"]["request_id"], resp.headers["X-Request-ID"])
        self.assertIn("environment", event)
        self.assertIn("release", event)
        # The bearer token appears NOWHERE in the serialized event.
        self.assertNotIn("supersecrettoken", json.dumps(event))

    def test_expected_4xx_produce_no_sentry_events(self):
        self._enable_sentry()
        self.client.get("/definitely-not-a-route")        # 404
        self.client.post("/inventory-sync/run")           # 422
        self.client.get("/vehicles/NOPE17CHARACTERSX")    # 404
        self.assertEqual(self.transport.events, [])

    def test_scrubber_redacts_request_sections_and_breadcrumbs(self):
        event = {
            "request": {"headers": {"Authorization": "Bearer x", "Accept": "json"},
                         "cookies": {"session": "abc"},
                         "data": {"file": "contents"},
                         "query_string": "vin=1TESTVIN000000001"},
            "breadcrumbs": {"values": [{"data": {"password": "p", "ok": "fine"}}]},
            "extra": {"DATABASE_URL": "postgres://u:p@h/db"},
        }
        scrubbed = observability._scrub_sentry_event(event, {})
        self.assertEqual(scrubbed["request"]["headers"]["Authorization"],
                         observability.REDACTED)
        self.assertEqual(scrubbed["request"]["cookies"]["session"],
                         observability.REDACTED)
        self.assertNotIn("data", scrubbed["request"])
        self.assertEqual(scrubbed["request"]["query_string"], observability.REDACTED)
        self.assertEqual(scrubbed["breadcrumbs"]["values"][0]["data"]["password"],
                         observability.REDACTED)
        self.assertEqual(scrubbed["breadcrumbs"]["values"][0]["data"]["ok"], "fine")
        self.assertEqual(scrubbed["extra"]["DATABASE_URL"], observability.REDACTED)


class AuthObservabilityTest(unittest.TestCase):
    """The auth events ride the existing required-mode test app --
    reuse tests/test_auth.py's harness rather than rebuilding it."""

    def test_denials_log_warning_without_tokens(self):
        from tests.test_auth import AuthTestCase, bearer

        capture = _LogCapture()
        logging.getLogger("dealerdoh").addHandler(capture)
        try:
            harness = AuthTestCase("run")
            harness.setUp()
            try:
                token = harness.token_for("lot_staff")
                resp = harness.client.post("/inventory-sync/run",
                                            headers=bearer(token))
                self.assertEqual(resp.status_code, 403)
                denied = capture.events("auth_denied")
                self.assertTrue(denied)
                record = denied[-1]
                self.assertEqual(record["level"], "WARNING")
                self.assertEqual(record["reason"], "role_not_permitted")
                self.assertEqual(record["role"], "lot_staff")
                self.assertNotIn(token, json.dumps(record))

                outsider = harness.token_for("outsider")
                resp = harness.client.get("/vehicles", headers=bearer(outsider))
                self.assertEqual(resp.status_code, 403)
                record = capture.events("auth_denied")[-1]
                self.assertEqual(record["reason"], "no_active_membership")
                self.assertNotIn(outsider, json.dumps(record))

                # The finished request record of an AUTHENTICATED call
                # carries the safe who/where ids (via request.state --
                # the sync-dependency contextvar trap this sprint
                # found and designed around).
                resp = harness.client.get("/vehicles",
                                           headers=bearer(harness.token_for("manager")))
                self.assertEqual(resp.status_code, 200)
                record = capture.events("http_request")[-1]
                self.assertEqual(record["role"], "manager")
                self.assertEqual(record["dealership_id"], "qa-motors")
                self.assertTrue(record["auth_user_id"])
                serialized = json.dumps(record)
                self.assertNotIn("@qa.dealerdoh.example", serialized)  # no email
            finally:
                harness.tearDown()
        finally:
            logging.getLogger("dealerdoh").removeHandler(capture)


class DevVerificationTriggerTest(ObservabilityTestCase):
    """The double-gated Sentry verification route
    (api/routers/observability_dev.py): nonexistent outside
    ENVIRONMENT=development; a genuine captured 500 inside it."""

    def test_404_outside_development(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": ""}):
            resp = self.client.post("/_observability/raise-test-error")
        self.assertEqual(resp.status_code, 404)

    def test_raises_and_captures_inside_development(self):
        import sentry_sdk

        with mock.patch.dict(os.environ,
                              {"SENTRY_DSN": "https://key@o0.ingest.invalid/1"}):
            self.assertTrue(observability.init_backend_sentry())
        transport = _FakeTransport()
        sentry_sdk.get_client().transport = transport
        try:
            with mock.patch.dict(os.environ, {"ENVIRONMENT": "development"}):
                resp = self.client.post("/_observability/raise-test-error")
            self.assertEqual(resp.status_code, 500)
            self.assertEqual(resp.json()["detail"]["code"], "INTERNAL_ERROR")
            self.assertEqual(len(transport.events), 1)
            record = self.capture.events("http_request")[-1]
            self.assertEqual(record["error_type"], "ObservabilityVerificationError")
        finally:
            sentry_sdk.init(dsn="")
            observability._SENTRY_ENABLED = False


class SyncCorrelationTest(ObservabilityTestCase):
    def test_sync_completion_links_request_id_to_sync_run_ids(self):
        fixtures = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
        with open(os.path.join(fixtures, "tekion_master.csv"), "rb") as handle:
            resp = self.client.post(
                "/inventory-sync/run",
                files={"tekion_unsold": ("t.csv", handle, "text/csv")},
            )
        self.assertEqual(resp.status_code, 200)
        completed = self.capture.events("inventory_sync_completed")[-1]
        self.assertEqual(completed["request_id"], resp.headers["X-Request-ID"])
        self.assertEqual(completed["sync_run_ids"],
                         [r["sync_run_id"] for r in resp.json()["sync_runs"]])
        started = self.capture.events("inventory_sync_started")[-1]
        self.assertEqual(started["request_id"], resp.headers["X-Request-ID"])


if __name__ == "__main__":
    unittest.main()
