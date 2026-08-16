# DealerDOH — Rolling Sprint History & Release Readiness

**Document Version:** 0.1  
**Last Updated:** August 16, 2026  
**Status:** Living Document  
**Repository File:** `SPRINT_HISTORY.md`

---

# Purpose

This document is the chronological engineering and product-development record for DealerDOH.

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

# Sprint 01 — Production Baseline & Git Foundation

**Status:** Complete

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

## Result

LotSync production became formally:

**STABLE / LOCKED**

Normal development moved to `dev`.

---

# Sprint 01.5 — Backup & CI Foundation

**Status:** Complete

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

## Result

DealerDOH development gained:

- verified recovery evidence
- automatic test/build gates
- a safer integration branch

---

# Process Milestone — DealerDOH Agent Development Procedures

**Status:** Complete

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

## Result

DealerDOH's development methodology became version-controlled institutional knowledge.

The task prompt now describes **what** to build.

DealerDOH process skills describe **how** the work must be performed.

---

# Sprint 02 — DealerDOH Development Environment Foundation

**Status:** Complete

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

## Result

DealerDOH gained a persistent integrated development environment completely separated from production.

---

# Sprint 03 — DEV SQLite → Supabase PostgreSQL Migration

**Status:** Complete

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

## Result

DealerDOH DEV moved to the intended future database architecture while production remained untouched on SQLite.

---

# Sprint 04 — Deterministic Synthetic QA Dealership

**Status:** Complete

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

## Result

DealerDOH DEV became a standing automated QA dealership instead of a simple demo environment.

---

# Sprint 05 — Supabase Auth, Users, Roles & Store Boundaries

**Status:** Complete

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

## Result

DealerDOH DEV became a real authenticated application with server-enforced membership/store authorization.

---

# Sprint 06 — Production Migration Planning & Cutover Runbook

**Status:** Complete

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

## Result

Production migration became a documented release operation rather than an improvised infrastructure change.

---

# Sprint 07 — Production Migration Rehearsal & Rollback Drill

**Status:** Complete

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

## Result

The migration rail is proven and can remain parked while v1.1.0-beta feature development continues.

---

# Sprint 08 — v1.1.0-beta.1 Scope & Release Readiness Register

**Status:** In Progress — Awaiting Merge

## Objective

Turn `v1.1.0-beta.1` from a collection of ideas into a controlled release contract: every proposed capability classified REQUIRED / CONDITIONAL / POST-v1.1, every REQUIRED rail given an owner sprint, purpose, addressed risk, exact exit conditions, required evidence, and a release-blocking status — plus the recommended Sprint 09+ execution order and explicit scope-discipline rules.

## Starting State

- `dev` = `51d59f9` (Sprint 07 merge), `master` locked at `v1.0.0-beta.6` / `13c4f815`
- CI green on the `dev` head; DEV and production endpoints healthy (read-only checks)
- This document (`SPRINT_HISTORY.md`) was found owner-staged locally but not yet committed — landed in-repo as this sprint's first commit, together with owner-staged reality corrections (stale smoke-test workflow note; `dealerdoh.com` now owned; status pointer)

## Major Work

Created **`V1_1_RELEASE_READINESS.md`** — the authoritative release contract for `v1.1.0-beta.1`:

- Readiness register: 13 rails + the production-migration rail, each with priority, status, planned sprint, blocking status, exit-condition summary, and required evidence
- Full exit criteria for every REQUIRED rail (A Account Lifecycle, B Onboarding/Help, C Role-Aware Presentation, D Ingestion Safety, F Observability, G Structured Logging, H Security Hardening, I Supply Chain, J Performance, K Accessibility blocking subset, L Privacy/Legal internal-beta subset, M Human UAT)
- **Sprint 08 decision:** Notifications (this document's Rail D / the spec's Rail E) classified **CONDITIONAL**, not REQUIRED — v1.1 ingestion is manual-upload-only, so sync outcomes are visible at the point of action; the rail auto-promotes if automated ingestion enters v1.1, if UAT shows users missing critical conditions, or by owner decision. Presented for owner ratification at this sprint's PR gate
- Automated Report Ingestion held CONDITIONAL behind the vendor-discovery checklist (owner action; answers targeted before Sprint 12 planning)
- Scope-discipline rules (five narrow admission criteria after Sprint 08), evidence rules (what "done" means per change class), back-burner trigger register, and the known-findings register with per-item blocking status
- **Recommended order (changed from provisional):** 09 Account → 10 Ingestion Safety → **11 Observability + Logging (moved up from 13)** → 12 Role-Aware UX + Onboarding → (12.5 Notifications only if triggered) → 13 Security + Supply Chain (folded) → 14 Performance + Accessibility → 15 Privacy/Legal → 16 Human UAT → 17 RC Freeze — nine sprints to RC instead of ten, with instrumentation in place before the big UX build and before UAT

Note: rail letters in `V1_1_RELEASE_READINESS.md` follow the Sprint 08 specification and diverge from this document's older catalog from D onward (mapping recorded in the register). The register is operative; this document's rails section remains historical context.

## Production Impact

None. Planning/documentation only. No production Supabase, no cutover scheduling, no user or DNS changes.

## PR

Recorded at merge time per the rolling-update procedure.

---

# Current v1.1.0-beta Goal

The first DealerDOH-era production release is expected to become:

**`v1.1.0-beta.1`**

rather than immediately cutting production over after Sprint 07.

Production remains:

**LotSync `v1.0.0-beta.6`**

while additional release features and production-readiness rails are developed in `dev`.

---

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

---

# Proposed v1.1.0-beta Sprint Roadmap

> **Superseded for scope and order (Sprint 08):**
> [`V1_1_RELEASE_READINESS.md`](V1_1_RELEASE_READINESS.md) is now the
> operative release contract — classifications, exit criteria,
> evidence rules, and the recommended Sprint 09–17 sequence live
> there. The roadmap below is retained as historical context per this
> document's no-rewrite rule.

This roadmap remains adjustable.

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

Never mark planned work as completed before it is actually merged and verified.

---

# Current Immediate Next Actions

1. ~~Establish the formal v1.1.0-beta release/readiness register.~~ Done pending merge — `V1_1_RELEASE_READINESS.md` (Sprint 08).
2. Owner: ratify the Sprint 08 classifications at the PR gate (especially Notifications → CONDITIONAL) and start the vendor-discovery checklist for automated ingestion.
3. Begin Sprint 09 — Account Lifecycle & Settings — when explicitly initiated.
4. Continue feature and production-readiness sprints on `dev`.
5. Keep real production frozen on `v1.0.0-beta.6`.
6. Do not schedule the real production cutover until the release candidate is frozen and `/release-readiness` passes.

---

# Long-Term Principle

DealerDOH does not need defenses for systems that do not exist yet.

It does need:

> Every attack surface and workflow that currently exists to be deliberately secured, tested, observable, recoverable, and documented.

And every future capability should have a documented trigger telling the team when its corresponding security, reliability, legal, or architectural controls become mandatory.

