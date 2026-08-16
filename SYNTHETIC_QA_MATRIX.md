# Synthetic QA Matrix — the DealerDOH DEV standing dealership

Sprint 04. This document is the **source of truth** for what the
development seed (`dev_seed/`) is intended to prove. Every synthetic
vehicle in DealerDOH DEV exists to demonstrate one or more specific,
already-implemented operational rules — if a future change alters any
expected outcome below, the automated assertions in
`tests/test_qa_dataset.py` (which import `dev_seed/expected.py`, the
machine-readable form of this matrix) fail on both SQLite and
PostgreSQL before the change reaches the deployed dev environment.

**This matrix asserts implemented behavior only.** No rule below was
invented for testing. Where a scenario family from the sprint brief
did not map to an implemented rule, the discrepancy is recorded in
"Discrepancies and non-mappings" at the bottom rather than papered
over.

---

## How the seed runs

The seed replays **two consecutive sync days** through
`sync/pipeline.py`'s `run_inventory_sync()` — the exact code path the
production Inventory Sync API uses (which itself reuses everything
`main.py` runs). Nothing in the seed writes rows directly; every row
in the standing database is the product of the real pipeline
processing deterministic source files.

| | Sync date | Purpose |
|---|---|---|
| **Day 1** | `2026-07-20` | Baseline state; creates the initial tasks/events |
| **Day 2** | `2026-07-21` (**QA reference date**) | State transitions: sale → Moot, RecovR pairing → Honored, threshold crossings, dedup-on-rerun, pending-identity promotion |

### Deterministic time strategy

All aging math in this pipeline runs against the **sync date passed to
the pipeline**, never the wall clock (`reconcile_keyper_tekion(…,
sync_date, …)`). The seed pins both sync dates and every source-file
date (checkout dates, stocked-in dates, sold dates) to fixed
calendar values relative to the QA reference date `2026-07-21`. A
vehicle whose key is "7 days out" is 7 days out **forever**, no matter
when the seed is run. Wall-clock values appear only in
display-oriented columns the business rules never read
(`observed_at`, `created_at`, sync-run timing — which is why the UI's
"Synced N hours ago" stays live while expected outcomes stay frozen).
No production time-mocking is involved.

### Synthetic identity rules

- VINs: `1QATEST` + 10 digits (17 chars) — impossible to mistake for a
  real VIN, and a distinct prefix from the unit-test fixtures'
  `1TESTVIN…` so the two populations can never be confused.
- Stock numbers: `QA####` (plus `K9####` for the new-car-format
  scenario and `QA###DM` for the damaged-repair-format scenario, since
  those formats ARE the rule under test).
- Vehicle names: obviously fictional (`2024 QA Sedan` etc.).
- Store name stays `Mark Kia` — it is the deployment's own configured
  store identity (the MDD dealership filter under test compares
  against it); no customer or employee names appear anywhere.
- All fixtures are safe to publish in Git. No production data, no
  secrets.

---

## Operational rules under test (reconstructed from code, Phase 0)

1. **`install_mdd_beacon`** — MDD not-paired row whose `Dealership`
   equals the configured store, VIN in Tekion active (non-fleet), not
   sold. *Not* Keyper-gated, *not* Wholesale-excluded
   (`build_tracker_install_tasks`, MDD loop).
2. **`install_recovr_device`** — RecovR `Paired=No`, VIN active + not
   sold, RapidRecon Step not `WHOLESALE`/`AT AUCTION`, **and Keyper
   confirms the key is In** (Sprint 3.8 gate).
3. **`investigate_key_for_recovr`** — same RecovR candidate but Keyper
   shows the key **Out** (any number of days).
4. RecovR candidate with **no Keyper record at all** → **no task**
   (absence of evidence is not evidence the key is In).
5. **`investigate_checked_out_key`** — any Keyper-matched active
   vehicle Out ≥ `KEY_OUT_INVESTIGATE_THRESHOLD_DAYS` (= 3), sold and
   Wholesale/At-Auction excluded. Independent of RecovR.
6. **Recommendation (`key_out_aging`)** — only for the most severe
   bucket (≥ 25 days, "Likely Sold, Verify to Remove from OMS").
7. **Reality-discharge** — new `tekion_sold` event **moots** open
   install tasks; RecovR flip to `paired` **honors** open
   `install_recovr_device`/`investigate_key_for_recovr`. Nothing
   discharges `investigate_checked_out_key` (documented limitation).
8. **Sold visibility** — `tekion_status = 'Sold'` excluded from the
   default vehicle list (`IS DISTINCT FROM`), fully reachable by VIN
   detail and `include_sold=true`; never deleted.
9. **Event dedup** — every source diffs before writing (Tekion on
   (status, stock) per event type; Keyper/MDD/RecovR on their status
   field; RapidRecon on `Step`). Unchanged re-observation → no new
   event; RapidRecon freshness row still updates.
10. **Aging buckets** — 0/1/3/7/14/25-day labels from
    `rules/aging.py` (Should be here / Might be here / Investigate /
    High Priority Investigate / Possibly Sold, Verify / Likely Sold,
    Verify to Remove from OMS).
11. **Pending identity** — auto-generated-numeric and unrecognized
    Keyper names, and ambiguous last-6 matches, become
    `pending_identity` rows; a later unambiguous match promotes
    (status `resolved` + `pending_identity_resolved` event).
12. **Missing source** — a source not uploaded gets **no SyncRun row**;
    a missing Keyper skips all RecovR-related task generation with an
    explicit warning (never "zero tasks silently").
13. **Archive is not an exclusion** — RapidRecon `ARCHIVE` means
    "RapidRecon is done with the vehicle," not sold/wholesale; RecovR
    eligibility is unaffected.

---

## Scenario roster (34 vehicles + 3 identity-only records)

Notation: **K**=Keyper (In/Out + checkout date), **T**=Tekion master,
**S**=Tekion sold, **R**=RecovR, **M**=MDD not-paired, **RR**=RapidRecon.
"→" marks a Day-1 → Day-2 change. Days-out are as of the reference
date 2026-07-21. Expected tasks/recs are the **standing state after
Day 2**.

### A — Baseline / no work (proves no over-generation)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-BASE-001 | 1QATEST0000000001 | QA1001 | K In, T, R Paired=Yes, RR Step=INSPECTION (unchanged Day 2) | 0 tasks. 4 events (keyper/tekion/recovr/rapidrecon observed once each — Day 2 adds none). RapidRecon freshness row updated by Day 2's run (rule 9). |
| QA-BASE-002 | 1QATEST0000000002 | QA1002 | K In, T, R Yes, RR INSPECTION → **DETAIL** | 0 tasks. 5 events — the Step change is the one claim Day 2 adds (rule 9). |
| QA-BASE-003 | 1QATEST0000000003 | QA1003 | K In, T only | 0 tasks. 2 events. The minimal healthy vehicle. |

### B — RecovR install (rule 2)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-RECOVR-001 | 1QATEST0000000011 | QA1011 | K In, T, R No | **install_recovr_device** (created Day 1, still exactly one open after Day 2 — task-level idempotency). |
| QA-RECOVR-005 | 1QATEST0000777666 | QA1015 | K In, T, R No with **6-char VIN fragment `777666`** | **install_recovr_device** — the unique-last-6 fragment resolution path, both in task generation and in `persist_recovr_observations`. |

### C — RecovR blocked by checked-out key (rules 3, 5 distinguished)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-RECOVR-002 | 1QATEST0000000012 | QA1012 | K Out 1 day (checkout 7/20), T, R No | **investigate_key_for_recovr** only — 1 day is below the 3-day aging threshold, so no `investigate_checked_out_key`. The two concepts are independent. |
| QA-RECOVR-003 | 1QATEST0000000013 | QA1013 | K Out 7 days (checkout 7/14), T, R No | **investigate_key_for_recovr + investigate_checked_out_key** (2 open tasks on one vehicle — also family K). |
| QA-RECOVR-004 | 1QATEST0000000014 | QA1014 | T (stocked 7/16), R No, **no Keyper row** | **0 tasks** (rule 4 — silence is not "key is In"). Doubles as the Trade/Other **overdue** incoming-report case: 5 days since stocked-in, no key → "Overdue - Investigate" (report-level, not DB). |

### D — Checked-out key aging ladder (rules 5, 6, 10)

All: Keyper Out (checkout at 00:00 for exact day math), Tekion active,
no RecovR/MDD/RapidRecon rows — pure aging behavior.

| ID | VIN | Stock | Days out (ref date) | Expected |
|---|---|---|---|---|
| QA-KEY-000 | 1QATEST0000000020 | QA1020 | **In → Out Day 2** (checkout 7/21, 0 days) | No task ("Should be here"). 2 keyper events — the In→Out transition, with `event_time` populated only on the Out event (family O). |
| QA-KEY-001 | 1QATEST0000000021 | QA1021 | 1 ("Might be here") | No task. Confirms day 1 is not yet actionable. |
| QA-KEY-003 | 1QATEST0000000022 | QA1022 | 3 ("Investigate") | **investigate_checked_out_key created on Day 2** — it was 2 days out on Day 1 (no task); the seed captures the threshold crossing itself. |
| QA-KEY-007 | 1QATEST0000000023 | QA1023 | 7 ("High Priority Investigate") | **investigate_checked_out_key** (created Day 1 at 6 days). |
| QA-KEY-014 | 1QATEST0000000024 | QA1024 | 14 ("Possibly Sold, Verify") | **investigate_checked_out_key**. |
| QA-KEY-025 | 1QATEST0000000025 | QA1025 | **exactly 25** ("Likely Sold…") | **investigate_checked_out_key + Recommendation created on Day 2** (24 days on Day 1 → no rec; ≥25 boundary is inclusive). |
| QA-KEY-030 | 1QATEST0000000026 | QA1026 | 30 ("Likely Sold…") | **investigate_checked_out_key + Recommendation** (rec created Day 1 at 29 days; Day 2 does not duplicate it). |

Labels 0/1/3/7/14/25 are the dealership's confirmed scale
(`rules/aging.py`); only the ≥3 task rule and the most-severe-bucket
recommendation rule generate DB work — the intermediate labels are
report/display tiers, asserted as bucket labels, not as new task types.

### E — RecovR present + key out (workflow non-conflation)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-KEY-PAIRED | 1QATEST0000000027 | QA1027 | K Out 10 days (7/11), T, **R Paired=Yes** | **investigate_checked_out_key only.** No RecovR task of either kind may exist — the device is already installed. |

### F — Wholesale exclusion (rules 2, 5 exclusions; rule 1 non-exclusion)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-WHOLESALE-001 | 1QATEST0000000031 | QA1031 | K In, T, R No, **RR Step=WHOLESALE**, M not-paired | **install_mdd_beacon only.** RecovR install excluded by Wholesale; the MDD task proves other valid work is asserted independently (MDD was never Wholesale-excluded — a governed asymmetry, not an oversight). |
| QA-WHOLESALE-002 | 1QATEST0000000032 | QA1032 | K Out 10 days (7/11), T, R No, **RR WHOLESALE** | **0 tasks** — Wholesale excludes `investigate_key_for_recovr` AND `investigate_checked_out_key` too (both loops check the step). |

### G — At Auction exclusion

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-AUCTION-001 | 1QATEST0000000033 | QA1033 | K In, T, R No, **RR Step=AT AUCTION** | **0 tasks** — same exclusion set as Wholesale. |

### H — RapidRecon Archive is NOT an exclusion (rule 13)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-ARCHIVE-001 | 1QATEST0000000034 | QA1034 | K In, T, R No, **RR Step=ARCHIVE** | **install_recovr_device** — Archive means "recon finished," and active-frontline evidence wins. |
| QA-ARCHIVE-002 | 1QATEST0000000035 | QA1035 | S (sold 7/10), **RR ARCHIVE** | 0 tasks, excluded from default list — sold because Tekion says sold, not because of Archive. |

### I — Sold vehicle preservation (rule 8)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-SOLD-001 | 1QATEST0000000041 | QA1041 | S (sold 7/10) both days, **K In both days**, R Paired=Yes, M not-paired | 0 tasks (MDD row on a sold VIN generates nothing). Hidden from default list, visible with `include_sold`, full detail/timeline reachable. Events: keyper (via the sold-key-not-removed flag path), tekion_sold, recovr, mdd — history preserved. Report-level: flag_to_controller + sold-report `needs_removal`. |
| QA-SOLD-002 | 1QATEST0000000042 | QA1042 | Day 1: T active, K In, R No → **install_recovr_device**. Day 2: dropped from master, **S (sold 7/20)**, Keyper key removed | Task **mooted** by the new tekion_sold event (rule 7). Standing: 1 task, `commitment_standing='moot'` (UI: "No Longer Needed"). |

### J/K — MDD work and multi-task coexistence (rule 1)

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-MDD-001 | 1QATEST0000000091 | QA1091 | K In, T, M not-paired | **install_mdd_beacon**. |
| QA-MULTI-001 | 1QATEST0000000092 | QA1092 | K In, T, M not-paired, R No | **install_mdd_beacon + install_recovr_device** — two legitimately coexisting installs (grouping / Vehicle Detail / work-order rendering). |
| QA-MDD-003 | 1QATEST0000000093 | QA1093 | K In, T, M not-paired but **Dealership = "QA Other Store"** | **0 tasks** (store filter), but `mdd_status='not_paired'` + an `mdd_observed` event ARE written (persist path is VIN-trust-based, deliberately not store-filtered). Documents the persist-vs-generate population divergence as implemented. |

### P — Task lifecycle in standing data (rule 7 + UI labels)

Covered by scenarios above, produced only through real pipeline paths:

| Standing | Producing scenario | UI label |
|---|---|---|
| `outstanding` ×16 | families B–K | "Open" |
| `honored` ×1 | **QA-RECOVR-006** (below) | "Completed" |
| `moot` ×1 | QA-SOLD-002 | "No Longer Needed" |

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-RECOVR-006 | 1QATEST0000000016 | QA1016 | K In, T, R **No → Paired=Yes Day 2** | Day-1 install_recovr_device **honored** on Day 2 by the paired flip; second recovr_observed event records the flip. |

`cancelled` and `superseded` are **deliberately absent from the
standing seed**: no pipeline or currently-shipped API surface produces
them (only the repository primitives `cancel_task`/`escalate_task`,
which no product flow calls yet). Fabricating them in the seed would
put state in dev that the product cannot create. They remain covered
by the existing unit tests (`tests/test_database_slice5.py` area) and
their UI labels ("Cancelled"/"Replaced") by `frontend/src/taskStatus.ts`'s
mapping. If a future sprint ships a cancel/escalate flow, extend the
seed then — through that flow.

### L — Conflicting source evidence

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-CONFLICT-001 | 1QATEST0000000051 | QA1051 | **In master AND sold list, both days** (sold 7/19) | Vehicle cache = `Sold` (sold walked last, by design) → hidden by default. Both `tekion_observed` and `tekion_sold` events exist (each loop diffs against its own event type → Day 2 adds nothing). Surfaces on `tekion_sync_conflicts.csv`. Ambiguity preserved, not auto-resolved. |
| QA-CONFLICT-002 | 1QATEST0000000052 | QA1052 / QA1052B | **Two sold rows, same VIN, different stocks** (sold 7/1 and 7/5), both days | The documented, accepted dedup limitation (persist_tekion_observations docstring): an internally contradictory export re-fires both claims per run → **4 tekion_sold events after two passes**. Asserted as-is so the limitation stays visible instead of silently changing. 0 tasks. |

### Q — Pending identity / unmatched evidence (rule 11)

| ID | Keyper name | Type | Expected |
|---|---|---|---|
| QA-PEND-001 | `9755` | tekion_auto_generated_stock_number | Standing `pending_identity`, status `pending` forever (no resolution path exists for this type). |
| QA-PEND-002 | `#QA-ODD` | unrecognized | Standing `pending_identity`, status `pending`. |
| QA-PEND-003 | `888555` | ambiguous_last6_vin_multiple_matches → **resolved** | Day 1: two active VINs end `888555` (QA-AMB-A `1QATEST0000888555` QA1061, QA-AMB-B `1QATEST0001888555` QA1062) → ambiguous → pending. Day 2: AMB-B sells (sold 7/20) → the last-6 now matches only AMB-A → fully_verified + **promotion**: pending row `resolved`, `pending_identity_resolved` event on AMB-A. |
| — | `GOLF CART` | non_vehicle | Skipped entirely — no exception, no pending row, no vehicle. |

### Incoming/missing classification (report-level; stock-format rules)

| ID | VIN | Stock | Sources | Expected (report, not DB) |
|---|---|---|---|---|
| QA-INCOMING-001 | 1QATEST0000000071 | **K91001** | T (stocked 7/19), no Keyper | New Car (Awaiting Dropoff), 2 days → "Awaiting Transport Dropoff". 0 tasks. |
| QA-INCOMING-002 | 1QATEST0000000072 | **QA903DM** | T (stocked 7/10), no Keyper | New (Damaged - In Repair) → "not yet timed" (no invented repair baseline). 0 tasks. |
| (QA-RECOVR-004) | — | QA1014 | — | Trade/Other, 5 days → "Overdue - Investigate…" (see family C). |

### Internal fleet exclusion

| ID | VIN | Stock | Sources | Expected |
|---|---|---|---|---|
| QA-FLEET-001 | 1QATEST0000000081 | QA1081 | T, listed in the seed's internal-fleet set | Vehicle persisted and visible, but excluded from `active_vins` → can never generate tasks, and excluded from the incoming report. 0 tasks, 1 event. |

### M — Missing source day (test harness, NOT standing state)

The standing seed always uploads all sources — a "missing file day" is
a transient condition of one sync, not a persistent dealership state,
so forcing it into the standing DB would misrepresent it. It is
covered as deterministic test cases in `tests/test_qa_dataset.py`
running a third pipeline pass over the same fixtures:

- **No Keyper upload** → the run emits the explicit warning, generates
  zero RecovR-related tasks, existing tasks/vehicles untouched, and no
  `keyper` SyncRun row is written (silence, not a zero-claim).
- **Only Keyper uploaded** → no SyncRun rows for the five absent
  sources; nothing catastrophically reinterpreted as absence.

### N/O — Event dedup, freshness, chronology

Not separate vehicles — properties asserted across the roster:

- Day 2 re-observes every unchanged vehicle; per-scenario event counts
  prove zero duplicate Timeline noise (rule 9).
- RapidRecon freshness (`event_freshness`) rows update
  `last_observed_at`/`last_sync_run_id` on Day 2 even when no event is
  written (QA-BASE-001).
- `event_time` (source-claimed) vs `observed_at` (pipeline-observed):
  Keyper Out events carry checkout `event_time` (In events
  deliberately don't); Tekion events carry stocked-in/sold dates; all
  strictly earlier than `observed_at`. Timeline ordering is by
  `event_id` (insertion order) — the governed deterministic behavior —
  asserted as such, not by `event_time`.

---

## Standing totals after a fresh seed (both engines)

| Metric | Expected |
|---|---|
| Vehicles | **34** |
| Active (default list) | **28** |
| Sold (hidden by default) | **6** (QA-ARCHIVE-002, QA-SOLD-001, QA-SOLD-002, QA-CONFLICT-001, QA-CONFLICT-002, QA-AMB-B) |
| Tasks total | **18** |
| — outstanding | **16** |
| — install_recovr_device | 4 (RECOVR-001, RECOVR-005, ARCHIVE-001, MULTI-001) |
| — investigate_key_for_recovr | 2 (RECOVR-002, RECOVR-003) |
| — investigate_checked_out_key | 7 (RECOVR-003, KEY-003/007/014/025/030, KEY-PAIRED) |
| — install_mdd_beacon | 3 (WHOLESALE-001, MDD-001, MULTI-001) |
| — honored | 1 (RECOVR-006) |
| — moot | 1 (SOLD-002) |
| Recommendations (open) | **2** (KEY-025, KEY-030) |
| Pending identities | **3** (2 pending, 1 resolved) |
| Sync runs | **10** (5 sources × 2 days, all `complete`) |
| Events | asserted per-scenario in `dev_seed/expected.py`; the global total is the sum and is verified by the suite |

Reseeding is **reset + replay**: `seed_dev.py --reset` always rebuilds
from Day 1, so these totals are exact after every reseed. (Running the
seeder again *without* `--reset` replays Day 2 onto existing state —
idempotent everywhere except QA-CONFLICT-002's documented re-fire,
which adds its 2 contradictory events per extra pass. The test suite
asserts this rerun behavior explicitly.)

## Discrepancies and non-mappings (sprint brief vs. implemented rules)

1. **"Aged checked-out keys" tiers ≠ task tiers.** Only ≥3 days
   creates a task and only ≥25 days creates a recommendation; the
   other scale labels are display buckets. Asserted as implemented.
2. **`cancelled`/`superseded` unreachable via product paths** — see
   family P. Kept out of the standing seed by design.
3. **"MDD present" cannot be modeled** — MDD supplies only a
   not-paired exception list; absence from it is silence, never
   "paired" (DECISION_FRAMEWORK.md). Baseline vehicles simply have no
   MDD row.
4. **`investigate_checked_out_key` has no Reality-discharge** and a
   stale `install_recovr_device` is not retroactively downgraded if a
   key later goes Out — documented limitations in
   `sync/reconciler.py`; the seed does not fabricate discharges for
   them.
5. **QA-CONFLICT-002 re-fires** on every replay of the contradictory
   export — the known, accepted dedup limitation, asserted rather than
   hidden.
6. **`event_freshness` is written only by the RapidRecon path**
   (migration 0008 scope); freshness assertions are scoped accordingly.
