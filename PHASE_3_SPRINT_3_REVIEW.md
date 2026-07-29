# Phase 3, Sprint 3 Review — Frontend Integration

**Date:** 2026-07-28
**Scope:** integration only, per this sprint's own explicit constraints —
backend considered complete for current scope, frontend UI considered
frozen, no redesign of either. No authentication, no Inventory Sync
uploads, no write APIs, no Requests/Transportation/Trade-Ins, no Rule
Engine/AI, no Sprint 4 work. Governing documents: `VISION.md`,
`PRODUCT.md`, `DATA_MODEL.md`, `DECISION_FRAMEWORK.md`,
`ARCHITECTURE.md`, `FRONTEND_BACKEND_RECONCILIATION.md`,
`API_CONTRACTS.md`, `PHASE_3_SPRINT_1_REVIEW.md`,
`PHASE_3_SPRINT_2_REVIEW.md`.

**A naming note, surfaced rather than silently resolved:** this
sprint's kickoff referred to this work as "Phase 4 — Sprint 3." Every
other artifact in this project — `PROJECT_STATUS.md`'s own "Upcoming
slices" recommendation, `PHASE_3_SPRINT_1_REVIEW.md`,
`PHASE_3_SPRINT_2_REVIEW.md`, and `PRODUCT.md`'s roadmap (which
reserves Phase 4 for Dealer Trades) — calls frontend integration
"Phase 3, Sprint 3." This review, `PROJECT_STATUS.md`, and
`CHANGELOG.md` are all named/labeled consistently with that existing
history rather than the kickoff message's phrasing. **Recommend the
product owner confirm which numbering is intended going forward** —
this is a labeling question, not a scope question, and didn't block
starting the sprint's actual work.

---

## 1. Sprint Summary

Replaced hardcoded mock data with real `fetch` calls against the
Phase 3 Sprint 2 read-only API, one screen at a time, in the
recommended order: Vehicle Detail → Vehicles List → Dashboard →
Activity → Recommendations → Tasks (after correcting the frontend's
Task model). Each screen's success, empty/loading, and
backend-unavailable states were verified directly in a browser against
a running backend (a throwaway, gitignored seed script populated
`data/lotsync.db` with realistic Vehicle/Task/Recommendation/Event/
SyncRun rows for this purpose — not part of the deliverable).

**Added:**
- `frontend/src/api/` (new) — the reusable frontend API service layer:
  `types.ts` (wire types mirroring `api/dtos.py` field-for-field),
  `client.ts` (`apiGet`, `ApiError`, `isBackendUnavailable`),
  `useApi.ts` (the one shared loading/error/success hook every screen
  uses), and one module per domain (`vehicles.ts`, `tasks.ts`,
  `recommendations.ts`, `activity.ts`, `dashboard.ts`).
- `.claude/launch.json` — lets this environment's browser-preview
  tooling start the Vite dev server; not part of the application.

**Changed (backend, minimal, not a contract change):**
- `api/app.py` — added `CORSMiddleware`, scoped to localhost dev
  origins via `LOTSYNC_CORS_ORIGINS`. The frontend runs on a different
  origin (Vite dev server) than the API for the first time this
  project has had a real browser calling it directly; this is
  transport-level plumbing, not a route/DTO/business-logic change —
  same category as Sprint 2's `check_same_thread=False` fix. Confirmed
  the full 292-test backend suite still passes unchanged.

**Changed (frontend):**
- `src/VehicleDetail.tsx` — wired to `GET /vehicles/{vin}`.
- `src/dashboards/VehiclesList.tsx` — wired to `GET /vehicles`.
- `src/dashboards/LotManager.tsx` — wired to `GET /dashboard` (Inventory
  Health, Connected Systems, Live Activity) and `GET /recommendations`
  (Suggestions panel).
- `src/dashboards/Activity.tsx` — wired to `GET /activity`.
- `src/dashboards/Tasks.tsx` — the Task model correction (Section 3)
  plus wiring to `GET /tasks`.
- `src/App.tsx` — `VehicleDetailPage` now receives a real `vin` prop
  (it previously received none at all — every field was hardcoded);
  the header search's VIN/stock regex was widened from `{4,8}` to
  `{4,17}` characters to admit full VINs.

**No governance document required an update.** Nothing this sprint
did contradicted `DATA_MODEL.md`, `ARCHITECTURE.md`, or
`DECISION_FRAMEWORK.md` — the Task-model correction (Section 3) is a
frontend catch-up to a design those documents already settled during
Pre-Sprint 4, not a new decision. `API_CONTRACTS.md` also needed no
edit: every gap this sprint hit (Vehicle photo, operational-status
enum, employee-name resolution, etc.) was already listed in its own
Section 9 as an open question — this sprint confirms those gaps are
real and current, it doesn't discover a new one requiring a contract
change.

---

## 2. Definition of Done Verification

For each of the six screens: real data renders correctly, loading
state shows while the request is in flight, a 404 (Vehicle Detail) or
empty-result (Vehicles List, Activity, Tasks) state renders without
crashing, and a fully unreachable backend (verified by killing the
`uvicorn` process mid-session and reloading) shows a plain-language
"LotSync API is unreachable" message rather than a blank screen or a
stack trace. Confirmed directly in-browser for all six; see Section 4
for the one case (Recommendations' `Suggestions` panel state) verified
by code-path inspection rather than a repeated live kill/restart cycle,
since it reuses the identical `useApi` pattern already proven four
times over.

Cross-screen navigation was also verified, not just each screen in
isolation: Vehicles List → Vehicle Detail (by VIN), Activity →
Vehicle Detail (by VIN), and Tasks → Vehicle Detail (by VIN) all
resolve correctly end-to-end against live data.

---

## 3. The Task Model Correction

This is the one piece of this sprint that's a genuine correction, not
just wiring, so it gets its own section.

**What was wrong:** `Tasks.tsx`'s mock `Task` type had two problems,
both already predicted by `FRONTEND_BACKEND_RECONCILIATION.md`'s
Architectural Risk #1 and `DATA_MODEL.md`'s own Task entry:
1. A single collapsed `status` field
   (`outstanding|in-progress|waiting-verification|verified|cancelled|superseded`)
   — exactly the shape the Pre-Sprint 4 design review rejected for the
   backend, because it can't honestly represent a human-asserted
   completion that hasn't yet been reality-confirmed.
2. `vehicles: TaskVehicle[]` on a single Task object — but
   `DATA_MODEL.md` is explicit that a real Task is one-vehicle-one-
   action; "Install RecovR Devices, 6 tasks" is six separate Task rows
   sharing a `task_type`, aggregated for the card, never one Task
   holding six vehicles.

**What changed:** `TaskDTO`'s two real, independent fields
(`commitment_standing`, `execution_status`) are used throughout,
never collapsed. `deriveDisplayStatus()` computes a label from both
purely for rendering — it is a read, not a write, and nothing is ever
stored back into one field. Real Tasks are grouped by `task_type`
client-side (a mechanical grouping operation, not an invented business
rule) to reconstruct the "N vehicles, M complete" card shape from
`DATA_MODEL.md`'s own description.

**Verified, not just implemented:** seeded a Task in the exact
"surfaced disagreement" state `API_CONTRACTS.md`'s own test names —
`commitment_standing = outstanding`, `execution_status = completed` —
and confirmed in the browser that both the group-card row and the
detail view render it as "Waiting Verification" with an explicit
callout explaining *why* it's not simply "Done," rather than picking
one field to display and hiding the other.

**Also corrected, smaller:** `reason` is now the real free-text string
(the mockup fabricated a structured pass/fail checklist with no
backend equivalent). "Automated" vs. "Management Requests" is now
driven by the real `ratification_type` field (`standing_policy`/`null`
vs. `human`) instead of a fabricated `TaskSource` union.

**Dropped, not fabricated:** the mockup's per-task `checklist` and
multi-step `timeline` (started/paused/completed/verified entries) have
no backend equivalent — there is no endpoint exposing
`TaskExecutionEvent` history at all today (see Section 5, Mismatch #8).
Rather than inventing fake sub-steps, the detail view shows only the
two real timestamps available (`created_at`, `completed_at`).

---

## 4. Deliverable: Integrated Frontend

| Screen | Endpoint(s) | Verified |
|---|---|---|
| Vehicle Detail | `GET /vehicles/{vin}` | Success, 404, backend-unavailable — all live-tested |
| Vehicles List | `GET /vehicles` | Success, empty-filter, backend-unavailable — all live-tested |
| Dashboard (Lot Manager) | `GET /dashboard`, `GET /recommendations` | Success, backend-unavailable — live-tested; Recommendations panel's own loading/error paths verified by code-path inspection (identical `useApi` shape already proven) |
| Activity | `GET /activity` | Success, filtering, cross-screen navigation, backend-unavailable — all live-tested |
| Recommendations | `GET /recommendations` (LotManager's Suggestions panel; also embedded in Vehicle Detail via `GET /vehicles/{vin}`'s nested `recommendations`) | Success — live-tested via both surfaces |
| Tasks | `GET /tasks` | Success (grouped, all queue/department/priority filters), the surfaced-disagreement state specifically, backend-unavailable — all live-tested |

---

## 5. API/Frontend Mismatches

Every mismatch below was resolved the same way: render the real,
available field honestly; never fabricate a value or duplicate a
backend business rule in React to paper over a gap. None required a
backend contract change — every one was already named as an open
question in `API_CONTRACTS.md` Section 9 or
`FRONTEND_BACKEND_RECONCILIATION.md`'s Architectural Risks, confirming
those sections are still accurate.

1. **No CORS configuration existed.** Fixed (Section 1) — transport
   plumbing, not a contract change.
2. **Vehicle identity mismatch.** Every dashboard's `onVehicleSelect`
   callback passes a *stock number*; `GET /vehicles/{vin}` only
   resolves by VIN, and no by-stock-number lookup endpoint exists.
   Fixed at every entry point this sprint actually wired (Vehicles
   List, Activity, Dashboard's real Live Activity feed, Tasks) by
   passing the real VIN instead. Entry points this sprint did **not**
   wire (`LotStaff.tsx`, `Requests.tsx` — both out of scope) still pass
   stock numbers; clicking through from those screens will show
   Vehicle Detail's "not found" state rather than crash, which is
   honest, not a bug.
3. **Vehicle Detail:** no backend source for photo (already flagged in
   `API_CONTRACTS.md` §9), lot zone, or days-in-inventory. Rendered as
   "Not tracked yet" rather than fabricated.
4. **Vehicles List:** no backend composite Vehicle operational-status
   enum (`API_CONTRACTS.md` §9, and already named as a compromise in
   `PHASE_3_SPRINT_2_REVIEW.md`). The mockup's 5-way status filter/
   column was replaced with direct reads of real fields (Keys Out /
   RecovR Missing / MDD Missing / Has Open Tasks). `trim`, `color`,
   `zone`, `inventoryAge`, `lastSyncHours` have no backend source and
   were dropped, not fabricated.
5. **Dashboard:** the mockup's 3-tier health breakdown (Fully Verified/
   Needs Attention/Critical, fabricated counts) has no backend
   equivalent — `InventoryHealthDTO` is a 2-way split. Reduced to an
   honest 2-tier ring. The "Morning Sync" summary card (Vehicles
   Processed/Issues Found/Tasks Generated) had entirely fabricated
   numbers with no equivalent in the derived Connected-Systems read the
   API actually serves — dropped rather than kept fake. "Today's
   Operations" (task board) and "Team Status" remain mock — see
   Section 6, Recommendation #3.
6. **Activity:** no employee-name resolution exists anywhere in the
   API (`actor_employee_id` is a raw id string, e.g. `emp-0142`, with
   no lookup endpoint) — shown as-is rather than inventing a name.
   `Event` has no status field at all (`DATA_MODEL.md`) — the
   mockup's per-row status pill was dropped. The mockup's cosmetic
   `type` taxonomy was replaced with the real, governed `source`
   vocabulary. No server-side search/pagination exists yet for
   `GET /activity` — this screen fetches a 200-row page and filters
   client-side, the same accepted compromise `GET /vehicles` already
   has (`PHASE_3_SPRINT_2_REVIEW.md`).
7. **Recommendations:** matched the contract exactly, no mismatch.
8. **Tasks:** see Section 3 for the model correction itself. One
   additional gap surfaced here specifically: **no endpoint exposes
   `TaskExecutionEvent` history at all** — not a DTO-shape question,
   an entirely missing route. If a real multi-step task timeline is
   wanted later, that's a new endpoint to design, not a frontend fix.
9. **No employee-list endpoint anywhere in the API.** This is the same
   root cause behind three separate surface symptoms (Activity's actor
   names, Task assignment display, Dashboard's Team Status panel) —
   worth fixing once, not three times. See Section 6, Recommendation
   #2.

---

## 6. Recommendations for Sprint 4

1. **Authentication.** `PRODUCT.md`'s own named trigger point, and this
   sprint had to introduce a placeholder "current employee" identity
   (`emp-0142`, matching the app's existing hardcoded "logged in as
   Marcus Torres" prototype convention) just to make "My Tasks"
   filterable at all. A real access surface now exists across six
   screens — this is a natural point to revisit whether auth is due,
   consistent with how Sprint 1 and Sprint 2 both explicitly re-raised
   this same question at their own close.
2. **A `GET /employees` endpoint.** Small, mechanical (the `employee`
   table and `get_employee`/`upsert_employee` already exist per Phase
   3 Sprint 1) — resolves the actor-name gap in Activity, Task
   assignment, and Dashboard's Team Status simultaneously.
3. **Wire `LotManager.tsx`'s "Today's Operations" task board** to the
   same grouped-by-`task_type` real data `Tasks.tsx` now uses. This was
   deliberately deferred within this sprint (the Dashboard step came
   before the Task-model correction in the recommended order), but the
   correction is done now — this is a small follow-up, not new design
   work.
4. **A lightweight frontend test setup (Vitest, the natural fit for a
   Vite project).** This sprint's verification was entirely manual,
   browser-driven (Section 2) because no test runner exists in
   `package.json` today. That was an acceptable, deliberate choice for
   a read-only integration sprint reusing one proven pattern
   (`useApi`) six times — it will not be an acceptable choice once
   write-path work starts, where an unverified regression has real
   consequences.
5. **Server-side search/pagination for `GET /vehicles` and
   `GET /activity`.** Already flagged in `PHASE_3_SPRINT_2_REVIEW.md`
   as a compromise; still unresolved, still fine at seed-data scale,
   still a real concern at actual dealership inventory volume
   (1,200+ vehicles).
6. **Requests, Trade-Ins, Transportation** remain exactly where
   `FRONTEND_BACKEND_RECONCILIATION.md` left them — open product-owner
   domain decisions, untouched by this sprint, per its own explicit
   exclusions.
7. **Confirm the Phase/Sprint naming** raised at the top of this
   review.

**Not recommended:** starting any of Section 6's items in the same
sprint as this review, or beginning write-path work before Recommendation
#4 is in place. Per this project's standing practice, stopping here for
explicit review is the point of finishing a sprint, not a formality to
skip past.

**Stopping here, per this sprint's own scope.** This review does not
begin Sprint 4.
