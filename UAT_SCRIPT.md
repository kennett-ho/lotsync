# DealerDOH Human UAT — Moderator Script (Sprint 16, Rail M)

Practical in-person script. Method and privacy rules:
[`UAT_PLAN.md`](UAT_PLAN.md). Record observations into
[`UAT_FINDINGS.md`](UAT_FINDINGS.md) using its template.

Every fixture named below exists in the standing DEV dataset
(`SYNTHETIC_QA_MATRIX.md`); expected states are as of the QA
reference date 2026-07-21 and do not age.

---

## 0. Moderator setup (before the participant sits down)

1. Open `https://dealerdoh-dev.vercel.app` and load any page once —
   this warms the free-tier backend (first request after idle can
   take ~50 s; never let the participant experience the cold start
   and mistake it for the product).
2. Confirm the purple **SYNTHETIC DEV** banner is visible.
3. Sign the device into the correct QA account for the session role
   (accounts table in `UAT_PLAN.md` §4), land on the role's start
   page, then **sign out and back in fresh** so the participant
   sees a genuine post-login landing.
4. Note the session ID (`Manager-01`, `LotStaff-01`, …), date, and
   start time (needed later to correlate telemetry).
5. Keep this script and a notes page open on a second device —
   never on the participant's screen.

**During the session:** no navigating for them, no naming controls,
no confirming guesses ("mm-hm" is fine; "yes, that's the sync page"
is not). Let silence run. Note timestamps at hesitations.

**If truly blocked** (participant asks directly or gives up):
record where / what they expected / what they tried / how long /
what explanation resolved it — then give the minimum explanation
and continue.

---

## 1. Opening language (say roughly this)

> "We're testing DealerDOH, not you. Nothing you do here is wrong,
> and nothing you break matters — this is a practice system with
> made-up vehicles. I'm interested in what the product makes clear
> or confusing. Please think out loud as you use it — say what
> you're looking at, what you expect, what surprises you. I may
> stay quiet even if you seem stuck, because I want to see what the
> product communicates on its own. Questions are allowed, but I may
> answer them at the end instead of right away."

Do **not** explain what any screen is before or during testing.

---

## 2. Manager / Admin session (account: `manager@qa.dealerdoh.example`)

### M1 — Initial orientation (unassisted)

Participant signs in (or you hand over the freshly signed-in
session at the Overview landing).

Prompt:
> "You just signed in. Without clicking anything yet, tell me what
> you think this page is showing you and what you would look at
> first."

Observe: dashboard comprehension; what they call things
(tasks/recommendations/health/sync tiles); visual hierarchy — where
the eye goes first; the first click they *want* to make.

### M2 — Operational issue

Prompt:
> "Find a vehicle that appears to need operational attention and
> tell me what you think is happening with it."

Good candidates they may land on (do not steer): **QA1013** (key
out 7 days — two open tasks), **QA1025 / QA1026** (key out 25/30
days — the two Recommendations), **QA1092** (needs both RecovR and
MDD installs). Observe: do they use the task groups, the
Recommendations panel, or the vehicle list? Can they say *why* the
product flagged it, in their own words?

### M3 — Vehicle lookup

Prompt:
> "Find stock number **QA1013** — or if you prefer, VIN
> **1QATEST0000000013** — and tell me what DealerDOH knows about
> that vehicle."

Observe: where they try to search and with what (stock vs VIN);
whether they find Vehicle Detail; whether they can summarize its
state (key checked out ~7 days; needs a RecovR device but the key
being out blocks installation).

### M4 — Timeline / evidence

Stay on a vehicle with history — steer only if needed:
> "Open stock **QA1016** and walk me through what you think
> happened to this vehicle."

(QA1016's story: needed a RecovR device; the device was later
paired; the install task shows **Completed**.) Observe: do they
read the timeline as a chronology of observations? Do they connect
the pairing event to the completed task? Do they notice what is
recent vs. old?

### M5 — Recommendation

Point them at Recommendations only if they haven't been there:
> "What do you think DealerDOH is recommending here, and what would
> you do with that information?"

(Standing recommendations: **QA1025** and **QA1026** — "Key checked
out 25/29 days — Likely Sold, Verify to Remove from OMS.")
Observe carefully: is it read as **evidence for their judgment**
("we should check whether it actually sold") or mistaken for a
command/fact ("the system says remove it, so remove it")? The
product's own framing — "Evidence for human review — nothing
commits automatically" — should be doing this work.

### M6 — Sync health

Prompt:
> "How would you determine whether DealerDOH's inventory
> information is current right now?"

Observe: do they find Inventory Sync status/history (header badge,
Overview tile, or the Inventory Sync page)? Can they read "last
sync" and per-source status? Do they express appropriate trust
("data is as of the last report upload") rather than assuming
live/real-time data?

### M7 — Help

Prompt:
> "If you forgot how all this works next week, where would you go?"

Observe: Help discoverability; whether they find the onboarding
replay; whether Help's content matches what they wanted to know.

---

## 3. Lot Staff session (account: `lotstaff@qa.dealerdoh.example`)

### L1 — Initial orientation (unassisted)

Participant signs in; landing should be **Today's Work**.

Prompt:
> "You've just started your shift. Show me what you think you need
> to work on."

Observe: do the work groups read as a prioritized queue? What do
they call the items? Do the group names (checked-out keys, RecovR
installs, key-for-RecovR, MDD beacons) mean anything in their
language?

### L2 — Task comprehension

Prompt:
> "Pick one item and explain what you think DealerDOH wants you to
> do, and why it's asking."

Observe: task title/description comprehension; whether the *why*
(the underlying evidence) is visible enough; whether "investigate"
vs "install" reads as different kinds of work.

### L3 — Vehicle context

Prompt:
> "Show me the vehicle information you would look at before
> actually doing that work."

Observe: navigation from task → vehicle; whether Vehicle Detail
answers pre-work questions (where's the key, what state is the
vehicle in, history).

### L4 — Resolution

Prompt:
> "Assume you just finished that work out on the lot. Show me what
> you would do next in DealerDOH."

**Known designed behavior, not a bug:** there is **no manual
"mark complete" control.** Tasks are discharged by the next sync's
evidence (a paired device honors an install task; a sale moots it).
Observe *without explaining this*: what do they look for? How long
do they search for a done-button? What do they conclude? Their
expectation here is core Sprint 16 evidence either way. Explain the
evidence-driven lifecycle only afterward, and record how they react
to the explanation.

### L5 — No-longer-applicable task

Prompt:
> "Say you walk out and that vehicle's gone — sold and delivered
> yesterday. The task doesn't need doing. What would you do?"

Then, separately, show a discharged example: open stock **QA1042**
(its install task shows **"No Longer Needed"** because the vehicle
sold) and ask:
> "Tell me what you think happened here."

Observe: honored-vs-moot comprehension via the UI labels
("Completed" vs "No Longer Needed"); whether "No Longer Needed"
reads as an error or as reality-discharge; terminology reactions.

### L6 — Missing / stale evidence

Open stock **QA1014** (RecovR says no device; **no key record
exists at all** — DealerDOH deliberately creates no task, because
missing evidence is not "key is In").

Prompt:
> "What would you do if DealerDOH doesn't appear to have current
> information about a vehicle — like this one?"

Observe: do they notice information is *absent* vs. *zero*? Do
they check sync freshness? Do they invent certainty the product
doesn't claim?

### L7 — Vehicle search

Prompt:
> "Find stock **QA1023** — or VIN **1QATEST0000000023**."

Observe: search discovery, stock-vs-VIN behavior, time to find,
dead ends.

### L8 — Sold inventory

Prompt:
> "Find a vehicle that has already been sold."

(Sold examples: **QA1041**, **QA1042**, **QA1062**.) Observe: do
they find the Sold filter? Do they understand sold vehicles are
preserved with full history rather than deleted?

### L9 — Permission boundary

Prompt:
> "Where would you go to upload the day's inventory reports?"

**Correct product behavior:** Lot Staff has **no Inventory Sync
controls anywhere** — no nav entry, no upload surface; report
uploads are a manager function. Observe: does the UI communicate
the boundary honestly (nothing misleading, no dead controls, no
implied-but-broken path)? Does the participant know who *does* do
uploads? Any confusion here is a finding; functional access would
be a **P0 role-leakage** finding.

---

## 4. Sales Manager exploratory session (optional; account: `salesmanager@qa.dealerdoh.example`)

**Discovery only.** DealerDOH v1.1 has no Sales module; the
participant sees the honest shared experience. Never imply
otherwise; record everything under `Sales Operations Discovery`
(`UAT-S-###`), separate from v1.1 defects.

- **S1** — "What dealership questions can you answer from this
  screen?"
- **S2** — "Find a vehicle that might not be ready for a customer
  interaction. What makes you say that?" (Candidates they may
  reach: QA1013, QA1025/QA1026, QA1092.)
- **S3** — "If a salesperson told you they couldn't find a vehicle
  or its key, where would you expect to look?"
- **S4** — "What operational information would you want before
  telling a salesperson a vehicle is ready?"
- **S5** — "What would make this useful to you every day?"
- **S6** — "What information here would you ignore?"
- **S7** — "What would you call these concepts in dealership
  language?" (tasks, recommendations, evidence, sync, honored/no
  longer needed…)

If an S-scenario exposes a *current v1.1 usability defect*, record
it as a normal finding too.

---

## 5. Closing questions (every role)

Ask openly; no leading, no defending the product:

- "What was the most confusing part?"
- "What felt obvious?"
- "Was there anything you expected to be able to do but couldn't?"
- "Was there anything on screen you didn't trust or understand?"
- "What terminology felt unnatural?"
- "What would stop you from using this during a normal workday?"
- "What would make you choose this over the way you do the work
  today?"
- "What, if anything, felt unnecessary?"

Avoid "Did you like it?" and any question that contains its own
answer.

---

## 6. Immediately after each session

1. Finalize notes while fresh; convert observations into
   `UAT_FINDINGS.md` entries (one behavior per finding).
2. Record session end time.
3. Sign the QA account out.
4. Do not discuss findings with the next participant.
