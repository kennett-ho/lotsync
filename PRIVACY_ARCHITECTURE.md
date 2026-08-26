# DealerDOH Privacy Architecture

**Established:** Sprint 15 (Rail L — Privacy / Legal Readiness).
This is the enduring technical description of what data DealerDOH
actually processes, where it lives, who can reach it, which third
parties touch it, and how long it remains. It is internal engineering
truth, deliberately separate from any customer-facing legal copy
(`PRIVACY_POLICY.md` and friends are *derived from* this document and
must never claim more than it proves). Point-in-time legal analysis
lives in [`LEGAL_READINESS.md`](LEGAL_READINESS.md); retention policy
in [`DATA_RETENTION.md`](DATA_RETENTION.md).

Where this document and the code disagree, the code and its tests win
— fix the document. Amend it in the same PR as any change to data
collection, storage, telemetry, providers, or retention behavior.
Governing rail contract: `V1_1_RELEASE_READINESS.md` §5.L.

**Evidence discipline.** Every claim here is one of:
- **[repo]** — verified from this repository's code/config/tests.
- **[measured]** — observed live on deployed DEV (date noted).
- **[provider]** — from the provider's own documentation (link +
  as-of date noted); re-verify before publication-grade claims.
- **[decision]** — an owner/governance decision, with its record.

---

## 1. The two deployed realities

DealerDOH's privacy posture is TWO postures today, and honest
documentation must not blur them:

| | Production (LotSync `v1.0.0-beta.6`) | DEV / v1.1 target stack |
|---|---|---|
| Users | Dealership personnel (Mark Kia), unauthenticated | Synthetic QA users; real staff arrive at UAT/production release |
| Auth | **None** (`AUTH_MODE` unset = disabled) [repo] | Supabase Auth, `AUTH_MODE=required` [repo] |
| Database | SQLite on Render persistent disk `/var/data/lotsync.db` [repo: `PRODUCTION_BASELINE.md`] | Supabase PostgreSQL (`dealerdoh-dev`, us-west-2) [repo: `DEV_ENVIRONMENT.md`] |
| Telemetry | **No Sentry, no PostHog, no analytics of any kind** — production sets none of the telemetry variables [repo: `OBSERVABILITY.md` §9] | Sentry + PostHog + structured logs, bounded per §6 |
| Data | Real dealership operational data (~4,700 vehicles) | Synthetic QA dealership only (`1QATEST…` VINs) [repo: `SYNTHETIC_QA_MATRIX.md`] |

The v1.1 release train migrates production to the right-hand column
under its own approvals (`PRODUCTION_MIGRATION_PLAN.md`). Customer-
facing documents drafted in Sprint 15 describe the **v1.1 stack**,
because that is what dealership users will be given; they must not be
published as descriptions of the current unauthenticated beta.

## 2. Data inventory (what is actually stored)

Thirteen application tables exist (migrations 0001–0010, both
engines) [repo: `database/migrations/`]. By category:

### 2.1 Vehicle operational data (the product's subject matter)

| Data | Where | Contents relevant to privacy |
|---|---|---|
| Vehicle identity | `vehicle` | VIN, stock number, `display_name` ("Year Make Model" verbatim from Tekion), per-source statuses. **VINs of dealership inventory — not linked to any consumer identity anywhere in the system** [repo] |
| History | `event` | `event_type`, `source`, timestamps, human-readable `summary`, `detail_fields` (structured dict). Summaries are template-generated ("Keyper: key checked Out, matched Tekion stock …") and contain **no person names** [repo: `sync/reconciler.py`] |
| Work | `task`, `task_execution_event` | Task type/priority/reason (rule-generated text), commitment/execution state. `assigned_employee_id` / `ratified_by` / `actor_employee_id` columns exist but **no write path populates them today** — no task-write or event-write endpoint exists [repo: `api/routers/`] |
| Recommendations | `recommendation` | Rule-generated titles/details (stock numbers, day counts) |
| Sync provenance | `sync_run`, `report_baseline`, `event_freshness`, `pending_identity` | Source names, counts, timestamps, raw unresolved identifiers (stock-number-shaped strings from Keyper) |
| Access model | `organization`, `dealership`, `user_membership` | See §3. `employee` table exists (migration 0006) and is **empty in both environments** — no code writes it [repo; verified against production backup inventory 2026-08-16 and the QA seed] |

**Vendor free text (the one incidental-personal-data vector):**
RapidRecon rows persist `recon_note`, `recon_priority`, `recon_recall`
verbatim into `Event.detail_fields` [repo: `sync/reconciler.py`
`persist_rapidrecon_observations`]. These are vendor-operator-typed
cells and *can* incidentally contain staff names ("waiting on Mike").
This is Security Audit finding F2 (Accepted — operational evidence by
design, rendered as text only, never in telemetry). Keyper's `Reason`
column is read but not persisted into events today.

### 2.2 Account / workforce identity (v1.1 auth stack)

| Data | System of record | DealerDOH's copy |
|---|---|---|
| Email, password, recovery/session tokens, last-sign-in | **Supabase Auth** (provider) | **None.** DealerDOH stores no passwords, tokens, or profile duplicates [repo: `AUTH_ARCHITECTURE.md`] |
| Display name, onboarding completion | Supabase Auth `user_metadata` (self-set; clamped to 100 chars, control chars stripped) | Not stored; travels inside the verified JWT per request [repo: `api/auth.py`] |
| Authorization | DealerDOH `user_membership` | `auth_user_id` (Supabase UUID as TEXT), organization, dealership, role, `active` — **the only account data in DealerDOH's own database** [repo: migration 0009] |

Who sees workforce identity inside the product: `GET /me` returns the
caller their *own* email/display name/role; the User Management
roster (`GET /users`, admin+manager only) lists members' emails,
display names, roles, and active state [repo: `api/routers/users.py`].
Lot staff and sales managers have no roster access.

Vendor-reported person names (Keyper `User`, `Issue Comment`,
`User Description`) are **not ingested today** — the current Keyper
contract reads `name`(stock), `Status`, `System`, `Location`,
`Reason`, `Checkout Date` only [repo: `sync/pipeline.py`,
`sync/report_contracts.py`]. They arrive only with the planned
Sprint 17 contract extension (§9).

### 2.3 Consumer data boundary — **none in the operational data model, verified**

**DealerDOH's intended, validated data flows ingest and store NO
consumer/customer personal information** (the raw-upload caveat
below is the one qualifier): no customer names, phone numbers, email
addresses, postal addresses, driver's-license data, deal numbers tied
to consumers, credit/financing data, SSNs, bank or payment-card data.
Verification, not assumption:

- Every governed report contract's column set is vehicle/key/device/
  recon operational data [repo: `sync/report_contracts.py` §3 table
  in `INGESTION_ARCHITECTURE.md`].
- Every reconciler persist function writes only
  stock/status/date/count fields (plus the §2.1 free-text note)
  [repo: `sync/reconciler.py`].
- The Tekion *sold* report asserts sale events (stock, VIN, sold
  date) **without purchaser identity** [repo: fixtures + contract].
- No API endpoint accepts consumer data; there is no CRM, deal, or
  financing surface [repo: `api/routers/`].

**Caveat that keeps this honest:** classification matches on a
signature-column *subset*, so a vendor export carrying extra columns
still classifies [repo: `sync/report_classifier.py`]. The operational
database would still ignore those columns — but the **raw uploaded
file is retained verbatim** (§7). If a dealership operator ever
exports a report variant containing customer fields, those bytes
would sit in the upload store even though nothing reads them. The
controls are operator export hygiene plus the raw-upload retention
decision in `DATA_RETENTION.md` (**D4 ratified 2026-08-21: raw
uploads are temporary operational evidence — 7-day accepted /
30-day rejected-or-HOLD bounded retention with deletion, never an
indefinite default; the tested implementation is pending as the
bounded retention remediation and is release-gating for v1.1 —
until it ships, files persist verbatim**; this
incidental-receipt possibility is also why the GLBA/Safeguards
assessment in `LEGAL_READINESS.md` §4 is stated non-categorically). Today's real export shapes carry no such columns
(evidenced by the contract registry and the synthetic fixtures that
mirror them).

**Trigger (recorded, owner-refined 2026-08-20):** if DealerDOH ever
**receives, retains, maintains, processes, or is permitted access
to** consumer/customer information — by deliberate ingestion (financing,
deal, CRM, credit, payment, or consumer-identity data), by
integration/DMS access, or by **discovering such content in
retained raw uploads** — the legal posture changes materially:
reassess `LEGAL_READINESS.md` §4 (GLBA/Safeguards) *before*
implementation, or immediately upon discovery for the incidental
case.

## 3. Access model (who can reach what)

- **FastAPI is the single authorization boundary** — token signature
  (ES256-pinned) + active membership in the serving dealership,
  re-read per request; roles from the membership row only
  [repo: `AUTH_ARCHITECTURE.md`, `tests/test_auth.py`].
- All operational reads are shared across active members of the
  store; the enforced role gates are sync run/validate
  (admin/manager) and user administration (admin/manager, least-
  privilege matrix) [repo].
- The browser has **no direct database path** (Supabase Data API
  exposes no app tables; RLS deferred with recorded conditions)
  [repo: `AUTH_ARCHITECTURE.md`].
- Operator/administrative access outside the app: Supabase dashboard
  (Auth admin, database), Render dashboard (env, disk, logs), Vercel
  dashboard, Sentry, PostHog, GitHub — all owner-held accounts
  [decision: single-operator beta; see `SECURITY_AUDIT.md`
  Confirm-Manually items for the 2FA/provider-hygiene checklist].
- One store per deployment; Store #2 in a shared database is a
  **blocking prerequisite** (per-row scoping + RLS) recorded in
  `SECURITY_ARCHITECTURE.md` §4 — also a privacy boundary, since
  cross-store data separation is what it enforces.

## 4. Browser storage (measured, deployed DEV, 2026-08-20)

Census of everything the v1.1 frontend stores in the browser
[measured on `https://dealerdoh-dev.vercel.app` with an authenticated
session]:

| Storage | Key | Contents | Essential? |
|---|---|---|---|
| localStorage | `sb-<project-ref>-auth-token` | The Supabase session (access + refresh token JSON). Written/owned by supabase-js; survives refresh; cleared on sign-out | **Yes** — this IS the login session [repo: `frontend/src/auth/supabase.ts`] |
| localStorage | `ph_<token>_posthog` | PostHog persistence: random `$device_id`, `distinct_id` (the internal auth UUID after identify — verified UUID-shaped, never email), session id, super props (`environment`, `release`), person-prop cache (`role`, `dealership_id`, `organization_id`, `environment`), SDK config mirrors | Analytics only |
| sessionStorage | `ph_<token>_window_id` + 3 siblings | PostHog per-tab window/session bookkeeping | Analytics only |
| Cookies | ~~`ph_<token>_posthog`~~ | **Pre-Sprint-15:** posthog-js's default `persistence: 'localStorage+cookie'` also wrote one first-party cookie duplicating the identifier state ($device_id, distinct_id, session id). **Sprint 15 remediation:** `persistence: 'localStorage'` is now explicit — the SDK keeps identity in localStorage only and **DealerDOH sets no cookies at all** (pinned by `tests/test_frontend_observability_config.py`) | — |

Not stored anywhere in the browser: passwords (Supabase receives
them transiently at sign-in over TLS), report contents, vehicle
data (rendered from API responses, never cached — the API sends
`Cache-Control: no-store` [repo: `api/app.py`]), theme/preference
state (none exists). Onboarding completion lives server-side in
Supabase `user_metadata`, not browser storage [repo].

The API authenticates by `Authorization: Bearer` header exclusively —
**no cookie is used for authentication anywhere** (which is also why
CSRF is structurally N/A) [repo: `SECURITY_AUDIT.md`].

## 5. Data-flow map (current runtime)

```text
                       ┌──────────────────────────────────────────┐
                       │ Person at the dealership (browser)       │
                       └───────┬──────────────────────────────────┘
              HTTPS (TLS)      │
   ┌───────────────────────────┼───────────────────────────────────┐
   │                           ▼                                   │
   │  [A] Vercel — static frontend (dealerdoh-dev.vercel.app)      │
   │      serves JS/CSS; platform edge/request logs (provider)     │
   │                           │                                   │
   │        sign-in, session   ▼ refresh, recovery, invites        │
   │  [B] Supabase Auth (dealerdoh-dev, us-west-2)                 │
   │      email, password, tokens, user_metadata, auth audit logs  │
   │                           │  ES256 JWT                        │
   │                           ▼                                   │
   │  [C] Render — FastAPI (dealerdoh-api-dev.onrender.com)        │
   │      authorization, business logic, uploads, structured logs  │
   │        │            │                │                        │
   │        ▼            ▼                ▼                        │
   │  [D] Supabase   [E] Upload/     [F] Sentry (errors,           │
   │      PostgreSQL     output          scrubbed, no user         │
   │      (business      files on        identity)                 │
   │      data)          service disk/                             │
   │                     filesystem                                │
   │                                                               │
   │  [G] PostHog (browser → us.i.posthog.com): explicit product   │
   │      events, identity = internal auth UUID                    │
   └───────────────────────────────────────────────────────────────┘

   Separate, operator-driven flows (not runtime):
   [H] Production backup: SQLite online backup → Render disk
       /var/data/backups/ → operator machine (LotSync-Backups) —
       real dealership data, owner-held [repo: PRODUCTION_BASELINE.md]
   [I] GitHub (private repo): source + synthetic fixtures ONLY —
       no real dealership operational data, no customer data, no
       secrets (full-history audit clean) [repo: SECURITY_AUDIT.md]

   FUTURE (Sprint 17 — planned, NOT current): inbound-email provider
   → webhook → Sprint 10 validation boundary. Adds a subprocessor,
   message metadata, and attachment retention — Rail L must be
   amended then (§9; V1_1_RELEASE_READINESS §5.L delta rule).
```

Per-arrow data categories: browser→[A] static asset requests;
browser→[B] credentials (transient), session refresh; browser→[C]
Bearer token + operational requests + uploaded report files
(admin/manager only); [C]→[D] business rows (§2.1) + membership
reads; [C]→[E] raw uploaded CSVs + generated report CSVs; [C]→[F]
unhandled-exception events (scrubbed, §6); browser→[G] explicit
events (§6). Production today runs only browser→[A]→[C]→SQLite+[E]
— no [B], [F], [G] [repo].

## 6. Telemetry (privacy-bounded, verified)

Canonical design: [`OBSERVABILITY.md`](OBSERVABILITY.md). The
privacy-load-bearing facts, re-verified for Sprint 15:

- **Structured logs**: route *templates* only (never raw paths — a
  raw path can carry a VIN), safe IDs only (`auth_user_id`, role,
  store/org IDs), no email/name/VIN/report contents; key- and
  value-shape redaction; exception type names only. Enforced by
  `tests/test_observability.py` [repo].
- **Backend Sentry**: unhandled exceptions only; `send_default_pii`
  false, local variables off, request bodies never, cookies
  wholesale-redacted, querystrings dropped [repo].
- **Frontend Sentry**: no user identity attached at all; replay
  never imported + init-filtered; breadcrumb URLs masked
  (identifier-like segments → `*`, querystrings dropped) [repo:
  `frontend/src/observability/sentry.ts`].
- **PostHog**: explicit event taxonomy only. Deployed-bundle
  byte-check 2026-08-20 [measured]: `autocapture:!1`,
  `capture_pageview:!1`, `capture_pageleave:!1`,
  `disable_session_recording:!0`, `disable_surveys:!0`,
  `person_profiles:'identified_only'`, zero `replayIntegration`
  references. Identity = internal auth UUID; person properties are
  exactly `role`/`dealership_id`/`organization_id`/`environment`
  [measured: persistence contents, 2026-08-20]; `posthog.reset()` on
  sign-out severs identity [repo].
- **What telemetry deliberately never receives** (the §7
  denylist, test-enforced): passwords, tokens, cookies, emails,
  display names, VINs, stock numbers, filenames, report
  contents/rows, raw querystrings [repo: `OBSERVABILITY.md` §7].
- Live payload evidence at this posture is recorded in
  `SPRINT_HISTORY.md` (Sprint 11 tri-correlation + 15-question
  review; Sprint 12/13/14 re-verifications on deployed DEV).

### IP addresses and device metadata (the honest platform-layer answer)

DealerDOH's own application records contain **no IP addresses and no
user-agent/device fields** [repo: log schema, §4 of
`OBSERVABILITY.md`]. But the platforms underneath do observe them:

| Layer | What it sees | Where it lands | Bound |
|---|---|---|---|
| uvicorn access log (in-process) | client IP + request line | Render service logs | Render log retention — 7 days on the current plan tier [provider: render.com/docs/logging, 2026-08-20] |
| Render / Vercel edge | connection IPs, TLS metadata | provider infrastructure logs | provider-internal |
| Supabase Auth | sign-in events (auth audit log; provider records request metadata) | Supabase project logs | 1-day log retention on the Free plan [provider: supabase.com/docs, 2026-08-20] |
| Sentry ingest | event source IP transiently; **not attached to events** (`sendDefaultPii: false` both runtimes) [repo] | — | — |
| PostHog ingest | client IP observed at ingest and used for GeoIP enrichment by default; browser/OS properties attached by the SDK's default properties | PostHog project (US cloud) | ~1 year event retention on the Free plan [provider: posthog.com docs/pricing, 2026-08-20] |

Customer-facing copy must therefore say "our hosting and telemetry
providers process IP addresses as part of operating the service" —
not "we do not collect IP addresses."

## 7. Files on disk (uploads, outputs, config)

| Artifact | Path (env-configured) | Behavior [repo: `api/routers/inventory_sync.py`, `reports/`] |
|---|---|---|
| `/validate` uploads | `LOTSYNC_API_UPLOADS_DIR/validate-*` | **Deleted before the response returns** (test-pinned) |
| `/run` uploads | `LOTSYNC_API_UPLOADS_DIR/<timestamp>/<slot>.csv` | **Bounded retention (D4 implemented + DEV-verified 2026-08-25; NOT production-activated)** — each request end stamps an `outcome.json` marker and an opportunistic sweep at `/run`/`/validate` deletes batches past their ratified window: accepted 7 days, rejected/unacknowledged-warning 30 days, unmarked (legacy or crash) conservatively 30 days [repo: `api/upload_retention.py`, test-pinned]. `UPLOAD_RETENTION_SWEEP=disabled` = operator kill-switch. **Production runs the pre-remediation indefinite-retention build until the v1.1 release train**; its accumulated legacy directories are pruned only at the release/operator gate (`DATA_RETENTION.md` §3). DEV Render free tier = ephemeral filesystem (lost on redeploy) |
| Generated report CSVs | `LOTSYNC_OUT_DIR/*.csv` | Fixed filenames **overwritten each sync** — only the latest survives |
| Work-order PDF | — | Built in memory (`io.BytesIO`) and returned; **never written to disk** |
| Business config | `LOTSYNC_CONFIG_PATH` (`oms_config.xlsx`) | Operator-maintained bucket/threshold config + store name — no personal data |
| CLI-era uploads | `LOTSYNC_UPLOADS_DIR` (`/var/data/uploads` in prod) | Pre-API operator workflow folder; current contents on the production disk are unverified from the repo — inventory at next operator session [decision needed — see `DATA_RETENTION.md`] |

The raw-upload indefinite retention was the sprint's main retention
finding — current behavior, business rationale, risk, and the
ratified bounded policy are in [`DATA_RETENTION.md`](DATA_RETENTION.md)
§3 (**D4 ratified 2026-08-21: raw uploads are temporary operational
evidence — 7-day accepted / 30-day rejected-or-HOLD bounded
retention with deletion is the v1.1 policy**; **no deletion behavior
was changed in Sprint 15**; **implemented 2026-08-25** as the
dedicated bounded-retention remediation — the legacy production
prune still waits for its production release/operator gate).

## 8. Backups and operator-held copies

- **Production SQLite**: manual, verified online-backup procedure;
  copies on the Render disk (`/var/data/backups/`) and the operator
  machine (`C:\Users\demon\LotSync-Backups\`); SHA-256-verified; no
  automated schedule yet [repo: `PRODUCTION_BASELINE.md`]. These
  contain real dealership operational data and inherit the owner's
  machine/account security.
- **DEV Supabase**: Free plan — **no provider-managed backups**
  [provider: supabase.com/docs/guides/platform/backups, 2026-08-20];
  acceptable because the dataset is synthetic and reseedable
  [decision: recorded in `DEV_ENVIRONMENT.md`].
- **Migration artifacts**: the rehearsal dataset is synthetic
  (generated, seed 20260816); the future cutover's final backup and
  the migration-epoch artifact carry real data with retention
  decisions already governed in `PRODUCTION_MIGRATION_PLAN.md`
  (§17–§18: legacy file deleted ~day 90 with owner approval G9;
  off-host backups kept ≥ 1 year; epoch artifact retained).
- **v1.1 production target**: adopting an appropriate paid Supabase
  tier is the migration plan's recorded direction (§22 register) —
  a privacy-relevant reason to fund it: real workforce/vehicle data
  deserves provider-managed backup + restore. Per owner **D10**
  (2026-08-20): a production/commercial-readiness decision, not a
  compliance claim — verify the tier's actual backup/retention
  benefits before relying on them in any published language; no
  benefit is claimed until the plan/configuration is confirmed.

## 9. Future integration boundary (Sprint 17 — documented, not current)

The planned Keyper scheduled-delivery path
(`KEYPER_AUTOMATED_INTEGRATION_PLAN.md`) will add, for the first
time: an inbound-email provider (new subprocessor), message metadata
(sender/recipient/message-ID), attachment fingerprints and retry/
dead-letter state, and — via the extended Keyper contract —
**structured workforce fields** (`User`, `Issue Comment`,
`User Description`: who holds a key, checkout/return actors,
department context). Privacy requirements already governed there:
§8 (no email bodies/attachments/transport headers/VINs/Keyper
comments in telemetry; configured IDs and fingerprints only) and §12
(a targeted Rail L amendment — provider-as-subprocessor, message/
attachment retention, Keyper user-context handling, policy-text
deltas — is a named verification dependency). `V1_1_RELEASE_READINESS.md`
§5.L carries the matching delta rule: **Rail L evidence cannot be
treated as final while the acquisition path is missing from it.**

Purpose grounding for the future workforce fields, recorded now: key
custody accountability is the dealership's real operational need
(who has the key for the vehicle a task concerns). That purpose
justifies ingesting the checkout user's name; it does not justify
inference about conduct (the plan already forbids treating
`Removal Type: Illegal` as a misconduct verdict).

## 10. Incident response — privacy link (internal-beta procedure)

Proportional to a single-operator beta; this section is the
"who does what when telemetry alarms" procedure Rail L exit 2
requires, connecting `OBSERVABILITY.md` §8 (detection) to privacy
duties. Responsible owner for every step: **the product owner
(Kennett Ho)** — there is no one else with access.

1. **Detect / triage** — Sentry alert or log review per the
   `OBSERVABILITY.md` §8 alert-condition inventory. Classify: is
   this an availability bug, a security event, or a suspected
   exposure of personal or dealership data?
2. **Scope from evidence** — correlate with `X-Request-ID` across
   structured logs / Sentry / SyncRun rows; establish which data
   categories (§2) and which environment (prod vs DEV) are involved.
3. **Preserve evidence** — do not reseed, rotate, redeploy, or
   delete logs/uploads for the affected window until scoped; export
   relevant provider logs before their short retention windows lapse
   (Render 7d, Supabase free 1d — §6).
4. **Contain** — provider-appropriate action (rotate the affected
   secret, deactivate the affected membership, suspend the service)
   using the documented inventories (`AUTH_ARCHITECTURE.md` secrets
   table; `SECURITY_ARCHITECTURE.md` §7).
5. **Coordinate providers** — Supabase/Render/Vercel/Sentry/PostHog
   support+status channels as relevant; GitHub for repo events.
6. **Assess notification duties case-specifically.** No statutory
   timeline is pre-promised in any DealerDOH document. The likely
   frame for current scope is Arizona's breach-notification statute
   (A.R.S. §§ 18-551/18-552: "personal information" includes
   name+specified-elements and email/username+password pairs;
   45 days to notify affected individuals after determination;
   >1,000 individuals adds the AG, AZ DHS, and the three CRAs)
   [legal research: azleg.gov, 2026-08-20 — see
   `LEGAL_READINESS.md` §3]. Whether a given event *is* a
   notifiable breach of *whose* data is a case-specific legal
   assessment — counsel involvement recommended at that moment.
7. **Record** — a dated incident record in the repository (what,
   scope, evidence, actions, disposition), same discipline as the
   sprint records.

A full commercial incident-response program (on-call, tabletops,
customer notification contracts) is a v2 prerequisite, recorded in
`LEGAL_READINESS.md` §6 — not faked here.

## 11. Data minimization review (Sprint 15 pass)

Fields audited against "do we actually need this?":

| Field | Verdict |
|---|---|
| Email (Supabase Auth) | Needed — sign-in identity + invite/recovery delivery |
| Display name (user_metadata) | Useful — roster/UI attribution; self-set; clamped; never in telemetry |
| Role/org/store (membership) | Needed — authorization |
| VIN / stock number | Needed — the product's operational subject (vehicle identity) |
| Vendor free-text (`recon_note` etc.) | Kept deliberately — operational evidence (F2 Accepted); never in telemetry; revisit if ever exported/rendered as markup |
| Telemetry identity | Already minimal — internal UUID only |
| PostHog persistence **cookie** | **Not needed** — removed in Sprint 15 (`persistence: 'localStorage'`); identity persistence continues in localStorage with zero functional loss |
| `employee` table | Empty, no write path — schema reserved; collects nothing |
| IP/device in app records | Not collected by the app (platform layer only, §6) |

No other collected-but-purposeless field was found. Collection is
already narrow because the product was built evidence-first; the
main minimization work left is **time-bounding** what is kept
(retention — `DATA_RETENTION.md`), not narrowing what is collected.

## 12. Related documents

- [`DATA_RETENTION.md`](DATA_RETENTION.md) — current behavior vs
  proposed policy vs future requirements, per artifact.
- [`LEGAL_READINESS.md`](LEGAL_READINESS.md) — point-in-time legal
  applicability assessment, owner decision register, counsel
  register.
- Draft customer-facing set (all **Draft — Owner Review Required**):
  [`PRIVACY_POLICY.md`](PRIVACY_POLICY.md),
  [`BETA_TERMS.md`](BETA_TERMS.md),
  [`ACCESSIBILITY_STATEMENT.md`](ACCESSIBILITY_STATEMENT.md),
  [`SECURITY_OVERVIEW.md`](SECURITY_OVERVIEW.md),
  [`SUBPROCESSORS.md`](SUBPROCESSORS.md).
- Enduring neighbors: `SECURITY_ARCHITECTURE.md`,
  `OBSERVABILITY.md`, `AUTH_ARCHITECTURE.md`,
  `ACCOUNT_LIFECYCLE.md`, `INGESTION_ARCHITECTURE.md`.
