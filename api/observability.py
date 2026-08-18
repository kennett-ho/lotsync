"""
Sprint 11 (Rails F+G) -- the backend observability core: environment/
release identity, request correlation, structured JSON application
logs, the severity policy, centralized redaction, and Sentry
initialization. OBSERVABILITY.md is the canonical architecture
document; this module is its implementation.

Three deliberately separate layers (do not blur them):

- Structured logs (THIS module): "what happened inside DealerDOH,
  during which request, in which environment/release, how long."
- Sentry: "what is breaking unexpectedly." Initialized here, fed by
  the unhandled-exception path -- never by expected 4xx outcomes.
- PostHog: "what are users doing." Frontend-only in this sprint
  (frontend/src/observability/); the backend deliberately does not
  duplicate product analytics.

Two invariants every piece of this module maintains:

1. TELEMETRY IS SECONDARY. Missing SENTRY_DSN means Sentry is a
   no-op; logging failures must never fail a request; nothing here
   sits on the critical path of Auth, validation, sync, or queries.
2. NOTHING SENSITIVE LEAVES. The redaction helpers below are applied
   to structured-log fields and Sentry events alike. Raw paths are
   never logged (route TEMPLATES only -- /vehicles/{vin} carries a
   real VIN in its raw form), exception messages are never logged
   into structured records (type name only -- a KeyError's message
   can contain report data), request bodies are never captured, and
   Sentry runs with send_default_pii=False and
   include_local_variables=False (a pandas DataFrame in a stack
   frame's locals IS the uploaded report).
"""

import contextvars
import datetime
import json
import logging
import os
import re
import subprocess
import time
import uuid

SERVICE_NAME = "dealerdoh-api"

# ---------------------------------------------------------------------------
# Environment identity (Sprint 11 phase 4).
#
# One model across logs, Sentry, and (frontend) PostHog:
# local / test / ci / development / production. Reuses the EXISTING
# deployment variable (ENVIRONMENT -- set to "development" on Render
# DEV since Sprint 02; production sets nothing today and will set
# "production" at its own release train) plus CI's own marker. No new
# overlapping flags.
# ---------------------------------------------------------------------------


def observability_environment() -> str:
    explicit = os.environ.get("ENVIRONMENT", "").strip().lower()
    if explicit in ("development", "production", "test"):
        return explicit
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return "ci"
    return "local"


# ---------------------------------------------------------------------------
# Release identity (phase 5): the immutable deployed code, not a
# mutable display version. Resolution order:
#   DEALERDOH_RELEASE (explicit override, e.g. future prod train)
#   RENDER_GIT_COMMIT (Render-provided deploy SHA)
#   git rev-parse HEAD (local checkouts -- guarded, best-effort)
#   "unknown"
# Cached once per process: a release cannot change mid-run.
# ---------------------------------------------------------------------------

_RELEASE_CACHE = None


def observability_release() -> str:
    global _RELEASE_CACHE
    if _RELEASE_CACHE is None:
        release = (os.environ.get("DEALERDOH_RELEASE", "").strip()
                   or os.environ.get("RENDER_GIT_COMMIT", "").strip())
        if not release:
            try:
                release = subprocess.run(
                    ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                    timeout=5, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                ).stdout.strip() or "unknown"
            except Exception:
                release = "unknown"
        _RELEASE_CACHE = release[:40] if release else "unknown"
    return _RELEASE_CACHE


# ---------------------------------------------------------------------------
# Request correlation (phase 6) + safe authenticated context.
#
# The request id is SERVER-generated (uuid4 hex), never taken from
# client input -- an inbound X-Request-ID is ignored as authority. It
# lives in a contextvar SET IN THE MIDDLEWARE TASK, whose context
# every downstream task/threadpool call inherits a copy of -- so
# reads work everywhere in the request.
#
# The authenticated context deliberately does NOT use a contextvar:
# it resolves inside a SYNC dependency, which Starlette runs in a
# threadpool with a copied context -- a contextvar .set() there is
# invisible to the middleware task and to sibling dependencies
# (found by this sprint's own tests). It rides request.state instead:
# mutations on the Request object are context-immune, and the
# middleware folds it into the finished http_request record.
# ---------------------------------------------------------------------------

request_id_var = contextvars.ContextVar("dealerdoh_request_id", default="")

REQUEST_ID_HEADER = "X-Request-ID"
_AUTH_STATE_ATTR = "dealerdoh_auth_context"


def current_request_id() -> str:
    return request_id_var.get()


def set_auth_log_context(request, *, auth_user_id: str, role: str,
                          organization_id: str, dealership_id: str) -> None:
    """Called by api/auth.py once a caller's membership resolves.
    Stable internal IDs only -- never email or display name."""
    setattr(request.state, _AUTH_STATE_ATTR, {
        "auth_user_id": auth_user_id, "role": role,
        "organization_id": organization_id, "dealership_id": dealership_id,
    })


def auth_log_context(request) -> dict:
    return getattr(request.state, _AUTH_STATE_ATTR, None) or {}


# ---------------------------------------------------------------------------
# Centralized redaction (phase 10). Applied to every structured-log
# field dict and to Sentry events. Key-based (name looks sensitive)
# and value-based (value looks like a credential) -- belt and
# suspenders, because "developers will remember not to log it" is not
# a control.
# ---------------------------------------------------------------------------

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_RE = re.compile(
    r"authorization|cookie|token|secret|password|passwd|credential|"
    r"api[-_]?key|database_url|dsn|recovery|jwt|bearer",
    re.IGNORECASE,
)

_SENSITIVE_VALUE_RE = re.compile(
    r"^Bearer\s|^eyJ[A-Za-z0-9_-]{8,}|^sb_secret_|^postgres(ql)?://|"
    r"^https://[^/]*ingest[^/]*sentry", re.IGNORECASE,
)


def redact_value(key, value):
    if _SENSITIVE_KEY_RE.search(str(key)):
        return REDACTED
    if isinstance(value, str) and _SENSITIVE_VALUE_RE.search(value):
        return REDACTED
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, (list, tuple)):
        return [redact_value("", v) for v in value]
    return value


def redact_mapping(mapping: dict) -> dict:
    return {str(k): redact_value(k, v) for k, v in mapping.items()}


# ---------------------------------------------------------------------------
# Structured JSON logging (phase 8) + severity policy (phase 9).
#
# One logger ("dealerdoh"), one line-delimited JSON record per event,
# in every environment -- uniform records are what make the tests and
# the deployed inspection identical. uvicorn's default access log is
# deliberately KEPT alongside (documented decision): it is the only
# record for requests that die before this middleware, its line
# carries no ids/durations/context so it does not duplicate ours in
# substance, and silencing it would require touching the Render start
# command for no safety gain.
#
# Severity policy (full text in OBSERVABILITY.md):
#   INFO     expected operational milestones (request completed,
#            validation completed, sync completed)
#   WARNING  expected degraded/suspicious outcomes (validation
#            blocked/warning, auth denied, missing dependent source)
#   ERROR    unexpected failure of an operation (unhandled exception,
#            sync execution failure)
#   CRITICAL service-level failure requiring immediate attention
# Expected 4xx outcomes are INFO/WARNING material and NEVER become
# Sentry events.
# ---------------------------------------------------------------------------

_logger = logging.getLogger("dealerdoh")


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
                .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "environment": observability_environment(),
            "release": observability_release(),
            "service": SERVICE_NAME,
        }
        fields = getattr(record, "dealerdoh_fields", None)
        if fields:
            payload.update(fields)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Idempotent. Installs the JSON handler on the dealerdoh logger;
    never touches uvicorn's loggers (see the keep-both decision)."""
    if any(isinstance(h.formatter, _JsonFormatter) for h in _logger.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def log_event(level: int, event: str, /, **fields) -> None:
    """The one structured-log entry point. Folds in the request id
    automatically (the middleware-task contextvar every downstream
    call inherits), redacts every field, and NEVER raises (telemetry
    is secondary). Authenticated who/where context appears on the
    http_request record via request.state -- see set_auth_log_context."""
    try:
        merged = {}
        rid = request_id_var.get()
        if rid:
            merged["request_id"] = rid
        merged.update(fields)
        _logger.log(level, event, extra={"dealerdoh_fields": redact_mapping(merged)})
    except Exception:  # pragma: no cover - the never-break-the-app guarantee
        pass


# ---------------------------------------------------------------------------
# Sentry (phase 11). Initialized once at app import; a missing
# SENTRY_DSN leaves every capture call a silent no-op. Conservative
# by construction: no PII, no local variables (report DataFrames live
# in stack locals), no performance tracing yet, scrubbed
# headers/cookies, and the FastAPI integration's own default of
# reporting only unhandled 500-class failures (expected 4xx
# HTTPExceptions never reach it).
# ---------------------------------------------------------------------------

_SENTRY_ENABLED = False


def _scrub_sentry_event(event, hint):
    try:
        request = event.get("request")
        if isinstance(request, dict):
            for section in ("headers", "env"):
                if isinstance(request.get(section), dict):
                    request[section] = redact_mapping(request[section])
            # EVERY cookie value is session material -- wholesale, not
            # key-pattern, redaction.
            if isinstance(request.get("cookies"), dict):
                request["cookies"] = {k: REDACTED for k in request["cookies"]}
            # Bodies are not captured by configuration; drop any that
            # an integration slipped in anyway, plus raw query strings
            # (raw paths/queries can carry VINs).
            request.pop("data", None)
            if request.get("query_string"):
                request["query_string"] = REDACTED
        for crumb in (event.get("breadcrumbs") or {}).get("values", []):
            if isinstance(crumb.get("data"), dict):
                crumb["data"] = redact_mapping(crumb["data"])
        for ctx_name in ("extra", "contexts", "tags"):
            if isinstance(event.get(ctx_name), dict):
                event[ctx_name] = redact_mapping(event[ctx_name])
        event.setdefault("tags", {})
        event["tags"].setdefault("service", SERVICE_NAME)
        rid = request_id_var.get()
        if rid:
            event["tags"].setdefault("request_id", rid)
    except Exception:  # pragma: no cover - scrubbing must never break capture
        pass
    return event


def init_backend_sentry() -> bool:
    """Called once from api/app.py. Returns whether Sentry is live."""
    global _SENTRY_ENABLED
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        _SENTRY_ENABLED = False
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import ignore_logger

        # Layer separation is deliberate: structured "dealerdoh" log
        # records are Layer A and NEVER auto-become Sentry events (the
        # default LoggingIntegration would turn every ERROR record
        # into a duplicate event -- proven by this sprint's tests).
        # capture_unexpected() is the one path into Sentry.
        ignore_logger("dealerdoh")

        sentry_sdk.init(
            dsn=dsn,
            environment=observability_environment(),
            release=observability_release(),
            send_default_pii=False,
            include_local_variables=False,
            traces_sample_rate=0.0,
            before_send=_scrub_sentry_event,
            max_request_body_size="never",
            # The middleware's capture_unexpected is the ONE capture
            # path -- the auto-enabled Starlette/FastAPI integration
            # would capture the same exception a second time at the
            # routing layer (proven by this sprint's tests), so
            # framework auto-instrumentation stays off.
            auto_enabling_integrations=False,
        )
        _SENTRY_ENABLED = True
    except Exception:
        # A malformed DSN or import problem must not stop DealerDOH.
        _SENTRY_ENABLED = False
    return _SENTRY_ENABLED


def sentry_enabled() -> bool:
    return _SENTRY_ENABLED


def capture_unexpected(exc: BaseException) -> str:
    """Report an unexpected exception to Sentry (no-op without DSN).
    Returns the Sentry event id ('' when disabled) so callers can
    surface a safe support reference."""
    if not _SENTRY_ENABLED:
        return ""
    try:
        import sentry_sdk

        return sentry_sdk.capture_exception(exc) or ""
    except Exception:  # pragma: no cover
        return ""
