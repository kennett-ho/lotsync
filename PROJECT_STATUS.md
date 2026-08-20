# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against. See
[`SPRINT_HISTORY.md`](SPRINT_HISTORY.md) for the chronological
DealerDOH infrastructure history and v1.1.0-beta release roadmap.

**Last updated:** 2026-08-20 (Sprint 15 at the PR approval gate — Rail L **Implementation Complete — Awaiting Merge**; `PRIVACY_ARCHITECTURE.md` + `DATA_RETENTION.md` + `LEGAL_READINESS.md` canonical; owner decisions D1–D10 **resolved**, five customer-facing drafts decision-complete and unpublished pending D2/D5 execution)

## ⚠️ Production is live and locked (2026-08-15)

LotSync is in real production use by dealership management.
Production is **`v1.0.0-beta.6`** (commit `13c4f815`, branch
`master`), deployed on Render (`lotsync-api`, FastAPI + SQLite on a
persistent disk) and Vercel (Vite frontend). The verified baseline —
version, hosting, database location, migration state, test/build
status, verified backup record and procedure, and lock rules — lives in
[`PRODUCTION_BASELINE.md`](PRODUCTION_BASELINE.md).

**New workflow as of this sprint:** normal development no longer
happens on `master`. Both Render and Vercel auto-deploy every push to
`master`, so a push there *is* a production deployment. Work flows
`feature/*` / `fix/*` → `dev` → QA → release train → `master`. The
`dev` branch was created this sprint from exactly the production
commit (`13c4f815`). Branch protection on `master` is not available on
the current GitHub plan (private repo, Free tier) — the lock is
procedural; see `PRODUCTION_BASELINE.md`.

**Infrastructure Sprint 01.5:** the first production database backup
was created with SQLite's online-backup API, downloaded off Render, and
re-verified locally by integrity check, schema version, row count, size,
and SHA-256. `.github/workflows/ci.yml` adds the same proven backend
suite and frontend production build as independent checks on every push
and pull request. Neither operation changed deployed application code or
the live production database.

**Infrastructure Sprint 02:** the first fully isolated DealerDOH
development environment exists — dev frontend
(`dealerdoh-dev.vercel.app`, permanent "DealerDOH DEV" banner), dev API
(`dealerdoh-api-dev.onrender.com`, ephemeral synthetic-seeded SQLite,
`/health` reports `environment=development`), and a dev-only Supabase
project (`dealerdoh-dev`, Postgres + Auth provisioned; app integration
deferred to Sprints 03/05). Production was not touched; no production
credential, path, or dataset exists anywhere in the dev stack. See
[`DEV_ENVIRONMENT.md`](DEV_ENVIRONMENT.md) for URLs, branch mappings,
seed/reset procedure, and the verified isolation guarantees.

**Infrastructure Sprint 03:** DealerDOH DEV now runs the real
application against **Supabase PostgreSQL** — dual-engine persistence
behind explicit `DATABASE_ENGINE` config (`database/engine.py` +
PostgreSQL dialect migrations), with the full behavioral suite green
on BOTH engines (402/402 SQLite, 402/402 PostgreSQL with one
documented engine-specific skip) in CI via a disposable postgres
service container, byte-identical CSV reports and row-identical
behavioral projections across engines from the same synthetic
fixtures. **Production is untouched and stays on SQLite** — the
engine split is intentional and temporary until production's own
migration sprint. See [`DEV_ENVIRONMENT.md`](DEV_ENVIRONMENT.md).

**Infrastructure Sprint 04:** DealerDOH DEV is now a deliberate **QA
dealership**, not a demo dataset — 34 synthetic vehicles
(`dev_seed/`), each exercising a specific implemented operational
rule, replayed as two deterministic sync days through the real
pipeline path and pinned to a fixed reference date (2026-07-21) so
expected outcomes never decay. Standing state: 98 events, 18 tasks
(16 open / 1 honored / 1 moot), 2 recommendations, 3 pending
identities, 10 sync runs. The scenario roster is governed by
[`SYNTHETIC_QA_MATRIX.md`](SYNTHETIC_QA_MATRIX.md), enforced
scenario-by-scenario by `tests/test_qa_dataset.py` on **both** engines
in the existing CI jobs (428/428 SQLite, 428/428 PostgreSQL, one
documented skip), and documented for humans in
[`DEV_QA_GUIDE.md`](DEV_QA_GUIDE.md). Production untouched.

**Infrastructure Sprint 05:** DealerDOH DEV has its first real
**authentication and authorization boundary** — Supabase Auth
(email/password, synthetic `.example` users only) issues ES256 JWTs
that FastAPI independently verifies against the project JWKS, then
authorizes against the new access model
(`organization → dealership → user_membership → role`, migration
0009 — executing DATA_MODEL.md's "Dealership gains a parent"
resolution). Server-side only: role and store come from the
membership row, never from the client; cross-store access is denied
and proven (a Store-B-only manager gets 403). One role restriction
exists (sync run = admin/manager); reads stay shared. RLS assessed
and deferred with documented conditions. `AUTH_MODE=disabled` is the
default — **production behavior is byte-for-byte unchanged** and the
suites prove it (454/454 SQLite, 454/454 PostgreSQL incl. 25 new auth
tests minting local ES256 tokens — no live Supabase in CI). See
[`AUTH_ARCHITECTURE.md`](AUTH_ARCHITECTURE.md).

**Infrastructure Sprint 06:** the production migration is now
**planned, not executed** — production remains LotSync
`v1.0.0-beta.6` on SQLite with no auth, untouched. The sprint
produced the full cutover playbook:
[`PRODUCTION_MIGRATION_PLAN.md`](PRODUCTION_MIGRATION_PLAN.md)
(strategy: short maintenance window; four separate releases — A: code,
B: database, C: auth, D: rebrand/domain — each with its own approval
gate, smoke, and rollback; nine explicit operator approval gates
G1–G9) and
[`PRODUCTION_MIGRATION_RUNBOOK.md`](PRODUCTION_MIGRATION_RUNBOOK.md)
(the numbered operator checklist). The production data inventory was
taken **read-only from the verified 2026-08-15 backup** (hash
re-verified): 4,672 vehicles, 8,876 events, 362 tasks, 14,606 business
rows, 4.02 MiB, integrity ok, zero orphans — production itself was
never touched. Prerequisite before any execution: a Sprint 07
rehearsal that builds and proves the migration tool end-to-end,
including a deliberate rollback drill.

**Infrastructure Sprint 07:** the Sprint 06 playbook was **rehearsed
end-to-end and passed** — against disposable local infrastructure
only (portable PostgreSQL 17.5; production untouched, standing dev
untouched and unreachable from the rehearsal). Built and committed:
`tools/migrate_sqlite_to_postgres.py` (defensive operator migration
tool: dry-run default, FK-safe verbatim-ID copy, sequence reset to
the sqlite high-water, four-layer exact validation, refusal
safeguards), `tools/generate_rehearsal_dataset.py` (deterministic
production-shaped synthetic SQLite — 4,700 vehicles / 14,665 business
rows incl. sparse-sequence and FK edge cases), and
`tools/behavior_compare.py` (cross-engine behavioral validation via
the app's own query layer — 22/22 identical). Executed: timed backup
→ freeze → migration (0.98 s at full scale, validation all-green) →
Release B env flip (healthy on PostgreSQL in ~18 s) → Release C auth
flip (full 401/403/role/store matrix green) → simulated first
PostgreSQL write (delta captured: 1 sync run, 3 events, 2 tasks
honored) → **pre-write rollback drill (19.4 s, zero loss proven
logically)** → post-write replay recovery (converged to identical
rows and IDs) → five failure injections (all failed closed; two real
tool defects found and fixed: missing connect timeout, prompt EOF
crash). Tests now **464/464 on both engines** (+10 migration-tool
tests in the PostgreSQL CI job; no CI workflow changes). Verdict:
**GO — technically ready to schedule**, pending the plan §22 owner
decisions and G1 provisioning. Full evidence:
[`PRODUCTION_MIGRATION_REHEARSAL.md`](PRODUCTION_MIGRATION_REHEARSAL.md).
Production remains LotSync `v1.0.0-beta.6`, untouched.

**Infrastructure Sprint 08:** `v1.1.0-beta.1` now has a **release
contract** —
[`V1_1_RELEASE_READINESS.md`](V1_1_RELEASE_READINESS.md): 13 rails +
the production-migration rail classified REQUIRED / CONDITIONAL /
POST-v1.1, each REQUIRED rail with owner sprint, purpose, addressed
risk, exact exit conditions, required evidence, and blocking status;
scope-discipline and evidence rules; back-burner trigger register;
known-findings register. Sprint 08 decisions (**both ratified by the owner 2026-08-16**, who
also adjusted scope: SPA deep-link routing → REQUIRED under the
account-lifecycle rail; sidebar-dismissal and sold-vehicle-browse
non-blocking unless UAT shows otherwise): **Notifications
reclassified CONDITIONAL** (manual-upload v1.1 shows sync outcomes at
the point of action; auto-promotes with automated ingestion or UAT
evidence);
**observability moved ahead of the UX build** (Sprint 11) so the
tutorial/help/sync surfaces ship instrumented and UAT runs observed;
supply-chain folded into the security sprint — nine sprints to RC
freeze (09 Account → 10 Ingestion → 11 Observability → 12 Role-UX/
Onboarding → 13 Security → 14 Perf+A11y → 15 Legal → 16 UAT → 17 RC).
This sprint also landed the owner-staged
[`SPRINT_HISTORY.md`](SPRINT_HISTORY.md) (rolling sprint history)
plus small reality corrections (stale smoke-test workflow note;
`dealerdoh.com` now owned). Planning only — no rail implementation,
production untouched.

**Sprint 15 (2026-08-20, PR gate):** Privacy, Data Governance &
Legal Readiness (Rail L) on branch `feature/sprint-15-privacy-legal`
from `dev` = `daf5ae0`. Audit-FIRST: full data inventory over the 13
real tables and every persist path, **verified consumer-data
boundary (no customer/consumer personal information ingested
anywhere — with the raw-upload caveat recorded)**, workforce-data
reality (no structured person names until the planned Sprint 17
Keyper contract; incidental vendor free-text = accepted audit F2),
browser-storage census **measured on deployed DEV** (one Supabase
session key + PostHog persistence + exactly one cookie — see
remediation), deployed-bundle telemetry-flag byte-check, honest
platform-layer IP/device-metadata statement, upload/output/file
lifecycle (the `/run` raw-upload indefinite-retention finding →
owner decision D4 — **owner-directed 2026-08-20: resolve before the
v1.1 release, never an indefinite default**; **no deletion behavior
changed**), backups, and an internal incident-response procedure.
Legal assessment from authoritative sources with per-area
classifications (FTC §5 Applicable; A.R.S. 18-551/552 incident
frame; Arizona has no enacted comprehensive consumer privacy law —
SB 1815 introduced 2026, not enacted; **GLBA/Safeguards stated
carefully and non-categorically: the intended/validated flows do
not appear to involve Safeguards customer information and DealerDOH
does not currently appear to act as a Safeguards service provider —
retained raw uploads keep incidental receipt a live
data-minimization risk, and the reassessment trigger covers
receiving, retaining, maintaining, processing, or being permitted
access to customer information**; CCPA/state/GDPR/COPPA classified) + owner decision
register **D1–D10** + counsel register **C1–C8**
(`LEGAL_READINESS.md`). New canonical docs `PRIVACY_ARCHITECTURE.md`
+ `DATA_RETENTION.md`; five customer-facing **drafts** (Privacy
Policy, Beta Terms, Accessibility Statement, Security Overview,
Subprocessors) — all "Draft — Owner Review Required", zero invented
facts, placeholders where owner input is genuinely required. One
evidence-backed remediation: PostHog `persistence: 'localStorage'` —
**DealerDOH now sets no cookies at all** (the SDK default had set
the app's only cookie; measured live, test-pinned). Suites 712/712
BOTH engines on the branch; frontend build clean; QA dataset
untouched (read-only checks); production untouched and verified
healthy. **Owner decisions D1–D10 RESOLVED at the gate
(2026-08-20)**: identity "DealerDOH, operated by Kennett Ho";
monitored dealerdoh.com contact created before publication;
U.S.-only/Arizona beta; raw uploads = temporary evidence with a
concrete 7-day-accepted/30-day-rejected retention proposal awaiting
ratification (**no destructive cleanup until approved;
release-gating**); publication on dealerdoh.com before the v1.1
production cutover, never on current LotSync production;
notice-only acceptance; customer-neutral public copy; provider
claims verified pre-publication (manual release-readiness actions);
**honest D9 disposition — no attorney review completed for the
beta, qualified review recommended/required before commercial GA**;
paid-Supabase as a verified-benefits readiness decision. **Rail L:
Implementation Complete — Awaiting Merge** — Verified now waits on
execution only (merge + merged-head CI, then D2 mailbox +
owner-approved final text + D5 pre-cutover publication). Rail D /
Sprint 10 / Sprint 17 states untouched.

**Sprint 14 (2026-08-20, merged + Complete):** **MERGED** (PR #23 →
`dev` = `c916208`, CI green on the merged head including the new
bundle-budget gate; sprint branch deleted). Both DEV services
restored to `dev` and verified serving the merge SHA (Vercel
auto-deployed on the Production-Branch push). **Merged-head
both-role smoke PASSED** — one `/dashboard` per role landing, 169 kB
initial wire, deferred PostHog + Sentry live with zero console/CSP
violations, first-Tab skip link on both roles' authenticated loads,
onboarding/drawer/Vehicle-Detail focus cycles, keyboard-operable
uploads with a live zero-mutation validate-only announcement, QA
search responsive with caps dormant, keyboard work-order both roles,
phone/640 px flows clean, signature 5.27:1 / badge 6.92:1, QA
dealership exactly intact (28-of-28 · 16 open · 58.82%) with zero
mutations, production untouched. **Rails J + K: Verified. Sprint 14
Complete.** Originally recorded at the PR gate as:**
Performance, Resilience & Accessibility (Rails J + K) on branch
`feature/sprint-14-performance-accessibility` from `dev` = `73dee99`.
Measure-first audit at QA scale AND the 4,700-vehicle production
shape, then only evidence-backed fixes, then re-measurement —
canonical records in **`PERFORMANCE.md`** and **`ACCESSIBILITY.md`**.
Performance: hot-path `sync_run` reads bounded in SQL (no migration;
semantics pinned), the live-verified duplicate `/dashboard` fetch
collapsed to one shared per-view request, PostHog deferred off the
critical path + role-gated surfaces code-split (initial JS **885→592
kB raw / 256→167 kB gzip, −35%**; production-posture builds never
fetch the PostHog chunk), bounded list/timeline rendering with
truthful "Show all/older" escapes (production-scale keystroke blocks
**400–850 ms → 27–74 ms**; 131k-DOM-node Sold paint bounded), 30 s
request timeouts; validation benchmark re-measured 0.033 s / 4,700
rows (no Sprint 11/13 regression); Render cold start measured and
separated (32.3 s platform wake vs ~3 ms warm server-side — not an
application defect). Accessibility: four-pass audit → full
remediation → **axe zero violations** on Overview/Vehicles/Tasks/
Vehicle Detail/Inventory Sync at desktop + mobile (was: unnamed dead
buttons ×5 critical, keyboard-locked file uploads, hidden-focusable
drawer controls, clickable-div rows, missing landmarks/headings,
color-only status, sub-AA contrast on informative text). Inert
drawer + full focus cycle, modal onboarding (containment, Escape=Skip,
step announcements — Sprint 12 clamp intact), announced outcomes,
labeled controls, skip link, per-surface titles/h1s, aria-current/
expanded/pressed/sort, AA contrast sweep (canvas-measured against the
Tailwind v4 oklch palette), reduced-motion, :focus-visible, 375/640 px
reflow with zero horizontal scroll. **No formal WCAG conformance
claimed** — remediated toward WCAG 2.2 AA-quality behavior; SR-user
study is a Rail M UAT risk. Guards in CI: bundle-budget gate
(`tools/check_bundle_budget.py`) + 51 structural tests. **708/708
SQLite · 708/708 PostgreSQL · build green.** Production untouched;
production-posture invariant verified byte-identical (54 pre-existing
pin tests). Rails J/K become Verified only after merge + merged-head
CI + deployed remeasure/keyboard/mobile/zoom smoke. Rail D and Sprint
17 untouched. Recommended next: Sprint 15 — Privacy / Legal.

**Sprint 13 (2026-08-19, merged + Complete same day):** Security
Hardening + Supply Chain (Rails H + I + §5.H.1 sanitation) —
**MERGED** (PR #21 → `dev` = `6bb3a9c`, CI green on the merged head
**including the new Security scans job**; sprint branch deleted).
Read-only audit → remediation → re-audit, canonical in
`SECURITY_ARCHITECTURE.md` + `SECURITY_AUDIT.md`. **0 Critical, 0
reachable High.** Remediated: security headers (API middleware +
`vercel.json` CSP), fail-closed destructive-seed guard, production
API-docs gating, ReportLab markup escaping, self-set `display_name`
clamp, login-error genericization. **Merged-head deployed security
smoke PASSED** on both DEV services auto-deployed from `dev` (headers
live on 200/404, CORS allow/deny + request-id exposure, live
`signup_disabled` probe, manager surfaces + roster restrictions under
CSP, work-order PDF, validate-only upload matrix with zero mutation,
Sentry zero-noise across the 4xx probe window, QA dealership intact —
no reseed; the fail-closed seed guard exercised non-destructively all
four ways; production docs gating subprocess-proven). The smoke found
one Low: the CSP blocked the Google Fonts `@import` (cosmetic
fallback) — fixed in the closeout PR with a pinning test.
**Rails H + I: Verified. Sprint 13 Complete. Repository sanitation:
Audit Clean** — full-history scan (685 blobs) found no secret ever
committed; no rotation, no history rewrite, repository stays PRIVATE
(publication remains a separate owner decision; the Mark Kia
customer-identity disclosure is recorded as an owner consideration).
Rail I: npm production deps clean, `pip-audit` clean, `nanoid` High =
build-only devDependency exception; CI `security` job live. Deferred
with rationale: rate limiting, RLS/Store #2 scoping, source-map
upload, CSV formula escaping. 656/656 SQLite · 656/656 PostgreSQL
(+31 security tests) · build green. Production untouched (`master` =
`13c4f815`/`v1.0.0-beta.6`); Sprint 10 Paused, Rail D NOT Verified,
Sprint 17 Planned — none touched. Next: Sprint 14 — Performance +
Accessibility on explicit owner go.

**Sprint 12 (2026-08-19, merged + Complete same day):** **MERGED**
(PR #19 → `dev` = `bafd747`, CI green on the merged head; sprint
branch deleted). Merged-head both-role verification PASSED on DEV
services restored to `dev`: Manager (Overview, Help with sync
section, persistence) and Lot Staff (Today's Work, no-sync nav,
dismissal, Sold, work order, live 403 with request-id); six analytics
events stamped with the merge SHA, zero PII, autocapture/pageview
still zero; Sentry clean; QA intact, no reseed.
**Rails B + C: Verified. Sprint 12 Complete.** Next: Sprint 13 —
Security + Supply Chain on explicit owner go. Original sprint
summary follows —
Rails B+C — Role-Aware UX, Onboarding & Contextual Help on
`feature/sprint-12-role-aware-ux` (`ROLE_AWARE_UX.md` canonical).
Server-confirmed-role navigation and landing: manager/admin →
Overview; lot_staff → Today's Work (execution-first over the
unchanged task engine, evidence-freshness line, no Inventory Sync nav
where every action 403s); sales_manager shared-honest. Role-aware
Getting Started tour (Supabase `user_metadata`, no migration; skip =
completion; replay from role-gated Help). Audit honesty fixes: dead
My Tasks/emp-0142 removed, VIN-only search truth, promoted
sidebar-dismissal defect fixed, nine dead controls removed, exception
codes translated, minimal Sold filter. AUTH-disabled production shape
byte-identical (test-pinned, verified locally + deployed). 624/624
SQLite · 624/624 PostgreSQL · 37 posture tests · build green.
Deployed both-role smoke passed on the review window; the smoke
found+fixed a rapid-click onboarding crash (captured live by the
Sprint 11 boundary+Sentry — Rails F/G proven on a real failure).
**Rails B+C: Implementation Complete — Awaiting Merge.** Rail D and
Sprint 17 scope untouched.

**Sprint 11 (2026-08-17, merged + Complete 2026-08-18):** Rails F+G —
Observability & Structured Logging — **MERGED** (PR #16 → `dev` =
`5ae6c79`, CI green on the merged head; sprint branch deleted).
Three-layer model (structured JSON logs / Sentry / PostHog —
`OBSERVABILITY.md` canonical), `X-Request-ID` correlation through
logs→SyncRun→Sentry, env/release identity, central redaction, React
Error Boundary, explicit-events-only analytics with internal-id
identity. All layers no-op unconfigured; 588/588 SQLite · 588/588
PostgreSQL. The DEV-only verification trigger route was removed
pre-merge (owner direction) after its evidence was recorded — the
permanent app ships no raising endpoint; capture verification is
offline (fake transport). Post-merge verification PASSED on both DEV
services redeployed from `dev` (serving-revision proof, fresh log
correlation, Sentry receipt with clean payload, explicit-only
PostHog events, signup disabled, QA dataset intact — no reseed).
**Rails F+G: Verified. Sprint 11 Complete.** Rail D untouched. Next:
Sprint 12 (Role-Aware UX + Onboarding) on explicit owner go.

**Post-Sprint-11 release-planning amendment (2026-08-18):** owner
discovery confirmed scheduled Keyper **All Vehicles / Full Inventory**
delivery and explicitly opted that bounded adapter into v1.1. The
release train now adds **Sprint 17 — Vendor Integration & Automated
Evidence Acquisition** (status **Planned**, not started) and moves the
existing RC Freeze to **Sprint 18 — Release Candidate Freeze / Release
Readiness**. The adapter must reuse Sprint 10 classification,
validation, fingerprinting, suspicious-count, HOLD, and reconciliation
safeguards; email is transport only. Other vendor automation, Keyper
Event ingestion, and unrelated work remain outside Sprint 17. Plan of
record: [`KEYPER_AUTOMATED_INTEGRATION_PLAN.md`](KEYPER_AUTOMATED_INTEGRATION_PLAN.md).

Notifications remains **CONDITIONAL**. After Sprint 17 implementation /
during Sprint 18 readiness, the release must record whether real
non-arrival, acquisition-failure, ERROR, WARNING/HOLD, stale-source, or
repeated-failure behavior requires a minimal in-app notification
surface. Sprint 10 remains **Implementation Paused — Awaiting Vendor
Evidence** and Rail D remains **Merged — NOT Verified; Awaiting Vendor
Evidence**; the real Keyper Event-vs-Full distinction still requires
vendor evidence before unattended Keyper activation/verification.
Planning/documentation only; no production impact.

**Sprint 10 (2026-08-16, merged 2026-08-17):** Rail D — Inventory
Ingestion Safety — is **MERGED** (PR #14 → `b389072`, owner-approved,
CI green on the merged head; deployed-DEV smoke passed pre-merge on
the branch review window). Sprint state: **Implementation Paused —
Awaiting Vendor Evidence** — Rail D is deliberately NOT Verified; the
real Keyper Event-vs-Full structural distinction awaits the vendor
format (§6.2 discovery), which is the un-pause trigger.
DealerDOH no longer trusts a spreadsheet merely because it can parse
it: every upload is deterministically classified by content
(slot/filename/MIME are hints, not identity), validated against its
report contract, checked for dangerous incompleteness, previewed
before mutation, and revalidated server-side at execution
([`INGESTION_ARCHITECTURE.md`](INGESTION_ARCHITECTURE.md) is
canonical). Empty/headers-only authoritative snapshots hard-reject;
wrong report types are named and blocked. Keyper: the Full Inventory
contract works and nonmatching Keyper-shaped evidence fails safely —
but the *real* Event-vs-Full structural distinction is **PENDING
VENDOR EVIDENCE** (no Event sample exists; **zero invented schema**;
owner-corrected status — post-merge sprint state: Implementation
Paused — Awaiting Vendor Evidence). Suspicious count changes vs the
scoped comparable baseline (`report_baseline`, migration 0010, both
engines) force explicit review — thresholds **owner-ratified
2026-08-16** as initial beta policy (drop >15% & ≥10 rows; increase
>50% & ≥25 rows), warning/review only, subject to tuning from real
operational evidence. Warning acknowledgement is fingerprint-bound to the
exact uploaded bytes, so skipping the preview, swapping files, or
asserting acknowledgement blind all fail closed with **zero
operational mutation** (API-test-pinned). Suites **548/548 both
engines** locally (+60 ingestion/authz/adversarial tests; standing
QA dealership untouched); production-scale validation measured
~40 ms/4,700 rows. Production untouched.

**Sprint 09 (2026-08-16):** Rail A — Account Lifecycle — is
**COMPLETE and Verified** (PR #12 merged as `02958f2`; CI green on the
merged head; post-merge smoke on dev-tracking DEV re-passed the full
matrix incl. the real emailed recovery loop, a live `signup_disabled`
probe, and a clean deployed-bundle secret scan — the first REQUIRED
rail of `v1.1.0-beta.1` is done). As implemented: manager/admin user provisioning
(no public signup; GoTrue invite flow; role policy server-enforced),
enumeration-safe password recovery over a real `/auth/reset-password`
direct link (Vercel SPA rewrite — the ratified Rail A requirement),
membership-based instant offboarding (same valid JWT → 403 next
request, proven by test), a Profile & Settings surface with **zero
decorative controls** (the prior page was entirely fake — disposition
table in [`ACCOUNT_LIFECYCLE.md`](ACCOUNT_LIFECYCLE.md)), and
post-reset global session revocation. Suites **488/488 both engines**
(+24 authorization-matrix tests). No schema change; production
untouched. *(An earlier revision of this entry said deployed smoke was
still pending — it passed on the merged head the same day, incl. the
live emailed recovery loop; Rail A is Verified, per the register and
PR #13.)*

**Pre-Sprint-09 governance update (2026-08-16):** Sprint 13's
Security + Supply Chain scope now includes **Repository
Public-Release Sanitation** (`V1_1_RELEASE_READINESS.md` §5.H.1) — a
read-only full-Git-history secret audit plus rotation/cleanup rules
that gate any future private → public repository change. Current
state: **Not Audited**; blocks repository publication only, not
v1.1. Same task reconciled the owner's expanded SPRINT_HISTORY.md
v0.2 with the merged Sprint 08 record.

**Staleness note:** the sections below this one were last brought
current at v0.7.4 (2026-08-03). Releases v0.8.0 → v1.0.0-beta.6
(pre-deployment hardening, deployment readiness, the six beta
releases, and deployment itself) are recorded in their git tag
messages and `DEPLOYMENT.md`, not yet backfilled here or in
`CHANGELOG.md` — a known gap, listed in
`PRODUCTION_BASELINE.md`'s Discrepancies. The backend test count is
**385/385** as of the baseline (the 328 below was correct at v0.7.4).

## Current position

| | |
|---|---|
| **Phase** | Phase 3 — Web application — **Sprint 3.8 done, product identity and governing docs realigned around lot staff as primary user** (Phase 2 remains complete underneath it; no code changed this sprint) |
| **Sprint** | Sprint 3.8 (v0.7.4) — Product Alignment (done) |
| **Scope note** | Governance-only sprint. `PRODUCT.md`'s "Users and stakeholders" rewritten (lot staff as primary user, others as contributors, "lot staff wins" tiebreaker), new "confirmed dealership policy is context, not enforcement logic" principle, "Explicit boundaries" split into Permanent product boundaries vs. Deferred technical scope, new Beta Vision (v1.0) section. `VISION.md` gained a matching Principle. `FRONTEND_BACKEND_RECONCILIATION.md` fully re-dispositioned (Keep/Revise/Remove/Discuss) against a new four-object product grammar (Vehicle, Task, Recommendation, Event/Timeline) and its two ingestion mechanisms (Sync, Quick Log) — no schema, API, or frontend code touched. See `CHANGELOG.md`'s v0.7.4 entry for the full account. |
| **Last completed** | Sprint 3.8 — `PRODUCT.md`, `VISION.md`, `FRONTEND_BACKEND_RECONCILIATION.md` rewritten; `CHANGELOG.md`/this file updated; no code, schema, or test changes |

## Completed slices

| Slice | Sprint | Summary | Review |
|---|---|---|---|
| 1 — SQLite foundation, Keyper write path | 1 | `vehicle`/`event` tables live; Keyper's pass persists to both, additively, with zero CSV output change | [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) |
| 2 — Full source coverage + `PendingIdentity` capture | 2 | All 5 sources (Tekion, Sold, MDD, RecovR, RapidRecon) persist their contribution; Keyper's unresolved-identity population captured via the new `PendingIdentity` model instead of being dropped; zero CSV output change | [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) |
| 3 + 4 — Historical diffing, `PendingIdentity` promotion, SyncRun provenance | 3 | Diff-before-write across all four diffed sources, compared against Event history rather than the Vehicle cache (a real bug was found and fixed mid-sprint); `PendingIdentity` → `Vehicle` promotion, the system's first state transition; `SyncRun` table with real per-source transactional semantics (stronger than originally scoped); one documented, accepted idempotency gap for an internally-contradictory upstream Tekion input | [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md) |
| 5 — Task generation | 4 | Pre-Sprint 4 design review reshaped `Task` into `commitment_standing`/`execution_status` (independent axes), a `TaskExecutionEvent` append-only log, and `escalated_from_task_id`. Backend: `generate_install_tasks` (reusing `build_tracker_install_tasks`), Reality-discharge wired into RecovR/Tekion-sold diffs, Intent-discharge (`cancel_task`/`escalate_task`), manual completion assertions coexisting with automatic discharge. Known, documented asymmetry: `install_mdd_beacon` Tasks have no automatic Honored path (MDD never positively confirms). | (no dedicated review file — folded into this dashboard + commit history) |
| 6 — Recommendation engine | 4 | `Recommendation` lifecycle (open/converted_to_task/dismissed), first rule (`key_out_aging`'s most-severe bucket, config-driven not hardcoded), conversion-to-Task as a ratified act, dismissed-reopening logic reusing Slice 3's Event history rather than new tracking fields. | (same as above) |
| 7 — Dashboard data layer | 4 | `queries/dashboard.py`: `connected_systems_status`, `recent_activity_feed`, `task_counts_by_department`, `inventory_health_percentage` — all read-only, no new stored state. Two terms neither `IMPLEMENTATION_PLAN.md` nor `DATA_MODEL.md` precisely defined ("health," "department" grouping) resolved as documented implementation decisions. Performance validated at 3,000 vehicles / 12,000 events — sub-second, no optimization needed yet. | (same as above) |
| Phase 3, Sprint 1 — Employee + Dealership | Phase 3, Sprint 1 | `database/migrations/0006_employee_dealership.sql`; `upsert_dealership`/`get_dealership`, `upsert_employee`/`get_employee` in `database/repository.py`. Real `FOREIGN KEY` from `employee.dealership_id` to `dealership`. Deliberately did not retrofit FKs onto the four existing tables' employee/dealership columns (same precedent as `event.sync_run_id`), and deliberately built no authentication scaffolding — see `PHASE_3_SPRINT_1_REVIEW.md`'s Risks section for both. | [`PHASE_3_SPRINT_1_REVIEW.md`](PHASE_3_SPRINT_1_REVIEW.md) |
| Phase 3, Sprint 2 — Read API Foundation | Phase 3, Sprint 2 | First FastAPI layer: `GET /dashboard`, `/vehicles`, `/vehicles/{vin}` (reference implementation), `/tasks`, `/recommendations`, `/activity`, `/reports`. New `queries/vehicles.py`, `queries/tasks.py`, `queries/recommendations.py`; `recent_activity_feed` extended to embed Vehicle summaries. A real cross-thread SQLite bug caught and fixed (`connect()` now uses `check_same_thread=False`). One `API_CONTRACTS.md` correction (`VehicleSummaryDTO.color` removed — no such backend column). No writes, no auth, frontend untouched. | [`PHASE_3_SPRINT_2_REVIEW.md`](PHASE_3_SPRINT_2_REVIEW.md) |
| Phase 3, Sprint 3 — Frontend Integration | Phase 3, Sprint 3 | New `frontend/src/api/` service layer (typed client + one module per domain + a shared `useApi` loading/error/success hook). Six screens wired to the real API: Vehicle Detail, Vehicles List, Dashboard (Lot Manager), Activity, Recommendations, Tasks. The frontend's collapsed Task `status` field was corrected into `commitment_standing`/`execution_status`, matching the backend's Pre-Sprint 4 design exactly — verified live against a real "surfaced disagreement" case. CORS added to `api/app.py` (transport plumbing, not a contract change). No writes, no auth, no new domain scope. | [`PHASE_3_SPRINT_3_REVIEW.md`](PHASE_3_SPRINT_3_REVIEW.md) |
| Phase 3, Sprint 4 — Real Inventory Sync | Phase 3, Sprint 4 | `sync/pipeline.py` orchestrates an upload-triggered sync over the unmodified reconciliation engine, gracefully degrading across the six upload slots' every partial combination via empty-columned `DataFrame` stand-ins. `POST /inventory-sync/run` (first write route), `GET /inventory-sync/history` (a derived, grouped-by-shared-timestamp read — no new `SyncRun` schema), `GET /inventory-sync/exceptions` (`PendingIdentityDTO`, implemented for the first time). Inventory Sync page rewired to real uploads/data, mockup layout preserved. Two real reconciliation-engine findings surfaced and documented, not silently patched: a `key_out_aging_df` empty-DataFrame `KeyError` (guarded at the call site) and a pre-existing RapidRecon idempotency gap. | [`PHASE_3_SPRINT_4_REVIEW.md`](PHASE_3_SPRINT_4_REVIEW.md) |
| Sprint 3.7 (v0.7.3) — Event Fidelity | Sprint 3.7 | `event.event_time` + `event_freshness` (`migrations/0008`); generic `_insert_event_if_changed` helper closes RapidRecon's missing diff-before-write (this project's own real instance of "repeated observation shouldn't duplicate the Timeline"); `build_tracker_install_tasks` now honors the Wholesale/AT AUCTION RecovR exclusion this project always intended but never actually wired into the live pipeline — verified against the existing, previously-unused correct logic before reuse, not reinvented. Two findings surfaced and confirmed with the product owner before implementing rather than assumed: the Wholesale rule wasn't live anywhere, and Keyper only exposes one confirmed timestamp (Checkout Date, trusted for `Status=Out` only). 12 new regression tests (`tests/test_event_fidelity.py`) plus two existing tests updated because they asserted the exact old, buggy behavior this sprint fixed. | (no dedicated review file — this dashboard + `CHANGELOG.md`'s v0.7.3 entry are the record) |
| Sprint 3.8 (v0.7.4) — Product Alignment | Sprint 3.8 | Governance-only. `PRODUCT.md`/`VISION.md` rewritten around lot staff as primary user, contributors reframed, Permanent/Deferred boundary split, Beta Vision section added. `FRONTEND_BACKEND_RECONCILIATION.md` re-dispositioned in full against a new four-object product grammar (Vehicle, Task, Recommendation, Event/Timeline) — Requests, Vehicle Movement, the Audit Queue, Customer Delivery, and department-specific dashboards removed as permanent-boundary conflicts; Trade-Ins, Transportation, Staged/Incoming Vehicle, Exception handling, and Authentication revised down; Vehicle/Task/Event/Recommendation/SyncRun/Quick Log confirmed already aligned. No schema, API, or frontend code changed; no test count change. | (no dedicated review file — this dashboard + `CHANGELOG.md`'s v0.7.4 entry are the record) |

## Upcoming slices

**Phase 3, Sprint 5 recommendation** (not started; per this project's
standing practice, starting it is a separate, explicit decision — see
`PHASE_3_SPRINT_4_REVIEW.md`'s Section 6 for the full reasoning):
authentication (now overdue across three sprints of recommending it,
and Sprint 4 added this project's first write route with no permission
model behind it), a `GET /employees` endpoint, a lightweight frontend
test setup (Vitest, more pressing now that a real write path exists
with zero automated frontend coverage), and wiring the Lot Manager
dashboard's "Today's Operations" board to the same grouped-Task data
Tasks.tsx already has. (The RapidRecon idempotency gap
`PHASE_3_SPRINT_4_REVIEW.md` Section 3.3 named is no longer on this
list — Sprint 3.7 closed it; see `CHANGELOG.md`'s v0.7.3 entry.) A new
item Sprint 3.7 surfaced but deliberately did not build: the "Verify if
these cars are going to wholesale" dashboard module `ARCHITECTURE.md`
already names for Archive-step (ambiguous) RapidRecon cases — Sprint
3.7 only restored the confident WHOLESALE/AT AUCTION exclusion, not
this separate, still-undesigned module.

## Regression status

- **328 / 328 backend tests passing** (309 at Sprint 4's close → 316
  via v0.7.2's Task/vehicle FK fix and `vehicle.display_name` work →
  328 this sprint: 12 new in `tests/test_event_fidelity.py`, plus two
  existing tests in `test_database_slice3.py`/`test_sync_pipeline.py`
  deliberately rewritten because they asserted the exact old RapidRecon
  behavior this sprint fixed, not left silently broken or silently
  deleted), run via
  `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`
  from the repo root.
- `.github/workflows/ci.yml` runs the 385-test backend suite and the
  frontend production build as independent jobs on every push and pull
  request; the workflow has no deploy or production-data access.
- **Frontend automated test coverage remains zero**, unchanged since
  Sprint 3 — no test runner exists in `frontend/package.json` today.
  This sprint's Timeline/event_time verification was again entirely
  manual, browser-driven, against the real, live 4,312-vehicle
  database. Materially less acceptable now than at Sprint 3's close —
  see `PHASE_3_SPRINT_4_REVIEW.md`'s Recommendation #4.

## Developer tooling (v0.7.1)

Not a Phase 3 slice or sprint — infrastructure alongside the product
work, tracked here for visibility rather than folded into "Completed
slices" above. Does not change Phase/Sprint scope: Phase 3, Sprint 4
above remains the last completed product-scope sprint; Sprint 5
(authentication, etc.) is still not started. See
[`tools/README.md`](tools/README.md) for full detail and
`CHANGELOG.md`'s v0.7.1 entry for the complete list.

A permanent one-command local developer workflow:
`tools/launch.ps1`/`stop.ps1`/`doctor.ps1`/`update.ps1` plus a
double-click `Launch LotSync.bat` entry point. Verifies Python/Node/
npm/git, installs missing backend (`.venv` + new repo-root
`requirements.txt`) and frontend (`npm install`) dependencies, starts
both servers, waits for each to come up, opens the browser. Process
tracking never touches a process it didn't start itself — verified
live against both a genuinely occupied port and a relaunch-over-a-
live-session scenario, not just inspected.

Two things surfaced and documented, not silently resolved: `.venv` was
actually missing `pandas`/`openpyxl`/`python-multipart` (real runtime
dependencies with no `requirements.txt` anywhere to catch the gap
before this); and `frontend/`'s `pnpm-lock.yaml` alongside
`package-lock.json` is confirmed intentional, not accidental — Figma
Make's hosted dev-container/deploy pipeline
(`frontend/.figma/make/*`) hardcodes pnpm, local development
standardizes on npm. One real bug was caught and fixed during release
review: a PowerShell 5.1 `$ErrorActionPreference`/native-stderr
interaction that made `launch.ps1` crash ungracefully on a machine
where `python` resolves to the Microsoft Store alias stub, instead of
showing the intended clean error — fixed and reverified against the
real stub.

Backend regression reconfirmed unchanged at 309/309 as part of this
work (not just assumed).

## Environment

- Python 3.12.10, `pandas` 3.0.5, `openpyxl` 3.1.5, installed locally.
- Sandbox-specific hardcoded paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR` /
  `LOTSYNC_DB_PATH` env vars, each defaulting to a repo-relative
  `data/` subfolder.
- Git-tracked, tagged `v0.1.0` through `v0.7.3`, pushed to `origin` on
  GitHub (private repository) — `v0.4.0` closed Sprint 4 and Phase 2;
  `v0.7.0` through `v0.7.3` cover Phase 3, Sprints 1–4, developer
  tooling, and Event Fidelity respectively. `v0.7.4` (Sprint 3.8 —
  Product Alignment) is this closeout's tagging step. This note was
  previously stale — written at Sprint 4's close and never updated as
  later tags landed; corrected during the Sprint 3.8 governance pass.

## Governance document status

Per the engineering workflow established after Sprint 1:
`VISION.md` and `PRODUCT.md` remain untouched and fully consistent with
everything implemented through Sprint 4 so far.
`DATA_MODEL.md` has received five changes total, all under the
"genuine architectural flaw" governance trigger, not a design change:
added `Event.event_id` (Sprint 1 — the table had no primary key), added
the `PendingIdentity` model (Sprint 2 — `Vehicle` had no honest way to
represent an observation with unresolved identity), added
`"in_progress"` to `SyncRun.status`'s documented values (Sprint 3 — the
original three values had no way to describe a row between INSERT and
completion), replaced `Task.status`'s three values with
`commitment_standing`/`execution_status` plus a new `TaskExecutionEvent`
entity (Pre-Sprint 4 design review — the original status couldn't
honestly represent a commitment discharged as moot, cancelled, or
superseded), and added `created_at`/`resolved_at` to `Recommendation`
(Slice 6 — implementing "a dismissed Recommendation does not reappear
unless state changed" requires knowing *when* it was dismissed, which
the table had no way to represent). `ARCHITECTURE.md` was touched for
the first time in Phase 2 during Slice 5 — a wording tightening
(Reality-discharge vs Intent-discharge) and a pointer to
`DECISION_FRAMEWORK.md`'s four-layer reasoning structure, both required
by `SPRINT_4_CHECKLIST.md`, not a new decision made outside review.
`PRODUCT.md`'s identical "closes itself" wording gap was deliberately
left alone — not in the checklist, and the design review explicitly
judged it not urgent enough to justify reopening that document on its
own. No governance document was touched during Slice 7 — `queries/
dashboard.py` is new, ungoverned application code, not a schema or
architecture change.

**Phase 3, Sprint 1:** no governance document was touched. `DATA_MODEL.md`'s
Employee and Dealership shapes were already fully specified and
implemented exactly as written — this sprint closed an implementation
gap (no migration existed), not a design gap. `FRONTEND_BACKEND_RECONCILIATION.md`
and `API_CONTRACTS.md` — both already governing-adjacent per the Phase
3 kickoff — are updated in spirit but not edited: their open questions
(Requests, Trade-Ins, Transportation/Customer Delivery, Authentication,
Employee's migration gap) are unchanged except that the Employee
migration gap specifically named in both is now closed. See
`PHASE_3_SPRINT_1_REVIEW.md` for the one real implementation-level
finding this sprint surfaced (a SQLite `NOT NULL`/`UPSERT` interaction
that made `upsert_vehicle`'s pattern unsafe to reuse verbatim for
`Employee`/`Dealership`) — an implementation detail, not a governance
question, so no `DATA_MODEL.md`/`ARCHITECTURE.md` change resulted.

**Phase 3, Sprint 2:** `API_CONTRACTS.md` was edited once, for a
genuine reason — `VehicleSummaryDTO`'s `color` field was removed,
since the backend has no such column and nothing populates one. This
is the same "fix the stale reference, not the correct document"
convention `DATA_MODEL.md` itself already establishes, applied to
`API_CONTRACTS.md` for the first time. No other governance document
was touched. `DATA_MODEL.md`/`ARCHITECTURE.md` remain fully consistent
with this sprint's implementation — nothing built this sprint required
a schema or architecture change, only new, additive query functions and
a new, additive `api/` package. See `PHASE_3_SPRINT_2_REVIEW.md` for
the one real implementation-level finding this sprint surfaced (a
SQLite cross-thread connection error, fixed via `check_same_thread=False`
on `connect()`) — again an implementation detail, not a governance
question.

**Phase 3, Sprint 3:** no governance document was touched, including
`API_CONTRACTS.md` — every gap this sprint's frontend integration hit
(Vehicle photo, no operational-status enum, no employee-name
resolution, no `TaskExecutionEvent` history endpoint) was already
named as an open question in `API_CONTRACTS.md` Section 9 or
`FRONTEND_BACKEND_RECONCILIATION.md`'s Architectural Risks before this
sprint started; this sprint confirmed those gaps are real and current
rather than discovering a new one that would require a contract edit.
The Task-model correction (collapsed `status` → `commitment_standing`/
`execution_status`) is the frontend catching up to a design
`DATA_MODEL.md` and `DECISION_FRAMEWORK.md` already settled during
Pre-Sprint 4 — not a new decision. See `PHASE_3_SPRINT_3_REVIEW.md`
for the full account, including a naming discrepancy this sprint
surfaced (its kickoff called it "Phase 4," inconsistent with every
other artifact's "Phase 3, Sprint 3") that's flagged for the product
owner to resolve, not silently picked one way or the other.

**Phase 3, Sprint 4:** `PRODUCT.md` was edited once, for the naming
discrepancy Sprint 3 flagged and left open — resolved this time, before
any code was written, per explicit product-owner direction: the Phase 3
roadmap paragraph now names Sprints 1–4 explicitly as real, demonstrated
scope growth within Phase 3, not a re-scoping. No change to `VISION.md`,
`ARCHITECTURE.md`, or `DATA_MODEL.md` — the partial-source sync design
(empty-columned `DataFrame` stand-ins for un-uploaded sources) and the
derived, grouped-by-shared-timestamp `SyncRun` history read are both
valid-input-shape and read-model decisions respectively, neither
requiring a schema or architecture change. `API_CONTRACTS.md` needed no
edit either — `PendingIdentityDTO` and `SyncRunDTO` were already fully
specified there; this sprint only closed the "specified, not yet
implemented" gap, matching Sprint 2's own precedent for Employee. See
`PHASE_3_SPRINT_4_REVIEW.md` for the two real, concrete
reconciliation-engine findings this sprint's testing surfaced
(documented, not silently patched into a governed module).

**Developer tooling (v0.7.1):** no governance document was touched —
`ARCHITECTURE.md`, `DATA_MODEL.md`, `PRODUCT.md`, `VISION.md`, and
`DECISION_FRAMEWORK.md` all remain fully consistent with this work,
which added only developer-facing scripts/docs (`tools/`, `Launch
LotSync.bat`, `requirements.txt`) and corrected two stale references
in `README.md`/`api/README.md` (the pip-install command and the
frontend's default port). No business logic, API contract, schema, or
frontend architecture changed.

**Sprint 3.7 (v0.7.3) — Event Fidelity:** `DATA_MODEL.md` edited under
the same "genuine architectural flaw" trigger as every prior schema
addition — `Event.event_time` and the new `EventFreshness` entry
document real columns this sprint's own migration adds, not a design
change (`event_time` is additive and independently nullable;
`observed_at`'s meaning is unchanged). `API_CONTRACTS.md`'s
`ActivityDTO` gained `event_time` for the same reason, plus two stale
`"color"` fields removed from example payloads (dead since Sprint 2's
own correction, never cleaned from these specific examples until now).
`ARCHITECTURE.md` received one correction, not a new decision: its
existing Wholesale/RecovR text already described `Step =
WHOLESALE/AT AUCTION` as "already" excluding vehicles from install
lists, a claim this sprint's review found wasn't actually true of the
live pipeline — now genuinely true, the text corrected to say so
explicitly. No change to `VISION.md`, `PRODUCT.md`, or
`DECISION_FRAMEWORK.md` — this sprint's mechanisms (generic
diff-before-write, freshness-as-current-state-not-history) are
applications of principles those documents already establish, not new
ones. See `CHANGELOG.md`'s v0.7.3 entry for the two findings (Wholesale
rule not actually live; Keyper's single, `Status=Out`-only-confirmed
timestamp) surfaced and confirmed with the product owner before any
code was written, per this sprint's own explicit instruction.

**Sprint 3.8 (v0.7.4) — Product Alignment:** the first sprint whose
*entire* scope is governance documents — no `DATA_MODEL.md` or
`ARCHITECTURE.md` change, because nothing about the backend's schema
or reasoning structure was wrong; the drift this sprint corrects was
in `PRODUCT.md`'s stakeholder framing and in the Phase 3 frontend
mockup, not in anything already implemented. `PRODUCT.md` and
`VISION.md` edited directly, under a new trigger this project hasn't
used before — not "genuine architectural flaw" (the Sprint 1–3.7
trigger for `DATA_MODEL.md`/`ARCHITECTURE.md`), but a direct,
explicit product-owner identity correction, following a full
Identity/Scope/Beta-Vision review conducted deliberately before any
document was touched. `FRONTEND_BACKEND_RECONCILIATION.md` rewritten
in full — its original factual inventory (Sections 1–5) preserved
rather than replaced, since the underlying observations about what
the frontend files contain didn't change; only the disposition drawn
from those observations did. No change to `DATA_MODEL.md`,
`ARCHITECTURE.md`, or `DECISION_FRAMEWORK.md`. This sprint deliberately
left three questions open rather than force a resolution: whether
Report aggregates belong in the grammar, whether manager/staffing
views are in-bounds as lot staff, and how contributor authentication
for Quick Log should work — see `FRONTEND_BACKEND_RECONCILIATION.md`'s
"Needs discussion" list and `CHANGELOG.md`'s v0.7.4 entry.

This sprint's own closing read-through caught two real
cross-document issues before they shipped, both corrected rather than
left for a future sprint: `PRODUCT.md`'s Beta Vision still called
Trade-In-as-its-own-domain-model undecided after the product-grammar
review had already settled it (`PendingIdentity` + Task, no new
model), and this file's own Environment section still described a
`v0.4.0` tag as an upcoming step three major versions after it
actually landed. See `CHANGELOG.md`'s v0.7.4 entry for both.

## Phase 2 complete — what the backend now provides

Every source (Tekion, Sold, MDD, RecovR, RapidRecon, Keyper) persists
its contribution to `Vehicle`/`Event`, diffed against history rather
than rewritten every sync (Slices 1–3). `PendingIdentity` captures and,
when a later sync resolves it, promotes unresolved Keyper identities
into real Vehicles (Slices 2–3). Every Event traces back to the
`SyncRun` that produced it, with real per-source transactional
semantics (Slice 4). `Task` models operational commitments with
independent commitment/execution axes, four terminal dispositions
split cleanly into Reality- and Intent-discharge, ratification/
authority tracking, and escalation (Slice 5). `Recommendation` models
interpretations distinct from commitments, with a working convert/
dismiss lifecycle (Slice 6). `queries/dashboard.py` proves all of the
above can actually answer dashboard-shaped questions without
introducing a second, driftable copy of any answer (Slice 7). Every
CSV report a dealership already depends on has produced byte-identical
output, unchanged, through all seven slices.

**Phase 3 has begun**, scoped narrowly and deliberately, sprint by
sprint: Sprint 1 built the Employee/Dealership backend foundation;
Sprint 2 built the first read-only API layer over the existing Phase 2
data; Sprint 3 wired six frontend screens to that API and corrected the
frontend's Task model to match the backend's already-settled design;
Sprint 4 replaced manual database seeding with a real, upload-triggered
Inventory Sync workflow — this project's first write route, built as a
thin orchestration layer over the unchanged reconciliation engine.
Authentication is still explicitly not built, now a two-sprint-running
recommendation. **Next decision, not yet made:** whether to begin
Phase 3, Sprint 5 (see "Upcoming slices" above), per this project's
standing practice of treating each sprint as its own scoped, reviewed
unit rather than an automatic continuation into the next.
