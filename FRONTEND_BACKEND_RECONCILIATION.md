# LotSync — Frontend/Backend Architectural Reconciliation

## What this document is

Originally, a one-time architectural bridge between the two LotSync
repositories, produced by studying both completely before any Phase 3
code was written — grounded in a direct read of both repositories, not
inference from summaries (see the original method note preserved in
Sections 1–5 below).

**Revised under v0.7.4 — Product Alignment.** Between the original
pass and this revision, a deliberate, explicit product-owner review
corrected the project's identity: LotSync has one primary user (lot
staff) and a set of contributors (Tower, Sales, Service, Controller),
not several co-equal department audiences — see `PRODUCT.md`, "Users
and stakeholders," and `VISION.md`'s Principles for the full reasoning.
That correction changes the *verdict* this document reaches for a
meaningful fraction of what it originally catalogued, even though the
underlying factual observations (what each frontend file actually
contains) haven't changed and are preserved below rather than deleted
— a screen being wrong for the product isn't a reason to pretend it
was never observed accurately.

**This revision does not implement anything.** It re-evaluates every
object and screen the original pass catalogued against the clarified
identity, using the product grammar established below, and records a
disposition for each: keep, revise, remove, or discuss. Implementation
sequencing (Section 7) is updated to match, but actual UI/API work is
still a separate, later decision.

## Product grammar

Established during the v0.7.4 design sessions, this is the small
vocabulary every object and screen below gets checked against.

**Core objects** — what a lot attendant actually thinks in terms of:
- **Vehicle** — the central entity. Everything else attaches to one.
- **Event**, presented as **Timeline** — the objective history of what
  happened to a vehicle. Event is the stored object; Timeline is how
  `VehicleDetail` renders a list of them.
- **Task** — one vehicle, one action, tracked to a terminal
  disposition (Reality-discharged or Intent-discharged — `DATA_MODEL.md`).
- **Recommendation** — a pattern surfaced for a human to judge, with a
  mandatory dismiss path. Not an instruction. This is the object that
  carries "LotSync surfaces evidence, it doesn't decide" —
  `PRODUCT.md`'s confirmed-dealership-policy-is-context principle.

**Ingestion mechanisms** — not domain objects, the two paths that
produce Events:
- **Sync** — systems reporting automatically (Tekion, Keyper, MDD,
  RecovR, RapidRecon).
- **Quick Log** — people reporting manually, as lightly as possible.
  This is `PRODUCT_BACKLOG.md`'s "LotSync Companion" concept,
  already prototyped as `QuickLog.tsx` — see Section 6.

**Supporting infrastructure** — real, necessary, genuinely invisible
to the user:
- **Employee** — attribution only. Not a department workspace.
- **SyncRun** — the audit record of a sync having happened; powers
  Connected Systems, isn't itself something a user browses.

**Not infrastructure, decomposes into Task:** `PendingIdentity` is
real work a lot attendant needs to see and act on — an unresolved key,
physically present, no confirmed VIN yet. It isn't a fifth core object
and it isn't invisible infrastructure either; it surfaces as a Task
("resolve this unidentified key"), the same way Trade-In decomposes
into `PendingIdentity` + Task rather than becoming its own model
(Section 6).

**The test used throughout this revision:** does the underlying need
survive, and if so, which of the above does it belong to? A screen
disappearing doesn't mean the need behind it was wrong — see each
disposition's reasoning below.

## Disposition summary

Every object and screen the original pass catalogued, re-evaluated.
Full reasoning for the non-obvious calls is in Section 6; this table
is the map.

| Object / Screen | Disposition | One-line reason |
|---|---|---|
| Vehicle | **Keep** | Core grammar. |
| Task | **Keep** | Core grammar; frontend `status` field still needs the `commitment_standing`/`execution_status` correction (Risk #1) — mechanical, unrelated to realignment. |
| Event / Activity | **Keep** | Core grammar, presented as Timeline. |
| Recommendation | **Keep** | Core grammar; carries "evidence, not decisions." |
| SyncRun / Connected Systems | **Keep** | Infrastructure — audit trail for the Sync ingestion path. |
| Employee | **Keep, scoped down** | Attribution only. Team/staffing views beyond bare attribution — see "Needs discussion." |
| Dealership | **Keep** | Infrastructure attribute of Vehicle/Task; needs its migration regardless. |
| Beacon | **Keep as-is** | Backend-only, no frontend need demonstrated; unaffected. |
| PendingIdentity | **Keep, redirected** | Decomposes into Task in the UI, not its own workflow. |
| Request | **Remove** | Permanent boundary — no cross-department ticketing system. Need absorbed into Quick Log. |
| Dealer Trade | **Revise** | Status-visibility need survives via Vehicle + Timeline + Task; dispatch/logistics shape does not (permanent boundary). |
| Customer Delivery | **Remove** | Unscoped in every backend document; now also a permanent-boundary conflict (no logistics platform) unless deliberately revisited. |
| Trade-In | **Revise** | Decomposes into `PendingIdentity` + Task (already the prior recommendation, now confirmed); Controller Audit View removed. |
| Incoming Vehicle | **Revise** | "Incoming Drop-Offs" need survives as a Task-type group; `IntakeStep[]` becomes Task-type group items. |
| Staged Vehicle (kanban) | **Revise** | Converges into `Vehicle.inventory_state` transitions + Task, not an independent, freely-overridable object. |
| Vehicle Movement | **Remove** | Fully overlaps with Task; no distinct need. |
| Exception (rich workflow) | **Revise** | Detection stays essential; the assignable, Controller-owned multi-stage workflow is removed (controller-workspace boundary) — surfaces as Recommendation/Task, Controller gets visibility. |
| Audit Queue Item | **Remove** | Controller-workspace boundary. The legitimate piece (who authorized a Task) already exists as `ratified_by`/`ratification_type`. |
| Notification Preference | **Keep deferred** | Phase 5, unaffected by realignment. |
| Report aggregates | **Discuss** | Not an identity violation, doesn't obviously fit the grammar either — genuinely undecided. |
| Authentication / Role / Session | **Revise** | Scoped to Beta Vision's "enough identity to attribute actions," not the 8-role department RBAC the prototype implies. |
| Lot Staff Dashboard | **Revise → becomes "Dashboard"** | Refocused around Task modules, Recommendations, Activity — the one dashboard, not one of several. |
| Lot Manager Dashboard | **Discuss** | Is a lot manager's view of their own team in-bounds (still lot staff), or should it merge into the single Dashboard? Not identity-violating either way. |
| Tower Manager Dashboard | **Remove** | Department workspace. |
| Controller Dashboard | **Remove** | Department workspace. |
| Vehicles List | **Keep** | Core grammar browsing surface. |
| Vehicle Detail | **Keep** | The centerpiece — Vehicle + Timeline + Task + Recommendation together. |
| Tasks | **Keep** | Pending Risk #1's mechanical correction. |
| Requests | **Remove** | See Request above. |
| Inventory Sync | **Keep** | The Sync ingestion mechanism's trigger/monitor UI. |
| Activity | **Keep** | Event/Timeline browsing surface. |
| Reports | **Discuss** | See Report aggregates above. |
| Incoming Inventory | **Revise** | Folds into Task-type groups / Vehicle state; may not need its own page. |
| Lot Staffing / Team Status | **Discuss** | Same open question as Lot Manager Dashboard. |
| Staging | **Revise** | Folds into `Vehicle.inventory_state` + Task. |
| Vehicle Movement | **Remove** | See object above. |
| Profile | **Revise** | Strip Notification Preference (still Phase 5) and full-auth Session assumptions; keep a simple self-view. |
| Transportation | **Remove** | Dispatch/logistics permanent boundary. |
| DealerTrades.tsx | **Remove, discard as design input** | Likely dead code (Risk #3) and the richest, most identity-violating of three competing shapes — don't mine it for detail. |
| Trade-Ins | **Revise** | See Trade-In object above. |
| QuickLog | **Keep, elevate** | The clearest, most-aligned piece of the whole frontend — the Quick Log ingestion mechanism, already prototyped. Prioritize, don't treat as one feature among many. |

---

## 1. Business Object Inventory (original pass, preserved)

Every business object referenced anywhere in the frontend, deduplicated
across files, as originally catalogued. "Existing backend equivalent"
is answered precisely in Section 2; this section is purely descriptive.
**Dispositions are in the summary table above, not repeated inline
here — this section is the factual record the dispositions were
reasoned from.**

### Vehicle
- **Purpose:** the physical car — the one object nearly every screen
  either lists, filters, or drills into.
- **Owner:** no single department; it's the cross-cutting object
  `PRODUCT.md`'s "Vehicles are the center" principle names.
- **Lifecycle (as the frontend implies it):** Incoming/Expected →
  Intake (checklist) → Staged (kanban stage) → Ready/Active in
  inventory → (Sold | Dealer-Traded | Wholesaled).
- **Relationships:** has Tasks, Events/Activity, Recommendations
  ("Operational Insights"), a current Dealership/zone, a Beacon-like
  device status (recovr/mdd, modeled as flat fields, not a separate
  entity anywhere in the frontend).
- **Fields observed across files:** `vin`, `stock`/`stockNumber`, `year`,
  `make`, `model`, `trim`, `color`, `zone`/`location`, `inventoryAge`/
  `daysInInventory`, `status` (a per-file free-form enum — see
  Architectural Risks), `photo`, `keysOut` (bool), `openTasks` (count),
  `lastSyncHours`, `mileage` (TradeIns only), `tekion`/`keyper`/`mdd`/
  `recovr` status equivalents (named and shaped differently per file).

### Task
- **Purpose:** an actionable, one-vehicle, one-action work item —
  matches `DATA_MODEL.md`'s Task almost exactly in intent.
- **Owner:** whichever department the task type belongs to (Lot,
  Sales, Recon, Controller in `Tasks.tsx`'s vocabulary).
- **Lifecycle (frontend's, as one field):** `outstanding →
  in-progress → waiting-verification → verified`, with `cancelled`/
  `superseded` as alternate terminals.
- **Relationships:** belongs to a Vehicle (sometimes several, via
  task-type grouping, matching `DATA_MODEL.md`'s explicit "task-type
  group is a display aggregation" decision), has a `TaskEvent[]`
  timeline, an optional `TaskReason` (a rule explanation with pass/fail
  checks), an optional `CheckItem[]` checklist, and a `TaskSource`
  (`inventory-sync` / `keyper` / `manager` / `manual` / `insight`).
- **Fields observed:** `id`, `title`, `priority`, `status`, `source`,
  `department`, `vehicles[]`, `assignment`, `dueLabel`, `description`,
  `reason`, `checklist`, `timeline`.
- **Critical mismatch, flagged in Architectural Risks:** the frontend's
  `status` is one field. The backend deliberately split this into two
  independent axes (`commitment_standing` / `execution_status`) during
  the Pre-Sprint 4 design review specifically because a single field
  couldn't honestly represent every real case. The frontend mockup
  predates or was never updated against that review's conclusion.

### Employee / Staff
- **Purpose:** the person doing the work — attribution for nearly
  every Task and Event, exactly as `DATA_MODEL.md`'s Employee entry
  anticipated.
- **Owner:** no single department; a home-department/home-dealership
  concept per person.
- **Lifecycle:** none in the frontend sense (not a work item) — an
  ongoing operational status (`available`/`busy`/`dealer-trade`/
  `break`/`idle` in one file; `Available`/`Driving`/`Dealer Trade`/
  `Installing`/`Lunch`/`Helping Sales` in another).
- **Relationships:** assigned to Tasks, actor on Events, has a
  home zone/department.
- **Fields observed:** `id`, `name`, `initials`, `avatarColor`, `title`/
  `role`, `department`, `status`, `currentAssignment`, `currentVehicle`,
  `tasksToday`/`tasksCompleted`, `openRequests`, `hoursOnClock`, `zone`,
  `recentActivity` (a per-employee activity feed, string-only).

### Event / Activity Log Entry
- **Purpose:** a recorded happening — matches `DATA_MODEL.md`'s Event
  closely, including the same summary-vs-detail split.
- **Owner:** whichever system or person generated it.
- **Lifecycle:** none — an immutable log entry, consistent with
  `DECISION_FRAMEWORK.md`'s "history is append-only" principle.
- **Relationships:** belongs to a Vehicle (`VehicleDetail.tsx`'s
  Timeline) or is employee-scoped (`Profile.tsx`'s "Recent Activity")
  or global (`Activity.tsx`).
- **Fields observed:** `id`, `dateGroup`/`time`, `actor`, `isSystem`
  (bool), `action`, `vehicle`/`vehicleStock`, `status`, `type`.

### Recommendation / Operational Insight / AI Suggestion
- **Purpose:** a system-surfaced pattern a person should look at —
  matches `DATA_MODEL.md`'s Recommendation, including the same
  shown-or-dismissed-before-becoming-a-Task lifecycle.
- **Owner:** the rule that generated it.
- **Lifecycle:** shown → (Create Task | Dismiss).
- **Relationships:** belongs to a Vehicle.
- **Fields observed:** `urgency`/`severity`, `headline`/`title`,
  `detail`, `actions[]` (always including a dismiss-equivalent).

### SyncRun / Connected Systems Status
- **Purpose:** per-source sync health — a near-exact match to
  `queries/dashboard.py`'s `connected_systems_status()`.
- **Owner:** the sync pipeline itself.
- **Lifecycle:** matches `SyncRun.status` almost exactly.
- **Fields observed:** `name`/`source`, `status`, `lastSync`, `records`/
  `recordsProcessed`, `warnings`/`issues_found`.

### Dealership
- **Purpose:** a location/business unit — matches `DATA_MODEL.md`'s
  Dealership in concept, but every frontend instance carries
  substantially more shape than the backend model currently has.
- **Owner:** Mark Auto Group.
- **Lifecycle:** none (a reference entity).
- **Fields observed (union across files, no two agree on shape):**
  `name`, `city`, `state`, `contact` (`DealerTrades.tsx`); `name`,
  `city`, `state` (`Transportation.tsx`); `pickupLocation`,
  `returnDestination` as flat strings (`Requests.tsx`).

### Request
- **Purpose:** a person asking another department to do something —
  **no backend equivalent exists.**
- **Owner:** whichever department receives it.
- **Lifecycle:** `new → accepted/assigned → completed`, with
  `cancelled` as an alternate terminal.
- **Fields observed:** `id`, `type`, `title`, `objective`, `status`,
  `source`, `requestedBy`, `receivedLabel`, `dueTimeLabel`,
  `nextActionLabel`, `vehicles[]`, `assignee`, `dealerInfo`.

### Dealer Trade
- **Purpose:** a vehicle moving between two dealerships.
- **Owner:** Dealer Trades department.
- **Lifecycle:** `awaiting-pickup → in-transit → returned → completed`,
  with `cancelled` as an alternate terminal.
- **Fields observed — three materially different shapes across three
  files** (see Architectural Risks #3):
  1. `DealerTrades.tsx` (not reachable via any nav route): full
     `{name, city, state, contact}`, `vin`, `paperwork[]`, `timeline[]`.
  2. `Transportation.tsx` (the one actually routed): thinner —
     `{name, city, state}`, no VIN, no paperwork, no timeline.
  3. `Requests.tsx`: a flat `dealerInfo: {pickupLocation,
     returnDestination}` — no structured entity.

### Customer Delivery
- **Purpose:** delivering a sold vehicle to a customer — **not named
  anywhere in `PRODUCT.md`'s roadmap.** `Transportation.tsx`'s own
  file header calls the page "Unified Dealer Trades + Customer
  Deliveries" — a frontend authoring decision, not a product one.
- **Fields observed:** `id`, `deliveryNumber`, `status`, `priority`,
  `customer{name,phone}`, `vehicle{...}`, `deliveryAddress`,
  `scheduledTime`, `assignedDriver`, `etaLabel`, `notes`.

### Trade-In
- **Purpose:** a customer's vehicle being taken in — a *different*
  concept from Dealer Trade despite the naming overlap.
- **Lifecycle:** `awaiting-stock → awaiting-keys → awaiting-recovr →
  awaiting-zone → ready → completed`.
- **Fields observed:** `id`, `vin`, `stock?`, `year`, `make`, `model`,
  `trim`, `color`, `mileage`, `purchaseType`, `status`, `assignedTo`,
  `timeline[]`, `auditFlags[]` (present but its Controller "Audit
  History" panel is hardcoded to "No audit events recorded").

### Incoming Vehicle
- **Purpose:** a vehicle expected but not yet on the lot.
- **Owner:** Tower Manager (receiving workflow).
- **Fields observed:** `id`, `stock`, `vin`, `year`, `make`, `model`,
  `color`, `carrier`, `source`, `arrivalStatus`, `etaLabel`,
  `arrivedAt`, `intakeSteps[]` (7 fixed steps), `stagingZone`, `notes`.

### Staged Vehicle (kanban stage)
- **Purpose:** a 7-column kanban (incoming, inspection, fuel, photos,
  ready, showroom, dealer-trade).
- **Lifecycle:** moves between the 7 stages, user-overridable via a
  dropdown — not a real state machine.
- **Fields observed:** `id`, `stock`, `year`, `make`, `model`, `color`,
  `stage`, `priority`, `timeInStage`, `assignedTo`, `note`.

### Vehicle Movement
- **Purpose:** a dispatched, one-time move of a vehicle — heavily
  overlapping with both Task and Request.
- **Fields observed:** `id`, `type`, `label`, `status`, `priority`,
  `requestedBy`, `requestedByTitle`, `requestedAt`, `assignedTo`,
  `dueLabel`, `vehicles[]`, `notes`, `timeline[]`.

### Exception (VIN Exception / Reconciliation Exception)
- **Purpose:** a cross-system contradiction needing human review.
- **Owner:** Controller.
- **Lifecycle:** `Open → Under Review → Pending Approval → Resolved`
  (`Controller.tsx`) or a different 5-value vocabulary
  (`InventorySync.tsx`) for the same conceptual object.
- **Fields observed:** `id`, `vin`, `stock`, `make`, `model`, `type`,
  `days`, `status`, `assignedTo`, `note`.

### Audit Queue Item
- **Purpose:** a pending Controller sign-off (Sold Vehicle Approval,
  Placeholder Stock Approval, Price Override Approval, Trade-In
  Valuation Sign-off) — **no backend equivalent.**
- **Lifecycle:** pending → (Approve | Hold | Reject) — Reject and
  Approve share one handler in the actual mockup, no behavioral
  distinction yet.
- **Fields observed:** `id`, `type`, `vehicle`, `submittedBy`, `time`,
  `priority`.

### Notification Preference
- **Purpose:** per-employee opt-in/out for 8 named event categories.
- **Fields observed (verbatim):** Dealer Trade Assigned, RecovR
  Tracker Verified, Inventory Sync Finished, Vehicle Not Found, Keys
  Checked Out 6+ Hours, Task Overdue, New Request Assigned to Me,
  Morning Sync Complete.

### Report (aggregate views)
- **Purpose:** seven read-only analytics tabs (Daily Summary, Vehicle
  Movement, Dealer Trades, Task Completion, Request Volume, Inventory
  Age, Exception Trends).
- **Backend equivalent:** partially covered by `queries/dashboard.py`'s
  four functions.

### Beacon / Tracker Device
- **Purpose:** matches `DATA_MODEL.md`'s Beacon in concept.
- **Frontend reality:** no file models this as its own entity — every
  reference is a flat field on Vehicle.

---

## 2. Backend Mapping (original pass, preserved)

| Frontend object | Status | Existing backend equivalent | Notes |
|---|---|---|---|
| Vehicle | Fully implemented (schema+persistence), partially (query surface) | `models/vehicle.py`, `vehicle` table | No dedicated single-Vehicle aggregate read query exists yet. |
| Task | Fully implemented, frontend model doesn't match | `models/task.py`, `task`/`task_execution_event` tables | Frontend's single `status` needs reconciling against `commitment_standing`/`execution_status`. |
| Employee | Documented, not implemented | `models/employee.py` (dataclass only) | No migration creates an `employee` table. |
| Dealership | Documented, not implemented, underspecified | `models/dealership.py` (dataclass only) | No migration; backend shape thinner than any frontend usage. |
| Event / Activity | Fully implemented | `models/event.py`, `event` table | Strong match, including summary/detail_fields split. |
| Recommendation | Fully implemented | `models/recommendation.py`, `recommendation` table | Strong match. |
| SyncRun / Connected Systems | Fully implemented, read query built | `models/sync_run.py`, `queries/dashboard.py` | Best-aligned object in the reconciliation. |
| Beacon | Documented, not implemented, not requested by frontend | `models/beacon.py` | Lowest-priority gap. |
| PendingIdentity | Fully implemented backend-side, frontend concept differs | `pending_identity` table | **Now resolved per this revision: decomposes into Task, not a rich workflow of its own.** |
| Request | Frontend only | None | **Now resolved: removed, absorbed into Quick Log.** |
| Dealer Trade | Frontend only, problem space named | `DATA_MODEL.md`'s two-dealership gap | **Now resolved: status-visibility survives, dispatch shape doesn't.** |
| Customer Delivery | Frontend only, unscoped | None | **Now resolved: removed.** |
| Trade-In | Frontend only, unscoped | Decomposes into `PendingIdentity`+Vehicle+Task | **Now confirmed, not just recommended.** |
| Incoming Vehicle | Frontend only, module named | `ARCHITECTURE.md`'s "Incoming Drop-Offs" | **Now resolved: Task-type group.** |
| Staged Vehicle | Frontend only | `Vehicle.inventory_state` (unpopulated placeholder) | **Now resolved: converges into inventory_state transitions.** |
| Vehicle Movement | Frontend only, overlaps Task | None distinct | **Now resolved: removed.** |
| Exception (rich workflow) | Partially implemented | `PendingIdentity`, exception CSVs | **Now resolved: surfaces as Recommendation/Task, no Controller workflow.** |
| Audit Queue Item | Frontend only | Adjacent to Ratification concept | **Now resolved: removed; `ratified_by`/`ratification_type` already covers the real need.** |
| Notification Preference | Frontend only, Phase 5 | None (by design) | Unchanged — correctly deferred. |
| Report aggregates | Partially implemented | `queries/dashboard.py` (4 of ~7 tabs) | Still open — see "Needs discussion." |
| Authentication / Role / Session | Frontend only, explicit prototype | None (by design) | **Now resolved: scoped to Beta Vision's lightweight identity, not 8-role RBAC.** |

---

## 3. Screen Dependency Matrix (original pass, preserved)

| Screen | Backend concepts depended on | Readiness / disposition |
|---|---|---|
| **Lot Staff Dashboard** | Task, SyncRun, Event, Recommendation, TaskExecutionEvent, Employee | **Revise** — becomes the one Dashboard. |
| **Lot Manager Dashboard** | Task counts, SyncRun, Event, Recommendation, Employee | **Discuss** — see Disposition Summary. |
| **Tower Manager Dashboard** | Dealer Trade, Incoming Vehicle, Vehicle Movement, Employee | **Remove** — department workspace. |
| **Controller Dashboard** | PendingIdentity/Exception, Audit Queue Item, Vehicle, SyncRun | **Remove** — department workspace. |
| **Vehicles List** | Vehicle, Task | **Keep.** |
| **Vehicle Detail** | Vehicle, Event, Recommendation, SyncRun | **Keep** — the centerpiece. |
| **Tasks** | Task, TaskExecutionEvent, Recommendation, Employee | **Keep**, pending Risk #1. |
| **Requests** | Request, Vehicle, Employee, Dealership | **Remove.** |
| **Inventory Sync** | SyncRun, PendingIdentity/Exception, Recommendation, Task | **Keep.** |
| **Activity** | Event | **Keep.** |
| **Reports** | Task, Event, Vehicle, Dealer Trade aggregates | **Discuss.** |
| **Incoming Inventory** | Incoming Vehicle, Vehicle | **Revise** — folds into Task-type groups. |
| **Lot Staffing / Team Status** | Employee | **Discuss.** |
| **Staging** | Vehicle (`inventory_state`) | **Revise** — folds into Vehicle state. |
| **Vehicle Movement** | Vehicle Movement (overlaps Task) | **Remove.** |
| **Profile** | Employee, Notification Preference, Session | **Revise** — strip Phase-5/full-auth assumptions. |
| **Transportation** | Dealer Trade, Customer Delivery, Dealership | **Remove** — dispatch boundary. |
| **DealerTrades** | Dealer Trade (richer shape) | **Remove, discard as design input** — likely dead code. |
| **Trade-Ins** | Trade-In (overlaps PendingIdentity/Vehicle/Task) | **Revise** — decomposes. |
| **QuickLog** | Event, TaskExecutionEvent-style assertion, Vehicle lookup | **Keep, elevate.** |

---

## 4. User Action Inventory (original pass, preserved)

Every distinct user-triggered action observed, grouped by the backend
service it would need. Actions tied to now-removed screens are marked
accordingly rather than deleted from the record.

| Action | Backend service needed | Disposition |
|---|---|---|
| Start / Continue / Pause a Task | Task execution service | Keep. |
| Mark Task Complete | Task execution service (assertion) | Keep. |
| Cancel / Escalate Task | Task discharge service | Keep. |
| Create Task from Recommendation | Recommendation conversion service | Keep. |
| Dismiss Recommendation | Recommendation service | Keep. |
| Accept / Assign / Decline a Request | New Request service | **Removed with Request.** |
| Run Sync Now (stub) | Sync-trigger service (doesn't exist yet) | Keep — real gap, still needed. |
| Log Activity via QuickLog | Manual Event/assertion service | Keep, elevate — this is the Quick Log ingestion path. |
| Assign Driver / Reassign (stub) | Assignment service | **Removed with Dealer Trade dispatch / Transportation.** |
| Approve / Hold / Reject (Audit Queue, stub) | New Ratification/approval service | **Removed with Audit Queue.** |
| Resolve / Review an Exception | Exception review service | **Revised** — becomes Recommendation/Task action, not a Controller workflow. |
| Toggle Notification Preference | Notification preference service (Phase 5) | Unchanged, deferred. |
| Edit Profile fields | User preference service (Phase 3) | Keep, scoped down. |
| Sign Out (stub) | Auth/session service (Phase 3) | Keep, scoped to Beta Vision's lightweight identity. |
| Create Trade-In | Decomposes into Vehicle/PendingIdentity upsert | Keep — resolves through Task, not a new endpoint. |
| Bulk actions on Vehicles List (stub, "Coming soon") | Bulk variants | Keep as future work — frontend authors already flagged these unbuilt. |

---

## 5. API Surface (original pass, preserved and trimmed)

Resources and responsibilities Phase 3 will actually need, after
removing what the realignment removed:

- **Vehicles** — read (list with filters, single detail aggregating
  Tekion/Keyper/MDD/RecovR status + open Tasks + Recommendations +
  Timeline), eventually write (manual field corrections).
- **Tasks** — read (list, filtered), write (execution transitions,
  discharge via honor/moot/cancel/escalate) — wraps existing,
  already-tested `database/repository.py` functions.
- **Recommendations** — read (list, per-vehicle), write (dismiss,
  convert-to-task).
- **Events / Activity** — read (global feed, per-vehicle timeline,
  per-employee feed), write (manual event creation — Quick Log's need).
- **Inventory Sync / SyncRuns** — read (`connected_systems_status`,
  run history), and a genuinely new capability: **trigger**.
- **Employees** — read/write, blocked on the missing migration.
- **Dealerships** — same blocker; reconcile the richer field shape
  (`city`/`state`/`contact`) once actually needed, not speculatively.
- ~~Requests~~ — **removed**, no resource needed.
- **Dealer Trades** — read-only status visibility only (Vehicle +
  Timeline + Task), not a dispatch resource; the two-dealership
  Task-modeling question remains real Phase 4 work whenever this is
  actually built.
- ~~Trade-Ins as a resource~~ — **removed**, resolves into existing
  Vehicle/PendingIdentity/Task endpoints.
- **Reports** — undecided, see "Needs discussion."
- **Notifications** — Phase 5, not in scope.
- **Authentication** — scoped to Beta Vision's lightweight identity,
  not the 8-role prototype's full RBAC.

---

## 6. Domain Review (rewritten for v0.7.4)

Every concept that previously needed a "formal design review," now
re-evaluated against the product grammar and permanent boundaries in
`PRODUCT.md`. Most of what previously required careful design work no
longer does — not because it was solved, but because it was removed.

### Transportation (Dealer Trade + Customer Delivery)
**Previously: highest-stakes unresolved area, formal design review
required.** Now: mostly resolved by removal. Customer Delivery was
never scoped in any backend document and is now a permanent-boundary
conflict (no logistics platform) — it stays out unless a future,
deliberate decision adds it. Dealer Trade's *dispatch* shape (driver
assignment, ETA, paperwork checklist, full timeline) is the same
boundary conflict and is removed. What survives: lot staff needs to
know a dealer trade is happening and its rough status — that's a
Vehicle + Timeline + Task need, not a page. The two-dealership Task
gap `DATA_MODEL.md` already named stays exactly as real as it was;
nothing here makes it easier, it just narrows what needs solving to
the status-visibility question instead of a full dispatch model.

### Trade-Ins
**Previously: formal design review required, strong prior toward
extending existing concepts.** Now: confirmed, not just favored. A
Trade-In without a stock number is `PendingIdentity`; once resolved,
its checklist is a Task-type group, identical in shape to install
tasks. No new model. The one addition this revision makes: the
Controller "Audit View" panel is removed outright, not revised —
Controller's need is visibility into what LotSync already surfaces,
not a dedicated view into someone else's workflow.

### Requests
**Previously: formal design review required, likely extends
Recommendation.** Now: removed. Not because the question ("does this
extend Recommendation or become its own object") was answered — it's
moot, because a formal cross-department request object is a permanent
boundary violation regardless of its internal shape. The actual need
— Tower or Sales telling lot staff something — is served by Quick Log
producing an Event, full stop.

### Notifications
**Unchanged: no design review needed yet**, correctly Phase 5 per
`PRODUCT.md`. The realignment doesn't create new urgency here.
`Profile.tsx`'s 8-category list is still useful input for whenever
Phase 5 starts, with the caveat that categories tied to now-removed
concepts (New Request Assigned to Me, Dealer Trade Assigned in its
dispatch sense) will need re-scoping to whatever survives.

### Authentication
**Previously: formal design review required at the start of Phase 3,
informed by 8 role-gated screens.** Still required, but the shape of
the problem changed: most of those 8 roles belonged to screens that no
longer exist (Tower Manager, Controller). Beta Vision already scopes
this down to "enough identity to attribute actions to a person," not
department-level RBAC — the open question this revision leaves is
narrower: how do contributors (Tower, Sales) authenticate at all for
Quick Log, if not through full accounts? That's genuinely undecided,
not resolved by the identity correction alone.

### Employee
**Unchanged: no design review needed** — the model shape is sound,
the migration is purely mechanical. What changed: the frontend's
"staffing dashboard" framing (Lot Staffing, Team Status, per-department
rosters) is now itself a "needs discussion" item, separate from the
Employee model's own soundness — see below.

### Dealership
**Unchanged: no design review needed for the core entity.** Its field
shape still needs a decision, but that decision is now much smaller —
it no longer has to satisfy Transportation's dispatch requirements,
just basic attribution (which store a vehicle is at).

### Needs discussion — genuinely open, not resolved by identity alone

- **Report aggregates.** Doesn't violate any permanent boundary (a
  management-BI view isn't a department workspace lot staff is denied
  access to build), but doesn't obviously belong to the product grammar
  either. Whether this belongs in LotSync at all, ever, is a real
  product-owner question this revision doesn't answer.
- **Lot Manager Dashboard / Lot Staffing / Team Status.** Is a lot
  manager's view of their own team's status a legitimate lot-staff
  need (still inside the primary-user boundary), or does it edge
  toward the department-workspace pattern that was just removed
  elsewhere? Genuinely ambiguous — the manager is still "lot staff" by
  role, but a dedicated staffing screen has a different flavor than
  Vehicle/Task/Timeline.
- **PendingIdentity's actual UI treatment.** Decomposing into Task
  resolves the *model* question; it doesn't yet answer whether that's
  sufficient on its own, or whether an "Investigate Unresolved
  Identities" task-type group needs anything beyond what a normal
  Task-type group already provides.
- **Quick Log authentication**, per the Authentication section above.

---

## 7. Implementation Order (rewritten for v0.7.4)

Recommended sequence — meaningfully shorter than the original, since
several of the original steps' targets no longer exist.

1. **Employee and Dealership migrations.** Unchanged from the original
   recommendation — pure additive schema work, no business-logic risk,
   still needed regardless of everything else in this revision.
2. **A read-only API layer over the existing Phase 2 query surface** —
   `queries/dashboard.py`'s functions, plus a single-Vehicle aggregate
   read and a Task list/detail read. Still the lowest-risk, highest-value
   Phase 3 slice, and now serves a smaller, more focused screen set
   (Dashboard, Vehicles List, Vehicle Detail, Tasks, Activity) instead
   of the original's dozen-plus.
3. **Lightweight identity for attribution** — not full Authentication/
   Role/Session per the original step 3. Enough to know who logged
   what; department-level RBAC is explicitly not beta scope.
4. **The Task model correction** (Risk #1) — unchanged, still needs to
   happen before the Task write-path contract is finalized.
5. **Task/Recommendation write-path API** — unchanged from the
   original; wraps already-tested repository functions.
6. **Quick Log write path** — elevated from the original's step 6.
   This is no longer "the natural point to revisit a backlog entry,"
   it's a core, prioritized piece of the beta experience — the
   contributor-facing ingestion mechanism the whole realignment depends
   on actually working well.
7. **PendingIdentity-as-Task surfacing** — new step, not in the
   original order. Confirm the "Investigate Unresolved Identities"
   Task-type group covers the real need before treating this as done.

**Removed from the original order entirely:** Requests domain design,
Dealer Trades/Transportation/Trade-Ins as their own implementation
phase, Notifications (still correctly last, unchanged — Phase 5).

---

## 8. Architectural Risks (updated for v0.7.4)

Original risks, marked resolved where the realignment resolved them,
kept live where it didn't, plus new risks the realignment itself
introduces.

1. **Frontend Task model re-fuses what the backend deliberately split.**
   **Still live**, unchanged by realignment — see Implementation Order
   step 4.
2. **Employee and Dealership are governed and load-bearing, no
   migration exists.** **Still live** — Implementation Order step 1.
3. **Three incompatible Dealer Trade shapes, one possibly dead code.**
   **Resolved by disposition**, not by confirmation: `DealerTrades.tsx`
   is removed and discarded as design input regardless of whether it's
   confirmed dead — its richer shape described dispatch functionality
   that's now out of scope either way.
4. **"Dealer Trade" and "Trade-In" are unrelated concepts sharing
   "trade" in the name.** **Still live and still worth the same
   discipline** (always use the full two-word terms) for whatever
   status-visibility and PendingIdentity+Task work survives.
5. **Customer Delivery is unscoped in every backend document.**
   **Resolved**: removed, permanent-boundary conflict, not just
   unscoped.
6. **Stale docstrings across every file in `models/`.** **Still live**,
   unrelated to realignment — still worth fixing next time
   `models/*.py` is touched for a real reason.
7. **`QuickLog.tsx` already answers questions `PRODUCT_BACKLOG.md`
   calls unresolved.** **Elevated, not just resolved** — Quick Log is
   no longer one backlog entry among many, it's core beta scope.
8. **Zero API integration surface anywhere in the frontend.** **Still
   live**, now scoped to a smaller action set per the trimmed User
   Action Inventory above.
9. **No shared frontend type definitions.** **Still live** — still
   needs a canonical shape decided deliberately, now over a smaller
   set of objects.
10. **`VehiclesList.tsx` already names its own expected evolution.**
    **Still live and still a good sign** — its named future filters
    (`verification-needed`, `outstanding-tasks`, `operational-insights`,
    `long-inventory`, `recommendations`) all map onto objects that
    survived this revision.

**New risk, introduced by this realignment:**

11. **Don't let "the frontend drifted" become an excuse to under-scrutinize
    the backend or the roadmap.** The identity review found the drift was
    concentrated in the frontend and in a few specific PRODUCT.md/roadmap
    cracks (now fixed) — but that finding is about where drift *was*
    found, not a guarantee about where it can't recur. Future screens or
    capabilities should still be checked against the product grammar and
    permanent boundaries directly, not assumed safe because "the backend
    was already fine."

---

## 9. Documentation Recommendations (updated for v0.7.4)

- **`API_CONTRACTS.md` (existing — update, not create).** Scope to the
  smaller object set: Vehicle, Task, Recommendation, Event, SyncRun,
  Employee, Dealership. Remove or mark deprecated any Request/Dealer-
  Trade-dispatch/Trade-In-as-resource/Audit-Queue shapes it may
  reference.
- **`AUTHENTICATION.md` (new).** Scoped down from the original
  recommendation — needs to resolve lightweight contributor identity
  for Quick Log, not 8 department roles (most of which no longer have
  screens to gate).
- ~~`PERMISSIONS.md`~~, ~~`DOMAIN_TRANSPORTATION.md`~~,
  ~~`DOMAIN_TRADE_INS.md`~~, ~~`DOMAIN_REQUESTS.md`~~ — **no longer
  needed.** Each was scoped to resolve a design question that removal
  made moot, not one that still needs answering.
- **`INTEGRATION_PLAN.md` (new) — still Phase 3's implementation
  plan.** Should feed from this revision's Disposition Summary and
  Implementation Order directly.
- **`DATA_MODEL.md` (update, once Employee/Dealership migrations
  land).** No new entities required by this revision — the grammar
  confirmed the existing model was already close to right, which is
  itself worth recording there.
- **`PRODUCT.md`** — already updated as part of v0.7.4; no further
  action from this document.
- **`PRODUCT_BACKLOG.md` (update).** Remove the Companion/Quick Event
  Window entry's "unscheduled" framing — it's no longer a backlog idea,
  it's core beta scope per this revision. Point to `QuickLog.tsx` and
  Implementation Order step 6.

---

## Summary for whoever picks this up next

The original reconciliation found that Phase 2's backend and the
frontend mockup had independently converged on much of the same
architecture — real, partial validation of the Phase 2 design. This
revision found something different: the frontend mockup had also
independently drifted into treating several departments as co-equal,
workspace-owning users, a drift that had started to creep into
`PRODUCT.md`'s own stakeholder framing before it was caught.

That drift is now corrected, not by inventing new architecture, but by
re-applying a four-object grammar — Vehicle, Event, Task, Recommendation
— that the backend had already, mostly, built correctly. Roughly a
third of what the original document catalogued (Requests, Transportation's
dispatch shape, Customer Delivery, Vehicle Movement, the Audit Queue,
every department-specific dashboard) is removed outright. Another third
(Trade-Ins, Staged Vehicle, Incoming Vehicle, Exception handling,
Authentication) survives with a meaningfully smaller shape. The rest
(Vehicle, Task, Event, Recommendation, SyncRun, Quick Log, and the
screens built directly around them) was already right and stays as-is.

What's left before Phase 3 can start cleanly: the same mechanical work
the original document named (Employee/Dealership migrations, the Task
model correction) plus two genuinely open product questions this
revision deliberately didn't resolve (Report aggregates, and whether
manager/staffing views are in-bounds) — smaller, more specific, and
far fewer than the original's open list.
