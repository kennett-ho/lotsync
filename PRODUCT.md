# LotSync — Product Definition

## What this document is

This is the canonical description of *what LotSync is for, who it's
for, what it does today, and what's planned versus explicitly out of
scope*. `VISION.md` explains **why** the project exists (the problem,
the principles). This document explains **who uses it, what it does,
in what order, and where its edges are**. `ARCHITECTURE.md` and
`DATA_MODEL.md` explain **how** it's built. `IMPLEMENTATION_PLAN.md`
is the detailed execution plan for Phase 2 specifically.

`ARCHITECTURE.md`, `DATA_MODEL.md`, and `IMPLEMENTATION_PLAN.md`
already cite this file by name in several places ("Phase 4 per
PRODUCT.md," "Phase 5 per PRODUCT.md," "PRODUCT.md is a governed
document") — this document did not previously exist as a checked-in
file. What follows is a synthesis of the product definition that was
already implicit across those documents, consolidated here for the
first time so those citations point at something real. It introduces
no new product ideas, phases, or capabilities beyond what those
documents already establish. Where the source material was ambiguous
or silent, that's called out explicitly in "Open questions," not
resolved by invention.

As with `DATA_MODEL.md`'s convention: if a phase or scope claim
elsewhere in the codebase (a docstring, a comment) ever disagrees with
this document, this document is correct and the other reference is
stale — fix the reference, not this file.

## Users and stakeholders

**Note on this section's history:** an earlier version of this
document (and, more consequentially, the Phase 3 frontend mockups
built alongside it) treated several departments as co-equal audiences,
each drifting toward its own dedicated LotSync workspace — a Tower
dashboard, a Controller approval queue, a cross-department request
system. A deliberate, explicit product-owner review corrected this.
What follows is that correction, not a drafting nit: LotSync has one
primary user and a set of contributors, not several equal audiences.

**Primary user: lot attendants / lot staff.** LotSync is their
operational workspace. Every dashboard, task module, and vehicle-detail
view exists to answer one question for this person: "what's really
going on with this car, right now, and what do I need to do about it
today?" (`VISION.md`). Where a design decision has to choose between
serving lot staff's daily workflow and serving another department's
convenience, lot staff's workflow wins.

**Contributors — not primary users.** These departments feed
operational information into LotSync so lot staff has it. They are not
the audience LotSync is designed around, and their interaction with it
should be as lightweight and minimally disruptive to their existing
workflow as possible — none of them get a dedicated LotSync workspace
unless a future, deliberate product decision changes that.

- **Tower.** Communicates deliveries, dealer trades, pull requests,
  showroom requests, and detail requests — information lot staff
  needs, not a workflow Tower manages inside LotSync.
- **Sales.** Communicates new trade-ins with as little friction as
  possible. A later iteration may add VIN-scan-based auto-population
  to reduce this further — not beta scope (see "Beta Vision" below).
- **Service / Recon.** Contribute operational context — a vehicle is
  in service, a vehicle is in recon — so lot staff understands why a
  vehicle isn't where or what they expected, without needing their own
  view into those departments' systems.
- **Controller / Tekion data owner.** Needs visibility into exceptions
  LotSync already surfaces (`flag_to_controller_report.csv`,
  `tekion_sync_conflicts.csv` today) — not a dedicated approval or
  audit workspace of their own.
- **Employees generally**, modeled with a home dealership assignment
  and role per `models/employee.py` — attribution for Events and Task
  assignment depends on this existing, independent of which category
  above a given employee falls into.

**The dealership organization: Mark Auto Group.** The actual and, at
present, only deployment target — Mark Kia, Mark Mazda, and Mark
Mitsubishi, operated as one environment where vehicles legitimately
move between stores while remaining the same physical vehicle (see
"Deployment scope" below). There is currently no other customer.

## The operational problem

A dealership runs on five or six systems that were never designed to
talk to each other — Tekion (inventory/DMS), Keyper (key tracking),
MDD and RecovR (GPS/beacon tracking), and RapidRecon (reconditioning
workflow). Each is independently accurate for what it tracks; none can
answer, on its own, what's really going on with one physical vehicle
right now. That gap is filled today by memory, phone calls, and manual
spreadsheet comparison — which fails in predictable, recurring ways:
a key sits in a drawer for years after its car sold, a tracker never
gets installed because a trade-in never hit the DMS, a vehicle shows
"sold" in one system and "in stock" in another until an audit finds
it. See `VISION.md` for the full framing of why this gets worse over
time, not better, without something watching the seams.

Concretely, today's reconciliation engine catches eight distinct
categories of this gap (see "Current capabilities" below) — each one
traced back to a real, observed operational failure mode, not a
hypothetical one. `tests/README.md` notes this pattern explicitly:
nearly every business rule in this codebase came from a real-data
surprise, not advance design.

## Core concept: operational awareness

LotSync's answer to the problem above, across every phase of the
roadmap, is best named **operational awareness**: an always-current,
trustworthy picture of what's really happening with each vehicle,
assembled from every source system at once rather than trusted to any
one of them alone. This is the same idea `VISION.md` names the
"**operational source of truth**" — this document adopts "operational
awareness" as a shorthand for it, used in the sections below, because
it names the outcome for the *user* (what lot staff comes away
knowing) rather than the system's role. The two phrases describe the
same product concept; neither supersedes the other.

Every capability in this document serves operational awareness one of
two ways: **catching** a gap between systems (the eight current
reports; Phase 2's Task/Recommendation generation), or **presenting**
that awareness to the person who needs to act on it (Phase 3's
dashboard). Note on scope: this label is a naming clarification
adopted at the product owner's request during documentation review —
it did not appear in the original source documents. Flagged here in
the same spirit as this document's other synthesis notes, so its
origin stays traceable.

## Product philosophy

Carried forward unchanged from `VISION.md`'s Principles and
`IMPLEMENTATION_PLAN.md`'s Development Philosophy — this section does
not add to either, it names the philosophy in one place so the rest
of this document can be read against it:

- **Vehicles are the center.** Everything organizes around one
  physical vehicle's complete story, not around any single source
  system's report of it.
- **Reports, tasks, and dashboards are outputs, not the product.**
  The product is the continuous reconciliation underneath them.
- **Tasks drive work; recommendations assist, they don't decide.**
  The goal is fewer things falling through the cracks, and a human
  stays the decision-maker on anything judgment-based.
- **Events preserve history.** Nothing gets forgotten between syncs —
  a big part of why Phase 2 exists at all (see Roadmap).
- **Preserve existing business behavior across every change.** A
  rule already encoded in `rules/aging.py`, `rules/inventory.py`, or
  `sync/normalizer.py` stays authoritative; restructuring where
  results go must never silently change what they say.
- **CSV reports are first-class, not legacy scaffolding.** A
  dealership runs its morning operations off these files today; they
  keep working, unchanged, through every stage of the roadmap below —
  not just at the end of it.
- **No infrastructure ahead of real need.** No database engine, web
  framework, authentication system, or multi-tenant model gets built
  speculatively. Each has a documented, low-cost extension path for
  if and when a real need actually appears (SQLite → PostgreSQL,
  Dealership → Tenant, script → API), but none is built in advance of
  that need being real and current.
- **Don't guess at business meaning from data patterns alone.**
  Where a source's data doesn't have a confirmed business meaning
  (RapidRecon's 77-value `Step` field, an untimed repair-duration
  bucket), the system surfaces the raw signal for a human to judge
  rather than encoding a plausible-looking but unconfirmed rule. The
  project has a specific bad precedent for this (the original,
  unfounded Incoming/Missing day thresholds) that later needed
  correcting against real workflow data — new rules should be
  grounded the same way those corrections were, not repeat the
  original mistake.
- **A confirmed dealership policy is context, not enforcement logic.**
  This is a distinct trap from the one above — it's not about
  unconfirmed meaning, it's about *human judgment calls that stay
  human even once LotSync knows the policy behind them.* A dealership
  may confirm a real, specific policy (e.g. a mileage threshold that
  informs a wholesale-vs-recon call) — that's genuinely useful context
  for interpreting evidence, and worth recording. But LotSync should
  never use it to independently predict, validate, or flag what a
  person "should" have decided, because the real decision routinely
  depends on judgment nothing in any system captures (an inspection
  finding, an exception for a specific vehicle type). LotSync surfaces
  what evidence exists; a person remains the one who decided, and the
  one who can be asked why.
- **Small, additive, revertible changes; the regression suite is the
  gate, not a suggestion.** Every implementation slice builds
  alongside the existing engine before anything is cut over, and must
  leave the regression suite passing and growing.

## Deployment scope

LotSync is being built for a single operational deployment — **Mark
Auto Group** (Mark Kia, Mark Mazda, Mark Mitsubishi) — not as
multi-tenant software for unrelated dealer groups. This was a
formal, resolved architecture decision (see `ARCHITECTURE.md`,
"Tenant vs Dealership"): `Dealership` (a location/business unit within
this one deployment) is modeled now; `Tenant` (a wholly separate
organization) is deliberately not modeled, with a documented low-cost
migration path (`Dealership` gains a `tenant_id`) if LotSync is ever
sold to other, unrelated dealer groups. Nothing about today's shape
needs to change to support that later — but there is no current
customer or requirement driving it, so it isn't built now.

## Current capabilities (shipped today — Phase 1)

The reconciliation engine runs against five source exports (Keyper,
Tekion current inventory, Tekion sold, MDD not-paired, RecovR full
list) plus a RapidRecon export for contextual enrichment, and produces
eight reports, each answering one specific reconciliation question:

| Report | Question it answers |
|---|---|
| `fully_verified_report.csv` | Key checked "In," matches an active Tekion vehicle — no action needed. |
| `key_out_aging_report.csv` | Key checked "Out" and matched — how long, and how concerning is that? |
| `flag_to_controller_report.csv` | Keyper has a key with no Tekion match at all — needs stocking in, or a sold vehicle whose key was never removed. |
| `incoming_or_missing_investigate_report.csv` | Tekion shows an active vehicle with no Keyper key — split by New Car (awaiting dropoff), New (damaged/in repair), or Trade/Other, each with a different expected timeline. |
| `sold_vehicles_report.csv` | Sold vehicles that still show a Keyper key and/or RecovR pairing — needs removal. |
| `tracker_install_tasks.csv` | Active vehicles missing an MDD beacon or RecovR device. |
| `tekion_sync_conflicts.csv` | Contradictions inside Tekion's own two exports (sold vs. stocked-in, duplicate sold VIN). |
| `data_quality_exceptions.csv` | Identifiers that couldn't be confidently classified or matched — a Tekion data-entry problem, not a reconciliation failure. |

All day-to-day tunable behavior (store name, sync date, VIN exclusion
list, aging-bucket thresholds) lives in `oms_config.xlsx`, editable
without touching code — see `README.md`.

**Known, named limitation of this stage:** no memory between runs.
Every run recomputes everything fresh; there is no way yet to answer
"how many sync cycles has this vehicle been flagged." This is the
specific gap Phase 2 exists to close.

## Roadmap

The phases below are the numbering already used and cross-referenced
throughout `ARCHITECTURE.md`, `DATA_MODEL.md`, and
`IMPLEMENTATION_PLAN.md`. This document is now the canonical anchor
for that numbering.

**Phase 1 — Reconciliation engine, modularized (done).** The original
single-file script, reorganized into the current module structure
(`importers/`, `sync/`, `rules/`, `reports/`) with zero business-logic
changes, verified byte-for-byte identical to the original via
regression test. This is what's described in "Current capabilities"
above.

**Phase 2 — Persistent operational platform (in progress).** Turns
the stateless reconciliation engine into one with memory: SQLite,
`Vehicle` and `Event` history, auto-resolving `Task`s, a
`Recommendation` engine, and a query layer proving the data can answer
dashboard-shaped questions. Fully specified in `IMPLEMENTATION_PLAN.md`
(7 vertical slices across 6 sprints). Explicitly stops short of any
web framework, API, authentication, or UI. Every CSV report from
Phase 1 keeps working, unchanged, throughout.

**Phase 3 — Web application.** The actual dashboard UI (FastAPI +
React, per the original proposal that prompted this reorganization),
built against the query layer Phase 2 validates — the lot-staff
dashboard organized as task modules ("Install RecovRs on these cars,"
"Incoming Vehicle Drop-Offs," etc.) and a vehicle detail page,
per the mockups referenced in `ARCHITECTURE.md`'s frontend-discovery
section. This is also where authentication is introduced, since it's
the first point a real multi-user access surface exists. Gets its own
implementation plan once Phase 2 is verifiably done — not before.

In practice, Phase 3 turned out to span more sprints than this original
paragraph anticipated, each documented in its own `PHASE_3_SPRINT_N_REVIEW.md`:
Sprint 1 built the `Employee`/`Dealership` backend foundation those
dataclasses had been missing since the frontend-discovery review; Sprint 2
built the first read-only API layer over Phase 2's data; Sprint 3 wired six
frontend screens to that API; Sprint 4 replaces manual database seeding
with a real, upload-triggered Inventory Sync workflow — the "Run Sync Now"
capability `API_CONTRACTS.md` Section 5 had already named as Phase 3
write-path scope. None of this is a re-scoping of Phase 3; it's this
paragraph catching up to what already shipped under it. Authentication,
named above, remains not yet built as of Sprint 4.

**Phase 4 — Dealer Trades.** Workflows spanning a vehicle move between
two dealerships (e.g. "Pending Pickup," "Accepted — In Transit," per
the dashboard mockups). Has a specifically documented open modeling
gap: `Task.dealership_id` as a single field can't represent a
two-dealership trade (origin and destination) — deferred, not solved,
until this phase actually starts (see `DATA_MODEL.md`, "Tenant vs
Dealership," and `IMPLEMENTATION_PLAN.md`'s Future Work section).
**Scope note, added at product-owner request:** this phase is
specifically about lot staff having accurate visibility into a dealer
trade's status — it is not a commitment to build driver dispatch,
customer delivery, or any other logistics-management capability. The
Phase 3 frontend mockups bundled "Customer Delivery" onto the same
page as Dealer Trades; that was a frontend authoring decision, not a
product one, and Customer Delivery remains unscoped and out of this
phase unless a future, deliberate decision adds it.

**Phase 5 — Notifications.** A real notification system — not yet
designed in any source document beyond being named and placed here.

**Phase 6 — Referenced, not yet defined.** `ARCHITECTURE.md` mentions
"multi-dealership / Dealer Trades workflows... already scopes this to
Phase 4/6" in one place, bundling a "multi-dealership" concern with
Dealer Trades without separating which phase covers which. Since
Dealer Trades is independently and consistently identified as Phase 4
elsewhere (`DATA_MODEL.md`, `IMPLEMENTATION_PLAN.md`), Phase 6 is left
here as a placeholder for whatever "multi-dealership" means distinctly
from Dealer Trades — genuinely undetermined from existing material.
See "Open questions" below; this document does not guess at its
content.

## Beta Vision (v1.0)

Added at product-owner request, alongside the "Users and stakeholders"
correction above — a concrete answer to "what does a focused, real
beta actually contain," so scope decisions have something specific to
check against instead of the roadmap's phase-level abstractions alone.

**A deployable beta lets lot staff:**
- See today's work as task modules generated from the reconciliation
  engine (install RecovR, verify wholesale, incoming drop-offs, and
  similar — per `ARCHITECTURE.md`'s dashboard vision).
- Open any vehicle and see its complete cross-system story in one
  place — Tekion/Keyper/MDD/RecovR/RapidRecon status, Timeline, open
  Tasks, Recommendations — without opening another system.
- Run Inventory Sync and see connected-systems health.
- Receive lightweight, logged contributions from Tower and Sales (a
  Companion/Quick-Event-Window-shaped mechanism per
  `PRODUCT_BACKLOG.md`, not a department dashboard).

**Explicitly not in beta:** everything under "Permanent product
boundaries" above is out of beta by definition, since those are never
built — no department dashboards, no Requests domain, no Transportation
dispatch workflow, no Controller Audit Queue. Beyond that, beta
specifically defers two items that are genuinely not-yet-decided or
not-yet-needed: the **multi-tab Reports/analytics suite**; and **full
role-based access control** (see "Deferred technical scope" above —
beta needs enough identity to attribute actions to a person, not
department-level permissions).

**Resolved, not deferred: Trade-In is not its own domain model.** An
earlier version of this section listed this as an open architecture
question. It no longer is. A dedicated product-grammar review —
defining LotSync's core objects (Vehicle, Task, Recommendation,
Event/Timeline), then validating them against a full walkthrough of a
lot attendant's actual shift — concluded that a Trade-In without a
resolved stock number is a `PendingIdentity`, and once resolved, its
checklist is a Task-type group like any other. That conclusion is the
result of the exercise, not a convenience adopted to avoid building
something: the same review specifically checked whether
`PendingIdentity` needed its own product surface and found it didn't.
No new model is planned. See `FRONTEND_BACKEND_RECONCILIATION.md`'s
"Product grammar" section and its Trade-In disposition for the full
reasoning.

## Success Definition

What "working" means operationally, at the current stage and as the
roadmap advances — not "code compiles" or "tests pass" (those are
engineering gates, covered in `IMPLEMENTATION_PLAN.md`), but what a
dealership should actually be able to say is true:

- **Today (Phase 1):** Every sync run reliably catches the eight
  categories of cross-system contradiction described in "Current
  capabilities" — a sold vehicle whose key wasn't pulled, a vehicle
  active in Tekion with no key at all, an MDD/RecovR device that was
  never installed — without anyone manually cross-referencing
  spreadsheets. The one-time historical sweep against the full
  2020–present Sold export (per `README.md`) is itself a concrete
  proof point: years of accumulated orphaned records, caught and
  surfaced, that manual comparison had missed.
- **Through Phase 2:** The same catches above, plus memory — a
  discrepancy open for three sync cycles is visibly, queryably
  different from one that just appeared, and a Task closes itself the
  moment its underlying condition resolves rather than waiting for
  someone to notice it's gone. Concretely, per `IMPLEMENTATION_PLAN.md`:
  "has this vehicle's RecovR status changed since yesterday" is
  answerable without recomputing from raw CSVs, and every CSV report a
  dealership currently depends on keeps working, unchanged, throughout.
- **Through Phase 3:** A lot attendant can answer `VISION.md`'s opening
  question — "what's really going on with this car, right now?" —
  directly from a dashboard, for any vehicle, without a phone call.
  Operational awareness (see above) stops being something produced
  once a day into CSV files and becomes something available on demand.
- **Structurally, at every stage:** Nobody has to change how they
  already work to get this — the CSV workflows a dealership runs today
  keep working, unchanged, the whole way through. Success is additive,
  never a disruptive migration.

## Design Principles (for Phase 3 UI)

Not new decisions — these are principles already implicit in choices
this project has already made (`VISION.md`'s principles,
`ARCHITECTURE.md`'s frontend-discovery section, `DATA_MODEL.md`'s
model reasoning), made explicit here so they're available ahead of
Phase 3's actual UI design work, rather than needing to be re-derived
from scattered rationale at that point.

- **Organize around the vehicle, not the source system.** A vehicle
  detail page shows one vehicle's complete cross-source story
  (Tekion/Keyper/MDD/RecovR status together); no view should require
  mentally cross-referencing per-source screens to answer a question
  about one car.
- **A task-type group is a display aggregation, not a unit of work.**
  "Install RecovR Devices — 6 tasks, 1 of 6 complete" is six
  independent, one-vehicle, one-action Tasks grouped for the card —
  never build an interaction that treats the group itself as the
  actionable unit (see `DATA_MODEL.md`, Task).
- **Every recommendation needs a real, visible dismiss path.**
  Consistent with "recommendations help people decide, they don't
  decide for them" (`VISION.md`) — a Recommendation's UI must always
  offer "dismiss" alongside "convert to task," never just the latter.
- **Distinct urgency gets a distinct module, not a shared filtered
  list.** Already-learned lesson from `ARCHITECTURE.md`'s
  frontend-discovery review: "Incoming Drop-Offs" (informational) and
  "Overdue - Investigate" (needs action) must be two separate
  dashboard cards, not one report with a `priority` column standing in
  for two different UI treatments.
- **Show raw signal instead of a guessed label when business meaning
  isn't confirmed.** If a field's mapping to a UI category isn't
  grounded in confirmed dealership workflow (RapidRecon's `Step` is
  the standing example), the UI shows the underlying value for a human
  to judge rather than inventing a bucket for it — the same restraint
  already exercised in the reports themselves.
- **Derive status panels from event data; never maintain a parallel
  status flag.** The "Connected Systems" panel is computed from
  `SyncRun` records grouped by source, not a separately-stored status
  field — avoids exactly the two-sources-of-truth drift `SystemStatus`
  was rejected to prevent (`DATA_MODEL.md`).
- **History reads as narrative, backed by structured data — not the
  reverse.** A Timeline entry displays `Event.summary` ("Keys checked
  out by Sales — 6hrs14min outstanding, typically <2hrs"); the
  underlying `detail_fields` support comparisons and filters, but are
  never the primary display text a user reads.

## Explicit boundaries — what LotSync is not building

Split into two kinds of claim, added at product-owner request: things
LotSync refuses to become regardless of scale or success, and things
LotSync simply hasn't built yet because nothing today requires them.
Confusing the two invites exactly the drift this distinction exists to
prevent — a genuine, demonstrated need can justify building something
in the second group; nothing justifies building something in the
first without a deliberate identity-level decision to change what
LotSync is.

### Permanent product boundaries

True at v1.0 and equally true at any future scale — these don't loosen
as the product grows, they're what keeps it the same product as it
grows.

- **Not a DMS, and not a replacement for Tekion, Keyper, MDD, RecovR,
  or RapidRecon.** Each remains the authoritative system of record for
  what it already tracks. LotSync coordinates between systems; it does
  not consolidate into one.
- **Not vendor software replacement of any kind.**
- **No predictive or ML-based recommendations.** Phase 2's
  `Recommendation` engine is rule-driven only, over the same rules
  already in `rules/aging.py` and `rules/inventory.py` — "AI
  Recommendations" in mockup UI labeling is a display label, not an
  architectural commitment to ML.
- **No business-meaning classification invented from data patterns
  alone** (e.g. RapidRecon's `Step` field, or a repair-duration
  threshold for damaged/in-repair vehicles) without the dealership's
  confirmation grounding it first — see "Product philosophy" above.
- **No department-specific workspaces.** Tower, Sales, Service, and
  Controller are contributors, not primary users (see "Users and
  stakeholders") — LotSync doesn't build a dedicated dashboard,
  approval queue, or workflow surface for any of them beyond the
  lightest mechanism needed to get information to lot staff.
- **No cross-department ticketing or request-routing system.** A
  department needing to tell lot staff something is a lightweight,
  logged contribution — not a formal request object with its own
  department-routing lifecycle competing with Task and Recommendation.
- **No logistics or dispatch platform.** Dealer trade and delivery
  information reaching lot staff (Phase 4) doesn't require driver
  assignment, ETA tracking, or a full dispatch workflow to satisfy that
  need — that's a different, heavier product than the one LotSync is.
- **No controller approval or audit workspace.** Controller's need is
  visibility into what LotSync already surfaces as an exception, not a
  dedicated sign-off queue with its own lifecycle.
- **Not an AI operations manager.** LotSync aggregates, correlates,
  and surfaces evidence. It does not decide a vehicle's operational
  fate — see the confirmed-dealership-policy Product Philosophy entry
  above.

### Deferred technical scope

Not built today because nothing currently demands it — each has a
stated trigger or a documented low-cost path to build it later, and
none of these represent an identity decision. Building one of these
when a real need appears is normal product growth, not drift.

- **Not public multi-tenant SaaS**, now or in the currently-planned
  roadmap above. `Tenant` is a documented future extension point, not
  a current build target.
- **No authentication system** until Phase 3 creates a real multi-user
  access surface requiring one. This doesn't mean full auth ships the
  moment beta does — see "Beta Vision," which scopes beta to enough
  identity for attribution, not department-level access control; full
  role/permission enforcement remains a later Phase 3 decision.
- **No cloud hosting or deployment infrastructure** — not needed for a
  single-dealer-group deployment running locally.
- **No PostgreSQL (or any server-based database)** until Phase 3's web
  app creates genuine concurrent-access need; SQLite is the deliberate
  starting point for Phase 2's single-process, nightly-sync workload.
- **No `Attachment`/`Document` model** — genuinely speculative; no
  real evidence of need has appeared yet.
- **No mobile app** — no current evidence of need.

## Open questions

Identified during this synthesis; not resolved here, since resolving
them would mean inventing product decisions rather than consolidating
existing ones.

1. **What is Phase 6, distinctly from Phase 4 (Dealer Trades)?**
   `ARCHITECTURE.md`'s only reference bundles "multi-dealership" and
   "Dealer Trades" under "Phase 4/6" without separating them. If
   "multi-dealership" means something beyond what `Dealership` (Mark
   Kia/Mazda/Mitsubishi) already covers today — e.g. onboarding an
   unrelated dealer group, which elsewhere reads as the `Tenant`
   concern — that should be stated explicitly, since it would directly
   affect whether Phase 6 and the deliberately-deferred `Tenant` model
   are the same future work or two different ones.
2. **"Milestone" vs. "Phase" numbering.** Two source references
   (`models/task.py`: "lot-staff dashboard (Milestone 2)";
   `models/beacon.py`: "original architecture doc, Milestone 1
   Reconciliation list") use a "Milestone" numbering that's never
   reconciled against the "Phase" numbering used everywhere else
   (including in this document). Milestone 1 appears to correspond to
   the reconciliation engine (Phase 1) and Milestone 2 to the
   dashboard (Phase 3), based on content, but no document states this
   equivalence directly — it's an inference, not a confirmed mapping.
   Worth confirming whether "Milestone" numbering comes from an
   earlier, separate planning document (the "original architecture
   doc" referenced) that should either be retired in favor of Phase
   numbering or reconciled with it explicitly.
3. **This document's own precedent.** Every other governing document
   in this project (`ARCHITECTURE.md`, `DATA_MODEL.md`,
   `IMPLEMENTATION_PLAN.md`) was written and refined against real
   project history, gate reviews, and data discoveries. This document
   was originally a first-pass consolidation from those artifacts, not
   an independently authored product spec — "Users and stakeholders"
   has since received direct product-owner input (see that section's
   own history note) and is no longer an example of this gap; Phase
   5/6 content remains thin because the source material is thin there,
   not because those areas are settled. Where this document is still
   sparse, that's a signal for direct product-owner input, not a gap
   this synthesis should have filled by guessing.
