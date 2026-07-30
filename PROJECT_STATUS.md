# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against.

**Last updated:** 2026-07-29 (Sprint 3.7 / v0.7.3 — Event Fidelity closed)

## Current position

| | |
|---|---|
| **Phase** | Phase 3 — Web application — **Sprint 3.7 done, Timeline reflects operational history rather than sync noise** (Phase 2 remains complete underneath it) |
| **Sprint** | Sprint 3.7 (v0.7.3) — Event Fidelity (done) |
| **Scope note** | `event.event_time` (source-provided timestamps, populated only where a source's meaning is confirmed: Keyper Checkout Date for `Status=Out` only, Tekion Stocked In/Sold Date); `event_freshness` (generic per-`(vin, event_type)` audit tracking, closing a gap that predates this sprint); RapidRecon's missing diff-before-write fixed via a new shared, reusable helper; a real, live gap between this project's stated Wholesale/RecovR rule and the actual wired pipeline found and closed (`build_tracker_install_tasks` now honors `Step ∈ {WHOLESALE, AT AUCTION}`, verified against the already-correct but previously unwired exclusion logic before reuse). No new features; no business rule invented — see `CHANGELOG.md`'s v0.7.3 entry for the full account, including the two findings surfaced and confirmed before implementing. |
| **Last completed** | Sprint 3.7 — `database/migrations/0008_event_fidelity.sql`, `sync/reconciler.py`'s `_insert_event_if_changed`/Wholesale exclusion/event_time wiring, `queries/dashboard.py`, `api/dtos.py`, and `VehicleDetail.tsx`/`Activity.tsx`/`LotManager.tsx`'s Timeline rendering, all wired end-to-end and verified against the real, live 4,312-vehicle database |

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
- No CI — the suite must be run manually. Standing risk, unchanged
  since Sprint 1.
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
- Git-tracked, tagged `v0.1.0`, `v0.2.0`, and `v0.3.0` (Sprint 3),
  pushed to `origin` on GitHub (private repository). Sprint 4's
  Slice 5/6/7 work is committed on top of `v0.3.0`; a `v0.4.0` tag
  (closing Sprint 4 and Phase 2) is this closeout's tagging step.

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
