# Changelog

Established at the start of Phase 2's ongoing sprint workflow. Entries
before this point (the Phase 1 module split) predate this file and are
described in `ARCHITECTURE.md` instead, not backfilled here.

Each entry links to its sprint review for full detail — this file is
a scannable log, not the record itself.

## Sprint 1 — Slice 1: SQLite foundation + Keyper write path (2026-07-23)

See [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) for full detail.

**Added**
- `database/migrations/0001_initial.sql` — `vehicle` and `event` tables.
- `database/repository.py` — `connect()`, `upsert_vehicle()`, `insert_event()`.
- `reconcile_keyper_tekion()` gained optional `db_conn`/`sync_run_id`
  parameters; when supplied, VIN-resolvable Keyper records additionally
  persist to `vehicle`/`event`. Default behavior (no params) unchanged.
- `PROJECT_STATUS.md`, this file, and the standing sprint-review
  workflow itself.

**Changed**
- `event_id` added to `Event` (`DATA_MODEL.md`, `models/event.py`) —
  the table had no primary key.
- Hardcoded `/mnt/user-data/...` paths replaced with
  `LOTSYNC_UPLOADS_DIR` / `LOTSYNC_CONFIG_PATH` / `LOTSYNC_OUT_DIR`
  env-var overrides, defaulting to a repo-relative `data/` folder.

**No change to:** any CSV report's content or format. See Sprint 1's
Definition of Done verification for how this was confirmed.

## Sprint 2 — Slice 2: Full source coverage + PendingIdentity capture (2026-07-23)

See [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) for full detail.

**Added**
- `database/migrations/0002_pending_identity.sql` — `pending_identity` table.
- `database/repository.py` — `upsert_pending_identity()`, keyed by
  `(source, raw_identifier)` (upsert, not insert-every-run).
- `sync/reconciler.py` — four new persistence functions:
  `persist_tekion_observations()`, `persist_mdd_observations()`,
  `persist_recovr_observations()`, `persist_rapidrecon_observations()`,
  plus `_persist_pending_identity()` wired into
  `reconcile_keyper_tekion()`'s three unresolved-identity exception
  branches. All are no-ops when `db_conn` is omitted.
- `main.py` wires all four new functions into the pipeline.
- `tests/test_database_slice2.py` (28 tests) and
  `tests/fixtures/synthetic/rapidrecon.csv` (no RapidRecon fixture
  existed before this sprint).

**Changed**
- `DATA_MODEL.md` — added the `PendingIdentity` model (decided during
  this sprint's pre-implementation design discussion).
- `tests/test_database_slice1.py` — fixed a hardcoded migration-count
  assertion that this sprint's new migration file exposed as fragile;
  also fixed a connection-leak-on-assertion-failure that caused a
  confusing Windows `PermissionError` instead of a clear test failure.

**No change to:** any CSV report's content or format. Verified via
full-suite regression (91 → 119 passing) plus an end-to-end `main.py`
smoke test against all five sources.

**Deliberately deferred to Slice 3:** `PendingIdentity` → `Vehicle`
promotion (detecting a previously-unresolved identifier resolving).
Capture-only in this sprint, as scoped from the outset.

## Sprint 3 — Slices 3+4: Historical diffing, PendingIdentity promotion, SyncRun provenance (2026-07-25)

See [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md) for full detail.

**Added**
- `database/migrations/0003_sync_run.sql` — `sync_run` table.
- `database/repository.py` — `get_last_event_detail_fields()`,
  `get_pending_identity()`, `resolve_pending_identity()`,
  `start_sync_run()`, `complete_sync_run()`, `fail_sync_run()`, and a
  `sync_run()` context manager giving each source's persistence pass
  real transactional semantics.
- `sync/reconciler.py` — `_promote_pending_identity_if_resolved()`,
  wired into `reconcile_keyper_tekion`'s two successful-resolution
  branches.
- `tests/test_database_slice3.py` (10 tests) and
  `tests/test_database_slice4.py` (8 tests).

**Changed**
- All four diffed persistence functions (`_persist_keyper_observation`,
  `persist_tekion_observations`, `persist_mdd_observations`,
  `persist_recovr_observations`) now write an `Event` only when the
  relevant claim actually changed since the last matching `Event` —
  not since whatever `vehicle`'s current-state field happens to hold
  (a real diffing bug, found and fixed mid-sprint; see
  `SPRINT_3_REVIEW.md`). Tekion's diff key is `(tekion_status,
  stock_number)`, not `tekion_status` alone.
- `upsert_vehicle()`, `insert_event()`, `upsert_pending_identity()`,
  `resolve_pending_identity()` no longer commit individually — commit
  responsibility moved to `sync_run()`'s transaction boundary.
- `main.py` wraps every source's persistence pass in `sync_run(...)`.
- `DATA_MODEL.md` — added `"in_progress"` to `SyncRun.status`'s
  documented values.

**No change to:** any CSV report's content or format. Verified via
full-suite regression (119 → 137 passing) plus an end-to-end `main.py`
smoke test against all five sources, with direct inspection of the
resulting `sync_run` table.

**Deliberately accepted, documented limitation:** a VIN with two
observations of the same `event_type` in one sync (the K80001/K80002
duplicate-sold-VIN fixture — an internally contradictory Tekion
export) does not achieve full idempotency on rerun. Not fixed; see
`SPRINT_3_REVIEW.md`'s "Problem solving" section for why.

## Sprint 4 — Slices 5, 6, 7: Task lifecycle, Recommendation engine, dashboard data layer (2026-07-26)

Phase 2 complete. See `IMPLEMENTATION_PLAN.md`'s Slice 5/6/7 sections and `PROJECT_STATUS.md`'s "Phase 2 complete" summary for full detail.

**Pre-Sprint 4 design review** (`DECISION_FRAMEWORK.md`, `SPRINT_4_DESIGN_REVIEW_SUMMARY.md`, `SPRINT_4_CHECKLIST.md`): reshaped `Task` from a three-value status into independent `commitment_standing`/`execution_status` axes, four terminal dispositions split into Reality-discharge (Honored/Moot) and Intent-discharge (Cancelled/Superseded), an append-only `TaskExecutionEvent` log, ratification/authority tracking, and escalation via `escalated_from_task_id`.

**Added**
- `database/migrations/0004_task.sql`, `0005_recommendation.sql` — `task`, `task_execution_event`, `recommendation` tables.
- `database/repository.py` — `insert_task`, `get_open_task`, `honor_task`/`moot_task` (Reality-discharge), `cancel_task`/`escalate_task` (Intent-discharge), `insert_task_execution_event`, `assert_task_completed`; `insert_recommendation`, `get_open_recommendation`, `get_latest_recommendation`, `dismiss_recommendation`, `convert_recommendation_to_task`.
- `sync/reconciler.py` — `generate_install_tasks()` (reuses `build_tracker_install_tasks`), Reality-discharge wired into `persist_recovr_observations`/`persist_tekion_observations`, `generate_key_out_aging_recommendations()` (reuses `rules/aging.py`'s existing output).
- `queries/dashboard.py` (new module) — `connected_systems_status()`, `recent_activity_feed()`, `task_counts_by_department()`, `inventory_health_percentage()`. Read-only; no new stored state.
- `tests/test_database_slice5.py` (34 tests), `tests/test_database_slice6.py` (21 tests), `tests/test_queries_dashboard.py` (19 tests).

**Changed**
- `DATA_MODEL.md` — `Task` reshaped as above; `Recommendation` gained `created_at`/`resolved_at` (needed to implement "dismissed unless state changed" at all).
- `ARCHITECTURE.md` — touched for the first time in Phase 2: Reality/Intent-discharge wording, a pointer to `DECISION_FRAMEWORK.md`'s four-layer reasoning structure.
- `models/task.py`, `models/recommendation.py` updated to match; new `models/task_execution_event.py`; `models/sync_run.py`'s stale Sprint-3-era docstring fixed in passing.

**No change to:** any CSV report's content or format, through all three slices. Verified via full-suite regression (137 → 211 passing) plus end-to-end `main.py` runs after each slice, with direct inspection of the resulting `task`/`recommendation` tables and dashboard query output.

**Deliberately documented, not silently resolved:**
- `install_mdd_beacon` Tasks have no automatic Honored path — MDD's export only ever reports "not paired," never a positive confirming claim.
- `generate_install_tasks` reuses `build_tracker_install_tasks`'s methodology specifically, not `build_recovr_install_from_keyper`'s different population — reconciling the two is a deferred product question, not a Task-architecture concern.
- "Inventory health percentage" and Task-department grouping were undefined terms; resolved as documented implementation decisions (health = percentage of vehicles with zero outstanding Tasks; department grouping includes an honest "Unassigned" bucket rather than inventing a mapping).

## Phase 3, Sprint 1 — Backend foundation: Employee + Dealership (2026-07-27)

See [`PHASE_3_SPRINT_1_REVIEW.md`](PHASE_3_SPRINT_1_REVIEW.md) for full detail. Closes the gap `FRONTEND_BACKEND_RECONCILIATION.md` and `API_CONTRACTS.md` both flagged: `Employee`/`Dealership` were fully specified in `DATA_MODEL.md` since Phase 2's frontend-discovery review but never migrated.

**Added**
- `database/migrations/0006_employee_dealership.sql` — `dealership` and `employee` tables, matching `DATA_MODEL.md`'s shapes exactly; `employee.dealership_id` carries a real `FOREIGN KEY` to `dealership` (safe at creation time, since both tables are new in this same migration).
- `database/repository.py` — `upsert_dealership`/`get_dealership`, `upsert_employee`/`get_employee`.
- `tests/test_database_dealership.py` (9 tests), `tests/test_database_employee.py` (11 tests).

**Deliberately NOT added:** any authentication scaffolding (identity/session/permission infrastructure). Per `PRODUCT.md`'s own explicit boundary ("No authentication system until Phase 3 creates a real multi-user access surface requiring one") and this sprint's own scope (no FastAPI, no controllers, no frontend integration — no access surface actually created yet), building auth infrastructure now would be exactly the "infrastructure ahead of real need" pattern this project avoids everywhere else. Deferred to whichever future sprint actually introduces the API layer.

**Deliberately NOT added:** `FOREIGN KEY` constraints retrofitted onto the four already-existing tables' employee/dealership-shaped columns (`vehicle.current_dealership_id`, `task.dealership_id`, `task.assigned_employee_id`, `task.ratified_by`, `event.actor_employee_id`, `event.dealership_id`, `sync_run.dealership_id`). SQLite has no `ALTER TABLE ... ADD CONSTRAINT`; retrofitting would mean recreating each live table. Same choice already made once before for `event.sync_run_id` in `migrations/0004_task.sql` — the "no orphans" guarantee is left to a future application-level test once something actually starts writing real employee/dealership references into these columns, which nothing does yet.

**A real bug caught before it shipped, worth recording:** the first draft of `upsert_dealership`/`upsert_employee` reused `upsert_vehicle`'s single "`INSERT ... ON CONFLICT DO UPDATE`" statement shape. Confirmed empirically (not assumed) that SQLite checks a table's `NOT NULL` constraints against the attempted `INSERT` row *before* conflict resolution redirects to `UPDATE` — so a partial update omitting `name` (both tables' one `NOT NULL` column beyond their primary key) raised `IntegrityError` even on an already-existing row with a perfectly valid name. `Vehicle` never surfaces this because it has no `NOT NULL` column besides its own primary key. Fixed by branching explicitly on row existence instead — a real `UPDATE` statement for existing rows (no `INSERT` attempted, so no `NOT NULL` check on omitted columns), and an explicit `ValueError` for the one genuinely new invalid case this branch introduces (creating a row without a name).

**No change to:** any CSV report's content or format, `main.py`'s pipeline, or any existing table. Verified via full-suite regression (211 → 231 passing).

## Phase 3, Sprint 2 — Read API Foundation (2026-07-27)

See [`PHASE_3_SPRINT_2_REVIEW.md`](PHASE_3_SPRINT_2_REVIEW.md) for full detail. First read-only API layer over the already-complete Phase 2/Sprint 1 data — no writes, no auth, no frontend changes.

**Added**
- `api/` (new package) — `dtos.py` (Pydantic models implementing `API_CONTRACTS.md`'s Section 3 DTOs for this sprint's scope), `dependencies.py` (`get_db`), `routers/{dashboard,vehicles,tasks,recommendations,activity,reports}.py`, `app.py`. First FastAPI dependency this project has ever added — anticipated by `ARCHITECTURE.md`, already the named Phase 3 tech choice in `PRODUCT.md`.
- `queries/vehicles.py` — `list_vehicles`, `get_vehicle_detail` (the sprint's named reference implementation for detail-page aggregation).
- `queries/tasks.py` — `list_tasks`. `queries/recommendations.py` — `list_recommendations`. Both reused unmodified by `get_vehicle_detail` via an optional `vin` filter — one function per concern at two scopes, not two functions.
- `queries/dashboard.py`'s `recent_activity_feed` extended (backward-compatibly) to embed a Vehicle summary per row and select the full Event column set (`sync_run_id`, `actor_employee_id`, `dealership_id`, `detail_fields`, parsed back from JSON) — the original Slice 7 version only selected six of Event's ten columns.
- `tests/test_queries_vehicles.py` (9), `tests/test_queries_tasks.py` (7), `tests/test_queries_recommendations.py` (5), new tests in `tests/test_queries_dashboard.py` (4), `tests/test_api_dtos.py` (14), `tests/test_api_routes.py` (22).
- `api/README.md` — how to run the server and test suite.

**Changed**
- `database/repository.py`'s `connect()` now passes `check_same_thread=False`. A real, load-bearing fix, not a stylistic one — see the "bug caught" note below.
- `API_CONTRACTS.md` — `VehicleSummaryDTO`'s `color` field removed; the `vehicle` table has no such column and nothing populates one. Caught during this sprint's implementation, corrected in the contract directly per this sprint's own instruction ("if implementation reveals a conflict... stop and explain it").

**A real bug caught before it shipped, worth recording:** the first test run against the new FastAPI routes failed with `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. FastAPI dispatches sync route handlers (and their dependencies) to a worker-pool thread, which is not necessarily the thread that opened the connection passed into a test's dependency override. Fixed at the source — `connect()` now opens with `check_same_thread=False`, safe because every request (real or test) still gets its own connection, never shared *concurrently* between two callers, only sequentially across threads. Zero behavior change for any existing single-threaded caller (`main.py`, every Phase 1/2 test) — confirmed via full-suite regression.

**No change to:** any CSV report, any existing table or migration, any write path, `main.py`'s pipeline, or the LotSyncWeb frontend (untouched, as instructed). Verified via full-suite regression (231 → 292 passing).

## Phase 3, Sprint 3 — Frontend Integration (2026-07-28)

See [`PHASE_3_SPRINT_3_REVIEW.md`](PHASE_3_SPRINT_3_REVIEW.md) for full detail, every API/frontend mismatch found, and the Sprint 4 recommendations.

**Added**
- `frontend/src/api/` (new) — `types.ts` (wire types mirroring `api/dtos.py` field-for-field), `client.ts` (`apiGet`/`ApiError`/`isBackendUnavailable`), `useApi.ts` (shared loading/error/success hook), plus one module per domain (`vehicles.ts`, `tasks.ts`, `recommendations.ts`, `activity.ts`, `dashboard.ts`). The first API integration surface this frontend has ever had — previously zero `fetch`/`axios` calls existed anywhere in `frontend/src`.
- `.claude/launch.json` — dev-server config for this environment's browser-preview tooling; not part of the application.

**Changed**
- `api/app.py` — added `CORSMiddleware` (origins via `LOTSYNC_CORS_ORIGINS`), so the Vite dev frontend can call the API cross-origin for the first time. Transport plumbing, not a contract change; full 292-test backend suite reconfirmed green.
- `frontend/src/VehicleDetail.tsx`, `frontend/src/dashboards/{VehiclesList,LotManager,Activity,Tasks}.tsx` — rewritten to fetch real data instead of hardcoded mocks. `Tasks.tsx` specifically: corrected the frontend's collapsed `status` field into the backend's `commitment_standing`/`execution_status` split, and switched from one-Task-holds-many-vehicles to real one-vehicle-one-Task rows grouped by `task_type` for display, per `DATA_MODEL.md`'s already-governed Task shape.
- `frontend/src/App.tsx` — `VehicleDetailPage` now receives a real `vin` prop (previously received none); header search regex widened to admit full 17-character VINs.

**Deliberately NOT fabricated, rendered honestly instead:** Vehicle photo, lot zone, days-in-inventory (no backend source anywhere in `DATA_MODEL.md`); a composite Vehicle operational-status enum (`API_CONTRACTS.md` already names this open); employee display names (no employee-lookup endpoint exists — raw `emp-XXXX` ids shown instead); a multi-step Task execution timeline (no endpoint exposes `TaskExecutionEvent` history today). Every one of these was already an open question in `API_CONTRACTS.md` Section 9 or `FRONTEND_BACKEND_RECONCILIATION.md`'s Architectural Risks before this sprint — none required a new contract decision.

**No change to:** any backend business logic, schema, or migration; any CSV report; `main.py`'s pipeline. Verified via full backend regression (292/292, unchanged) plus live, in-browser verification of every screen's success/empty/loading/backend-unavailable states.
