# Sprint 3 Review — Historical Diffing, PendingIdentity Promotion, SyncRun Provenance

Sprint 3 covers Slices 3 and 4 of `IMPLEMENTATION_PLAN.md`, built on top
of the `v0.2.0` baseline (Phase 2 Sprint 2 / Slice 2). This is also the
first sprint built explicitly against `DECISION_FRAMEWORK.md`, the
design-review document produced ahead of this sprint — several of this
review's design decisions cite it directly, since it's what this sprint
was meant to validate against real implementation, not just theory.

## Sprint objective

Make persistence actually pay for itself. Slices 1–2 wrote every
observation unconditionally, every sync, which meant `Event` was
already accumulating duplicate noise rather than real history. Slice 3
adds diff-before-write across all four discrete `Vehicle` status fields
(`tekion_status`, `keyper_status`, `mdd_status`, `recovr_status`) so an
`Event` is written only when something actually changed, plus
`PendingIdentity → Vehicle` promotion — the system's first genuine
state transition, decided during Sprint 2's design discussion but
deliberately deferred to this sprint. Slice 4 adds `SyncRun`
provenance, so every `Event` traces back to the sync that produced it.

## Completed work

**Diffing (`sync/reconciler.py`, all four persistence functions):**
- `_persist_keyper_observation()`, `persist_tekion_observations()`,
  `persist_mdd_observations()`, `persist_recovr_observations()` — each
  now compares a new observation against the most recent `Event` of the
  same `event_type` for that VIN (not against `vehicle`'s current-state
  field — see "Unexpected discoveries" for why that distinction turned
  out to be load-bearing) before deciding whether to write a new
  `Event`. `vehicle`'s field is still upserted unconditionally either
  way — it's a cache of current belief, not history.
- `database/repository.py` — new `get_last_event_detail_fields()`, the
  correct basis for this comparison; `get_pending_identity()` and
  `resolve_pending_identity()` for promotion.
- Tekion's diff key is `(tekion_status, stock_number)`, not
  `tekion_status` alone — a deliberate design decision (see "Problem
  solving" below), not an implicit choice.
- RapidRecon remains entirely outside diffing, writing every sync
  unconditionally — pressure-tested at kickoff and confirmed for two
  *separate* reasons, not one: `DIS`/`DIR` are continuously-drifting
  counters (same class as `days_out`); `Step`/`Note` are discrete
  claims that would in principle qualify for diffing, but stay
  exempt because `ARCHITECTURE.md` already scopes RapidRecon as "not
  yet a state provider" — a different, already-governed boundary, not
  a diffing-philosophy exemption of its own.

**Promotion (`sync/reconciler.py`):**
- `_promote_pending_identity_if_resolved()` — called at both of
  `reconcile_keyper_tekion`'s successful-resolution points. A no-op
  unless a `pending_identity` row already exists, `pending`, for the
  exact raw identifier that just resolved. Reuses the same
  identity-resolution match the caller already made rather than
  introducing a separate, looser heuristic — per
  `DECISION_FRAMEWORK.md`'s "reconciliation is not authorship."

**SyncRun (`database/migrations/0003_sync_run.sql`,
`database/repository.py`, `main.py`):**
- `sync_run` table — one row per source per pipeline run.
- `start_sync_run()`, `complete_sync_run()`, `fail_sync_run()`, and a
  `sync_run()` context manager giving each source's pass **real
  transactional semantics** (see "Problem solving"): `complete` means
  everything that source wrote this run committed; `failed` means none
  of it did. This required removing the per-statement `conn.commit()`
  that `upsert_vehicle`/`insert_event`/`upsert_pending_identity`/
  `resolve_pending_identity` had each done individually since Slice 1.
- `main.py` wraps all five sources' passes in `sync_run(...)`.

**Tests:** [`tests/test_database_slice3.py`](tests/test_database_slice3.py)
(10 tests — idempotency across the four diffed sources, single-field
diff, promotion, and the documented duplicate-sold-VIN exception) and
[`tests/test_database_slice4.py`](tests/test_database_slice4.py) (8
tests — SyncRun provenance and transactional rollback/commit
semantics). One Slice 1 test
(`test_rerunning_with_identical_input_produces_no_duplicate_events`,
formerly `test_rerunning_without_diffing_writes_duplicate_events_not_errors`)
updated in place — it was written at Sprint 1 specifically to be the
canary for this exact moment.

## Definition of Done verification

Per `IMPLEMENTATION_PLAN.md` Slice 3:

| Requirement | Status | Evidence |
|---|---|---|
| Same input twice produces zero new Events | **Met, with one documented exception** | `test_second_identical_run_produces_zero_new_events_for_diffed_sources`; the duplicate-sold-VIN case (`1TESTVIN000080001`) is a known, accepted, explicitly-tested exception — see "Problem solving." |
| Exactly one changed field produces exactly one new Event | **Met** | `test_recovr_status_flip_for_one_vehicle_produces_exactly_one_new_event`. |
| A previously-pending identifier that resolves promotes to a real Vehicle + Event | **Met** | `test_later_resolution_promotes_pending_identity_to_vehicle`; does not repeat on a third run (`test_promotion_does_not_repeat_on_a_third_run`). |
| CSVs remain byte-identical | **Met** | `test_regression.py`'s full suite unchanged and passing; end-to-end `main.py` smoke test against all five fixture sources produces correct reports. |

Per `IMPLEMENTATION_PLAN.md` Slice 4:

| Requirement | Status | Evidence |
|---|---|---|
| One SyncRun row per source with correct counts | **Met** | `test_one_sync_run_per_source_with_correct_records_processed`; confirmed again via a real `main.py` run against fixture data. |
| Every Event has a valid sync_run_id; zero orphaned Events | **Met** | `test_every_event_has_a_valid_sync_run_id_no_orphans` (SQL-level check — see "Unexpected discoveries" for why not a Python-side set comparison). |
| SyncRun reaches "complete" only on successful commit | **Met, strengthened beyond the original slice scope** | Real transactional semantics (see "Problem solving") — `TransactionalIntegrityTest`'s 4 tests, including a forced mid-source failure that leaves zero partial writes committed. |

## Regression test status

- Start of sprint (Sprint 2 close): 119 tests, all passing.
- End of sprint: **137 tests, all passing** — 18 net new
  (10 in `test_database_slice3.py`, 8 in `test_database_slice4.py`),
  plus one existing Slice 1 test updated in place (not counted as new).
- Full suite re-run after every logical milestone, not just once at the
  end: Keyper diffing + promotion (119, unchanged count, behavior
  verified), Tekion diffing (119), MDD + RecovR diffing (119), Slice 3
  tests added (129), the diff-basis bug found and fixed (129, same
  count, correctness re-verified), SyncRun migration + repository +
  main.py wiring (129), Slice 4 tests added (137).

## Architectural assumptions validated

1. Diffing against the four named discrete fields, not continuously-
   drifting values — held, as `IMPLEMENTATION_PLAN.md` anticipated.
2. `PendingIdentity` promotion reusing existing identity-resolution
   logic rather than a new heuristic — held; the ambiguous-last-6 test
   case resolves correctly once a later "sync" removes the ambiguity.
3. RapidRecon's exemption from diffing — held, but only after
   correcting the reasoning mid-kickoff (see "Problem solving").

## Problem solving

This sprint surfaced more genuine design tension than either prior
sprint, entirely expected given it's the first sprint built against
`DECISION_FRAMEWORK.md` under real implementation pressure rather than
design-review discussion. Each was surfaced and resolved explicitly
with the product owner before proceeding, not silently decided:

1. **Tekion's diff key.** A literal reading of `IMPLEMENTATION_PLAN.md`'s
   "diff on the four named fields" would have silently dropped the
   duplicate-sold-VIN contradiction (`tekion_sync_conflicts.csv`'s own
   test fixture) as a false no-op repeat. Resolved: Tekion diffs on
   `(tekion_status, stock_number)` together — the claim Tekion actually
   makes each time includes which stock number was sold, not just the
   status label. Keyper/MDD/RecovR have no equivalent secondary field
   and stay single-field.
2. **The RapidRecon exemption, re-examined.** Initially stated as one
   blanket exemption; pressure-testing against `DECISION_FRAMEWORK.md`'s
   claims test split it into two different justifications (`DIS`/`DIR`
   are continuously-drifting; `Step`/`Note` are deferred to an
   already-governed `ARCHITECTURE.md` boundary, not a diffing-philosophy
   exemption). Conclusion held, but the reasoning was corrected before
   proceeding.
3. **The diffing bug: Vehicle's field cache is the wrong comparison
   basis.** The idempotency test caught this directly — a VIN touched
   by two different observations sharing one `Vehicle` field within a
   single run (Tekion's master-list and sold-list writes both target
   `tekion_status`) generated 2 spurious Events on every rerun, forever,
   because each write's "previous value" comparison was polluted by the
   sibling write from earlier in the same run. Fixed by comparing
   against the most recent `Event` of the matching type instead of
   `vehicle`'s blended current-state field — a general fix, not a
   Tekion-specific patch, since it's a strictly more correct basis for
   every diffed source and happens to be behavior-identical to the old
   approach for Keyper/MDD/RecovR (which never had this compounding
   problem to begin with).
4. **The duplicate-sold-VIN case remains imperfectly idempotent, by
   deliberate choice.** Even after fix #3, a VIN with *two rows of the
   same `event_type`* in one sync (the K80001/K80002 fixture — the same
   VIN sold under two different stock numbers in one Tekion export)
   still refires both Events on every rerun. Fully solving this would
   require comparing each run's whole ordered sequence of same-type
   observations against the previous run's sequence — real additional
   machinery. Decided, explicitly, not to build it: this is an
   internally contradictory upstream input, not a normal operational
   state, and `tekion_sync_conflicts.csv` already surfaces it to a human
   daily regardless of anything in the database. Per
   `DECISION_FRAMEWORK.md`'s "don't build ahead of a demonstrated
   workflow" — documented as accepted debt (see the class docstring in
   `tests/test_database_slice3.py` and `persist_tekion_observations`'
   docstring), not silently hidden.
5. **SyncRun's transactional strength.** `IMPLEMENTATION_PLAN.md`'s risk
   note describes real transactional wrapping, but every write function
   had committed individually since Slice 1 — no actual multi-statement
   transaction existed to roll back. Decided to build real atomicity
   (Option B over a bookkeeping-only alternative): a `SyncRun` marked
   `failed` now means *nothing* from that attempt persisted, giving the
   table a clean semantic contract instead of a label that could
   describe a partially-committed run. This meant removing per-call
   commits from four repository functions — verified not to break any
   existing test, since all Slice 1–3 tests read via the same open
   connection that sees its own uncommitted writes.

## Unexpected discoveries

- **The idempotency test itself needed correction, not the code.**
  RapidRecon writing a new Event on an identical rerun is correct,
  by-design behavior, but the first draft of the idempotency test
  wrongly asserted zero new events overall. Fixed the test's scope, not
  the code.
- **A Python-vs-SQL type-affinity trap in the orphan-Event check.**
  `event.sync_run_id` is `TEXT`-affinity (unchanged since Slice 1, to
  preserve the free-form string `sync_run_id` convention every existing
  test already relies on); `sync_run.sync_run_id` is a real `INTEGER`
  PK. SQLite's own comparison rules correctly treat `'1'` and `1` as
  equal inside a query, but a naive Python-side comparison of two sets
  pulled from each column does not. Caught by a failing test, fixed by
  doing the orphan check as a single SQL query instead of a Python set
  comparison — documented in both the test and `start_sync_run()`'s
  docstring so a future contributor doesn't rediscover this the hard
  way.

## Technical debt introduced

- **Duplicate-sold-VIN idempotency gap** (see "Problem solving" #4) —
  deliberately accepted, documented in code and tests, revisit only if
  a real workflow demonstrates it matters (e.g. an unfixed Tekion
  contradiction persisting for weeks floods a future dashboard activity
  feed once Slice 7 builds one).
- **No hard FOREIGN KEY from `event.sync_run_id` to
  `sync_run.sync_run_id`**, despite `sync_run` now existing — adding one
  would break Slices 1–3's established free-form-string testing
  convention. "No orphaned Events" is proven at the application/test
  level instead, per `IMPLEMENTATION_PLAN.md`'s own success-criteria
  wording ("an explicit assertion in tests," not a schema constraint).
- **`issues_found` and `tasks_generated` on `sync_run` are populated as
  `NULL`, always** — accurate accounting requires Task/Recommendation
  logic that doesn't exist until Slices 5–6. Not computed speculatively.

## Lessons learned

- **A blended current-state cache is the wrong basis for "did this
  claim change," the moment more than one observation can write to it
  within a single run.** This is the sprint's central lesson, and it's
  a direct, concrete validation of `DECISION_FRAMEWORK.md`'s own
  distinction between derived current state and the history behind
  it — the bug only existed because the diff check was, in effect,
  comparing against a derived read instead of against history itself.
- **The permanent idempotency test suite is worth writing before
  believing a diffing implementation is correct** — the Vehicle-cache
  bug (Problem solving #3) was invisible to every other test in the
  suite (including the existing Slice 1/2 tests, which never ran the
  same source twice) and was only caught because Slice 3's own DoD
  required an explicit rerun test.
- **Not every open design question needs the same resolution.** The
  duplicate-sold-VIN gap and the SyncRun transactional-strength
  question look superficially similar (both are "should we build more
  machinery for correctness") but resolved oppositely — one because a
  real, already-existing report already covers the gap and no workflow
  asks for more; the other because the guarantee's whole purpose
  (SyncRun's meaning) collapses without it. The same governing
  principle, applied honestly, doesn't always point the same direction.

## Risks

- Carried forward, still open: no CI (suite must be run manually).
- **New this sprint:** the duplicate-sold-VIN idempotency gap (accepted,
  documented) means anyone building Slice 7's dashboard activity feed
  should be aware that an unfixed Tekion data contradiction could, in
  principle, generate a small amount of repeat noise in the Event
  stream for that specific pathological case — worth a one-line
  awareness note when that slice is scoped, not a blocker now.

## Recommendations for the next slice

- Slice 5 (Task generation) is the first slice where the database
  becomes load-bearing — the diffing and promotion machinery this
  sprint built is exactly what makes "a Task closes itself when its
  condition resolves" possible. No design gap surfaced this sprint that
  changes Slice 5's scope as already written.
- When Slice 7 builds the dashboard's recent-activity feed, revisit
  whether the duplicate-sold-VIN gap (Technical debt above) has become
  a real, observed nuisance in practice — if so, that's the
  demonstrated-workflow trigger `DECISION_FRAMEWORK.md` asks for before
  building sequence-aware diffing.
