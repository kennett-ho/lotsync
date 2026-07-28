# Phase 3, Sprint 1 Review — Backend Foundation: Employee + Dealership

**Date:** 2026-07-27
**Scope:** infrastructure only, per this sprint's own explicit
constraint — no FastAPI, no controllers, no DTO serialization, no
Transportation/Trade-Ins/Requests/Notifications. Governing documents:
`VISION.md`, `PRODUCT.md`, `DATA_MODEL.md`, `DECISION_FRAMEWORK.md`,
`ARCHITECTURE.md`, `FRONTEND_BACKEND_RECONCILIATION.md`,
`API_CONTRACTS.md`.

---

## 1. Summary

Built the Employee and Dealership backend foundation that
`FRONTEND_BACKEND_RECONCILIATION.md` and `API_CONTRACTS.md` both
identified as the first, purely mechanical gap blocking Phase 3: both
entities were fully specified in `DATA_MODEL.md` since Phase 2's
frontend-discovery review, and both were referenced by four existing
tables as unconstrained free-text columns, but neither ever had a
migration.

**Added:**
- `database/migrations/0006_employee_dealership.sql` — `dealership`
  and `employee` tables, matching `DATA_MODEL.md`'s documented shapes
  exactly, with a real `FOREIGN KEY` from `employee.dealership_id` to
  `dealership`.
- `database/repository.py` — `upsert_dealership`/`get_dealership`,
  `upsert_employee`/`get_employee`, following the existing repository's
  partial-upsert conventions.
- `tests/test_database_dealership.py` (9 tests),
  `tests/test_database_employee.py` (11 tests).
- Updated `PROJECT_STATUS.md`, `CHANGELOG.md`.

**Explicitly not built, by design, not oversight:**
- Any authentication scaffolding (identity model, role mapping,
  permission scaffolding, session strategy) — see Section 2 and Section 4.
- `FOREIGN KEY` constraints retrofitted onto the four already-existing
  tables' employee/dealership-shaped columns — see Section 2.
- Anything touching Transportation, Trade-Ins, Requests, or
  Notifications, per this sprint's explicit constraints.

**Test suite:** 211 → 231 tests passing (all new tests are additive;
zero changes to any existing test, migration, or CSV-producing code
path). Full suite re-run confirmed green after this sprint's changes.

---

## 2. Architecture Review

**Against `DATA_MODEL.md`:** both tables match their documented field
lists exactly — no field added, renamed, or dropped relative to what
was already governed. The one schema-level decision this sprint made
beyond a literal transcription was declaring `name NOT NULL` on both
tables; `DATA_MODEL.md`'s field tables don't state this explicitly, but
a nameless Employee or Dealership record isn't a meaningful state for
either entity, and this is exactly the kind of literal, non-load-bearing
validation gap the project's own established convention (`Event.event_id`,
`SyncRun`'s `in_progress` value, `Task`'s Sprint 4 split) treats as
worth adding without needing a governance-document edit — no existing
document asserted the opposite, so nothing became stale.

**Against `ARCHITECTURE.md`:** the module boundary is unchanged —
`database/repository.py` remains the only persistence-layer file, no
second pattern was introduced (see the "real bug caught" note below
for why the *shape* of `upsert_dealership`/`upsert_employee` differs
slightly from `upsert_vehicle`, without becoming a different pattern).
`ARCHITECTURE.md`'s note that "the module boundaries in this
reorganization exist so that work is a natural extension later" held
up directly: extending `database/repository.py` required no
restructuring, just two new sections following the file's existing
`upsert_*`/`get_*` conventions.

**Against `API_CONTRACTS.md`:** `EmployeeDTO` and `DealershipDTO`'s
field lists (Section 3) match what got built column-for-column — this
sprint didn't add or need any field `API_CONTRACTS.md` didn't already
name. `API_CONTRACTS.md`'s own "implementation status, stated plainly"
notes on both DTOs ("no migration exists today") are now stale in the
narrow sense that the migration exists — but this doesn't require an
edit to that document: `API_CONTRACTS.md` is a contract about shape,
not a implementation-status tracker, and it already correctly deferred
implementation-status tracking to `PROJECT_STATUS.md`/`CHANGELOG.md`
(both updated this sprint). Section 9's open questions (#7, Employee
implementation; #8, Dealership's shape) are updated by this sprint only
in the sense that #7 is now resolved — that's reflected in
`PROJECT_STATUS.md`, not by editing `API_CONTRACTS.md` itself, since
editing a contract document to mark one open question resolved isn't
the same class of change as revising the contract's actual shape.

**A genuine implementation-level finding, not a design flaw:** the
first draft of `upsert_dealership`/`upsert_employee` reused
`upsert_vehicle`'s exact single-statement "`INSERT ... ON CONFLICT DO
UPDATE`" shape, since the sprint brief and `API_CONTRACTS.md`'s own
Design Philosophy both call for reusing existing patterns rather than
inventing new ones. Verified directly against real SQLite (not
assumed) that this shape is unsafe for any table with a `NOT NULL`
column beyond its own primary key: SQLite evaluates `NOT NULL`
constraints against the attempted `INSERT` row *before* conflict
resolution redirects to `UPDATE`, so a call that only wants to update
`status` (omitting `name` from that call's arguments) raises
`IntegrityError` even though the row already exists with a perfectly
valid name. `Vehicle` never surfaces this because `vin` is its only
`NOT NULL` column. Fixed by branching explicitly on row existence
instead of reusing the single-statement form — a real `UPDATE`
statement for existing rows (which never attempts an `INSERT` at all,
so never triggers this check), and an explicit `ValueError` for
first-time creation without a name. This is the same repository
module, the same connection-passing convention, the same
dict-of-columns return shape as every other repository function — a
corrected implementation of the same pattern's *intent*, not a second
pattern.

---

## 3. Remaining Work — Recommended Scope for Sprint 2

Per `FRONTEND_BACKEND_RECONCILIATION.md`'s Section 7 and
`API_CONTRACTS.md`'s Section 9, with this sprint's Employee/Dealership
work now closing the one purely mechanical gap that stood before it:

**Recommended: a thin, read-only API layer over the already-complete
Phase 2 query surface.** Concretely: `queries/dashboard.py`'s four
existing functions (`connected_systems_status`,
`recent_activity_feed`, `task_counts_by_department`,
`inventory_health_percentage`) exposed over HTTP, plus one genuinely
new read query — a single Vehicle's full aggregate (Tekion/Keyper/MDD/
RecovR status + open Tasks + Recommendations + Timeline), matching
`API_CONTRACTS.md`'s already-defined `VehicleDetailDTO` shape. This is
the lowest-risk possible next step: no new write paths, reuses
fully-tested Phase 2 code, and is the first point a real multi-user
access surface would actually exist — which is also, per this sprint's
own recommendation (Section 4 below), the right point to revisit
whether any authentication work is actually due yet.

**Not recommended for Sprint 2:** the Task-model frontend correction
(`API_CONTRACTS.md`/reconciliation's Risk about `commitment_standing`/
`execution_status`) is a frontend-repo change, not backend work, and
doesn't block a read-only API layer being built correctly on the
backend side as long as the API contract itself (already written)
keeps the two fields separate — which it does. Recommend sequencing
that correction whenever frontend work actually begins, not as backend
Sprint 2 scope.

**This sprint's own scope-narrowing decision, restated for the
record:** Requests, Trade-Ins, Transportation/Customer Delivery, and
Notifications all remain exactly where `FRONTEND_BACKEND_RECONCILIATION.md`
left them — open product-owner questions, not backend work items yet.
Nothing in this sprint's implementation changed that assessment.

**Stopping here, per this sprint's own scope.** This review does not
begin Sprint 2 — that's a separate decision to make explicitly, the
same way beginning Phase 3 itself was.

---

## 4. Risks

1. **Authentication Foundation was descoped from this sprint, and I'd
   flag that decision explicitly for confirmation rather than let it
   pass silently.** `PRODUCT.md`'s own boundary ("No authentication
   system until Phase 3 creates a real multi-user access surface
   requiring one") wasn't met by this sprint's own constraints — no
   endpoint, no controller, no frontend integration was built, so no
   real access surface exists yet to protect. Building session/
   identity/permission scaffolding now would have been speculative
   infrastructure with zero consumers, the exact pattern this project
   has avoided at every other turn (SQLite-not-Postgres, Dealership-
   not-Tenant). This was raised as an explicit question before any code
   was written this sprint, and the answer was to defer it entirely —
   recorded here so it's visible in the sprint record, not just in the
   conversation that decided it.

2. **No `FOREIGN KEY` retrofit onto four existing tables' employee/
   dealership columns.** `vehicle.current_dealership_id`,
   `task.dealership_id`, `task.assigned_employee_id`,
   `task.ratified_by`, `event.actor_employee_id`,
   `event.dealership_id`, `sync_run.dealership_id` all remain
   unconstrained free text. This mirrors an already-accepted precedent
   (`event.sync_run_id` in `migrations/0004_task.sql`), and nothing
   currently populates any of these columns with real employee/
   dealership IDs, so there's no present data-integrity exposure — but
   it is a real, open gap. **Recommendation:** once any future slice
   starts writing real values into these columns (Task assignment,
   dealership attribution in an importer), add an application-level
   orphan-check test the same way `tests/test_database_slice4.py`
   already does for `event.sync_run_id`, rather than retrofitting the
   schema constraint itself.

3. **`Employee.status` and `Employee.role` remain unconstrained free
   strings**, per `DATA_MODEL.md`'s own documented shape (illustrative
   examples only, no closed enum). `API_CONTRACTS.md`'s Section 6
   already flags that frontend files disagree with each other on
   status vocabulary — this sprint didn't resolve that, and shouldn't
   have (closing that vocabulary is a product/UX decision, not a schema
   one). Left open, as `API_CONTRACTS.md` already left it.

4. **No implementation currently calls `upsert_employee`/
   `upsert_dealership` from any importer or pipeline code.** This
   sprint built the foundation, not the wiring — `main.py`'s pipeline
   is entirely unchanged, and no source (Tekion, Keyper, MDD, RecovR,
   RapidRecon) currently attributes its records to a real Dealership or
   Employee row. This is expected and correct for this sprint's scope,
   not a bug, but worth stating plainly so it isn't mistaken for
   "Employee/Dealership data now populates automatically" — it
   doesn't, yet.
