# DealerDOH Human UAT Plan — Sprint 16 (Rail M)

**Established:** Sprint 16 (2026-08-25). Governs the human User
Acceptance Testing of DealerDOH v1.1 against the register's Rail M
exit conditions (`V1_1_RELEASE_READINESS.md` §5.M). Companion
documents: [`UAT_SCRIPT.md`](UAT_SCRIPT.md) (the moderator script)
and [`UAT_FINDINGS.md`](UAT_FINDINGS.md) (the structured evidence
log). `UAT_EXIT_REPORT.md` is produced at sprint exit, never before
real sessions have occurred.

**The one rule above all others: findings are recorded observations
of real people, never fabricated, never inferred from automated
testing.** Automated QA (732 backend tests, axe audits, deployed
smokes) already exists; Rail M exists because none of that proves a
dealership employee can use the product uncoached.

---

## 1. Purpose and questions

Determine whether real dealership users can understand and operate
DealerDOH v1.1 in realistic role-specific workflows. The sessions
should answer, with evidence:

- Can users tell what DealerDOH is showing them?
- Can they find what they need without coaching?
- Do the role-aware surfaces make sense to people in those roles?
- Are Tasks and Recommendations understood as what they are —
  committed work vs. evidence for human judgment — and never as
  commands or facts?
- Do users correctly distinguish current, stale, and missing
  evidence?
- Are any controls misleading, dead, or ambiguous?
- Does product terminology match dealership language?
- Does the product reduce or introduce operational friction?
- Is v1.1 credible as a controlled beta for daily use?

## 2. Scope

**In scope:** DealerDOH v1.1 as deployed on DEV today — role-aware
navigation and landings, Overview dashboard, Today's Work, vehicle
list/search/Sold filter, Vehicle Detail and timeline, Tasks and the
evidence-driven task lifecycle, Recommendations, Inventory Sync
status/history (Manager only), Help and onboarding, work-order PDF.

**In-scope roles:**

- Manager / Admin (starting surface: Overview)
- Lot Staff (starting surface: Today's Work)
- Sales Manager — **exploratory discovery only**, if a suitable
  participant is available (see §8)

**Out of scope — do not test, do not promise, do not build:**

- any future Sales module or Sales workspace
- commercial billing, contracts, multi-rooftop functionality
- Sprint 17 vendor automation (automated Keyper acquisition)
- Sprint 18 release operations, production cutover, migration
- generic feature ideation sessions ("what should we add?")

## 3. Environment and data safety

- **Environment:** DEV only — `https://dealerdoh-dev.vercel.app`
  against `https://dealerdoh-api-dev.onrender.com`, Supabase Auth,
  deterministic synthetic dealership dataset
  (`SYNTHETIC_QA_MATRIX.md` is the source of truth: 34 `1QATEST…`
  vehicles, 18 tasks, 2 recommendations, QA reference date
  2026-07-21). The purple **SYNTHETIC DEV** banner must be visible
  in every session.
- **Production is never used.** No production URLs, no production
  credentials, no real dealership operational data on screen.
- No real customer information exists in DEV and none may be
  entered during sessions — participants must not type real
  customer names, phone numbers, or real VINs into anything.
- Sessions run against the deployed SHA recorded in the preflight
  (Appendix A). If DEV redeploys mid-UAT, re-verify the served SHA
  before the next session.
- First request after DEV idle can take 30–55 s (free-tier cold
  start). The moderator warms both services **before** the
  participant sits down so cold start is never mistaken for product
  slowness.

## 4. Participants and privacy

- Target: at least one representative **Manager/Admin** and one
  representative **Lot Staff** participant (Rail M minimum), plus a
  Sales Manager/GSM for the exploratory section if available.
- Participants are recorded **only** as `Manager-01`, `LotStaff-01`,
  `SalesManager-01`, … in every artifact. No names, phone numbers,
  personal email addresses, or HR information in the repository.
- Findings record **product behavior, not employee evaluation**.
  - GOOD: "LotStaff-01 interpreted 'No Longer Needed' as an error
    state and hesitated ~18 s."
  - BAD: any statement grading the person.
- Participants sign in with the **synthetic QA accounts** (below),
  never their personal accounts. Credentials are handled by the
  owner/moderator; they are never typed into notes or the repo.

**Accounts (Supabase `dealerdoh-dev`, memberships in the DEV DB):**

| Session role | Account | Landing |
|---|---|---|
| Manager/Admin | `manager@qa.dealerdoh.example` | Overview |
| Lot Staff | `lotstaff@qa.dealerdoh.example` | Today's Work |
| Sales Manager (exploratory) | `salesmanager@qa.dealerdoh.example` | shared/generic experience — no Sales workspace exists and none is implied |

## 5. Session format

Target **20–40 minutes** per participant.

1. **Introduction** (2–3 min) — the script's opening language,
   verbatim tone: we test the product, not the person.
2. **Unassisted orientation** (3–5 min) — first-impression protocol
   before any navigation is explained.
3. **Role-specific scenarios** — Manager M1–M7 or Lot Staff L1–L9
   (Sales Manager S1–S7 exploratory), in script order, skipping
   gracefully under time pressure (orientation and the first three
   scenarios take priority).
4. **Exploratory time** (3–5 min) — "use it as you would on a
   normal day," moderator silent.
5. **Closing questions** (5 min) — the script's non-leading set.
6. **Moderator notes finalized** immediately after the session,
   while memory is fresh; session start/end times recorded for
   telemetry correlation.

## 6. Moderation philosophy

Observation, not demonstration. Non-leading throughout.

- Never ask "Is this easy?", "You understand this, right?",
  "Wouldn't this help you?", or explain "this button is for X."
- Prefer: "What would you do next?", "What do you think this
  means?", "Where would you look for…?", "What do you expect this
  to do?", "Tell me what you think happened here.", "What
  information are you missing?", "What would you normally call this
  at the dealership?"
- **Record behavior before explanation.** Stay quiet through
  hesitation — silence is data.
- If a participant becomes genuinely blocked, record: where; what
  they expected; what they tried; roughly how long they were
  blocked; what explanation finally resolved it. Then continue.
- Do not optimize the sessions to make DealerDOH look good. A
  confused participant is the sprint working as intended.

## 7. Evidence structure

Every observation becomes a structured finding in
`UAT_FINDINGS.md` with an ID (`UAT-M-###` / `UAT-L-###` /
`UAT-S-###`), the fields defined there, and exactly one severity
category:

| Category | Meaning |
|---|---|
| **Blocking** | User cannot complete the intended workflow |
| **Severe friction** | Completes only with substantial confusion, coaching, or repeated attempts |
| **Moderate friction** | Succeeds, but terminology/layout/feedback causes avoidable hesitation |
| **Minor friction** | Small polish issue, low operational impact |
| **Positive validation** | Understands/completes naturally, no coaching |
| **Discovery** | Reveals a real-world workflow or need outside current v1.1 scope |
| **Not actionable** | Personal preference or one-off request that should not drive product change |

**Metrics** (directional evidence only — no statistical claims at
this sample size): task completion; completion without coaching;
time-to-first-correct-action where practical; navigation dead ends;
terminology misunderstandings; mistaken stale/missing-evidence
interpretations; moderator interventions; repeated-click failures;
role-permission confusion; participant confidence explaining what a
screen means; per-workflow completion rate.

## 8. Sales Manager discovery boundary

The Sales Manager section is **discovery for the future Sales
Operations expansion, not a test of features that do not exist**.
The moderator must not imply a Sales workspace exists. Findings from
S1–S7 are recorded under `Sales Operations Discovery` in
`UAT_FINDINGS.md` and feed the roadmap — they do **not** become
Sprint 16 implementation work unless they expose a current v1.1
usability defect or the owner explicitly changes sprint scope.

## 9. Fix policy during Sprint 16

Findings are triaged (Phase 4/5 of the sprint) before any code
changes:

- **P0** — data/security issue, role leakage, blocker,
  dangerous/misleading workflow → fix in-sprint.
- **P1** — severe recurring confusion, broken navigation, task
  lifecycle misunderstanding caused by the interface, stale/missing
  evidence misrepresented, runtime crash → fix in-sprint.
- **P2** — moderate friction, terminology mismatch, clear
  affordance issue → fix if contained; otherwise defer with
  rationale.
- **P3** — minor polish → usually defer.
- **Discovery** — roadmap, not Sprint 16 implementation.

Every fix references its finding ID, carries regression coverage
where practical, maintains SQLite/PostgreSQL compatibility,
preserves the security/privacy/accessibility posture, deploys to
DEV, and the affected scenario is re-tested — with a human for
human findings (automated green is not human-verified). No large
speculative redesigns inside Sprint 16.

## 10. Exit criteria (Rail M mapping)

Rail M (`V1_1_RELEASE_READINESS.md` §5.M) can only be dispositioned
from evidence:

1. Real sessions occurred: Manager/Admin AND Lot Staff represented.
2. Core scenarios attempted per role (M1–M7, L1–L9 or documented
   subset with rationale).
3. No unresolved Blocking finding.
4. Severe findings resolved or explicitly accepted/deferred by the
   owner with rationale.
5. Role boundaries held throughout (no leakage observed; L9 pass).
6. Findings traceable to fixes/deferrals; telemetry from the
   sessions reviewed against observations (§5.M exit 4).
7. `UAT_EXIT_REPORT.md` written; owner approves the disposition.

Vocabulary for the disposition: `Verified` /
`Conditionally Verified` / `Human Verification Incomplete` /
`Blocked` — chosen by evidence only. Sales Manager participation is
valuable discovery but is **not** a Rail M requirement.

---

## Appendix A — Preflight record (2026-08-25, PASSED)

Executed against DEV serving `dev` = `9ca0e61` (backend `/health`
release AND frontend bundle byte-verified; CI green on that head).
Re-verify the served SHA if DEV redeploys between sessions.

**Environment & identity**
- Backend: `ok / development / postgres / release=9ca0e61…`;
  frontend bundle embeds `9ca0e61…`. Purple banner visible:
  *"DealerDOH DEV — Development Environment — Synthetic/Test Data
  Only."* Production untouched (`master` = `13c4f815` =
  `v1.0.0-beta.6`).

**Authentication & memberships**
- Tokenless `GET /dashboard` and `POST /inventory-sync/validate` →
  401. `/me` (manager session) returns membership-backed
  `role=manager`. Roster via `/users`: all five expected
  memberships active — admin, manager, lot_staff ×2 (incl. the
  owner's account), sales_manager. Session refresh after access-token
  expiry works (reload → supabase-js refresh → authenticated).
- **Not re-exercised live, deliberate:** Lot Staff login (passwords
  are owner-held; see launch packet step 0), and sign-out (would
  destroy the moderator session asset). Both are covered by the CI
  auth matrix on this SHA and prior deployed evidence (Sprints
  05/09/12/13) on unchanged auth/nav code, and both occur naturally
  during real sessions.

**Role surfaces & navigation (manager, live)**
- Landing = Overview with the standing dashboard (16 open tasks in
  4 groups: 7 checked-out-key / 4 RecovR / 2 key-for-RecovR /
  3 MDD; 2 recommendations; 58.82% inventory health; sync tile).
- Manager nav: Overview / Tasks / Vehicles / Inventory Sync / Help /
  Profile & Settings / Sign Out — Inventory Sync present for this
  role as required.
- First Tab on a fresh authenticated load focuses **"Skip to main
  content"** (real key event, verified live).

**Core workflows (live, zero-mutation)**
- Vehicles: 28 active listed; page search (labeled *stock, VIN,
  make, model*) filters `QA1013` to exactly 1; **Sold** toggle shows
  the 6 sold vehicles (incl. QA1042) and hides them again. Global
  header search is **VIN-only by design** (labeled "Search by
  VIN…") — a distinct surface from the page search.
- Vehicle Detail: opens from the row control; QA1016 shows the full
  honored story (Install RecovR task labeled **"Completed"**, the
  pairing event in the timeline); QA1013 shows both outstanding
  investigate tasks; sidebar navigation dismisses the detail (the
  Sprint 12 fix, live).
- API spot-checks match `SYNTHETIC_QA_MATRIX.md` exactly: QA1016
  honored / QA1042 sold+moot / QA1013 two outstanding /
  QA1014 zero tasks (missing-Keyper rule); 28/34 active/total;
  2 recommendations (QA1025, QA1026); sync history = 2 batches,
  newest 2026-08-16.
- Tasks page: all four groups render. Inventory Sync page: last
  sync shown, all five sources listed, history and the
  validate/run controls present (manager). Help: renders with the
  manager sync section; **"Replay the Getting Started tour"** opens
  a true dialog ("Step 1 of 4"), "Skip for now" closes it cleanly.

**Reliability & telemetry**
- Zero application console errors or CSP violations across the
  whole pass (the only console entries are this preflight's own
  intentional 4xx probe responses). Backend healthy throughout.
- Telemetry posture unchanged and pinned by CI on this SHA
  (explicit events only; `$autocapture`/`$pageview` off; PostHog
  `persistence:'localStorage'` byte-verified in the served bundle
  2026-08-25 — zero cookies with analytics active). No real names,
  emails, VINs, or report content were entered during preflight —
  only `QA…`/`1QATEST…` fixtures.

**Honest limitations of this preflight**
- The in-app browser pane ran hidden, which swallows real
  mouse-click dispatch; functional UI checks above were driven by
  page-context JS where real clicks did not land. Real-input
  interaction fidelity (keyboard cycles, Escape-closes-detail,
  focus management, touch targets) is covered by the Sprint 14
  merged-head deployed evidence with real key events — the frontend
  interaction code is unchanged since — plus the 47 structural
  accessibility pins green in CI on this SHA. Human sessions use a
  real browser and will exercise real input by definition.
- Sentry was not re-inspected live this pass (zero-noise proven
  repeatedly on this code line; no new error paths shipped since).
  Session telemetry review happens per §5.M exit 4 after sessions.

**Verdict: DEV is ready for human sessions. No pre-UAT blocker.**
