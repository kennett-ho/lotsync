# LotSync — Why This Exists

## The problem

A dealership runs on five or six systems that were never designed to
talk to each other. Tekion knows what's in inventory. Keyper knows
where the keys are. MDD and RecovR know which vehicles have tracking
devices. RapidRecon knows what's still being reconditioned. Each one
is good at its own job. None of them, on their own, can answer the
question a lot attendant actually has: *what's really going on with
this car, right now?*

That question gets answered today by memory, phone calls, and someone
manually comparing spreadsheets — which works, until it doesn't. A key
sits in a drawer for years after the car it belongs to was sold. A
tracker never gets installed because the car arrived as a trade before
its VIN ever hit the DMS. A vehicle shows "sold" in one system and
"in stock" in another, and nobody notices until an audit finds it.
None of these are exotic failures — they're the ordinary, predictable
result of five systems that don't know about each other, run by people
who are busy doing their actual jobs, not reconciling data.

## Why it gets worse over time, not better

Every one of those systems is independently accurate *for what it
tracks*. The inconsistency isn't a bug in any of them — it's what
naturally happens when nothing is watching the space between them. The
longer a dealership runs this way, the more small gaps accumulate:
orphaned keys, untracked vehicles, sold cars nobody closed out. Nobody
did anything wrong. Nobody was watching the seams.

## What LotSync is — and isn't

LotSync does not replace Tekion, Keyper, MDD, RecovR, or RapidRecon.
Each stays the authoritative system of record for what it already
does best — Tekion owns inventory, Keyper owns keys, and so on.
LotSync becomes the **operational source of truth** by continuously
reconciling, validating, and coordinating what those systems say about
every vehicle — catching the contradictions, surfacing what's missing,
and turning that into work someone can actually act on.

## Principles

- **Vehicles are the center.** Everything organizes around one
  physical vehicle's complete story, not around any single system's
  report of it.
- **Reports are outputs, not the product.** A CSV, a dashboard card,
  a task list — these are different views into current vehicle state,
  not the thing LotSync is actually for.
- **Tasks drive work.** The goal was never more information. It's
  fewer things falling through the cracks — install this, verify that,
  go check on this car.
- **Events preserve history.** Nothing gets forgotten between syncs.
  If something's been flagged for a week, LotSync knows that, not just
  that it's flagged right now.
- **Recommendations help people decide — they don't decide for them.**
  LotSync surfaces patterns a person should look at. It doesn't act
  on its own judgment about what a vehicle's fate should be.

## What LotSync is explicitly not building

- Another DMS, or a replacement for any vendor system already in use.
- Vendor software replacement of any kind — the goal is coordination
  between systems, not consolidation into one.
- Infrastructure ahead of real need — multi-tenant SaaS, authentication
  systems, billing, or anything else with no current dealership asking
  for it. LotSync grows when a real operational problem shows up, not
  because a capability seemed worth having in advance.
