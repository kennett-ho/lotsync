# DealerDOH DEV — QA Guide

How to use, inspect, and reset the standing QA dealership in the
development environment. Written for future agents and developers
running `/smoke-test` or manually verifying behavior after a change.

- **Dev frontend:** https://dealerdoh-dev.vercel.app (permanent
  "DealerDOH DEV" banner)
- **Dev API:** https://dealerdoh-api-dev.onrender.com (`GET /health` →
  `{"status":"ok","environment":"development","database_engine":"postgres"}`;
  free tier — first request after idle takes ~50s)
- **Scenario source of truth:** `SYNTHETIC_QA_MATRIX.md` ·
  **asserted form:** `dev_seed/expected.py` ·
  **seed internals:** `dev_seed/README.md`

## Is the seed healthy?

Standing counts after a fresh reseed (exact, deterministic):

| vehicles | active | sold | tasks | open | honored | moot | recs | events | pending | sync runs |
|---|---|---|---|---|---|---|---|---|---|---|
| 34 | 28 | 6 | 18 | 16 | 1 | 1 | 2 | 98 | 3 | 10 |

Open tasks by type: 4× Install RecovR Device · 2× Investigate Key for
RecovR · 7× Investigate Checked-Out Key · 3× Install MDD Beacon.

Quick checks: the Vehicles page shows 28 rows by default (34 with sold
included); the Tasks page shows 16 open; Dashboard's health figure is
20/34 vehicles with no open work (58.82%). If any of these differ and
nobody changed business rules on purpose, something regressed — the
same numbers are enforced by `tests/test_qa_dataset.py` in CI on both
engines. (Replaying a sync day without resetting first adds 2 events
via QA-CONFLICT-002 — see "known quirk" below.)

**Note on dates:** all aging/expected outcomes are pinned to the QA
reference date **2026-07-21** (see the matrix's time-strategy section).
Relative display text ("Synced N hours ago") tracks the real clock;
the *business outcomes* (which tasks exist, which buckets apply) never
drift.

## Role-aware expectations (Sprint 12)

What each standing QA login should see on a healthy deployment
(`ROLE_AWARE_UX.md` is canonical):

| Login | Landing | Nav | Notes |
|---|---|---|---|
| `manager@qa.dealerdoh.example` | Overview (the dashboard, retitled) | Overview · Tasks · Vehicles · Inventory Sync | Help + Profile below the divider; User Management inside Profile |
| `lotstaff@qa.dealerdoh.example` | **Today's Work** (16 open tasks in 4 groups, expanded; freshness line; Generate Work Order) | Today's Work · Vehicles · Tasks — **no Inventory Sync item** (every action there 403s for the role; the server still enforces this regardless of UI) | Help has no Inventory Sync section |
| sales manager QA login | Overview | Overview · Vehicles · Tasks | Shared honest experience; no invented workflow |

First authenticated login per user shows the role-aware Getting
Started tour once (completion lives in Supabase `user_metadata`, so
it follows the user across devices; skip counts as completion;
replay any time from Help). Onboarding/Help do not exist in the
unauthenticated production posture. To re-test first-run for a QA
user, clear `user_metadata.dealerdoh_onboarding` for that user in
the Supabase dashboard.

## Signing in (Sprint 05)

DealerDOH DEV requires authentication — unauthenticated visitors see
the login screen, and every operational API route returns 401 without
a valid token. Synthetic accounts (passwords in the owner's password
manager; **never** in this repo):

| Email | Role | Dealership | Use it to test |
|---|---|---|---|
| `admin@qa.dealerdoh.example` | Admin | qa-motors | everything, incl. sync run |
| `manager@qa.dealerdoh.example` | Manager | qa-motors | everything, incl. sync run |
| `lotstaff@qa.dealerdoh.example` | Lot Staff | qa-motors | shared operational data; sync run must be **denied** (403) |
| `salesmanager@qa.dealerdoh.example` | Sales Manager | qa-motors | shared data access; no extra features exist yet by design |
| `outsider@qa.dealerdoh.example` | Manager | **qa-store-b only** | the store boundary: this login gets **403** from every operational endpoint of this deployment |

There is deliberately no role switcher — to test another role, sign
out and sign in as another account. The sidebar footer shows the
server-verified identity (email · role · dealership, from `GET /me`).

After any `seed_dev.py --reset`, membership rows are gone (Auth users
survive — they live in Supabase, not the app schema): re-run
`tools/provision_dev_auth.py` to re-link them. See
`AUTH_ARCHITECTURE.md` for the full model.

## What to click — one tour per behavior

Find any vehicle fast: Vehicles page → search its stock number.

| To see… | Open… | Expect… |
|---|---|---|
| A healthy vehicle (no over-generation) | stock **QA1001** | 0 open tasks; timeline has exactly one card per source; RecovR shows paired |
| A ready-to-install RecovR task | **QA1011** | one "Install RecovR Device" open task, reason says Keyper confirms the key is In |
| Install blocked by a checked-out key | **QA1012** | "Investigate Key for RecovR" (NOT an install task) — key is Out 1 day |
| Two tasks coexisting on one vehicle | **QA1013** | "Investigate Key for RecovR" + "Investigate Checked-Out Key" (7 days out) |
| The multi-install vehicle | **QA1092** | "Install MDD Beacon" + "Install RecovR Device" |
| The aging ladder | **QA1020–QA1026** | keys out 0/1/3/7/14/25/30 days; tasks only from QA1022 (3 days) up; QA1025/QA1026 also carry a High recommendation ("Likely Sold…") |
| RecovR paired + key out stay separate | **QA1027** | only "Investigate Checked-Out Key" — no RecovR task exists |
| Wholesale exclusion | **QA1031** | only "Install MDD Beacon" (RecovR install suppressed by Step=WHOLESALE); **QA1032** = zero tasks despite 10-days-out key |
| At Auction exclusion | **QA1033** | zero tasks |
| Archive is NOT an exclusion | **QA1034** | "Install RecovR Device" exists despite Step=Archive |
| A completed (honored) task | **QA1016** | task shows **Completed** — RecovR paired on Day 2 |
| A mooted task | **QA1042** (enable "include sold" / open by VIN) | task shows **No Longer Needed** — vehicle sold before install |
| Sold preservation | **QA1041** | hidden from default list, full timeline preserved (keyper/sold/recovr/mdd cards), 0 open tasks |
| Conflicting evidence | **QA1051** | status Sold (sold list wins the cache); timeline holds BOTH the stocked-in and sold claims |
| The contradictory sold export | **QA1052** | 4 sold events (2 stocks × 2 runs — the documented re-fire limitation) |
| Pending identity resolved | **QA1061** | timeline includes "Keyper identifier '888555' … now resolves to this vehicle" |
| An unmatched key with no vehicle | Inventory Sync screen | pending identities `9755` and `#QA-ODD` remain pending |
| No-Keyper-evidence restraint | **QA1014** | RecovR shows not paired, key record absent → zero tasks (silence ≠ "key is In") |
| Internal fleet exclusion | **QA1081** | visible, zero tasks ever |
| Store-filter divergence | **QA1093** | MDD shows not_paired on the vehicle, but no task (other store's row) |

UI label mapping (frontend/src/taskStatus.ts): outstanding → **Open**,
honored → **Completed**, moot → **No Longer Needed**, cancelled →
**Cancelled**, superseded → **Replaced**. The standing seed contains
the first three; cancelled/superseded have no product-reachable
producer yet (unit-tested at the repository layer only).

## Ingestion safety (Sprint 10 — Rail D)

The Inventory Sync page is now a validate → preview → run flow:
select files, **Validate Reports**, review the per-report preview
(detected type, counts, previous-comparable change, issues), tick the
acknowledgement if warnings exist (never pre-checked), then **Run
Sync Now** (disabled until then). Changing any file clears the
preview. Full behavior: `INGESTION_ARCHITECTURE.md`.

QA tour, using `tests/fixtures/` copies as uploads (manager/admin
login — lot staff correctly cannot see this work at all):

| Behavior | Upload | Expect |
|---|---|---|
| Clean set previews Ready | `synthetic/tekion_master.csv` in Tekion Unsold (+ any others in their slots) | per-report **Ready**, counts shown, "No prior baseline" on first use; Run enables |
| Empty snapshot rejected | `ingestion/tekion_headers_only.csv` in Tekion Unsold | **Rejected — No vehicle records were found…**; Run stays disabled; run attempt (direct API) 422s with zero mutation |
| Wrong report type | `synthetic/tekion_sold.csv` in Tekion **Unsold** | **Rejected — Wrong report type**, message names Sold Inventory and the right slot |
| Keyper variant boundary | `ingestion/keyper_variant_stand_in.csv` in Keyper | **Rejected** — "…not the Full Key Inventory report… not yet supported… never substitute" |
| Missing column | `ingestion/tekion_missing_status.csv` in Tekion Unsold | **Rejected — required column(s) missing: Status** |
| Acknowledged zero | `ingestion/mdd_headers_only.csv` in MDD | **Review needed** warning; Run disabled until the box is ticked; after run, MDD SyncRun records 0 honestly |
| Suspicious count | two sequential syncs of generated Tekion files (e.g. 40 rows then 20) | second preview shows previous 40 / change −20 (−50%) + warning; unacknowledged run 409s |
| Duplicates surfaced | `ingestion/tekion_duplicate_vins.csv` | warning names the repeated VIN |

The standing 34-vehicle QA dealership is untouched by all of the
above — rejected/previewed uploads mutate nothing (that's the rail).

## Work-order PDF

Tasks page → Print Work Order (or `GET /tasks/work-order` on the dev
API). Expect all 16 open tasks grouped by type across the 14 vehicles
that hold them, sold vehicles absent.

## How to reseed dev

Deliberate operator action (never a boot side effect). From a machine
with the repo:

```bash
DATABASE_ENGINE=postgres DATABASE_URL=<dev-only DSN from the owner's password manager> ENVIRONMENT=development PYTHONPATH=.. python seed_dev.py --reset
```

- `--reset` drops the app tables and re-migrates, then replays QA Day 1
  + Day 2. Final line prints the standing counts (must match the table
  above; the DSN is never printed).
- **Sprint 13 (fail-closed guard):** a PostgreSQL `--reset` now requires
  `ENVIRONMENT` to explicitly name a development environment
  (`development`/`local`/`test`) — the command above already sets
  `ENVIRONMENT=development`, so nothing changes for the documented
  workflow. Running the postgres reset with `ENVIRONMENT` unset or an
  ambiguous value (`prod`, `staging`, …) is now **refused** (it would
  otherwise drop every table from whatever `DATABASE_URL` names — the
  absence of the literal `"production"` is not proof of a safe target).
- Local practice run (SQLite, no env needed):
  `PYTHONPATH=.. python seed_dev.py --reset`
- Known quirk: replaying a day **without** `--reset` is idempotent
  except QA-CONFLICT-002, which re-fires its 2 contradictory sold
  events per pass (documented, asserted limitation).

## Never do against production

- Never run `seed_dev.py` with production values. Guardrails refuse
  `ENVIRONMENT=production` and the production DB path, but the rule is
  procedural too: production (`master`, `lotsync-api.onrender.com`,
  `lotsync-nu.vercel.app`, `/var/data/lotsync.db`) is locked at
  v1.0.0-beta.6 — release train only.
- Never point `DATABASE_URL` anywhere but the `dealerdoh-dev` Supabase
  project (DealerDOH org). Never touch the Wise Pelican Supabase org.
- Never copy production data into dev — the QA dealership is complete
  on its own by design.
