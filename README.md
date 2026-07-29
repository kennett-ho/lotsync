# LotSync OMS

LotSync compares your dealership's key-tracking system (Keyper), DMS
inventory (Tekion), GPS tracking (RecovR), beacon tracking (MDD), and
reconditioning workflow (RapidRecon) against each other, and produces a
set of reports telling you where they disagree. It does not change
anything in any of those systems -- it only reads exports from them and
tells you what to look into.

The reconciliation engine described below (`reconcile.py`'s original
CLI workflow, now `main.py`) is still exactly how it's always worked --
nothing about it changed. As of Phase 3, there are now two ways to run
it: the original CLI script, reading files from a folder on disk, or
the web application (FastAPI backend + React frontend) described in
"Running LotSync" immediately below, which is the real day-to-day path
for a dealership employee going forward -- upload reports through a
browser, no folder or file-naming convention to manage by hand. Both
paths call the exact same reconciliation code; neither is more
authoritative than the other.

## Running LotSync

### Backend (FastAPI)

```
cd lotsync
PYTHONPATH=.. python -m pip install fastapi uvicorn python-multipart
PYTHONPATH=.. uvicorn lotsync.api.app:app --reload
```

Serves at `http://localhost:8000` by default; interactive docs at
`/docs`. See [`api/README.md`](api/README.md) for the full route list
and testing instructions.

### Frontend (React + Vite)

```
cd lotsync/frontend
npm install
npm run dev
```

Serves at `http://localhost:8443` (or `5173` outside this project's own
dev-container setup) and calls the backend at `http://localhost:8000` by
default -- override via a `.env.local` file's `VITE_API_BASE_URL` if
your backend runs elsewhere (see `frontend/src/api/client.ts`).

### Inventory Sync (the real day-to-day workflow)

With both servers running, open the frontend and go to **Inventory
Sync** in the sidebar. Upload the same six reports the CLI workflow
below reads from disk -- Tekion Unsold Inventory, Tekion Sold Inventory,
Keyper, MDD, RecovR, and RapidRecon -- through the six labeled upload
slots (any subset is accepted; Tekion Unsold and Tekion Sold are
independent slots, not one combined upload), then **Run Sync Now**.
This runs the exact same reconciliation engine as the CLI path, persists
the results to SQLite, and still writes the eight CSV reports described
under "The reports" below to the same output location -- no manual
database seeding, no CLI invocation required. See
[`PHASE_3_SPRINT_4_REVIEW.md`](PHASE_3_SPRINT_4_REVIEW.md) for exactly
how partial uploads (e.g. Tekion Unsold only) are handled.

### Developer workflow

```
cd lotsync
PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"
```

Run this after any change to `sync/`, `rules/`, `database/`, `queries/`,
or `api/` -- see [`tests/README.md`](tests/README.md) for what's
covered. No frontend test runner exists yet (a standing, named gap --
see `PHASE_3_SPRINT_4_REVIEW.md`'s recommendations); frontend changes
are verified manually, in-browser.

## Before you run it (CLI workflow)

Every time you run this, you need five files in the same folder as
the exports:

| File | Where it comes from |
|---|---|
| `All_Keys_Keyper.csv` | Keyper, full key export |
| `Tekion_Master_List.csv` | Tekion, current stocked-in inventory |
| `Tekion_Sold.csv` | Tekion, sold vehicle report |
| `Not_Paired_-_MDD_Locate.csv` | MDD, "not paired" report |
| `RecovR_List.csv` | RecovR, full vehicle list |

Plus `oms_config.xlsx`, described below.

## Configuration -- `oms_config.xlsx`

Everything you'd need to change day-to-day lives in this workbook, not
in the Python code. You should never need to open or edit the `.py`
file itself to keep this running correctly.

**Settings sheet**
- **Store Name**: must exactly match the "Dealer Name" value in your
  Tekion exports and the "Dealership" value in MDD exports (currently
  `Mark Kia`). If you ever run this for a different store, this is
  the one cell to change.
- **Sync Date**: leave this blank in normal use -- the script will use
  today's date automatically. Only fill this in if you're re-running
  the script against older, saved export files and want the "days
  out" calculations to reflect when those exports were actually
  pulled, not today.

**Excluded VINs sheet**
Vehicles that are dealership-owned/employee-use but got stocked into
Tekion like sale inventory (so they'd otherwise show up incorrectly on
the tracker-install and investigate reports). Add one row per vehicle:
VIN, a description, why it's excluded, and the date you added it.
Delete the example row before adding real entries -- but if you forget,
the script skips it automatically since its Reason column starts with
"Example."

**Key Out Aging Buckets sheet**
Controls the labels on the Key Out Aging report (see below). Each row
is a minimum number of days a key has been checked "Out," and the
label that applies starting at that many days. Rows must stay sorted
by Minimum Days Out, ascending -- the script assumes each label applies
up to (not including) the next row's minimum. The shipped scale was
adjusted slightly from what was originally sketched out, because the
original had overlapping day ranges (e.g. "3-7" then "7-14" both
included day 7) -- these were tightened so each day falls in exactly
one bucket.

**Incoming Missing Buckets sheet**
Controls the priority label for **Trade/Other** vehicles on the
Incoming/Missing Investigate report -- vehicles presumed already
physically on the lot, based on days since Stocked In in Tekion with
no Keyper key ever created. Grounded in the real lot workflow: fresh
trades are checked every morning and stocked into Keyper by midshift,
normally within 2 days. Same sorted-ascending, non-overlapping-tier
rule as the other bucket sheets applies here too.

**New Car Buckets sheet**
Controls the priority label for **New Car (Awaiting Dropoff)**
vehicles on the same report -- stock numbers that are a bare "K"
followed only by digits (e.g. K30707), which are factory orders
Stocked In before they physically arrive. No Keyper key is expected
until transport drops the vehicle off, so this uses a longer default
window (7 days) than the trade-vehicle scale. Same sorting rule
applies.

## How to run it

From a terminal, in the folder with the script and all the CSV/xlsx
files:

```
python3 reconcile.py
```

It prints a summary to the screen and writes eight report files into
an `outputs` folder (or wherever `OUT_DIR` at the top of the script
points -- the only path you'd need to touch in the code itself, if you
ever move where files are read from or written to).

## The reports

| File | What it means |
|---|---|
| `fully_verified_report.csv` | Key is checked "In" at Keyper and matches an active Tekion vehicle. No action needed. |
| `key_out_aging_report.csv` | Key is checked "Out" and matches an active Tekion vehicle, labeled by how many days it's been out (see Key Out Aging Buckets above). |
| `flag_to_controller_report.csv` | Keyper has a key, but there's no matching vehicle in Tekion at all. Usually means the vehicle needs to be stocked into Tekion, but also catches vehicles that were sold with the key never removed from Keyper. |
| `incoming_or_missing_investigate_report.csv` | Tekion shows an active vehicle, but there's no key for it in Keyper at all. Split into three vehicle types with different expected timelines, based on stock number: **New Car (Awaiting Dropoff)** -- a bare "K" plus digits only (e.g. K30707), a factory order Stocked In before physically arriving, so no key is expected yet; **New (Damaged - In Repair)** -- stock number ends in "DM," a new vehicle that arrived damaged and is in or awaiting repair; physically present but not lot-ready, so neither other scale's assumptions fit it -- no priority bucket is applied here yet, since there's no confirmed typical repair duration to ground one against; and **Trade/Other** -- everything else (KB, KT, K####A, K####SL, etc.), a vehicle presumably already on the lot. Model year is deliberately not used to tell these apart, since current-model-year vehicles also come in as trade-ins. There's also a fourth possibility this report can't distinguish from an overdue Trade/Other case: a vehicle that was sold, never marked sold in Tekion, and had its key deleted from Keyper once the fob went out the door -- invisible to the Sold-report cross-check, since an unrecorded sale never makes it into that report either. |
| `sold_vehicles_report.csv` | Every sold vehicle, flagged `needs_removal` if a key is still in Keyper and/or RecovR still shows it Paired. Includes `days_since_sale` -- useful for prioritizing when the Sold report covers a wide date range: a vehicle sold last week still showing a key is routine pipeline lag, one sold a year ago is a genuine, probably-forgotten orphan. Note: MDD can't be checked here -- only MDD's "not paired" list is available, not a full list of what's currently paired, so there's no way to confirm a sold car's beacon was actually removed. **Operational note:** an initial one-time sweep used a full historical Sold export (2020–present, ~34K rows) specifically to catch years of accumulated orphaned records; going forward, the Sold report used in normal syncs is year-to-date, not full history. |
| `tracker_install_tasks.csv` | Vehicles missing an MDD beacon or a RecovR device, already filtered to exclude vehicles that are actually sold or belong to a different store. |
| `tekion_sync_conflicts.csv` | Contradictions inside Tekion's own two exports -- a VIN marked "Sold" in one report and "Stocked In" in the other, or the same VIN sold twice under different stock numbers. Not a Keyper problem; this needs someone who manages Tekion data, not lot staff. |
| `data_quality_exceptions.csv` | Identifiers that couldn't be confidently classified or matched at all -- mostly Tekion's own auto-generated placeholder stock numbers, which need to be corrected/renamed in Tekion directly. |

## Known limitations (not bugs -- just what this version doesn't do yet)

- **No memory between runs, from the reports' point of view.** Every
  report above is still recomputed fresh from that run's exports --
  none of them read from persisted history. (Internally, as of Phase 2
  Slice 1, a local SQLite database has begun tracking a subset of this
  each run -- Keyper only, so far -- but this is not yet surfaced in
  any report and doesn't change anything described in this file. See
  `IMPLEMENTATION_PLAN.md` if you're curious where this is headed.)
  There's still no tracking of "this vehicle has shown up in
  flag_to_controller for 3 syncs in a row" from a report-reading
  perspective -- each report reflects only the moment the exports were
  pulled.
- **MDD's full assignment list isn't available**, only its "not
  paired" export -- so the sold-vehicle report can't confirm MDD
  beacon removal, only flag it as unknown.

## Why some of the matching logic looks the way it does

If you're modifying this script, a few non-obvious things are worth
knowing before you change them:

- **Keyper has no VIN column.** Its "name" field is either a Tekion
  stock number or the last 6 digits of a VIN (used when a car hasn't
  been stocked into Tekion yet), and the script has to infer which
  from the shape of the value.
- **Keyper's "System" field is not a reliable store/brand indicator**,
  even though it looks like one. Real data showed Kia-prefixed stock
  numbers filed under Mitsubishi/Mazda systems about a quarter of the
  time -- it reflects which physical cabinet a key sits in, not which
  store owns the vehicle. Store scoping is done by stock-number prefix
  instead.
- **Tekion's "Age (Days)" field doesn't reliably mean "days since
  stocked in."** It diverges from what the Stocked In Date implies on
  about 10% of rows, sometimes by hundreds of days. The script computes
  age from Stocked In Date directly rather than trusting that field.
