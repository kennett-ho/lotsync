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

*Sections below this line are added as the sprint progresses:
role experience principles, information architecture, onboarding
model, Help model, analytics questions, and limitations.*
