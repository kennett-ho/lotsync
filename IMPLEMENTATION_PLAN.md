# LotSync — Phase 2 Implementation Plan

If you're a new engineer reading this a year from now: this document
tells you what to build next, in what order, and why. If you're about
to write code that isn't accounted for here, stop and check whether
it actually belongs in Phase 2 at all — see "Scope boundary" below
before anything else.

## Scope boundary (read this first)

This plan covers Phase 2 only: turning the stateless reconciliation
engine into a persistent operational platform (SQLite, `Vehicle` and
`Event` history, `Task` and `Recommendation` generation). It
deliberately stops before any web framework, API, authentication, or
UI work — that's Phase 3 per `PRODUCT.md`, which is a governed
document now and isn't being silently expanded here. The last sprint
in this plan proves the database can answer the questions a dashboard
would ask; it does not build the dashboard. Phase 3 gets its own
implementation plan when Phase 2 is actually, verifiably done.

## 1. Phase 2 Vision

Right now, LotSync recomputes everything from scratch on every run.
Every CSV report is a snapshot with no memory of the run before it —
which is exactly why questions like "how many sync cycles has this
been flagged" have come up repeatedly in this project's history and
never had a real answer. That's not a bug in the current system; it's
the natural limit of a stateless design, and it's the reason Phase 2
exists.

Phase 2 replaces "recompute everything, every time" with "persist
what we know, update it incrementally, and remember what changed."
Concretely: a `Vehicle` row exists per VIN and holds current state; an
`Event` gets written only when something actually changes; a `Task`
can auto-resolve when the condition that created it goes away, instead
of requiring a human to notice and close it manually.

**What success looks like, concretely:** by the end of this plan, the
system can answer "has this vehicle's RecovR status changed since
yesterday" without recomputing anything from raw CSVs, a Task closes
itself automatically when its underlying condition resolves, and every
CSV report a dealership currently depends on still works, unchanged,
throughout the entire transition — not after it, throughout it.

## 2. Development Philosophy

- **Preserve existing business behavior, always.** Every rule in
  `rules/aging.py`, `rules/inventory.py`, `sync/normalizer.py` stays
  authoritative. Phase 2 changes where results go, not what the rules
  decide. If a Phase 2 slice changes a business outcome, that's a bug,
  not a refactor.
- **CSV reports are first-class outputs, not legacy scaffolding to be
  tolerated during a migration.** A dealership runs its morning
  operations off these files today. They must keep working, unchanged,
  through every sprint below — not just at the end.
- **Build alongside the current engine before replacing anything.**
  Every early slice is additive: the database gets populated
  *alongside* the existing CSV-generating code path, which stays
  completely untouched until a specific, later slice deliberately
  cuts over. There is no sprint where both are being rewritten at once.
- **Small, vertical, revertible slices.** Every slice in section 3
  produces something that actually runs and can be verified — not a
  layer that only makes sense once three other layers also exist.
- **The regression suite is the gate, not a suggestion.** It must pass
  after every slice, and it should only grow — if a slice doesn't add
  a test for its own new behavior, the slice isn't done.
- **The database is additive until explicitly promoted, never
  implicitly authoritative.** There is a specific, named point (Sprint
  4) where Task generation starts reading from the database instead of
  a CSV. Before that point, nothing depends on the database being
  correct. This is a deliberate design choice: it means an early
  mistake in schema or write logic can be found and fixed with zero
  consequence to anything a dealership actually uses.
- **No speculative schema.** A column or table gets added when a
  specific slice's Definition of Done requires it — not because it
  seems like it'll be needed eventually. This is `VISION.md`'s "no
  infrastructure ahead of real need" principle applied to the database
  specifically.

## 3. Implementation Order (vertical slices)

**Progress tracking:** See `PROJECT_STATUS.md` for the current
at-a-glance state (phase/sprint/slice, regression count, last
updated). Each completed slice below is marked `STATUS: DONE`, with a
link to its `SPRINT_X_REVIEW.md` — the review is the permanent record
of what was actually built and why; this document stays the plan, not
a duplicate log.

### Slice 1 — SQLite foundation + single-source write path

**STATUS: DONE** (Sprint 1). See [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md)
for full verification, discoveries, and debt. No adjustment to Slices
2–7 below was warranted — Sprint 1 didn't reveal anything this plan
hadn't already anticipated (the identity-resolution question below was
already flagged as Slice 2's risk before Slice 1 started).

**Purpose:** Prove the write-and-persist pattern works at all, in
complete isolation from anything user-facing.

**Scope:** `database/schema.sql` (or equivalent) for `Vehicle` and
`Event` only — no other tables yet. A minimal repository layer
(`database/repository.py`) with upsert/insert functions. Keyper's
processing path in `sync/reconciler.py` additionally upserts a
`Vehicle` row (by VIN) and writes an `Event` per processed record.
This is pure addition — no existing function's return value or the
CSVs it produces change at all.

**Definition of Done:** Running `main.py` produces byte-identical CSVs
to the pre-Phase-2 baseline, and a SQLite file now exists with
`Vehicle`/`Event` rows reflecting Keyper's pass.

**Success criteria:** Full regression suite passes unchanged. A direct
DB query shows Vehicle/Event row counts consistent with Keyper's
import (accounting for excluded non-vehicle keys).

**Risk:** Schema drafted here may need revision once it meets more
real data in Slice 2 — treat this slice's schema as intentionally
provisional and say so in the migration file's comments, not as final.

**Rollback:** Delete the SQLite file, remove the write calls. Nothing
else in the system references the database yet, so this is a true
no-consequence rollback.

---

### Slice 2 — Full source coverage

**STATUS: DONE** (Sprint 2). See [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md)
for full verification, discoveries, and debt. No adjustment to Slices
3–7 below was warranted beyond what's already noted in Slice 3's scope
(the `PendingIdentity` promotion addition, decided during this sprint's
pre-implementation design discussion, predating any Slice 2 code).

**Purpose:** Every source contributes to `Vehicle`/`Event`, not just
Keyper — a vehicle's persisted state should reflect everything
currently known about it.

**Scope:** Extend Slice 1's write path to Tekion, Sold, MDD, RecovR,
and RapidRecon. Each source's existing processing additionally updates
the relevant `Vehicle` status field and writes an `Event`. Keyper
records that cannot be resolved to a VIN (`tekion_auto_generated_stock_number`,
`unrecognized`, `ambiguous_last6_vin_multiple_matches` — today's
`data_quality_exceptions.csv` population) are captured as
`PendingIdentity` rows instead of being silently dropped — **capture
only.** Detecting that one of these later resolves and promoting it to
a real `Vehicle` + `Event` is explicitly Slice 3's responsibility, not
this one's — see Slice 3's updated scope below and `DATA_MODEL.md`'s
`PendingIdentity` entry for the full reasoning.

**Definition of Done:** After one full pipeline run, every Vehicle a
source mentions has that source's contribution reflected in the DB,
and every unresolved-identity Keyper record has a `PendingIdentity`
row. CSVs remain byte-identical to baseline.

**Success criteria:** DB Vehicle count is consistent with the union of
VINs seen across all five sources. `PendingIdentity` count matches
`data_quality_exceptions.csv`'s row count for the applicable reasons.
Zero CSV regression.

**Risk:** Scope discipline — it would be easy to reach for "just also
detect resolution while we're in here" once `PendingIdentity` exists.
Don't. Promotion is a state transition, and building it here would
duplicate what Slice 3 is about to build generally for exactly this
kind of change-detection, for one narrow case. If a `PendingIdentity`
row's identifier happens to resolve during Slice 2's implementation
window, it still just sits there as `status: "pending"` until Slice 3
lands — that's correct, not a bug.

**Rollback:** Same as Slice 1 — additive only. `PendingIdentity` is a
new table with no foreign keys pointing into it yet, so it drops
cleanly too.

---

### Slice 3 — Historical diffing (change-detection, not re-recording)

**STATUS: DONE** (Sprint 3). See [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md)
for full verification, discoveries, and debt — including one deliberate,
documented gap (a duplicate-sold-VIN fixture doesn't achieve perfect
idempotency, by design; see that review's "Problem solving" section)
and a design refinement to Tekion's diff key not anticipated below (it
diffs on `(tekion_status, stock_number)`, not `tekion_status` alone).

**Purpose:** This is where persistence actually starts paying for
itself. Without this slice, every sync just re-writes the same state
over and over, and `Event` becomes noise instead of history.

**Scope:** Before writing an observation, compare it against the
`Vehicle` row's current persisted field. Only write an `Event` if the
field's value actually changed since the last sync. Always update the
current field regardless of whether an Event was written (current
state is a cache; Events are the history behind it).

**Also in scope, decided during Sprint 2 design discussion (see
`DATA_MODEL.md`'s `PendingIdentity` entry):** `PendingIdentity` →
`Vehicle` promotion. When a previously-unresolved identifier now
resolves (its Keyper record matches Tekion on a later sync), this
slice's diffing machinery detects that and promotes it: set
`resolved_vin`/`resolved_at`/`status: "resolved"` on the
`PendingIdentity` row, upsert the real `Vehicle` row, and write an
`Event` capturing the transition. This is the first genuine state
transition in the system — an observation becoming an identified
vehicle — which is why it belongs here rather than in Slice 2 alongside
plain source-coverage writes.

**Definition of Done:** Running the pipeline twice on identical input
produces zero new Events on the second run. Running it with exactly
one changed field (e.g. a fixture where RecovR flips No→Yes for one
vehicle) produces exactly one new Event. Running it against a fixture
where a previously-pending identifier now resolves promotes that
`PendingIdentity` to a `Vehicle` with the transition captured as an
`Event`.

**Success criteria:** The idempotency test above passes, and is a
permanent addition to the regression suite, not a one-off manual check.
A dedicated promotion test (pending → resolved, `Vehicle` + `Event`
created, `PendingIdentity` marked resolved) is added and passes.

**Risk:** "What counts as a change worth an Event" needs a precise,
written answer, not an implicit one. Recommendation: only discrete
state fields (`tekion_status`, `keyper_status`, `mdd_status`,
`recovr_status`) generate Events on change. Continuously-drifting
derived values (`days_out`, aging bucket labels) are NOT persisted as
Events — they're computed fresh at read time from raw timestamps
already in the data. Without this distinction, a vehicle whose key has
been out for two weeks would generate a new "changed" Event every
single sync just because the day count ticked up, which defeats the
entire purpose of this slice.

**Rollback:** If diffing logic has a bug, Slice 1/2's "always write"
behavior is a safe interim fallback while it's fixed — worse
(noisier), not wrong.

---

### Slice 4 — SyncRun provenance

**STATUS: DONE** (Sprint 3). See [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md)
for full verification. Built with a stronger transactional guarantee
than originally scoped below: a deliberate Sprint 3 decision to give
SyncRun real per-source transaction semantics (`complete` iff every
write committed, `failed` iff none did) rather than bookkeeping-only
status tracking — see that review's "Problem solving" section for the
tradeoff and why the stronger guarantee was chosen.

**Purpose:** Auditability. Every Event should trace back to which sync
detected it — this is also what eventually answers "when did we last
hear from RecovR," matching the Connected Systems panel design already
recorded in `DATA_MODEL.md`.

**Scope:** `SyncRun` table. `main.py` wraps each source's processing in
a `SyncRun` record (started, completed, records processed, issues
found, status). Every `Event` written in this run carries that
`sync_run_id`.

**Definition of Done:** After a run, one `SyncRun` row exists per
source with correct counts; every `Event` has a valid `sync_run_id`;
zero orphaned Events.

**Success criteria:** `SyncRun.records_processed` matches the
corresponding CSV's row count for that source. No orphaned Events, an
explicit assertion in tests.

**Risk:** Low — this is bookkeeping around already-verified logic from
Slices 1–3, not new business logic. The main risk is a crash mid-sync
leaving a `SyncRun` in an ambiguous state — mitigated by wrapping each
source's processing in a transaction and only marking a `SyncRun`
complete after a successful commit; `SyncRun.status` already has a
"failed" option in the model for exactly this case.

**Rollback:** Additive, safe to revert.

---

### Slice 5 — Task generation (the database becomes load-bearing)

**Purpose:** This is the first slice where persisted state actually
drives something, rather than just observing it. Prove the concrete
payoff named in `ARCHITECTURE.md`'s Phase 2 spec: a Task closes itself
when the condition that created it resolves.

**Scope:** `Task` table. Task-generation logic runs against Slice 3's
diff output — a changed field can create a Task or auto-complete an
existing open one. **Critical constraint: Task-generation logic must
call the same `rules/aging.py` / `rules/inventory.py` functions the
CSV reports already use — it must not reimplement the same business
rule a second time.** Two independent implementations of "does this
vehicle need a RecovR" is exactly the kind of drift this plan exists
to prevent. The existing CSV-generating code path is still completely
untouched in this slice.

**Definition of Done:** After a sync, the `Task` table has open tasks
that correspond (in substance, not necessarily row-for-row) to what
today's task-shaped CSVs already show. A fixture test demonstrates
auto-resolution: flip a fixture's RecovR status, rerun, confirm the
corresponding Task auto-completes without manual intervention.

**Success criteria:** Task counts are consistent with the equivalent
CSV report's counts for the same condition. The auto-resolution test
above is a permanent regression test.

**Risk:** Rule-logic duplication (see Scope above) is the primary risk
— mitigated structurally, not just by discipline, by requiring shared
function calls rather than parallel logic.

**Rollback:** The `Task` table can be dropped or cleared with zero
effect on the CSV pipeline, since CSVs still come from the untouched
original code path.

---

### Slice 6 — Recommendation engine

**Purpose:** Implement `Recommendation`'s actual lifecycle (open →
converted to Task, or dismissed) — distinct from Task per
`DATA_MODEL.md`'s reasoning.

**Scope:** `Recommendation` table. Rule evaluation producing
Recommendation rows, reusing Slice 3's change-detection machinery for
"should this reappear" rather than inventing new logic. No UI needed
— testable via direct DB queries or a small script.

**Definition of Done:** Recommendations generate correctly per rule.
Converting one creates a linked `Task`. Dismissing one keeps it
dismissed across subsequent syncs unless the underlying vehicle state
genuinely changes again.

**Success criteria:** No duplicate open Recommendations for the same
vehicle+rule pair. A dismissed Recommendation does not reappear on the
next sync unless state changed — an explicit regression test.

**Risk:** Same class of problem as Slice 3 (what counts as "state
changed enough to reopen a dismissed recommendation") — mitigated by
reusing, not reinventing, Slice 3's diffing.

**Rollback:** Additive, safe to revert.

---

### Slice 7 — Dashboard data layer (Phase 2's final slice)

**Purpose:** Validate that everything built in Slices 1–6 can actually
answer the real questions a dashboard needs — before any web
framework, API, or UI investment happens. This is explicitly the
boundary of Phase 2; see "Scope boundary" above.

**Scope:** A query module (e.g. `queries/dashboard.py`) with plain,
well-tested Python functions matching the panels already designed in
the frontend discovery review — inventory health percentage, task
counts by department, connected-systems status (derived from
`SyncRun`, per the already-documented decision not to build a separate
`SystemStatus` model), a live-activity-style recent-Events feed.
Output is inspectable data (dict/JSON-shaped), no HTTP server.

**Definition of Done:** Each dashboard panel from the mockup has a
corresponding, tested query function returning correct results against
known fixture data.

**Success criteria:** Query results match hand-computed expected values
for fixture scenarios. Basic query performance is validated against
realistic data volumes (thousands of vehicles, the scale already seen
in real exports) — not optimized prematurely, but not left unchecked
either.

**Risk:** Query performance at scale in SQLite — likely fine given
current data volumes, but worth validating explicitly rather than
assuming. The documented escape hatch (PostgreSQL, per
`ARCHITECTURE.md`) exists precisely for if this stops being true.

**Rollback:** Purely additive — if the data layer isn't ready, Phase 3
simply doesn't start yet. Nothing else is affected.

## 4. Sprint Roadmap

| Sprint | Contents | Exit condition | Status |
|---|---|---|---|
| 1 | Slice 1 — SQLite foundation, Keyper write path | Regression suite passes; DB populated from Keyper alone | **DONE** — see [`SPRINT_1_REVIEW.md`](SPRINT_1_REVIEW.md) |
| 2 | Slice 2 — full source coverage + `PendingIdentity` capture | All 5 sources persisted; unresolved identities captured, not dropped | **DONE** — see [`SPRINT_2_REVIEW.md`](SPRINT_2_REVIEW.md) |
| 3 | Slices 3 + 4 — historical diffing, `PendingIdentity` promotion, SyncRun provenance | Idempotency test passes; promotion test passes; every Event traceable to a SyncRun | **DONE** — see [`SPRINT_3_REVIEW.md`](SPRINT_3_REVIEW.md) |
| 4 | Slice 5 — Task generation | Auto-resolution demonstrated; zero rule-logic duplication | Not started |
| 5 | Slice 6 — Recommendation engine | Convert/dismiss lifecycle correct and tested | Not started |
| 6 | Slice 7 — dashboard data layer | Every mockup panel has a tested, correct query function | Not started |

Phase 2 is done at the end of Sprint 6. Phase 3 (web application) gets
its own implementation plan at that point — not before.

## 5. Technical Risks

- **Duplicate events.** Primary defense is Slice 3's diff-before-write
  pattern. Secondary defense: idempotency is a named, permanent
  regression test (same input twice → zero new Events), not a one-time
  manual check.
- **Vehicle identity.** Risk of the same physical vehicle becoming two
  `Vehicle` rows — via a VIN typo, an unresolved-identity edge case
  handled inconsistently, or (per `DATA_MODEL.md`) a dealership
  transfer accidentally creating a new row instead of updating
  `current_dealership_id`. Mitigation: VIN is a strict upsert key;
  Slice 2 makes the unresolved-identity handling an explicit, written
  decision instead of an implicit one; a regression test explicitly
  asserts that the same VIN observed from two different sources in one
  run never creates two Vehicle rows.
- **Migration strategy.** Decide this in Sprint 1, not retrofit it once
  Sprint 3 has real data in a live file. Recommendation: numbered SQL
  migration files from day one (`database/migrations/0001_initial.sql`,
  etc.), applied in order, even though Sprint 1's schema is small. This
  is the "spend a day now, not weeks later" principle in its most
  literal form.
- **Performance.** Already-seen real data volumes (34K-row Sold
  history, ~2,000 Keyper records) are well within SQLite's comfort
  zone, but this should be validated at Slice 7, not assumed. Indexing
  on `vin`, `sync_run_id`, and `event_type` from Sprint 1 onward, not
  added reactively after something is slow.
- **Historical consistency.** `Event.dealership_id` and similar
  "captured at write time" fields (per `DATA_MODEL.md`) are correctness-
  critical and, unlike current state, don't self-correct on the next
  sync if written wrong — a bug here silently corrupts history. Needs
  explicit test coverage specifically for these fields, not just
  general Event-writing tests.
- **Database schema evolution.** The migration-file pattern above
  handles the mechanics; the governance model already agreed to
  (`DATA_MODEL.md` as the canonical source, kept in sync) handles the
  discipline side — a schema change without a corresponding
  `DATA_MODEL.md` update should be treated as incomplete.
- **Regression drift.** The real risk isn't the CSV pipeline breaking
  loudly — it's Task/Recommendation logic quietly reimplementing a
  business rule slightly differently than the CSV path does, so both
  keep running and slowly diverge. Mitigated structurally (Slice 5's
  shared-function requirement), not just by good intentions.
- **Partial sync failure.** Not in the original risk list but real
  given this plan: a crash mid-sync-run risks leaving some sources
  updated and others not, with no clear record of what happened.
  Mitigation: each `SyncRun` wraps its source's writes in a
  transaction; a `SyncRun` only reaches "complete" on successful
  commit; the "failed" status already in the `SyncRun` model exists
  specifically for this case, so use it.

## 6. Success Metrics

Per-stage, not "code compiles":

- **Every sprint:** Full regression suite passes; CSV outputs remain
  byte-identical to the Phase 1 baseline until the deliberate,
  documented point (not reached in this plan) where that changes.
- **Sprint 1–2:** Zero duplicate Vehicle rows for any VIN across a full
  sync run.
- **Sprint 3:** Same-input-twice produces zero new Events (permanent
  test, not a one-off check).
- **Sprint 4:** Zero orphaned Events; `SyncRun` record counts match
  their corresponding CSV row counts.
- **Sprint 5:** At least one demonstrated auto-resolution (a Task
  closes itself without manual action) as a permanent regression test.
- **Sprint 6:** Zero duplicate open Recommendations per vehicle+rule
  pair; dismissed Recommendations stay dismissed unless state
  genuinely changes.
- **Sprint 7 (Slice 7):** Every dashboard panel from the frontend
  discovery mockups has a tested, correct query function — before any
  Phase 3 work begins.
- **Across all of Phase 2:** The regression test count only grows,
  sprint over sprint. A shrinking test count is itself a red flag
  worth stopping and asking about.

## 7. Future Work — acknowledged, intentionally deferred

- **Phase 3's actual web application** (FastAPI, React, the real
  dashboard UI) — deliberately excluded from this plan; see "Scope
  boundary."
- **Authentication** — no current need until there's a real multi-user
  access surface, which Phase 3 introduces.
- **Cloud hosting / deployment** — not needed for a single-dealer-group
  deployment running locally.
- **Multi-tenant SaaS (`Tenant` model)** — already documented as a
  deliberate non-build in `DATA_MODEL.md`, with a clean extension path
  if it's ever actually needed.
- **Notifications** — Phase 5 per `PRODUCT.md`.
- **Dealer Trade workflows** — Phase 4 per `PRODUCT.md`; also has a
  specifically documented modeling gap (`Task.dealership_id` can't
  represent a two-dealership trade) that needs real design work when
  that phase starts, not a rushed retrofit now.
- **Predictive/ML-based recommendations** — explicitly deferred per the
  frontend discovery review; Phase 2's Recommendations are rule-driven
  only.
- **Mobile app** — no current evidence of need.
