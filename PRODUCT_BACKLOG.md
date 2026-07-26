# LotSync — Product Backlog (Unscheduled Ideas)

This is **not** a governed document. `VISION.md`, `PRODUCT.md`,
`ARCHITECTURE.md`, and `DATA_MODEL.md` require a genuine trigger
(architectural flaw, real-workflow contradiction, or an intentional
product-owner scope change) before they're touched. This file requires
none of that — it exists specifically so validated product feedback
and ideas can be preserved *before* they've been triaged into the
roadmap, without that act of writing them down being mistaken for a
commitment.

An entry here is not scheduled, not scoped, and not architected.
Promoting one — assigning it to a phase in `PRODUCT.md`'s roadmap, or
a slice in `IMPLEMENTATION_PLAN.md` — is a deliberate, later decision
the product owner makes explicitly. Only at that point do the relevant
governed documents get updated, through the normal process.

---

## LotSync Companion / Quick Event Window

**Status:** Unscheduled. Not assigned to any phase or sprint. No
implementation or architectural work is requested or implied by this
entry — it exists to preserve context for a future decision, nothing
more.

**Origin:** Surfaced while showing the LotSync mockup to two tower
managers. One observed that recording a quick operational update
shouldn't require navigating through the full application.

**The workflow problem:** Operational staff spend most of their day
working in Tekion, OEM portals, email, and other dealership software —
not in LotSync. If recording a manual event requires switching into
LotSync, finding the right vehicle, and opening a form, that friction
is enough that many real operational events may simply never get
recorded — not because staff don't care, but because the cost of
logging it exceeds the perceived value of logging it *right now*, in
the middle of something else.

**The proposed concept:** Not another dashboard. A small, focused
utility — a "LotSync Companion" or "Quick Event Window" — that lets
someone record an operational event while remaining in their current
workflow, then immediately return to it. Illustrative shape:

```
Working in Tekion (or another system)
  → Launch LotSync Companion
  → Record a quick event, minimal required information
  → Submit
  → Companion closes
  → Back to previous work
```

**Example use cases:**
- Dealer trade initiated
- Vehicle moved
- RecovR installed
- Customer hold placed
- Key returned
- Other manual operational assertions

**Why this aligns with the existing event-driven philosophy:**
`VISION.md`'s principle — "Manual input is an assertion, not an
override" — already establishes that a person logging something
updates LotSync right away *provisionally*, without needing to wait
for or override the authoritative system. The Companion doesn't
introduce a new kind of truth or change what a manual `Event` means;
it's simply a faster, lower-friction *mechanism* for creating the same
kind of assertion that already exists conceptually. The idea is
additive to that principle, not in tension with it.

**Why this is intentionally NOT part of the committed roadmap:**
`PRODUCT.md`'s Phase 3 is already scoped specifically as the web
dashboard (FastAPI/React) — the Companion is a *different* delivery
surface, not a variant of that one, and folding it into Phase 3 without
deliberate discussion would quietly expand what Phase 3 means. It also
raises real design questions nobody has answered yet — does it need its
own lightweight API surface, does it reuse the `Event`/`Task` models
as-is or need its own, does it require any auth given it might run
outside LotSync's normal access path, does it work offline-first given
it's meant to interrupt someone mid-task elsewhere. None of that is
resolved here on purpose; naming the questions is different from
answering them.

**When to revisit:** Not tied to a specific sprint — tied to a
milestone. The natural trigger point is when Phase 3 planning actually
begins (`IMPLEMENTATION_PLAN.md`: "Phase 3 gets its own implementation
plan when Phase 2 is actually, verifiably done"). At that point, the
underlying question this idea answers — how should operational staff
actually interact with LotSync day-to-day — is already on the table
for the dashboard; deciding then whether the Companion is a
complementary surface, an alternative, or deferred further is a much
better-informed conversation than deciding now, disconnected from any
concrete Phase 3 design work.
