# LotSync — Frontend/Backend Architectural Reconciliation

## What this document is

A one-time architectural bridge between the two LotSync repositories,
produced by studying both completely before any Phase 3 code is
written. It does not implement anything, modify the database, or
create an API. Per `PRODUCT.md`'s roadmap and `IMPLEMENTATION_PLAN.md`'s
"Scope boundary," Phase 2 (the persistent operational platform) is
complete and Phase 3 (the web application) has not yet been started as
an explicit product-owner decision — this document is preparation for
that decision, not a substitute for it.

**Method:** every claim below is grounded in a direct read of both
repositories, not inference from summaries. On the backend side:
`VISION.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`,
`DECISION_FRAMEWORK.md`, `PRODUCT_BACKLOG.md`, `IMPLEMENTATION_PLAN.md`,
`PROJECT_STATUS.md`, `SPRINT_4_CHECKLIST.md`,
`SPRINT_4_DESIGN_REVIEW_SUMMARY.md`, `README.md`, every file in
`models/`, `database/repository.py`, all five `database/migrations/*.sql`
files, `queries/dashboard.py`, and `main.py`. On the frontend side:
`src/App.tsx`, `src/VehicleDetail.tsx`, `src/components/QuickLog.tsx`,
and all 17 files in `src/dashboards/` — every one read in full, not
sampled.

**A framing fact that shapes everything below:** the LotSyncWeb repo is
not a new design brief. It is (or is a later iteration of) the exact
"Figma Make mockups" `ARCHITECTURE.md`'s "Frontend discovery" section
already describes reviewing — same tool (`AGENTS.md` confirms this is
a Figma Make project), same vocabulary (Tekion/Keyper/MDD/RecovR/
RapidRecon), same central patterns (Vehicle Timeline, task-type
grouping, AI Recommendations with a dismiss path). Several of
`DATA_MODEL.md`'s decisions (`Employee`, `SyncRun`, `Recommendation`,
`Event.summary`) were already made in response to an earlier pass over
this material. This reconciliation is the second, more literal pass —
reading every screen completely rather than a representative sample —
and it both confirms that earlier work and surfaces what it didn't
cover (see "Business Object Inventory" and "Architectural Risks"
below).

**A second framing fact:** the frontend has **zero backend
integration of any kind**. A repo-wide grep across `src/` for `fetch`,
`axios`, `useQuery`, `useSWR`, `process.env`, and `import.meta.env`
returns nothing. Every page is `useState` over inline mock arrays.
There is no router (`activeNav` string + role switch in `App.tsx`
stands in for routing), no auth, and no shared type definitions across
files — each dashboard independently declares its own `Vehicle`/`Task`/
etc. interface, with overlapping but non-identical field sets. This
means Phase 3 is not "wiring up an existing contract" — it's designing
the contract from scratch, informed by (but not bound by) 19 files'
worth of independently-authored assumptions about what that contract
should look like.

---

## 1. Business Object Inventory

Every business object referenced anywhere in the frontend, deduplicated
across files. "Existing backend equivalent" is answered precisely in
Section 2; this section is purely descriptive.

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
  closely, including the same summary-vs-detail split
  (`ARCHITECTURE.md`'s "Event needed a richer shape").
- **Owner:** whichever system or person generated it.
- **Lifecycle:** none — an immutable log entry, consistent with
  `DECISION_FRAMEWORK.md`'s "history is append-only" principle, which
  the frontend never contradicts (no file lets a user edit a past
  activity entry).
- **Relationships:** belongs to a Vehicle (`VehicleDetail.tsx`'s
  Timeline) or is employee-scoped (`Profile.tsx`'s "Recent Activity")
  or global (`Activity.tsx`).
- **Fields observed:** `id`, `dateGroup`/`time`, `actor`, `isSystem`
  (bool — distinguishes system-detected from human-logged, matching
  `Event.actor_employee_id`'s nullability exactly), `action`, `vehicle`/
  `vehicleStock`, `status`, `type`.

### Recommendation / Operational Insight / AI Suggestion
- **Purpose:** a system-surfaced pattern a person should look at —
  matches `DATA_MODEL.md`'s Recommendation, including the same
  shown-or-dismissed-before-becoming-a-Task lifecycle
  (`PRODUCT.md`'s "every recommendation needs a real, visible dismiss
  path" design principle is honored everywhere this appears).
- **Owner:** the rule that generated it (`rule_source` equivalent not
  explicitly named in the frontend, but every instance has a specific,
  attributable cause).
- **Lifecycle:** shown → (Create Task | Dismiss).
- **Relationships:** belongs to a Vehicle.
- **Fields observed:** `urgency`/`severity` (`critical`/`high`/`medium`/
  `low`, matching backend's Critical/High/Medium/Low vocabulary
  case-insensitively), `headline`/`title`, `detail`, `actions[]`
  (button labels, always including a dismiss-equivalent).

### SyncRun / Connected Systems Status
- **Purpose:** per-source sync health — a near-exact match to
  `queries/dashboard.py`'s `connected_systems_status()`, right down to
  the same underlying justification (`ARCHITECTURE.md`'s explicit
  rejection of a separate `SystemStatus` model in favor of a derived
  view over `SyncRun`).
- **Owner:** the sync pipeline itself.
- **Lifecycle:** matches `SyncRun.status` almost exactly
  (`in-progress`/`running` → `done`/`complete`, with `error` states
  present in `LotStaff.tsx`'s per-source upload simulation that aren't
  in the backend's four-value enum — see Architectural Risks).
- **Fields observed:** `name`/`source`, `status`, `lastSync`, `records`/
  `recordsProcessed`, `warnings`/`issues_found`.

### Dealership
- **Purpose:** a location/business unit — matches `DATA_MODEL.md`'s
  Dealership in concept, but every frontend instance carries
  substantially more shape than the backend model currently has.
- **Owner:** Mark Auto Group (single deployment, consistent with
  `PRODUCT.md`'s deployment scope).
- **Lifecycle:** none (a reference entity).
- **Relationships:** origin/destination pair on DealerTrade; home
  assignment on Employee (not directly modeled in the frontend, but
  implied by staffing pages being per-location).
- **Fields observed (union across files, no two files agree on
  shape):** `name`, `city`, `state`, `contact` (`DealerTrades.tsx`);
  `name`, `city`, `state` (`Transportation.tsx`, no `contact`);
  `pickupLocation`, `returnDestination` as flat address strings, not a
  structured entity at all (`Requests.tsx`). Backend's `Dealership` has
  only `dealership_id`, `name`, `brand` — none of `city`/`state`/
  `contact`/address exist there today.

### Request
- **Purpose:** a person asking another department to do something —
  **no backend equivalent exists.** This is the clearest case of a
  frontend concept that doesn't map onto anything in `DATA_MODEL.md`.
- **Owner:** whichever department receives it (`tower`/`sales`/
  `service`/`recon`/`controller`/`lot`).
- **Lifecycle:** `new → accepted/assigned → completed`, with
  `cancelled` as an alternate terminal — structurally identical in
  shape to Task's commitment lifecycle, but modeled as an entirely
  separate object.
- **Relationships:** requested by an Employee, concerns one or more
  Vehicles, optionally carries `dealerInfo` when `type === 'dealer-trade'`.
- **Fields observed:** `id`, `type`, `title`, `objective`, `status`,
  `source` (person/system/manual — the same three-way provenance split
  `DECISION_FRAMEWORK.md`'s Ontology names for Assertion), `requestedBy`,
  `receivedLabel`, `dueTimeLabel`, `nextActionLabel`, `vehicles[]`,
  `assignee`, `dealerInfo`.
- See Domain Review (Section 6) for whether this should extend
  Recommendation or Task rather than become a new model.

### Dealer Trade
- **Purpose:** a vehicle moving between two dealerships — matches the
  workflow `DATA_MODEL.md` already names as Phase 4 scope
  ("Pending Pickup," "Accepted — In Transit") and already flags as
  having an unresolved two-dealership modeling gap.
- **Owner:** Dealer Trades department (already named in
  `Task.department`'s documented vocabulary).
- **Lifecycle:** `awaiting-pickup → in-transit → returned → completed`,
  with `cancelled` as an alternate terminal.
- **Relationships:** origin Dealership, destination Dealership, one or
  more Vehicles (each tagged `incoming`/`outgoing`), an assigned
  Employee (driver), a paperwork checklist.
- **Fields observed — three materially different shapes across three
  files** (see Architectural Risks #3 for why this matters):
  1. `DealerTrades.tsx` (not reachable via any nav route — see below):
     `origin`/`destination` as `{name, city, state, contact}`,
     `pickupLocation`/`returnLocation` full address strings, `vehicles[]`
     with `vin`, a `paperwork[]` checklist, a full `timeline[]`.
  2. `Transportation.tsx` (the one actually routed): `origin`/
     `destination` as `{name, city, state}` — no `contact`, no address
     strings, no `vin` on vehicles, no paperwork, no full timeline; uses
     the literal string `'Here'` for the home dealership rather than
     naming it.
  3. `Requests.tsx`: a flat `dealerInfo: {pickupLocation,
     returnDestination}` — no structured dealership entity at all.

### Customer Delivery
- **Purpose:** delivering a sold vehicle to a customer — **not named
  anywhere in `PRODUCT.md`'s roadmap, at any phase.** `Transportation.tsx`'s
  own file header calls the page "Unified Dealer Trades + Customer
  Deliveries," meaning the frontend has already bundled this with
  Phase 4 Dealer Trades scope without that decision existing in any
  backend document.
- **Owner:** Sales-adjacent (customer-facing), but dispatched through
  the same Tower/Lot Staff workflow as Dealer Trades in the mockup.
- **Lifecycle:** `scheduled → assigned → en-route → delivered`, with
  `cancelled` as an alternate terminal.
- **Relationships:** one Vehicle, one customer (name/phone, not a
  modeled entity), an assigned Employee (driver).
- **Fields observed:** `id`, `deliveryNumber`, `status`, `priority`,
  `customer{name,phone}`, `vehicle{stock,year,make,model,color}`,
  `deliveryAddress`, `scheduledTime`, `assignedDriver`, `etaLabel`,
  `notes`.

### Trade-In
- **Purpose:** a customer's vehicle being taken in — a *different*
  concept from Dealer Trade despite the naming overlap (see
  Architectural Risks #4). Not named anywhere in `PRODUCT.md`'s
  roadmap at any phase.
- **Owner:** Sales-initiated, Lot/Tower-executed intake.
- **Lifecycle:** `awaiting-stock → awaiting-keys → awaiting-recovr →
  awaiting-zone → ready → completed`. This is, in substance, a Vehicle
  identity-resolution-then-Task-checklist sequence wearing its own
  name — see Domain Review.
- **Relationships:** one Vehicle (which may not yet have a `stock`
  number — i.e., may not yet be resolvable, the same shape
  `PendingIdentity` already exists to hold), an assigned Employee,
  role-gated read/write views (Lot Staff acts on it, Controller has an
  explicit "Audit View — Read Only").
- **Fields observed:** `id`, `vin`, `stock?`, `year`, `make`, `model`,
  `trim`, `color`, `mileage`, `purchaseType` (`customer-trade`/
  `lease-return`/`auction`), `status`, `assignedTo`, `timeline[]`,
  `auditFlags[]` (present but its Controller "Audit History" panel is
  hardcoded to "No audit events recorded" — the UI slot exists, wired
  to nothing).

### Incoming Vehicle
- **Purpose:** a vehicle expected but not yet on the lot — matches
  `ARCHITECTURE.md`'s explicitly-named "Incoming Drop-Offs" dashboard
  module concept.
- **Owner:** Tower Manager (receiving workflow, per this page's own
  file comment).
- **Lifecycle:** `expected/scheduled → arrived/unexpected → (intake
  checklist complete) → staged`.
- **Relationships:** one Vehicle, an `IntakeStep[]` checklist (7 fixed
  steps: arrived, keys received, VIN verified, initial inspection,
  photos, fuel level, ready for staging).
- **Fields observed:** `id`, `stock`, `vin`, `year`, `make`, `model`,
  `color`, `carrier`, `source`, `arrivalStatus`, `etaLabel`,
  `arrivedAt`, `intakeSteps[]`, `stagingZone`, `notes`.

### Staged Vehicle (kanban stage)
- **Purpose:** a finer-grained prep pipeline than Task or Incoming
  Vehicle — a vehicle's position in a 7-column kanban (incoming,
  inspection, fuel, photos, ready, showroom, dealer-trade).
- **Owner:** Tower Manager.
- **Lifecycle:** moves between the 7 stages, user-overridable via a
  dropdown (not a real state machine — any stage can move to any other
  stage directly).
- **Relationships:** one Vehicle per card; no separate entity beyond a
  `stage` field and per-column capacity limits.
- **Fields observed:** `id`, `stock`, `year`, `make`, `model`, `color`,
  `stage`, `priority`, `timeInStage`, `assignedTo`, `note`.

### Vehicle Movement
- **Purpose:** a dispatched, one-time move of a vehicle (lot-move,
  service-pull, showroom, staging, delivery, dealer-trade) — has its
  own request/dispatch/status lifecycle, distinct from (but heavily
  overlapping with) both Task and Request.
- **Owner:** whoever requested it; executed by Lot/Tower staff.
- **Lifecycle:** `requested → assigned → accepted → completed`, with
  `cancelled` as an alternate terminal — a fixed 4-stage timeline is
  rendered per movement (the most structured status-history object
  observed in the whole frontend).
- **Relationships:** one or more Vehicles (each with `fromZone`/
  `toZone`), a requester, an assignee.
- **Fields observed:** `id`, `type`, `label`, `status`, `priority`,
  `requestedBy`, `requestedByTitle`, `requestedAt`, `assignedTo`,
  `dueLabel`, `vehicles[]`, `notes`, `timeline[]`.

### Exception (VIN Exception / Reconciliation Exception)
- **Purpose:** a cross-system contradiction needing human review —
  the frontend's take on what `data_quality_exceptions.csv`/
  `tekion_sync_conflicts.csv`/`PendingIdentity` already catch on the
  backend, but modeled with a richer, assignable workflow.
- **Owner:** Controller (matches `PRODUCT.md`'s stated audience for
  this category of problem exactly).
- **Lifecycle:** `Open → Under Review → Pending Approval → Resolved`
  (`Controller.tsx`) or `pending → in-review → task-created →
  auto-resolved → resolved` (`InventorySync.tsx`) — two different
  status vocabularies for what is conceptually the same object.
- **Relationships:** one Vehicle (by VIN/stock), an assignable Employee.
- **Fields observed:** `id`, `vin`, `stock`, `make`, `model`, `type`
  (`Missing from DMS`/`Not Found on Lot`/`Duplicate VIN`/`Price
  Discrepancy`/`Missing Title`), `days`, `status`, `assignedTo`, `note`.
- **Backend equivalent is narrower than the frontend wants:**
  `PendingIdentity.status` is binary (`pending`/`resolved`). The
  frontend wants a multi-stage human-assignable workflow
  (`Under Review`, `Pending Approval`) that doesn't exist backend-side
  today, for any object.

### Audit Queue Item
- **Purpose:** a pending approval requiring Controller sign-off (Sold
  Vehicle Approval, Placeholder Stock Approval, Price Override
  Approval, Trade-In Valuation Sign-off) — **no backend equivalent.**
  Conceptually the clearest UI expression of
  `DECISION_FRAMEWORK.md`'s Ratification step in the
  Reality → Assertion → History → Interpretation → **Ratification** →
  Commitment → Execution flow, but not connected to that framework
  anywhere in the frontend or backend today.
- **Owner:** Controller.
- **Lifecycle:** pending → (Approve | Hold | Reject) — note: in the
  actual mockup, Reject and Approve share one handler
  (`setApprovedIds`); there is no behavioral distinction between them
  yet, just two labels.
- **Relationships:** submitted by an Employee, concerns one Vehicle.
- **Fields observed:** `id`, `type`, `vehicle`, `submittedBy`, `time`,
  `priority`.

### Notification Preference
- **Purpose:** per-employee opt-in/out for 8 named event categories —
  concrete evidence of what Phase 5 Notifications would need to cover,
  even though `PRODUCT.md` explicitly defers all Notification design
  to Phase 5 ("not yet designed in any source document beyond being
  named").
- **Owner:** each Employee, for themselves (`Profile.tsx`).
- **Fields observed (the 8 categories, verbatim):** Dealer Trade
  Assigned, RecovR Tracker Verified, Inventory Sync Finished, Vehicle
  Not Found, Keys Checked Out 6+ Hours, Task Overdue, New Request
  Assigned to Me, Morning Sync Complete.
- Notably, several of these map directly onto existing backend concepts
  (Task discharge, SyncRun completion, PendingIdentity/Exception
  detection) — this list is a reasonable starting input for Phase 5
  design, not a new domain model in itself.

### Report (aggregate views)
- **Purpose:** seven read-only analytics tabs (Daily Summary, Vehicle
  Movement, Dealer Trades, Task Completion, Request Volume, Inventory
  Age, Exception Trends) — not a domain object, a rendering surface
  over other objects' aggregates.
- **Backend equivalent:** partially covered by `queries/dashboard.py`'s
  four functions (`task_counts_by_department`,
  `inventory_health_percentage`, `recent_activity_feed`,
  `connected_systems_status`), but the frontend's seven tabs go
  considerably further (hourly/daily time-series bar charts,
  per-department breakdowns across five more categories) than anything
  Slice 7 built or validated.

### Beacon / Tracker Device
- **Purpose:** matches `DATA_MODEL.md`'s Beacon in concept
  (duplicate-device detection).
- **Frontend reality:** **no file models this as its own entity.**
  Every frontend reference to RecovR/MDD status is a flat field on
  Vehicle (`recovr: 'installed'|'missing'|'needs-verification'`, etc.).
  No screen shows a beacon independent of the vehicle it's attached
  to, and nothing in the frontend does duplicate-beacon detection.
  This is a case where the frontend has not (yet) demonstrated a need
  for a concept the backend already modeled — worth noting as the
  inverse of the usual gap direction.

---

## 2. Backend Mapping

| Frontend object | Status | Existing backend equivalent | Notes |
|---|---|---|---|
| Vehicle | **Fully implemented** (schema + persistence), **partially implemented** (query/read surface) | `models/vehicle.py`, `vehicle` table (migration 0001) | Core fields (`vin`, `stock_number`, `tekion_status` etc.) all exist and are populated by Phase 2. No dedicated read query for a single Vehicle's full aggregate view exists yet in `queries/dashboard.py` — Slice 7 built dashboard-level aggregates, not a `get_vehicle(vin)` detail read. |
| Task | **Fully implemented** (schema + persistence + lifecycle), **frontend model doesn't match** | `models/task.py`, `task`/`task_execution_event` tables (migration 0004), full `insert_task`/`honor_task`/`moot_task`/`cancel_task`/`escalate_task`/`insert_task_execution_event` API in `database/repository.py` | Backend is *more* architecturally resolved than the frontend here: the frontend's single `status` field needs to be reconciled against the backend's two-axis `commitment_standing`/`execution_status`, not the other way around. |
| Employee | **Documented, not implemented** | `models/employee.py` (dataclass only) | **No migration creates an `employee` table.** Every FK-shaped reference (`Task.assigned_employee_id`, `Event.actor_employee_id`, `Task.ratified_by`) is an unconstrained free-text column today (see migration comments: "no Employee table exists yet"). The frontend's extensive Employee usage (staffing dashboards, status enums, assignment) has no real backend entity to attach to yet. |
| Dealership | **Documented, not implemented, and underspecified** | `models/dealership.py` (dataclass only) | **No migration creates a `dealership` table.** `Vehicle.current_dealership_id`, `Task.dealership_id`, `SyncRun.dealership_id`, `Event.dealership_id` are all unconstrained free-text columns. Even once built, backend's `{dealership_id, name, brand}` shape is thinner than any frontend usage — none of `city`/`state`/`contact`/address exist. |
| Event / Activity | **Fully implemented** | `models/event.py`, `event` table (migration 0001), `insert_event`/`get_last_event_detail_fields` | Strong match, including the `summary`/`detail_fields` split the frontend's Timeline/Activity feed both rely on. |
| Recommendation | **Fully implemented** | `models/recommendation.py`, `recommendation` table (migration 0005), full lifecycle API | Strong match. Frontend's "Operational Insights"/"AI Suggestions" map directly; only gap is the frontend never surfaces `rule_source` for traceability. |
| SyncRun / Connected Systems | **Fully implemented, with a read query already built** | `models/sync_run.py`, `sync_run` table (migration 0003), `queries/dashboard.py`'s `connected_systems_status()` | Best-aligned object in the entire reconciliation — the backend's exact intended read shape already exists and was validated at Sprint 4. |
| Beacon | **Documented, not implemented, not yet requested by frontend** | `models/beacon.py` (dataclass only) | No migration, no frontend screen treats it as its own entity either. Lowest-priority gap — nothing currently depends on it. |
| PendingIdentity | **Fully implemented backend-side, frontend concept is different shape** | `models/task.py`... `pending_identity` table (migration 0002), full promotion logic | Backend's binary `pending`/`resolved` doesn't cover the frontend's desired `Under Review`/`Pending Approval` workflow (see Exception, above) — this is a genuine gap, not just a naming difference. |
| Request | **Frontend only** | None | No backend model, table, or vocabulary corresponds to this at all. See Domain Review. |
| Dealer Trade | **Frontend only**, but its *problem space* is named | `DATA_MODEL.md`'s documented, deliberately-unsolved "dealer-trade tasks span two dealerships" gap | The gap was already identified and explicitly deferred to Phase 4 — the frontend's three inconsistent shapes are new information about *what* Phase 4 needs to resolve, not a contradiction of the deferral itself. |
| Customer Delivery | **Frontend only, and not scoped in any backend document** | None | Doesn't appear in `PRODUCT.md`'s roadmap at all, at any phase. Requires an explicit product-owner scoping decision before anything else. |
| Trade-In | **Frontend only, and not scoped in any backend document** | None directly, but decomposes heavily into `PendingIdentity` + `Vehicle` + `Task` | See Domain Review — likely should not become an independent model. |
| Incoming Vehicle | **Frontend only**, but the *dashboard module* is named | `ARCHITECTURE.md`'s explicitly-planned "Incoming Drop-Offs" module | The module concept was already anticipated; the `IntakeStep[]` checklist shape is new information for how to build it (likely a Task-type group, consistent with how every other checklist-shaped thing in this system already works). |
| Staged Vehicle | **Frontend only** | Loosely: `Vehicle.inventory_state` (the "eventual state-machine label," per `DATA_MODEL.md`, not yet built) | The kanban's 7 stages look like a candidate concrete value set for `inventory_state`, which today is an unpopulated placeholder field. |
| Vehicle Movement | **Frontend only**, heavily overlapping with Task | None distinct | See Domain Review — the frontend's own `Movement` object and backend's `Task` cover almost the same ground (one vehicle, one dispatched action, requester, assignee, timeline) with different names. |
| Exception (rich workflow) | **Partially implemented** | `PendingIdentity`, `data_quality_exceptions.csv`, `tekion_sync_conflicts.csv` | The underlying detection already exists; the assignable, multi-stage review workflow around it does not. |
| Audit Queue Item | **Frontend only** | Conceptually adjacent to `DECISION_FRAMEWORK.md`'s Ratification step, but not implemented as any entity | No `ratified_by`/`ratification_type`-style workflow exists independent of Task today. |
| Notification Preference | **Frontend only, Phase 5 per PRODUCT.md** | None (by design — Phase 5 not started) | Correctly out of scope right now; useful input for later. |
| Report aggregates | **Partially implemented** | `queries/dashboard.py` (4 of the ~7 tabs' worth of data needs) | Slice 7 proved the pattern works; extending it to cover Vehicle Movement/Dealer Trades/Request Volume/Inventory Age/Exception Trends is additive, not architecturally new work. |
| Authentication / Role / Session | **Frontend only, explicitly a prototype** | None (by design — Phase 3 not started) | `RoleSwitcher` is labeled "Switch Role — Prototype" in its own UI text; this is honest mockup scaffolding, not a design proposal to build against literally. |

---

## 3. Screen Dependency Matrix

For each page: the backend concepts it depends on, and how close that
dependency already is to being servable.

| Screen | Backend concepts depended on | Readiness |
|---|---|---|
| **Lot Staff Dashboard** (`LotStaff.tsx`, default view) | Task (outstanding, priority, dispatch), SyncRun/Connected Systems, Event (Live Activity), Recommendation, TaskExecutionEvent (the "Verification Needed" pending-confirmation pattern), Employee (current user) | Mixed — Task/SyncRun/Event/Recommendation are Fully Implemented; Employee (current-user identity) is Documented Only. |
| **Lot Manager Dashboard** (`LotManager.tsx`) | Task (`task_counts_by_department` is a literal match), SyncRun, Event, Recommendation (AI Suggestions), `inventory_health_percentage` (literal match), Employee (team roster) | Best-aligned dashboard in the app — two of its panels map onto already-built, already-tested query functions. |
| **Tower Manager Dashboard** (`TowerManager.tsx`) | Dealer Trade, Incoming Vehicle, Vehicle Movement, Employee (staffing) | Weakest — three of four depended-on concepts are Frontend Only. |
| **Controller Dashboard** (`Controller.tsx`) | PendingIdentity/Exception, Audit Queue Item, Vehicle (aggregate counts), SyncRun | Mixed — Exception detection exists; the assignable review/audit workflow around it does not. |
| **Vehicles List** (`VehiclesList.tsx`) | Vehicle (core fields), Task (open count) | Closest 1:1 match to an existing model of any screen in the app. |
| **Vehicle Detail** (`VehicleDetail.tsx`) | Vehicle, Event (Timeline), Recommendation (Operational Insights), SyncRun (per-system cards) | This screen *is* `ARCHITECTURE.md`'s stated Phase 2 target made literal — "one Vehicle object shows Tekion/Keyper/MDD/RecovR status together." All four dependencies are Fully Implemented; only a single-vehicle detail *query* needs to be written (it doesn't exist yet — Slice 7 built dashboard aggregates, not this). |
| **Tasks** (`Tasks.tsx`) | Task, TaskExecutionEvent (timeline), Recommendation (`source.type === 'insight'`), Employee (assignment) | Data layer ready; frontend's Task *shape* needs correction first (see Architectural Risks #1) before an API contract should be finalized against it. |
| **Requests** (`Requests.tsx`) | Request (none), Vehicle, Employee, Dealership (`dealerInfo`) | Needs a domain decision before any backend work (see Domain Review). |
| **Inventory Sync** (`InventorySync.tsx`) | SyncRun (literal match), PendingIdentity/Exception, Recommendation, Task (`tasks_generated`) | Strong match on SyncRun; the "Run Sync Now" trigger action itself has no backend endpoint concept at all yet (this is currently a scheduled/manual `main.py` run, not a callable service). |
| **Activity** (`Activity.tsx`) | Event | Closest 1:1 match to Event of any screen — this is essentially `recent_activity_feed()` with richer client-side filtering. |
| **Reports** (`Reports.tsx`) | Task, Event, Vehicle, Dealer Trade (aggregates across all) | Partially ready (4 of 7 tabs' data shape already proven at Slice 7); 3 tabs (Vehicle Movement, Dealer Trades, Request Volume) depend on Frontend Only concepts. |
| **Incoming Inventory** (`IncomingInventory.tsx`) | Incoming Vehicle (new), Vehicle | The named "Incoming Drop-Offs" module was anticipated; the `IntakeStep[]` checklist shape needs a decision (new entity vs. Task-type group). |
| **Lot Staffing / Team Status** (`LotStaffing.tsx`) | Employee | Blocked entirely on Employee's missing migration. |
| **Staging** (`Staging.tsx`) | Vehicle (`inventory_state` candidate values) | Frontend Only concept, but plausibly just populates an already-modeled, currently-unused field. |
| **Vehicle Movement** (`VehicleMovement.tsx`) | Vehicle Movement (new, overlaps with Task) | Needs the Task-vs-Movement decision in Domain Review before backend work. |
| **Profile** (`Profile.tsx`) | Employee (self), Notification Preference (new, Phase 5), Session (new, Phase 3 auth) | Blocked on both Employee's missing migration and Phase 3 auth not having started. |
| **Transportation** (`Transportation.tsx`) | Dealer Trade, Customer Delivery (new, unscoped), Dealership (pairs) | Needs product-owner scoping for Customer Delivery before any backend design. |
| **DealerTrades** (`DealerTrades.tsx`) | Dealer Trade (richer shape) | **Not reachable via any nav route in the current app** — see Architectural Risks #3. Likely stale mockup debris superseded by `Transportation.tsx`, but this should be confirmed, not assumed. |
| **Trade-Ins** (`TradeIns.tsx`) | Trade-In (new, unscoped, overlaps with PendingIdentity/Vehicle/Task) | Needs a domain decision before any backend work (see Domain Review). |
| **QuickLog** (embedded in Lot Staff Dashboard) | Event (creation), TaskExecutionEvent-style assertion, Vehicle lookup | Directly implements `PRODUCT_BACKLOG.md`'s "LotSync Companion" concept — see Architectural Risks #7. |

---

## 4. User Action Inventory

Every distinct user-triggered action observed, grouped by the backend
service it would need. (Actions that are currently pure UI stubs with
no handler wired — noted explicitly per-file by the research passes —
are marked **(stub)**; these need a real decision, not just a backend
endpoint, since nobody has yet specified what they should do.)

| Action | Backend service needed | DB writes | Activity logging | Permission checks | Notification implications | Audit requirements |
|---|---|---|---|---|---|---|
| Start / Continue / Pause a Task | Task execution service | `task_execution_event` insert, `task.execution_status` cache update | Yes — the transition itself is the log entry | Assignee or manager role | "Task Overdue" pref if it stalls | Full — append-only by design |
| Mark Task Complete | Task execution service (assertion, not direct status write) | `task_execution_event` insert (`transition_type='completed'`) — **not** `commitment_standing` | Yes | Assignee | None currently named | Provisional until source corroborates (`VISION.md`'s assertion principle) — must surface disagreement if the source disputes it |
| Cancel / Escalate Task | Task discharge service | `_discharge_task` (cancelled/superseded) + possible new Task on escalate | Yes | Manager-level (Intent-discharge requires `ratified_by`) | None currently named | `ratified_by`/`ratification_type` required — Authority is independent from provenance |
| Create Task from Recommendation | Recommendation conversion service | `convert_recommendation_to_task` | Yes | Manager-level (ratification) | None currently named | `ratified_by` required |
| Dismiss Recommendation | Recommendation service | `dismiss_recommendation` | No (lightweight, per `DATA_MODEL.md`'s own reasoning — no ratification tracked) | Any assigned viewer | None currently named | None beyond `resolved_at` |
| Accept / Assign / Decline a Request | **New Request service** (see Domain Review) | New table needed | Yes, ideally | Role-gated (manager vs. non-manager already differ in the mockup) | "New Request Assigned to Me" pref already named in Profile | Needs a decision — see Domain Review |
| Run Sync Now **(stub)** | Sync-trigger service — doesn't exist; today `main.py` is invoked manually/on schedule | `sync_run` row via existing `sync_run()` context manager | Yes (already the case) | Likely Controller/admin-only | "Morning Sync Complete" / "Inventory Sync Finished" prefs already named | Already fully audited via `SyncRun` |
| Log Activity via QuickLog | Manual Event/assertion service | `insert_event`, and for `recovr`/`mdd`/`tag` action types, `task_execution_event`-style provisional assertion | Yes — this action **is** activity logging | Any logged-in employee | None currently named, but conceptually close to several existing prefs | Provisional-until-corroborated, exactly like Task completion — the mockup's own UI copy ("queued for verification... Inventory Sync will confirm it") already states this pattern correctly |
| Assign Driver / Reassign (Dealer Trade, Delivery, Movement) **(stub in most files)** | Assignment service, likely shared across Task/Movement/DealerTrade | Update to `assigned_employee_id`-equivalent | Yes | Manager/Tower-level | None currently named | None beyond normal attribution |
| Approve / Hold / Reject (Audit Queue) **(stub — Approve and Reject share one handler today)** | **New Ratification/approval service** (see Domain Review) | No backend equivalent exists | Yes, ideally | Controller-only | None currently named | This is exactly what `DECISION_FRAMEWORK.md`'s Ratification concept is for — worth designing against that vocabulary directly rather than inventing new terms |
| Resolve / Review an Exception | Exception review service (richer than `PendingIdentity`'s binary state) | Needs new status field(s) beyond `pending`/`resolved` | Yes, ideally | Controller | None currently named | See Section 2 gap note |
| Toggle Notification Preference | Notification preference service (Phase 5) | New table needed | No | Self only | This *is* the notification system's configuration | None |
| Edit Profile fields, change theme/density | User preference service (Phase 3) | New table needed | No | Self only | None | None |
| Sign Out **(stub)** | Auth/session service (Phase 3) | Session invalidation | Possibly (login/logout events already appear as mock Activity entries) | Self | None | Standard session audit |
| Create Trade-In | See Domain Review — likely decomposes into existing `Vehicle`/`PendingIdentity` upsert, not a new "create" endpoint | `vehicle` upsert (if VIN resolves) or `pending_identity` upsert | Yes | Sales Manager / Tower Manager (role-gated in mockup) | None currently named | Same provisional/corroboration pattern as everything else manually asserted |
| Bulk actions on Vehicles List (Create Task, Move Zone, Log Activity, Export) **(all four explicitly disabled "Coming soon" in the mockup itself)** | Bulk variants of the above services | Varies | Varies | Varies | None | None — frontend authors already flagged these as unbuilt, not a gap this review discovered |

---

## 5. API Surface

Resources and responsibilities, not endpoint-level detail — per the
task's framing, this identifies *what* Phase 3 will need to expose,
not routes/verbs.

- **Vehicles** — read (list with filters, single detail aggregating
  Tekion/Keyper/MDD/RecovR status + open Tasks + Recommendations +
  Timeline), and eventually write (manual field corrections, though no
  frontend screen currently asks for this directly).
- **Tasks** — read (list, filtered by department/priority/assignee/
  commitment_standing), write (create execution-transition, discharge
  via honor/moot/cancel/escalate — all of which already exist as
  `database/repository.py` functions and just need a thin service
  layer over them).
- **Recommendations** — read (list, per-vehicle), write (dismiss,
  convert-to-task).
- **Events / Activity** — read (global feed, per-vehicle timeline,
  per-employee feed), write (manual event creation — QuickLog's
  primary need).
- **Inventory Sync / SyncRuns** — read (`connected_systems_status`
  equivalent, run history), and a genuinely new capability: **trigger**
  (today, sync only runs via direct `main.py` invocation; "Run Sync
  Now" has no backend concept to call at all).
- **Employees** — read/write, but **blocked on the missing migration**
  — this needs to be built before it can be an API surface at all.
- **Dealerships** — same blocker; additionally needs the frontend's
  richer shape (`city`/`state`/`contact`) reconciled into the schema
  before the API can honestly represent what three different frontend
  files already assume exists.
- **Requests** — pending the Domain Review decision below; if it
  extends Recommendation, this may not need to be a separate top-level
  resource at all.
- **Dealer Trades / Transportation** — pending a canonical shape
  decision (Section 6) and the two-dealership Task-modeling question
  `DATA_MODEL.md` already named as unresolved.
- **Trade-Ins** — pending the Domain Review decision; may resolve into
  existing Vehicle/PendingIdentity/Task endpoints rather than a new
  resource.
- **Reports** — read-only aggregate endpoints, extending
  `queries/dashboard.py`'s existing four functions to cover the three
  additional tabs the frontend wants.
- **Notifications** — Phase 5, not in scope for this API surface.
- **Authentication** — Phase 3's own gate; needs to formalize the 8
  frontend roles into real accounts/roles/permissions, replacing the
  explicitly-labeled prototype `RoleSwitcher`.

---

## 6. Domain Review

Frontend concepts that exist only as UI, evaluated for whether they
extend an existing backend concept or need a new domain model — and
whether each deserves a formal design-review process (the same kind
`ARCHITECTURE.md`/`DATA_MODEL.md` document having already run for
Vehicle, Task, and Event) before implementation.

### Transportation (Dealer Trade + Customer Delivery)
**Recommendation: formal design review required, and it should happen
before any schema work — the highest-stakes unresolved area in this
whole reconciliation.** Three separate issues compound here:
1. `DATA_MODEL.md` already named the two-dealership problem as an open
   gap for Dealer Trade specifically — this reconciliation adds no new
   information to *that* gap, but confirms it's real by showing three
   independent frontend attempts to represent it, none matching the
   backend's single `dealership_id` field.
2. The frontend has already, unilaterally, decided Customer Delivery
   is the same page/workflow as Dealer Trade ("Unified Dealer Trades +
   Customer Deliveries"). Nothing in `PRODUCT.md` says these are the
   same product concept, or even that Customer Delivery exists as a
   planned capability at all. This should not be silently accepted
   just because the mockup bundled them — it's a real scope question
   for the product owner.
3. Three inconsistent shapes for the same conceptual object
   (`DealerTrades.tsx` vs. `Transportation.tsx` vs. `Requests.tsx`'s
   `dealerInfo`) mean there is no single "the frontend's design" to
   extend — a canonical shape has to be decided, not extracted.

### Trade-Ins
**Recommendation: formal design review required, with a strong prior
that this should extend existing concepts rather than become a new
model.** Per `PRODUCT.md`'s "prefer extending existing domain concepts"
philosophy: a Trade-In without a stock number is exactly what
`PendingIdentity` already exists to represent (a real, physically
present item without a resolved identity yet). Once it resolves, the
checklist (`Mark Keys Received` → `Mark RecovR Installed` → `Assign
Parking Zone` → `Confirm Inventory Ready`) is structurally identical to
a Task-type group — the same "one vehicle, one action, grouped for
display" pattern `DATA_MODEL.md` already settled for install tasks.
Building a parallel `TradeIn` entity with its own status enum would
duplicate machinery that already exists and is already tested, for no
apparent behavioral gain — this is worth surfacing to the product
owner as a specific tradeoff (extend PendingIdentity + Task vs. build
new), not deciding silently either way.

### Requests
**Recommendation: formal design review required.** Structurally, a
Request's lifecycle (`new → accepted → completed`, with a dismiss/
decline path) is nearly identical to Recommendation's
(`open → converted_to_task → dismissed`) — the only real difference is
*provenance* (a person asking vs. a rule firing), which
`DECISION_FRAMEWORK.md`'s Ontology already treats as a same-shape
distinction (Assertion's `source` can be a system or a person without
needing two different models). Worth asking directly: should Request
become "Recommendation, human-sourced" rather than a fourth parallel
object alongside Task/Recommendation/Request? This is exactly the kind
of design-tradeoff-surfaced-not-silently-decided moment
`DECISION_FRAMEWORK.md`'s own reasoning tools were built for.

### Notifications
**Recommendation: no design review needed yet** — correctly Phase 5
per `PRODUCT.md`, and nothing in this reconciliation surfaces urgency
to move it earlier. `Profile.tsx`'s 8-category preference list is
useful, concrete input to hand to whoever eventually scopes Phase 5,
not a reason to start early.

### Authentication
**Recommendation: formal design review required, at the start of
Phase 3** (per `PRODUCT.md`, this is already the named trigger point).
The frontend's 8 roles, and the fact that at least three screens
(`Requests.tsx`, `TradeIns.tsx`, `Transportation.tsx`) already
role-gate behavior differently per role, means real design work is
needed here beyond "add a login screen" — a Role/Permission model has
implicit requirements already visible in the mockup that should inform
the design rather than be re-derived from scratch.

### Employee
**Recommendation: no design review needed — this is a straightforward
build, not a design gap.** The model shape in `DATA_MODEL.md` is
already sound; what's missing is purely mechanical (a migration).
Extend the existing model with what the frontend's usage newly
reveals as needed (a richer `status` value set, `currentAssignment`)
rather than treating this as unresolved.

### Dealership
**Recommendation: no design review needed for the core entity, but
its field shape needs a decision alongside the Transportation review
above** (they're the same underlying question — what does a
Dealership need to hold to make Dealer Trade origin/destination
meaningful). Don't resolve Dealership's shape independently of that
review; the two are coupled.

---

## 7. Implementation Order

Recommended sequence, based on architectural dependency, not on which
page a stakeholder might want first.

1. **Employee and Dealership migrations.** Nearly everything else in
   this document depends on these existing as real, FK-backed tables
   rather than unconstrained free-text columns — `Task.
   assigned_employee_id`, `Vehicle.current_dealership_id`,
   `Event.actor_employee_id`/`dealership_id`, `SyncRun.dealership_id`
   are all already declared as columns, deliberately left
   unconstrained "until that table exists" per multiple migration
   comments. This is pure additive schema work with no business-logic
   risk — the safest possible starting point, and it unblocks the
   Lot Staffing, Team Status, and Profile screens immediately.
2. **A read-only API layer over the existing Phase 2 query surface.**
   `queries/dashboard.py`'s four functions, plus new read queries for a
   single Vehicle's aggregate detail (Tekion/Keyper/MDD/RecovR status +
   open Tasks + Recommendations + Timeline — the exact shape
   `VehicleDetail.tsx` and `ARCHITECTURE.md`'s stated Phase 2 target
   both already describe) and a Task list/detail read. This is the
   lowest-risk Phase 3 slice: no new write paths, reuses fully-tested
   Phase 2 code, and immediately lights up VehiclesList, VehicleDetail,
   Activity, Tasks (read-only), and both manager dashboards.
3. **Authentication/Role/Session**, per `PRODUCT.md`'s own stated
   Phase 3 trigger — needed before any write endpoint should be
   exposed to more than one trusted caller, and before the frontend's
   `RoleSwitcher` prototype can be replaced with something real.
4. **A correction pass on the frontend's Task model** — expose
   `commitment_standing` and `execution_status` as two independent
   signals (already anticipated in `SPRINT_4_CHECKLIST.md`'s "UI/API
   implications" section, now confirmed as a real, present gap by this
   reconciliation) *before* the Task write-path API contract is
   finalized, so the contract isn't designed around a UI assumption
   that's already known to be wrong.
5. **Task/Recommendation write-path API** — start/pause/complete/
   cancel/escalate, convert/dismiss. Directly wraps existing,
   already-tested `database/repository.py` functions; wires up the
   majority of currently-stubbed action buttons across Tasks,
   Dashboards, and VehicleDetail.
6. **Manual assertion / QuickLog write path** — Event creation plus
   the provisional-assertion pattern, reusing exactly what Task
   completion already does. This is also the natural point to revisit
   `PRODUCT_BACKLOG.md`'s Companion/Quick Event Window entry, since its
   own stated trigger ("when Phase 3 planning actually begins") is now
   true, and the mockup has already made several of that entry's
   open design choices concretely (see Architectural Risks #7).
7. **Requests domain design and API** — sequenced after Task/
   Recommendation's write path since the Domain Review recommendation
   (extend Recommendation's shape) depends on that lifecycle already
   being solid and tested.
8. **Dealer Trades / Transportation / Trade-Ins / Customer Delivery** —
   Phase 4 scope per `PRODUCT.md`, sequenced last both because the
   product document already places it there and because this
   reconciliation surfaces real, unresolved modeling questions (two-
   dealership Tasks, Customer Delivery's scope, Trade-In's relationship
   to PendingIdentity) that need the design reviews in Section 6
   resolved first, not concurrently with implementation.
9. **Notifications** — Phase 5, last, per `PRODUCT.md`. Capture
   `Profile.tsx`'s 8-category list as input now; don't build against it
   yet.

---

## 8. Architectural Risks

1. **Frontend Task model re-fuses what the backend deliberately split.**
   `Tasks.tsx`'s single `status` field
   (`outstanding|in-progress|waiting-verification|verified|cancelled|
   superseded`) is exactly the shape the Pre-Sprint 4 design review
   rejected for the backend, for named reasons (`DATA_MODEL.md`,
   `SPRINT_4_DESIGN_REVIEW_SUMMARY.md`). This isn't a cosmetic
   mismatch — building an API contract around the frontend's current
   shape would reintroduce a problem the backend already solved.
   **Resolution:** correct the frontend model (Section 7, step 4)
   before finalizing the Task API contract; don't let contract design
   proceed from the mockup's shape as-is.

2. **Employee and Dealership are governed, modeled, and load-bearing —
   and have no migration.** `DATA_MODEL.md` calls Employee "foundational,
   not optional," and both are cited throughout `ARCHITECTURE.md`. But
   `database/migrations/` has no file for either, and every referencing
   column across four tables is explicitly, deliberately unconstrained
   "until that table exists." This is a real documentation-vs-
   implementation gap worth naming plainly: the models are correctly
   designed, but two Phase 2 entities that everything else assumes
   exist were never actually built. **Resolution:** Section 7, step 1.

3. **Three incompatible Dealer Trade shapes, one of them possibly
   dead code.** `DealerTrades.tsx` is not reachable from any
   `activeNav` route in `App.tsx` — a repo-wide check confirms nothing
   imports or renders it. It may be earlier mockup work superseded by
   `Transportation.tsx`'s simpler "Dealer Trades" tab, or it may be
   intended future UI nobody wired up yet. **This should be confirmed
   with whoever owns the frontend repo, not assumed either way** — if
   it's stale, its richer shape (contact info, paperwork checklist,
   full timeline) may still be *useful design input* even though the
   file itself shouldn't be treated as current.

4. **"Dealer Trade" and "Trade-In" are unrelated concepts sharing
   "trade" in the name.** A Dealer Trade moves an existing inventory
   vehicle between two of Mark Auto Group's own stores. A Trade-In is
   a customer's vehicle entering inventory for the first time. Nothing
   in the frontend or backend vocabulary currently prevents these from
   being confused in code, docs, or an API surface — recommend the API
   and any new documentation always use the full two-word terms
   (`dealer_trade`, `trade_in`), never abbreviate either to "trade."

5. **Customer Delivery is unscoped in every backend document.**
   `PRODUCT.md`'s roadmap has no phase that names it. The frontend
   bundling it with Dealer Trades under one page is a frontend
   authoring decision, not a product decision — treating it as
   automatically Phase 4 scope because it's on the same page as Dealer
   Trades would be exactly the kind of silent scope expansion
   `PRODUCT_BACKLOG.md`'s own governance model exists to prevent.
   **Resolution:** explicit product-owner scoping call, per Section 6.

6. **Stale docstrings across every file in `models/`.** Every dataclass
   (`Vehicle`, `Task`, `Employee`, `Dealership`, `Recommendation`,
   `Event`, `Beacon`, `SyncRun`, `TaskExecutionEvent`) is headed
   `"PHASE 2 SCAFFOLDING -- not yet used"` (`SyncRun`'s and `TaskExecutionEvent`'s
   have been partially updated; the rest have not). This was accurate
   when Phase 2 began. It is no longer accurate: Phase 2 is complete,
   and every table these dataclasses describe is live, populated, and
   covered by 211 passing tests — but the actual read/write code path
   is raw SQL through `database/repository.py`'s dict-shaped rows, not
   these dataclasses. Per `ARCHITECTURE.md`'s and `DATA_MODEL.md`'s own
   convention ("if a docstring and this document ever disagree, fix
   the docstring"), these headers should be corrected — not because
   anything is broken, but because a new contributor reading
   `models/vehicle.py` today would be actively misled about whether
   Phase 2 exists yet.

7. **`QuickLog.tsx` already answers questions `PRODUCT_BACKLOG.md`
   calls unresolved.** The backlog entry for "LotSync Companion / Quick
   Event Window" lists open questions: does it need its own API
   surface, does it reuse Event/Task as-is, does it require auth, does
   it work offline-first. `QuickLog.tsx` is a fully-built prototype of
   this exact concept, embedded directly in the main Lot Staff
   dashboard rather than as a standalone lightweight surface, and its
   UI copy ("queued for verification... Inventory Sync will confirm
   it") already assumes reuse of the Task-completion assertion pattern
   without a separate API surface. This doesn't mean the backlog entry
   is wrong to call these open — it means the mockup has already made
   several of these decisions informally, and whoever picks the
   backlog entry up should look at this component first rather than
   design from a blank slate. **Recommendation: this reconciliation
   surfaces the connection; resolving it is a product-owner call,**
   consistent with `PRODUCT_BACKLOG.md`'s own rule that promoting an
   entry out of the backlog is a deliberate, explicit decision.

8. **Zero API integration surface anywhere in the frontend.** Every
   action button that looks like it does something (Accept, Assign,
   Cancel, Approve, Start, Complete...) is presently local component
   state with no backend call — and in a substantial number of cases
   (noted per-file throughout this reconciliation), no handler wired
   at all, just a styled button. Phase 3 is not "add a fetch call
   where one implicitly exists" — every single action in Section 4
   needs its behavior specified, not just its endpoint.

9. **No shared frontend type definitions.** Every one of the 19 files
   read declares its own local interface for Vehicle, Task, Dealer
   Trade, etc., with overlapping but non-identical field names and
   shapes (e.g., vehicle identity is `stock` in some files, `stockNumber`
   nowhere, `vehicleStock` in `Activity.tsx`). An API contract designed
   by generalizing from "the frontend's shape" needs to pick one
   canonical shape deliberately — there isn't a single existing shape
   to extract.

10. **`VehiclesList.tsx` already names its own expected evolution.** A
    code comment states outright: *"Future: filters will be generated
    from backend operational state... Future additions:
    'verification-needed' | 'outstanding-tasks' | 'operational-insights'
    | 'long-inventory' | 'recommendations'."* These five terms map
    directly onto existing backend concepts (TaskExecutionEvent
    contradiction states, `Task.commitment_standing='outstanding'`,
    Recommendation, aging thresholds, Recommendation again). This is
    the single clearest piece of evidence in the whole frontend that
    its own authors anticipated exactly the direction this
    reconciliation recommends — worth treating as a low-risk, high-
    confidence starting point rather than a risk in itself.

---

## 9. Documentation Recommendations

- **`API_CONTRACTS.md` (new).** Needed before frontend integration
  starts, precisely because no canonical shape exists to extract from
  the frontend today (Risk #9) — this document should *be* the
  canonical shape, informed by every field observed in Sections 1–4 but
  not bound to reproduce any single file's inconsistencies.
- **`AUTHENTICATION.md` (new).** Phase 3's named gate. Needs to resolve
  the 8 frontend roles into real accounts, and address whether an
  employee can legitimately hold more than one role (the mockup's
  `RoleSwitcher` implies one role at a time; real staff likely don't
  work that way).
- **`PERMISSIONS.md` (new, or a section of `AUTHENTICATION.md`).**
  Role-gated behavior already exists informally across at least three
  files (`Requests.tsx`, `TradeIns.tsx`, `Transportation.tsx`) with
  different per-role rules each time — this should be centralized
  before Phase 3 API design, not re-derived per endpoint.
- **`DOMAIN_TRANSPORTATION.md` (new).** Covers Dealer Trade and
  Customer Delivery together, since the frontend already couples them
  — needed to resolve the canonical shape (Risk #3), the two-
  dealership Task question (`DATA_MODEL.md`'s existing gap), and
  Customer Delivery's scope (Risk #5).
- **`DOMAIN_TRADE_INS.md` (new).** Needed to resolve whether Trade-In
  becomes its own model or decomposes into PendingIdentity + Vehicle +
  Task (Section 6) — this is exactly the kind of design question that
  benefits from being written down and reviewed rather than decided in
  passing during implementation.
- **`DOMAIN_REQUESTS.md` (new), or fold into a revised `DATA_MODEL.md`
  Recommendation section.** Needed to resolve whether Request extends
  Recommendation or becomes independent (Section 6).
- **`INTEGRATION_PLAN.md` (new) — this is Phase 3's implementation
  plan**, which `IMPLEMENTATION_PLAN.md` already promises will exist
  "when Phase 2 is actually, verifiably done" (true as of
  `PROJECT_STATUS.md`'s last update). This reconciliation document
  should feed directly into that plan's scoping, the same way the
  original Figma Make mockup review fed into `DATA_MODEL.md`'s Sprint-4-
  era decisions.
- **`DATA_MODEL.md` (update, once the above decisions are made).**
  Add the Employee/Dealership migrations once built; add whatever
  Request/Trade-In/Dealer-Trade/Customer-Delivery modeling the domain
  reviews conclude; fix the stale `models/*.py` docstring convention
  note (Risk #6) the next time this document is touched for a real
  reason.
- **`PRODUCT.md` (update — a real trigger, not a drive-by edit).**
  Two gaps this reconciliation surfaces meet `PRODUCT.md`'s own
  governance bar (a genuine scope question, not a drafting nit): (a)
  Phase 4's "Dealer Trades" name doesn't currently say whether it
  includes Trade-Ins or Customer Deliveries — both share a page/name
  with Dealer Trades in the mockup, and (b) Phase 6 remains
  undifferentiated from Phase 4, a gap `PRODUCT.md`'s own "Open
  questions" section already flagged before this reconciliation
  started. Recommend the product owner resolve both when this document
  is next revisited, rather than letting the frontend's page-bundling
  choices silently answer them.
- **`PRODUCT_BACKLOG.md` (update).** Add a pointer from the Companion/
  Quick Event Window entry to `QuickLog.tsx`'s existing implementation
  (Risk #7) — the entry's own stated revisit trigger ("when Phase 3
  planning actually begins") is now true.

---

## Summary for whoever picks this up next

Phase 2 delivered exactly what `IMPLEMENTATION_PLAN.md` promised: a
persistent, tested, internally-consistent operational platform. The
frontend mockup independently converged on much of the same
architecture — the manual-assertion/corroboration pattern, task-type
grouping, dismiss-path recommendations, Vehicle as the aggregation
point — which is real, if partial, validation of Phase 2's design
(the same kind of validation `ARCHITECTURE.md`'s original "Frontend
discovery" review already noted, now confirmed by a second, more
complete pass).

What's actually missing before Phase 3 can start cleanly is not more
architecture — it's four decisions and one piece of missing schema:
build the Employee/Dealership migrations (mechanical, no design
question); correct the frontend's Task model before it becomes an API
contract (a known-solved problem, just not yet propagated to the UI);
and get explicit product-owner rulings on Requests, Trade-Ins, and
Transportation/Customer-Delivery (three genuine, unresolved domain
questions this document deliberately does not answer on its own).
