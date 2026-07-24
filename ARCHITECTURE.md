# LotSync OMS — Architecture

This is documentation for whoever is extending this code, not for
someone running the reports. If you just need to know what a report
means or how to edit config, see README.md instead.

## Where this project is, honestly

This is a **Phase 1** reorganization. The reconciliation logic itself
is unchanged from the original single-file script — every function
was moved verbatim into a module with a clear responsibility, and
verified byte-for-byte identical against the original via a regression
test before this was called done. Nothing here is a rewrite of
business logic. A **Phase 2** rewrite (described below) is planned but
not started: it would change how data flows internally, not what the
reports say.

If you're about to add a feature and find yourself fighting the
current structure, that's a signal Phase 2 is due, not a signal to
work around it in Phase 1's shape.

## Why Vehicle is meant to be the core object (and isn't yet)

Right now, `sync/reconciler.py` computes each report semi-independently:
`reconcile_keyper_tekion` walks Keyper looking for Tekion matches,
`build_sold_vehicles_report` separately walks Sold looking for Keyper
and RecovR matches, `build_tracker_install_tasks` separately walks
MDD and RecovR. The same VIN gets looked up repeatedly, in different
functions, against different lookup indexes, and there's no single
place that holds "everything we currently know about this vehicle."

That's fine for eight independent CSV reports. It stops being fine the
moment you want a lot-staff dashboard (Milestone 2) or a vehicle
detail page showing Tekion/Keyper/MDD/RecovR status together — that
needs one object per vehicle, not eight report-shaped dataframes you'd
have to cross-reference by VIN every time.

`models/vehicle.py` defines the target shape. It is **not currently
built or updated by anything** — it's scaffolding so the shape is
decided in advance, not invented mid-rewrite. The Phase 2 work is:
restructure `sync/reconciler.py` so each importer's data updates a
`Vehicle`'s corresponding status field (`tekion_status`, `keyper_status`,
etc.) instead of directly producing report rows, and have `rules/`
functions evaluate a `Vehicle`'s state to decide what `Task`s it needs.
Reports become a rendering step over a collection of `Vehicle` objects,
not something reconciliation computes directly.

## How the synchronization pipeline currently works

```
config/settings.py  →  read oms_config.xlsx (store name, sync date,
                        bucket thresholds, VIN exclusion list)

importers/*.py       →  read each source CSV, apply sync/normalizer.py
                         to classify identifiers (stock number vs.
                         last-6-VIN vs. exception), return a dataframe

sync/matcher.py       →  build lookup indexes (stock number → row,
                          last-6-VIN → rows) for Tekion and Sold

sync/reconciler.py    →  walk Keyper rows, resolve each against the
                          lookups, route into fully_verified /
                          key_out_aging / flag_to_controller /
                          exceptions; separately build the sold-vehicle,
                          tracker-install, and incoming/missing reports

rules/*.py             →  classification and threshold logic consulted
                           by sync/reconciler.py (is this stock number a
                           new car? what label does N days-out get?)

rules/validation.py    →  Tekion-internal contradiction checks,
                           independent of Keyper matching

reports/writer.py      →  write the resulting dataframes to CSV,
                           print the run summary
```

`main.py` orchestrates this and should stay thin — if you're deciding
something (a threshold, a classification rule, a matching strategy),
that decision belongs in `rules/` or `sync/`, not in `main.py`.

## How to add a new importer

Look at `importers/recovr.py` as the simplest example. An importer's
job is exactly two things: read the source file, and — if the source
has its own identifier quirks — call into `sync/normalizer.py` to
classify them into the shared `identifier_type` / `identifier_value`
shape the rest of the system expects. It should NOT contain business
rules (what counts as "new," what a threshold is) — those belong in
`rules/`.

`importers/mdd_history.py` is a real example of "not built yet" —
read its docstring for what's blocking it and where the logic would
go once it exists.

## Where business rules belong

- **Format questions** ("is this a stock number or a VIN fragment") →
  `sync/normalizer.py`.
- **Business classification questions** ("is this vehicle new,
  damaged, or a trade") → `rules/inventory.py`.
- **Threshold/state questions** ("what does 9 days out mean") →
  `rules/aging.py` (the actual default values) evaluated by
  `sync/state_engine.py` (the generic evaluator) with overrides read
  by `config/settings.py`.
- **Cross-source contradiction checks that don't involve Keyper
  matching** → `rules/validation.py`.

`rules/tracker.py` is currently a stub, not a real split — read its
docstring. The MDD/RecovR "missing device" logic still lives in
`sync/reconciler.py`'s `build_tracker_install_tasks` because it's
tightly interleaved with matching mechanics (store scoping, sold-vehicle
exclusion) that don't cleanly separate from the business rule without
the Phase 2 Vehicle-object rewrite. Forcing a split today would have
fragmented working logic across two files without actually decoupling
anything — so it wasn't forced.

## How state transitions work (and don't, yet)

Right now, "state" is computed fresh on every run from a snapshot
comparison — there's no memory of what the last run found.
`sync/state_engine.py`'s `day_out_bucket` is a pure function: given a
day count and a threshold table, return a label. It doesn't know
anything about a previous run.

The real state-transition engine described in the original project
vision (`Pending DMS Entry → Vehicle Appears in Tekion → Generate
Replace Tags Task`) requires two things this codebase doesn't have
yet: a `Vehicle` object whose state persists across runs, and a
`database/` layer to store it in. Both are deliberately absent right
now — see `database/__init__.py` for why adding persistence
speculatively, before anything needs it, would be premature complexity
rather than preparation.

When that's built, `models/event.py` is where a per-run observation
("this VIN appeared in Tekion for the first time today") would be
recorded, and the actual transition logic (comparing today's Event
against history to decide if a Task should fire) would live in
`sync/state_engine.py`, replacing today's pure snapshot evaluation.

### Phase 2 database design (decided, not yet built)

The following was worked through in project discussion ahead of Phase
2 actually starting, specifically so these decisions exist as a spec
to build against rather than being invented mid-implementation:

**Engine: SQLite to start, not PostgreSQL.** A single-process nightly
sync-and-diff workflow doesn't need a server or concurrent-write
support yet. Starting with PostgreSQL now, with no multi-user or
cloud-hosted reason requiring it, would be exactly the premature
infrastructure PRODUCT.md warns against. Migrating to PostgreSQL later
-- once Phase 3's web app creates a real concurrent-access need -- is
a much smaller lift than running and maintaining a Postgres server for
a use case that doesn't need one yet.

**Identity key: VIN**, consistent with how identity resolution already
works everywhere else in this pipeline. The one edge case worth
designing for up front rather than retrofitting later: a meaningful
population of Keyper records never resolve to a VIN at all (see
`data_quality_exceptions.csv` -- auto-generated placeholder stock
numbers, ambiguous last-6 matches). The database needs "known key,
unknown vehicle identity" as a genuinely distinct case from "known
vehicle," not an error state or a dropped row -- these are real,
physically-present vehicles this pipeline just can't currently name.

**Diffing is field-level, not record-level.** A vehicle's
`tekion_status`, `keyper_status`, `mdd_status`, and `recovr_status` can
each change independently between syncs. "What changed" needs to be
answerable per field ("RecovR pairing changed from No to Yes on VIN
X"), not as a single "this vehicle is different somehow" flag -- that
granularity is what lets a Task auto-resolve (the RecovR install task
for a vehicle closes itself once a diff shows `recovr_status` flip to
paired) instead of requiring a human to manually close it.

**This is the event-sourcing direction, not the snapshot direction**
-- the tradeoff was named back when Milestone 1 was first being
scoped (store current state vs. store the stream of changes that
produced it). Each sync doesn't just overwrite current state, it
*records* the transition. This is also what finally answers "how many
sync cycles has this been flagged," a real gap that's come up
repeatedly in this project's history and that a snapshot-only design
can never answer, since a snapshot has no memory of what a previous
run found.

### The dashboard vision this is ultimately in service of

For a concrete Phase 3 target to build the above against, not an
abstract one: a lot-staff dashboard organized as task modules --
"Install RecovRs on these cars," "Install MDD beacons on these cars,"
"Incoming Vehicle Drop-Offs," "Verify if these cars are going to
wholesale" -- each backed by a query against persisted Vehicle/Task
state rather than a regenerated-from-scratch CSV. Two things worth
remembering when that gets built, surfaced during design discussion:

- **"Incoming Drop-Offs" and "Overdue - Investigate" need to become
  two separate modules**, not one filtered report. Today's
  `incoming_or_missing_investigate_report.csv` conflates "expected
  soon, informational" with "overdue, needs action" in a single
  `priority` column -- fine for a CSV, wrong shape for two different
  dashboard cards with different urgency.
- **"Verify if these cars are going to wholesale" is a new module,
  not a relabeled existing report.** It's the opposite case from what
  `Step = WHOLESALE/AT AUCTION` already does (confidently *excluding*
  vehicles from install lists) -- this module is for cases where
  wholesale status is genuinely unclear and needs a human to check,
  closer in spirit to `recovr_install_needs_review.csv`'s Archive-step
  bucket, but likely needs to be broader. Not designed in detail yet.

## A known non-obvious bug fixed during the Phase 1 split

`rules/validation.py`'s `find_tekion_sync_conflicts` originally
iterated over a raw Python set intersection (`sold_vins & master_vins`),
which produces a different row order on every process run due to hash
randomization — not a logic bug, but a reproducibility one. This
surfaced during the regression test that verified this reorganization
against the original script (two independent runs of supposedly
identical logic produced differently-ordered CSVs). Fixed by sorting
before iterating. Worth knowing this class of bug exists elsewhere if
you ever see a report's row order change between runs with no
underlying data change — check for raw set iteration.

## Testing

`tests/` has a real automated suite now (unittest, stdlib only, no
pip install required) — see `tests/README.md` for how to run it and
`tests/fixtures/README.md` for what each synthetic fixture row tests.
This replaced the manual "run old script, run new package, diff every
CSV" verification performed during the Phase 1 module split — that
manual process is exactly what `tests/test_regression.py` now
automates. Run it after any change to `sync/` or `rules/`.

## RapidRecon: contextual enrichment only, not yet a state provider

`sync/reconciler.py`'s `enrich_with_rapidrecon()` attaches recon
context (Step, DIS, DIR, Priority, Note) to the Incoming/Missing report
by VIN — it does not classify, bucket, or exclude anything based on
that data. This is a deliberate scope boundary, not an oversight.

Real data shows this restraint is warranted: `Step` has 77 distinct
values, most with only a handful of rows, spanning at least three
different concerns (recon workflow stage, disposition routing like
WHOLESALE/AT AUCTION, and terminal states like Archive) with no
confirmed mapping from value to business meaning. A first pass at
reading the data suggested roughly half of RapidRecon-matched
"Overdue" rows are vehicles never headed to retail inventory at all
(wholesale/auction bound) — a real, actionable pattern — but turning
that observation into an actual exclusion rule without the
dealership's confirmation would repeat the exact mistake made earlier
in this project with the original (unfounded) Incoming/Missing day
thresholds: a plausible-looking number standing in for a real answer.

RapidRecon becomes a genuine state provider in Phase 2, once `Vehicle`
objects exist as the core reconciliation unit (see "Why Vehicle is
meant to be the core object" above) — at that point `recon_step` would
map onto `Vehicle.inventory_state` transitions the same way Tekion and
Keyper status already would, with the Step vocabulary properly
confirmed against real dealership workflow first, not inferred from
value counts alone.

## Frontend discovery (Figma Make mockups) -- decisions this drove

A round of interactive dashboard/vehicle-detail mockups (built via
Figma Make, reviewed alongside a ChatGPT-authored architecture brief)
converged independently on the same core shape already specified
above -- Vehicle as the central object, reports as views over it. That
convergence from a different direction is real validation. It also
surfaced two gaps in what had been decided so far, both resolved here
rather than left open:

**Event needed a richer shape than a raw field diff.** The original
`models/event.py` was "field X changed from A to B." The mockup's
Timeline needs narrative entries ("Keys checked out by Sales --
Checked out to James Miller, 6hrs14min outstanding, typically <2hrs"),
which a bare diff can't produce alone. `Event` now carries a `summary`
(display) separate from `detail_fields` (structured data behind it,
e.g. for duration-vs-baseline comparisons), plus `sync_run_id` and
`actor_employee_id` for attribution.

**Task granularity needed to be decided explicitly.** The dashboard
mockup shows "Install RecovR Devices -- 6 tasks, 1 of 6 complete" --
that reads as one Task with a count, but it's actually a task-TYPE
group; each of the 6 is its own per-vehicle Task, aggregated by
`task_type` for the dashboard card. Decided now because getting this
wrong would silently break the dashboard's grouping logic once built.

**Two models added, judged foundational rather than deferrable:**
`Employee` (nearly every Event/Task in the mockups has an attributed
actor -- this isn't optional for Timeline or Task to function) and
`SyncRun` (every Event needs to trace back to which sync detected it).
A third proposed model, `SystemStatus`, was deliberately rejected in
favor of treating it as a derived view over `SyncRun` grouped by
source -- modeling it separately would create two sources of truth
that can drift.

**One more model added, deliberately distinct from Task:**
`Recommendation`. The mockup's "AI Recommendations" cards have their
own lifecycle (shown / converted to a Task / dismissed) before ever
becoming a Task -- collapsing the two would lose the dismiss path. Note
on naming: these are rule-driven (the same rules already in
`rules/aging.py` and `rules/inventory.py`), not ML-driven, despite the
UI label -- predictive/ML recommendations are explicitly deferred, not
an architectural requirement now.

**Explicitly NOT pulled forward by this review:** multi-dealership /
Dealer Trades workflows shown in the mockup (PRODUCT.md already scopes
this to Phase 4/6 -- seeing it in a mockup doesn't change that),
`Notification` as a real system (Phase 5), `Attachment`/`Document`
(no real evidence of need yet, genuinely speculative), and any actual
REST API or database engine implementation (Phase 2/3 build work, not
a scaffolding decision).

## Tenant vs Dealership (the gate-review blocker, resolved)

A formal architecture gate review before Phase 2 implementation
identified one real blocking question: the data model had no
dealership or tenant concept at all, despite every source in this
project already having one baked in ad hoc (Keyper's `System` field,
RecovR's Kia/MARK_AUTO umbrella split, RapidRecon's multi-brand
export). Left unresolved, this would have meant guessing at an
identity model that's expensive to retrofit after Phase 2 database
code exists.

**Resolved**: LotSync is not being built as public multi-tenant SaaS.
The deployment target is Mark Auto Group, with Mark Kia/Mazda/
Mitsubishi treated as one operational environment where vehicles
legitimately move between stores while remaining the same physical
vehicle. `Dealership` is now modeled (`models/dealership.py`) as a
current concern; `Tenant` is deliberately not modeled, documented as a
low-cost future extension point rather than built speculatively. Full
reasoning and field-level detail: `DATA_MODEL.md`, "Tenant vs
Dealership."

This also gave the "how does a source record get attributed to a
store" problem — solved four separate ad hoc ways across this
project's history — a single place to eventually resolve to, instead
of staying four different one-off patterns.

## What's still just a script, not a platform

No web framework, no database, no auth, no API exist in this codebase.
The proposal that prompted this reorganization mentioned FastAPI,
React, PostgreSQL, and cloud deployment as the eventual direction —
none of that is built here, on purpose. Adding those dependencies now,
with nothing yet needing them, would be speculative complexity. The
module boundaries in this reorganization exist so that work is a
natural extension later (a FastAPI layer would import from `sync/` and
`rules/` the same way `main.py` does now; `database/` is reserved,
empty, for exactly this) — not so those tools get adopted prematurely.
