# LotSync OMS — Data Model

This is the canonical source for model shapes and relationships. If
this document and a docstring in `models/*.py` ever disagree, this
document is correct and the docstring is stale — fix the docstring.

## Tenant vs Dealership (resolved)

Two previously-conflated concepts, separated deliberately:

**Tenant (future concern, NOT modeled).** A completely separate
organization — e.g. Mark Auto Group vs. some other, unrelated dealer
group. Different tenants should never share data. LotSync is not being
built as public SaaS right now; there is no current customer for
tenant management, auth, billing, or routing, and building any of that
speculatively would violate the same "no premature infrastructure"
principle already applied everywhere else in this project. If LotSync
ever becomes a product sold to unrelated dealer groups, `Dealership`
gains a `tenant_id` and becomes a child of `Tenant` — that's the whole
migration. Nothing about the shape below needs to change to support it.

**Dealership (current concern, modeled — see `models/dealership.py`).**
A location/business unit inside one deployment — Mark Kia, Mark Mazda,
Mark Mitsubishi. Vehicles legitimately move between dealerships
(dealer trades, inventory transfers) while remaining the same physical
vehicle. **Dealership boundaries are not identity boundaries.** VIN
remains a vehicle's lifetime identity regardless of which dealership
currently has it.

This also gives the "how does a source record get attributed to a
dealership" problem — previously solved four separate times, ad hoc,
once per source (Keyper's unreliable `System` field, RecovR's
Kia/MARK_AUTO umbrella split, Tekion's single-file scope, RapidRecon's
prefix overlap) — a single place to eventually live, once each
importer's attribution logic is written to resolve to a `Dealership`
record instead of a bare string.

**Known gap, explicitly deferred, not solved:** dealer-trade tasks
("Pending Pickup," "Accepted — In Transit" in the dashboard mockup)
inherently span two dealerships — an origin and a destination — which
`Task.dealership_id` as a single field can't represent. Every Phase 2
task type is genuinely single-dealership, so this isn't a blocker now.
It's Phase 4 (Dealer Trades, per PRODUCT.md) work to design properly —
written down here so it's a planned revisit, not a surprise.


## Models

### Dealership
A location/business unit within one deployment. See "Tenant vs
Dealership" above.

| Field | Notes |
|---|---|
| `dealership_id` | |
| `name` | e.g. "Mark Kia" |
| `brand` | e.g. "Kia" |

### Vehicle
The central object. Represents one physical vehicle, identified by
VIN for its entire lifetime, regardless of which dealership currently
has it.

| Field | Notes |
|---|---|
| `vin` | Primary identity — never scoped by dealership |
| `stock_number` | Current, from Tekion |
| `year`, `make`, `model`, `new_or_used` | |
| `current_dealership_id` | Mutable current attribute, not identity — see "Tenant vs Dealership" |
| `tekion_status`, `keyper_status`, `mdd_status`, `recovr_status` | Flat fields for now — see gate review re: normalized alternative |
| `inventory_state` | Eventual state-machine label (Phase 2) |
| `pending_tasks` | List of open `Task` |
| `history` | List of `Event` |

### Task
One vehicle, one action. NOT a count — "Install RecovR Devices, 6
tasks" on a dashboard is six separate Task rows of the same
`task_type`, grouped for display, not one Task with a quantity. See
ARCHITECTURE.md's frontend discovery section for why this was decided
explicitly rather than left implicit.

**Revised during the Pre-Sprint 4 design review** (see
`DECISION_FRAMEWORK.md`'s "Ontology, Architecture, Invariants, and
Reasoning Tools" section and `SPRINT_4_DESIGN_REVIEW_SUMMARY.md`): a
Task is an operational commitment, not a directive and not a
Recommendation with a richer status — distinguished from both by kind,
not degree. The original three-value `status` couldn't honestly
represent a commitment discharged because it became moot, was
cancelled, or was superseded; closing one of those would have required
either lying (marking it "complete") or leaving it open forever.

**Commitment standing and execution status are independent axes**, the
same cache-over-log pattern `Vehicle.recovr_status` already uses,
confirmed here at a second object: a Task can be `outstanding` while
its execution is `blocked`, or already `cancelled` while execution was
mid-flight. Neither field is derivable from the other.

**Discharge always traces to one of two mechanisms — LotSync never
invents which applies:**
- **Reality-discharged** (`honored`, `moot`) — the world changed. A
  claim from the relevant source satisfied the Task's condition
  (`honored`), or made it irrelevant before it was satisfied (`moot` —
  e.g. the vehicle sold before its RecovR install happened).
- **Intent-discharged** (`cancelled`, `superseded`) — the organization
  changed its own mind, independent of anything the world reported.

Every terminal disposition traces to either a claim (Reality) or a
legitimate authority acting directly (Intent) — never a case where the
system originates the fact of closure on its own.

| Field | Notes |
|---|---|
| `task_id` | |
| `vin` | FK to Vehicle |
| `dealership_id` | Single dealership only — see "Known gap" re: dealer-trade tasks above |
| `task_type` | Controlled vocabulary, e.g. `install_recovr_device` |
| `department` | e.g. "Inventory", "Controller", "Lot Ops", "Dealer Trades" |
| `priority` | "Critical" / "High" / "Medium" / "Low" |
| `commitment_standing` | "outstanding" / "honored" / "moot" / "cancelled" / "superseded" — replaces the original three-value `status` (see above) |
| `execution_status` | Derived cache — "not_started" / "in_progress" / "blocked" / "completed", computed from the most recent `TaskExecutionEvent` for this task. Not independently writable; see `TaskExecutionEvent` below |
| `assigned_employee_id` | Nullable — "Unassigned" is a real, valid state |
| `ratified_by` | `employee_id`, or a standing-policy identifier — who authorized this commitment |
| `ratification_type` | "human" / "standing_policy" — authority is independent from provenance: a Recommendation converting to a Task is provenance, not authority, and a human still ratifies it |
| `escalated_from_task_id` | Nullable; FK to Task — set when this Task exists because a parent Task's condition changed shape rather than simply resolving. Lets Moot-evaluation walk a parent's status instead of only this Task's own condition |
| `reason`, `created_at` | |
| `completed_at` | Set when `commitment_standing` reaches ANY terminal value (`honored`/`moot`/`cancelled`/`superseded`), not only when work is literally "complete" — the name predates the `commitment_standing`/`execution_status` split and is kept rather than renamed, since renaming it isn't required by anything this review demonstrated a need for |

**Known, unresolved gap, not silently assumed:** a dealership transfer
is currently an *implicit* assumption for install-type Tasks (does an
open `install_recovr_device` Task still make sense if the vehicle
moves to a different dealership mid-Task?). Per the "a commitment may
depend only on explicit assumptions" invariant, this must be encoded
explicitly or explicitly excluded before Sprint 4's discharge logic
ships — left open here deliberately, not solved by this review, and
tracked in `SPRINT_4_CHECKLIST.md`.

### TaskExecutionEvent
Append-only log of a Task's execution progress, independent of
`commitment_standing`. Added during the Pre-Sprint 4 design review: a
mutable execution-status field failed the same test `PendingIdentity`
already failed once (see `DECISION_FRAMEWORK.md`) — consecutive
transitions carry real information a terminal snapshot destroys (e.g.
`started → blocked → resumed → completed` tells a materially different
story than `started → completed`, even though both end the same way).

Task completion is itself a manual assertion, not a direct status
write, per `VISION.md`'s existing "manual input is an assertion, not
an override" principle: a human recording `completed` here is
provisional until corroborated by the relevant source's next sync (or
the Task surfaces a contradiction if the source disagrees) — the same
pattern every other manual claim in this system already follows.

| Field | Notes |
|---|---|
| `task_execution_event_id` | Surrogate primary key |
| `task_id` | FK to Task |
| `transition_type` | "started" / "blocked" / "resumed" / "completed" |
| `actor_employee_id` | Nullable — who made this transition |
| `note` | Free text, optional |
| `observed_at` | |

### Event
A single observed change or logged action for a vehicle. Carries a
human-readable `summary` for the Timeline UI separate from
`detail_fields` (structured data behind it), because a raw field diff
alone can't produce the narrative entries the Vehicle Detail mockup
requires. See ARCHITECTURE.md, "Event needed a richer shape."

| Field | Notes |
|---|---|
| `event_id` | Surrogate primary key. Added during Phase 2 Sprint 1 schema work -- Event has no natural unique key (a vehicle can have many events over time), unlike Vehicle (`vin`) or Task (`task_id`), which this table's original definition overlooked. |
| `vin` | FK to Vehicle |
| `event_type` | e.g. "appeared_in_tekion", "keys_checked_out", "dealer_transfer" |
| `source` | "tekion" / "keyper" / "mdd" / "recovr" / "rapidrecon" / "lot" |
| `sync_run_id` | FK to SyncRun — which sync detected this |
| `actor_employee_id` | Nullable — system-detected events have none |
| `dealership_id` | Captured at write time, NOT derived from `Vehicle.current_dealership_id` — keeps past events historically accurate across a later transfer |
| `observed_at` | |
| `summary` | Human-readable, for display |
| `detail_fields` | Structured data (unvalidated dict for now — accepted debt, see gate review) |

### Beacon
An MDD or RecovR physical device, modeled separately from the vehicle
it's attached to (or isn't). Needed for duplicate-beacon detection —
reasoning about a device independent of any one vehicle.

| Field | Notes |
|---|---|
| `device_id` | |
| `device_type` | "mdd" or "recovr" |
| `vin` | Currently assigned vehicle, if any |
| `paired` | |
| `battery_level` | |

### Employee
Added as foundational, not optional, during the frontend discovery
review — nearly every Event and Task carries an attributed actor.

| Field | Notes |
|---|---|
| `employee_id` | |
| `name`, `role`, `department` | |
| `dealership_id` | Home/primary assignment, not a hard constraint — real Keyper data shows staff already work across sister-store lines |
| `status` | e.g. "Available", "Installing", "Lunch" |

### SyncRun
One execution of the reconciliation pipeline against one source.
Every Event traces back to the SyncRun that detected it. The
"Connected Systems" dashboard panel (per-source record count, last
sync time) is a derived view over this, grouped by source — NOT a
separate `SystemStatus` model (deliberately rejected, see
ARCHITECTURE.md, to avoid two sources of truth that can drift).

| Field | Notes |
|---|---|
| `sync_run_id` | |
| `started_at`, `completed_at` | |
| `source` | Which importer this run was for |
| `dealership_id` | Which dealership's export this run processed |
| `records_processed`, `issues_found`, `tasks_generated` | |
| `status` | "in_progress" / "complete" / "delayed" / "failed" -- "in_progress" added during Phase 2 Sprint 3 (Slice 4 implementation): the original three values had no way to describe a row between INSERT and completion, the same category of gap `Event.event_id`'s addition closed in Sprint 1 (a table that can't be correctly built and used as originally specified) |

### Recommendation
Deliberately distinct from Task — has its own lifecycle (shown /
converted to a Task / dismissed) before ever becoming a Task.
Rule-driven (the same rules already in `rules/aging.py` and
`rules/inventory.py`), not ML-driven, despite the "AI Recommendations"
UI label — predictive/ML recommendations are explicitly deferred.

| Field | Notes |
|---|---|
| `recommendation_id` | |
| `vin` | FK to Vehicle |
| `severity` | "Critical" / "High" / "Medium" / "Low" |
| `title`, `detail` | |
| `rule_source` | Which rule generated this, for traceability |
| `status` | "open" / "converted_to_task" / "dismissed" |
| `resulting_task_id` | Nullable |
| `created_at` | Added during Slice 6 implementation — the original table had no way to know when a Recommendation was raised, the same class of gap that added `Event.event_id` and `SyncRun.status`'s `"in_progress"` value |
| `resolved_at` | Nullable; set when `status` moves to `converted_to_task` or `dismissed`. Needed to implement the literal, already-decided requirement that a dismissed Recommendation "does not reappear... unless the underlying vehicle state genuinely changes again" — answering that requires knowing *when* it was dismissed, which the table couldn't previously represent at all |

No `dealership_id` here, deliberately — a Recommendation always
reflects a Vehicle's *current* state, so its dealership is always
derivable via `vin -> Vehicle.current_dealership_id`. Unlike `Event`,
there's no historical-accuracy reason to duplicate the value.

## Relationships

```
Dealership *—1 Tenant (future, not modeled -- see "Tenant vs Dealership")
Vehicle    *—1 Dealership (current_dealership_id, mutable, NOT identity)
Employee   *—1 Dealership (home assignment, not a hard constraint)
Task       *—1 Dealership (single dealership only -- see "Known gap")
SyncRun    *—1 Dealership
Event      *—1 Dealership (captured at write time, historical)

Vehicle 1—* Event
Vehicle 1—* Task
Vehicle 1—* Recommendation
Vehicle *—1 Beacon (current; historical assignments via Event)
PendingIdentity *—0..1 Vehicle (resolved_vin, set only upon resolution -- Slice 3)
Task    *—1 Employee (assigned_to, nullable)
Task    *—1 Vehicle
Task    *—0..1 Task (escalated_from_task_id -- Sprint 4)
Task    1—* TaskExecutionEvent (Sprint 4)
TaskExecutionEvent *—0..1 Employee (actor, nullable)
Event   *—1 Vehicle
Event   *—1 SyncRun
Event   *—0..1 Employee (actor)
SyncRun 1—* Event
Recommendation *—1 Vehicle, produces 0..1 Task on conversion
```

### PendingIdentity
Added during Sprint 2 design discussion, before Slice 2 implementation
began (see `IMPLEMENTATION_PLAN.md` Slice 2 and `SPRINT_2_REVIEW.md`
for the reasoning). Represents an observation from a source that could
not be resolved to a known Vehicle's VIN at the time it was recorded —
Keyper's auto-generated placeholder stock numbers and ambiguous
last-6-VIN matches are the known population today (see
`data_quality_exceptions.csv`). These are real, currently-tracked items
(a physical key sitting in a cabinet), not vehicles in their own right
and not data to be dropped.

This is deliberately a separate model from `Vehicle`, not a `Vehicle`
row with `vin = NULL` or a sentinel placeholder VIN. Two considered
alternatives were rejected: a nullable `vin` as Vehicle's primary key
(defeats `upsert`'s conflict-target semantics — SQL treats every `NULL`
as distinct, so the same unresolved record would re-insert as a new
row on every sync instead of updating in place) and a synthetic
sentinel VIN string (pollutes `vin`'s meaning — every future reader of
`Vehicle` would need to know to filter out non-real values). The
underlying reasoning is the same one that already separated
`Recommendation` from `Task`: an unresolved observation and a known
physical vehicle are different lifecycle stages of the same
real-world thing, and squeezing the former into `Vehicle`'s shape
would be the same mistake in a different spot.

**Resolution is explicitly out of scope for this model's introduction.**
Detecting that a previously-unresolved identifier now resolves (e.g.
after a data-quality fix in Tekion) and promoting it to a real
`Vehicle` + `Event` is a state transition — the first one in this
system — and belongs alongside the general historical-diffing/
change-detection machinery Slice 3 builds, not duplicated here for one
case. See `IMPLEMENTATION_PLAN.md` Slice 3.

| Field | Notes |
|---|---|
| `pending_identity_id` | Surrogate primary key |
| `source` | Which importer produced this observation, e.g. "keyper" |
| `raw_identifier` | The original, unresolved identifier string as observed (e.g. Keyper's raw "name" field value) |
| `identifier_type` | Same vocabulary as `sync/normalizer.py`'s classification -- e.g. `tekion_auto_generated_stock_number`, `unrecognized`, `ambiguous_last6_vin_multiple_matches` |
| `status` | "pending" / "resolved" |
| `first_observed_at` | When this identifier was first seen unresolved |
| `last_observed_at` | Most recent sync that still couldn't resolve it -- what eventually answers "how many cycles has this been pending," the same gap named throughout this project's history |
| `resolved_vin` | Nullable; FK to Vehicle, set only once Slice 3's promotion logic resolves this |
| `resolved_at` | Nullable; when resolution happened |

## Explicitly not modeled yet, and why

- **Tenant** — see "Tenant vs Dealership" above. Not a deferral by
  accident; a deliberate decision with a documented, low-cost
  extension path if it's ever needed.
- **Notification** — Phase 5 per PRODUCT.md; no current evidence forcing this forward.
- **Attachment/Document** — no real evidence of need in current mockups; genuinely speculative if added now.
