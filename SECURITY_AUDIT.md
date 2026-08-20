# DealerDOH Security Audit — Sprint 13

**Point-in-time.** Read-only audit performed 2026-08-19 on
`feature/sprint-13-security-supply-chain` (from `dev` = `384970b`),
followed by remediation and re-audit. Enduring architecture is in
[`SECURITY_ARCHITECTURE.md`](SECURITY_ARCHITECTURE.md); this is the
evidence record. Governing contract: `V1_1_RELEASE_READINESS.md`
§5.H / §5.I / §5.H.1.

> **Merged + deployed-verified (2026-08-19):** PR #21 merged as `dev` =
> `6bb3a9c`; CI green on the merged head including the Security scans
> job; both DEV services verified serving the merge SHA; the deployed
> security smoke PASSED (headers live on API 200/404 and frontend, CORS
> allow/deny/expose, live `signup_disabled` probe, manager surfaces +
> roster policy under CSP, work-order PDF, validate-only upload matrix
> with zero mutation, Sentry zero-noise across the expected-4xx probe
> window, QA dealership intact, seed guard exercised non-destructively,
> production docs-gating subprocess-proven). One smoke-found Low (F9,
> Google Fonts vs CSP) fixed in the closeout PR. **Rails H + I:
> Verified.** Full record: `SPRINT_HISTORY.md` Sprint 13 entry.

## Methodology

Read-only audit FIRST, then remediation, then re-audit. Every claim is
classified with file/line evidence:

- **PASS** — repository/config evidence supports the control.
- **FAIL** — repository/config evidence supports a vulnerability/gap.
- **UNKNOWN** — code alone cannot prove external/provider behavior.
- **N/A** — genuinely not applicable to this stack.

UNKNOWN is never silently promoted to PASS. The "75 Common Vibe-Coded
Web App Vulnerabilities" handbook was used as a threat catalog, not as
proof of presence. Findings were produced by manual review plus a
delegated file-by-file sweep and automated scans (npm audit, pip-audit,
a full-Git-history secret scan, a current-tree secret scan, and a
production bundle scan).

## SECURITY SCORE: 42 / 45 applicable checks PASS

3 checks were FAIL at audit time; all 3 are remediated in this sprint
(§ Findings). 4 items are UNKNOWN (provider-side, Confirm-Manually). No
Critical or reachable High vulnerability was found.

- **Critical (exploitable now): 0**
- **High (reachable): 0**
- **Medium: 1** (remediated) + 1 architectural prerequisite (Store #2, deferred)
- **Low: 5** (3 remediated, 2 accepted/deferred)
- **Repository history: CLEAN** (no secret ever committed)

---

## Findings

Severity is by actual reachability in the deployed architecture, not by
the handbook's generic label.

### F1 — Weak destructive-operation guard in `seed_dev.py` — Medium — FIXED
- **Evidence:** `seed_dev.py` (pre-fix): under `DATABASE_ENGINE=postgres`,
  `db_path` is always `None`, so the production-path guard was dead code and
  the destructive `--reset` (drops 14 application tables from whatever
  `DATABASE_URL` names) was gated only by an exact-string
  `ENVIRONMENT == "production"` match.
- **Impact:** an operator with `ENVIRONMENT` unset, `"prod"`, `"staging"`,
  etc. could drop every table in the target database — a destructive
  operator-error risk (a named primary risk). Not remotely reachable (a dev
  CLI, not an endpoint); blast radius is a PostgreSQL `DATABASE_URL`.
- **Remediation:** `refuse_if_production` now **fails closed** — a postgres
  `--reset` proceeds only when `ENVIRONMENT` explicitly names a development
  environment (`development`/`local`/`test`), not merely when it is not
  "production". Regression: `tests/test_seed_dev.py::PostgresResetGuardTest`.
- **Final state: PASS.**

### F2 — Vendor free-text persisted and surfaced verbatim — Low — ACCEPTED
- **Evidence:** `sync/reconciler.py` writes raw vendor CSV cells (e.g.
  RapidRecon's `Note`) into `Event.detail_fields`, surfaced via the untyped
  `ActivityDTO.detail_fields` (`api/dtos.py`).
- **Impact:** content, not injection — React escapes it as text (no XSS), and
  telemetry redaction keeps it out of logs. This is inherent to an
  evidence-aggregation product.
- **Disposition: ACCEPTED** (operational data by design; no XSS path; not
  rendered as HTML). Revisit if these fields are ever rendered as markup or
  exported.

### F3 — Unguarded coercions in the reconciler — Low — ACCEPTED
- **Evidence:** `sync/reconciler.py` has no `try/except`; malformed values
  past the ingestion contract raise mid-sync.
- **Impact:** availability/consistency (a partially-applied sync with
  per-source transactional integrity), **no disclosure** — the router masks
  the error as a generic 500 with a request id
  (`api/routers/inventory_sync.py`).
- **Disposition: ACCEPTED** — the Sprint 10 validation boundary rejects
  malformed shapes before the engine runs; per-source transactions contain
  the blast radius. Not expanding scope to wrap 1,563 lines.

### F4 — Unbounded self-set `display_name` — Low — FIXED
- **Evidence:** `display_name` is self-written to `user_metadata` and rendered
  in the admin roster; the server previously accepted any string
  (`isinstance` check only).
- **Impact:** UI spoofing (e.g. a misleading roster name); no XSS (escaped as
  text); never affects authorization.
- **Remediation:** `api/auth.py::clamp_display_name` bounds it to 100 chars
  and strips control characters at both boundaries where it enters DealerDOH
  (`AccessContext` and `api/supabase_admin.py::_safe_user`). Regression:
  `tests/test_auth.py::DisplayNameClampUnitTest` + `/me` integration tests.
- **Final state: PASS.**

### F5 — Login error leaked account state — Low — FIXED
- **Evidence:** `frontend/src/auth/Login.tsx` (pre-fix) surfaced non-"Invalid
  login credentials" Supabase errors verbatim (e.g. "Email not confirmed"),
  partially undercutting the enumeration-safe recovery flow.
- **Remediation:** every sign-in failure now collapses to one generic
  "Invalid email or password." (rate-limit notices excepted, revealing
  nothing about the account).
- **Final state: PASS** (frontend; covered by the production build + DEV smoke).

### F6 — ReportLab markup injection from vendor text — Low — FIXED
- **Evidence:** `reports/work_order.py` embedded vendor stock numbers/VINs and
  the operator store name into reportlab Paragraph mini-markup unescaped.
- **Impact:** a `<`/`>`/`&` in a value would break the Paragraph parser
  mid-render (a generic 500), not XSS (the output is an `attachment` PDF).
- **Remediation:** `_markup_safe()` escapes vendor/operator text before it
  enters the markup. Regression: `tests/test_work_order.py::VendorMarkupEscapingTest`.
- **Final state: PASS.**

### F7 — Missing security headers — Medium (defense-in-depth) — FIXED
- **Evidence (audit, deployed):** the DEV API returned **no** security headers;
  the DEV frontend had HSTS (Vercel) but **no** CSP, frame protection, nosniff,
  or referrer/permissions policy.
- **Impact:** no clickjacking protection, no MIME-sniffing protection, no CSP
  defense-in-depth against injected content. Reachability is limited (Bearer
  JSON API, React auto-escaping, no cookies), hence Medium not High.
- **Remediation:** API middleware (`api/app.py`) + `frontend/vercel.json` CSP
  and header set (§6 of the architecture doc). Regression:
  `tests/test_security_headers.py`, `tests/test_frontend_config.py::SecurityHeadersConfigTest`.
- **Final state: PASS** (config pinned by tests; deployed values on the DEV
  smoke checklist).

### F8 — Client dealership identity in the tree — Informational — REPO-GATE NOTE
- **Evidence:** the real client name ("Mark Kia" / `MARK_AUTO`) is present in
  importers, fixtures, config, and docs.
- **Impact:** none to running security; relevant only to the **public-release**
  decision (it identifies the customer). Not a secret. Recorded in the
  public-release gate below for owner awareness before any publication.

### F9 — CSP blocked the Google Fonts stylesheet — Low — FIXED (found by the deployed smoke)
- **Evidence:** `frontend/src/index.css` `@import`s Plus Jakarta Sans /
  JetBrains Mono from `fonts.googleapis.com`; the first CSP's
  `style-src 'self' 'unsafe-inline'` blocked it (console violation on
  every load; silent system-font fallback — nothing functional broke).
  The origin-enumeration pass missed it because the reference lives in
  the built CSS, not the JS bundle or network capture.
- **Remediation:** `style-src` additionally allows
  `https://fonts.googleapis.com` and `font-src` allows
  `https://fonts.gstatic.com` (`frontend/vercel.json`); pinned by
  `tests/test_frontend_config.py::test_csp_allows_google_fonts`.
- **Final state: PASS** (exactly why deployed verification is an exit
  requirement — config-level controls need live proof).

---

## Category results (PASS / FAIL / N/A / UNKNOWN)

| Category | Result | Evidence |
|---|---|---|
| BOLA / IDOR | PASS (single-store) | `api/auth.py` serving-dealership from config; `tests/test_auth.py` |
| BFLA / function-level authz | PASS | `require_roles`, `/users` policy; `test_user_management.py`, `test_auth.py` |
| Privilege escalation / mass assignment | PASS | role from membership only; `InviteRequest` ignores extra keys; `test_role_cannot_be_spoofed…` |
| Cross-store isolation | PASS (single-store) + Store #2 prerequisite | `test_cross_store_denial`; `AUTH_ARCHITECTURE.md` |
| JWT verification (alg/iss/aud/exp/kid) | PASS | `api/auth.py`; `test_auth.py` negative suite |
| `user_metadata` trust | PASS | role never from metadata; `display_name` clamped (F4) |
| Public signup / recovery / session | PASS (code) / UNKNOWN (provider config) | `ACCOUNT_LIFECYCLE.md`; `Login.tsx`, `ResetPassword.tsx` |
| SQL injection | PASS | parameterized throughout; dynamic identifiers are code constants only (`database/repository.py`, `queries/*`) |
| Command / template / deserialization injection | N/A | no shell (`grep` clean), no server templating, no untrusted deserialization |
| XSS | PASS | zero `dangerouslySetInnerHTML`/`innerHTML` in `frontend/src`; React text-escaping; F6 PDF markup fixed |
| CSRF | N/A | Bearer-token API, no cookie auth (`api/client.ts`, `api/app.py`) |
| CORS | PASS | explicit allowlist, no reflection (verified live); `api/app.py` |
| Security headers / CSP / clickjacking | FAIL→PASS | F7 (remediated) |
| SSRF | N/A | only outbound fetches are to configured Supabase (`api/auth.py`, `api/supabase_admin.py`); no user-supplied URL |
| File upload safety | PASS | fixed names, size/row caps, magic-byte, no traversal (`api/routers/inventory_sync.py`, `sync/ingestion.py`) |
| CSV formula injection | N/A now (deferred) | outputs not served for download (`reports/writer.py`) |
| PDF generation | FAIL→PASS | F6 (remediated) |
| Rate limiting / brute force | Deferred (accepted) | provider-throttled auth; §10 architecture |
| Error handling / leakage | PASS | generic 500 + request id, type-name-only logs (`api/app.py`, `api/observability.py`) |
| Logging / telemetry redaction | PASS | Sprint 11 redaction re-verified (`api/observability.py`; `test_observability.py`) |
| Debug / test routes | PASS | no crash/raise endpoint (test-pinned 404); figma plugins dev-only (`vite.config.ts`) |
| API docs exposure | FAIL→PASS (decision) | env-gated (F7 area); `api/app.py` |
| Source maps | PASS | none served (`vite.config.ts sourcemap:false`; bundle scan: 0 `sourceMappingURL`) |
| Secrets — current tree | PASS | `.env` untracked, placeholders only; `tools/secret_scan.py` clean |
| Secrets — frontend bundle | PASS | bundle scan: no service-role/DSN/auth-token (only the `sb_secret_` **literal string** in supabase-js code, not a value) |
| Secrets — Git history | PASS | full-history scan: 0 real secrets (§ Sanitation) |
| Supabase service-role key | PASS | server-only, one module (`api/supabase_admin.py`) |
| RLS posture | Deferred (documented) | no browser→DB path (`AUTH_ARCHITECTURE.md`) |
| Dependencies (npm/pip/actions) | PASS (with 1 dev-only advisory) | § Supply chain |

---

## Multi-tenancy: **Is DealerDOH safe for Store #2 today?**

**No — not for two stores sharing one database.** The current architecture
is safe as *one store per deployment* (verified isolation), but business
rows are not per-row store-scoped. **Exact prerequisites before Store #2**
(none of which is a current exploit, because there is only one store's data
per database):
1. Per-row `dealership_id` scoping on `vehicle`, `task`, `event`,
   `recommendation`, `sync_run`, `report_baseline`, and pending-identity rows.
2. Query filters deriving the store from the caller's membership (not client input).
3. RLS policies + a non-owner database role (before any direct browser→DB path).
4. Cross-store isolation tests across all of the above.

Recorded as a **blocking Store #2 prerequisite** (SECURITY_ARCHITECTURE.md §4),
not scheduled for implementation in Sprint 13 (no current exploitable bug).

---

## Secrets

- **Current tree:** CLEAN. No `.env`, DB, dump, or backup tracked; both
  `.env.example` files hold placeholders/commented public identifiers only;
  `tools/secret_scan.py` passes (321 tracked files, 0 secrets).
- **Frontend bundle:** CLEAN. Scanned the production build — no service-role
  key, `DATABASE_URL`, Sentry auth token, or PostHog personal key. The only
  `sb_secret_` occurrence is the **literal prefix string** inside supabase-js's
  own key-type check, not a credential value.
- **Git history (all commits/branches/tags):** CLEAN. A full-history scan of
  685 blobs found **zero real secrets**. The only credential-shaped strings are
  documented non-secrets: the CI PostgreSQL service container's throwaway
  `postgres:postgres@127.0.0.1` DSN (`.github/workflows/ci.yml`) and
  documentation/test placeholder DSNs (`u:p@h`, `user:pass@host` in
  `SQLITE_TO_POSTGRES_ASSESSMENT.md`, `tests/test_observability.py`). No
  `sb_secret_*`, service-role JWT, private key, or provider token was ever
  committed.
- **Provider/manual (UNKNOWN — Confirm Manually):** whether the Supabase
  service-role key / DB password / provider dashboards hold any exposed
  credential is not repo-verifiable — see Confirm-Manually.

*No secret value appears anywhere in this report — only masked fingerprints
and classifications.*

---

## Repository Public-Release Sanitation (§5.H.1)

- **Full-history audit:** performed read-only across all reachable commits,
  branches, tags, and deleted files (`tools/secret_scan.py` covers the current
  tree in CI; the history sweep was a one-time full-blob scan).
- **Historical secret exposure:** **none found.** No credential requires
  rotation on the basis of repository history. Therefore **no Git-history
  rewrite is warranted** and none was performed (per the rules: rotation would
  come first, and there is nothing to rotate).
- **Current-tree checklist:** `.gitignore` excludes local secret files ✓;
  `.env.example` placeholders only ✓; no DB/backup tracked ✓; bundle has only
  intentional public identifiers ✓; no source maps served ✓; CI secret-scanning
  now exists ✓; dependency scanning now exists ✓; docs reveal no credentials ✓.
- **Non-secret disclosure note (F8):** publication would disclose the client
  dealership identity ("Mark Kia") present throughout importers/fixtures/docs —
  an owner-awareness item, **not** a secret and **not** a blocker for the
  secret gate.

### Gate state

> **REPOSITORY PUBLIC-RELEASE GATE: `Audit Clean` — but publication remains a
> separate owner decision, and the repository stays PRIVATE.**

The history-secret dimension is clean (state advances from `Not Audited` →
`Audit Clean`). This clears the **secret** blocker only. Actually making the
repository public is out of scope for Sprint 13 and requires the owner to
separately accept the F8 customer-identity disclosure. **Not made public.**

---

## Supply chain (Rail I)

- **npm:** production dependencies **clean** (`npm audit --omit=dev
  --audit-level=high` → 0). One High advisory exists in `nanoid@3.3.16`, a
  **build-only devDependency** reachable only through `vite → postcss`, absent
  from the shipped bundle — classified **not reachable**, consistent with the
  standing classification. Not force-fixed.
- **pip:** `pip-audit` on the installed environment → **no known
  vulnerabilities**.
- **GitHub Actions:** first-party `actions/*` on major-version tags; workflow
  permissions `contents: read`. No untrusted PR-secret exposure; no install
  hooks of concern.
- **CI gate added:** the `security` job (secret scan + prod-dep audit as hard
  gates; pip-audit + full npm audit as advisory).

---

## Telemetry security

Sprint 11 posture re-verified: no passwords/tokens/cookies/emails/VINs/report
bodies in logs or Sentry; layered redaction (`api/observability.py`); no
session replay, no autocapture, no pageview (`frontend/src/observability/`);
internal-UUID identity only. PASS.

---

## Confirm Manually (provider-side, not repo-verifiable — UNKNOWN)

1. Supabase: public signups disabled project-wide; redirect-URL allowlist
   limited to the DEV reset-password URL.
2. Supabase service-role key and DB password are healthy/unexposed in the
   provider dashboard (rotate only on an evidence-backed exposure — none found).
3. Render/Vercel: secrets only in environment (never build logs); account
   access via individual logins with 2FA.
4. Domain/DNS (`dealerdoh.com`): registrar 2FA, CAA records — pre-publication.
5. HSTS/TLS coverage across all subdomains before any HSTS `preload` decision.

---

## Accepted risks / deferred (owner-visible)

| Item | Disposition | Rationale |
|---|---|---|
| Store #2 per-row scoping + RLS | Deferred (blocking prereq for 2nd store) | no current exploit in single-store deployment |
| Rate limiting (app-side) | Deferred | provider throttles auth; multi-worker Render makes in-memory limiter non-authoritative |
| Source-map upload | Deferred | none served; secure upload belongs to prod observability activation |
| CSV formula escaping | Deferred | report CSVs not downloadable today |
| F2 vendor free-text, F3 reconciler coercions | Accepted (Low) | no disclosure; contained by Sprint 10 boundary + React escaping |
| MFA | Post-v1.1 | future decision |
| Sprint 17 webhook controls | Documented, not implemented | `KEYPER_AUTOMATED_INTEGRATION_PLAN.md` |
| nanoid advisory | Accepted | build-only devDependency, unreachable |
| Customer identity in repo (F8) | Owner decision | blocks public-release only, not v1.1 |
