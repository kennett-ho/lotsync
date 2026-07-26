# Pre-Sprint 4 Design Review — Summary

**Scope:** What is a Task? Conducted the same way as the Sprint 3 Event
review — pressure-testing, not designing. No code, no governed-document
edits until this closing pass.

## Architectural decisions confirmed

- **A Task is an operational commitment**, not a directive and not a
  Recommendation with a richer status. Distinguished from both by kind,
  not degree: a claim describes what happened, an interpretation
  describes what LotSync believes deserves attention, a commitment
  records that the organization has committed to acting.
- **Authority is independent from provenance.** Who may legitimately
  create or discharge a commitment is a different question from what
  informed that decision — confirmed against the Recommendation-
  conversion case (human authority, system-generated provenance).
- **Commitment standing and execution are independent dimensions**,
  cache-over-log for execution — the same pattern `Vehicle.recovr_status`
  already used, now confirmed at a second object.
- **Reality and organizational intent are two coupled but distinct
  systems.** A commitment can be discharged by the world changing
  (Honored, Moot) or by the organization changing its own mind
  (Cancelled, Superseded) — confirmed against a genuine adversarial
  case (a cancelled task whose vehicle is later reported paired anyway)
  that showed these mechanisms don't actually conflict, they operate
  independently.
- **LotSync never invents operational truth.** Every terminal
  disposition traces to either a claim (Reality-discharged) or a
  legitimate authority acting directly (Intent-discharged) — no fifth
  mechanism, no case where the system originates a fact on its own.

## What changed from the original design

- **Task status can no longer be three values.** `not_started` /
  `in_progress` / `complete` cannot honestly represent a commitment
  discharged because it became moot, was cancelled, or was superseded
  — currently, closing such a Task would require either lying (marking
  it "complete") or leaving it open forever.
- **Execution needs to be a first-class, append-only log**, not a
  mutable status field. Tested directly against `PendingIdentity`'s
  history (which failed the same test and correctly has no log) —
  execution passed where `PendingIdentity` didn't, because consecutive
  transitions carry real information a terminal state alone destroys.
- **A Task needs an escalation-reference field.** Discovered while
  testing whether "vehicle sold, three open Tasks" decomposes cleanly
  — it does, but only if Moot-evaluation can walk a parent Task's
  status, which nothing in the current schema supports.
- **Task completion is a manual assertion**, not a direct status
  write — provisional until corroborated by the relevant source, same
  as any other manual claim, per the existing `VISION.md` principle
  ("fast doesn't mean final").

## Principles added to `DECISION_FRAMEWORK.md`

Four artifacts, kept separate rather than fused as before: **Ontology**
(what exists — collapsed to 7 items after Assertion/Recorded Claim
failed to show any demonstrated behavioral difference), **Architecture**
(the flow, corrected to show Interpretation as optional and real exit
branches before Execution — the original linear diagram overclaimed),
**Invariants** (8, each independently tested, one scoped down to avoid
absurd literal application), and **Reasoning Tools** (6 core/historical
tools, each validated against multiple real cases across this review
and the Sprint 3 review it built on).

## What remains intentionally unresolved

- **Candidates, not yet promoted:** Individual-correctness-vs-aggregate-
  rule-health (real, but demonstrated only once); Causal Path (likely
  reducible to the explicit-assumptions invariant, not yet shown
  independent).
- **Open gaps, correctly left open:** assertion staleness thresholds
  and content plausibility — both depend on manual assertions becoming
  a scheduled capability, which they aren't yet.
- **Dealership-transfer as an implicit assumption** for install-type
  Tasks — a real gap this review surfaced but didn't resolve; per the
  "explicit assumptions only" invariant, it needs to be encoded or
  explicitly excluded, not left implicit, before Sprint 4 implements
  discharge logic that would otherwise silently depend on it.

## Consistency audit — findings

Checked `VISION.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `DATA_MODEL.md`,
`DECISION_FRAMEWORK.md` against each other and against this review's
conclusions. No contradictions found. Two precision gaps, not
contradictions:

- `PRODUCT.md` and `ARCHITECTURE.md` both describe Task auto-resolution
  as "closes itself once [condition] resolves" — true for Reality-
  discharge, but doesn't capture Intent-discharge (Cancelled/Superseded
  close with no condition ever resolving) or the assertion-based path
  to Honored. Not false, incomplete — a wording tightening for whenever
  these documents are next touched for a real reason, not urgent enough
  to justify reopening them now.
- `DATA_MODEL.md`'s current Task section is known-incomplete (three-
  state status, no execution log, no escalation reference) but asserts
  nothing false — it simply predates this review. Folded into the
  Sprint 4 checklist rather than treated as a contradiction.

No stale references to the old `DESIGN_PHILOSOPHY.md` filename found
anywhere; the rename to `DECISION_FRAMEWORK.md` is consistent across
every document that cites it.

## Why we're confident enough to begin Sprint 4

Every conclusion in this review was reached by trying to break it, not
by proposing it and moving on — the audit alone reversed one confirmed
finding (individual/aggregate demoted for consistency), collapsed one
ontology item that hadn't earned its place, and caught two real
diagram/prose gaps rather than rubber-stamping the existing state. The
open items that remain are genuinely deferred, not merely undiscovered
— each has a named reason it isn't being solved now (no demonstrated
workflow yet) rather than being an unexamined gap. That's the same bar
Sprint 3 was held to before it shipped clean.

**The Pre-Sprint 4 Design Review is complete.**
