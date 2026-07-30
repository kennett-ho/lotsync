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

## Phase 3, Sprint 4 — Real Inventory Sync (2026-07-28)

See [`PHASE_3_SPRINT_4_REVIEW.md`](PHASE_3_SPRINT_4_REVIEW.md) for full detail, every architectural decision, and the two real reconciliation-engine findings this sprint's testing surfaced.

**Added**
- `sync/pipeline.py` (new) — `run_inventory_sync()`, the thin orchestration layer behind the upload-triggered sync; reuses `main.py`'s exact importer/`sync/reconciler.py`/`reports/writer.py` call graph, `main.py` itself untouched.
- `sync/upload_validation.py` (new) — per-slot required-column validation before anything persists.
- `queries/inventory_sync.py` (new) — `list_pending_identities()`, `sync_run_history()` (a derived, grouped-by-shared-`started_at` read, not a new stored batch concept).
- `api/routers/inventory_sync.py` (new) — `POST /inventory-sync/run` (this project's first write route), `GET /inventory-sync/history`, `GET /inventory-sync/exceptions`.
- `api/dtos.py` — `PendingIdentityDTO`, `SyncRunDTO` implemented for the first time (both already specified in `API_CONTRACTS.md`); new `SyncRunBatchDTO`, `SyncSummaryDTO`.
- `frontend/src/api/inventorySync.ts`, `apiPostForm()` in `client.ts` (the frontend's first non-GET call), new wire types in `types.ts`.
- `tests/test_sync_pipeline.py` (11 tests), `tests/test_api_inventory_sync.py` (6 tests).

**Changed**
- `database/repository.py`'s `sync_run()` gained an optional `started_at` passthrough (`start_sync_run` already accepted it) — every existing caller unaffected.
- `frontend/src/dashboards/InventorySync.tsx` — rewritten in place (same layout) to upload real files and render real data; see `PHASE_3_SPRINT_4_REVIEW.md` Section 4 for exactly what was preserved vs. corrected.
- `PRODUCT.md` — Phase 3 roadmap paragraph amended to name Sprints 1–4 explicitly, resolving a Phase/Sprint naming question raised at this sprint's kickoff *before* any code was written (see the review's opening section).
- `api/app.py`, `api/README.md` — new router registered; `python-multipart` added as a real new dependency (required by file-upload form fields).

**Deliberately documented, not silently fixed:** a real `KeyError` `generate_key_out_aging_recommendations` would hit on a columnless empty `key_out_aging` DataFrame (guarded at the `sync/pipeline.py` call site, not inside `sync/reconciler.py`); a pre-existing RapidRecon idempotency gap (no diff-before-write at all) this sprint's partial-source testing newly exercised but did not introduce or fix.

**No change to:** any CSV report's content or format via the CLI path; `main.py`; `sync/reconciler.py`; `sync/matcher.py`; `rules/validation.py`; any existing migration or DTO shape. Verified via full backend regression (292 → 309 passing) plus live, in-browser, real-multipart-upload verification of the complete six-source sync workflow.

## v0.7.1 — Developer Tooling (2026-07-28)

Local developer tooling only — no change to reconciliation logic, the API, or the frontend. Not a Phase 3 slice or sprint (Sprint 5 is still not started); see `tools/README.md` for full detail on how each script works and the governance decisions this work surfaced rather than silently resolved.

**Added**
- `tools/launch.ps1`, `stop.ps1`, `doctor.ps1`, `update.ps1`, `common.ps1` — a permanent one-command developer workflow: verifies Python/Node/npm/git, creates `.venv` and installs backend dependencies if needed, runs `npm install` if needed, gracefully stops any previous LotSync session this tooling itself started, starts backend + frontend, waits for both to come up, opens the browser, prints a startup summary. Process tracking is signature-verified (matches a live process's command line against the wrapper script it was launched with) before ever stopping anything — never a blanket "kill all python"/"kill all node."
- `Launch LotSync.bat` — double-click entry point at the repo root.
- `requirements.txt` (repo root, new) — the backend's dependency set, written down in one place for the first time. Fixes a real gap found while building this tooling: `.venv` had `fastapi`/`uvicorn`/`httpx` installed but was missing `pandas`, `openpyxl`, and `python-multipart` — all three real runtime dependencies (`config/settings.py` reads `oms_config.xlsx` via `pandas.read_excel`, which needs `openpyxl`; the inventory-sync upload route needs `python-multipart`).
- `tools/README.md` — documents each script plus the governance decisions below.

**Changed**
- `README.md`, `api/README.md` — pip-install instructions now point at `requirements.txt`; new "Developer Quick Start" section; the frontend port note corrected to match `vite.config.ts`'s actual default (`8443`, not `5173` — see "Deliberately documented" below).
- `.gitignore` — excludes `tools/.state/` (generated runtime state: wrapper scripts, PID files, logs — machine-local, never source).

**Deliberately documented, not silently resolved:**
- **npm vs. pnpm** — `frontend/` has both `package-lock.json` and `pnpm-lock.yaml`. Confirmed intentional, not accidental: six tracked scripts under `frontend/.figma/make/*` are Figma Make's own hosted dev-container/deploy pipeline, and every one of them hardcodes `pnpm`. Local development standardizes on npm (this tooling, `README.md`, `api/README.md`); `pnpm-lock.yaml` and `frontend/.mise.toml`'s pnpm pin are kept because Figma Make's pipeline depends on them. See `tools/README.md`'s "npm vs. pnpm" section.
- **`README.md`'s stale frontend port note** — previously claimed the dev server falls back to port `5173` "outside this project's own dev-container setup"; `vite.config.ts` actually hardcodes `8443` as its fallback regardless of dev-container context. Corrected in this release.

**A real bug caught during release review, worth recording:** under Windows PowerShell 5.1's `$ErrorActionPreference = "Stop"`, redirecting a native command's stderr (even `2>&1` or to `$null`) wraps each stderr line into an ErrorRecord and throws, regardless of exit code. This silently broke the exact check meant to catch it gracefully: on a machine where `python` on PATH resolves to the Microsoft Store's alias stub (a common fresh-Windows state), `Get-PythonCommand`'s `& python --version 2>&1` threw an uncaught terminating exception instead of falling through to a clean "[FAIL] No usable Python found" message. Confirmed by direct testing against the real stub; fixed via a shared `Invoke-Quiet`/`Get-CommandOutputText` helper pattern in `tools/common.ps1` that isolates the native call's error-action scope, and reverified against both a working `python` and a stub-only `PATH`.

**No change to:** any CSV report's content or format; any backend business logic, schema, or migration; the frontend's architecture or component structure. Verified via full backend regression (309/309, unchanged), a genuine fresh `git clone` + `npm install` + `npm run dev` smoke test, and repeated live end-to-end `tools/launch.ps1`/`tools/stop.ps1` runs including a real "port already held by an unrelated process" refusal test and a relaunch-over-a-live-session regression test.

## Sprint 3.7 (v0.7.3) — Event Fidelity (2026-07-29)

The Timeline should represent the operational history of a vehicle, not a log of when LotSync happened to sync — this sprint closes three real gaps between that intent and what the platform actually did, found via a full review of the original reconciliation engine and every governing doc *before* any code was written (per this sprint's own explicit instruction). No new features; no business rule invented.

**Added**
- `event.event_time` (`migrations/0008_event_fidelity.sql`) — the source's own claimed timestamp for when something actually happened, distinct from `observed_at` (when LotSync's sync learned about it — unchanged, still always populated, still the audit trail). Populated only where a source genuinely exposes one with a *confirmed* meaning: Keyper's Checkout Date for `keyper_observed` events with `Status=Out` only (the one interpretation this project already trusted, via the existing days-out calculation) — deliberately **not** inferred for `Status=In`, since nothing confirms what the same field means on a returned key (see Finding B below); Tekion's Stocked In Date / Sold Date for `tekion_observed`/`tekion_sold` (each unambiguously tied to one claim). MDD, RecovR, and RapidRecon's raw exports have no per-observation date column at all — `event_time` stays null there, honestly.
- `event_freshness` table (same migration) — one row per `(vin, event_type)`, recording when a claim was last reconfirmed regardless of whether that reconfirmation wrote a new `Event`. Closes a real, pre-existing audit gap: once a repeated identical observation is correctly suppressed (Keyper/Tekion/MDD/RecovR have always done this), nothing previously recorded that it happened — `SyncRun` only tracks aggregate per-source execution, not which VINs it touched. Generic by construction (not a Vehicle column per source — RapidRecon deliberately has none, per Sprint 2's own decision), so any future source gets this for free via the same shared helper, not by reinventing it.
- `sync/reconciler.py`'s `_insert_event_if_changed()` — a generic version of the diff-before-write pattern Slice 3 already established per-source, used to close `persist_rapidrecon_observations`' gap: it was the one source with no diffing at all, so an unchanged "Step=WHOLESALE" observation created a duplicate Timeline card every single sync — this project's own real-world instance of the exact "repeated observation should not clutter the Timeline" problem this sprint set out to fix. Diffed on `Step` alone (not DIS/DIR, which are continuously-drifting day-counters excluded from the diff key for the same reason `days_out` alone was never treated as a claim — `DECISION_FRAMEWORK.md`). The four already-diffed sources were deliberately **not** migrated to the shared helper — each already works and is already tested; touching working code wasn't needed to fix the actual gap.
- `tests/test_event_fidelity.py` (12 tests) — event_time (Keyper Out/In, Tekion observed/sold), the Wholesale exclusion (below) including two over-exclusion regression guards, and Keyper-departure/silence behavior.

**Fixed**
- **A real, live business-rule gap, found and closed, not invented:** `build_tracker_install_tasks()` — the function that actually feeds `tracker_install_tasks.csv`, the API path, and Task generation — took no RapidRecon input at all, so a Wholesale-bound vehicle with an unpaired RecovR device generated an install task like any other. A *different*, structurally separate function, `build_recovr_install_from_keyper()`, already implemented the `Step ∈ {WHOLESALE, AT AUCTION}` exclusion this project has always intended — but nothing outside its own tests ever called it; it fed no CSV, no API route, no Task generation. `ARCHITECTURE.md` itself already named this precisely: *"'Verify if these cars are going to wholesale' is a new module... Not designed in detail yet."* This sprint verified that exclusion criterion was sound (confirmed against real RapidRecon Step-value analysis already on record) and reused it verbatim inside `build_tracker_install_tasks` itself — not by adopting `build_recovr_install_from_keyper`'s entirely different Keyper-starting-point population, which was never asked for and would have silently dropped candidates the live function correctly includes today. Scoped to RecovR only, matching exactly what was asked — MDD beacon installs were not given the same exclusion, since neither this project's stated rule nor the dead-code function ever covered MDD.
- `persist_rapidrecon_observations` no longer writes a duplicate Event for an unchanged Step observation (see `_insert_event_if_changed` above).

**Two findings surfaced and confirmed before implementing, per this sprint's explicit "stop and explain differences before implementing" instruction:**
- **Finding A:** the "Wholesale vehicles shouldn't need a RecovR tracker" rule wasn't actually implemented anywhere live — only in unused dead code. Confirmed via direct `grep` (nothing outside its own tests called `build_recovr_install_from_keyper`) and `ARCHITECTURE.md`'s own text. Resolved per explicit direction: verify the dead code's logic first, then wire the *criterion* (not the whole methodology) into the live pipeline.
- **Finding B:** Keyper's export has exactly one timestamp column ("Checkout Date"), not separate Checked-Out/Checked-In fields as initially assumed — and nothing in the codebase confirms what it means when `Status=In`. Resolved per explicit direction: trust it only for `Status=Out` (the one place the days-out calculation already trusts it); leave `event_time` null for `Status=In` rather than infer a return timestamp that isn't actually known.

**Changed**
- `sync/pipeline.py`, `main.py` — `rapidrecon_df` now threaded into `build_tracker_install_tasks`/`generate_install_tasks`'s call sites (was already loaded for other purposes in both; no new data dependency introduced).
- `queries/dashboard.py`'s `recent_activity_feed`, `api/dtos.py`'s `ActivityDTO`, `frontend/src/api/types.ts`'s `ActivityDTO` — `event_time` added throughout. `Activity.tsx`, `LotManager.tsx`, `VehicleDetail.tsx` — Timeline rendering now prefers `event_time ?? observed_at` everywhere a vehicle's activity timestamp is displayed.
- Two existing tests updated, not silently left broken, because they asserted the exact old behavior this sprint fixed: `test_database_slice3.py`'s RapidRecon idempotency test (was asserting a duplicate Event *would* be written on rerun; now asserts it isn't, plus a new `event_freshness` audit-integrity assertion) and `test_sync_pipeline.py`'s repeat-import delta test (2 documented non-idempotency gaps → 1, now that RapidRecon's is closed).
- `DATA_MODEL.md` (`Event.event_time`, new `EventFreshness` entry), `API_CONTRACTS.md` (`ActivityDTO.event_time`, two stale `"color"` fields removed from unrelated example payloads found in passing), `ARCHITECTURE.md` (correction note on the Wholesale section, since its "already does" claim wasn't actually true of the live pipeline until this sprint).

**No change to:** `build_tracker_install_tasks`'s MDD logic; any of Keyper/Tekion/MDD/RecovR's existing diff-before-write mechanics; any DTO or column beyond the additions above; any CSV report's *format* (only `tracker_install_tasks.csv`'s *content* changes, and only for the Wholesale-excluded rows — a deliberate, confirmed fix, not drift). Verified via full backend regression (316 → 328 passing), and empirically against the real, live seeded database (4,312 vehicles) and a real Inventory Sync run through the actual API and browser.
