# Phase 3, Sprint 2 Review — Read API Foundation

**Date:** 2026-07-27
**Scope:** read-only infrastructure only, per this sprint's own
explicit constraints — no write operations, no authentication, no
frontend modifications. Governing documents: `VISION.md`, `PRODUCT.md`,
`DATA_MODEL.md`, `DECISION_FRAMEWORK.md`, `ARCHITECTURE.md`,
`FRONTEND_BACKEND_RECONCILIATION.md`, `API_CONTRACTS.md`,
`PHASE_3_SPRINT_1_REVIEW.md`.

---

## 1. Sprint Summary

Built the first read-only API layer over the backend Sprint 1 left in
place — the smallest complete surface needed to serve the seven
screens this sprint prioritized (Dashboard, Vehicles, Vehicle Detail,
Tasks, Recommendations, Activity, Reports), reusing the existing
query/repository architecture throughout rather than duplicating any
business logic already in `sync/`, `rules/`, or `queries/`.

**Added:**
- `api/` (new package) — `dtos.py` (Pydantic models implementing
  `API_CONTRACTS.md`'s Section 3 for this sprint's scope: `VehicleDTO`,
  `VehicleSummaryDTO`, `VehicleDetailDTO`, `TaskDTO`, `RecommendationDTO`,
  `ActivityDTO`, `ConnectedSystemStatusDTO`, `InventoryHealthDTO`,
  `DashboardSummaryDTO`), `dependencies.py` (`get_db`), six routers, and
  `app.py`. This is the first web-framework dependency this project has
  ever had — not a new architectural decision, since `PRODUCT.md`
  already named FastAPI as the Phase 3 choice and `ARCHITECTURE.md`
  already anticipated exactly this moment.
- `queries/vehicles.py` — `list_vehicles` (Vehicles List) and
  `get_vehicle_detail` (Vehicle Detail, this sprint's named reference
  implementation).
- `queries/tasks.py` — `list_tasks`. `queries/recommendations.py` —
  `list_recommendations`. Each is one function serving two consumers
  (the standalone screen, with no `vin` filter, and
  `get_vehicle_detail`'s nested collections, with one) — not two
  functions, per this sprint's "do not duplicate queries" instruction.
- `queries/dashboard.py`'s `recent_activity_feed` extended
  (backward-compatibly — every existing caller and test needed zero
  changes) to select Event's full column set and embed a Vehicle
  summary, since API_CONTRACTS.md's ActivityDTO wants one specifically
  for the global Activity screen.
- 61 new tests across 6 files (21 query-layer, 14 DTO-level, 22 route-level via FastAPI's `TestClient`).
- `api/README.md` — how to run the server and the test suite.

**Test suite:** 231 → 292 passing. Full regression re-run confirmed
green after every change, including the two below.

**Two real things caught and fixed during implementation, not before
it — see Section 3 for both in full:**
1. `API_CONTRACTS.md`'s `VehicleSummaryDTO` listed a `color` field that
   doesn't exist anywhere in the backend schema. Corrected in the
   contract directly, per this sprint's own "stop and explain" instruction.
2. A real `sqlite3.ProgrammingError` from FastAPI's threadpool dispatch
   model handing a connection across threads. Fixed at the source
   (`connect(..., check_same_thread=False)`), not worked around per-call.

**Explicitly not built, by design:** any write route, any
authentication/session/permission logic, and no LotSyncWeb file was
read for editing purposes or modified in any way.

---

## 2. API Surface

| Route | API_CONTRACTS.md DTO | Backend function(s) reused |
|---|---|---|
| `GET /dashboard` | `DashboardSummaryDTO` | `connected_systems_status`, `task_counts_by_department`, `inventory_health_percentage`, `recent_activity_feed` (all four, unmodified in behavior except the `recent_activity_feed` extension above) |
| `GET /vehicles` | `list[VehicleDTO]` | `queries/vehicles.py`'s new `list_vehicles` |
| `GET /vehicles/{vin}` | `VehicleDetailDTO` | `queries/vehicles.py`'s new `get_vehicle_detail`, itself composed from `list_tasks`, `list_recommendations`, `recent_activity_feed`, and `connected_systems_status` — zero duplicated queries |
| `GET /tasks` | `list[TaskDTO]` (query params: `department`, `priority`, `commitment_standing`, `assigned_employee_id`) | `queries/tasks.py`'s new `list_tasks` |
| `GET /recommendations` | `list[RecommendationDTO]` (query param: `status`) | `queries/recommendations.py`'s new `list_recommendations` |
| `GET /activity` | `list[ActivityDTO]` (query params: `vin`, `limit`) | `recent_activity_feed` |
| `GET /reports` | `DashboardSummaryDTO` (deliberately, not a new DTO — see below) | Same four functions as `/dashboard` |

**Every route is a thin translation layer, nothing more.** No route
handler contains a `SELECT`, a business rule, or a threshold — each
one calls an existing (or, for the three new modules, newly-added but
architecturally identical) `queries/` function and wraps its plain-dict
output in the matching Pydantic model. `api/dtos.py` and the six
`api/routers/*.py` files are the only files in this sprint that import
`fastapi` or `pydantic` at all.

**A deliberate reuse worth calling out explicitly:** `GET /reports`
returns the exact same `DashboardSummaryDTO` type as `GET /dashboard`,
not a new `ReportsSummaryDTO`. `API_CONTRACTS.md`'s Section 3 never
defined a Reports-specific DTO, and this sprint's instructions were
explicit — do not invent new DTOs. `API_CONTRACTS.md`'s own Section 4
already described Reports' currently-backend-supported content as
"extensions of `DashboardSummaryDTO`'s aggregation pattern," so this is
a literal reading of the existing contract, not an invented shortcut.
`connected_systems` and `recent_activity` end up present in the
`/reports` payload even though the current frontend Reports tabs don't
display them — harmless, and the honest alternative to inventing a new
type just to trim two fields.

---

## 3. Architecture Review

**Against `DATA_MODEL.md`:** every DTO field traces to a real column —
verified column-by-column against all six migrations, not assumed.
This is exactly how the one real deviation got caught: `VehicleSummaryDTO`'s
`color` field, present in `API_CONTRACTS.md` since Sprint... since that
document was written, doesn't exist in `vehicle` (migration 0001) and
nothing in `importers/` ever extracts one. Corrected by removing the
field, not by adding an unpopulated column or fabricating data —
`API_CONTRACTS.md` itself now documents this correction directly, and
`api/dtos.py` implements the corrected shape.

**Against `ARCHITECTURE.md`:** the module boundary held exactly as
anticipated — "a FastAPI layer would import from `sync/` and `rules/`
the same way `main.py` does now" is literally what happened, one layer
removed: `api/` imports from `queries/`, which already imports from
nothing but `sqlite3`. No route handler reaches past `queries/` into
`database/repository.py` or raw SQL directly.

**Against `API_CONTRACTS.md`, specifically the Task section — the
single most load-bearing check this sprint needed to pass:**
`TaskDTO.commitment_standing` and `TaskDTO.execution_status` are two
separate, independently-set fields throughout — in the Pydantic model,
in every `queries/tasks.py` row, and in every test (`test_api_dtos.py`'s
`test_commitment_standing_and_execution_status_are_independent_fields`
constructs the exact "surfaced disagreement" case — execution
`completed`, commitment still `outstanding` — and confirms both survive
independently). No code path anywhere in this sprint collapses them
into one field.

**A genuine implementation-level finding, not a design flaw:** the
first test run against the FastAPI routes failed with
`sqlite3.ProgrammingError: SQLite objects created in a thread can only
be used in that same thread`. FastAPI dispatches a sync route handler's
entire dependency-and-handler chain to a worker-pool thread — not
necessarily the thread whatever test code opened a connection on. Fixed
at the source: `database/repository.py`'s `connect()` now passes
`check_same_thread=False`. This is safe, not a workaround papering over
a real hazard — every request (real or test) still gets exactly one
connection, opened and closed within that request's own lifecycle,
never shared *concurrently* between two callers. The flag only lifts
sqlite3's same-thread assertion for a connection used sequentially
across threads, which is precisely this project's actual usage
pattern now that a threaded web framework is in the picture. Confirmed
zero behavior change for every existing single-threaded caller via full
regression (`main.py`'s pipeline, every Phase 1/2/Sprint-1 test).

**Compromises, stated plainly:**
- `list_vehicles` implements no search or status filtering server-side.
  `API_CONTRACTS.md`'s own Section 9 already names the reason: there is
  no canonical, backend-computed Vehicle operational-status enum yet
  (only the four flat per-source status fields and the unpopulated
  `inventory_state` placeholder) — filtering by "status" server-side
  would mean inventing that enum under sprint pressure, which
  `API_CONTRACTS.md` explicitly left open rather than guessed at.
- `/reports` reuses `DashboardSummaryDTO` wholesale rather than a
  trimmed subset — a deliberate reuse (see Section 2), not an
  oversight, but it does mean the `/reports` response carries two
  fields (`connected_systems`, `recent_activity`) the current frontend
  Reports tabs don't use.

---

## 4. Frontend Readiness

Mapped against `FRONTEND_BACKEND_RECONCILIATION.md`'s Screen Dependency
Matrix (19 distinct routed screens, plus `VehicleDetail` as a
modal-style view and `QuickLog` as an embedded write-only component,
counted separately below).

**Fully ready — real backend data now covers the screen's core
content:**
- **Vehicles List** → `GET /vehicles`. Closest 1:1 match of any screen
  in the app.
- **Vehicle Detail** → `GET /vehicles/{vin}`. This sprint's named
  reference implementation — `ARCHITECTURE.md`'s originally-stated
  Phase 2 target ("one Vehicle object shows Tekion/Keyper/MDD/RecovR
  status together") made literal.
- **Tasks** → `GET /tasks`. Data-ready; the frontend's own Task model
  still needs the `commitment_standing`/`execution_status` split
  applied before this can be wired without reintroducing the collapsed
  single-status shape (see `FRONTEND_BACKEND_RECONCILIATION.md`'s
  Architectural Risk #1 — unchanged by this sprint, backend side is
  correct and waiting).
- **Activity** → `GET /activity`. Closest 1:1 match to Event of any
  screen, per the reconciliation's own assessment.

**Partially ready — some panels covered, others depend on Frontend
Only concepts this sprint didn't (and per its scope, shouldn't) build:**
- **Lot Manager Dashboard** → `GET /dashboard`. Two of its four panels
  (Connected Systems, task counts by department, inventory health) are
  a near-exact match; its "Live Activity"/"AI Suggestions" panels are
  covered too via the same response's `recent_activity` — this is the
  best-aligned dashboard in the app, per the reconciliation's own
  earlier finding, now backed by a real endpoint.
- **Lot Staff Dashboard** → `GET /dashboard` (Connected Systems, a
  slice of Live Activity) + `GET /recommendations` (Operational
  Insights). The current-assignment/dispatch/verification-queue
  panels remain Frontend Only.
- **Controller Dashboard** → `GET /dashboard`'s `connected_systems`
  only. The VIN Exceptions table and Audit Queue panel depend on
  richer PendingIdentity/Ratification workflows this sprint's priority
  list didn't include (Inventory Sync wasn't in this sprint's seven).
- **Reports** → `GET /reports`, covering roughly 2 of the frontend's 7
  tabs' worth of content (Daily Summary, Task Completion) at the
  aggregate level; Vehicle Movement, Dealer Trades, Request Volume,
  Inventory Age, and Exception Trends all depend on Frontend Only
  concepts.
- **Inventory Sync** → `GET /dashboard`'s `connected_systems` only.
  The exceptions list and the "Run Sync Now" trigger are both real
  gaps — the latter doesn't have a backend concept to call at all yet
  (today, sync only runs via direct `main.py` invocation).

**Not ready — no backend endpoint exists for this screen's core
content, and building one wasn't in this sprint's scope (nor should it
have been, per the domain decisions `FRONTEND_BACKEND_RECONCILIATION.md`
already deferred):** Tower Manager Dashboard, Requests, Incoming
Inventory, Lot Staffing / Team Status, Staging, Vehicle Movement,
Profile, Transportation, Trade-Ins, and the orphaned `DealerTrades.tsx`.

**`QuickLog`** (the embedded write-only Companion component) isn't
counted above — this sprint built no write routes at all, so it
remains entirely un-servable regardless of read-API progress, by
design.

**Estimate:** counting the 4 fully-ready screens at full weight and the
5 partially-ready screens at half weight, against 19 total routed
screens: (4 + 2.5) / 19 ≈ **34%** of the frontend's distinct screens now
have some real backend data source for their primary content; a
smaller, cleaner **~21%** (the 4 fully-ready screens) could be wired
with zero additional backend work. This measures data availability,
not integration effort — Tasks in particular is "data-ready" but needs
a frontend-side model correction first, so treat that 34% as an upper
bound on what Sprint 3 could plausibly attempt, not a promise that all
of it is equally cheap to wire.

---

## 5. Sprint 3 Recommendation

**Smallest, safest integration slice: wire exactly one screen, prove
the pattern end-to-end, then stop and review before doing a second.**
Concretely, in order of confidence:

1. **Vehicle Detail first.** It's this sprint's own reference
   implementation, the single closest match between what the backend
   now serves and what the frontend mockup already expects
   (`VehicleDetail.tsx`'s Timeline, Operational Insights, and
   Connected-Systems cards line up with `GET /vehicles/{vin}` almost
   field-for-field), and it touches exactly one frontend file. Proving
   the integration pattern (a `fetch` call, a loading state, an error
   state for the 404 case, replacing the hardcoded mock arrays) here
   first means every subsequent screen reuses an already-validated
   approach instead of inventing one under pressure.
2. **Vehicles List second**, once the pattern from (1) is proven — the
   next-closest match, and the natural place to validate a *list*
   response (pagination/loading-list states) rather than a single
   aggregate object.
3. **Do not attempt Tasks yet**, even though its data is ready — wiring
   it before the frontend's own `commitment_standing`/`execution_status`
   correction would either reintroduce the collapsed single-status
   shape or require improvising a translation in the integration code
   that then has to be undone later. Sequence the frontend model fix
   first, as its own small slice, then wire Tasks.
4. **Everything else in Section 4's "partially ready" and "not ready"
   lists stays backend work, not frontend integration work, until its
   own domain question is resolved** — Requests, Trade-Ins,
   Transportation, and the richer Exception/Audit-Queue workflows all
   still need the product-owner calls `FRONTEND_BACKEND_RECONCILIATION.md`
   named, unchanged by this sprint.

**Not recommended:** integrating multiple screens in one sprint, or
standing up authentication "while we're in there." Per this project's
own stated preference, each of these should be its own scoped,
reviewed slice — a single successful integration, reviewed and
confirmed working, is worth more right now than several attempted at
once with no checkpoint in between.

**Stopping here, per this sprint's own scope.** This review does not
begin Sprint 3.
