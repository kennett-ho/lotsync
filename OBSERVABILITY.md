# DealerDOH Observability (Sprint 11 — Rails F + G)

**Status: canonical.** How DealerDOH answers *what is breaking*
(Sentry), *what are users doing* (PostHog), and *what happened inside
the application, during which request, in which environment/release,
and how long did it take* (structured logs). Implemented in
`api/observability.py` (backend) and `frontend/src/observability/`
(browser). Amend this document in the same PR as any behavior change.

Two invariants everything here obeys:

1. **Telemetry is secondary.** Every layer is a silent no-op when
   unconfigured; a telemetry failure can never block Auth, validation,
   sync, queries, or startup. Local checkouts and CI need no
   observability configuration and never contact a vendor (tests use
   an in-process fake Sentry transport; PostHog is init-gated).
2. **Nothing sensitive leaves.** No tokens, cookies, passwords,
   recovery material, server secrets, DSN/DB credentials, uploaded
   report contents, spreadsheet rows, raw paths/querystrings, VINs,
   emails, or display names. Stable internal ids only. §7 is the
   enforcement inventory.

---

## 1. The three layers — responsibilities that do not blur

| Layer | Question | Feed | Never used for |
|---|---|---|---|
| Structured logs (`dealerdoh` logger, JSON lines) | What happened, in which request, how long? | Request records, validation/sync lifecycle, auth denials, degraded states | Product analytics; a Sentry substitute |
| Sentry (backend `SENTRY_DSN`, frontend `VITE_SENTRY_DSN`) | What is breaking *unexpectedly*? | Unhandled exceptions only, via ONE explicit capture path per runtime | Expected 4xx outcomes; logs; analytics |
| PostHog (`VITE_POSTHOG_KEY`/`VITE_POSTHOG_HOST`, browser only) | What are users doing? | The explicit event taxonomy (§6) | Error logging; server-side duplication of logs |

Layer separation is mechanical, not aspirational: the Sentry
`LoggingIntegration` is disabled for the `dealerdoh` logger (an ERROR
record would otherwise auto-become a duplicate Sentry event — proven
by test), framework auto-instrumentation is off
(`auto_enabling_integrations=False`; the middleware's
`capture_unexpected()` is the one backend path into Sentry), and the
backend sends nothing to PostHog.

## 2. Environment and release identity

One model across all layers: `local` · `test` · `ci` · `development`
· `production`. Resolved from the EXISTING deployment variable
`ENVIRONMENT` (backend; Render DEV has set `development` since Sprint
02) / `VITE_ENVIRONMENT` (frontend), plus `GITHUB_ACTIONS` → `ci`.
Production sets its variables at its own future release train — no
new overlapping flags were invented.

Release = the immutable git SHA, never a mutable display version:
backend `DEALERDOH_RELEASE` (explicit override) → `RENDER_GIT_COMMIT`
(Render-supplied) → local `git rev-parse` → `unknown`; frontend
`__DEALERDOH_RELEASE__` baked at build from `VERCEL_GIT_COMMIT_SHA` →
`GITHUB_SHA` → `local-build` (`vite.config.ts`). `/health` now
reports it (§5).

## 3. Request correlation

Every API request gets a server-generated `X-Request-ID` (uuid4 hex;
client-supplied ids are never the authority), returned on every
response and carried by every structured record the request emits.
The frontend `ApiError` retains it (`error.requestId`) so UI can show
a safe "Reference: …" for unexpected failures. Sentry events carry it
as the `request_id` tag. Sync execution logs it next to the created
`sync_run_ids` (§4), completing the chain:

    browser action → X-Request-ID → structured records → SyncRun rows
                                  → Sentry event (if something broke)

No schema changed for this — SyncRun's business meaning is untouched.

**Threadpool caveat (learned by test, preserved as design):** sync
FastAPI dependencies run in threadpool-copied contexts, so a
contextvar set there is invisible outside. The request id lives in a
middleware-task contextvar (inherited downstream — reads work
everywhere); the authenticated context rides `request.state` and is
folded into the finished request record by the middleware. Do not
"simplify" auth context back into a contextvar.

## 4. Structured log schema and events

One JSON object per line on stdout (Render captures it), every
environment. Base fields on every record: `timestamp` (UTC ISO,
ms), `level`, `event`, `environment`, `release`, `service`
(`dealerdoh-api`). Request records add: `request_id`, `route`
(**route template only** — `/vehicles/{vin}` raw paths carry real
VINs; unmatched paths log `(unmatched)`), `method`, `status_code`,
`duration_ms`, and — when authenticated — `auth_user_id`, `role`,
`organization_id`, `dealership_id` (ids only; never email/name).

Current event vocabulary:

| Event | Level | Extra fields |
|---|---|---|
| `http_request` | INFO (<500) / ERROR (≥500) | base + request fields; 500s add `error_type` (+`sentry_event_id`) — exception TYPE only, messages can carry report data |
| `inventory_validation_completed` / `_warning` / `_blocked` | INFO / WARNING / WARNING | `duration_ms`, per-report `{slot, detected, status, total_rows, valid_rows, codes}` |
| `inventory_sync_started` | INFO | `slots`, `warnings_acknowledged` |
| `inventory_sync_completed` | INFO | `sync_run_ids`, counts, `pipeline_warnings`, `duration_ms` |
| `inventory_sync_failed` | ERROR | `slots`, `error_type`, `duration_ms` (+`sentry_event_id`) |
| `auth_denied` | WARNING | `reason` (`no_active_membership` / `role_not_permitted`) + safe ids |
| `auth_infrastructure_failure` | ERROR | `reason=jwks_unreachable`, `error_type` — provider outage, distinguishable from credential failure (which logs nothing; its 401 request record is the trace) |

Severity policy: **INFO** = expected milestones · **WARNING** =
expected degraded/suspicious outcomes (validation warnings, auth
denials, missing dependent source) · **ERROR** = unexpected operation
failure · **CRITICAL** = reserved for service-level failure. Expected
401/403/404/409/422 are never ERROR and never Sentry events.

**uvicorn access log decision:** kept as-is alongside. It is the only
record for requests that die before the middleware, carries no
ids/durations/context (so it does not duplicate ours in substance),
and silencing it would mean touching the Render start command for no
safety gain.

`print()` calls in `config/settings.py` (missing-oms-config
warnings) and the CLI report writer predate this sprint and remain —
plain-text noise in deployed logs, recorded as a finding, not worth
churning the CLI-era modules for.

## 5. Backend Sentry

`init_backend_sentry()` (called at app import): no `SENTRY_DSN` → 
disabled, every capture a no-op. When enabled:
`send_default_pii=False`, `include_local_variables=False` (a pandas
DataFrame in a stack frame IS the uploaded report),
`traces_sample_rate=0` (no perf tracing until justified),
`max_request_body_size="never"`, `auto_enabling_integrations=False`,
`dealerdoh` logger ignored, and `before_send=_scrub_sentry_event`
(redacts headers/env, wholesale-redacts every cookie, drops request
bodies and querystrings, scrubs breadcrumbs/extra/contexts, stamps
`service` + `request_id` tags). The ONLY capture sites are the
middleware's unhandled-exception path and the sync-execution failure
handler. There is no crash or verification endpoint of ANY kind — the
application ships no deliberately raising route, in any environment.
Capture-path verification is automated offline: the suite drives a
genuine unhandled exception through the middleware via a test-local
route (added and torn down per test) against an in-process fake
transport (`tests/test_observability.py`). The DEV-only trigger route
that produced Sprint 11's live deployed evidence was removed before
merge (owner direction) once that evidence was recorded; a test pins
its path answering 404 even under `ENVIRONMENT=development`, and the
evidence stands in `SPRINT_HISTORY.md` as historical verification.

`/health` additionally reports `release` (non-secret by definition;
no hostnames, DSNs, or provider config are ever exposed there).

## 6. Frontend Sentry, Error Boundary, PostHog

**Sentry** (`frontend/src/observability/sentry.ts`): disabled without
`VITE_SENTRY_DSN` (a browser DSN is an intentionally public
identifier). Captures global JS errors, unhandled rejections, and
React render errors (via the boundary). `sendDefaultPii: false`, no
tracing, **Session Replay OFF and never imported** (plus a defensive
init filter dropping any integration named like Replay), fetch/xhr
breadcrumb URLs masked (identifier-like path segments → `*`,
querystrings dropped). No user identity is attached to Sentry at all.

**Error Boundary** (`observability/ErrorBoundary.tsx`, mounted
outside the auth gate): honest fallback — plain language, a reload
button, the DEV banner preserved, an optional safe `Reference:
<event-id>`, never a stack trace, never a claim that data saved.

**PostHog** (`observability/analytics.ts`): disabled without
`VITE_POSTHOG_KEY` (browser project token = public identifier; a
PostHog PERSONAL/admin key is a secret and appears nowhere in this
repository). Explicit flags pin the beta posture: `autocapture:
false`, `capture_pageview: false`, `capture_pageleave: false`,
`disable_session_recording: true`, `person_profiles:
'identified_only'`. Identity = `auth_user_id` (internal UUID,
identified only after `/me` confirms the membership server-side) with
`role`/`dealership_id`/`organization_id`/`environment` person
properties; `signOut()` — the single sign-out choke point — calls
`posthog.reset()`, so User B on a shared browser never inherits
User A. Every event carries `environment` + `release` via
`posthog.register`.

### Event taxonomy (stable names; add sparingly, with the authority noted)

| Event | Authority | Properties |
|---|---|---|
| `app_loaded` | UI | — |
| `page_viewed` | UI | `page` (controlled id: dashboard/vehicles/tasks/inventory-sync/profile/vehicle-detail; Sprint 12 adds today/help) |
| `vehicle_detail_opened` | UI | `source` page id (no VIN) |
| `onboarding_started` / `_completed` / `_skipped` / `_replayed` | UI (Sprint 12 -- lifecycle of the role-aware Getting Started tour; skip records completion, replay never rewrites) | — |
| `help_opened` | UI (Sprint 12) | — |
| `today_work_opened` | UI (Sprint 12 -- the Lot Staff landing surface) | — |
| `password_recovery_requested` | observed provider accept | — (never the email) |
| `profile_display_name_updated` | observed server outcome | — (never the name) |
| `user_management_opened` | UI | — |
| `inventory_validation_completed` / `_warning` / `_blocked` | **observed server response** (the DTO is the server's verdict) | `slots`, `codes`, `total_rows`, `valid_rows` |
| `inventory_sync_started` | user intent (the click) | `slots`, `warnings_acknowledged` |
| `inventory_sync_completed` | observed server response | `sources`, counts |
| `inventory_sync_failed` | observed 5xx | `status` |
| `work_order_generated` | observed server response (PDF arrived) | — |

Client-vs-server authority rule: a frontend event may claim an
outcome only when it observed the server's response saying so;
structured server logs remain the authority on what actually
happened. The backend does not duplicate product analytics.

## 7. Privacy and redaction enforcement

Central redaction (`redact_mapping`) applies to every structured-log
field and Sentry event: key-pattern matching (authorization, cookie,
token, secret, password, credential, api_key, database_url, dsn,
recovery, jwt, bearer) AND value-shape matching (`Bearer …`, JWT
`eyJ…`, `sb_secret_…`, `postgres[ql]://…`), recursing through
dicts/lists; cookies are wholesale-redacted. Exception MESSAGES are
never logged (type names only). Uploaded files never reach any
telemetry: validation events carry codes/counts only, and
`sync/ingestion.py` already normalizes parser failures into codes
before anything here sees them.

Enforced by tests, not memory: `tests/test_observability.py`
(request-id lifecycle, schema, route-template/VIN absence, redaction
matrix, severity policy, Sentry disabled/capture/4xx-silence/scrub
via fake transport, auth-denial events, sync correlation, health
metadata) and `tests/test_frontend_observability_config.py` (PostHog
posture flags, no replay import, identity/reset wiring, no
email/VIN/filename properties, no privileged secret referenced in
frontend source, release plumbing).

**The 15-question telemetry privacy review** (sprint phase 40) runs
against REAL DEV payloads before any Rail F/G verification claim; its
record lives in the sprint entry in `SPRINT_HISTORY.md`.

## 8. Alert conditions & telemetry census (Rail G exits 4–5)

**Alert-condition inventory** — the governed list of conditions that
must reach a human. Named recipient for every condition: **the owner
(Kennett Ho)**. Delivery today: Sentry's built-in email alerts for
the exception-class conditions once the DEV (and later production)
Sentry project exists; the log-derived conditions are a documented
review inventory until a delivery mechanism ships (Rail G explicitly
accepts simple email — the INVENTORY is the requirement; richer
delivery is Rail E's conditional territory).

| Condition | Signal source | Initial threshold (beta; tune from evidence) |
|---|---|---|
| Sustained 5xx rate | `http_request` records `status_code>=500` / Sentry event burst | >5 in 10 min |
| DB unreachable | `/health` failing (Render health checks) · `error_type` Operational/Pool errors | any occurrence |
| Inventory Sync execution failure | `inventory_sync_failed` record / its Sentry event | any occurrence |
| Repeated auth failures | `auth_denied` WARNING rate · `auth_infrastructure_failure` | >20 denials in 10 min; any infrastructure failure |
| Storage problems (upload/report disk) | 500s on `/inventory-sync/*` with IO `error_type` | any occurrence |
| Abnormal operational counts | `inventory_validation_warning` records carrying `SUSPICIOUS_COUNT_*` codes | every occurrence is already operator-facing (Rail D ack flow); alert if acknowledged-and-run >2×/week |

**Telemetry census** — each signal has exactly ONE primary home
(anti-duplication):

| Signal | Primary home | Notes |
|---|---|---|
| Request lifecycle (route/status/duration/who) | Structured logs | uvicorn access line kept only as pre-middleware belt |
| Unexpected exceptions (stack, release) | Sentry | log record carries only `error_type` + `sentry_event_id` pointer |
| Expected denials/degraded outcomes (auth_denied, validation warnings) | Structured logs (WARNING) | never Sentry |
| Validation/sync lifecycle + counts + run ids | Structured logs | PostHog gets the user-facing subset only |
| Product usage (pages, feature events) | PostHog | never in logs; backend does not duplicate |
| Deploy identity (release/environment) | All three, as tags/fields | the one deliberate duplication — it IS the correlation key |
| Alert delivery | Sentry email (exception-class) + this inventory | until/unless Rail E promotes richer delivery |

## 9. Configuration inventory

| Item | Where | Nature |
|---|---|---|
| `SENTRY_DSN` | Render DEV env (backend) | Public-shaped identifier, kept server-side anyway |
| `VITE_SENTRY_DSN` | Vercel DEV env (build-time) | Intentionally browser-public |
| `VITE_POSTHOG_KEY` (`phc_…`) | Vercel DEV env (build-time) | Intentionally browser-public project token |
| `VITE_POSTHOG_HOST` | Vercel DEV env | Public URL (defaults to PostHog US cloud) |
| `DEALERDOH_RELEASE` | optional override, any backend env | Non-secret |
| `SENTRY_AUTH_TOKEN` | **NOWHERE yet** — only if source-map upload is later adopted; build-secret ONLY, never `VITE_*` | **SECRET** |
| PostHog personal/admin API key | **NOWHERE** — never needed by the app | **SECRET** |

Local/CI: none of the above set → everything disabled, all tests
offline. **Production: nothing configured this sprint** — production
Sentry/PostHog activation is a deliberate future release-train step
with its own projects/keys, never a side effect of this work.

## 10. Source maps — deliberate deferral

Production-style builds emit no source maps (`vite.config.ts`:
`sourcemap: false`), so DEV Sentry stack traces are minified: usable
via error type/message, masked breadcrumbs, and `request_id`
correlation to backend records, but not line-precise. Secure upload
(hidden source maps + `SENTRY_AUTH_TOKEN` as a Vercel build secret)
is deferred as disproportionate for this beta window — recorded as a
known diagnostic limitation rather than shipping an insecure
shortcut (the token must never ride `VITE_*`/the bundle). Revisit at
production observability activation.

**Sprint 13 security confirmation:** the audit verified that **no source
maps are served publicly** (`sourcemap: false`; the deployed production
bundle carries zero `sourceMappingURL` references — no source-code
exposure). The deferral of secure upload stands unchanged; there is no
insecure interim state to remediate. See `SECURITY_AUDIT.md`.

## 11. Troubleshooting

- *Find what happened to a user action:* get `X-Request-ID` from the
  response (or the UI "Reference"), search Render logs for it —
  every record of that request carries it; sync runs list their
  `sync_run_ids` beside it; a Sentry event shares it as a tag.
- *Sentry silent?* `SENTRY_DSN` unset (intended default) or invalid —
  init fails closed as disabled. Check `/health`'s `release` to
  confirm which code is deployed.
- *Verify backend Sentry capture:* run
  `tests/test_observability.py` — it drives a real unhandled
  exception through the middleware against a fake transport, no
  vendor contact. There is no in-app trigger route (removed
  pre-merge in Sprint 11). For a live end-to-end delivery proof,
  add a short-lived raising route on a review branch and remove it
  before merge — the Sprint 11 pattern; its recorded evidence is in
  `SPRINT_HISTORY.md`.
- *PostHog silent?* `VITE_POSTHOG_KEY` absent from the BUILD (Vercel
  env vars bake at build time — redeploy after adding).
- *A log field shows `[REDACTED]`:* the redactor matched a sensitive
  key/value shape; that is the control working, not a bug.
