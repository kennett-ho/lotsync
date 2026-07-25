# Sprint 2 Review — Full Source Coverage + PendingIdentity Capture

Sprint 2 covers Slice 2 of `IMPLEMENTATION_PLAN.md`, built on top of the
`v0.1.0` baseline (Phase 2 Sprint 1 / Slice 1). This is a permanent
record of what was built, what it proved, and what's next — written so
a future contributor understands the reasoning, not just the diff.

## Sprint objective

Extend Slice 1's write path from Keyper alone to all five sources —
Tekion, Sold, MDD, RecovR, RapidRecon — so a `Vehicle` row reflects
everything currently known about it, from every source, not just one.
Separately, capture Keyper's unresolved-identity population (auto-
generated placeholders, ambiguous last-6 matches) instead of leaving it
silently absent from persistence, via a new `PendingIdentity` model
decided during this sprint's pre-implementation design discussion (see
`DATA_MODEL.md`). Explicitly out of scope: detecting that a
`PendingIdentity` resolves and promoting it to a real `Vehicle` — that
state transition belongs to Slice 3.

## Completed work

**Design, decided before implementation began (see kickoff summary
in-conversation, now reflected in `DATA_MODEL.md` and
`IMPLEMENTATION_PLAN.md`):**
- `PendingIdentity` model — separate from `Vehicle`, upserted by
  `(source, raw_identifier)`, not insert-every-run like `Event`.
- RapidRecon writes an `Event` only, no new `Vehicle` status field —
  no field is defined for it in `DATA_MODEL.md`, and inventing one
  would repeat this project's own corrected mistake (unfounded
  thresholds standing in for a confirmed answer).
- MDD, RecovR, and RapidRecon all share one restraint: never create a
  new `Vehicle` row on their own, only annotate a VIN already known
  from Tekion — all three sources can span multiple stores/brands in
  one export, and Tekion's own import is this deployment's one
  reliably single-store source.

**Schema**
- [`database/migrations/0002_pending_identity.sql`](database/migrations/0002_pending_identity.sql)
  — the `pending_identity` table.
- [`database/repository.py`](database/repository.py) —
  `upsert_pending_identity()`, keyed by `(source, raw_identifier)`.

**Write paths, each a standalone function in
[`sync/reconciler.py`](sync/reconciler.py), each a no-op when
`db_conn` is `None`:**
- `_persist_pending_identity()` — wired into `reconcile_keyper_tekion`'s
  three exception branches (`tekion_auto_generated_stock_number`,
  `unrecognized`, `ambiguous_last6_vin_multiple_matches`).
- `persist_tekion_observations()` — walks the full `tekion_df` and
  `sold_df` independently of Keyper matching (Master/Unsold and Sold
  both write to the same `tekion_status` field; Sold runs second, so a
  vehicle in both ends up correctly showing "Sold" as current state).
- `persist_mdd_observations()` — `mdd_status = "not_paired"` for known
  VINs only; stays `NULL` (never inferred `"paired"`) for everything
  else, since MDD only ever supplies an exception list.
- `persist_recovr_observations()` — `recovr_status` set both ways
  (`"paired"`/`"not_paired"`) for known VINs, including sold ones (a
  raw source fact, not a business exclusion); short VIN fragments
  resolved via unique last-6 suffix match, skipped if ambiguous.
- `persist_rapidrecon_observations()` — `Event` only, per the design
  decision above.
- [`main.py`](main.py) — wires all four new functions into the
  pipeline, in source-load order, alongside the still-unchanged CSV
  path.

**Tests:** [`tests/test_database_slice2.py`](tests/test_database_slice2.py)
— 28 new tests across `PendingIdentity` capture, each source's write
path, and the cross-source identity guarantee. Added
[`tests/fixtures/synthetic/rapidrecon.csv`](tests/fixtures/synthetic/rapidrecon.csv)
(no RapidRecon fixture existed before this sprint — `test_regression.py`
never exercised it).

## Definition of Done verification

Per `IMPLEMENTATION_PLAN.md` Slice 2:

| Requirement | Status | Evidence |
|---|---|---|
| Every Vehicle a source mentions has that source's contribution reflected in the DB | **Met** | End-to-end `main.py` smoke test against all five fixture sources: 17 `vehicle` rows, every status field populated exactly as expected per VIN (verified by direct DB inspection, not just unit assertions). |
| Every unresolved-identity Keyper record has a `PendingIdentity` row | **Met** | 3 rows (`784`, `#ODD1`, `555555`), matching `data_quality_exceptions.csv`'s applicable population exactly. |
| CSVs remain byte-identical to baseline | **Met** | Every new write path is a side-effect-only function with no return value feeding any report; `test_regression.py`'s full 30-assertion suite still passes unmodified, and each new persistence function has its own pure-addition/no-mutation test. |
| DB Vehicle count consistent with the union of VINs across all five sources | **Met** | 17, confirmed both by direct count and by `test_vehicle_count_is_union_not_sum_across_all_five_sources`. |
| `PendingIdentity` count matches `data_quality_exceptions.csv` | **Met** | 3, exact match. |
| Zero CSV regression | **Met** | See above. |

## Regression test status

- Start of sprint (Sprint 1 close): 91 tests, all passing.
- End of sprint: **119 tests, all passing** — 28 net new
  (`test_database_slice2.py`), plus one existing test fixed (see
  "Unexpected discoveries").
- Full suite re-run after every source's write path landed, not just
  once at the end — PendingIdentity (96), Tekion (102), MDD+RecovR
  (111), RapidRecon (115), cross-source test (119).

## Architectural assumptions validated

All five assumptions named in this sprint's kickoff summary held up
under implementation with no surprises requiring reversal:

1. RapidRecon Event-only, no new field — held; no code anywhere
   needed a Vehicle-level RapidRecon status.
2. RapidRecon annotates existing Vehicles only — held; the fixture's
   deliberately-unknown VIN (`1TESTVIN999999999`) was correctly
   skipped with zero side effect.
3. `mdd_status` stays `NULL`, never inferred `"paired"` — held;
   confirmed directly (`1TESTVIN000000002` known from Tekion, absent
   from MDD's file, stays `NULL`).
4. `PendingIdentity` upserted by `(source, raw_identifier)` — held;
   `first_observed_at` frozen and `last_observed_at` advancing on
   re-observation, confirmed by direct assertion.
5. Tekion Master/Unsold and Sold share one `tekion_status` field —
   held; the sync-conflict fixture VIN (in both files) correctly
   resolved to `"Sold"` as current state while preserving both
   observations as separate Events.

One additional assumption emerged **during** implementation, not
anticipated at kickoff: RecovR needed the exact same "known-Vehicle-
only, resolve-or-skip" treatment as RapidRecon and MDD, for the same
underlying reason (its export can also span a multi-brand "Kia
umbrella" account per `importers/recovr.py`). This wasn't listed as a
kickoff assumption because it was initially planned as a reuse of
`build_tracker_install_tasks`'s existing scoping logic; implementation
revealed a cleaner, more uniform design instead (see "Lessons learned").

## Unexpected discoveries

- **A latent fragility in Slice 1's own test suite, exposed (not
  caused) by this sprint.** `test_connecting_twice_to_same_file_is_idempotent`
  hardcoded `schema_migrations` count as exactly `1` — true only
  because exactly one migration file existed at the time. Adding
  `0002_pending_identity.sql` made the count 2, failing the assertion.
  Worse, the failure left a SQLite connection open when the test's
  `tempfile.TemporaryDirectory` context manager tried to clean up,
  which fails hard on Windows (file still locked) — turning a clear
  assertion failure into a confusing `PermissionError` instead. Fixed
  both: the test now asserts the count stays *stable* across a
  reconnect (which is what "idempotent" actually means, and doesn't
  hardcode a number that grows every slice), and the connection close
  is now in a `finally` block so a future assertion failure fails
  cleanly instead of cascading into an unrelated OS error.
- **RapidRecon's test fixture VIN turned out to already be shared with
  Keyper/Tekion/MDD's test VIN** (`1TESTVIN000000001` / K30001) —
  chosen deliberately so RapidRecon's write path had a "known Vehicle"
  to annotate, but not deliberately chosen to *also* be the strongest
  possible cross-source identity test case. It ended up proving that
  VIN correctly merges contributions from **four** sources in one row,
  stronger evidence than the three-source case originally planned.

## Technical debt introduced

- **Five independent write-path functions, one per source**, all
  hand-written rather than sharing a common "walk a dataframe, upsert
  by VIN" abstraction. Deliberate, not an oversight — each source's
  identity-resolution mechanics differ enough (direct VIN column vs.
  last-6 fragment matching vs. store-scoped exception vocabulary) that
  a shared abstraction now would likely be wrong in a way that isn't
  visible until Slice 3 or later adds a sixth. Revisit if a sixth
  source's write path turns out to be a near-duplicate of an existing
  one.
- **RecovR/MDD/RapidRecon's "known-Vehicle-only" scoping logic doesn't
  reuse `build_tracker_install_tasks`'s existing store/sold-exclusion
  filtering** — a deliberate choice (see "Lessons learned"), but it
  does mean two different scoping philosophies now coexist in the
  codebase: the CSV report's business-rule-laden filtering, and the
  DB write path's simpler VIN-existence check. Not a bug — they answer
  different questions (should this become an install task, a business
  recommendation, vs. what did this source say about this VIN, a raw
  fact) — but worth naming so it isn't mistaken for drift later.
- **No `PendingIdentity` test for the case where the SAME raw
  identifier is reused by two conceptually different physical items**
  (e.g., a genuinely new, unrelated key that happens to also get
  classified as `unrecognized` with a colliding raw string). Considered
  low-probability given real data patterns seen so far, but not
  proven impossible.

## Lessons learned

- **"Reuse an existing function's scoping logic" isn't always the
  right call, even when it's available and already correct.**
  `build_tracker_install_tasks` already implements MDD/RecovR store and
  sold-vehicle scoping — reusing it for persistence was the initial
  plan. Implementation revealed a cleaner alternative: since
  `persist_tekion_observations` runs first and populates `vehicle` with
  every VIN this store's Tekion export knows about, querying `vehicle`
  directly ("is this VIN already known?") is a simpler, self-contained
  guard that sidesteps needing to re-derive or reuse business-rule
  scoping at all — and it's the same pattern RapidRecon already needed
  for an unrelated reason (multi-brand export). Recognizing the two
  problems were actually the same problem, once Tekion's write path
  existed to lean on, simplified three source's worth of design into
  one.
- **A fixture reused across two tests for two different reasons can
  quietly strengthen a test beyond what was planned** — worth
  double-checking fixture VIN choices don't accidentally invalidate an
  assertion's literal expected value (the "three sources" mistake
  above), but also worth recognizing when that accident is actually a
  better test than the one that was planned.
- **A hardcoded count in a test is a ticking time bomb the instant
  anything about "how many X exist" is expected to grow** — obvious in
  hindsight, but this is exactly the kind of small early-slice fragility
  the plan's own "the regression suite is the gate" principle exists to
  catch before it compounds silently across many more slices.

## Risks

- Carried forward from Sprint 1, still open: no CI (suite must be run
  manually); this repository now has version control (`v0.1.0`
  established between sprints), which resolves the previously-named
  "no rollback mechanism" risk — Slice 2's changes are cleanly
  revertible via git if needed, not just "additive in principle."
- **New this sprint:** the two different scoping philosophies noted
  under Technical Debt above are a genuine risk if a future contributor
  assumes they're the same thing and tries to "simplify" by merging
  them — they answer different questions and shouldn't be collapsed
  without deliberate review.

## Recommendations for the next slice

- Slice 3's diffing machinery is the natural place to also resolve the
  `PendingIdentity` → `Vehicle` promotion path, exactly as already
  decided in `IMPLEMENTATION_PLAN.md`. No new design work surfaced this
  sprint that changes that plan.
- When Slice 3 adds change-detection, it will need to decide whether
  `PendingIdentity`'s `last_observed_at` advancing (this sprint's
  behavior) itself counts as "a change worth noting" or is exempt the
  same way `days_out` and aging-bucket labels are exempt (per
  `IMPLEMENTATION_PLAN.md` Slice 3's existing Risk entry) — flagging
  now since it's the same class of question, not yet answered for this
  specific field.
- Consider whether the "known-Vehicle-only" pattern established this
  sprint (MDD/RecovR/RapidRecon) should become an explicit, named
  convention in `ARCHITECTURE.md` once a sixth source proves it's
  actually a repeating shape and not a coincidence of three.
