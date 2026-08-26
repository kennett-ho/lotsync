# LotSync — API Contracts

## 1. Purpose

**Why contracts exist before endpoints.** `FRONTEND_BACKEND_RECONCILIATION.md`
established that the frontend has zero existing API integration and no
shared type definitions of its own — 19 files, 19 independently-authored
`Vehicle`/`Task`/etc. shapes, none agreeing on field names. If Phase 3
starts by writing endpoints, each endpoint's response shape gets decided
locally, by whoever writes that endpoint, against whichever frontend
file they happened to be looking at — which is exactly how the frontend
arrived at its current fragmentation in the first place. This document
exists to make that decision once, centrally, before any endpoint code
exists, so every future endpoint is an implementation of an
already-agreed contract rather than a fresh negotiation.

**Why before endpoints, specifically.** An endpoint is a commitment to
a URL, a verb, a status-code convention — infrastructure decisions that
are comparatively cheap to change later. A data contract is a
commitment to *what a Task is*, from the frontend's point of view —
expensive to change later, because both a React component tree and
whatever consumes it end up encoding assumptions about the shape. Get
the shape right first; the transport is replaceable underneath it
without either side noticing.

**Relationship to `DATA_MODEL.md`.** `DATA_MODEL.md` is the canonical
description of what's stored and why — Vehicle, Task, Event, and the
rest, as backend concepts with a persistence shape and a lifecycle
history (Sprint 1 through Sprint 4's design reviews). This document
does not re-derive or re-justify any of that. Every DTO below is a
*projection* of a `DATA_MODEL.md` entity for a specific consumer (the
frontend), not a redefinition of the entity itself. Where a DTO's field
list differs from `DATA_MODEL.md`'s (an added computed field, an
omitted internal field), that difference is called out explicitly and
justified against a real frontend need identified in the
reconciliation — never assumed silently.

**Relationship to `FRONTEND_BACKEND_RECONCILIATION.md`.** That document
is this document's primary source of requirements. Section 1's Business
Object Inventory, Section 3's Screen Dependency Matrix, and Section 4's
User Action Inventory are what every DTO and write model below is
built from. Where the reconciliation named an unresolved domain
question (Requests, Trade-Ins, Transportation/Customer Delivery,
Employee/Dealership's missing migrations), that question is preserved
here as open, in Section 9 — this document does not quietly resolve
anything the reconciliation deliberately left open for a product-owner
call.

**The frontend/backend relationship this document assumes.** The
backend is the only party that knows what's true — every field in
every DTO below either comes directly from a persisted claim (`Event`),
a cached derivation of accumulated claims (`Vehicle.tekion_status`,
`Task.execution_status`), or a computed read over both (dashboard
aggregates). The frontend never originates truth; it displays what it's
given and collects what a person asserts, which the backend then treats
as a new claim, not an edit to an old one (`DECISION_FRAMEWORK.md`'s
"history is append-only" principle applies to every write model in
Section 5 without exception).

---

## 2. Design Philosophy

- **Backend owns truth; frontend renders state.** No DTO field is
  ever "corrected" by the frontend and sent back as if it always said
  that — every user action in Section 5 is either a new claim (an
  Event) or a request to discharge/convert/dismiss something that
  already exists via its own defined transition, never a raw field
  overwrite. This is `DATA_MODEL.md`'s "manual input is an assertion,
  not an override" principle applied at the contract level, not just
  the database level.
- **DTOs are not database tables.** A DTO may combine, flatten, or omit
  columns from one or more backend tables; it is defined by what a
  screen needs, not by what a migration created. Conversely, no DTO
  invents a fact the backend doesn't actually hold — where a frontend
  screen wants a field the backend has no source for (e.g. Vehicle's
  `photo` field), that gap is named, not silently fabricated into the
  contract as if it already existed.
- **Contracts stay stable even if implementation changes.** Whether
  `Task.execution_status` is computed by a database trigger, an
  application-level cache update, or something else internally is a
  backend implementation detail explicitly out of scope for this
  document (per `ARCHITECTURE.md`'s own note that `execution_status` is
  "a plain, application-managed cache column... NOT a database
  trigger" — a decision this document does not need to know about,
  much less restate). The contract only commits to: this field exists,
  this is what it means, this is when it changes.
- **Avoid exposing persistence details.** No DTO includes migration
  version numbers, internal row IDs that aren't also meaningful
  identifiers (e.g. `schema_migrations` never appears here), or SQL
  storage types (`TEXT` vs `INTEGER` distinctions collapse into
  "string" vs "number" — the wire format doesn't need to know SQLite's
  type affinity rules the way `database/repository.py`'s own comments
  do).
- **Naming convention — a real decision, made once, here.** Field names
  in every DTO below match the backend's existing field names verbatim
  (`vin`, `stock_number`, `commitment_standing`, `dealership_id`) rather
  than translating into a frontend convention. This is not a stylistic
  preference — it is the direct fix for the exact fragmentation the
  reconciliation observed: `stock` in some files, `stockNumber` nowhere,
  `vehicleStock` in `Activity.tsx`. Introducing a translation layer at
  the contract boundary would let that fragmentation continue on the
  frontend side while pretending it doesn't exist on the wire. One name
  per concept, matching the name `DATA_MODEL.md` already uses, is the
  whole fix.
- **Minimizing chatter is a contract-shape decision, not a caching
  optimization.** Where a screen needs a vehicle's `year`/`make`/
  `model`/`stock_number` alongside a list of Tasks, the Task-list
  response embeds that summary directly (see `VehicleSummaryDTO` in
  Section 3) rather than requiring the frontend to issue a follow-up
  lookup per row. This is decided at the DTO level so it can't be
  quietly undone by a future endpoint implementation choosing the
  chattier shape out of convenience.
- **Every DTO field is either read-only, write-only, or computed —
  never ambiguous.** A field the frontend can set and a field the
  frontend can only display are never the same field under the same
  name; where the two need to relate (e.g. a person asserting a Task
  is complete vs. the Task's actual `commitment_standing`), they are
  modeled as separate fields precisely because they are separate facts
  (Section 3's Task entry is the clearest example of why this matters).

---

## 3. Canonical DTOs

### Supporting type: `VehicleSummaryDTO`

Not one of the twelve primary DTOs, but referenced by several of them —
defined first because it exists purely to satisfy the "minimize
chatter" principle above.

- **Purpose:** a lightweight, embeddable projection of a Vehicle, for
  contexts that need to show *which* vehicle something concerns without
  paying for a full `VehicleDTO` round trip (a Task row, a
  Recommendation card, an Activity entry).
- **Fields:** `vin`, `stock_number`, `display_name`, `year`, `make`, `model`.
- **Read-only.** Never independently fetched or written — always
  embedded inside another DTO.
- **`display_name` (Phase 3, Sprint 5 addition):** the best available
  human-readable name for UI display — the one field a consumer should
  render for "this vehicle's name," not `year`/`make`/`model` joined
  client-side. Decoupled from which source or shape supplied it: today
  populated verbatim from Tekion's single "Year Make Model" export
  column (never parsed into `year`/`make`/`model` — see those fields'
  own note in `VehicleDTO` below for why not); a future structured
  source may populate it too, from whatever it actually knows, without
  this field's meaning changing.
- **Corrected during Phase 3, Sprint 2 implementation:** this section
  originally also listed `color`, sourced from frontend field
  observation without cross-checking it against `DATA_MODEL.md`'s
  actual Vehicle schema. The `vehicle` table has no `color` column, and
  no importer in `importers/` extracts one from any source today —
  there is nothing to serve. Removed rather than added speculatively;
  see `PHASE_3_SPRINT_2_REVIEW.md` for where this was caught. If a real
  need for vehicle color surfaces later, that's a schema change to
  propose deliberately, not a gap to paper over here.
- **When embedded inside `VehicleDetailDTO`'s nested `tasks`/
  `recommendations`/`timeline` collections, this field is omitted
  (`null`)** — redundant with the vehicle the detail view is already
  about, the same reasoning `ActivityDTO`'s own note below already
  states explicitly for the Timeline case, extended consistently to
  Task and Recommendation.

### VehicleDTO

- **Purpose:** the list/summary view of a Vehicle — one row in
  `VehiclesList`, one card in a kanban, one line in a report table.
  Per `PRODUCT.md`'s "Vehicles are the center" principle and
  `ARCHITECTURE.md`'s description of Vehicle as the eventual core
  object, this is the DTO every other DTO either embeds
  (`VehicleSummaryDTO`) or hangs off of (`VehicleDetailDTO`).
- **Ownership:** no single department — this is the cross-cutting
  object, per `PRODUCT.md`.
- **Required fields:** `vin` (identity — per `DATA_MODEL.md`, "never
  scoped by dealership," never null, never reassigned).
- **Optional fields (nullable in the backend, so nullable here):**
  `stock_number`, `display_name`, `year`, `make`, `model`, `new_or_used`,
  `current_dealership_id`, `tekion_status`, `keyper_status`,
  `mdd_status`, `recovr_status`, `inventory_state`.
- **`display_name` vs. `year`/`make`/`model`:** these are deliberately
  independent, not one derived from the other. `display_name` is
  populated from whatever raw, honest display text a source can supply
  (currently Tekion's "Year Make Model" column, copied verbatim);
  `year`/`make`/`model` stay reserved for a source that genuinely
  supplies them as separate, structured values (MDD/RecovR's own
  exports already have separate Year/Make/Model columns, not yet wired
  into persistence; a VIN decoder is a named future source). There is
  no reliable, general way to split Tekion's combined string into
  `make`/`model` without a canonical-make lookup table (a naive
  token-split silently misparses multi-word makes like "Land Rover"),
  so this project deliberately does not attempt it — see
  `migrations/0007_vehicle_display_name.sql`.
- **Nested objects:** none at this level — `VehicleDTO` is
  intentionally flat; aggregation happens in `VehicleDetailDTO`.
- **Relationships:** `current_dealership_id` references a
  `DealershipDTO` (see Section 9 — Dealership's real shape is an open
  question); everything else (Tasks, Recommendations, Events) is a
  *reverse* relationship, resolved by fetching those DTOs filtered by
  `vin`, never embedded directly in `VehicleDTO` itself (that's what
  `VehicleDetailDTO` is for — keeping the two separate is what lets the
  list screen stay cheap).
- **Read-only fields:** every field listed above. No frontend screen
  identified in the reconciliation edits a Vehicle's own fields
  directly — all Vehicle state changes happen as a side effect of a
  sync run or a Task/Event write, never a direct Vehicle PATCH. If a
  future screen needs one (e.g. correcting a data-entry error), that's
  a new write model to design deliberately, not an implicit capability
  of this DTO.
- **Write-only fields:** none.
- **Computed fields:** `open_task_count` — not a stored column; a count
  of Tasks for this `vin` with `commitment_standing = 'outstanding'`,
  exactly matching the semantics `queries/dashboard.py`'s
  `inventory_health_percentage()` already uses internally, exposed here
  per-vehicle instead of aggregated.
- **Known gap, not resolved here:** the frontend's `photo` field
  (vehicle image URL) has no backend source of truth anywhere in
  `DATA_MODEL.md`. Not added to this DTO — see Section 9.
- **Example payload:**
  ```
  {
    "vin": "1HGCM82633A004352",
    "stock_number": "A48291",
    "display_name": "2023 Honda Accord",
    "year": null,
    "make": null,
    "model": null,
    "new_or_used": "New",
    "current_dealership_id": "mark-kia",
    "tekion_status": "Stocked In",
    "keyper_status": "Out",
    "mdd_status": "not_paired",
    "recovr_status": "not_paired",
    "inventory_state": null,
    "open_task_count": 2
  }
  ```

### VehicleDetailDTO

- **Purpose:** the single-vehicle aggregate view — the literal target
  `ARCHITECTURE.md` names ("a vehicle detail page showing Tekion/
  Keyper/MDD/RecovR status together") and the DTO `VehicleDetail.tsx`
  needs directly. Distinct from `VehicleDTO` deliberately — see
  Section 4's chattiness discussion for why these are two DTOs, not
  one with optional expansion.
- **Ownership:** same as Vehicle.
- **Required fields:** everything `VehicleDTO` requires (this DTO is a
  superset, not a sibling — every field `VehicleDTO` has, this has,
  under the same name).
- **Nested objects:**
  - `tasks`: `TaskDTO[]`, filtered to this `vin`.
  - `recommendations`: `RecommendationDTO[]`, filtered to this `vin`.
  - `timeline`: `ActivityDTO[]`, filtered to this `vin`, newest first —
    this is the Vehicle's Timeline, per `DATA_MODEL.md`'s Event entry
    and `ARCHITECTURE.md`'s "Event needed a richer shape" note.
  - `connected_systems`: a per-source status projection (see
    `SyncRunDTO` below) scoped to sources relevant to this vehicle —
    not a filtered `SyncRun` list (a `SyncRun` is a whole-source
    pipeline execution, not vehicle-scoped), but the same
    `{status, started_at, completed_at}` shape
    `connected_systems_status()` already returns, presented per system
    for this one vehicle's context.
- **Relationships:** as `VehicleDTO`, plus the nested collections above.
- **Read-only fields:** all of them — this is a read view; every
  mutation implied by what's nested here (completing a Task, dismissing
  a Recommendation, logging an Event) is one of Section 5's write
  models, never a field write on this DTO.
- **Computed fields:** none beyond what its nested DTOs already compute.
- **Example payload:** omitted for length — composition of the
  examples given for `VehicleDTO`, `TaskDTO`, `RecommendationDTO`, and
  `ActivityDTO` below, plus a `connected_systems` map keyed by source
  name (see `SyncRunDTO`'s example for that shape).

### TaskDTO

- **Purpose:** one vehicle, one action — matches `DATA_MODEL.md`'s Task
  exactly, including its most consequential design decision.
- **Ownership:** `department` (Inventory / Controller / Lot Ops /
  Dealer Trades, per `DATA_MODEL.md`'s documented vocabulary).
- **Required fields:** `task_id`, `vin`, `task_type`,
  `commitment_standing`, `execution_status`, `created_at`.
- **Optional fields:** `dealership_id`, `department`, `priority`,
  `assigned_employee_id`, `ratified_by`, `ratification_type`,
  `escalated_from_task_id`, `reason`, `completed_at`.
- **Nested objects:** `vehicle` (`VehicleSummaryDTO`) — embedded so a
  Task list never needs a separate per-row Vehicle lookup, per the
  chattiness principle in Section 2.
- **Relationships:** `vin` → Vehicle; `assigned_employee_id` →
  Employee; `escalated_from_task_id` → another `TaskDTO` (self-
  referential, matching the backend's real foreign key here); a Task
  may trace back to a `RecommendationDTO` via that Recommendation's own
  `resulting_task_id` — the reference lives on Recommendation, not
  duplicated onto Task.
- **Read-only fields:** every field above, without exception. This is
  the single most important rule in this document to get right:
  **`commitment_standing` and `execution_status` are never
  directly writable by the frontend.** They change only as the result
  of the write actions in Section 5 (start/pause/complete/cancel/
  escalate), each of which the backend interprets and applies —
  exactly preserving the Pre-Sprint 4 design review's central finding
  that these are independent axes, neither derivable from nor
  overridable by the other. A frontend that could `PATCH
  {"commitment_standing": "honored"}` directly would silently
  reintroduce the single-status model Sprint 4 specifically tore apart.
- **Write-only fields:** none on this DTO — all writes happen through
  the named actions in Section 5, each with its own, narrower input
  shape.
- **Computed fields:** none — both status axes are already backend
  caches over history (`execution_status` over `TaskExecutionEvent`,
  `commitment_standing` over discharge calls); this DTO exposes them
  as-is rather than re-deriving anything.
- **Preserved from Sprint 4, stated plainly for anyone extending this
  contract later:** a Task's `commitment_standing` reaching a terminal
  value (`honored`/`moot`/`cancelled`/`superseded`) and its
  `execution_status` reaching `completed` are independent facts that
  can disagree (a human-asserted `completed` execution with
  `commitment_standing` still `outstanding` is a real, valid,
  surfaced-not-hidden state — see `TaskExecutionEventDTO` and the
  "Complete Task" write model in Section 5). **Do not collapse these
  two fields into one "status" field anywhere in the frontend** — this
  is the exact correction `FRONTEND_BACKEND_RECONCILIATION.md`
  identified as required before this contract could be finalized.
- **Example payload:**
  ```
  {
    "task_id": 4821,
    "vin": "1HGCM82633A004352",
    "vehicle": { "vin": "1HGCM82633A004352", "stock_number": "A48291",
                 "display_name": "2023 Honda Accord", "year": null, "make": null, "model": null },
    "dealership_id": "mark-kia",
    "task_type": "install_recovr_device",
    "department": "Inventory",
    "priority": "High",
    "commitment_standing": "outstanding",
    "execution_status": "in_progress",
    "assigned_employee_id": "emp-0142",
    "ratified_by": null,
    "ratification_type": null,
    "escalated_from_task_id": null,
    "reason": "Missing RecovR — 42 days untracked",
    "created_at": "2026-07-20T07:08:00",
    "completed_at": null
  }
  ```

### Supporting type: `TaskExecutionEventDTO`

Referenced by Task-related write models in Section 5; not one of the
twelve primary DTOs but necessary to state precisely, since it's the
mechanism behind `execution_status`.

- **Purpose:** one entry in a Task's append-only execution log — matches
  `models/task_execution_event.py` exactly.
- **Fields:** `task_execution_event_id`, `task_id`, `transition_type`
  (`started`/`blocked`/`resumed`/`completed`), `actor_employee_id`
  (nullable), `note` (nullable, free text), `observed_at`.
- **Read-only** from the frontend's perspective once written — created
  only via the write models in Section 5, never edited or deleted
  (append-only, per `DECISION_FRAMEWORK.md`).

### RecommendationDTO

- **Purpose:** a system-surfaced pattern needing human judgment,
  distinct from a Task per `DATA_MODEL.md`'s explicit reasoning (its
  own dismiss/convert lifecycle before ever becoming a commitment).
- **Ownership:** `rule_source` names which rule generated it.
- **Required fields:** `recommendation_id`, `vin`, `rule_source`,
  `status`, `created_at`.
- **Optional fields:** `severity`, `title`, `detail`,
  `resulting_task_id`, `resolved_at`.
- **Nested objects:** `vehicle` (`VehicleSummaryDTO`), same chattiness
  rationale as `TaskDTO`.
- **Relationships:** `vin` → Vehicle; `resulting_task_id` → `TaskDTO`,
  set only once, on conversion (never reassigned — per
  `DATA_MODEL.md`, a Recommendation converts at most once).
- **Read-only fields:** all of them. Status changes only via the
  Dismiss/Convert write models (Section 5) — never a direct `status`
  write, for the same reason Task's fields aren't directly writable.
- **Write-only fields:** none.
- **Computed fields:** none — `status` is already the backend's own
  field, not derived here.
- **Example payload:**
  ```
  {
    "recommendation_id": 991,
    "vin": "1HGCM82633A004352",
    "vehicle": { "vin": "1HGCM82633A004352", "stock_number": "A48291",
                 "display_name": "2023 Honda Accord", "year": null, "make": null, "model": null },
    "severity": "High",
    "title": "RecovR tracker missing — 42 days untracked",
    "detail": "No RecovR pairing detected since Vehicle first appeared in Tekion.",
    "rule_source": "recovr_missing",
    "status": "open",
    "resulting_task_id": null,
    "created_at": "2026-07-20T07:08:00",
    "resolved_at": null
  }
  ```

### ActivityDTO

- **Purpose:** one entry in a Vehicle's Timeline, an Employee's
  personal activity feed, or the global Activity Log — matches
  `DATA_MODEL.md`'s Event, including the same `summary`/`detail_fields`
  split `ARCHITECTURE.md` describes as necessary for the Timeline's
  narrative display.
- **Ownership:** `source` names the originating system, or `actor_employee_id`
  names the originating person.
- **Required fields:** `event_id`, `vin`, `event_type`, `source`,
  `observed_at`.
- **Optional fields:** `sync_run_id`, `actor_employee_id`,
  `dealership_id`, `event_time`, `summary`, `detail_fields`.
- **`event_time` vs. `observed_at` (Sprint 3.7 / "Event Fidelity"):**
  two deliberately independent fields, never one overloaded. `observed_at`
  is when LotSync's sync learned about this — always populated, the
  audit trail, unchanged by this addition. `event_time` is the
  source's own claimed timestamp for when it actually happened — the
  Timeline should render this when present, falling back to
  `observed_at` only when it's null. Nullable because most sources
  don't expose a per-observation timestamp with a confirmed meaning;
  see `DATA_MODEL.md`'s Event entry for exactly which `event_type`s
  populate it and why (e.g. Keyper's Checkout Date is trusted only for
  `Status=Out`, deliberately not inferred for `Status=In`).
- **Nested objects:** `vehicle` (`VehicleSummaryDTO`) — included
  specifically for the global Activity Log screen, which lists entries
  across many vehicles at once and needs to display which vehicle each
  one concerns without a per-row lookup; omitted (redundant) when this
  DTO appears already nested inside a `VehicleDetailDTO`'s `timeline`.
- **Relationships:** `vin` → Vehicle; `sync_run_id` → a `SyncRunDTO`
  (informational provenance only — per `DATA_MODEL.md`'s migration
  notes, this reference is intentionally not hard-enforced backend-side
  either); `actor_employee_id` → Employee, nullable (system-detected
  events have none, per `DATA_MODEL.md`).
- **Read-only fields:** all of them, always — this is the clearest
  case of "history is append-only" in the entire contract. There is no
  write model anywhere in this document that edits an existing
  `ActivityDTO`. The only write is "Log Event" (Section 5), which
  creates a new one.
- **Write-only fields:** none.
- **Computed fields:** none — `summary` is already produced and stored
  at write time (per `ARCHITECTURE.md`, this DTO does not reconstruct
  or reformat it).
- **`detail_fields` is intentionally untyped further here** — per
  `DATA_MODEL.md`'s own note ("unvalidated dict for now — accepted
  debt"), this contract does not invent a stronger schema for it than
  the backend itself currently enforces. Treat it as an open bag of
  structured data whose shape depends on `event_type`/`source`, not as
  a fixed set of named fields.
- **Example payload:**
  ```
  {
    "event_id": 58213,
    "vin": "1HGCM82633A004352",
    "vehicle": { "vin": "1HGCM82633A004352", "stock_number": "A48291",
                 "display_name": "2023 Honda Accord", "year": null, "make": null, "model": null },
    "event_type": "keys_checked_out",
    "source": "keyper",
    "sync_run_id": 204,
    "actor_employee_id": null,
    "dealership_id": "mark-kia",
    "observed_at": "2026-07-27T07:22:00",
    "event_time": "2026-07-27T01:08:00",
    "summary": "Keys checked out by Sales — Checked out to James Miller, 6hrs14min outstanding, typically <2hrs",
    "detail_fields": { "checked_out_to": "James Miller (Sales)", "duration_minutes": 374, "typical_minutes": 120 }
  }
  ```

### EmployeeDTO

- **Purpose:** the person doing or assigned the work — matches
  `DATA_MODEL.md`'s Employee, identified there as "foundational, not
  optional."
- **Ownership:** self (an Employee owns their own record).
- **Required fields:** `employee_id`, `name`.
- **Optional fields:** `role`, `department`, `dealership_id`, `status`.
- **Nested objects:** none.
- **Relationships:** `dealership_id` → Dealership (home/primary
  assignment, explicitly "not a hard constraint," per `models/employee.py`'s
  own docstring — real staff work across sister-store lines).
- **Read-only fields (from any screen other than the employee's own
  profile):** all of them.
- **Write-only fields:** none defined yet — see Section 9; whether
  `status` (Available/Busy/Break/etc.) is self-updatable by the
  employee or system-derived from their current Task assignments is an
  open question the reconciliation didn't resolve and this document
  doesn't invent an answer to.
- **Computed fields:** none.
- **Implementation status, stated plainly:** per
  `FRONTEND_BACKEND_RECONCILIATION.md`, **no database migration creates
  an `employee` table today** — every backend column that should
  reference one (`Task.assigned_employee_id`, `Event.actor_employee_id`)
  is presently free, unconstrained text. This DTO defines the shape
  both sides should agree to build against; it does not imply the
  backend already serves it. *(Correction — Sprint 15 audit,
  2026-08-20: migration `0006_employee_dealership.sql` has since
  created the `employee` table in both engines. It is **empty in
  every environment** — no code writes it, the reference columns
  remain unconstrained text in practice, and the DTO remains
  unserved. The sentence above was true when written and is kept for
  history; the table-existence fact is now governed by
  `PRIVACY_ARCHITECTURE.md` §2.1's inventory.)*
- **Example payload:**
  ```
  {
    "employee_id": "emp-0142",
    "name": "Marcus Torres",
    "role": "Lot Attendant",
    "department": "Lot Operations",
    "dealership_id": "mark-kia",
    "status": "Installing"
  }
  ```

### DealershipDTO

- **Purpose:** a location/business unit within Mark Auto Group — matches
  `DATA_MODEL.md`'s Dealership exactly, in its currently-documented
  (minimal) shape.
- **Ownership:** Mark Auto Group (the single deployment, per `PRODUCT.md`).
- **Required fields:** `dealership_id`, `name`.
- **Optional fields:** `brand`.
- **Nested objects:** none.
- **Relationships:** referenced by `Vehicle.current_dealership_id`,
  `Task.dealership_id`, `Employee.dealership_id`, `SyncRun.dealership_id`,
  `Event.dealership_id` — always as a mutable, current attribute, never
  as part of another object's identity (per `DATA_MODEL.md`'s "Tenant
  vs Dealership" section — VIN remains the vehicle's lifetime identity
  regardless of dealership).
- **Read-only fields:** all of them, for every screen identified in the
  reconciliation — no frontend action edits a Dealership's own record.
- **Write-only / Computed fields:** none.
- **Implementation status, stated plainly:** same gap as Employee — **no
  migration creates a `dealership` table today.** *(Correction —
  Sprint 15 audit, 2026-08-20: migration
  `0006_employee_dealership.sql` creates `dealership` too, and
  migration 0009 gave it `organization_id`; the DEV access model
  populates store rows (e.g. `qa-motors`) since Sprint 05, while
  production rows are created only at the migration's Release C
  prep. The DTO itself remains unserved by any endpoint.)*
- **Known gap, not resolved here:** every frontend screen that displays
  a Dealership in a Dealer Trade or Transportation context wants
  `city`, `state`, and sometimes `contact` — none of which exist in
  `DATA_MODEL.md`'s current Dealership shape. This DTO reflects only
  what's already governed; extending it is explicitly one of the open
  questions in Section 9, coupled to the Transportation domain review
  the reconciliation already called for.
- **Example payload:**
  ```
  {
    "dealership_id": "mark-kia",
    "name": "Mark Kia",
    "brand": "Kia"
  }
  ```

### SyncRunDTO

- **Purpose:** one execution of the reconciliation pipeline against one
  source — matches `DATA_MODEL.md`'s SyncRun and, in its aggregated
  form, is already the best-aligned object in the entire reconciliation
  (`queries/dashboard.py`'s `connected_systems_status()` already
  computes almost exactly this shape).
- **Ownership:** the sync pipeline itself.
- **Required fields:** `sync_run_id`, `source`, `started_at`, `status`.
- **Optional fields:** `dealership_id`, `completed_at`,
  `records_processed`.
- **Corrected during Phase 3, Sprint 4 implementation:** this section
  originally also listed `issues_found`/`tasks_generated` as optional
  fields. Nothing populates either column on the `sync_run` row itself —
  `sync/pipeline.py`'s `run_inventory_sync()` computes task/recommendation
  counts as summary-level fields on `SyncSummaryDTO` instead (see below),
  not per-`SyncRun` fields. Removed rather than served as
  always-`null`, the same "fix the stale reference, not the correct
  document" convention `VehicleSummaryDTO.color`'s Sprint 2 correction
  already established.
- **Implementation status:** implemented for the first time in Phase 3,
  Sprint 4 (`api/dtos.py`) — this section's shape existed here since
  before Sprint 2, but no route served it as its own DTO until the
  history endpoint below needed one.
- **Nested objects:** none.
- **Relationships:** referenced (informationally, not by hard
  constraint) from `ActivityDTO.sync_run_id`; grouped by `source` to
  produce the derived "Connected Systems" read model (see Section 4).
- **Read-only fields:** all of them — a `SyncRun` is a record of
  something that already happened; nothing on this DTO is ever edited
  by the frontend. (Whether a *new* SyncRun can be triggered from the
  frontend at all — "Run Sync Now" — is a write model with its own,
  much narrower input shape; see Section 5.)
- **Computed fields:** none on the row itself; see below for the
  derived, grouped read model this feeds.
- **Derived read model — Connected Systems status (not a separate
  top-level DTO, a specific read composed from `SyncRunDTO` rows):**
  one entry per source, reflecting that source's most recent `SyncRun`
  — `{source, status, started_at, completed_at, records_processed}`,
  exactly `connected_systems_status()`'s existing return shape. This is
  what `VehicleDetailDTO.connected_systems` and every dashboard's
  "Connected Systems" panel actually consume; a raw list of all
  historical `SyncRunDTO` rows is a different, separate read (sync run
  history), not this one.
- **Example payload (a single `SyncRunDTO` row):**
  ```
  {
    "sync_run_id": 204,
    "source": "recovr",
    "dealership_id": "mark-kia",
    "started_at": "2026-07-27T07:02:00",
    "completed_at": "2026-07-27T07:03:42",
    "records_processed": 1247,
    "status": "complete"
  }
  ```

### Observability surface (new, Sprint 11 — Rails F+G)

Transport-level additions every consumer may rely on (full design in
`OBSERVABILITY.md`):

- **`X-Request-ID` response header** — on every API response, a
  server-generated uuid4 hex. Client-supplied values are never the
  authority. The frontend `ApiError` retains it (`requestId`) as the
  safe support reference tying a failure to the backend's structured
  log records.
- **Unexpected-failure 500 shape** — `{"detail": {"code":
  "INTERNAL_ERROR", "message": <plain language>, "request_id": ...}}`
  (the Sprint 10 `SYNC_EXECUTION_FAILED` detail also gained
  `request_id`). Never a traceback.
- **`GET /health`** additionally reports `release` (deployed git SHA
  — non-secret; no hostnames/DSNs/provider config).
- **`GET /me`** (authenticated shape) additionally reports
  `auth_user_id` — the stable internal Supabase user UUID the
  frontend uses as its analytics identity (deliberately the internal
  id; email/display name never go to telemetry).

### SyncRunBatchDTO and SyncSummaryDTO (new, Phase 3 Sprint 4)

Not among this document's original twelve DTOs — added when
`POST /inventory-sync/run` (see Section 5) was actually built, per the
same discipline as every other addition here: a real, demonstrated need,
not speculative.

- **`SyncRunBatchDTO`** — `GET /inventory-sync/history`'s entry shape:
  `{started_at, overall_status, sources: SyncRunDTO[]}`. `started_at` is
  a *derived grouping key*, not a stored batch id — every `SyncRun` row
  one call to `run_inventory_sync()` creates shares one `started_at`
  value (via `sync_run()`'s new optional passthrough), so "which
  `SyncRun` rows belong to the same sync" is answerable without a new
  `DATA_MODEL.md`-governed `batch_id` column. `overall_status` is
  "worst status wins" across the batch's sources (`failed` >
  `in_progress` > `complete`).
- **`SyncSummaryDTO`** — `POST /inventory-sync/run`'s response shape:
  `{triggered_at, sync_runs: SyncRunDTO[], vehicles_processed,
  exceptions_found, tasks_generated, recommendations_generated}`.
  Deliberately carries no single top-level `sync_run_id` — `SyncRun` is
  real per-source granularity, so a fabricated singular id would
  misstate that; `triggered_at` (the shared batch key) plus the full
  `sync_runs` list (each with its own real `sync_run_id`) are what a
  future write-path caller would actually need. `vehicles_processed` is
  the count of distinct VINs seen across every uploaded source in this
  run — stated explicitly as an implementation decision, matching this
  document's own precedent for resolving undefined terms (e.g. Slice
  7's "inventory health").
- **Example (Connected Systems derived read, keyed by source):**
  ```
  {
    "tekion":     { "status": "complete", "started_at": "...", "completed_at": "...", "records_processed": 1247 },
    "keyper":     { "status": "complete", "started_at": "...", "completed_at": "...", "records_processed": 1189 },
    "recovr":     { "status": "complete", "started_at": "...", "completed_at": "...", "records_processed": 1162 },
    "mdd":        { "status": "complete", "started_at": "...", "completed_at": "...", "records_processed": 1200 },
    "rapidrecon": { "status": "complete", "started_at": "...", "completed_at": "...", "records_processed": 980 }
  }
  ```

### IngestionValidationDTO family (new, Sprint 10 — Rail D)

`POST /inventory-sync/validate`'s response, and the `validation`
payload inside `/run`'s structured `422`/`409` rejections. Shapes are
defined by `sync/ingestion.py`'s `ReportSetValidation.to_dict()`
(the source of truth); `api/dtos.py` pins them as pydantic models.

- **`IngestionValidationDTO`** — `{validated_at, fingerprint, status:
  "ready"|"needs_review"|"rejected", requires_acknowledgement,
  reports: ReportValidationDTO[]}`. `fingerprint` is derived from the
  uploaded bytes (per-file SHA-256, combined per-set) — it is what a
  subsequent `/run` must echo back when acknowledging warnings, so an
  acknowledgement can only ever refer to the exact files the server
  validated (see `INGESTION_ARCHITECTURE.md` §9).
- **`ReportValidationDTO`** — per slot: `{slot, slot_label, status,
  fingerprint, expected: ReportContractRefDTO, detected:
  ReportContractRefDTO | null, classification: {confidence, reasons},
  stats: {total_rows, valid_rows, invalid_rows, duplicate_rows,
  duplicate_identifiers}, baseline: {previous_rows, previous_at,
  change, change_pct} | null, issues: IngestionIssueDTO[]}`.
- **`IngestionIssueDTO`** — `{severity: "error"|"warning"|"info",
  code, message}`. Codes are stable machine identifiers
  (`WRONG_REPORT_TYPE`, `NO_DATA_ROWS`, `SUSPICIOUS_COUNT_DROP`, …
  — full vocabulary in `INGESTION_ARCHITECTURE.md` §5); messages are
  dealership language, never raw parser text.
- **Structured rejections:** `/run` rejects with
  `detail: {code: "REPORT_VALIDATION_FAILED" (422) |
  "WARNINGS_NOT_ACKNOWLEDGED" | "STALE_VALIDATION" (409),
  validation: IngestionValidationDTO}` so the frontend renders the
  full preview of WHY, never a flattened sentence.

### PendingIdentityDTO

- **Purpose:** an observation that couldn't be resolved to a known
  Vehicle's VIN at the time it was recorded — matches `DATA_MODEL.md`'s
  PendingIdentity exactly, including its deliberately narrow,
  binary-status shape.
- **Ownership:** `source` names the importer that produced it.
- **Required fields:** `pending_identity_id`, `source`, `raw_identifier`,
  `identifier_type`, `status`, `first_observed_at`, `last_observed_at`.
- **Optional fields:** `resolved_vin`, `resolved_at`.
- **Nested objects:** none — a `PendingIdentity` by definition doesn't
  yet resolve to a `Vehicle`, so there's nothing to embed until
  resolution (at which point `resolved_vin` can be used to fetch the
  resulting `VehicleDTO` separately, not embedded here).
- **Relationships:** `resolved_vin` → Vehicle, set only once, on
  resolution (never reassigned).
- **Read-only fields:** all of them. Resolution is a backend-internal
  state transition (per `DATA_MODEL.md`, triggered by a later sync
  recognizing a previously-unresolved identifier) — there is no
  frontend write model for resolution in this document, because no
  frontend screen in the reconciliation asks a person to manually
  resolve one.
- **Known gap, not resolved here:** the frontend's "Exception" concept
  (Controller and Inventory Sync screens) wants a multi-stage,
  assignable workflow (`Open → Under Review → Pending Approval →
  Resolved`) that this DTO's binary `pending`/`resolved` status
  cannot represent. This document does not invent the richer status
  values or an `assigned_employee_id` field to bolt onto
  `PendingIdentityDTO` — see Section 9.
- **Implementation status:** implemented for the first time in Phase 3,
  Sprint 4 (`api/dtos.py`, `queries/inventory_sync.py`'s
  `list_pending_identities()`) — serves the Inventory Sync page's
  Exceptions panel with these real fields, deliberately not the
  frontend's fabricated assignable-workflow shape (see the "known gap"
  note above, still open).
- **Example payload:**
  ```
  {
    "pending_identity_id": 1183,
    "source": "keyper",
    "raw_identifier": "K30707",
    "identifier_type": "tekion_auto_generated_stock_number",
    "status": "pending",
    "first_observed_at": "2026-07-10T06:00:00",
    "last_observed_at": "2026-07-27T06:00:00",
    "resolved_vin": null,
    "resolved_at": null
  }
  ```

### NotificationDTO (future — Phase 5, speculative)

- **Purpose:** per-employee opt-in/out for a notification category.
  **Not implemented on either side today.** `PRODUCT.md` explicitly
  defers all Notification design to Phase 5 ("not yet designed in any
  source document beyond being named"). This entry exists only because
  the reconciliation found concrete frontend input worth preserving
  (`Profile.tsx`'s 8-category preference list) — it is not a commitment
  to build this shape, and it is marked speculative throughout.
- **Ownership:** self (each employee configures their own preferences).
- **Speculative fields, sketched from `Profile.tsx`'s observed
  categories, not from any backend design:** `notification_type` (one
  of: `dealer_trade_assigned`, `recovr_tracker_verified`,
  `inventory_sync_finished`, `vehicle_not_found`,
  `keys_checked_out_long`, `task_overdue`, `new_request_assigned`,
  `morning_sync_complete`), `enabled` (bool).
- **Explicitly not decided here:** delivery mechanism (in-app, email,
  push), whether preferences are per-employee or per-role-default,
  whether any of these categories map to a real backend-detectable
  event yet (several plausibly do — `task_overdue`, `morning_sync_complete`
  — but that mapping is Phase 5 design work, not this document's).

### ProfileDTO

- **Purpose:** the current employee's own profile screen —
  `Profile.tsx`'s aggregate view of self.
- **Ownership:** self, exclusively — this DTO is never fetched for
  anyone other than the currently-authenticated employee (which itself
  depends on Phase 3 authentication existing — see Section 9).
- **Nested objects:** `employee` (`EmployeeDTO`, the editable subset of
  self — see below), `notification_preferences`
  (`NotificationDTO[]`, ⚠ Phase 5 speculative, per above).
- **Fields explicitly out of scope for this DTO:** appearance settings
  (theme/density) and session information (device, browser, IP,
  active-session count) observed in `Profile.tsx` are **not** included
  here. Theme/density are plausibly pure client-side preferences with
  no backend need at all; session information is inherently a Phase 3
  authentication concern this document doesn't design ahead of that
  work (see Section 9). Neither is silently added to `ProfileDTO` on
  the assumption they'll obviously need a backend field — that
  determination hasn't been made.
- **Read-only fields:** `employee.employee_id`, `employee.dealership_id`
  — identity and home assignment are not self-editable.
- **Write-only / editable fields:** `employee.name` (display name, if
  distinct from a legal/system name — not yet distinguished anywhere in
  `DATA_MODEL.md`, so this document doesn't invent that distinction
  either), `employee.role`, `employee.department` are plausible
  candidates for self-edit but more likely admin-managed — **not
  resolved here**, since it depends on the Phase 3 permissions design
  in Section 9.
- **Computed fields:** none.

### DashboardSummaryDTO

- **Purpose:** the common aggregate payload behind the Lot Manager and
  Controller dashboards — directly composed from
  `queries/dashboard.py`'s four already-built, already-tested functions.
  This is the single clearest case in the whole contract of "reuse
  existing backend models" being not just possible but nearly
  mechanical.
- **Ownership:** no single department — an aggregate view.
- **Nested / composed fields:**
  - `connected_systems`: the derived Connected-Systems read described
    under `SyncRunDTO` above.
  - `task_counts_by_department`: a map of department name (or
    `"Unassigned"`, per `queries/dashboard.py`'s own documented
    handling of untagged Tasks) to outstanding Task count — exactly
    `task_counts_by_department()`'s return shape.
  - `inventory_health`: `{healthy_vehicles, total_vehicles,
    health_percentage}` — exactly `inventory_health_percentage()`'s
    return shape, including its documented `null` case when there are
    no known vehicles.
  - `recent_activity`: `ActivityDTO[]`, limited (default 20, matching
    `recent_activity_feed()`'s default), each with `vehicle` embedded
    per the chattiness principle.
- **Read-only:** entirely — this is a read-only aggregate, no part of
  it is written to directly.
- **Known limitation, stated plainly:** this DTO does not cover the
  Tower Manager dashboard, which per the reconciliation's Screen
  Dependency Matrix depends primarily on Dealer Trade, Incoming
  Vehicle, and Vehicle Movement — three Frontend Only concepts this
  document does not define (see Section 9). `DashboardSummaryDTO` is
  the Lot Manager/Controller dashboards' payload, not a universal
  one-size-fits-all dashboard DTO.

---

## 4. Read Models

For each screen: primary DTOs, derived/aggregated values, and fields
that should never be requested separately (the chattiness question).

**Lot Staff Dashboard** — Primary: `TaskDTO[]` (filtered to
`assigned_employee_id = self` and department-relevant unassigned Tasks),
`DashboardSummaryDTO.connected_systems`, `RecommendationDTO[]`
("Operational Insights" equivalents scoped to vehicles the employee is
actively working). Derived: none beyond what the DTOs already compute.
Never fetch separately: a Task's vehicle summary — always embedded, per
`TaskDTO.vehicle`.

**Vehicle List** — Primary: `VehicleDTO[]`, paginated/filtered
server-side (search, status filters). Derived: `open_task_count`
(already computed on the DTO, not a separate call). Never fetch
separately: nothing further needed per row — this is the one screen
`VehicleDTO`'s deliberately flat shape is optimized for.

**Vehicle Detail** — Primary: a single `VehicleDetailDTO`. This is the
canonical example of "fields that should never be requested
separately" — Tasks, Recommendations, Timeline, and Connected Systems
for one vehicle are one fetch, not four, precisely because this screen
is `ARCHITECTURE.md`'s named target for showing "Tekion/Keyper/MDD/
RecovR status together" without the user (or the frontend code)
needing to cross-reference separate per-source screens.

**Inventory Sync** — Primary: the Connected-Systems derived read
(`SyncRunDTO`-based), `PendingIdentityDTO[]`/Exception-equivalent list
(pending resolution of the Exception workflow gap, Section 9), a
sync-run history list (raw `SyncRunDTO[]`, not the derived per-source
view — this screen explicitly wants history, unlike the dashboards).
Derived: `tasks_generated`/`issues_found` per run, already on
`SyncRunDTO`.

**Activity** — Primary: `ActivityDTO[]`, global (not vehicle-scoped),
paginated, with `vehicle` embedded per row (this is the one screen
where `ActivityDTO.vehicle` is never omitted, since the whole point of
this screen is seeing activity *across* vehicles).

**Reports** — Primary: extensions of `DashboardSummaryDTO`'s
aggregation pattern — `task_counts_by_department` and
`inventory_health` already cover 2 of 7 tabs; the remaining tabs
(Vehicle Movement, Dealer Trades, Request Volume) depend on Frontend
Only concepts and are not defined by this contract yet (Section 9).
Derived: every stat-card and chart value in this screen is a
server-side aggregate — this document does not recommend the frontend
compute any of them client-side from raw lists, since that would
duplicate exactly the aggregation logic `queries/dashboard.py`'s own
functions exist to centralize.

**Tower Dashboard** — Primary: none of the twelve canonical DTOs cover
this screen's core content (Dealer Trade, Incoming Vehicle, Vehicle
Movement are all Frontend Only per Section 2 of the reconciliation).
`EmployeeDTO[]` (staffing) is the one part of this screen this contract
already covers. The rest is explicitly deferred to Section 9 and the
Transportation domain review the reconciliation already called for.

**Lot Manager Dashboard** — Primary: `DashboardSummaryDTO` in full —
this is the dashboard that `DashboardSummaryDTO` was named for, since
its four panels map onto the four `queries/dashboard.py` functions
directly. Plus `EmployeeDTO[]` (team roster) and `TaskDTO[]` (the
operational task board itself, beyond the summary counts).

**Controller Dashboard** — Primary: `PendingIdentityDTO[]`/Exception-
equivalent list, `DashboardSummaryDTO.connected_systems`. The Audit
Queue panel depends on a Frontend Only concept (no backend Ratification
entity exists yet — Section 9).

---

## 5. Write Models

No HTTP verbs. Each action names its purpose, required inputs,
validation expectations, the object it changes, what activity logging
it implies, and what permission it should require.

### Start Task
- **Purpose:** record that work on a Task has begun.
- **Required inputs:** `task_id`, `actor_employee_id`.
- **Optional inputs:** `note`.
- **Validation expectations:** the Task must exist and currently have
  `commitment_standing = 'outstanding'` — starting a discharged Task is
  not a valid transition.
- **Resulting object:** a new `TaskExecutionEventDTO`
  (`transition_type = 'started'`); `Task.execution_status` becomes
  `in_progress` as a side effect (the cache update `insert_task_execution_event`
  already performs — this document doesn't change that mechanism, only
  names the action that triggers it).
- **Expected activity log:** yes — every execution transition is
  itself the log entry (`TaskExecutionEventDTO` is append-only), no
  separate `ActivityDTO` is implied unless the backend chooses to also
  mirror it as an `Event` (not required by anything in `DATA_MODEL.md`
  today).
- **Permission requirements:** the assignee, or a manager-level role
  acting on their behalf — not resolved further here (see Section 9,
  Permissions).

### Pause / Block Task
- Same shape as Start, with `transition_type = 'blocked'`, optionally
  `note` explaining why.

### Complete Task
- **Purpose:** a person asserting they finished the work — **an
  assertion, not a direct discharge**, per `VISION.md`'s "manual input
  is an assertion, not an override" and `SPRINT_4_CHECKLIST.md`'s
  explicit completion-handling note.
- **Required inputs:** `task_id`, `actor_employee_id`.
- **Optional inputs:** `note`.
- **Validation expectations:** same outstanding-Task guard as Start.
- **Resulting object:** a new `TaskExecutionEventDTO`
  (`transition_type = 'completed'`); `execution_status` becomes
  `completed`. **`commitment_standing` is deliberately NOT changed by
  this action.** It remains `outstanding` until the relevant source's
  next sync corroborates it (flips `commitment_standing` to `honored`
  via Reality-discharge) — or the Task surfaces a contradiction if the
  source disagrees. A Task sitting with `execution_status = 'completed'`
  and `commitment_standing = 'outstanding'` is not a bug state; it's
  the surfaced disagreement this system is designed to show rather
  than silently resolve either direction.
- **Expected activity log:** the `TaskExecutionEventDTO` itself.
- **Permission requirements:** the assignee.

### Cancel Task
- **Purpose:** Intent-discharge — the organization decided not to
  pursue this commitment, independent of what the world reports.
- **Required inputs:** `task_id`, `ratified_by`, `ratification_type`
  (always required here — Intent-discharge, unlike Reality-discharge,
  requires a legitimate authority acting, per `DECISION_FRAMEWORK.md`'s
  "authority is independent from provenance" invariant).
- **Validation expectations:** outstanding-Task guard, as above.
- **Resulting object:** `Task.commitment_standing` becomes `cancelled`;
  `completed_at` is set.
- **Expected activity log:** plausibly an `ActivityDTO` entry
  (`event_type` such as `task_cancelled`) — not strictly required by
  `DATA_MODEL.md` today, but consistent with keeping Vehicle Timelines
  complete; not decided definitively here.
- **Permission requirements:** manager-level (ratification implies
  authority beyond the assignee alone).

### Escalate Task
- **Purpose:** Intent-discharge (Superseded) plus creation of a
  replacement Task, per `database/repository.py`'s `escalate_task`.
- **Required inputs:** `task_id` (the parent), `new_task_type`,
  `ratified_by`, `ratification_type`.
- **Optional inputs:** `department`, `priority`, `reason` overrides for
  the new Task.
- **Resulting object:** the parent `TaskDTO`'s `commitment_standing`
  becomes `superseded`; a new `TaskDTO` is created with
  `escalated_from_task_id` pointing at the parent. Per
  `SPRINT_4_CHECKLIST.md`, the new Task does **not** inherit the
  parent's disposition automatically — it starts `outstanding` and is
  evaluated on its own condition.
- **Permission requirements:** manager-level.

### Convert Recommendation to Task
- **Purpose:** the Interpretation-to-Ratification-to-Commitment path —
  a human reviewing a Recommendation and deciding to act on it.
- **Required inputs:** `recommendation_id`, `task_type`, `ratified_by`
  (always required — converting is itself an act of ratification, per
  `database/repository.py`'s `convert_recommendation_to_task`).
- **Optional inputs:** `department`, `priority`, `reason` (defaults to
  the Recommendation's own `detail` if omitted).
- **Validation expectations:** the Recommendation must currently be
  `status = 'open'` — converting an already-resolved Recommendation is
  invalid, not a silent no-op.
- **Resulting object:** a new `TaskDTO`; the source `RecommendationDTO`'s
  `status` becomes `converted_to_task`, `resulting_task_id` set,
  `resolved_at` set.
- **Permission requirements:** manager-level (ratification).

### Dismiss Recommendation
- **Purpose:** a person deciding this Recommendation doesn't need
  action — the lighter-weight counterpart to conversion, per
  `PRODUCT.md`'s "every recommendation needs a real, visible dismiss
  path" principle.
- **Required inputs:** `recommendation_id`.
- **Validation expectations:** must currently be `status = 'open'`.
- **Resulting object:** `RecommendationDTO.status` becomes `dismissed`,
  `resolved_at` set.
- **Expected activity log:** none required — per `DATA_MODEL.md`,
  dismissing is deliberately lighter-weight than discharging a Task; no
  ratification is tracked here either.
- **Permission requirements:** any employee with visibility into the
  Recommendation — no ratification implied, unlike conversion.

### Log Event
- **Purpose:** a manual assertion about a vehicle — the write model
  behind `QuickLog.tsx`'s entire purpose, and the natural home for
  eventually resolving `PRODUCT_BACKLOG.md`'s Companion/Quick Event
  Window question (see Section 9).
- **Required inputs:** `vin`, `event_type`, `source` (for manually
  logged events, plausibly always `"lot"` per the vocabulary
  `DATA_MODEL.md` already lists — not firmly decided here),
  `actor_employee_id`, `summary`.
- **Optional inputs:** `detail_fields`, `dealership_id` (defaults to
  the Vehicle's current dealership if omitted — captured at write time
  per `DATA_MODEL.md`'s historical-accuracy requirement, not derived
  later).
- **Validation expectations:** `vin` must resolve to a known Vehicle —
  what happens when it doesn't (a genuinely new observation, the
  `PendingIdentity` case) is not addressed by this write model; no
  frontend screen in the reconciliation asks a person to manually
  create a `PendingIdentity`.
- **Resulting object:** a new `ActivityDTO` row. Always inserted, never
  updates an existing entry (append-only).
- **Expected activity log:** this action *is* the activity log entry.
- **Permission requirements:** any authenticated employee — logging an
  observation doesn't require special authority (it's a claim, not a
  discharge); per `QuickLog.tsx`'s own observed behavior, some
  event types (`recovr`, `mdd`, `tag`) are provisional pending the next
  Inventory Sync's corroboration — this document doesn't currently
  define a distinct backend flag for "provisional," since
  `DATA_MODEL.md` doesn't have one either; whether one is needed is
  folded into Section 9's Employee/manual-assertion open questions.

### Assign Employee
- **Purpose:** setting or changing `Task.assigned_employee_id` (or the
  equivalent field on a future Movement/Request/DealerTrade object).
- **Required inputs:** `task_id`, `employee_id`.
- **Validation expectations:** the Task should not already be
  discharged (assigning a cancelled Task is not a meaningful action,
  though whether it should be a hard validation error or a silent
  no-op is not decided here).
- **Resulting object:** `TaskDTO.assigned_employee_id` updated.
- **Permission requirements:** manager-level, per every frontend screen
  observed that gates "Assign"/"Reassign" to manager roles.

### Run Inventory Sync — implemented, Phase 3 Sprint 4

- **Purpose:** trigger a sync execution from real uploaded files, not a
  scheduled/manual `main.py` invocation. Built as `POST /inventory-sync/run`
  — see `PHASE_3_SPRINT_4_REVIEW.md` for the full account.
- **Required inputs:** at least one of six named multipart file fields
  (`tekion_unsold`, `tekion_sold`, `keyper`, `mdd`, `recovr`,
  `rapidrecon`) — all individually optional, matching this sprint's
  requirement that Tekion Unsold/Sold remain independent slots and that
  partial combinations are supported.
- **Resulting object:** `SyncSummaryDTO` (see above) — a new `SyncRunDTO`
  per *uploaded* source only; a source not included in the request
  produces no `SyncRun` row at all, the same "no data, no claim"
  treatment `sync/reconciler.py`'s persist functions already give an
  absent source.
- **Validation expectations, resolved (not left open as originally
  written):** every provided file is validated (required-column
  presence per its slot) **before** anything persists — a bad file in
  one slot fails the whole request with a specific, per-file reason
  (`422`), never a partial sync. Concurrent-trigger queuing/rejection
  was considered and deliberately not built — implemented as a single
  synchronous request/response, since a background job queue would be
  infrastructure ahead of this workload's real, small, low-concurrency
  scale (`PRODUCT.md`'s own standing rule; Slice 7 already validated
  sub-second reconciliation performance at 3,000 vehicles).
- **Permission requirements:** none implemented yet — this sprint
  explicitly excluded authentication/authorization. `POST /inventory-sync/run`
  is this project's first write route with no permission model behind
  it at all; see Section 9 and `PHASE_3_SPRINT_4_REVIEW.md`'s
  Recommendation #2. *(Resolved later: Sprint 05 gated it to
  admin/manager via `SYNC_RUN_ROLES`, inert under
  `AUTH_MODE=disabled`.)*
- **Sprint 10 update (Rail D — Inventory Ingestion Safety):** the
  per-slot required-column check above grew into the full ingestion
  boundary (`sync/ingestion.py` — classification, structural/row/
  duplicate validation, per-contract zero-row policy, comparable-
  baseline count sanity; `INGESTION_ARCHITECTURE.md` is canonical).
  `/run` recomputes ALL of it server-side on every request —
  previewing via `/validate` first is UX, not a prerequisite the
  server trusts. Two new optional form fields:
  `acknowledge_warnings` (bool) and `validation_fingerprint` (the
  `/validate` response's fingerprint). Validation ERRORs → `422
  {code: REPORT_VALIDATION_FAILED, validation}` with zero mutation of
  any kind (no SyncRun, no events/tasks, no report CSVs, no baseline
  row). WARNINGs without both a true acknowledgement AND a matching
  fingerprint → `409` (`WARNINGS_NOT_ACKNOWLEDGED` /
  `STALE_VALIDATION`), zero mutation. After a successful run, each
  accepted report's counts are recorded to `report_baseline`
  (`DATA_MODEL.md`) as the next comparable baseline. A runtime
  failure after validation returns `500 {code:
  SYNC_EXECUTION_FAILED, message}` in dealership language — never a
  stack trace; per-source transactional integrity per
  `database/repository.py`'s `sync_run()` contract.

### Validate Inventory Reports — implemented, Sprint 10 (Rail D)

- **Purpose:** the pre-sync preview — classify and validate the
  selected report files with **zero operational mutation**, so the
  operator answers "what am I about to tell DealerDOH is true?"
  before anything runs.
- **Route:** `POST /inventory-sync/validate` — same six optional
  multipart file fields as `/run`, same admin/manager role gate
  (the preview exposes the same operational surface).
- **Resulting object:** `IngestionValidationDTO` (above). Always
  `200` with the full per-report result — rejections included; it is
  a preview, not a gate (the gate is `/run`'s own revalidation).
- **Mutation contract:** no `SyncRun`, no Vehicle/Event/Task/
  Recommendation writes, no report CSVs, no `report_baseline` write
  (baselines are only *read* for comparison), and the uploaded bytes
  are deleted before the response returns — all API-test-pinned.

### Resolve Exception
- **Purpose:** named in the task brief, but **cannot be fully specified
  yet** — see `PendingIdentityDTO`'s "known gap" note above. The
  backend's only matching concept, `PendingIdentity`, has a binary
  `pending`/`resolved` status with resolution happening automatically
  (a later sync recognizing the identifier), not as a person-triggered
  action. The frontend's desired workflow (`Under Review`/`Pending
  Approval`, assignable to a person) has no backend mechanism to attach
  to today. **This write model is deliberately left incomplete — see
  Section 9.**

### Create Dealer Trade / Create Trade-In
- **Purpose:** named in the task brief, but **not specified here** —
  both depend on domain modeling decisions
  `FRONTEND_BACKEND_RECONCILIATION.md` explicitly deferred to a
  product-owner call (Section 6 of that document: whether Trade-In
  decomposes into existing `PendingIdentity`/`Vehicle`/`Task` machinery
  rather than becoming its own entity; whether Dealer Trade's
  two-dealership shape extends `Task` or needs a new model entirely).
  Writing a write model for either now would mean inventing the answer
  this document is supposed to preserve as open. See Section 9.

---

## 6. Shared Enumerations

Only values already supported by the governed architecture appear as
canonical here. Where the reconciliation found a conflicting frontend
enum, it's flagged, not silently reconciled.

**Task — Commitment Standing.** Canonical (`DATA_MODEL.md`):
`outstanding` / `honored` / `moot` / `cancelled` / `superseded`.

**Task — Execution Status.** Canonical (`DATA_MODEL.md`): `not_started`
/ `in_progress` / `blocked` / `completed`.
**Conflict flagged:** `Tasks.tsx` uses a single field combining both
axes (`outstanding`/`in-progress`/`waiting-verification`/`verified`/
`cancelled`/`superseded`) — not reusable as-is; see `TaskDTO`'s note
above. `waiting-verification`/`verified` don't correspond to backend
values at all — they appear to be the frontend's informal name for
"`execution_status = completed` but `commitment_standing` not yet
`honored`" (see "Complete Task" write model) — plausible, but not
confirmed, and not adopted into the canonical enum on that guess alone.

**Task Priority.** Canonical (`DATA_MODEL.md`): `Critical` / `High` /
`Medium` / `Low`. Frontend usage is case-inconsistent (`critical`/
`high`/... lowercase in some files) — cosmetic, not a modeling
conflict; the contract's canonical casing matches `DATA_MODEL.md`'s.

**Recommendation Severity.** Canonical (`DATA_MODEL.md`): same four
values as Task Priority. No conflict found.

**SyncRun Status.** Canonical (`DATA_MODEL.md`): `in_progress` /
`complete` / `delayed` / `failed`.
**Conflict flagged:** `LotStaff.tsx`'s simulated per-source upload flow
uses an `error` state with no backend equivalent (`failed` is the
closest match, but the frontend also has a distinct `idle` pre-upload
state that doesn't correspond to any real `SyncRun` row existing yet at
all — it's a pre-sync UI state, not a `SyncRun` status value).

**Employee Status.** **No canonical enum exists.** `DATA_MODEL.md`
gives only illustrative examples (`"Available"`, `"Installing"`,
`"Lunch"`) with no closed list. Frontend files disagree with each other
(`available|busy|dealer-trade|break|idle` in one file;
`Available|Driving|Dealer Trade|Installing|Lunch|Helping Sales` in
another). **Not resolved here** — establishing a closed vocabulary is
listed in Section 9.

**Vehicle Operational Status.** **No canonical enum exists.** The
backend has no single "status" field for a Vehicle at all — only the
four flat per-source status fields (`tekion_status`, `keyper_status`,
`mdd_status`, `recovr_status`) plus the currently-unpopulated
`inventory_state` placeholder. The frontend's various `VehicleStatus`
enums (`ready`/`needs-tracker`/`in-recon`/`keys-out`/`needs-attention`,
different again per file) are frontend-derived interpretations of the
four backend fields, not a value the backend stores directly anywhere.
**Flagged prominently** — `VehiclesList.tsx`'s own code comment
(quoted in full in `FRONTEND_BACKEND_RECONCILIATION.md`, Architectural
Risk #10) already anticipates this should become backend-computed
rather than frontend-invented; this contract does not yet define that
computed enum, since doing so would mean designing the `inventory_state`
state machine `ARCHITECTURE.md` calls "the eventual state-machine
label" — real design work, not a naming reconciliation.

**Sync Status** — see SyncRun Status above; same enumeration, listed
separately in the task brief but not a distinct concept.

**Notification Type.** ⚠ Speculative — see `NotificationDTO` above.
Not canonical; sketched only from `Profile.tsx`'s 8 observed categories.

**Department.** Canonical (`DATA_MODEL.md`'s `Task.department`
examples): `Inventory` / `Controller` / `Lot Ops` / `Dealer Trades` —
stated as *examples*, not declared as a closed list in `DATA_MODEL.md`.
**Conflict flagged:** the frontend's role-to-`navGroup` mapping uses a
different, overlapping vocabulary (`tower`/`sales`/`service`/`recon`/
`controller`/`lot`) for what's conceptually the same idea in some
places (department) and role-derived navigation grouping in others —
these are not obviously the same list and shouldn't be assumed to
unify without confirming that with whoever owns the frontend's role
model.

**Role.** **No backend enum exists at all** — `Employee.role` is a free
string (`DATA_MODEL.md`'s own examples: `"Lot Manager"`, `"Sales"`).
The frontend has a closed, 8-value `Role` type (`Lot Staff`/`Lot
Manager`/`Tower Manager`/`Controller`/`Sales Manager`/`Recon Manager`/
`Service Advisor`/`Detail Team`). This is real, concrete input toward a
canonical Role enum, but formalizing it is Phase 3 authentication work,
named as an open question in Section 9, not decided here.

---

## 7. Object Relationships

```
Vehicle
 ├── Tasks (1—*, by vin)
 ├── Recommendations (1—*, by vin)
 ├── Timeline / Activity (1—*, by vin)
 ├── Connected Systems status (derived, grouped SyncRun by source — not vehicle-owned, contextualized per vehicle)
 └── Current Dealership (*—1, mutable, NOT identity)

Task
 ├── Vehicle (*—1, required)
 ├── Assigned Employee (*—1, nullable — "Unassigned" is a valid state)
 ├── Escalated-from Task (*—0..1, self-referential)
 ├── TaskExecutionEvent log (1—*, append-only — backs execution_status)
 └── Recommendation (0..1—1, reverse reference only: a Recommendation may
     point at the Task it produced; a Task does not point back)

Recommendation
 ├── Vehicle (*—1, required)
 └── Resulting Task (produces 0..1, set once on conversion)

Event / Activity
 ├── Vehicle (*—1, required)
 ├── SyncRun (*—0..1, informational provenance, not hard-enforced)
 └── Actor Employee (*—0..1, nullable — system-detected events have none)

SyncRun
 └── Dealership (*—1, which dealership's export this run processed)

Employee
 └── Dealership (*—1, home/primary assignment, not a hard constraint)

PendingIdentity
 └── Vehicle (*—0..1, resolved_vin, set only upon resolution)
```

This mirrors `DATA_MODEL.md`'s own Relationships section deliberately —
this contract does not introduce a single new edge that document
doesn't already govern. Where the frontend implies additional edges
(Request → Vehicle, Dealer Trade → two Dealerships, Trade-In →
Vehicle), those are absent from this diagram on purpose — they belong
to Section 9's open questions, not to a relationship map claiming
they're already resolved.

---

## 8. Versioning Strategy

- **Backward compatibility is the default expectation.** A DTO gains
  fields; it does not silently repurpose one. This mirrors
  `DATA_MODEL.md`'s own amendment history exactly — every change that
  document records (`Event.event_id`, `PendingIdentity`,
  `SyncRun.status`'s `in_progress` value, `Task`'s
  commitment_standing/execution_status split, `Recommendation`'s
  `created_at`/`resolved_at`) was an addition triggered by a named,
  genuine gap, never a silent redefinition of an existing field's
  meaning. This contract should evolve the same way: a new optional
  field, added under a stated reason, not a reinterpretation of an old
  one.
- **Optional fields are the primary extension mechanism.** Any field
  not listed as "required" in Section 3 may be added to later without
  breaking an existing consumer, provided it's nullable/omittable — the
  same discipline `DATA_MODEL.md`'s own schema changes already follow
  (every addition documented there was nullable at introduction).
- **Deprecation, not deletion.** A field that stops being meaningful is
  marked deprecated (documented here, alongside its replacement) for at
  least one full Phase before removal — this document does not specify
  a numeric timeline (that's an implementation/release-process
  decision, out of scope), only the principle that removal is a
  distinct, later step from deprecation.
- **Breaking changes require an explicit version marker on the
  contract itself** (not on individual DTOs) — e.g. this document's own
  revision history should record the date and reason for any breaking
  change, the same way `DATA_MODEL.md` records the rationale for each
  of its five schema changes to date. A breaking change to `TaskDTO`
  (for instance) is a breaking change to this whole contract's version,
  not a private matter for that one DTO.
- **Frontend migration policy is not decided here** — the frontend
  currently has no build tooling, generated client, or shared type
  package pulling from any contract at all (per the reconciliation, no
  file imports from a shared `types.ts`). Whether Phase 3 introduces
  generated types from this document, a hand-maintained shared package,
  or something else is an implementation choice explicitly deferred —
  this document defines the contract's content, not the mechanism by
  which the frontend stays in sync with it.

---

## 9. Open Questions

Listed, not answered — each already surfaced in
`FRONTEND_BACKEND_RECONCILIATION.md` and preserved here rather than
resolved by this document.

1. **Transportation domain** (Dealer Trade + Customer Delivery). Three
   incompatible frontend shapes for Dealer Trade exist; Customer
   Delivery isn't named in `PRODUCT.md`'s roadmap at all. No `DealerTradeDTO`
   or `CustomerDeliveryDTO` is defined in Section 3 because doing so
   would require answering this first.
2. **Trade-In modeling.** Does it decompose into existing
   `PendingIdentityDTO` + `VehicleDTO` + `TaskDTO`, or does it need its
   own entity? No `TradeInDTO` is defined here for the same reason as
   above.
3. **Requests.** Does this extend `RecommendationDTO`'s lifecycle
   (human-sourced rather than rule-sourced), or is it a genuinely
   separate object? No `RequestDTO` is defined here.
4. **Customer Delivery scope.** Is it Phase 4 (bundled with Dealer
   Trades, as the frontend's own page structure implies) or its own,
   unscoped concern? Not decided by this document, or by `PRODUCT.md`
   as it currently stands.
5. **Permissions.** Which roles may perform which write models in
   Section 5 beyond the loose "manager-level" / "assignee" language
   used there? The frontend already role-gates several actions
   differently (`Requests.tsx`, `TradeIns.tsx`, `Transportation.tsx`)
   with no single centralized rule set — a real design question, not
   answered here.
6. **Authentication.** How the frontend's 8 named roles become real
   accounts; whether an employee can hold more than one role; what a
   session/token looks like. Entirely out of scope for this document,
   per `PRODUCT.md`'s own Phase 3 gate.
7. **Employee implementation.** `EmployeeDTO`'s shape is defined
   (Section 3), but no migration creates the underlying table yet —
   this is closer to "needs building" than "needs deciding" (per the
   reconciliation's own assessment), listed here mainly so it isn't
   lost.
8. **Dealership's real shape.** Does it gain `city`/`state`/`contact`
   fields to satisfy Transportation's needs, and if so, is that
   decided independently or only as part of the Transportation domain
   review (#1)? Not decided here — `DealershipDTO` reflects only
   today's governed, minimal shape.
9. **Exception / PendingIdentity workflow richness.** Does
   `PendingIdentityDTO` gain a multi-stage, assignable status beyond
   `pending`/`resolved`, or does the frontend's desired review workflow
   live in a new, separate entity? The "Resolve Exception" write model
   in Section 5 is left incomplete pending this.
10. **Vehicle Operational Status.** Should the four flat per-source
    status fields be joined by a real, backend-computed
    `inventory_state` enum (the placeholder `DATA_MODEL.md` already
    reserves for this), and if so, what are its values? Not designed
    here — this is state-machine design work, not a contract-naming
    question.
11. **Audit Queue / Ratification as a first-class object.** The
    frontend's Controller-facing approval workflow (Sold Vehicle
    Approval, Placeholder Stock Approval, etc.) has no backend
    equivalent. `DECISION_FRAMEWORK.md`'s own Ratification concept is
    the closest existing vocabulary — worth evaluating whether this
    becomes a first-class object built on that vocabulary, rather than
    a new one invented independently. Not decided here.
12. **Manual-assertion provisional state.** Should "Log Event" (Section
    5) carry an explicit provisional/pending-corroboration flag for
    event types like `recovr`/`mdd`/`tag` (as `QuickLog.tsx`'s own UI
    copy already implies), or does the existing pattern (a Task's
    `execution_status`/`commitment_standing` disagreement) already
    cover this without a new field on `Event`? Not decided here.
13. **`PRODUCT_BACKLOG.md`'s Companion/Quick Event Window.** Per
    `FRONTEND_BACKEND_RECONCILIATION.md`'s Architectural Risk #7,
    `QuickLog.tsx` already answers several of that backlog entry's
    stated open questions informally. Whether to formally promote the
    backlog entry now that Phase 3 planning has begun (its own named
    trigger) is a product-owner call, not something this contract
    resolves by defining a Companion-specific DTO.
