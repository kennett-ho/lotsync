# LotSync — Design Philosophy

## What this document is, and isn't

This isn't a roadmap, an implementation plan, or a product
specification. `VISION.md` explains why LotSync exists to someone
who's never opened the codebase. `PRODUCT.md`, `ARCHITECTURE.md`, and
`DATA_MODEL.md` govern *what's decided*. This document is different in
kind: it explains how to reason about a design question you haven't
hit yet — the tests to apply when the existing documents don't already
have your answer.

**Governance, since this document isn't protected the same way the
other three are:** it holds itself to its own standard. A principle
gets added here only when a real scenario pressure-tests it and it
survives — not asserted because it sounds right. An existing principle
gets revised only when a real scenario demonstrates it's wrong, the
same evidentiary bar the principles themselves demand of everything
else in this system. A philosophy built on "don't rewrite history
without cause" would be self-defeating if this document could be
rewritten without cause.

**Origin:** these principles weren't designed in advance. They emerged
from a design review ahead of Phase 2 Sprint 3, working through what
should have been narrow, specific questions — what is an Event, should
`PendingIdentity` have its own history — and finding that each one
only resolved cleanly by stepping back to a more fundamental question
underneath it. The principles below are what was still standing after
that process, not what anyone proposed going in.

## The root principle

**History is append-only, and only claims about reality earn a place
in it.**

Everything else here is either a consequence of this or a refinement
of what's allowed to count as "a claim."

## Claims vs. interpretations

**The test:** would this still be true, or still have happened, in a
world where LotSync's business rules didn't exist?

A claim is a fact reported by a source that knows about it —
Tekion reporting a sale, Keyper reporting a key, a person reporting
that a tracker was installed. Delete every rule LotSync has ever
written and the claim is still true. An interpretation only exists
because LotSync applied a rule or threshold to facts the sources never
directly stated — an aging bucket, a priority level, a Recommendation,
a classification heuristic. Delete the rule and the interpretation
evaporates; nothing about the underlying vehicle changed.

Claims are eligible for history. Interpretations are not — they belong
to a different, not-yet-designed category of history (LotSync's
reasoning about a vehicle, not the vehicle's own story), and inventing
that category speculatively isn't warranted by anything built so far.

## Reconciliation is not authorship

When LotSync connects two independently-sourced claims — a Keyper
identifier resolving to a Tekion VIN, a `PendingIdentity` promoting to
a `Vehicle` — that connection is still a claim, not an interpretation,
*when the confidence is earned*. The connection would be true whether
or not LotSync ever made it; LotSync is discovering it, not inventing
it.

The discipline this demands: when confidence isn't earned, LotSync
says so rather than guessing. An ambiguous match stays ambiguous. A
`PendingIdentity` that seems obviously the same vehicle doesn't get to
borrow that appearance as evidence — "probably right" is still a
guess, and this system doesn't get credit for good odds. Reconciling
with honest uncertainty preserved is reconciliation. Reconciling by
picking the likely answer is authorship wearing reconciliation's
clothes.

## History is immutable — corroboration and contradiction are
relationships, not states

Once a claim exists, it's permanent. A later claim can agree with it
or disagree with it, but neither of those is an edit to the original
— they're new, independently timestamped claims that stand next to it.

This one is easy to violate by accident, because it's tempting to give
a claim a status field that updates as new evidence arrives — assign
"confirmed" once a source agrees, "contradicted" once it doesn't. That
mutates the claim to reflect something that wasn't known when the
claim was made, which is the same failure as backdating a `Vehicle`'s
Timeline to imply certainty that didn't exist at the time. Both are the
same mistake at different points in the model: collapsing "what was
claimed" into "what was later learned," instead of keeping them as two
honestly separate, separately dated facts.

## Current state is always a derived read, never stored history

If history can't be mutated, then anything that needs to reflect the
*current* answer to a question can't live in history itself — it has
to be computed fresh from the claims accumulated so far.

This isn't a new pattern invented for this discussion — it's already
how `Vehicle.recovr_status` works, and it's the correct shape for
"is this assertion currently believed" too: not a field stored on the
assertion, but a read over the relationship between it and whatever
claims came after it. It's also the answer to a question that looks
like it needs new machinery but doesn't: a source going silent about a
vehicle isn't a claim (nobody said anything — it fails the very first
test in this document), but "how long has it been silent" is a
derived read from the last real claim's timestamp, the same shape as
`days_out`, capable of driving a Recommendation without ever being
stored as history in its own right. The same shape applies going forward to
dashboards, task states, and anything else that needs to answer "what
do we currently believe" — compute it, don't store a second copy of
the answer that can drift from the history it's supposed to reflect.

## Operational entities tell stories; work items track progress

Not every concept in this system needs a Timeline. The distinguishing
question: does this thing accumulate a story over its life, or does it
just move toward a resolution?

A `Vehicle` has a story — what happened to it, in order, is the whole
point. A `PendingIdentity` doesn't; it's a work item that exists only
because something hasn't been resolved yet, and once it resolves,
nothing about its own internal history matters — only the outcome
does. The same is true of `Recommendation`. Work items get summary
lifecycle fields (when created, current status, how it resolved).
Operational entities get a Timeline. Giving a work item a Timeline
because the architecture makes it *possible* to give it one elegantly
— rather than because a real workflow demonstrated the need — is the
same mistake as building infrastructure ahead of demonstrated need,
just one layer deeper than that principle usually gets applied.

**Not every story needs its own storage.** `Beacon` is the clearest
test case: it has a real story (installed, paired, reassigned across
vehicles over years — duplicate-beacon detection genuinely needs this,
not hypothetically), so it's an operational entity, not a work item.
But its story doesn't require its own claim store. "RecovR paired:
Device #4821" is already a Vehicle-Timeline-eligible claim. A
`Beacon`'s history is a derived view — every claim, across every
vehicle, that references its `device_id` — not a second, separately
maintained history. The same goes for what looked like it might need
a multi-vehicle claim (a beacon moving from one vehicle to another, a
dealer trade): both decompose into independent single-vehicle claims
("unpaired from A," "paired to B"; a dealership field changing on one
vehicle) rather than requiring a claim to span two vehicles at all —
and the decomposed version is more honest, since the source data never
actually states "transferred," only two separate facts.

**Not yet fully resolved for every entity in the system** — this
distinction has now been tested against `Vehicle`, `PendingIdentity`,
`Recommendation`, and `Beacon`; nothing currently in scope remains
untested.

## Don't build ahead of a demonstrated workflow — including in the data model

`VISION.md`'s non-goals already say this about features and
infrastructure. It applies with the same force to the shape of the
data itself. The clearest example so far: a `PendingIdentity` Timeline
looked like the natural, elegant consequence of principles already
agreed on — and it was still wrong, because no actual workflow ever
needed it. Elegance is not evidence of need. The question to ask isn't
"does the architecture make this possible," it's "has a real scenario
demonstrated this is necessary" — and if the honest answer is no, the
simpler model is correct, even if a more general one seems more
satisfying to build.

## How to use this document

When a new design question doesn't have an obvious answer, in order:

1. **Is this a claim, or an interpretation?** (Would it still be true
   without LotSync's rules?)
2. **If it's a connection LotSync is making itself, is the confidence
   actually earned** — or is this authorship dressed up as
   reconciliation?
3. **Does resolving this require editing something that already
   happened, or only adding something new?** If it requires an edit,
   the model is probably wrong.
4. **Is what's needed a stored value, or a read computed from history?**
   If it needs to update as new information arrives, it's probably a
   derived read, not a stored field.
5. **Does this thing have a story, or does it have a state en route to
   a resolution?** That decides whether it needs a Timeline or a
   status.
6. **Has a real, demonstrated workflow asked for this — or does the
   architecture just make it possible to build?** If nobody's asked,
   don't build it yet.

If a question survives all six honestly and still doesn't resolve,
that's a sign this document is missing something — which is exactly
how everything already written here got found in the first place.

## Open gaps — honestly unresolved, not quietly assumed away

- **Assertion staleness, specifically its application.** The
  mechanism resolves cleanly (a derived read from a claim's own
  timestamp — identical in shape to `days_out` and to silence-duration
  below), but whether staleness should drive a threshold or a
  Recommendation *at all* isn't decided, because manual assertions
  aren't yet a scheduled capability (`PRODUCT_BACKLOG.md`). Designing
  the threshold now would be solving a problem no real workflow has
  asked about yet.
- **No plausibility constraint on assertion content.** Authority was
  resolved (any attributed source can assert; status doesn't depend on
  who), but nothing has asked whether the system should have any
  sanity boundary on what a claim can say, versus accepting anything
  at face value. Same reasoning as above — no demonstrated workflow to
  test this against yet, so it correctly stays open rather than being
  speculatively designed.

*(Beacon's category, multi-vehicle claims, and silence-vs-absence were
raised as open questions in the original review and have since been
resolved — see "Not every story needs its own storage" above and
"current state is always a derived read" for how each was settled.)*

## Ontology, Architecture, Invariants, and Reasoning Tools (Task review)

A second design review, ahead of Sprint 4 (Task generation), produced
four distinct kinds of knowledge that this document previously left
fused together. Separating them turned out to matter: they change at
different rates and answer different questions when someone's trying
to model something new.

### Ontology — what exists

Reality, Assertion, History, Interpretation,
Ratification, Commitment, Execution.

Notably: LotSync never observes Reality directly. It only ever
receives Assertions *about* reality, from a source (a system, a
person). This distinction matters specifically because "the system
never invents operational truth" (below) depends on it — there is no
path from Reality to LotSync that skips a source making a claim.

**"Recorded Claim" was tested as a separate ontology item and
collapsed back into Assertion.** The test: would another system
necessarily have this as a distinct concept? Only if something
depends on an Assertion sometimes *not* becoming part of History.
Nothing currently does — every Assertion that reaches LotSync is
recorded unconditionally, no filter sits between them. Keeping two
concepts with no demonstrated behavioral difference is exactly the
premature complexity this document argues against elsewhere. **The
named trigger for reintroducing the distinction:** if the still-open
"no plausibility constraint on assertion content" gap (see Open Gaps)
is ever resolved with a real rejection mechanism, Assertion and
Recorded Claim would need to split apart again, for a concrete reason
rather than a hypothetical one.

### Architecture — how those concepts relate

```
Reality → Assertion → History → [Interpretation] → Ratification → Commitment → Execution → Reality
```

Drawn as a single line, this overclaims. Two corrections, found during
final review rather than assumed correct on first pass:

- **Interpretation is optional, not mandatory.** A Recommendation
  converting into a Task passes through Interpretation. A standing
  policy adopted from direct organizational judgment — no system-
  generated Recommendation behind it — never does. Ratification can be
  informed by Interpretation or by unmediated human/organizational
  judgment; both are legitimate provenance.
- **The flow branches before Execution, not only after it.** A
  Ratification can be refused (no Commitment forms). A Commitment can
  terminate via Cancelled or Superseded *without ever reaching
  Execution*. The straight line is the common path, not the only one.

### Invariants — what must remain true regardless of implementation

- The system never invents operational truth. (Every claim traces to
  a source; LotSync's own reconciliation connects existing claims with
  earned confidence — never authors a new one. "Reconciliation is not
  authorship" is one instance of this, not a separate rule.)
- History is append-only. Corroboration and contradiction are
  relationships between claims, never mutations of one.
- Current state is always a cache over history, never a second,
  independently-maintained copy of the answer.
- Authority is independent from provenance — who may legitimately
  create or discharge a commitment is a different question from what
  informed that decision.
- Commitment standing is independent from execution — an outstanding
  commitment and its current work-in-progress state can both be true
  and different at the same instant.
- Reality is independent from organizational intent — the world
  changing and the organization changing its mind are two distinct
  mechanisms, each capable of ending a commitment on its own.
- A commitment may depend only on *explicit* assumptions — scoped to
  assumptions that differentiate whether this specific commitment
  still holds, not literally every conceivable precondition (a
  commitment doesn't need to restate that its vehicle still exists).

### Reasoning tools — how to approach a new modeling question

**Core (general-purpose):**
1. **Claims vs. Interpretations** — would this still be true if
   LotSync's business rules didn't exist?
2. **Story vs. Progress** — does this thing accumulate a narrative, or
   move toward one resolution?
3. **Orthogonal-Axis Test** — can two proposed readings be true and
   different at the same instant? (Not "does this feel complex" — a
   field can carry a lot of meaning without needing a split, per
   `Vehicle.tekion_status`, which correctly stayed unsplit.)
4. **Dependency Decomposition** — is this genuinely one problem, or
   several independently-triggered ones that got fused together by
   sharing a trigger?

**Historical (apply only once something has passed the tools above and
looks like a history candidate):**
5. **Timeline Admission** — assuming this is history, whose story does
   it belong to?
6. **Compression-Survival** — after removing every consecutive
   restatement that changes nothing, does anything remain that a
   current-state cache can't answer?

**Candidates — real findings, not yet earned permanent status:**
- *Individual correctness ≠ aggregate rule health.* Real, and likely
  true, but has appeared in exactly one topic so far. Held to the same
  bar as everything else here: demonstrated once isn't demonstrated
  enough yet.
- *Causal Path* ("did a discharging claim satisfy the commitment's own
  stated assumptions, or arrive by an independent path"). On the audit
  that produced this list, this looks more like an *application* of
  the explicit-assumptions invariant via Dependency Decomposition than
  an independent tool — checking discharge against properly-explicit
  assumptions already answers what Causal Path was reaching for. Kept
  here as a candidate rather than promoted or discarded, since the
  distinction it names was genuinely useful once, even if it isn't yet
  shown to be a repeatable, independent move.

**A note on evidence quality, not just content:** this list's ontology
was tested against a second hypothetical domain (Warranty Claims)
without needing to rename anything. That's promising, not proof —
the mapping was constructed in the same review, with full knowledge of
what it was being tested against, which is weaker evidence than an
independently-built system arriving at compatible structures on its
own. Treat the reuse claim as *not yet falsified*, not as *validated*.
