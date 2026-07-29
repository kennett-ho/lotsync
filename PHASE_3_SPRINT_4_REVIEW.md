# Phase 3, Sprint 4 Review — Real Inventory Sync

**Date:** 2026-07-28
**Framing:** this sprint marks the transition from architecture
validation to operational validation. Sprints 1–3 proved the platform
(backend foundation, read API, frontend integration, all against
seeded/mock data). This sprint begins validating LotSync against real
dealership workflows and reports — replacing manual database seeding
with a real, employee-facing upload-triggered sync.

**Scope:** the complete Inventory Sync workflow — six upload slots
(Tekion Unsold, Tekion Sold, Keyper, MDD, RecovR, RapidRecon), a thin
orchestration layer reusing the existing reconciliation engine
unmodified in its business logic, one new write endpoint, and the
Inventory Sync page wired to real data. Per this sprint's own explicit
exclusions: no authentication, no Task/Recommendation write APIs, no
Requests/Trade-Ins/Transportation, no notifications, no AI, no cloud
deployment, no security hardening, no Sprint 5 work.

**A naming note, resolved before implementation began, not silently:**
this sprint's kickoff titled itself "Phase 4 — Sprint 4," which would
have collided with `PRODUCT.md`'s existing Phase 4 (Dealer Trades) —
content this sprint explicitly excludes. Per the product owner's
direction, this was resolved as a documentation-only step *before* any
Sprint 4 code: `PRODUCT.md`'s Phase 3 roadmap paragraph was amended to
name Sprints 1–4 explicitly (Employee/Dealership backend, read API,
frontend integration, and now Inventory Sync) as real, demonstrated
scope growth within Phase 3, not a new phase. This sprint is named
"Phase 3, Sprint 4" throughout, consistent with `PHASE_3_SPRINT_1/2/3_REVIEW.md`.

---

## 1. Sprint Summary

**Added — backend:**
- `sync/pipeline.py` (new) — `run_inventory_sync()`, the thin
  orchestration layer coordinating an upload-triggered sync. Calls the
  exact same importer/`sync/reconciler.py`/`rules/`/`reports/writer.py`
  functions `main.py` already drives; `main.py` itself is untouched.
  Handles the one real architectural gap `main.py` never had to:
  building a coherent result from a *partial* set of uploaded sources
  (see Section 3).
- `sync/upload_validation.py` (new) — per-slot required-column checks
  (`pd.read_csv(path, nrows=0)`, header-only) so a file dropped in the
  wrong upload slot fails with a specific, readable reason before
  anything persists, rather than a downstream `KeyError` or a silently
  wrong reconciliation.
- `queries/inventory_sync.py` (new) — `list_pending_identities()` (the
  Exceptions panel's real data source) and `sync_run_history()` (groups
  `sync_run` rows into batches by shared `started_at` — a derived read,
  not a new stored concept; see Section 3).
- `api/routers/inventory_sync.py` (new) — `POST /inventory-sync/run`
  (this project's first write route), `GET /inventory-sync/history`,
  `GET /inventory-sync/exceptions`.
- `api/dtos.py` — `PendingIdentityDTO` and `SyncRunDTO` implemented for
  the first time (both already specified in `API_CONTRACTS.md`, neither
  previously built); new `SyncRunBatchDTO`, `SyncSummaryDTO`.
- `database/repository.py`'s `sync_run()` context manager gained an
  optional `started_at` passthrough (one parameter; `start_sync_run`
  already accepted it, the convenience wrapper just didn't expose it).
  Every existing caller (`main.py`, every prior test) is byte-for-byte
  unaffected — the default remains `None`.
- `tests/test_sync_pipeline.py` (11 tests), `tests/test_api_inventory_sync.py`
  (6 tests) — see Section 2.

**Added — frontend:**
- `frontend/src/api/inventorySync.ts`, plus `apiPostForm()` in
  `client.ts` (this frontend's first non-GET call) and new wire types in
  `types.ts` (`PendingIdentityDTO`, `SyncRunDTO`, `SyncRunBatchDTO`,
  `SyncSummaryDTO`), following the exact per-domain-module + `useApi`
  pattern Sprint 3 established.
- `frontend/src/dashboards/InventorySync.tsx` — rewritten in place (same
  header/stats-bar/two-column layout) to upload real files and render
  real data. See Section 4 for exactly what was preserved vs. corrected.

**Changed:**
- `PRODUCT.md` — Phase 3 roadmap paragraph amended (Section, above).
- `api/app.py` — registers the new router; docstring/version updated to
  note this project's first write route exists now.
- `api/README.md` — `python-multipart` added to the install command (a
  real new dependency, required by FastAPI's file-upload form fields;
  caught by the test suite failing to import until installed).

**No change to:** `main.py`, `sync/reconciler.py`, `sync/matcher.py`,
`rules/validation.py`, any existing migration, any existing DTO's
shape, or any CSV report's content/format when run via the CLI path.

---

## 2. Definition of Done Verification

**Backend regression: 309/309 tests passing** (292 before this sprint +
17 new — 11 in `test_sync_pipeline.py`, 6 in `test_api_inventory_sync.py`),
run via `PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"`.
Covers every item in this sprint's own checklist: empty database,
first-time import, repeat import (idempotency, with two real caveats —
see Section 3), vehicle additions/updates, a vehicle silently absent
from a later upload (confirmed *not* treated as removal — see Section
3), task generation, recommendation generation, `SyncRun` history
grouping, and the exact partial combinations named in the brief (Tekion
Unsold only; +Keyper; +Keyper+MDD; full six-source upload) plus the API
layer's upload validation, write-then-read consistency, and empty-state
responses.

**Live, in-browser, real-multipart verification** (not just the test
suite): started a real `uvicorn` instance and the real Vite dev server,
uploaded the same six synthetic fixture CSVs through the six real
`<input type="file">` slots via the browser, and clicked the real "Run
Sync Now" button. Confirmed:
- The button is disabled with no files selected, enabled once at least
  one is chosen.
- A successful run returns `19 vehicles processed`, `3 exceptions`,
  `3 tasks generated`, `1 recommendation` — exactly matching the
  fixture-derived expectations already encoded in
  `tests/test_sync_pipeline.py`'s `FirstImportTest`.
- The Exceptions panel populated with the three real `PendingIdentity`
  rows (`555555`, `#ODD1`, `784`) and their real reasons.
- System Status and Run History updated with real per-source record
  counts and a real, correctly-grouped multi-source batch.
- No console errors at any point.
- Navigating to Vehicles List afterward shows the newly-synced test
  VINs with no code change needed there — Sprint 2's read endpoints
  already serve whatever `sync/pipeline.py` persists, confirming the
  "refresh Dashboard/Vehicles/Tasks/Recommendations" requirement is
  satisfied by the existing read API, not new work.

---

## 3. Architectural Decisions and Real Findings

### 3.1 Partial-source sync: empty-columned stand-ins, not a redesign

`main.py` calls all six loaders unconditionally; several downstream
functions (`build_tracker_install_tasks`, `find_tekion_sync_conflicts`,
`enrich_with_rapidrecon`) do a handful of *vectorized* column accesses
outside any `iterrows()` loop that would `KeyError` on a truly
columnless empty `DataFrame`. Resolved by having `sync/pipeline.py`
substitute an empty `DataFrame` carrying that source's real columns for
any source not uploaded this run — a valid-input-shape decision, zero
changes to `sync/reconciler.py`/`sync/matcher.py`/`rules/validation.py`.
Tekion Unsold and Tekion Sold are gated independently (either can be
present without the other; `persist_tekion_observations` already walks
each as two independent loops), matching this sprint's explicit
instruction that they remain independent slots.

**A real bug this surfaced, not present in `main.py`'s own usage:**
`generate_key_out_aging_recommendations` does `key_out_aging_df["aging_bucket"]`
unguarded — fine every time `main.py` calls it (a real Keyper export
always has at least one "Out" row in practice so far), but a genuine
`KeyError` when `key_out_aging` comes back from `reconcile_keyper_tekion`
as a truly empty, columnless `DataFrame` (no Keyper file this run, or a
Keyper file with zero "Out"-and-matched rows). Fixed at the call site in
`sync/pipeline.py` (`if len(key_out_aging): generate_key_out_aging_recommendations(...)`),
not inside `sync/reconciler.py` — this sprint's own scope commits to not
touching that module, and the guard belongs with the caller that
introduced the possibility of an empty input, not the callee.

### 3.2 Sync history is a derived read, not a new stored concept

`DATA_MODEL.md`'s `SyncRun` is explicitly per-source. Rather than adding
a `batch_id` column (a `DATA_MODEL.md` governance change not warranted
here), `sync/pipeline.py` stamps every source it processes in one
request with a shared `started_at` (via `sync_run()`'s new optional
passthrough, Section 1), and `queries/inventory_sync.py`'s
`sync_run_history()` groups by that shared value. Confirmed live: the
CLI path (`main.py`, unmodified) produces five separate one-source
batches in this same grouped view, since it has no shared-timestamp
concept — an honest, expected difference between the CLI and API
trigger paths, not a bug. Per-batch task/recommendation/exception counts
are deliberately **not** reconstructed retroactively for history entries
(no column ties a `task`/`recommendation` row back to the sync that
produced it — both are derived computations, not per-source imports,
per their own docstrings). Only the just-completed run's own response
carries that full summary; this is stated in `sync_run_history()`'s
docstring, not silently approximated.

### 3.3 RapidRecon: exactly the existing boundary, nothing further

`Upload → validate "VIN" column present → load_rapidrecon() → persist_rapidrecon_observations() (Event only) → done.`
No Vehicle field, no Task, no Recommendation — `persist_rapidrecon_observations`
already only ever wrote an `Event`, unchanged by this sprint.

**A real, pre-existing idempotency gap this sprint's testing newly
exercised, not introduced by it:** `persist_rapidrecon_observations` has
no diff-before-write at all — `SPRINT_3_REVIEW.md`'s diffing work
explicitly covered "four diffed sources" (tekion/keyper/mdd/recovr), not
RapidRecon. It re-writes one `rapidrecon_observed` `Event` per matched
VIN on every single run, forever. Combined with the already-documented
K80001/K80002 duplicate-sold-VIN idempotency gap
(`SPRINT_3_REVIEW.md`), a full six-source rerun against this project's
fixture set produces exactly 3 new `Event` rows, not zero —
`tests/test_sync_pipeline.py`'s `RepeatImportTest` asserts this exact,
understood delta rather than a false "fully idempotent" claim. Not
fixed here (would mean touching `sync/reconciler.py`, out of this
sprint's scope) — flagged as a real, concrete Sprint 5+ candidate.

### 3.4 Silence is not a removal

Per `DECISION_FRAMEWORK.md`'s root principle, a vehicle silently absent
from a later Tekion Unsold upload is not treated as sold, removed, or
otherwise changed — its last-known `tekion_status` stays exactly as it
was. Confirmed directly:
`tests/test_sync_pipeline.py::VehicleUpdateTest::test_a_vehicle_not_reasserted_keeps_its_last_known_state`.
This is existing behavior (the diffing functions were already built
this way), not new logic — but Sprint 4 is the first time a caller could
plausibly upload a *shrinking* source set run over run, so it's worth
this sprint recording the confirmation explicitly rather than assuming
it.

### 3.5 Report-type identification is slot-based, not content-sniffing

"Validate reports → identify report types" (the brief's own pipeline
diagram) is answered by which of the six explicitly labeled upload
slots a person chose, not by guessing from filename or content — the
same six real-world naming variations `utils/file_resolution.py`
already documents (timestamp-prefixed exports, etc.) would make
content-based auto-detection both unnecessary and a worse user
experience than an explicit choice. `sync/upload_validation.py`'s
column-presence check exists as the safety net for a file dropped in
the *wrong* slot, not as the primary identification mechanism.

---

## 4. Inventory Sync Page: What Was Preserved vs. Corrected

Per this sprint's own instruction (and Sprint 3's established
precedent): integrate the existing mockup, don't redesign it; where the
mockup shows something with no backend equivalent, render the real
backend truth instead of inventing UI.

**Preserved exactly:** page header, stats-bar-of-four-cards layout,
two-column body (Exceptions table left, System Status/Detected
Changes/Run History right), all icon components, all Tailwind class
structure.

**Corrected, not fabricated:**
- The mockup's "Sync Run Selector" (two fixed, hardcoded tabs — "7:02
  AM" / "12:31 PM" — each with a pre-baked exceptions/tasks snapshot)
  assumed a per-run history richer than `SyncRun` actually stores (see
  Section 3.2). Replaced with a real "Recent Sync Runs" strip driven by
  `GET /inventory-sync/history` — showing what a batch of `SyncRun` rows
  actually carries (timestamp, sources, overall status), not fabricated
  per-run stats.
- The Exceptions table's assignable `status`/`suggestedAction` workflow
  (Pending/In Review/Task Created/Auto-Resolved, an editable Controller
  review queue) has no backend behind it at all —
  `FRONTEND_BACKEND_RECONCILIATION.md` already named this gap.
  Replaced with the real, persisted `PendingIdentity` rows via the
  already-governed `PendingIdentityDTO` (raw identifier, identifier
  type, first/last observed) — real data, honestly scoped to what it
  actually is: a list of unresolved identifiers, not an assignable
  workflow.
- The System Status panel's mock `SYSTEMS` array is replaced with
  `GET /dashboard`'s real `connected_systems` — the same derived
  Connected-Systems read every other screen in this app already uses,
  reused here rather than duplicated.
- The Stats Bar and Detected Changes panel reflect the most recent sync
  *in this browser session* (`SyncSummaryDTO`'s own fields) — not
  persisted, not reconstructed after a reload, for the reason given in
  Section 3.2.

**Added, not present in the original mockup at all:** the six-slot
upload section itself (the mockup had no file inputs anywhere — "Run
Sync Now" was a styled button with no handler). This is new
functionality the brief explicitly asked for, not a mockup correction.

---

## 5. A Note on the Environment

A stray `python.exe` process (PID varies by machine) was already bound
to port 8000 in this development environment when this sprint's
verification began, serving a stale (pre-Sprint-4) instance of the API.
Rather than stop a process this session didn't start and couldn't fully
account for, verification ran a fresh instance on port 8001 with a
temporary `frontend/.env.local` override (`VITE_API_BASE_URL`, the
mechanism `client.ts` already documents for exactly this purpose) — both
cleaned up after verification completed. Worth a human checking whether
that port-8000 process is still needed.

---

## 6. Recommendations for Sprint 5

1. **RapidRecon idempotency** (Section 3.3) — a real, now-concretely-
   understood gap, not urgent (RapidRecon's own `Event`s are additive
   context, not state-changing), but worth fixing the next time
   `sync/reconciler.py` is touched for any reason.
2. **Authentication** — `PRODUCT.md`'s own named trigger, raised again
   at the close of Sprints 1–3 and still not built. This sprint adds
   this project's first *write* route with no permission model behind
   it at all (per this sprint's own explicit exclusion of
   authorization) — the next sprint that adds a write path should not
   also be the one after that raises this a fourth time without acting.
3. **A `GET /employees` endpoint** — unchanged recommendation from
   Sprint 3, still not built, still resolves three separate display
   gaps at once.
4. **A lightweight frontend test setup (Vitest)** — unchanged
   recommendation from Sprint 3. This sprint's frontend verification was
   again entirely manual/browser-driven (Section 2); acceptable once
   more for a sprint reusing one proven pattern, materially less
   acceptable now that a real write path (file upload, multipart,
   validation-error rendering) exists with zero automated frontend
   coverage.
5. **Sync-run history's per-batch summary gap** (Section 3.2) — if a
   real operational need appears for reconstructing historical
   exception/task/recommendation counts per batch, that's a deliberate
   schema decision to make then (e.g. a `sync_run_id` FK on `task`/
   `recommendation`), not something to retrofit speculatively now.
6. **Requests, Trade-Ins, Transportation** remain exactly where
   `FRONTEND_BACKEND_RECONCILIATION.md` left them — untouched, per this
   sprint's own explicit exclusions.

**Stopping here, per this sprint's own scope.** This review does not
begin Sprint 5.
