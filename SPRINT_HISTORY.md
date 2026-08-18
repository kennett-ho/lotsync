# DealerDOH — Rolling Sprint History & Release Readiness

**Document Version:** 0.2  
**Last Updated:** August 16, 2026  
**Status:** Living Document  
**Repository File:** `SPRINT_HISTORY.md`

---

# Purpose

This document is the canonical chronological engineering, product-development, decision-memory, and release-readiness record for DealerDOH.

It intentionally serves four purposes at once: historical record, current-state snapshot, architectural decision memory, and forward release-readiness register.

It exists to answer:

- What did each sprint set out to accomplish?
- What actually changed?
- What architectural and product decisions were made?
- What was tested?
- What risks or defects were discovered?
- What happened to production?
- What did each sprint unlock for the next one?
- What is still planned for the next production release?

This document should be updated after every completed sprint and merged PR.

Do not rewrite history when architecture changes later. Record what was true at the time and add the newer state chronologically.

---

# Executive Current State at a Glance

| Area | Current State |
|---|---|
| **Production product** | LotSync |
| **Production release** | `v1.0.0-beta.6` |
| **Production branch / commit** | `master` / `13c4f8153561402ef40116d9148c047a8463fe25` |
| **Production persistence** | SQLite on Render persistent disk |
| **Production Auth** | Disabled / not yet rolled out |
| **Development product** | DealerDOH |
| **Development branch / current head** | `dev` / `b389072` (PR #14 merged — Sprint 10 ingestion boundary) |
| **Development persistence** | Supabase PostgreSQL |
| **Development Auth** | Supabase Auth + FastAPI server-side authorization (`AUTH_MODE=required`) |
| **Current backend regression baseline** | 548/548 SQLite and 548/548 PostgreSQL (CI green on merged `dev` = `b389072`) |
| **Standing DEV QA dataset** | 34 vehicles, 18 tasks, 2 recommendations, 98 events, 10 sync runs |
| **Latest completed sprint** | Sprint 09 — Account Lifecycle, Recovery & Functional Settings (Rail A Verified) |
| **Migration readiness** | Technical rehearsal PASS / GO; real production cutover intentionally unscheduled |
| **Current release target** | `v1.1.0-beta.1` |
| **Open PRs** | tracked per sprint; see Git/PR records in each entry |
| **Public domain** | `dealerdoh.com` owned; production domain cutover not yet performed |
| **Immediate focus** | Sprint 10 MERGED (`b389072`); sprint state: **Implementation Paused — Awaiting Vendor Evidence** (Keyper Event contract, §6.2 discovery); Rail D NOT Verified. Closeout in progress: DEV services back to `dev` (owner), reseed + membership re-provision, health verification. Sprint 11 not begun (owner directive). |

**Production rule:** `master` is what real dealership users are allowed to depend on. Normal development belongs on task branches and `dev`; production remains frozen until an explicit release train is approved.

---

# Current Product Identity

## Original Product

**LotSync**

LotSync began as a dealership inventory and lot-operations platform built around reconciling disconnected systems used at Mark Kia.

Core integrations/data sources include:

- Tekion
- Keyper
- RecovR
- RapidRecon
- MDD

Core operational concepts:

- **Vehicle** — central entity
- **Event** — factual observation/history
- **Task** — actionable committed work
- **Recommendation** — evidence/pattern surfaced for human judgment

Supporting concepts include:

- SyncRun
- PendingIdentity
- Employee/User

## New Product Identity

**DealerDOH**

**Dealer Digital Operations Hub**

DealerDOH is the planned evolution of LotSync from a lot/inventory-specific operational tool into a broader dealership operations platform.

The public domain `dealerdoh.com` is owned.

## Core Product Doctrine

The following decisions are foundational and should survive individual screen or infrastructure changes:

- **Vehicle is the central operational entity.**
- **Systems provide evidence/context; DealerDOH correlates and explains that evidence.**
- **Events are factual observations/history; Tasks are committed work; Recommendations surface evidence for human judgment.**
- **Humans retain subjective dealership decisions.** DealerDOH should not become an AI operations manager or silently replace dealership judgment.
- **Missing evidence is not zero.** A missing vendor source must never be interpreted as proof that no records exist.
- **Invalid evidence is not valid zero.** An empty, incomplete, wrong-type, or malformed vendor report must fail closed rather than generate destructive operational conclusions.
- **Preserve the workflow need, not unnecessary UI.** A screen can change while the operational need survives.
- **Lot Staff remain the primary operational users of the original inventory workflow.** Managers and other departments contribute or receive role-aware surfaces according to real workflow needs.

---

# Current Release State

## Production

**Product:** LotSync  
**Version:** `v1.0.0-beta.6`  
**Branch:** `master`  
**Commit:** `13c4f8153561402ef40116d9148c047a8463fe25`

Production remains actively used by dealership personnel.

### Production Architecture

```text
Vercel
LotSync frontend
    ↓
Render
FastAPI
    ↓
SQLite
Render persistent disk
```

Production currently has:

- SQLite persistence
- no production authentication
- original LotSync branding
- real dealership data

Production has remained intentionally frozen while DealerDOH development proceeds independently.

---

# Development

**Branch:** `dev`  
**Current recorded head:** `51d59f9`

Current architecture:

```text
Vercel
DealerDOH DEV frontend
    ↓
Supabase Auth
    ↓
Render FastAPI DEV
    ↓
Supabase PostgreSQL
```

DealerDOH DEV includes:

- isolated frontend
- isolated API
- isolated PostgreSQL database
- Supabase Auth
- deterministic QA dealership
- server-side authorization
- SQLite + PostgreSQL CI
- development smoke testing
- release-process automation

---

# Release Philosophy

Normal DealerDOH development follows:

```text
feature/* / fix/* / chore/*
        ↓
        PR
        ↓
       dev
        ↓
deployed DEV environment
        ↓
smoke / QA
        ↓
release readiness
        ↓
release train
        ↓
      master
        ↓
production
```

`master` represents what production users are allowed to depend on.

Normal development does not occur directly on `master`.

---

# Canonical Decision Register

These are current decisions, not brainstorms. Future sprints should treat them as governing constraints unless a later explicit decision supersedes them.

| Decision | Current Position | Why / Trigger for Revisit |
|---|---|---|
| **Production branch** | `master` = production | Existing Render/Vercel production wiring. Rename only in a deliberate release/infrastructure change. |
| **Integration branch** | `dev` = next integrated release | All normal work enters through task branch → PR → `dev`. |
| **Public signup** | Disabled | DealerDOH accounts are created/invited by an authorized manager/admin. |
| **Role presentation** | One application with role-aware Manager vs Lot Staff presentation | Avoid fake role switching/separate apps. Truly different departments may later receive distinct operational surfaces when workflows justify it. |
| **Authorization boundary** | FastAPI | Sensitive dealership data is accessed through server-side business logic; the browser does not directly query protected tables. |
| **RLS** | Deferred defense-in-depth | Reassess when browser access to sensitive Supabase data begins or richer multi-store tenancy requires a second DB-layer boundary. |
| **Store scoping** | Explicit serving-dealership membership in FastAPI | Full per-row store scoping becomes mandatory before Store #2 goes live. |
| **Production migration risk** | Database, Auth, and branding are separate release risks | Keep Release A/B/C/D independently reversible where practical. |
| **Evidence handling** | Missing evidence ≠ zero | Prevent source outages/missing reports from generating false state. |
| **Ingestion safety** | Invalid evidence ≠ valid zero | Empty/incomplete/wrong report types must be rejected before state mutation. |
| **Future ingestion channels** | Manual upload, scheduled email, and vendor API must converge on the same classifier/validator | Prevent automated ingestion from bypassing the safeguards added for manual upload. |
| **Notifications v1** | In-app first | SMS/push/Slack/digests remain deferred unless a concrete operational need appears. |
| **Observability** | Sentry + PostHog planned, with deliberate redaction/privacy rules | Error telemetry and product analytics serve different purposes and should not receive secrets/raw sensitive reports. |
| **Real user validation** | Human UAT is required before production cutover | AI/browser smoke tests cannot substitute for a manager and lot attendant using the product uncoached. |

---

# Known Active Findings & Technical Debt Register

| Finding / Debt | Status | Required Before | Notes / Trigger |
|---|---|---|---|
| Sold vehicles have no normal browse path | **Open — planned Sprint 12** | Non-blocking unless Manager UAT or a required workflow demonstrates otherwise (owner decision 2026-08-16) | API/history supports sold vehicles; UI discovery path remains missing. |
| Sidebar navigation can leave Vehicle Detail open | **Open — planned Sprint 12** | Non-blocking unless UAT demonstrates otherwise (owner decision 2026-08-16) | State-navigation UX issue surfaced by QA dataset. |
| SPA deep links can 404 on Vercel | **Open — REQUIRED, Sprint 09 (Rail A)** | v1.1 (owner decision 2026-08-16: recovery/password-reset links may depend on direct routing) | App is currently state-based rather than fully URL-routed/rewrite-safe. |
| Admin and Manager are currently mostly equivalent | **Accepted / Deferred** | User-management maturity | Intentional minimal role model; diverge only when justified capabilities exist. |
| Full per-row store scoping | **Deferred / Triggered before Store #2** | Second real store | Current single-serving-store membership boundary is proven, but multi-store rows need explicit scoping. |
| Legacy HS256 Supabase key retirement | **Open operator hardening item** | Security-hardening / production Auth readiness | DealerDOH verifier already pins ES256; confirm legacy anon/service-role key dependencies before retirement. |
| Historical `CHANGELOG.md` backfill | **Open** | Nice-to-have before v1.1 archive/freeze | Existing changelog historically stopped at v0.7.4 while later releases live in tags/history. |
| Automatic-ingestion vendor research | **Active / Conditional** | Before automated ingestion implementation | Verify actual Tekion/Keyper/RecovR/RapidRecon/MDD mechanisms this week. |
| Privacy/legal production documents | **Planned** | Broader commercial rollout / release-readiness assessment | Data inventory must precede accurate Privacy Policy, Accessibility Statement, security/subprocessor disclosures, etc. |
| Render persistent disk after Postgres | **Operational constraint, not removable yet** | Production cost optimization | The disk also supports `oms_config.xlsx`, upload staging, and generated report/output workflows; PostgreSQL migration alone does not make it disposable. |

---

# Development Eras

The numbered DealerDOH production-maturity sprints below are **not the beginning of the project**. LotSync already had substantial product, backend, frontend, and deployment work before production was locked. This document preserves those earlier efforts as eras rather than renumbering historical phase/sprint schemes. Exact historical sprint numbering should remain in the original roadmap/docs/tags where it was used.

## Era I — Operational Problem Discovery & Prototype

LotSync originated from real dealership operations work at Mark Kia. The initial problem was not "build dealership SaaS"; it was reconciling operational truth scattered across multiple systems. Early work included:

- comparing Tekion inventory state with Keyper, RecovR, MDD, and RapidRecon evidence;
- building a master reconciliation workflow from exports/spreadsheets;
- identifying practical rules around sold vehicles, checked-out keys, tracking devices, recon state, and stale system evidence;
- shifting from ad hoc spreadsheet analysis toward a vehicle-centered operational system.

**What this era established:** the domain knowledge and operational pain that later became the product's business rules.

## Era II — Backend Foundation & Persistent Operational Model

The backend evolved into a Python/FastAPI/SQLite application with migrations and raw SQL. Historical work in this era established the durable domain model and core reconciliation pipeline, including:

- vehicle-centered persistence;
- source import/persistence across dealership systems;
- SyncRun provenance/history;
- event history/freshness;
- task generation;
- recommendations;
- dashboard/read-model queries;
- regression tests around reconciliation behavior.

Historical architectural milestones later reflected in the repository include `v0.7.1` architecture/developer-tooling stabilization, `v0.7.2` vehicle display-name improvements, and `v0.7.3` Event Fidelity.

**What this era established:** a persistent operational engine instead of a one-off reconciliation script.

## Era III — Product Alignment & Operational MVP

By the `v0.7.4` Product Alignment milestone and subsequent `v0.8.x` work, the system's product identity became clearer:

- Lot Staff were established as the primary operational users of the original product;
- the product grammar centered Vehicle / Event / Task / Recommendation;
- task lifecycle and operational wording were refined;
- RecovR, Keyper, MDD, sold/active inventory, and missing-source behavior were aligned with dealership reality;
- dashboard Tasks became grouped operational work rather than raw rule-engine output;
- responsive/mobile field usability became part of the product.

**What this era established:** LotSync as an operational product with governed semantics, not merely data reconciliation.

## Era IV — Deployment Beta & Real-World Validation

The `v0.9.x` → `v1.0.0-beta.x` period established the live beta and corrected issues that only surfaced in production-like operation. This era included:

- Vercel frontend deployment;
- Render FastAPI deployment;
- SQLite persistence on a Render disk;
- `/health`;
- CORS configuration;
- upload-path security hardening;
- production report-output directory fixes;
- Inventory Sync scrolling/field usability fixes;
- printable Daily Work Order PDF (`v1.0.0-beta.6`);
- real manager use of Inventory Sync after the developer left the dealership.

**What this era established:** the product could be used independently by real dealership personnel, which is why the next era begins by formally locking production.

---

# Era V — DealerDOH Production-Maturity Program

This era begins once the working LotSync beta is treated as real production and DealerDOH development is separated behind a governed dev → production release train.

# Sprint 01 — Production Baseline & Git Foundation

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Stop treating the existing LotSync deployment as a development playground and formally establish it as a production system.

The sprint needed to determine exactly what was currently deployed before any environment restructuring occurred.

## Starting State

LotSync was publicly deployed and functioning, but development and production were not yet governed by a formal release train.

The assumed release was `v1.0.0-beta.6`, but this needed verification rather than assumption.

## Major Work

Fable performed a full repository and deployment audit.

Verified:

- repository structure
- Git history
- Git tags
- production branch
- backend tests
- frontend build
- database location
- schema migration state
- production API
- production deployment relationship

### Important Discovery

The repository uses:

`master`

not:

`main`

This became a permanent process consideration because both Render and Vercel production deployments were connected to `master`.

## Verified Production Baseline

- Version: `v1.0.0-beta.6`
- Production commit: `13c4f8153561402ef40116d9148c047a8463fe25`
- Backend tests: **385/385 passing**
- Frontend build: passing
- Database: `/var/data/lotsync.db`
- Render persistent disk: `lotsync-data`
- Schema migration: `0008_event_fidelity.sql`

## Documentation

Created:

- `PRODUCTION_BASELINE.md`

Updated:

- `PROJECT_STATUS.md`
- `DEPLOYMENT.md`

## Git Foundation

Created:

`dev`

directly from the verified production state.

Initial documentation commit on `dev`:

`7348aec`

## Important Findings

- `PROJECT_STATUS.md` was stale.
- `CHANGELOG.md` stopped at `v0.7.4`.
- Production frontend URL was undocumented.
- No CI existed.
- No verified off-host production database backup existed.
- A push to `master` automatically triggered production deployment.

## Production Impact

No product behavior was intentionally changed. Production was inspected and documented, then treated as the locked reference point. Normal development moved away from production.

## Result

LotSync production became formally:

**STABLE / LOCKED**

Normal development moved to `dev`.

## What This Enabled Next

A safe baseline from which backups, CI, dev infrastructure, and all later DealerDOH work could proceed without ambiguity about what production actually was.

---

# Sprint 01.5 — Backup & CI Foundation

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Close the most immediate operational risks identified in Sprint 01:

1. no verified production backup
2. no automated CI gate

## Production Backup

A safe SQLite online backup was created from the live Render database using SQLite's backup mechanism rather than blindly copying the active file.

Verified backup:

- integrity check: `ok`
- database size: `4,210,688 bytes`
- schema migration: `8`
- vehicle count at backup time: `4,672`

SHA-256:

`7111f1176d420b984a3e7fdcd0d217e15897e4c0b951204ea5e4f5fedc7f226c`

A verified off-Render copy was downloaded locally.

Production remained healthy after backup.

## CI

GitHub Actions was introduced.

Initial gates:

### Backend

- Python environment
- complete backend test suite

### Frontend

- clean dependency installation
- Vite production build

CI contained:

- no deployment steps
- no production secrets
- no production DB access

## Dependency Finding

An existing `nanoid` advisory was discovered and classified rather than blindly upgraded.

It was determined to be:

- transitive
- build-time/dev-only
- not present in the production bundle's vulnerable path

The dependency was not changed as part of this infrastructure sprint.

## PR

**PR #1**

Task commit:

`32e6f90`

Merged into `dev`.

Merge commit:

`aed153d`

## Production Impact

The production database was read through SQLite's safe online-backup mechanism and remained healthy. CI had no deployment step and no production DB access.

## Result

DealerDOH development gained:

- verified recovery evidence
- automatic test/build gates
- a safer integration branch

## What This Enabled Next

Infrastructure work could become more autonomous because every PR now had a repeatable test/build gate and production had a verified recovery artifact.

---

# Process Milestone — DealerDOH Agent Development Procedures

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

This occurred between Sprint 01.5 and Sprint 02.

## Objective

Encode the development process itself so Fable/Claude/Codex would follow a repeatable DealerDOH engineering procedure rather than relying on long one-off prompts.

The process was inspired by development skills used successfully inside Wise Pelican.

## Added Commands

DealerDOH gained commands/workflows including:

- `/start-task`
- `/pr`
- `/review-comments`
- `/merge-dev`
- `/release-readiness`
- `/release-train`
- `/smoke-test`
- `/production-smoke`
- `/data-migration`
- `/handoff-report`

## Repo-Specific Corrections

The imported procedure was adapted to DealerDOH reality:

- production branch is `master`
- `master` auto-deploys
- `dev` is the integration branch
- production release requires explicit approval
- normal smoke tests never target production
- migration workflows default to non-production
- real repo test/build commands replaced generic placeholders

## PR

**PR #2**

Reviewed commit:

`15c28cc`

Merge commit:

`dac6088e`

## Production Impact

None. The change was process/documentation only and explicitly taught agents that production release actions require separate approval.

## Result

DealerDOH's development methodology became version-controlled institutional knowledge.

The task prompt now describes **what** to build.

DealerDOH process skills describe **how** the work must be performed.

## What This Enabled Next

Future Fable/Claude/Codex work could follow a durable task → PR → merge → smoke → release procedure without re-explaining every safety rule in every sprint.

---

# Sprint 02 — DealerDOH Development Environment Foundation

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Create somewhere safe to build and break DealerDOH without affecting the dealership using LotSync.

## Development Infrastructure Created

### Supabase DEV

Project:

`dealerdoh-dev`

Region:

`us-west-2`

Used initially for:

- PostgreSQL foundation
- Auth foundation

### Render DEV

Service:

`dealerdoh-api-dev`

URL:

`https://dealerdoh-api-dev.onrender.com`

Configuration:

- Render Free
- no persistent disk
- isolated environment variables
- development health endpoint
- disposable SQLite during the initial sprint

### Vercel DEV

Project:

`dealerdoh-dev`

URL:

`https://dealerdoh-dev.vercel.app`

## Development Indicator

A visible purple:

**DealerDOH DEV — Synthetic/Test Data Only**

banner was added so development could never be confused with production.

## Synthetic Seed Foundation

A disposable deterministic seed process was introduced.

The initial DEV dataset contained:

- 17 synthetic vehicles
- 3 open tasks
- 5 sync runs

## Isolation Proof

Verified:

- DEV frontend calls DEV API only.
- DEV API cannot access the production disk.
- DEV contains no production dealership records.
- Production API rejects DEV origin.
- DEV API rejects production origin.
- DEV credentials and production credentials are separated.

## Tests

Backend increased to:

**390/390 passing**

Frontend build remained green.

## Smoke Testing

Verified live:

- Dashboard
- Vehicles
- Vehicle Detail
- Tasks
- Inventory Sync
- work-order PDF
- console

## PR

**PR #3**

Implementation commits:

- `691675a`
- `3c20fd4`

Merge commit:

`610763b`

## Follow-Up Documentation PR

Sprint branch references inside `DEV_ENVIRONMENT.md` became stale after the merge.

Rather than pushing directly to `dev`, the fix used the normal PR process.

**PR #4**

Commit:

`b1b4594`

Merge commit:

`ea50df30`

## Production Impact

None. `master`, the production Render service, the production Vercel project, the production SQLite DB, and production credentials remained untouched.

## Result

DealerDOH gained a persistent integrated development environment completely separated from production.

## What This Enabled Next

Invasive architecture work—especially the SQLite → PostgreSQL migration—could be performed against a real deployed stack without risking the dealership.

---

# Sprint 03 — DEV SQLite → Supabase PostgreSQL Migration

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Replace disposable DEV SQLite persistence with Supabase PostgreSQL without changing DealerDOH business behavior.

Production remained on SQLite.

## Dual-Engine Architecture

DealerDOH gained support for:

```text
DATABASE_ENGINE=sqlite
```

and:

```text
DATABASE_ENGINE=postgres
```

## PostgreSQL Work

Added:

- psycopg
- PostgreSQL connection pooling
- engine dispatch
- PostgreSQL migrations
- portable SQL behavior

Major compatibility changes included:

- SQLite `?` placeholders → PostgreSQL-compatible parameters
- `lastrowid` → `RETURNING`
- `INSERT OR IGNORE` → `ON CONFLICT`
- type normalization
- sync-run ID compatibility
- PostgreSQL-safe sold filtering
- connection lifecycle/pooling
- PostgreSQL test schemas

All eight existing migrations were ported.

## CI

CI began running the behavioral suite against:

- SQLite
- PostgreSQL

## Cross-Engine Verification

Sprint-specific test baseline:

**402/402 SQLite**

**402/402 PostgreSQL**

Synthetic fixtures were run through both engines.

Results included:

- identical counts
- all eight generated CSV reports byte-identical
- important business projections row-for-row identical

## Supabase DEV Cutover

DealerDOH DEV was connected to Supabase using the session pooler.

DEV data survived Render redeploys/restarts, proving persistence had moved out of Render's ephemeral filesystem.

`/health` began reporting:

- environment: development
- database engine: postgres

## Credential Hygiene

A DEV DB password appeared once in a development-session screenshot.

The password was subsequently rotated.

Render's `DATABASE_URL` was updated.

Post-rotation verification confirmed:

- health green
- original dataset still present
- no reseed
- no DB connection errors
- new credentials functioning
- plaintext temporary DSN file deleted

## PR

**PR #5**

Sprint commits:

- `558cc93`
- `eb1702b`
- `e1dc8d1`

Merge commit:

`6bf862f`

## Production Impact

None. Production continued using the existing SQLite path. The dual-engine design intentionally kept SQLite as the safe/default compatibility path while DEV switched to PostgreSQL.

## Result

DealerDOH DEV moved to the intended future database architecture while production remained untouched on SQLite.

## What This Enabled Next

DEV gained durable persistence and a realistic future production DB architecture, making richer QA state, auth, and later migration rehearsal possible.

---

# Sprint 04 — Deterministic Synthetic QA Dealership

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Turn DEV from "some fake data" into a deliberately engineered dealership regression environment.

## QA Matrix

Created:

- **17 scenario families**
- **37 concrete scenarios**
- **34 synthetic vehicles**

Additional identity-only records supported pending-identity testing.

## Standing Expected State

- 34 vehicles
- 28 active
- 6 sold
- 18 tasks
  - 16 outstanding
  - 1 honored
  - 1 moot
- 2 recommendations
- 98 events
- 10 sync runs
- 3 pending identities
  - 1 resolved

## Scenario Coverage

The QA dealership explicitly tests:

### Baseline

- active vehicle requiring no work

### RecovR

- install required
- blocked by checked-out key
- RecovR present with independent key issue

### Keyper

Deterministic aging cases:

- 0 days
- 1 day
- 3 days
- 7 days
- 14 days
- 25 days
- 30 days

### Exclusions

- Wholesale
- At Auction

### RapidRecon

- Archive as context, not automatic exclusion

### Sold Inventory

- default active exclusion
- historical preservation
- moot work behavior

### MDD

- missing beacon work

### Multiple Tasks

- legitimate multiple open tasks on one vehicle

### Conflicting Evidence

- preserved ambiguity
- governed conflict behavior

### Missing Source

- missing evidence cannot be treated as zero

### Events

- deduplication
- freshness
- authoritative event times
- chronology

### Task Lifecycle

- outstanding
- honored
- moot

### Pending Identity

- ambiguous evidence
- resolution/promotion path

## Determinism

The seed uses fixed reference dates so aging outcomes do not drift with the calendar.

Expected outcomes are asserted by scenario, not merely global totals.

## Testing

Sprint-specific baseline:

**428/428 SQLite**

**428/428 PostgreSQL**

The QA assertions run in both engines.

## Live DEV Verification

Verified:

- Dashboard grouping
- Inventory Health
- Vehicles
- Vehicle Detail
- Timeline
- Tasks
- closed-task labels
- work-order PDF

## Product Findings Exposed

The richer dataset revealed three pre-existing UI issues:

1. Sold vehicles have no normal UI browse path.
2. Sidebar navigation does not dismiss an open Vehicle Detail state.
3. SPA deep links can 404 because URL routing/rewrites are incomplete.

These were documented, not silently absorbed into the sprint.

## PR

**PR #6**

Task commit:

`e2ed776`

Merge commit:

`e25e498`

## Production Impact

None. Only synthetic DEV fixtures and assertions changed; no production data was copied or mutated.

## Result

DealerDOH DEV became a standing automated QA dealership instead of a simple demo environment.

## What This Enabled Next

Authentication, authorization, UX changes, and later release features could be validated against a known scenario matrix rather than arbitrary fake data.

---

# Sprint 05 — Supabase Auth, Users, Roles & Store Boundaries

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Introduce real authentication and server-enforced dealership authorization in DEV.

Production remained unauthenticated.

## Authentication

Supabase Auth integrated using:

- email/password
- Supabase-issued JWT
- ES256
- project JWKS

FastAPI verifies:

- cryptographic signature
- expected algorithm
- issuer
- audience
- expiry
- trusted key

Rejected conditions include:

- invalid token
- expired token
- incorrect issuer
- incorrect audience
- unknown signing key
- unsigned/`alg=none` token

## AUTH_MODE

Default:

`AUTH_MODE=disabled`

DealerDOH DEV:

`AUTH_MODE=required`

This allowed production to remain behaviorally unchanged while DEV gained real authentication.

## Access Model

Migration `0009` introduced:

```text
organization
    ↓
dealership
    ↓
user_membership
```

The existing governed `dealership` entity was reused rather than inventing a duplicate Store table.

Membership stores:

- Supabase Auth user ID
- organization
- dealership
- role
- active state

## Roles

Current roles:

- admin
- manager
- lot_staff
- sales_manager

Role is resolved from the server-side membership table.

Client-supplied role data is not trusted.

## Initial Role Gate

Inventory Sync execution:

Allowed:

- admin
- manager

Denied:

- lot_staff
- sales_manager

## Store Boundary

DealerDOH DEV serves:

`qa-motors`

Membership must match the serving dealership.

A synthetic Store-B-only user was used to prove cross-store denial.

## Synthetic DEV Accounts

Development-only synthetic users were provisioned for:

- admin
- manager
- lot staff
- sales manager
- Store-B outsider

No real Mark Kia employee identities were used.

Public signup was disabled.

## Frontend

Added:

- login gate
- real Supabase session
- Bearer token attachment
- `/me`
- authenticated identity display
- role display
- dealership display
- sign out

Refresh preserves the session.

## Security Testing

Added 25+ auth/authorization tests.

Sprint baseline:

**454/454 SQLite**

**454/454 PostgreSQL**

Proven:

- unauthenticated → 401
- invalid token → 401
- no membership → 403
- inactive membership → 403
- cross-store user → 403
- role spoofing fails
- unknown role constrained
- misconfiguration fails closed

## RLS Decision

Supabase RLS was intentionally deferred.

Reason:

The browser does not directly query sensitive DealerDOH tables.

FastAPI remains the authorization and business-logic boundary.

RLS remains a future defense-in-depth requirement if client database access or richer multi-tenancy is introduced.

## PR

**PR #7**

Implementation commits:

- `c0ac0ed`
- `5446481`

Merge commit:

`a2f6322`

## Production Impact

None. Production remained unauthenticated with `AUTH_MODE=disabled` by default; no real employee accounts or production Supabase/Auth resources were introduced.

## Result

DealerDOH DEV became a real authenticated application with server-enforced membership/store authorization.

## What This Enabled Next

Production migration planning could include a proven Auth path, real role/store boundaries, and realistic login/session smoke testing instead of hypothetical access-control design.

---

# Sprint 06 — Production Migration Planning & Cutover Runbook

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Design the real production migration before touching production.

No migration was executed.

## Production Data Inventory

The verified production backup was inspected read-only.

Production-scale finding:

Approximately:

- **4.02 MiB**
- **14,606 business rows**

The relatively small data size indicated migration time would be dominated by operator verification rather than raw data copy.

## Recommended Strategy

A short controlled maintenance window was selected over shadow migration or dual-write.

Reason:

- only one meaningful production write route
- inventory sync is operator-triggered
- small database
- simpler rollback
- lower split-brain risk

## Release Decomposition

Production transition was split into four release trains.

### Release A — Code Compatibility

Deploy DealerDOH-capable code while keeping:

- SQLite
- Auth disabled
- current behavior

### Release B — Database Cutover

Move production persistence:

SQLite → Supabase PostgreSQL

### Release C — Authentication

Provision users and enable production Auth.

### Release D — Branding/Domain

Move public identity to DealerDOH and the final domain structure.

Database, Auth, and branding are intentionally separate risk classes.

## Migration Plan

Defined:

- write freeze
- final SQLite backup
- migration
- sequence reset
- exact validation
- env cutover
- smoke test
- rollback

## Rollback Boundary

Critical production concept established:

Before the first accepted PostgreSQL production write:

**SQLite rollback can be zero-loss.**

After PostgreSQL accepts new writes:

A raw SQLite rollback may lose new data unless that work is replayed/recovered.

## Render Disk Retention Finding

A critical cost/architecture assumption was corrected during planning: moving the production database to PostgreSQL does **not** immediately make the Render persistent disk disposable. The disk also supports operational files such as `oms_config.xlsx`, upload staging, and generated report/output workflows.

The production migration can retire `lotsync.db` as the authoritative datastore without automatically removing the disk or its cost. Disk retirement requires a separate storage/output migration decision.

## Runbook

Created:

- `PRODUCTION_MIGRATION_PLAN.md`
- `PRODUCTION_MIGRATION_RUNBOOK.md`

## PR

**PR #8**

Task commit:

`3465a62`

Merge commit:

`4f765bc`

## Production Impact

None. The sprint was planning/read-only. No Supabase production project, env changes, production migrations, or release-train execution occurred.

## Result

Production migration became a documented release operation rather than an improvised infrastructure change.

## What This Enabled Next

A full rehearsal could test the exact cutover, validation, rollback, and failure-handling procedure before any real production scheduling.

---

# Sprint 07 — Production Migration Rehearsal & Rollback Drill

**Status:** Complete  
**Date:** TBD — populate from merged PR/commit metadata; do not guess.

## Objective

Execute the production migration procedure against disposable infrastructure and prove both:

1. migration works
2. rollback/recovery works

## Production-Shaped Synthetic Dataset

Generated:

- 4,700 vehicles
- 8,894 events
- 686 event-freshness rows
- 365 tasks
- 3 recommendations
- 3 task-execution events
- 12 sync runs
- 2 pending identities

Total:

**14,665 business rows**

The dataset intentionally reproduced production migration risks including:

- sparse sequences
- non-contiguous IDs
- null-heavy data
- task self-FKs
- recommendation→task relationships
- historical events
- empty access-model tables

## Migration Tool

Added:

`tools/migrate_sqlite_to_postgres.py`

Capabilities include:

- safe SQLite source
- DSN via environment
- dry-run default
- explicit remote destination confirmation
- migration execution
- FK-safe copying
- explicit ID preservation
- sequence reset
- exact count validation
- invariant checks
- representative row comparisons
- JSON reporting
- failure exit codes

## Validation

Structural verification:

- expected tables
- expected indexes
- migrations 1–9
- valid sequences
- valid FKs

Data validation:

- exact table counts
- domain invariants
- representative VIN comparisons
- sync runs
- pending identities

Behavior:

**22/22 behavioral comparisons identical**

including work-order output.

## Timings

Measured local rehearsal:

- backup + verify: ~0.06 sec
- migration + validation: ~0.98 sec
- behavior comparison: ~2.3 sec
- DB cutover → healthy: ~17.8 sec
- Auth cutover → healthy: ~23.9 sec
- smoke testing: ~4 min
- pre-write rollback: ~19.4 sec

Production estimate revised to approximately:

**30 minutes active work**

with a planned:

**90-minute safety window**

## First PostgreSQL Write Simulation

A real synthetic sync write was accepted by PostgreSQL.

The delta was explicitly recorded.

This demonstrated the true rollback boundary.

## Rollback Drill

### Before PostgreSQL Write

Rollback to SQLite succeeded with zero logical data loss.

### After PostgreSQL Write

The PostgreSQL-only delta was identified.

Replaying the same source report against the restored SQLite state converged back to the same logical state, demonstrating a practical recovery path.

## Failure Injection

Tested:

- bad PostgreSQL DSN
- validation mismatch
- interrupted migration
- Auth misconfiguration
- unreachable DB after engine cutover
- confirmation-prompt failure

All were made to fail closed with documented operator actions.

## Tests

Sprint baseline:

**464/464 SQLite**

**464/464 PostgreSQL**

Frontend build passes.

## Verdict

**PASS**

Technical assessment:

The production migration is technically ready to schedule.

It is intentionally **not scheduled** because additional v1.1.0-beta features and rails are planned first.

## PR

**PR #9**

Task commit:

`133fecb`

Merged into `dev`.

Merge commit:

`51d59f9`

## Production Impact

None. Rehearsal used disposable synthetic infrastructure and production-shaped fake data. `master`, production deployments, production SQLite, real users, and DNS remained unchanged.

## Result

The migration rail is proven and can remain parked while v1.1.0-beta feature development continues.

## What This Enabled Next

The technical migration question is no longer the blocker. DealerDOH can spend the next release cycle on product, security, observability, ingestion safety, accessibility, legal readiness, and human UAT before freezing the v1.1 candidate.

---

# Sprint 08 — v1.1.0-beta.1 Scope & Release Readiness Register

**Status:** Complete  
**Date:** 2026-08-16 (merged same day)

## Objective

Turn `v1.1.0-beta.1` from a collection of ideas into a controlled release contract: every proposed capability classified REQUIRED / CONDITIONAL / POST-v1.1, every REQUIRED rail given an owner sprint, purpose, addressed risk, exact exit conditions, required evidence, and a release-blocking status — plus the recommended Sprint 09+ execution order and explicit scope-discipline rules.

## Starting State

- `dev` = `51d59f9` (Sprint 07 merge), `master` locked at `v1.0.0-beta.6` / `13c4f815`
- CI green on the `dev` head; DEV and production endpoints healthy (read-only checks)
- This document was found owner-staged locally but not yet committed — landed in-repo as the sprint's first commit, together with owner-staged reality corrections (stale smoke-test workflow note; `dealerdoh.com` now owned; status pointer)

## Major Work

Created **`V1_1_RELEASE_READINESS.md`** — the authoritative release contract for `v1.1.0-beta.1`:

- Readiness register: 13 rails + the production-migration rail, each with priority, status, planned sprint, blocking status, exit-condition summary, and required evidence
- Full exit criteria for every REQUIRED rail (A Account Lifecycle, B Onboarding/Help, C Role-Aware Presentation, D Ingestion Safety, F Observability, G Structured Logging, H Security Hardening, I Supply Chain, J Performance, K Accessibility blocking subset, L Privacy/Legal internal-beta subset, M Human UAT)
- **Sprint 08 decision:** Notifications classified **CONDITIONAL**, not REQUIRED — v1.1 ingestion is manual-upload-only, so sync outcomes are visible at the point of action; the rail auto-promotes if automated ingestion enters v1.1 or on UAT evidence
- Automated Report Ingestion held CONDITIONAL behind the vendor-discovery checklist (owner action; answers targeted before Sprint 12 planning)
- Scope-discipline rules (five narrow admission criteria after Sprint 08), evidence rules per change class, back-burner trigger register, and the known-findings register with per-item blocking status
- **Recommended order (changed from provisional):** 09 Account → 10 Ingestion Safety → **11 Observability + Logging (moved up from 13)** → 12 Role-Aware UX + Onboarding → (12.5 Notifications only if triggered) → 13 Security + Supply Chain (folded) → 14 Performance + Accessibility → 15 Privacy/Legal → 16 Human UAT → 17 RC Freeze — nine sprints to RC instead of ten

Note: rail letters in `V1_1_RELEASE_READINESS.md` follow the Sprint 08 specification and diverge from this document's older rail catalog from D onward (mapping recorded in the register). **The register is operative**; this document's rails section and readiness-summary table remain historical context.

## Owner Ratification & Scope Adjustment (2026-08-16, pre-merge)

The owner ratified both Sprint 08 decisions (Notifications → CONDITIONAL with automated-ingestion-or-UAT promotion triggers; Observability/Logging ahead of the Role-Aware UX + Onboarding sprint) and made one scope adjustment, applied to the register before merge:

- **SPA deep-link routing → REQUIRED** under Rail A (Sprint 09): account-recovery/password-reset links may depend on direct routing.
- **Sidebar/Vehicle-Detail dismissal:** planned for the Role-Aware UX sprint, **non-blocking unless UAT demonstrates otherwise**.
- **Sold-vehicle browse path:** planned, **non-blocking unless Manager UAT or a required workflow demonstrates it must ship in v1.1**.

## Production Impact

None. Planning/documentation only. No production Supabase, no cutover scheduling, no user or DNS changes.

## PR

**PR #10.** Task commits: `28b6009` (owner-staged history landing), `a5ffaf6` (register), `4e1c232` (ratification). Merge commit: `dddbb5f`. CI green on the merged head (SQLite, PostgreSQL, frontend build; both Vercel preview statuses).

## Result

`v1.1.0-beta.1` has a release contract: scope is classified, exit criteria and evidence rules are explicit, and conditional/deferred work cannot silently grow the release.

## What This Enabled Next

Sprints 09–17 execute against a frozen contract instead of a provisional idea list, starting with Account Lifecycle & Settings.

---

# Sprint 09 — Account Lifecycle, Recovery & Functional Settings

**Status:** Complete  
**Date:** 2026-08-16

## Objective

Rail A: manager/admin-provisioned users (no public signup), real password recovery over direct links, immediate membership-based offboarding, and a Profile & Settings surface containing only real functionality.

## Major Work

- **Backend:** `api/supabase_admin.py` (server-only GoTrue Admin boundary; `SUPABASE_SECRET_KEY` in Render env only, 503 when absent) · `api/routers/users.py` (roster / invite / deactivate / reactivate; role policy admin→all four, manager→lot_staff+sales_manager; dealership always derived from the caller's membership; self-deactivation and last-active-admin guards; 404-entire-surface under `AUTH_MODE=disabled`) · membership repo additions (any-state lookup, roster list, active toggle, admin count) · `AccessContext`/`GET /me` gain `display_name` from verified token `user_metadata`.
- **Recovery & routing:** Forgot Password on login (enumeration-safe generic response) · `/auth/reset-password` page outside the auth gate (invite + recovery landings; invalid/expired links fail safely) · Vercel SPA rewrite (the Sprint 08-ratified Rail A requirement) pinned by `tests/test_frontend_config.py` · post-reset session policy: `updateUser` then global sign-out (all refresh tokens revoked — real, provider-supported revocation).
- **Frontend:** `AccessProvider` (one shared `/me`, account-disabled screen on identity-level 403, global 401→clean sign-out; per-action 403s stay page-level) · honest Profile & Settings rewrite (every prior control was fake — full disposition table in `ACCOUNT_LIFECYCLE.md`) · User Management UI for admin/manager · fake header notification bell removed.
- **Tests:** `tests/test_user_management.py` (the Phase 19 matrix: 401/403/cross-store/escalation/mass-assignment/idempotent-invite/deactivation-with-live-JWT/reactivation/self+last-admin guards/DTO-field allowlist/disabled-mode 404) + config guards. Suites now **488/488 SQLite and 488/488 PostgreSQL**.
- **Docs:** `ACCOUNT_LIFECYCLE.md` (new canonical), `AUTH_ARCHITECTURE.md` addendum, `DEV_ENVIRONMENT.md`, `.env.example`.

## Decisions

Display name = Supabase `user_metadata` (Auth owns profile identity; **no migration 0010**, production-migration assumptions untouched). Offboarding = membership deactivation only (Auth ban/delete assessed, deferred — destroys identity/history for no added control). In-app direct change-password deferred (recovery flow is the password path; Supabase stays the authority). **Flagged-open:** manager→manager administration (smallest policy shipped).

## Deployed DEV Smoke (performed pre-merge on the branch deployment)

All green, including the full live loop with an operator-provided deliverable address: **invite (manager UI/API) → real Supabase invite email → direct link opened from fresh navigation (SPA rewrite live) → set first password → global sign-out → login with the new password → correct Lot Staff identity/store from `/me`**. Live authorization probes: manager granting admin → 403; manager deactivating admin → 403; self-deactivation → 403; duplicate invite → 409 (single email sent); lot_staff on `/users` and sync-run → 403; shared reads + work-order PDF → 200; roster enriched with emails + invited-state badge; deactivate→reactivate cycle on the invited account. Unauthenticated: every operational + user route 401; `/health` public; direct `/auth/reset-password` → 200 HTML from fresh navigation; console clean (only deliberate 403 probes). QA dealership intact (16 open tasks / 2 recs / matrix on the dashboard).

Three live findings, each fixed on the branch during smoke: (1) display-name save invisible until token refresh → `refreshSession()` after `updateUser` (`5225c57`); (2) provider-refused vs credential-unavailable conflated in one 503 → distinguishable 422/503 classes (`c960ada`); (3) operator-side: a whitespace character inside the pasted `SUPABASE_SECRET_KEY` value on Render broke the credential (owner re-staged; the tool's local key test isolated it). Supabase's built-in email delivered to the team-member address after a delay — the provider limitation stands documented for non-member addresses.

Cleanup note: the test account (`kennett20054@gmail.com`, lot_staff, qa-motors) remains active for owner disposition — deactivate via User Management or keep as a live test identity.

## Production Impact

None. No schema change, no production env/config/user changes; the `/users` surface does not exist under the production posture.

## PR

**PR #12.** Task commits: `d1fe92c` (implementation), `5225c57` (display-name token refresh, found live), `c960ada` (admin-boundary error-class split, found live), `5831be8` (smoke record). Merge commit: **`02958f2`**. CI green on the merged head (488/488 SQLite, 488/488 PostgreSQL, frontend build, Vercel).

## Post-Merge Verification (dev-tracking DEV)

Both DEV services returned to tracking `dev` and redeployed the merged commit. Re-verified on the merged deployment: direct `/auth/reset-password` 200 from fresh navigation; tokenless 401s; deployed-bundle secret scan clean (no server key; only the public `sb_publishable_` anon key); **live signup probe → `signup_disabled`**; lot-staff session (the test account signing in with its recovery-set password — an end-to-end recheck in itself): shared reads + work-order 200, `/users` + sync-run 403, Settings shows no User Management; manager session: roster of 5 enriched members (Store B absent), deactivate→reactivate cycle on the synthetic lot-staff account, grant-manager and deactivate-admin both 403; display name set in Sprint 09 flowed through a fresh manager login. **Rail A: Verified** (register updated).

## Result

DealerDOH DEV has a complete dealership account lifecycle: authorized managers/admins provision users without public signup, users recover access through a real direct-link password-reset flow, dealership access revokes immediately through membership state, and Profile & Settings contains only real functionality — all privilege/store boundaries enforced server-side.

## What This Enabled Next

Sprint 10 — Inventory Ingestion Safety — starts against a DEV environment with real accounts, real recovery, and a user-administration surface; UAT (Sprint 16) can now onboard real testers without developer intervention.

---

# Governance Update — Repository Public-Release Sanitation Gate (pre-Sprint 09)

**Status:** Complete (docs-only)  
**Date:** 2026-08-16

Prompted by the possibility of eventually making the repository public: current secret-handling practices are strong (env-var deployment config, password-manager storage, deleted scratch staging, pre-PR secret scans, public-vs-secret key separation), but **historical repository exposure has not yet been proven clean** — a later `.gitignore` or file deletion does not remove a secret from prior commits.

Added to `V1_1_RELEASE_READINESS.md`:

- **§5.H.1 Repository Public-Release Sanitation** inside Rail H (executes in Sprint 13's security pass): read-only full-history audit (all commits/branches/tags/deleted files, env/config/scripts/workflows/fixtures/docs/dumps/backups/artifacts), the credential search list, the public-identifier vs real-secret distinction, the seven-step response to any historical secret (rotation first; history rewriting never sufficient alone, never automatic), current-tree public-release checks, and the gate states
- A register row: current state **Not Audited**; blocks **repository publication only, not v1.1**
- A back-burner trigger: **Public repository visibility** — fires when the owner intends private → public; requires the full audit, rotations, cleanup assessment, current-tree sanitation, CI scanning, final re-scan, and explicit owner approval

Repository publication remains a separate owner decision, deliberately decoupled from the v1.1 release. No implementation, scanning, rotation, or history modification occurred in this task.

---

# Sprint 11 — Observability, Structured Logging & Product Analytics

**Status:** In Progress on `feature/sprint-11-observability` (from `dev` = `61f9def`).
**Date:** 2026-08-17
**Rails:** F (Sentry + PostHog) + G (Structured Logging & Monitoring) — operative register lettering.

## Scope delivered on the branch (evidence grows toward the gate)

Three deliberately separate layers (`OBSERVABILITY.md` is canonical):
structured JSON application logs ("what happened, in which request,
how long"), Sentry ("what is breaking unexpectedly" — backend +
frontend, DSN-gated no-ops otherwise), PostHog ("what are users
doing" — explicit events only, autocapture/replay/form-capture OFF,
identity = internal `auth_user_id`, sign-out resets). Server-generated
`X-Request-ID` on every response, propagated through structured
records, Sentry tags, and the sync-completion record's
`sync_run_ids` (no schema change — no migration 0011). Environment
model local/test/ci/development/production reusing the existing
`ENVIRONMENT`/`VITE_ENVIRONMENT` variables; release = git SHA from
`RENDER_GIT_COMMIT` / build-baked `VERCEL_GIT_COMMIT_SHA`. Central
redaction (key-pattern + value-shape, wholesale cookies) applied to
logs and Sentry events; severity policy pins expected 4xx as
INFO/WARNING and never Sentry material; React Error Boundary gives
render failures an honest fallback. Sprint 10's ingestion boundary is
instrumented end to end (validation outcomes with codes/counts,
sync lifecycle with correlated run ids) with report contents/VINs/
filenames provably absent from telemetry.

**Design findings recorded while building (both caught by this
sprint's own tests):** (1) sync FastAPI dependencies run in
threadpool-copied contexts, so the authenticated log context rides
`request.state` rather than a contextvar (a contextvar set there is
invisible to the middleware task); (2) Sentry's default
LoggingIntegration would double-report every ERROR record as a second
event — the `dealerdoh` logger is ignored and
`auto_enabling_integrations=False` keeps `capture_unexpected()` the
single capture path.

**Deferred deliberately:** source-map upload (production builds emit
no source maps; secure upload needs `SENTRY_AUTH_TOKEN` as a build
secret — disproportionate this window; recorded diagnostic
limitation in `OBSERVABILITY.md` §10). Production activation of any
provider (future release train). Backend PostHog (frontend explicit
events only).

**Tests:** 37 new (26 backend observability incl. fake-transport
Sentry matrix + 11 frontend posture assertions following the
`test_frontend_config.py` precedent). Suites on the branch:
**586/586 SQLite · 586/586 PostgreSQL** (10/1 pre-existing skips).
Frontend production build green; bundle 538→848 kB raw (142→243 kB
gzip) from the two SDKs — recorded as a Rail J finding. Measured
overhead: `log_event` ≈ 0.07 ms; full local request round-trip
≈ 7 ms through TestClient (middleware share sub-ms); Sprint 10's
4,700-row validation benchmark unchanged (≈ 0.04 s).

**Pending toward Rails F/G verification:** owner DEV provider setup
(Sentry project + PostHog project; consolidated request at the
setup gate) · review-window deploy · deployed structured-log +
correlation + live Sentry/PostHog event evidence · the 15-question
telemetry privacy review against real payloads · merge · CI on
merged `dev`. Rail D remains untouched (Merged — NOT Verified;
Awaiting Vendor Evidence).

---

# Sprint 10 — Inventory Ingestion Safety, Report Classification & Pre-Sync Validation

**Status:** **Implementation Paused — Awaiting Vendor Evidence** (owner-directed closeout state). The known-evidence implementation is **MERGED** — PR #14 → `dev` as **`b389072`**, owner-approved 2026-08-17, **CI green on the merged head**, deployed-DEV smoke passed pre-merge on the branch review window. The sprint deliberately does not close as Complete (and Rail D is **not** Verified): the real Keyper Event contract remains pending vendor evidence, and resolving the actual Full-vs-Event structural distinction is the un-pause trigger (see Decisions 4–5).
**Date:** 2026-08-16 → merged 2026-08-17
**Rail:** D (operative register) / E (this catalog's lettering)

## Objective

Build the single trustworthy boundary between external dealership
reports and the sync engine, so a wrong, empty, or mis-generated
spreadsheet can never become false operational truth. *Missing
evidence ≠ zero. Invalid evidence ≠ valid zero.*

## Starting State

`dev` = `b19a56a` (Sprint 09 closed, Rail A Verified). The audit
found the reconciliation engine itself sound (presence-driven
diff-before-write, no absence-based transitions, missing-Keyper
skip+warn) — but the boundary treated "parsed" as "true": headers-only
files became `complete` SyncRuns with 0 records and overwrote the
day's operational report CSVs; slot labels were the only report
identity (any VIN-bearing file ingested as RapidRecon); no zero-row,
duplicate, row-shape, size, or count-sanity checks; no preview; a
blank Tekion VIN could create a corrupt `vehicle` row.

## Implementation

One boundary, both endpoints, every future acquisition path
(`INGESTION_ARCHITECTURE.md` is canonical):

- **Contract registry** (`sync/report_contracts.py`): 7 contracts —
  6 supported slots + Keyper Key Event recognized-but-UNSUPPORTED
  with deliberately **zero invented column facts** (no sample exists;
  vendor discovery §6.2 is the trigger). Ingestion modes:
  authoritative/historical/exception/contextual snapshot +
  incremental_event.
- **Deterministic content classification**
  (`sync/report_classifier.py`): headers are identity;
  slot/filename/MIME are hints. Exact / ambiguous / vendor-variant /
  unrecognized, never probabilistic, never guessed.
- **Validation boundary** (`sync/ingestion.py`): file safety (20 MB
  cap enforced at save, 50k-row cap, Excel/ZIP magic, BOM, duplicate
  headers, undecodable bytes), wrong-slot rejection naming
  expected+detected, structural (missing required columns named),
  per-contract zero-row policy (authoritative snapshots hard-reject;
  MDD/RapidRecon zero warns + requires acknowledgement), row-level
  VIN checks (blank VIN in identity-originating Tekion reports
  rejects the file — the recorded exit-5 decision; inert bad VINs
  warn), per-contract duplicate semantics (sold-report VIN repeats
  stay legitimate history), scoped comparable baselines with
  suspicious-count warnings, ERROR/WARNING/INFO severities with
  stable codes, dealership-language messages (no raw parser text),
  SHA-256 fingerprints.
- **API**: `POST /inventory-sync/validate` (zero-mutation preview,
  same admin/manager gate, temp files deleted) and `/run` now
  **revalidates everything server-side** — errors 422; warnings need
  `acknowledge_warnings` + a fingerprint matching the exact uploaded
  bytes (409 `WARNINGS_NOT_ACKNOWLEDGED`/`STALE_VALIDATION`);
  structured rejection payloads carry the full validation DTO;
  runtime failures return a dealership-language 500, never a trace.
  Baselines recorded per accepted report after success.
- **Migration 0010** `report_baseline` (both engine dialects), scoped
  `(vendor, report_type)` — deliberately not derived from
  `sync_run.records_processed` (the `tekion` run spans both Tekion
  report types by design). Migration-drift guard satisfied:
  `tools/migrate_sqlite_to_postgres.py` `EXPECTED_SCHEMA_VERSION`
  9→10 + `TABLE_ORDER`/`IDENTITY_PKS`/`ORDER_BY`; seed-schema pin
  updated; RC-freeze rehearsal refresh flagged in the migration
  header and register.
- **Frontend** (`InventorySync.tsx`): validate → preview
  (per-report detected type, counts, baseline change, issues) →
  acknowledgement (never pre-checked) → run; file changes invalidate
  the preview; structured 422/409 render the server's fresh view.
- Retired `sync/upload_validation.py` (absorbed; no second
  column-requirements table).
- Dev tooling: launch entries for parallel-session local
  verification (alt ports), `run_dev_seed_api.py` honors `PORT`.

## Decisions Recorded

1. **Zero-row policy per contract** (registry table in
   `INGESTION_ARCHITECTURE.md` §3): reject for Tekion
   current/sold, Keyper full, RecovR; warn+acknowledge for MDD
   not-paired and RapidRecon (a legitimately-empty exception list is
   plausible; a human confirms, and the acknowledged zero is recorded
   honestly as zero).
2. **Invalid record shape = quarantine-file, never silent row drops**
   (Rail D exit 5): blank VINs where rows originate Vehicle identity
   reject the file with line numbers; malformed-but-present VINs
   warn; identity-inert sources warn only. Evidence files are never
   edited.
3. **Duplicates = surfaced warnings, never silent dedupe** (exit 6):
   per-contract keys; sold-report VIN repeats deliberately unflagged
   (legitimate history owned by the existing conflicts machinery).
4. **Suspicious-count thresholds — OWNER-RATIFIED at the PR gate
   (2026-08-16)** as the initial beta policy, subject to tuning from
   real operational evidence (exit 7): warn on decrease >15% AND ≥10
   rows; warn on increase >50% AND ≥25 rows (the RecovR
   umbrella-file shape). Warning/review thresholds, never hard
   rejection; explicit Manager/Admin acknowledgement required;
   future unattended ingestion HOLDs. Grounding in
   `INGESTION_ARCHITECTURE.md` §8.
5. **Keyper Event Report — evidence status corrected by the owner
   (2026-08-16)**: no sample exists → no schema invented. What the
   synthetic stand-in PROVES: the known Full Inventory contract
   works, and unsupported/nonmatching Keyper-shaped evidence fails
   safely (rejected in every slot, "can never substitute for the
   full snapshot" language, test-pinned). What it does NOT prove: a
   *real* Event report could plausibly satisfy the current Full
   signature — the actual Full-vs-Event structural distinction is
   **PENDING VENDOR EVIDENCE** and must not be claimed PASS
   (`INGESTION_ARCHITECTURE.md` §6 evidence table). This is why the
   sprint's post-merge state is Implementation Paused — Awaiting
   Vendor Evidence. Vendor discovery (register §6.2) is the trigger;
   when the real format arrives, re-verify the Full signature
   actually discriminates and add discriminating columns if the real
   formats overlap.
6. **Unattended-ingestion HOLD rule** documented now (any WARNING →
   HOLD, automation never auto-acknowledges) for the conditional
   §6.2 rail to inherit.

## Tests / CI

+60 tests: `tests/test_ingestion_validation.py` (47 — registry,
classifier matrix incl. case-sensitivity evidence, wrong-slot incl.
the RecovR→RapidRecon hole, Keyper boundary, file safety incl.
parser-bomb caps and no-raw-parser-text sweep, zero-row matrix,
row-level, duplicates, baseline scoping + exact threshold boundaries,
fingerprints, no-mutation, production-scale perf), API-level
revalidation/acknowledgement/stale-fingerprint/zero-mutation/
baseline-recording/suspicious-count-E2E, `/validate` authz matrix in
`test_auth.py`. Suites locally: **548/548 SQLite; 548/548
PostgreSQL 17.5** (portable rehearsal cluster; 1 documented engine
skip). Standing QA dealership regression untouched. Performance:
validate 4,700-row Tekion ≈ **0.04 s**. Frontend build clean. CI on
the PR: green (next section).

## CI on PR #14

Fully green on head `c818d23` (2026-08-16): Backend tests (SQLite) ·
Backend tests (PostgreSQL) · Frontend production build · Vercel
(dealerdoh-dev + lotsync + preview comments).

## Deployed-DEV Smoke — branch review window (2026-08-16/17, PASSED)

Owner switched Render `dealerdoh-api-dev` + Vercel `dealerdoh-dev` to
the sprint branch; verified serving it before smoke (API `/health`
ok/postgres + `/inventory-sync/validate` present (401 = auth-gated,
would be 404 on old code); new frontend bundle carries the Sprint 10
strings; deployed-bundle secret scan clean — the lone `sb_secret`
grep hit is supabase-js's own key-format guard string; only the
intentionally-public `sb_publishable_` key present). Run as the
retained manager session against the live standing QA dealership:

- **Valid set:** generated 40-row Tekion current (smoke-namespaced
  `9SMOKEVIN…`/`S10SMK…`) → classified exact, preview Ready, "No
  prior baseline" INFO → run → "Sync complete — 40 vehicles
  processed"; history/last-sync updated; baseline recorded.
- **Empty authoritative snapshot:** headers-only Tekion → Rejected
  with the export-mistake message (incl. the "will not treat an empty
  export as 'the lot has zero vehicles'" language), Run disabled;
  direct-API `/run` → **422 `REPORT_VALIDATION_FAILED` /
  `NO_DATA_ROWS`** with zero mutation.
- **Wrong report type:** sold-shaped file in the Unsold slot →
  Rejected, "Detected: Tekion — Sold Inventory", message names both
  contracts.
- **Missing column:** Status-less Tekion → Rejected, "required
  column(s) missing: Status".
- **Keyper variant:** stand-in in the Keyper slot → Rejected with the
  "not the Full Key Inventory report… not yet supported… can never
  substitute for the full inventory snapshot" language.
- **Suspicious count:** 20-row follow-up → preview "20 rows vs 40 in
  the previous comparable report (−20, −50.0%)", Review-needed chip,
  acknowledgement present and UNCHECKED, Run disabled; **direct API
  unacknowledged → 409 `WARNINGS_NOT_ACKNOWLEDGED` with
  `SUSPICIOUS_COUNT_DROP` recomputed server-side; blind
  `acknowledge_warnings=true` without fingerprint → 409
  `STALE_VALIDATION`**; UI tick + run → "Sync complete — 20 vehicles
  processed"; baseline advanced to 20.
- **Authorization:** tokenless 401s on `/validate`, `/run`,
  `/vehicles`, `/tasks`, `/inventory-sync/history`, `/dashboard`;
  the entire manager path exercised live. Deployed lot-staff 403s
  were not re-exercised this window (no lot_staff session available;
  credentials live in the owner's password manager) — covered by the
  CI negative matrix on this exact head (`/validate` + `/run` role
  tests), the unchanged Sprint 05 auth layer, and Sprint 09's
  deployed lot-staff 403 evidence.
- **Existing product:** Dashboard matrix exact (16 open / 2 recs /
  58.82% health), Vehicles list, Vehicle Detail QA1025 with
  timeline, Tasks page dispatch queue grouped exactly
  (7 checked-out-key / 4 recovr-install / 2 key-for-recovr / 3 mdd;
  Closed 2), work-order PDF 200 `%PDF` (~5 KB), Profile & Settings.
- **QA dealership intact:** 28 standing active QA vehicles and all
  16 outstanding QA tasks unchanged; the smoke syncs generated
  **zero** tasks (Tekion-only evidence — the missing-Keyper
  restraint, live) and the run summary carried the "Keyper report
  was not provided" warning. **Smoke residue, clearly namespaced for
  cleanup:** 40 `9SMOKEVIN…` vehicles, 3 sync-run batches, 2
  baseline rows, 0 tasks — recommend the standard `seed_dev.py
  --reset` reseed at `/merge-dev` closeout to restore the exact
  standing matrix.
- **Console:** clean except the three deliberate probe responses
  (409/409/422) logged natively by the browser.

## Local UI Verification (pre-PR, seeded dev API + Vite, this branch)

Empty snapshot → Rejected card with the export-mistake message, Run
disabled; file swap → preview invalidated; clean 40-row file → Ready
→ run → "Sync complete — 40 vehicles processed", baseline recorded;
20-row follow-up → "20 rows vs 40 … (−20, −50.0%)" warning, ack box
unchecked, Run gated until ticked, then success; 21-row (+5%) → Ready
with comparison, no warning; Keyper file in Tekion slot → Rejected
naming both contracts. All network calls 200 post-CORS-fix; no new
console errors.

## Production Impact

None. `master` untouched at `13c4f815` / `v1.0.0-beta.6`; no
production deploy, data, env, Supabase, or DNS change.

## /data-migration record — migration 0010 (owner-directed closeout pass, 2026-08-16)

Per `.claude/workflows/data-migration.md`, invoked explicitly:

- **Target environments:** local SQLite + Supabase DEV only (both via
  the existing auto-migration runner at connect/deploy). Production
  is NOT a target; it receives 0010 only through the governed release
  trains, never as a side effect.
- **Branch/SHA:** `feature/sprint-10-ingestion-safety` (0010
  introduced in `31753b0`).
- **Schema state:** 9 → 10. **Change class: additive** (one new
  table, `report_baseline`; no existing table/column/index touched;
  no backfill — pre-Sprint-10 baselines are deliberately not
  reconstructable; no destructive step). **Rollback:** `DROP TABLE
  report_baseline`.
- **Backup status:** the verified 2026-08-15 production backup is
  untouched and unaffected (production schema unchanged at v9 until
  Release A).
- **Affected tables / data volume:** `report_baseline` only; zero
  rows at creation, grows one row per accepted report per executed
  sync.
- **SQLite→Postgres checklist:** dual dialect files following the
  0001–0009 port conventions (AUTOINCREMENT→IDENTITY,
  `datetime('now')`→`now()::text` TEXT timestamps); `RETURNING` used
  (no `lastrowid`); no booleans/JSON; FK to `dealership` nullable
  (ordered after its parent in `TABLE_ORDER`); ordering/pagination via
  integer PK `ORDER BY … LIMIT 1` (engine-neutral); qmark
  translation as everywhere else.
- **Production migration path understands v10 — PROVEN end-to-end**
  on the Sprint 07 portable PG 17.5 cluster (started for this pass,
  disposable DB, dropped + cluster stopped after):
  `tools/generate_rehearsal_dataset.py --scale production` emitted a
  **schema v10** source automatically (it applies the real runner) —
  4,700 vehicles / 14,665 business rows; tool **dry-run** passed the
  v10 preflight gate; tool **--execute** copied 13 tables incl.
  `report_baseline` (0 rows, correctly) and **all four validation
  layers passed exactly** (`schema_migrations 1..10`, 14 tables, 15
  indexes, sequences, counts, breakdowns, orphans, time-ranges,
  sampled rows) in **1.156 s** — in line with Sprint 07's 0.98 s;
  focused `tests/test_migration_tool` re-run under PostgreSQL:
  **10/10**.
- **RC-rehearsal consequence:** the RC-freeze rehearsal refresh must
  use a v10 source — which the generator now produces by
  construction, and which this pass already exercised once
  end-to-end. Dated amendment notes added to
  `PRODUCTION_MIGRATION_PLAN.md` and
  `PRODUCTION_MIGRATION_RUNBOOK.md` (read "0001–0009" as
  "0001–0010"; Release A boot applies 0009+0010, both additive;
  beta.6-rollback-over-newer-DB argument holds identically; final
  pre-cutover backup will be v10). `PRODUCTION_MIGRATION_REHEARSAL.md`
  is left as the accurate Sprint 07 historical record.

## Git

Task branch `feature/sprint-10-ingestion-safety`: `31753b0`
(implementation), `dd7d868` (launch tooling), `58545dd` (sprint
record), `c818d23` (PR fill), `f5a368b` (gate state), `9a03329`
(owner closeout passes), `a999af9` (deployed smoke record).
**PR #14, owner-approved, MERGED as `b389072`** (merge commit = `dev`
head), **CI green on the merged head.** Closeout branch
`docs/sprint-10-merge-closeout` carries this record plus the
reseed-drop-list fix (below).

## Merge & Closeout (2026-08-17)

- **Merged:** PR #14 → `b389072`; CI on merged `dev`: success.
- **Closeout finding (fixed before the reseed ran):** `seed_dev.py`'s
  postgres `--reset` drop list `_APP_TABLES` was missing
  `report_baseline` — 0010 landed without updating it, and the miss
  was silent (`DROP … CASCADE` tolerates the dangling FK; `CREATE
  TABLE IF NOT EXISTS` keeps the survivor), so a reseed would have
  left the smoke-era baseline rows behind and the next real sync
  would have false-warned against them. Fixed on the closeout branch;
  `tests/test_seed_dev.py::ResetDropListDriftGuardTest` now pins
  `_APP_TABLES ⊇ tools/migrate_sqlite_to_postgres.TABLE_ORDER` so the
  next migration cannot repeat the drift.
- **DEV restoration to `dev` tracking (owner, 2026-08-17):** DONE —
  Render `dealerdoh-api-dev` back on `dev`; Vercel `dealerdoh-dev`
  production deployment rebuilt from `dev`.
- **Standard reseed (2026-08-17):** DONE, from the fixed checkout,
  credentials via the owner-staged file (Sprint 04 pattern; file
  deleted afterward, absence verified, no values printed).
  `seed_dev.py --reset` dropped **14** application tables (the fixed
  list incl. `report_baseline`) and replayed the QA days:
  **vehicle=34, event=98, task=18, recommendation=2,
  pending_identity=3, sync_run=10** — the exact standing matrix.
  `tools/provision_dev_auth.py` re-provisioned all **5** synthetic
  memberships (every Supabase identity "existing" — relinked, not
  recreated). Post-reseed verification: `report_baseline` **empty**
  (stale smoke baselines gone), **zero** `9SMOKEVIN…` vehicles or
  events, 28 active / 6 sold. NOTE: the reset also removed the Sprint
  09 test account's membership (kennett20054@gmail.com — its Supabase
  Auth identity survives, but it holds no dealership access until
  re-granted via User Management; flagged to the owner).
- **Post-restoration health verification (2026-08-17):** DEV API
  `/health` ok/development/postgres; `/inventory-sync/validate`
  present + auth-gated (401 tokenless) — Sprint 10 code now served
  FROM `dev`; frontend 200; live pane check as the re-provisioned
  manager membership: DEV banner, dashboard at the exact standing
  matrix (16 open tasks / 2 recommendations / 58.82% health).
- **Sprint-branch deletion:** DONE — `feature/sprint-10-ingestion-safety`
  deleted remote + local (was `a999af9`) after both services were
  confirmed off it.

## Findings / Risks

- ~~Suspicious-count thresholds pending ratification~~ —
  **owner-ratified at the gate (2026-08-16)** as initial beta
  policy, subject to tuning from real operational evidence.
- **Keyper Full-vs-Event residual risk (owner-corrected evidence
  status):** the real structural distinction is PENDING VENDOR
  EVIDENCE — if a real Event export happens to carry the Full
  signature columns, the classifier would accept it as a snapshot.
  Predates Sprint 10 (any superset passed before); narrowed but not
  closable without the vendor format. Keyper stays manual-upload;
  no Keyper acquisition automation before discovery. Ingestion of
  the Event report itself is NOT required for v1.1.
- Pre-Sprint-10 baselines don't exist (`records_processed` is
  polluted by design) — first post-merge sync per report type shows
  "No prior baseline" once, then comparisons begin. Honest, not a
  defect.
- The CLI (`main.py`) remains outside the boundary — documented
  exclusion (`INGESTION_ARCHITECTURE.md` §12), future
  retire-or-wire decision.
- Rail J note: frontend bundle-size warning unchanged (pre-existing,
  register-tracked).

## What This Enables Next

Sprint 11 (Observability & Structured Logging) instruments a sync
flow that now has crisp, named states (validated / rejected /
needs-review / executed / failed) and stable issue codes to count —
and the conditional automated-ingestion rail inherits a boundary that
already refuses to trust unattended evidence.

---

# Current v1.1.0-beta Goal

The first DealerDOH-era production release is expected to become:

**`v1.1.0-beta.1`**

rather than immediately cutting production over after Sprint 07.

Production remains:

**LotSync `v1.0.0-beta.6`**

while additional release features and production-readiness rails are developed in `dev`.

---

# v1.1.0-beta Release Readiness Register

> **Superseded (Sprint 08):** the operative register — with the
> ratified classifications, frozen sprint order, exact exit
> conditions, and evidence rules — is
> [`V1_1_RELEASE_READINESS.md`](V1_1_RELEASE_READINESS.md). The table
> below predates that freeze and is retained as historical context
> per this document's no-rewrite rule.

This table is the fast release-gate view. The detailed Rail sections below explain the scope and reasoning. **Planned sprint numbers are provisional until Sprint 08 formally freezes the roadmap.**

| Rail | Priority | Status | Provisional Sprint | Blocks v1.1? | Exit Condition |
|---|---|---|---|---|---|
| Account Lifecycle | Required | Planned | 09 | Yes | Admin/manager provisioning, password reset/recovery, settings/profile, disable/offboard path verified |
| User Onboarding & Help | Required | Planned | 10 | Yes | First-login guidance + contextual Help usable by uncoached user |
| Role-Aware Presentation | Required | Planned | 10 | Yes | Manager and Lot Staff see appropriate emphasis without bypassing server authorization |
| Notifications | Likely Required | Planned / scope to confirm | 12 | TBD | Minimal in-app actionable notifications with read/unread + safe retention |
| Inventory Ingestion Safety | Required | Planned | 11 | Yes | Empty/incomplete/wrong-type reports fail closed; preview/sanity checks precede mutation |
| Automated Report Ingestion | Conditional | Discovery | TBD | No, unless vendor research makes it an explicit release item | Vendor mechanisms confirmed and routed through same classifier/validator |
| Observability (Sentry/PostHog) | Required | Planned | 13 | Yes | Error telemetry + product events live with verified redaction/privacy controls |
| Structured Logging & Monitoring | Required | Planned | 13 | Yes | Request IDs, structured safe logs, key alerts/health checks verified |
| Security Hardening | Required | Planned | 14 | Yes | Read-only audit → fixes → adversarial re-test; no unresolved release-blocking Critical/High gaps |
| Dependency / Supply Chain | Required | Planned | 14 | Yes | npm/Python scans in CI; reachable Critical/High findings resolved or explicitly accepted |
| Performance & Resilience | Required | Planned | 15 | Yes | Realistic dealership load/slow-network paths measured and release blockers fixed |
| Accessibility | Required engineering target | Planned | 15 | Yes | WCAG 2.2 AA-oriented audit complete; release-blocking accessibility defects fixed |
| Privacy / Legal Readiness | Required assessment | Planned | 16 | Yes for commercial/public readiness | Data inventory + retention/subprocessor mapping + accurate policy/statement drafts |
| Human UAT | Required | Planned | 17 | Yes | Manager + Lot Staff complete uncoached DEV tasks; blockers addressed |
| Release Candidate Freeze | Required | Planned | 18 | Yes | Scope frozen, `/release-readiness` green, final smoke/security/accessibility/migration assumptions confirmed |

# v1.1.0-beta Release Rails

---

# Rail A — Account Lifecycle

**Priority:** REQUIRED

Planned:

- manager/admin-created users
- no public signup
- invite/provision user workflow
- password reset
- account recovery
- working Profile/Settings
- session lifecycle review
- account disable/offboarding
- role/store display
- password/security controls

Longer-term:

- MFA for privileged users

---

# Rail B — User Onboarding & Help

**Priority:** REQUIRED

Planned:

- first-login tutorial
- guided onboarding
- contextual Help button
- Inventory Sync help
- page-level explanations
- understandable empty states
- loading states
- friendly error states

Goal:

DealerDOH should not depend on the developer personally teaching every new user how the application works.

---

# Rail C — Role-Aware Presentation

**Priority:** REQUIRED

Decision:

Do not create separate applications for Manager vs Lot Staff.

Use role-aware presentation within one DealerDOH application.

## Manager Experience

Potential emphasis:

- operational overview
- inventory health
- recommendations
- sync controls
- broader task visibility
- warnings/system information

## Lot Staff Experience

Potential emphasis:

- Today's Work
- Tasks
- Vehicle lookup
- Vehicle Detail
- work-order execution
- less management noise

Future departments may gain genuinely distinct operational screens/modules when their workflows justify them.

---

# Rail D — Notifications

**Priority:** LIKELY REQUIRED

Initial v1 scope should remain intentionally small.

Potential notification types:

- inventory sync failure
- required source missing
- significant recommendation
- task assignment/work generation
- important system warning
- account/security event

Initial features:

- in-app notification center
- unread/read state
- timestamps
- relevant destination
- mark read
- retention policy

Deferred:

- SMS
- mobile push
- Slack
- complex digests
- advanced notification preferences

---

# Rail E — Inventory Ingestion Safety

**Priority:** REQUIRED

**Status (2026-08-16):** implemented in Sprint 10 (this catalog's E =
the operative register's Rail D — see the lettering note there). The
pipeline below was built as specified; `INGESTION_ARCHITECTURE.md` is
now canonical; suspicious-count thresholds owner-ratified as initial
beta policy. Pending: merge + deployed-DEV smoke; the real Keyper
Full-vs-Event structural distinction is **PENDING VENDOR EVIDENCE**
(post-merge sprint state: Implementation Paused — Awaiting Vendor
Evidence). See the Sprint 10 entry for the full record.

This is a major operational safety rail.

Principle:

> Invalid evidence is not valid zero.

DealerDOH must never interpret an incorrectly generated or empty dealership report as meaning that inventory disappeared.

## Planned Ingestion Pipeline

```text
Input
    ↓
Identify Vendor
    ↓
Identify Report Type
    ↓
Validate Structure
    ↓
Validate Data
    ↓
Sanity Check
    ↓
Preview
    ↓
Accept / Reject
    ↓
Sync Engine
```

## Report-Type Awareness

Example:

### Keyper

- Full Inventory Report
- Key Event Report

These must not be treated as interchangeable.

### Tekion

- Current Inventory
- Sold Inventory

Other vendor report contracts should be identified as they are understood.

## Validation Examples

### Empty file

Reject.

Example user message:

> This report contains no vehicle records. Verify that vehicles were selected when generating the export.

### Headers but no records

Reject.

### Missing required columns

Reject and identify the missing fields.

### Wrong report type

Detect and explain the mismatch.

### Suspicious count change

Example:

Previous Tekion inventory:

987

New report:

14

Do not automatically process.

Warn that the export may be incomplete.

## Sync Preview

Potential future UX:

```text
Tekion Current Inventory

Vehicles: 972
Valid VINs: 972
Duplicates: 0
Missing VINs: 0
Previous report: 964
Difference: +8 (+0.8%)

Report looks valid.
```

This validation layer should eventually serve:

- manual uploads
- emailed reports
- vendor API imports

---

# Rail F — Automated Report Ingestion

**Priority:** CONDITIONAL

Implementation should wait until dealership research confirms the available vendor mechanisms.

Current investigation:

## Tekion

Potential scheduled emailed reports.

Need to verify:

- full inventory vs delta
- cadence
- attachments
- sender/subject
- filenames
- export reliability

## Keyper

Potential email reports/events.

Need to distinguish:

- full inventory report
- event report

## RecovR

Current researched possibilities:

- API access through dealership IT/vendor coordination
- browser automation fallback

## RapidRecon

Known limitation:

- emailed summary approximately once daily

## MDD

Still under research.

Potential long-term architecture:

```text
Manual Upload ─────┐
                   │
Scheduled Email ───┼─→ Report Validation Pipeline
                   │
Vendor API ────────┘
                           ↓
                       Sync Engine
```

---

# Rail G — Observability

**Priority:** REQUIRED

Planned services:

## Sentry

Purpose:

> What is breaking?

Potential capture:

- frontend exceptions
- backend exceptions
- release/version
- environment
- request correlation
- route
- safe user/store context

Never capture:

- passwords
- JWTs
- Authorization headers
- database passwords
- raw sensitive uploads

## PostHog

Purpose:

> What are users actually doing?

Potential events:

- Inventory Sync Started
- Inventory Sync Completed
- Inventory Sync Failed
- Help Opened
- Work Order Generated
- Tutorial Completed

Potential product questions:

- Where do users get stuck?
- Which features are actually used?
- How often do syncs fail?
- Does Help reduce workflow abandonment?

Session replay must be intentionally reviewed for privacy/redaction before enabling broadly.

---

# Rail H — Structured Logging & Monitoring

**Priority:** REQUIRED

Move beyond plain console output.

Desired structured fields:

- timestamp
- level
- environment
- request ID
- safe user ID
- dealership ID
- route
- response status
- duration
- safe error code

Never log:

- passwords
- access tokens
- Authorization headers
- private keys
- DB credentials
- full sensitive reports

Potential alerts:

- sustained API errors
- DB unavailable
- failed sync
- unusual authentication failures
- storage issues
- abnormal operational changes

---

# Rail I — Security Hardening

**Priority:** REQUIRED

Before `v1.1.0-beta.1`, perform a dedicated read-only security audit followed by targeted remediation.

Audit categories include:

- authentication
- authorization
- object-level authorization
- tenant/store boundaries
- secrets
- SQL injection
- XSS
- request validation
- upload validation
- path traversal
- rate limiting
- brute-force resistance
- API payload limits
- excessive data exposure
- error leakage
- security headers
- CSP
- clickjacking
- dependency vulnerabilities
- debug/test exposure
- session/token handling
- CORS
- logging/redaction
- environment separation
- race conditions
- business-logic abuse

Do not blindly implement controls that do not apply.

Audit findings should be classified:

- PASS
- FAIL
- UNKNOWN
- N/A

Every PASS/FAIL should have code evidence.

---

# Rail J — Dependency / Supply-Chain Security

**Priority:** REQUIRED

Planned:

- npm dependency audit
- Python dependency audit
- direct/transitive package inventory
- lockfile verification
- reachability review
- vulnerability classification
- automated dependency scanning in CI

Do not blindly apply breaking upgrades because a scanner returns a warning.

Critical/High reachable vulnerabilities should block release readiness unless explicitly reviewed.

---

# Rail K — Performance & Resilience

**Priority:** REQUIRED

Test against realistic dealership usage, not arbitrary internet-scale numbers.

Areas:

- Dashboard queries
- Vehicles
- search/filter
- Tasks
- Inventory Sync
- PDF generation
- mobile
- multiple concurrent dealership users
- thousands of vehicle/events
- network throttling

Check:

- query performance
- indexes
- API payload sizes
- pagination
- expensive endpoints
- frontend bundle size
- unnecessary requests
- loading states
- slow/mobile connection behavior

---

# Rail L — Accessibility

**Priority:** REQUIRED ENGINEERING TARGET

Target:

**WCAG 2.2 AA-quality behavior**

Review:

- keyboard navigation
- focus visibility
- labels
- screen-reader semantics
- forms
- errors
- modal focus
- color contrast
- touch targets
- heading structure
- loading/status announcements
- mobile zoom
- reduced motion where applicable

Future public materials should include an Accessibility Statement, but actual product accessibility is the primary requirement.

---

# Rail M — Privacy / Legal Readiness

**Priority:** REQUIRED ASSESSMENT

Before broader commercial rollout, create an accurate data inventory covering:

- user identity
- account information
- vehicle information
- uploaded reports
- logs
- IP/device information
- analytics
- error telemetry
- retention

Planned documents may include:

- Privacy Policy
- Terms of Service
- Accessibility Statement
- Security page
- Data retention/deletion policy
- Incident-response procedure
- Subprocessor list
- support/security contact
- customer/SaaS agreement
- future security/DPA addendum

Do not publish generic legal documents that promise controls DealerDOH does not actually implement.

---

# Rail N — Human User Acceptance Testing

**Priority:** REQUIRED

AI smoke testing is not a replacement for actual dealership users.

Before production cutover:

## Manager UAT

Provide login and a goal.

Do not coach.

Observe:

- confusion
- hesitation
- terminology
- incorrect clicks
- missed actions
- Help usage
- error recovery

## Lot Staff UAT

Repeat with the actual operational workflow.

Use findings to identify true release blockers.

---

# Back-Burner Security / Architecture Triggers

Do not build these prematurely.

Instead, trigger the corresponding work when DealerDOH crosses the relevant boundary.

## RLS

Trigger:

- browser begins direct sensitive Supabase access
- richer multi-store architecture

## Full Per-Row Store Scoping

Trigger:

- before onboarding a second real dealership/store

## Webhook Security

Trigger:

- first inbound third-party webhook

Require:

- signature verification
- replay prevention
- idempotency

## AI Tool Security

Trigger:

- DealerDOH gains an AI assistant capable of reading protected data or taking actions

Require:

- authorization outside the model
- constrained tools
- validated arguments
- prompt-injection controls
- confirmation for irreversible work

## Customer Financial Information / GLBA

Trigger:

DealerDOH begins ingesting dealership customer financial or other sensitive customer information.

Perform dedicated regulatory/security assessment before shipping.

## Public API

Trigger:

first external DealerDOH API/integration.

Require:

- scoped credentials
- rotation
- revocation
- least privilege
- rate limiting

## Payments

Trigger:

DealerDOH introduces self-service billing/subscriptions.

Perform dedicated payment/security implementation rather than extending current operational auth casually.

## Object Storage

Trigger:

source reports or generated artifacts begin living in Supabase Storage or another object store.

Require private-by-default storage policy and authorized access.

## Public Repository Visibility

Trigger:

Owner intends to change repository visibility from private → public.

Required controls before the trigger may execute:

- full-history secret audit (all reachable commits/branches/tags, deleted files included)
- credential rotation for every historical exposure
- history-cleanup assessment (rotation first; rewriting never automatic, never sufficient alone)
- current-tree sanitation checks
- CI secret/dependency scanning in place
- final re-scan
- explicit owner approval

The audit itself is scheduled inside Sprint 13 — Security + Supply Chain (`V1_1_RELEASE_READINESS.md` §5.H.1). Current state: **Not Audited**.

---

# Proposed v1.1.0-beta Sprint Roadmap — Provisional

> **Superseded (Sprint 08):** the frozen order (09 Account →
> 10 Ingestion → 11 Observability → 12 Role-UX/Onboarding →
> 13 Security+Supply-Chain → 14 Perf+A11y → 15 Legal → 16 UAT →
> 17 RC) lives in
> [`V1_1_RELEASE_READINESS.md`](V1_1_RELEASE_READINESS.md) §9.
> Retained below as historical context.

This roadmap remains adjustable and is **not locked** until Sprint 08 formalizes the scope/readiness register. Sprint numbers, bundling, and order may change as risk and dealership research clarify priorities.

## Sprint 08 — v1.1 Release Scope & Readiness Register

Formalize:

- required rails
- conditional rails
- deferred scope
- release blockers
- acceptance criteria

## Sprint 09 — Account Lifecycle & Settings

Potential scope:

- password reset
- account recovery
- Profile/Settings
- user provisioning/invite foundations
- session behavior
- account disablement

## Sprint 10 — Onboarding, Help & Role-Aware UX

Potential scope:

- first-login tutorial
- contextual Help
- Manager presentation
- Lot Staff presentation
- loading/error/empty states

## Sprint 11 — Inventory Ingestion Safety

Potential scope:

- report classification
- report-type contracts
- Excel validation
- empty-file protection
- suspicious-count detection
- wrong-report detection
- pre-sync preview

## Sprint 12 — Notifications

Potential scope:

- notification model
- in-app center
- read/unread
- system/sync/task events

## Sprint 13 — Observability

Potential scope:

- Sentry
- PostHog
- structured logging
- request IDs
- alerting
- safe telemetry rules

## Sprint 14 — Production Security Hardening

Potential sequence:

1. read-only audit
2. findings classification
3. targeted fixes
4. adversarial verification
5. re-audit

## Sprint 15 — Performance, Reliability & Accessibility

Potential scope:

- slow-network testing
- realistic concurrency
- query/index review
- bundle/API analysis
- accessibility audit
- accessibility fixes

## Sprint 16 — Privacy / Legal Readiness

Potential scope:

- data-flow inventory
- retention inventory
- analytics/subprocessor inventory
- Privacy Policy draft
- Accessibility Statement
- security disclosures
- incident-response documentation

Legal review may still be appropriate before broader commercialization.

## Sprint 17 — Human UAT

Manager and Lot Staff testing against DEV without developer coaching.

Fix only true release blockers.

## Sprint 18 — v1.1.0-beta Release Candidate Freeze

- freeze feature scope
- `/release-readiness`
- final security audit
- final accessibility checks
- regression suite
- final DEV smoke
- confirm Sprint 07 migration assumptions still apply
- repeat targeted migration rehearsal if necessary
- select production window

## Production Train

Expected sequence remains:

### Release A

DealerDOH-capable production code, still SQLite/Auth disabled.

### Release B

Production PostgreSQL cutover.

### Release C

Production Auth enablement.

### Release D

DealerDOH branding/domain migration.

Target first DealerDOH production version:

**`v1.1.0-beta.1`**

---

# Conditional Feature Discovery — This Week

Investigate dealership systems before committing automatic ingestion to v1.1.

Questions to resolve:

## Tekion

- Can scheduled reports be emailed automatically?
- Which report types?
- Full snapshot or delta?
- Minimum frequency?
- Attachment format?
- Stable filename/subject/sender?

## Keyper

- Full inventory export?
- Event report?
- Email scheduling?
- Snapshot vs delta behavior?

## RecovR

- API availability?
- dealership IT/vendor approval process?
- browser automation fallback?

## RapidRecon

- exact daily emailed-summary capabilities

## MDD

- available export/API/email mechanisms

Automatic ingestion remains conditional until this research is complete.

---

# Evidence & Status Rules

To keep this document trustworthy, sprint status is evidence-based:

- **Complete** means the work was merged into `dev` (or the intended target), the merge SHA is recorded, and required post-merge CI/smoke checks passed.
- **Implementation Complete — Awaiting Merge** means the PR is green but has not yet been merged.
- **Planned** means no implementation claim should appear in the completed-history sections.
- Record the **PR number, task commit(s), merge commit, and CI result on the merged head** whenever known.
- When runtime behavior changes, record deployed smoke-test evidence after merge.
- Never invent missing SHAs, dates, counts, or test results. Use **TBD** and fill from Git/PR metadata later.
- Dates should come from PR/commit/release metadata, not memory guesses.
- A finding remains in the Active Findings register until explicitly resolved, accepted/deferred with a trigger, or superseded by a later decision.
- Historical behavior should not be rewritten to match current architecture; newer decisions belong later in chronology or in the Decision Register.

# Rolling Update Procedure

At the completion of each sprint:

1. Add the sprint chronologically.
2. Record objective.
3. Record starting state.
4. Record actual implementation.
5. Record decisions.
6. Record tests/CI results.
7. Record smoke results.
8. Record production impact.
9. Record PR number.
10. Record task commit(s).
11. Record merge commit.
12. Record findings/risks.
13. Record what the sprint enabled next.
14. Update Current State.
15. Update planned sprint roadmap.
16. Move completed rails from Planned → Verified when appropriate.
17. Update the Executive Current State table (branch heads, latest sprint, test baseline, open PRs, cutover status).
18. Reconcile the Active Findings register and Decision Register.
19. If a planned sprint changed scope/order, update the provisional roadmap without rewriting older sprint history.

Never mark planned work as completed before it is actually merged and verified.

---

# Current Immediate Next Actions

1. ~~Run Sprint 08 to formalize the v1.1.0-beta scope/readiness register.~~ Done and merged (PR #10, `dddbb5f`) — `V1_1_RELEASE_READINESS.md` is operative, both Sprint 08 decisions ratified.
2. ~~Begin Sprint 09 — Account Lifecycle & Settings.~~ Done and merged (PR #12 `02958f2`, PR #13 `b19a56a`) — Rail A Verified.
2a. ~~Land Sprint 10 — Inventory Ingestion Safety.~~ **MERGED** (PR #14 → `b389072`, CI green on merged head; smoke passed pre-merge). Sprint state: **Implementation Paused — Awaiting Vendor Evidence** — the real Keyper Event contract (discovery item, §6.2) is the trigger to close it and complete Rail D's exit-4 Keyper half. Rail D NOT Verified until then.
2b. Sprint 11 (Observability & Structured Logging) starts only on explicit owner initiation — not begun (owner directive at the Sprint 10 gate).
3. Complete dealership vendor research before committing automatic email/API ingestion to the release (answers targeted before Sprint 12 planning).
4. Continue feature and production-readiness work only through task branch → PR → `dev`.
5. Keep real production frozen on `v1.0.0-beta.6`.
6. Do not schedule the real production cutover until the candidate is frozen, `/release-readiness` passes, and any changes that affect migration assumptions receive a targeted rehearsal refresh.

---

# Long-Term Principle

DealerDOH does not need defenses for systems that do not exist yet.

It does need:

> Every attack surface and workflow that currently exists to be deliberately secured, tested, observable, recoverable, and documented.

And every future capability should have a documented trigger telling the team when its corresponding security, reliability, legal, privacy, accessibility, or architectural controls become mandatory.

The purpose of this document is not to prove that DealerDOH is finished. It is to make the product's history, present state, known risks, release gates, and future obligations legible enough that neither a human nor an AI agent has to rediscover them from scratch.

