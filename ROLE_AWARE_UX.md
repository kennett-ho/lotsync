# DealerDOH Role-Aware UX, Onboarding & Contextual Help

**Status:** Sprint 12 in progress — this document begins as the
Phase 1 Role/Workflow Audit and grows into the canonical UX
architecture record as the sprint lands. Rails: **B — Onboarding &
Contextual Help** and **C — Role-Aware Presentation**
(`V1_1_RELEASE_READINESS.md` §5.B / §5.C).

Governing philosophy (from the product doctrine — presentation may
change emphasis, never truth):

> Vehicle is the central operational entity. Systems provide
> evidence. DealerDOH connects evidence and surfaces work. Humans
> retain operational judgment. Missing evidence ≠ zero. Invalid
> evidence ≠ valid zero. Stale evidence ≠ current evidence.

Server authorization remains the security boundary
(`api/auth.py`); everything this document describes is
presentation.

---

## 1. Phase 1 Audit — the product as it stands (pre-Sprint-12)

Audited 2026-08-19 against merged `dev` (`d434b7f`) — code reading
of every reachable surface plus a live deployed walkthrough as the
standing QA manager. The deployed walkthrough for Lot Staff is
scheduled with the smoke phase (synthetic QA lot_staff user); its
presentation below is derived from code, which is authoritative
today because the frontend renders almost everything
role-identically.

### 1.1 The authoritative authorization matrix (server truth)

| Role | May do | May NOT do |
|---|---|---|
| `admin` | Everything below + all shared surfaces | — |
| `manager` | Same as admin today (distinction reserved, not invented) | — |
| `lot_staff` | All shared operational reads/workflows (vehicles, tasks, work-order PDF, dashboard, recommendations, sync history/exceptions reads) | `POST /inventory-sync/validate`, `POST /inventory-sync/run`, all `/users*` administration (403) |
| `sales_manager` | Authenticated store-scoped shared data access (architecture reservation) | Same restrictions as lot_staff |

Restricted surface total: **two** — sync execution
(`SYNC_RUN_ROLES`) and user administration (`USER_ADMIN_ROLES`),
both admin/manager.

### 1.2 What the frontend does with roles today

Exactly two role-conditional renders exist in the live bundle:

1. `Profile.tsx` — the **User Management** section/tab renders only
   for admin/manager.
2. `UserManagement.tsx` — a manager's grantable-role list is
   restricted (lot_staff + sales_manager only).

Everything else — navigation, landing page, Dashboard content,
Inventory Sync controls, Tasks, Vehicles, Vehicle Detail — renders
byte-identically for every role. `App.tsx`'s own comment records
this as a deliberate MVP posture: *"one nav, one workflow … no
branching here — just the fixed set of screens every user sees."*

### 1.3 Current navigation & landing (all roles)

- Sidebar: **Dashboard · Vehicles · Tasks · Inventory Sync**
  (fixed `NAV_ITEMS`), identity footer (name · role · dealership ·
  Sign Out), **Profile & Settings** entry.
- Landing: always **Dashboard** (`useState('dashboard')`).
- Header: VIN search, live systems badge, last-sync relative time.
- Navigation is state-based (no URL routing) — recorded by
  Sprint 09/`main.tsx` as this sprint's question.

### 1.4 Per-surface findings

**Dashboard** ("Good Morning — here's your work queue for today")
— stat strip (RecovR installs pending · MDD installs pending ·
Open recommendations · Inventory health %), Open Tasks grouped
accordion, Recommendations list, Inventory Sync health card,
Recent Activity. A solid *hybrid* — but its emphasis (health %,
recommendation review, sync state) is manager judgment work, and it
is also what a lot-staff user lands on: their "what do I do right
now" is one collapsed accordion among manager panels.

**Vehicles** — real-field filters (All / Keys Out / RecovR Missing
/ MDD Missing / Has Open Tasks), sortable columns, 28-of-28 active
QA vehicles. Sold vehicles are excluded with **no browse path**
(known finding, reassessed in §1.7). Rows open Vehicle Detail.

**Tasks** — dispatch queue grouped by `task_type`, with
`commitment_standing` and `execution_status` correctly kept
separate everywhere; Generate Work Order (PDF) works; sidebar
queues Active / My Tasks / Standing Policy / Ratified by Person /
Verification Needed / Closed Today / Closed.

**Vehicle Detail** — the app's evidence-richest surface: identity,
per-system status, timeline (source-attributed events with
timestamps), connected-systems cards with record counts and
last-sync times.

**Inventory Sync** — the full Sprint 10 validate → preview →
acknowledge → run workflow, recent runs, exceptions
(PendingIdentity), per-system status. Rendered identically for
every role.

**Profile & Settings** — Sprint 09's honest settings: display name
(real), read-only email/access, password-reset email, sign out;
User Management tab for admin/manager only.

### 1.5 Dead, fake, or dishonest controls found

| # | Finding | Location | Severity for this sprint |
|---|---|---|---|
| D1 | **"My Tasks" filter is permanently empty** — filters on `assigned_employee_id === 'emp-0142'`, a pre-auth placeholder; the employee table is empty in every real environment and no assignment concept exists. The Demo-Polish rule that hides can-only-be-zero Department/Priority filters was never applied to it. | `Tasks.tsx` `CURRENT_EMPLOYEE_ID` | Fix in-sprint (remove honestly; assignment does not exist) |
| D2 | Header search placeholder promises "Search VIN, Stock #, Customer…" but only a VIN resolves (`GET /vehicles/{vin}` is the only lookup); stock numbers dead-end in Vehicle Detail's not-found state; no customer entity exists anywhere. | `App.tsx` Header | Fix in-sprint (honest placeholder; stock lookup only if trivially supportable) |
| D3 | Task actions (Start / Pause / Mark Complete / Cancel) and Vehicle Detail actions (Edit Vehicle / Create Task / Log Event) are disabled "Coming soon" — write APIs deliberately don't exist. Honest as far as it goes, but six disabled buttons is real noise for a lot-staff execution surface. | `Tasks.tsx`, `VehicleDetail.tsx` | Presentation decision in-sprint; write APIs stay out of scope |
| D4 | Exceptions table surfaces raw engine codes (`tekion_auto_generated_stock_number`, `unrecognized`) as the REASON column. | `InventorySync.tsx` | Translate to operational language in-sprint (Phase 6 rule) |

### 1.6 Navigation finding — confirmed live, promoted to in-sprint fix

The known sidebar-vs-Vehicle-Detail finding reproduced immediately
and is worse than its register entry describes. With a vehicle
open, clicking any sidebar item: (1) appears to do nothing (the
overlay stays), (2) moves the sidebar highlight to the clicked
surface anyway, and (3) silently rewrites the breadcrumb — after
clicking **Tasks** the breadcrumb read **"Dashboard /"** and its
Back button then landed on **Tasks**. Three contradictory signals
in one interaction. Mechanism: `App.tsx` `setActiveNav` never
clears `selectedVehicle`, and `backLabel` only knows
`'vehicles' → Vehicles, else Dashboard`. Sprint 08 classified this
non-blocking *unless UX work promoted it* — role-aware navigation
does exactly that. **Disposition: fix in Sprint 12.**

### 1.7 Sold-vehicle browse (Phase 18 reassessment input)

Sold rows are retained and directly retrievable
(`GET /vehicles/{vin}` resolves them; QA has 6). Manager workflows
that genuinely reach for them exist in the current product's own
evidence: the standing QA recommendations are literally
*"Key checked out N days — Likely Sold, Verify to Remove from
OMS"*, and sold-vehicle key/device cleanup is a governed Sprint 17
cross-system scenario (`Review Sold Vehicle Key`). A manager
investigating one today must already know the VIN. Assessment: a
**minimal filter addition** on the existing Vehicles surface (an
"Include sold" / "Recently sold" filter chip reusing the already
present per-row data) is justified by current workflows; a full
archive is not. Final disposition decided at implementation.

### 1.8 Missing context for a first-time user

- **No onboarding of any kind** — first login lands cold on the
  manager-leaning Dashboard with zero explanation of what DealerDOH
  is, what evidence means, or why work exists.
- **No Help surface at all** — zero help entry points anywhere.
- **Task "why"** — group cards carry one honest sentence (e.g.
  *"Key has been checked out longer than expected"*), but the
  evidence trail (days out, per-source timestamps) lives only in
  Vehicle Detail's timeline, and nothing explains
  Standing Policy vs Ratified by Person, or what
  commitment/execution states mean.
- **Recommendations** are already fairly explainable
  (*"Key checked out 25 days — Likely Sold, Verify to Remove from
  OMS"*) but nothing explains that recommendations are
  evidence-for-human-judgment, not committed work.
- **Freshness** — the header's "Synced N ago", Dashboard's last
  sync, and per-system completed-at timestamps all exist (SyncRun
  data); nothing frames staleness. Per-source
  Fresh/Aging/Stale classification is Sprint 17's model — Sprint 12
  surfaces only what SyncRun already supports.
- **Empty states** — several are already good ("No open tasks.",
  "No syncs recorded yet — upload reports to get started."); the
  full audit of remaining ones happens at implementation.

### 1.9 Role mismatches (seen action ≠ permitted action)

| Role | Mismatch |
|---|---|
| lot_staff | Sees the entire Inventory Sync upload/validate/run workflow; every action would 403 server-side. The nav item itself invites a dead end. |
| lot_staff | Lands on the manager-emphasis Dashboard; no execution-first surface exists. |
| sales_manager | Has no distinct workflow at all (by design — architecture reservation); sees the same manager-leaning everything, including the Inventory Sync dead end. |
| manager/admin | No authority gaps found; their mismatch is absence — no onboarding/help to delegate learning to. |

### 1.10 What is genuinely good and must not be churned

Grouped dispatch cards; the commitment/execution split rendered
everywhere; honest empty states and the data-driven
hide-zero-filters rule; the work-order PDF flow; Vehicle Detail's
evidence timeline; Sprint 10's validation preview UX; Sprint 09's
honest settings; the live systems badge. Sprint 12 reorganizes
emphasis around roles — it does not redesign these.

---

## 2. Role experience principles (Phase 2)

One application, one operational truth, one task engine. Role
changes **emphasis, ordering, landing, and visibility of
action-surfaces the role cannot use** — never data truth, task
semantics, or authorization.

### Manager (and Admin)

Primary question: **"What needs attention right now?"**
Landing: **Overview** (the existing Dashboard, retitled — its
content already answers the manager questions: health, open work,
recommendations, sync state, activity; it is not rebuilt).
Emphasis: inventory health · recommendations (judgment work) ·
full task visibility · Inventory Sync control · User Management.
Admin is presented exactly as Manager (the server-side equivalence
is deliberate and reserved; no separate Admin workspace).

### Lot Staff

Primary question: **"What do I need to do, on which vehicle, and
why?"**
Landing: **Today's Work** — a new execution-first composition over
the existing task data (see §4). Emphasis: outstanding work
grouped and prioritized · vehicle identity and lookup · the reason
work exists · work-order access. Reduced: manager judgment panels
(health %, recommendation review) and administration.
The **Inventory Sync nav item is not shown** to lot_staff: it is an
action surface whose actions 403 for them (audit §1.9) — a standing
dead end. The *evidence* it carries stays reachable where lot staff
need it: per-system freshness on Vehicle Detail, the header sync
badge, and Today's Work's evidence-freshness line. Hiding the
dead-end control is presentation; `SYNC_RUN_ROLES` remains the
security boundary and is regression-tested.

### Sales Manager

No mature distinct workflow exists and none is invented. Sales
Managers get the shared presentation (Overview landing, Vehicles,
Tasks) without the Inventory Sync action surface, and without the
lot-execution framing. Recorded honestly as the current
disposition; future Sales modules are POST-v1.1 architecture.

## 3. Information architecture (Phase 3)

Role-resolved navigation, computed from the server-confirmed `/me`
role (`AccessProvider`) — never from client-selectable state; there
is no role switcher of any kind.

| Role | Nav order | Landing |
|---|---|---|
| admin / manager | Overview · Tasks · Vehicles · Inventory Sync (+ Profile & Settings, Help) | Overview |
| lot_staff | Today's Work · Vehicles · Tasks (+ Profile & Settings, Help) | Today's Work |
| sales_manager | Overview · Vehicles · Tasks (+ Profile & Settings, Help) | Overview |

Rules:

- **`AUTH_MODE=disabled` (today's production posture) is
  byte-identical to pre-Sprint-12 behavior**: the fixed
  four-item nav, Dashboard landing, no onboarding, no role logic.
  `/me` provides no membership there; role-aware presentation
  activates only on a server-confirmed role. This is the sprint's
  production-safety invariant and is test-pinned.
- Unknown/unresolved role (loading, or an unexpected value) falls
  back to the shared shape (current nav + Dashboard landing) —
  presentation fails open to the generic experience, never to a
  privileged one; the server keeps authorizing every request
  regardless.
- Shared surfaces stay shared: Vehicles, Tasks, Vehicle Detail,
  Profile render the same product truth for everyone.
- Navigation stays state-based this sprint (no URL routing
  introduced); the sidebar-dismissal defect in §1.6 is fixed so
  state navigation is honest.

## 4. Sprint 12 decision record (implementation contract)

| # | Decision | Rationale |
|---|---|---|
| S12-1 | Dashboard is retitled **Overview** for manager/sales_manager and remains the same component with the same data; greeting copy becomes role-neutral operational language. | Phase 4: don't replace working data for novelty. |
| S12-2 | **Today's Work** is a new composition (`TodaysWork.tsx`) over `GET /tasks` (outstanding) + the existing work-order PDF endpoint + `GET /dashboard` freshness metadata. No new endpoints, no task-engine duplication, commitment/execution vocabulary reused verbatim. | Phase 5. |
| S12-3 | Task actions remain read-only (no write APIs invented); Today's Work presents status honestly and routes execution evidence through Vehicle Detail. Recorded as a UAT-risk finding (execution tracking is still paper/verbal). | Phase 5 boundary; write APIs out of scope. |
| S12-4 | "My Tasks" queue filter is **removed** (D1): no assignment concept exists; a permanently-empty filter is dishonest. Returns only with a real assignment feature. | Audit D1. |
| S12-5 | Header search placeholder becomes honest ("Search by VIN…"); no stock-number lookup invented this sprint. | Audit D2. |
| S12-6 | Sidebar navigation clears an open Vehicle Detail; breadcrumb reflects the true origin surface. | Audit §1.6, promoted per Sprint 08 condition. |
| S12-7 | Exceptions REASON codes are translated to operational sentences at render (map in the frontend; codes remain the API contract). | Audit D4, Phase 6. |
| S12-8 | Vehicles gains a **Sold** filter chip (default view unchanged: active only). | Audit §1.7 reassessment. |
| S12-9 | Onboarding completion lives in **Supabase `user_metadata`** (`dealerdoh_onboarding`) via the Sprint 09 display-name mechanism (client `updateUser` + the existing token-refresh handling); follows the user across devices; **no DealerDOH schema migration**. If implementation surfaces a hard edge, the documented fallback is localStorage with the tradeoff recorded. | Phase 10; smallest correct model, proven mechanism. |
| S12-10 | Onboarding is a short role-aware welcome (3–4 steps). **Skip records completion** (analytics distinguishes skipped from finished); replay is always available from Help — so it can never block work and never nags. | Phases 8/9/11. |
| S12-11 | **Help** is a lightweight surface (sidebar entry) with role-aware sections; Inventory Sync help appears only for sync-authorized roles; "Replay Getting Started" lives there. Contextual help is added sparingly: recommendations meaning, task standing/execution meaning, validation-warning meaning. | Phases 12/13. |
| S12-12 | New analytics events (all through the Sprint 11 wrapper, safe props only): `onboarding_started` / `onboarding_completed` / `onboarding_skipped` / `onboarding_replayed`, `help_opened`, `today_work_opened`. `page_viewed` is reused for the new surfaces (new controlled page ids `today-work`, `help`). | Phases 19/20; questions recorded in §analytics. |
| S12-13 | Evidence freshness this sprint = what SyncRun already supports (last accepted sync per source, presented with relative time). Per-source Fresh/Aging/Stale classification is Sprint 17's model and is **not** built here. | Phase 7. |

## 5. Onboarding model (implemented)

Completion state: Supabase `user_metadata.dealerdoh_onboarding`
(`frontend/src/onboarding/state.ts`) — `{completed_at, version,
skipped}` — written with the Sprint 09-proven client `updateUser`
mechanism. Cross-device, no migration, no API surface; read
client-side from the auth user object, so no token-refresh dance.
Every function is a safe no-op without a Supabase client and never
throws: onboarding is secondary to work.

Behavior: first authenticated session with no record opens the tour
(3–4 role-aware steps, `onboarding/Onboarding.tsx`); **skip records
completion** exactly like finishing (a skipped user chose not to
tour — never nag) and the two are distinguished only in analytics;
**replay** is always available from Help and never rewrites the
record. With auth disabled (production) onboarding does not exist.
Content per role: manager/admin (Overview → evidence/Inventory
Sync → Help), lot_staff (Today's Work → why work exists → Help;
never mentions Inventory Sync or User Management), shared/sales
(Overview/Vehicles/Tasks → Help). Copy is operational and short —
what it is, what it shows, who decides.

## 6. Help model (implemented)

`help/Help.tsx`, reachable from the sidebar for every role, beneath
the operational nav. Sections: What is DealerDOH · Understanding
Tasks · Understanding Recommendations · Vehicles & the evidence
timeline · Inventory Sync (**rendered only for sync-authorized
roles**) · Account & access (admin flavor for user admins, standard
otherwise) · Troubleshooting · Replay the Getting Started tour.
Contextual help stays sparse by design: the one inline explainer is
the Overview's recommendations subtitle ("Evidence for human review
— nothing commits automatically"); tasks and validation-warning
meaning live in Help and in the surfaces' own existing copy.

## 7. Analytics — events and their product questions (Phase 19/20)

All through the Sprint 11 wrapper; safe properties only (role and
controlled identifiers ride the existing person/registered
properties; the Sprint 11 posture suite's repo-wide `track()` scan
covers every new call).

| Event | Product question it answers |
|---|---|
| `onboarding_started` | Do first-time users actually receive the getting-started flow? |
| `onboarding_completed` | Do first-time users finish it? |
| `onboarding_skipped` | Are users abandoning onboarding because it is unnecessary or too long? (ratio vs completed) |
| `onboarding_replayed` | Do users return to the tour for re-orientation — is Help discoverable and the tour worth revisiting? |
| `help_opened` | Where do users seek additional explanation? (volume/role mix) |
| `today_work_opened` | Do Lot Staff use the role-focused work surface as their operational starting point? |
| `page_viewed` (reused) | Which surfaces do the roles actually live on? New controlled ids: `today`, `help`. |

## 8. Current limitations (recorded honestly)

- **Task execution is display-only** — no write APIs exist; Start/
  Complete tracking remains paper/verbal. The dead buttons are gone
  (audit D3); the capability gap stays and is a UAT-risk finding.
- **Recommendations cannot be dismissed or converted to tasks
  in-app** (the local-only Dismiss was removed as dishonest, D5).
- **Search is VIN-only**; a stock-number lookup would need a backend
  endpoint that doesn't exist yet.
- **Freshness is last-accepted-sync recency only** — per-source
  Fresh/Aging/Stale classification, HOLD-state surfacing, and
  automated acquisition status displays are Sprint 17's model; the
  Today's Work freshness line and per-system timestamps are the
  seams they will extend.
- **sales_manager** has an honest shared experience, no distinct
  workflow (future Sales modules are POST-v1.1).
- Navigation remains state-based (no URLs); the dismissal defect is
  fixed, the wider routing question stays open in the findings
  register.
