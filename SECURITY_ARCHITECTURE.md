# DealerDOH Security Architecture

**Established:** Sprint 13 (Rails H + I — Security Hardening & Supply
Chain). This is the enduring reference for DealerDOH's trust
boundaries, authentication/authorization model, tenancy posture,
secret handling, transport/header controls, dependency policy, and the
security requirements that future work (especially Sprint 17 vendor
integration) must satisfy. The point-in-time findings and their
remediations live separately in [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md);
this document describes the system as it is *designed to be*.

Where this document and the code disagree, the code and its tests win —
fix the document. Governing rail contract:
[`V1_1_RELEASE_READINESS.md`](V1_1_RELEASE_READINESS.md) §5.H / §5.I.

---

## 1. Assets, actors, trust boundaries (the working threat model)

Deliberately practical, not exhaustive.

### Assets (what we protect)
- Dealership operational data — vehicles, events, tasks, recommendations, sync history.
- User identities and the role/membership authorization state.
- Uploaded vendor evidence (Tekion/Keyper/MDD/RecovR/RapidRecon CSVs).
- Auth credentials and session tokens (owned by Supabase Auth, never by DealerDOH).
- Service credentials — `DATABASE_URL`, the Supabase service-role key, telemetry DSNs.
- Migration backups and the production SQLite database (real dealership data).

### Actors (who interacts)
- Anonymous internet user (unauthenticated).
- Authenticated `lot_staff`, `sales_manager`, `manager`, `admin`.
- A compromised user account (valid token, hostile intent).
- A malicious insider (a legitimate low-privilege member escalating).
- An external attacker probing the API directly.
- A compromised dependency (build-time or runtime).
- A compromised vendor/integration source (Sprint 17 — future).

### Trust boundaries
```
Browser (React, untrusted)
   │  Bearer token on every call (no cookies for API auth)
   ▼
FastAPI  ◀── THE authorization boundary (api/auth.py) ──▶  Supabase Auth
   │  parameterized SQL, membership re-checked per request     (identity only)
   ▼
PostgreSQL (DEV) / SQLite (PROD)
```
- **Browser ↔ FastAPI** — the browser is never trusted; every operational
  request is authorized server-side by token signature + active membership.
- **FastAPI ↔ database** — the app is the only database client; the browser
  has no direct database path (why RLS is deferred — see §4).
- **FastAPI ↔ Supabase Auth/Admin** — identity, password, recovery, and the
  privileged Admin API (server-only service-role key).
- **Vercel / Render / GitHub Actions** — deployment/build platforms.
- **Future inbound email / vendor adapters** — Sprint 17; §8.

### Primary risks (ranked by the review)
Unauthorized dealership access · privilege escalation · cross-store
leakage · secret exposure · malicious upload · ingestion poisoning ·
dependency compromise · telemetry leakage · destructive operator error.

---

## 2. Authentication

Full design: [`AUTH_ARCHITECTURE.md`](AUTH_ARCHITECTURE.md). Security-relevant invariants:

- **Identity provider:** Supabase Auth (email/password, DEV only). DealerDOH
  stores no passwords, no tokens, no profile duplicates.
- **Token verification** (`api/auth.py`): signature verified against the
  project's public JWKS, **algorithm pinned to ES256** — HS256 (including
  against any retired legacy secret) and `alg:none` fail closed. Issuer,
  audience, and expiry are required and checked; `sub` is required. All
  proven by negative tests in `tests/test_auth.py`.
- **Auth-provider posture:** `AUTH_MODE=disabled` on production (the
  unauthenticated beta, byte-for-byte pre-Sprint-05 behavior);
  `AUTH_MODE=required` on DEV. Misconfiguration fails **closed** (500, never
  open — `test_required_mode_without_key_source_is_500_not_open`).
- **Public signup is disabled** project-wide; the invite flow is the only
  account-creation path (provider setting — confirm-manually item).
- **Password recovery** is Supabase-managed (expiring, single-use tokens);
  after a reset DealerDOH forces `signOut({scope:'global'})` — the strongest
  revocation the provider offers. Recovery is enumeration-safe.
- **Login errors** collapse to one generic message so the screen never
  reveals account state (Sprint 13, finding F5).
- **`user_metadata` is NEVER authoritative.** It carries only self-set
  profile fields (display name, onboarding state). Role, dealership, and
  organization come exclusively from the `user_membership` row. `display_name`
  is length/character-clamped when it crosses into DealerDOH (Sprint 13, F4).

---

## 3. Authorization (the boundary that matters)

**FastAPI is the single, tested authorization boundary. Frontend role
visibility is presentation only** — every hidden control has an
independent server check.

- Every operational router is protected at include time
  (`api/app.py::_OPERATIONAL_ROUTERS`), so a new router inherits protection
  by default. `/health` is the one deliberately public endpoint.
- **Role source of truth:** the membership row only. Role spoofing via token
  claims/query/body is structurally impossible
  (`test_role_cannot_be_spoofed_from_token_claims`).
- **BFLA:** the one enforced role gate is `POST /inventory-sync/run|validate`
  (admin/manager), enforced server-side via `require_roles`
  (`SYNC_RUN_ROLES`), negative-tested for every role. User administration
  (`/users`) is least-privilege: a manager can neither create nor administer
  an admin or another manager; nobody administers their own membership; the
  last active admin cannot be deactivated.
- **Membership revocation is immediate:** authorization re-reads the
  membership row on every request, so a still-valid JWT stops working the
  moment its membership is deactivated — no token revocation needed or
  pretended.
- **BOLA / object IDs:** identifier-taking endpoints (`/vehicles/{vin}`,
  `/tasks`, `/activity?vin=`, …) are scoped to the deployment's single serving
  dealership; the serving dealership comes from deployment configuration
  (`DEALERDOH_DEALERSHIP_ID`), **never from client input**. See §4 for the
  single-store model and its Store #2 prerequisite.

---

## 4. Multi-tenancy — the single-store model and the Store #2 gate

**True today:** every request is authorized against the deployment's own
serving dealership. A member of only another store gets 403
(`test_cross_store_denial`; the live `outsider@` account). One store's data
lives in one deployment's database.

**Not true yet (mandatory before a second real store shares a database):**
business rows (`vehicle`, `task`, `event`, …) are **not** per-row
store-scoped. The current model is *one store per deployment*, made
explicit rather than faked.

> **Store #2 security prerequisite (BLOCKING before onboarding a second
> store into one database):** per-row `dealership_id` scoping on business
> tables + query filters deriving the store from membership, **plus** RLS
> (see below). This is recorded as a blocking prerequisite, not an optional
> improvement. It is **not** an exploitable bug in the current single-store
> deployment — there is only one store's data to reach.

**RLS (Row-Level Security) is deliberately deferred** with documented
conditions (`AUTH_ARCHITECTURE.md`): the browser has no direct database
path (the Supabase Data API exposes no app tables), and the API connects as
the table owner (which RLS would not constrain). RLS becomes **required**
before any direct browser-to-database access or before Store #2. Enabling it
today would be decoration, not defense — do not enable it blindly.

---

## 5. Ingestion security

Full design: [`INGESTION_ARCHITECTURE.md`](INGESTION_ARCHITECTURE.md).
Sprint 10 established one validation boundary
(`sync/ingestion.py::validate_report_set`) that every acquisition path must
route through. Security-relevant properties, re-verified in Sprint 13:

- **Upload hardening:** CSV-only (Excel/OLE2 magic-byte rejected), 20 MB size
  cap enforced *during* streaming (writing stops at cap+1 so a hostile
  multi-GB body never lands), 50,000-row cap, BOM/duplicate-header/encoding
  checks. Files are saved under **fixed server-side names** (`{slot}.csv`) in
  a per-request timestamped directory — the client filename is never used as
  or in a path (no traversal). `/validate` deletes its uploads; `/run` keeps
  them as evidence of what was rejected.
- **Validation before mutation:** `/run` re-runs the full boundary on the
  uploaded bytes regardless of any prior `/validate`; a fingerprint-bound
  acknowledgement means a client cannot assert past a warning it never
  previewed.
- **Evidence semantics:** missing ≠ zero; invalid ≠ valid zero; the engine is
  presence-driven and never treats absence as evidence.
- **CSV formula injection (assessed):** the generated report CSVs contain
  vendor-controlled cells but are **written server-side and never served to a
  browser for download** — no current reachable path. If report download is
  ever added, cells beginning `=` `+` `-` `@` must be escaped before export.
  Recorded as a deferred control, not a current exposure.

---

## 6. Transport, CORS, and security headers

- **TLS everywhere** — Vercel (frontend) and Render (API) terminate HTTPS;
  Vercel sends HSTS. No plaintext path to authenticated traffic.
- **CORS** (`api/app.py`): an explicit origin allowlist (`LOTSYNC_CORS_ORIGINS`),
  never a wildcard, never origin-reflection. An unexpected origin gets no
  `Access-Control-Allow-Origin` (verified live). `X-Request-ID` is explicitly
  exposed so the browser can read the correlation id. Credentials are allowed
  but unused (the API authenticates by Bearer header, not cookies).
- **API security headers** (Sprint 13, `api/app.py` middleware — on every
  response including 404/500): `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`,
  `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. Deliberately no
  script/style CSP on the JSON API (it would break the Swagger UI and adds
  nothing to non-executable JSON).
- **Frontend security headers** (Sprint 13, `frontend/vercel.json`): a real
  Content-Security-Policy plus nosniff, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, and a restrictive
  `Permissions-Policy`. The CSP `connect-src` allowlist was enumerated from
  the deployed bundle — `'self'`, the API (`*.onrender.com`), Supabase Auth
  (`*.supabase.co`), Sentry ingest (`*.sentry.io`), and PostHog
  (`*.posthog.com`); `script-src 'self' https://*.posthog.com`, no
  `unsafe-eval`; `frame-ancestors 'none'`; `object-src 'none'`;
  `base-uri 'self'`. `style-src` allows `'unsafe-inline'` (React/Tailwind
  inline style attributes; not a meaningful XSS vector — inline *scripts* are
  not permitted) plus `https://fonts.googleapis.com`, and `font-src` allows
  `https://fonts.gstatic.com` — the app's typography `@import` (found live by
  the Sprint 13 deployed smoke, F9). Any Sprint 17 vendor origin must be
  added deliberately.
- **API documentation** (Sprint 13, deliberate decision — not obscurity):
  `/docs`, `/redoc`, `/openapi.json` are available in development/local (an
  integration convenience) and disabled when a deployment sets
  `ENVIRONMENT=production`. Current production predates that variable and is
  unaffected; a future production release train inherits the reduced surface.

---

## 7. Secret handling

- **Public-by-design vs secret is an explicit, enforced separation.** Browser
  identifiers — the Supabase publishable/anon key, the PostHog project token,
  the browser Sentry DSN — are intentionally in the bundle and are **not**
  secrets. Real secrets — `DATABASE_URL`, the Supabase **service-role** key,
  a future Sentry auth token, a PostHog personal key — live only in the
  deployment environment and the owner's password manager, **never** in git,
  the bundle, `VITE_*`, logs, or error bodies.
- **The service-role key is read in exactly one module** (`api/supabase_admin.py`)
  and never reaches a response.
- **Telemetry redaction** (`api/observability.py`): key- and value-shape
  redaction of tokens/DSNs/cookies/passwords across every structured-log
  field and Sentry event; exception messages are never logged (type names
  only); uploaded report contents never reach telemetry. (Sprint 11; re-verified.)
- **CI secret scanning** (Sprint 13): `tools/secret_scan.py` runs on every
  push/PR and fails the build on any credential-shaped material in the tracked
  tree; it distinguishes intentional public identifiers and documented
  non-secrets (the CI container DSN, placeholders). It is also the operator's
  re-scan tool for the public-release gate.
- **Full Git-history secret audit:** performed in Sprint 13 — see
  `SECURITY_AUDIT.md` for the result and the repository public-release gate.

---

## 8. Future integration security (Sprint 17 — documented, not implemented)

Sprint 17 adds an authenticated inbound-email callback for Keyper scheduled
delivery. It must reuse the Sprint 10 validation boundary (no second
validation path) and satisfy, before it may process unattended or be marked
Verified (see [`KEYPER_AUTOMATED_INTEGRATION_PLAN.md`](KEYPER_AUTOMATED_INTEGRATION_PLAN.md)):

- Provider **webhook signature / authentication** verification on the raw body
  before parsing.
- **Replay/idempotency** protection (provider message-ID + attachment SHA-256).
- **Timestamp / freshness** validation (Stale evidence ≠ current evidence).
- **Recipient/source allowlist** — recipient, sender, subject, filename, and
  MIME claim are transport hints, never evidence authority.
- **Attachment validation** through the existing classifier/validator; a
  WARNING defaults to **HOLD** (automation never auto-acknowledges).
- **Secret rotation** for the inbound webhook secret; the secret is server-only.
- No new first-class concepts; email is transport only.

---

## 9. Dependency / supply-chain policy (Rail I)

Proportional to a small two-language project — not an enterprise program.

- **Lockfiles are authoritative and committed** (`frontend/package-lock.json`);
  Python runtime deps are listed in `requirements.txt`.
- **CI scanning** (`.github/workflows/ci.yml` `security` job):
  - *Hard gate:* `npm audit --omit=dev --audit-level=high` — a High/Critical
    advisory in a **runtime-reachable** production dependency blocks the build.
  - *Hard gate:* the secret scan.
  - *Advisory:* `pip-audit` and full-tree `npm audit` surface transitive/dev
    findings for the exception register without red-X-ing every PR.
- **Triage, not blind fixing.** Findings are classified: runtime-reachable
  (fix or owner-except with a revisit date) vs build-only / transitive /
  unreachable (documented, not blindly upgraded). Never `npm audit fix --force`;
  no breaking major upgrades without impact analysis. The standing `nanoid`
  advisory (a build-only devDependency reachable only through vite, absent from
  the shipped bundle) is the model exception.
- **GitHub Actions** are first-party `actions/*` pinned to major-version tags;
  workflow token permissions are `contents: read`. SHA-pinning is a future
  hardening option, not required for first-party actions.
- **Review cadence:** the CI advisory output is the standing signal; a
  dependency review accompanies each security-relevant sprint and any new
  direct dependency.

---

## 10. What is deliberately deferred (with rationale)

- **Rate limiting** — the brute-force-sensitive surfaces (login, recovery)
  are Supabase-throttled at the provider; the app's own mutation endpoints are
  authenticated, single-store, and low-abuse. A durable/distributed limiter is
  deferred because Render may run multiple workers, so an in-memory limiter
  would not be globally authoritative; shipping one would be security theater.
  Revisit if abuse is observed or at multi-store scale.
- **RLS / per-row store scoping** — deferred with the §4 conditions; required
  before Store #2 or any browser-to-database path.
- **MFA** — post-v1.1 (Supabase supports it; enforcement is a future decision).
- **Source-map upload to Sentry** — no source maps are served publicly
  (`vite.config.ts sourcemap:false`, verified: zero `sourceMappingURL` in the
  production bundle); secure upload with a build-secret auth token is deferred
  to production observability activation. The token must never ride `VITE_*`.
- **CSV formula escaping** — deferred until report CSVs become downloadable (§5).

Each deferral is an owner-visible accepted risk, recorded in
`SECURITY_AUDIT.md`'s register — not a silent omission.
