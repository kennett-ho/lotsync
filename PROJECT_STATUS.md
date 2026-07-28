# LotSync — Project Status

Engineering dashboard, kept current after every completed slice or
sprint. This is a snapshot, not a narrative — see `SPRINT_X_REVIEW.md`
files for the story behind each entry, and `IMPLEMENTATION_PLAN.md`
for the full plan this tracks progress against.

**Last updated:** 2026-07-27 (Phase 3, Sprint 2 closed — read-only API layer)

## Current position

| | |
|---|---|
| **Phase** | Phase 3 — Web application — **Sprint 2 done, backend-only** (Phase 2 remains complete underneath it) |
| **Sprint** | Phase 3, Sprint 2 — Read API Foundation (done) |
| **Scope note** | First read-only API layer (`GET /dashboard`, `/vehicles`, `/vehicles/{vin}`, `/tasks`, `/recommendations`, `/activity`, `/reports`) over the already-complete Phase 2/Sprint 1 data. No writes, no auth, no frontend changes (LotSyncWeb untouched). See `PHASE_3_SPRINT_2_REVIEW.md` for the full report, the Frontend Readiness estimate, and the Sprint 3 recommendation. |
| **Last completed** | Phase 3, Sprint 2 — `api/` package, three new `queries/` modules, 61 new tests |

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

## Upcoming slices

**Phase 3, Sprint 3 recommendation** (not started; per this project's
standing practice, starting it is a separate, explicit decision — see
`PHASE_3_SPRINT_2_REVIEW.md`'s "Sprint 3 Recommendation" section for
the full reasoning): the smallest, safest frontend integration slice —
wire ONE screen (recommended: Vehicle Detail, this sprint's own
reference implementation) to its real endpoint, prove the integration
pattern end-to-end, then decide whether to repeat it per-screen or
batch several at once. Also the natural point to revisit whether any
authentication scaffolding is actually needed yet, now that a real,
running access surface exists for the first time.

## Regression status

- **292 / 292 tests passing** (`tests/`, run via
  `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`
  from the repo root).
- Growth this sprint: 231 → 292 (+61: 21 across three new `queries/`
  test files plus 4 added to `test_queries_dashboard.py`, 14 in
  `test_api_dtos.py`, 22 in `test_api_routes.py`).
- No CI — the suite must be run manually. Standing risk, unchanged
  since Sprint 1.
- **New for this sprint:** running `tests/test_api_routes.py` requires
  `fastapi`/`uvicorn`/`httpx` installed (see `api/README.md`) — the
  first test file in this project needing anything beyond the standard
  library. Every other test file remains dependency-free.

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
data. Both explicitly excluded authentication and frontend integration.
**Next decision, not yet made:** whether to begin Phase 3, Sprint 3 (a
single-screen frontend integration slice — see "Upcoming slices"
above), per this project's standing practice of treating each sprint as
its own scoped, reviewed unit rather than an automatic continuation
into the next.
