# Sprint 1 Review — SQLite Foundation + Keyper Write Path

Sprint 1 covers Slice 1 of `IMPLEMENTATION_PLAN.md`, plus the
environment work that had to happen before any of it could run on
this machine. This is a permanent record of what was done, what it
proved, and what it didn't — written so a future contributor can
understand the reasoning, not just diff the code.

Follows the standard sprint-review template established after this
sprint, applied retroactively so Sprint 1 isn't structurally
inconsistent with the sprints that follow it.

## Sprint objective

Per `IMPLEMENTATION_PLAN.md`'s Slice 1 ("SQLite foundation +
single-source write path"): prove the write-and-persist pattern works
at all, in complete isolation from anything user-facing. Concretely:
`database/schema.sql` (or equivalent) for `Vehicle` and `Event` only;
a minimal repository layer with upsert/insert; Keyper's processing
path additionally writing to it; zero change to any existing report
output. Nothing about Tekion, Sold, MDD, RecovR, or RapidRecon was in
scope — that's Slice 2.

Ahead of that, two environment blockers identified during onboarding
had to be resolved first: no Python interpreter existed on this
machine, and `config/settings.py`, `utils/file_resolution.py`, and
`main.py` all hardcoded `/mnt/user-data/...` paths specific to this
project's original development sandbox, not this machine.

## Completed work

**Environment**
- Installed Python 3.12.10 via winget, plus `pandas` 3.0.5 and
  `openpyxl` 3.1.5.
- Replaced the hardcoded sandbox paths with `LOTSYNC_UPLOADS_DIR`,
  `LOTSYNC_CONFIG_PATH`, and `LOTSYNC_OUT_DIR` environment-variable
  overrides, each defaulting to a repo-relative `data/` subfolder
  (`utils/file_resolution.py`, `config/settings.py`, `main.py`).
  Created `data/uploads/` and `data/outputs/` locally.

**Slice 1**
- [`database/migrations/0001_initial.sql`](database/migrations/0001_initial.sql)
  — `vehicle` and `event` tables, matching `DATA_MODEL.md`'s full
  decided column shape (not a reduced subset — see "Architectural
  assumptions validated" below for why). Indexes on `event.vin`,
  `event.sync_run_id`, `event.event_type` per the plan's Technical
  Risks section, from this migration onward rather than added
  reactively later.
- [`database/repository.py`](database/repository.py) — `connect()`
  (opens a connection, applies any pending numbered migration files,
  idempotent to re-running), `upsert_vehicle()` (partial upsert — only
  supplied columns are touched, via `ON CONFLICT ... DO UPDATE SET`),
  `insert_event()` (always inserts; no change-detection yet — that's
  Slice 3).
- [`sync/reconciler.py`](sync/reconciler.py) — `reconcile_keyper_tekion()`
  gained two new optional, defaulted-to-`None` parameters, `db_conn`
  and `sync_run_id`. When a connection is supplied, every Keyper record
  that resolves to an actual VIN (the `fully_verified`, `key_out_aging`,
  and `sold_key_not_removed_from_keyper` cases) additionally upserts a
  `Vehicle` row and writes an `Event`, via a new
  `_persist_keyper_observation()` helper. No existing return value,
  and no CSV-producing code path, changed.
- [`main.py`](main.py) — opens a database connection via
  `database.repository.connect()` and passes it through, alongside the
  otherwise-unchanged CSV pipeline.
- [`DATA_MODEL.md`](DATA_MODEL.md) and [`models/event.py`](models/event.py)
  — added `event_id` as `Event`'s surrogate primary key (see
  "Unexpected discoveries"). This is the one governance-document change
  in this sprint, made under the "implementation reveals a genuine
  architectural flaw" trigger — a missing primary key isn't a design
  preference, it's a gap a working schema can't function without.
- [`database/__init__.py`](database/__init__.py) — docstring updated;
  it previously described persistence as not-yet-acted-on, which is no
  longer accurate.
- [`tests/test_database_slice1.py`](tests/test_database_slice1.py) —
  10 new tests (detailed under "Definition of Done verification").
- [`tests/README.md`](tests/README.md) — documents the new test file
  alongside `test_regression.py`.

## Definition of Done verification

Per `IMPLEMENTATION_PLAN.md` Slice 1:

| Requirement | Status | Evidence |
|---|---|---|
| Running `main.py` produces byte-identical CSVs to the pre-Phase-2 baseline | **Met** | Verified two ways: (1) `test_regression.py`'s 30 assertions against `reconcile_keyper_tekion()`'s report output all still pass unmodified, calling it exactly as before (`db_conn` omitted); (2) a new test directly compares `reconcile_keyper_tekion()`'s four report DataFrames with `db_conn` supplied vs. omitted and asserts they're identical (`test_report_output_identical_with_and_without_db_conn`). No literal two-CSV-directory byte-diff was performed, since no pre-Phase-2 CSV snapshot was retained — the DataFrame-equality test is the stronger check, since it isolates the exact function in question rather than the whole pipeline. |
| A SQLite file now exists with Vehicle/Event rows reflecting Keyper's pass | **Met** | Manually verified against the synthetic fixtures run through `main.py` end-to-end: 6 `vehicle` rows, 6 `event` rows, matching the 6 Keyper records that resolve to a real VIN (`K30001`, `K30002`, `K30003`, `099999`→`K40001`, `K30099`, `K30005`). Automated in `test_vehicle_rows_match_only_vin_resolvable_keyper_records`. |
| Full regression suite passes | **Met** | 91/91, see "Regression test status" below. |
| DB row counts consistent with Keyper's import (accounting for excluded non-vehicle keys) | **Met** | `GOLF CART` (non-vehicle) and `ZZ00001` (out-of-scope store) never reach the DB, same as they never reach any report — confirmed by count (6, not 8 or 14) and by `test_no_vehicle_row_for_unresolvable_identity_records` explicitly asserting the 5 unresolved-identity records (`K30006`, `K30007`, `784`, `#ODD1`, `555555`) are absent too. |

## Regression test status

- Baseline before any Sprint 1 change: 81 tests, all passing.
- After environment/path changes only: 81/81, unchanged — confirms the
  path changes touched no business logic.
- After wiring `db_conn`/`sync_run_id` into `reconcile_keyper_tekion`:
  81/81, unchanged — confirms the reconciler change was pure addition
  before any new tests were even written.
- Final, with `test_database_slice1.py` added: **91/91 passing.**
- The regression suite grew this sprint, per
  `IMPLEMENTATION_PLAN.md`'s Success Metrics ("the regression test
  count only grows, sprint over sprint").

## Architectural assumptions validated

- **The additive pattern works exactly as designed.** Passing
  `db_conn=None` (every pre-Slice-1 call site) reproduces the original
  function's behavior with zero database activity; passing a real
  connection adds persistence without touching a single existing
  return value. This was the entire point of Slice 1 and it held.
- **SQLite's partial-upsert pattern (`ON CONFLICT DO UPDATE SET
  <only the supplied columns>`) is sufficient for the multi-source
  Vehicle model.** This was untested until now — `DATA_MODEL.md`
  assumed Tekion, Keyper, MDD, and RecovR would each update their own
  slice of one `Vehicle` row without clobbering the others, but that
  was a design intent, not a proven mechanism. Confirmed directly:
  upserting `stock_number` after `keyper_status` leaves `keyper_status`
  untouched (see `test_upsert_vehicle_partial_update_does_not_clobber_other_columns`).
- **The numbered-migration-file convention is viable with zero
  tooling.** `apply_migrations()` is ~15 lines against the stdlib
  `sqlite3` module — no migration framework was needed to satisfy the
  plan's "numbered SQL migration files from day one" recommendation.
- **Building the full `Vehicle`/`Event` column shape now, populating
  only a subset, is the right call.** The plan's "no speculative
  schema" principle is about not adding columns a slice doesn't need
  — it is not a reason to under-build a table shape `DATA_MODEL.md`
  already decided in full. Columns like `tekion_status` and
  `dealership_id` exist now, NULL, ready for Slice 2 onward, rather
  than requiring an `ALTER TABLE` later.

## Unexpected discoveries

- **`DATA_MODEL.md`'s `Event` table had no primary key.** Every other
  model with no natural unique key either has one modeled explicitly
  (`Vehicle.vin`, `Task.task_id`) or wasn't examined at the SQL-schema
  level until now. `Event` was the one gap. Fixed by adding `event_id`
  to both `DATA_MODEL.md` and `models/event.py`.
- **No Python interpreter, and sandbox-specific hardcoded paths.**
  Neither was a code defect — both were artifacts of this project's
  original development environment not matching its actual deployment
  target (a local Windows machine, per `PRODUCT.md`'s "Deployment
  scope"). Worth naming explicitly since nothing in `ARCHITECTURE.md`
  or `IMPLEMENTATION_PLAN.md` flagged this as a Sprint 1 prerequisite.

## Technical debt introduced

- **Duplicate Events on every rerun.** Slice 1 has no change-detection
  (Slice 3's job) — running the same Keyper export through twice
  writes two Events per vehicle, not one. Documented and pinned down
  by a permanent test
  (`test_rerunning_without_diffing_writes_duplicate_events_not_errors`),
  not a silent gap — but the `event` table will accumulate redundant
  rows for as long as Slice 3 hasn't landed.
- **Unconstrained foreign-key-shaped columns.** `event.sync_run_id`,
  `event.actor_employee_id`, and `event.dealership_id` exist as plain
  columns with no `FOREIGN KEY` constraint, since `sync_run`,
  `employee`, and `dealership` tables don't exist yet. Nothing enforces
  they'll ever resolve to something real once those tables do exist —
  worth a data-quality check when Slice 4 (SyncRun) lands.
- **The unresolved-identity Keyper population still isn't persisted.**
  By design (see "Lessons learned" below) — but it means today's
  `database/` state genuinely undercounts "keys LotSync knows about"
  relative to what Keyper itself reports, until Slice 2 makes an
  explicit decision about it.
- **Schema is explicitly provisional**, per the plan's own Slice 1 Risk
  note — real data in Slice 2 (five sources instead of one) may force
  a revision to columns or types decided here.

## Lessons learned

- **Scope boundaries need to be read at the row level, not just the
  function level.** The plan says Keyper's write path persists "every
  processed record," but read literally that would have preempted
  Slice 2's explicitly-scoped identity-resolution decision (what to do
  with Keyper records that never resolve to a VIN at all —
  `tekion_auto_generated_stock_number`, `unrecognized`,
  `ambiguous_last6_vin_multiple_matches`, `pending_dms_entry`,
  `out_and_unmatched_no_tekion_record`). Reading Slice 2's Risk section
  alongside Slice 1's Scope section resolved the apparent conflict:
  only VIN-resolvable records get persisted in Slice 1.
- **Exact fixture data beats inferring from documentation.** Writing
  `test_database_slice1.py`'s expected-VIN set from `keyper.csv` /
  `tekion_master.csv` / `tekion_sold.csv` directly (rather than from
  `tests/fixtures/README.md`'s prose summary) caught the exact VIN
  strings needed for precise assertions — the summary describes
  scenarios, not values.
- **The env-var-with-repo-relative-default pattern, already used for
  uploads/config/output paths, extended cleanly to the database path**
  (`LOTSYNC_DB_PATH`) with no new pattern needed.

## Risks

- **No version control.** This repository is not a git repository.
  Every change made this sprint — schema, code, docs — has no commit
  history, no diff trail, and no rollback mechanism beyond manually
  reconstructing prior file contents. `IMPLEMENTATION_PLAN.md` names
  "Rollback" as a per-slice success criterion; today that criterion is
  only satisfiable by hand. This risk grows, not shrinks, as more
  slices land across more files.
- **No automated test execution.** The regression suite exists and
  passes, but nothing runs it automatically — every verification this
  sprint was a manually-triggered `python -m unittest` run. A future
  change could silently break something between sessions if the suite
  isn't re-run.

## Recommendations for the next slice

- **Make the unresolved-identity decision in writing before touching
  the write path**, exactly as `IMPLEMENTATION_PLAN.md` already
  instructs: a `vehicle` row with `vin = NULL` plus whatever
  Keyper-side identifier is known, not a dropped row. This needs a
  schema change (a nullable `vin` can't remain the `PRIMARY KEY` as
  currently declared) — worth deciding the new primary key shape
  explicitly rather than discovering it mid-implementation.
- **Extend `_persist_keyper_observation`'s pattern to each of the four
  new sources individually** (Tekion, Sold, MDD, RecovR, RapidRecon),
  rather than one large multi-source function — keeps each source's
  Slice 2 contribution reviewable and testable in isolation, the same
  way Keyper's was.
- **Reuse `test_database_slice1.py`'s structure** (a pure-addition
  test + a row-count/content test per source) rather than inventing a
  new test shape — it's already proven out this sprint.
- **Consider initializing version control** before Slice 2 broadens
  the blast radius across five sources instead of one — noted as a
  risk above, not a blocker, but the case for it gets stronger as more
  slices land.
