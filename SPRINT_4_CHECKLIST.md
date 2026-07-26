# Sprint 4 Implementation Checklist

Concrete work only. No open design questions belong on this list — if
something here turns out to need a design decision, that's a sign it
doesn't belong here yet.

## Required updates to `DATA_MODEL.md`

- [ ] Replace `Task.status` (`not_started`/`in_progress`/`complete`)
      with two fields: **commitment standing** (`outstanding` /
      `honored` / `moot` / `cancelled` / `superseded`) and
      **execution status** (derived — see schema section below).
- [ ] Add `Task.escalated_from_task_id` (nullable, FK to `Task`) —
      required for Moot-evaluation to walk a parent Task's status, not
      just the child's own condition.
- [ ] Add `Task.ratified_by` (`employee_id` or a standing-policy
      identifier) and `Task.ratification_type` (`human` /
      `standing_policy`) — Authority is now a modeled concept, not
      implicit in `assigned_employee_id`.
- [ ] Document the four terminal dispositions' discharge mechanisms
      directly in the `Task` section (Reality-discharged:
      Honored/Moot; Intent-discharged: Cancelled/Superseded) — this is
      where `DECISION_FRAMEWORK.md`'s findings become concrete schema
      notes, not just narrative.
- [ ] Add a `TaskExecutionEvent` (or equivalent) entity: append-only,
      `task_id`, `transition_type` (`started`/`blocked`/`resumed`/
      `completed`), `actor_employee_id`, `note` (free text, optional),
      `observed_at`.
- [ ] Note explicitly: completion is a manual assertion, not a direct
      status write — reference `VISION.md`'s existing assertion
      principle rather than re-deriving it.
- [ ] Add a line item under known gaps: dealership-transfer as an
      implicit assumption for install-type Tasks is unresolved — must
      be explicitly encoded or explicitly excluded before Sprint 4's
      discharge logic ships, not left to default silently.

## Required updates to `ARCHITECTURE.md`

- [ ] Tighten the "closes itself once [condition] resolves" language
      (frontend-discovery section) to distinguish Reality-discharge
      from Intent-discharge — currently true only for the former.
- [ ] Add a short pointer to `DECISION_FRAMEWORK.md`'s Ontology/
      Architecture/Invariants/Reasoning-Tools split for anyone
      modeling a new object after Task (Warranty Claims or otherwise)
      — the four-layer structure is the reusable part, worth surfacing
      from `ARCHITECTURE.md` directly, not just left in the framework
      doc for someone to find on their own.

## Database / schema changes

- [ ] Migration: split `Task.status` into `commitment_standing` +
      derived `execution_status` (cache column, updated by trigger or
      application logic — not independently writable).
- [ ] New table: task execution transitions (append-only, per schema
      note above). Index on `task_id`, `observed_at`.
- [ ] New column: `Task.escalated_from_task_id`, FK, nullable, indexed
      (Moot-evaluation will query it).
- [ ] New columns: `Task.ratified_by`, `Task.ratification_type`.
- [ ] Confirm `Recommendation.resulting_task_id` (already modeled)
      still correctly represents provenance independent of the new
      `ratified_by`/`ratification_type` authority fields — these
      are orthogonal per the audit, verify the migration doesn't
      conflate them.

## Backend implementation tasks

- [ ] Task-generation logic must call the same `rules/aging.py` /
      `rules/inventory.py` functions the CSV reports already use — per
      `IMPLEMENTATION_PLAN.md`'s Slice 5 constraint, unchanged by this
      review, worth restating here since it's easy to violate silently.
- [ ] Moot-evaluation: when checking whether a Task's assumptions still
      hold, must also check `escalated_from_task_id`'s status if
      present — a Task escalated from a now-moot parent needs its own
      independent evaluation, not automatic inheritance, per the
      "decompose, don't inherit" finding from the vehicle-sale case.
- [ ] Completion handling: a human marking a Task complete creates an
      assertion (writes to the execution-transition log with
      `transition_type=completed`), does not directly set
      `commitment_standing=honored`. `commitment_standing` becomes
      `honored` once corroborated by the relevant source's next sync —
      or the Task surfaces a contradiction if the source disagrees,
      per the existing manual-assertion pattern.
- [ ] Aggregate monitoring (deferred to product analytics, not
      per-Task logic): count how often a given `task_type` resolves as
      Moot at creation time or shortly after — a high rate signals the
      standing rule's trigger condition needs review, not something
      any individual Task's logic should react to.

## UI / API implications

*(Noted for whenever Phase 3 planning happens — not Sprint 4 work,
listed here only so it isn't lost.)*

- Task cards need to distinguish commitment standing from execution
  status visually — two independent signals, not one status pill.
- "Unassigned" needs to render as a real, valid state, not an error or
  empty state — per the original commitment-not-directive finding.
- A cancelled-then-later-corroborated Task (the Reality/Intent conflict
  case) needs a surfaced-discrepancy UI treatment — not an error state,
  not silently resolved either direction.

## Items intentionally deferred, not solved here

- Assertion staleness thresholds and content-plausibility rules — wait
  for manual assertions to become a scheduled capability.
- Dealer-trade two-dealership Task modeling — Phase 4, already
  documented as an open gap in `IMPLEMENTATION_PLAN.md`.
- Promoting Individual/Aggregate or Causal Path from Candidate status —
  wait for a second real demonstration, don't force it.
- Applying `DECISION_FRAMEWORK.md`'s ontology to a genuinely independent
  domain (Warranty Claims or otherwise) to test reuse for real, not
  hypothetically — valuable, but not Sprint 4 scope.
