# DealerDOH Ingestion Architecture — Report Classification & Pre-Sync Validation

**Established Sprint 10 (Rail D — Inventory Ingestion Safety,
REQUIRED for `v1.1.0-beta.1`).** This is the canonical description of
the boundary between external dealership reports and the
synchronization engine. Code of record: `sync/report_contracts.py`
(the contract registry), `sync/report_classifier.py` (deterministic
classification), `sync/ingestion.py` (validation, severity,
baselines, fingerprints), `api/routers/inventory_sync.py` (the two
endpoints). Where this document and that code disagree, the code and
its tests win — fix the document.

## 1. The problem this layer exists for

A parser successfully reading a spreadsheet proves nothing about the
spreadsheet. A Tekion export generated with no vehicles selected, a
Keyper file dropped in the wrong slot, a truncated download, a
multi-store umbrella export — before Sprint 10, any of these could
become a `complete` SyncRun, overwrite the day's operational report
CSVs, and silently under-generate the day's work. The reconciliation
engine itself was never the danger (it is presence-driven and never
treats absence as evidence — see §7); the danger was the boundary
treating "parsed" as "true."

Two canonical product rules govern everything here:

> **Missing evidence ≠ zero.** (pre-existing, preserved)
> **Invalid evidence ≠ valid zero.** (Sprint 10)

## 2. One boundary, every acquisition path

```text
Manual Upload ─────┐
                   │
Scheduled Email ───┼──→ Classification → Validation → Sanity checks
(conditional, 6.2) │         ↓
Vendor API ────────┘   Accept / Needs-review / Reject
                             ↓ (accepted evidence only)
                         Sync Engine (unchanged)
```

`sync/ingestion.py::validate_report_set()` is the single entry point.
`POST /inventory-sync/validate` calls it to build the operator
preview; `POST /inventory-sync/run` calls it AGAIN before any
mutation. The preview is UX; the run-time revalidation is the
invariant. **Standing architectural rule:** any future acquisition
mechanism (scheduled email attachments, vendor APIs, import agents)
routes through this same function. Building a second validation path
is an architecture violation, not a shortcut
(V1_1_RELEASE_READINESS §6.2 records the same rule from the release
side).

**Future unattended-ingestion rule (documented now, enforced when
that path exists):** a report producing a WARNING defaults to
**HOLD** for human review. Automation never auto-acknowledges.

## 3. Report contracts (the registry)

One `ReportContract` per report type DealerDOH recognizes — vendor,
report type, ingestion mode, required columns, identifying signature
columns, VIN semantics, duplicate semantics, zero-row policy. Column
facts come exclusively from real importers and fixtures; the registry
invents nothing.

| Contract | Vendor / report | Slot | Mode | Supported | Zero rows | Distinctive structural evidence |
|---|---|---|---|---|---|---|
| `tekion_current_inventory` | Tekion — Current (Unsold) Inventory | `tekion` | authoritative_snapshot | yes | **reject** | `Stock #`, `VIN #`, `Stocked In Date` |
| `tekion_sold_inventory` | Tekion — Sold Inventory | `sold` | historical_snapshot | yes | **reject** | `Stock #`, `VIN #`, `Sold Date` |
| `keyper_full_inventory` | Keyper — Full Key Inventory | `keyper` | authoritative_snapshot | yes | **reject** | `name`, `System`, `Checkout Date` |
| `keyper_key_event` | Keyper — Key Event Report | — | incremental_event | **no** | n/a (undecided — real vendor semantics unknown) | **none recorded — no sample exists** (see §6) |
| `mdd_not_paired` | MDD — Not Paired exception list | `mdd` | exception_snapshot | yes | **warning + acknowledgement** | `vin`, `stock`, `Dealership` (lowercase IS evidence) |
| `recovr_device_state` | RecovR — Device/Pairing State | `recovr` | authoritative_snapshot | yes | **reject** | `VIN`, `Stock Number`, `Paired` |
| `rapidrecon_recon_status` | RapidRecon — Reconditioning Status | `rapidrecon` | contextual_snapshot | yes | **warning + acknowledgement** | `VIN`, `Step` |

Zero-row rationale (the per-contract decision Sprint 10 records): a
car lot, a key cabinet, a deployed device fleet, and a sold-report
window are never genuinely empty — an empty export of those is an
export mistake, hard-rejected with a message naming the likely cause.
An empty MDD *exception* list ("nothing unpaired") or an empty recon
board is plausible-but-suspicious — processed only after explicit
human acknowledgement, and the acknowledged zero is then recorded
honestly as a zero.

Ingestion modes carry the evidence semantics (§7): only
`authoritative_snapshot` may ever let absence mean something;
`incremental_event` absence means **nothing**; `historical_snapshot`
rows assert history; `exception_snapshot`/`contextual_snapshot`
enrich without originating identity.

## 4. Classification (deterministic, content-based)

`classify_headers()` identifies a file by the columns it actually
carries — never by filename, upload-slot label, or browser MIME type
(hints at best; the slot expresses *intent*, the content decides
*identity*). A contract matches when its full signature-column set is
present. Exactly one match → classified. More than one →
`AMBIGUOUS_REPORT_TYPE`, rejected (never guessed — with today's
registry that requires a file carrying both Tekion date columns,
which no real export does). No full match but ≥2 of one vendor's
signature columns → a recognized vendor *variant*,
`REPORT_VARIANT_UNSUPPORTED`. Nothing → `UNRECOGNIZED_REPORT`.

Wrong-slot protection falls out directly: detected contract ≠ the
slot's expected contract → `WRONG_REPORT_TYPE`, with both names in
the message ("Expected the Tekion Current (Unsold) Inventory report,
but this file's columns identify it as the Tekion Sold Inventory
report…"). There is no silent reinterpretation into the other slot —
by design decision, not omission.

Deliberate tightening recorded here: the RapidRecon slot previously
required only a `VIN` column, which let ANY VIN-bearing file (a
RecovR export, for instance) ingest as RapidRecon observations.
Recognition now requires RapidRecon's own evidence (`VIN` + `Step`,
both present in every real export and fixture). Ingestion
requirements are unchanged (`VIN` alone remains the only *required*
column; all other RapidRecon reads stay guarded).

## 5. Validation pipeline, severities, codes

Per file, in order (each stage only reached if the prior passed):

1. **File safety** — size cap (20 MB; the router stops writing at
   cap+1 bytes so hostile bodies never land), zero-byte check, Excel/
   ZIP/OLE2 magic-byte detection (CSV is the only ingested format —
   deliberately not broadened), UTF-8 decodability, BOM detection,
   duplicate-header detection, 50,000-row cap. Validation reads with
   the same parser posture as the engine's importers so its
   acceptance is always a SUBSET of the engine's — validation may
   reject what the engine could parse, never the reverse.
2. **Classification + wrong-slot** (§4).
3. **Structural** — every required column present, else
   `MISSING_REQUIRED_COLUMN` naming the missing fields.
4. **Zero-data** — per-contract policy (§3).
5. **Row-level** — see the recorded VIN decision below.
6. **Duplicates** — per-contract semantics (below).
7. **Comparable baseline / count sanity** (§8).

Severity model: **ERROR** (cannot process; request rejected; zero
mutation) / **WARNING** (potentially valid but suspicious; explicit
acknowledgement required) / **INFO** (context; never blocks). Stable
codes, dealership-language messages, never raw parser text:
`EMPTY_FILE`, `FILE_TOO_LARGE`, `UNSUPPORTED_FORMAT`,
`UNREADABLE_FILE`, `TOO_MANY_ROWS`, `DUPLICATE_HEADER`,
`WRONG_REPORT_TYPE`, `AMBIGUOUS_REPORT_TYPE`,
`REPORT_VARIANT_UNSUPPORTED`, `UNRECOGNIZED_REPORT`,
`MISSING_REQUIRED_COLUMN`, `NO_DATA_ROWS`, `MISSING_VINS`,
`MALFORMED_VINS`, `DUPLICATE_ROWS`, `DUPLICATE_VINS`,
`DUPLICATE_IDENTIFIERS`, `SUSPICIOUS_COUNT_DROP`,
`SUSPICIOUS_COUNT_INCREASE`, `NO_PRIOR_BASELINE`.

**Recorded decision — invalid VIN/record shape (Rail D exit 5,
"reject-row vs quarantine-file: decide once"):** the file is the unit
of evidence; rows are never silently dropped and uploaded files are
never edited. Where rows originate Vehicle identity (both Tekion
reports — their VINs become the `vehicle` table's primary key), a
blank VIN is corrupting and **rejects the file** (`MISSING_VINS`,
error, offending file lines named). Present-but-malformed VINs there
warn (`MALFORMED_VINS`) — a typo'd real vehicle is surfaced, not
blocked. Sources that never originate identity (RecovR, MDD,
RapidRecon — their bad VINs are inert downstream by the engine's own
"weaker source can't originate identity" design) warn only. Keyper
has no VIN column; unresolvable key identifiers are the
PendingIdentity machinery's designed input, not invalid evidence.

**Recorded decision — duplicates (Rail D exit 6):** duplicates are
surfaced as WARNINGS with counts and sample identifiers, never
silently deduplicated and never silently processed. Per contract:
duplicate VINs in a *current* snapshot are contradictory claims →
`DUPLICATE_VINS`; VIN repeats in the *sold* report are legitimate
history (same vehicle sold twice under different stock numbers — the
existing `tekion_sync_conflicts` machinery owns that question
downstream) and only exact duplicate rows are flagged; Keyper
duplicate key names, RecovR/MDD/RapidRecon duplicate VINs →
warnings. True event history is never deduplicated merely because an
identifier repeats.

## 6. Keyper: Full Inventory vs Event Report

The one place the architecture deliberately models a report it cannot
ingest. **No sample of the Keyper Event Report exists in this
repository, so its schema is deliberately not recorded and not
invented** — `KEYPER_KEY_EVENT` carries zero column facts. What is
built and tested instead is the boundary itself:

- The registry names the concept with `ingestion_mode:
  incremental_event` and `supported: false`.
- A Keyper-like file that is not the Full Inventory contract is
  rejected as `REPORT_VARIANT_UNSUPPORTED` with the honest message:
  if this is a Keyper Event/history export, that report type is not
  yet supported **and can never substitute for the full inventory
  snapshot**.
- Tests pin that such a file is rejected in *every* slot
  (`tests/test_ingestion_validation.py::KeyperEventBoundaryTest`),
  using an explicitly-labeled synthetic stand-in fixture — see
  `tests/fixtures/ingestion/README.md`.

**What this evidence does and does not prove (owner-corrected status,
2026-08-16):**

| Claim | Status |
|---|---|
| The known Keyper Full Inventory contract classifies and ingests correctly | **PASS** |
| Unsupported/nonmatching Keyper-shaped evidence fails safely (rejected, named, never a snapshot) | **PASS** |
| A *real* Keyper Event Report is structurally distinguishable from Full Inventory by the current classifier | **PENDING VENDOR EVIDENCE** |
| Keyper Event ingestion | Unsupported — not required for v1.1 |

The stand-in proves the rejection boundary for evidence that does
NOT match the Full contract. It cannot prove the converse: a real
Event report could plausibly carry `name`, `System`, and a checkout
timestamp — and if a real Event export happens to satisfy the Full
signature, the current content classifier would accept it as a Full
snapshot. That residual risk predates Sprint 10 (before it, ANY
column-superset file passed); Sprint 10 narrows it (nonmatching
variants are now rejected) but **cannot close it without the real
vendor format — do not invent one to close it.** Until vendor
evidence arrives, the real Full-vs-Event structural distinction is
explicitly PENDING VENDOR EVIDENCE, the keyper slot remains a
manual, operator-selected upload, and no Keyper acquisition may be
automated (V1_1_RELEASE_READINESS §6.2 gates that on discovery
regardless).

**Remaining trigger:** vendor discovery
(V1_1_RELEASE_READINESS §6.2, owner action). When the real format
arrives: give `KEYPER_KEY_EVENT` its real columns from the real
sample, re-verify the Full classifier's signature actually
discriminates against it (adding discriminating columns if the real
formats overlap), decide its zero-event semantics from real vendor
meaning (a zero-event window may be a *valid* empty event set —
undecidable until then), flip `supported` only with an ingestion
path that processes represented events exclusively, and never lets
absence imply anything. The snapshot/event distinction is already
priced into the architecture; supporting the report is
contract-filling, not redesign.

## 7. What accepted evidence means (source semantics, unchanged)

Validation feeds the existing reconciliation engine; it does not
replace or alter its semantics (Rail D exit 9: the standing
QA-dealership regression passes untouched, both engines). The
engine's own properties, verified during the Sprint 10 audit and
worth stating as load-bearing:

- **Presence-driven, never absence-driven.** Events are
  diff-before-write observations; the only automatic task discharge
  (mooting install tasks) fires on a *positive* `tekion_sold` event,
  never on a vehicle missing from a file. A vehicle absent from an
  upload simply receives no fresh observation.
- **Missing source ≠ zero.** A source not uploaded produces no
  SyncRun row and no zero-claim; Keyper's absence skips
  RecovR-dependent task generation *with a warning in the summary*
  (`generate_install_tasks`' None-vs-empty contract). Unchanged, and
  pinned by API-level test.
- The engine therefore distinguishes, end to end: **valid data** /
  **valid-and-acknowledged empty** (a human confirmed the zero; the
  run records 0 honestly) / **invalid** (rejected; nothing recorded)
  / **missing** (not supplied; skip + warn, no claim) /
  **unsupported** (rejected at classification; nothing recorded).

## 8. Comparable baselines & the suspicious-count policy

`report_baseline` (migration 0010) records each accepted report's
row counts per executed sync — written by `/run` only *after* the
sync succeeds, keyed `(vendor, report_type)`. Validation READS the
newest comparable row: a Tekion sold baseline can never judge a
Tekion current file, and Keyper full evidence could never be compared
against a future Keyper event report. No comparable history → `No
prior baseline` (INFO), never a blocker. (This is why
`sync_run.records_processed` was not reused: the `tekion` SyncRun
deliberately covers both Tekion report types in one number, and
SyncRun's governed meaning was not stretched.)

**Suspicious-count thresholds — OWNER-RATIFIED 2026-08-16 (Sprint 10
PR #14 gate) as the initial beta policy, explicitly subject to tuning
from real operational evidence.** They are warning/review thresholds,
never hard rejection: a triggered condition requires explicit
Manager/Admin acknowledgement, and future unattended ingestion must
HOLD on it. (No governed threshold pre-existed anywhere in docs,
config, or code — audited 2026-08-16; these numbers were proposed by
Sprint 10 and ratified by the owner at the gate.)

| Condition | Ratified beta default | Grounding |
|---|---|---|
| Drop vs previous comparable | WARN when drop > **15%** AND ≥ **10 rows** | Catches the register's own catastrophic example (987→14 = −98%) with wide margin; day-over-day drift from tens of sales against hundreds-to-thousands of rows stays inside ±15%; the absolute floor keeps small sources (e.g. a 40-row MDD list dropping 9) from nagging |
| Increase vs previous comparable | WARN when increase > **50%** AND ≥ **25 rows** | The real observed failure shape: the multi-brand RecovR "umbrella" export (importers/recovr.py's `MARK_AUTO` exclusion is the evidence) roughly doubles the store-specific count when uploaded by mistake |
| Zero rows | Not a threshold question | Already a hard per-contract policy (§3) before any comparison runs |

Behavior: a triggered condition is a WARNING — visible in the
preview with both counts and the delta, requiring acknowledgement,
never silent processing and never silent rejection. Constants:
`sync/ingestion.py` (`SUSPICIOUS_DROP_PCT`, `SUSPICIOUS_DROP_MIN_ROWS`,
`SUSPICIOUS_INCREASE_PCT`, `SUSPICIOUS_INCREASE_MIN_ROWS`).
Boundary-exact tests pin all four numbers, so a future tuning from
operational evidence is a constants-plus-tests edit plus a recorded
owner decision, not a design change.

## 9. The acknowledgement contract (why a client cannot lie)

Everything the gate depends on is server-derived from the uploaded
bytes:

- `/run` recomputes classification, validation, and baselines itself
  on every request. Skipping `/validate` skips nothing.
- Errors always reject (422 `REPORT_VALIDATION_FAILED`), zero
  mutation — no SyncRun, no Vehicle/Event, no task, no
  recommendation, no report CSVs, no baseline row (API-test-pinned).
- Warnings require `acknowledge_warnings=true` **and**
  `validation_fingerprint` equal to the SHA-256-derived fingerprint
  of the exact bytes `/run` just received (409
  `WARNINGS_NOT_ACKNOWLEDGED` / `STALE_VALIDATION` otherwise). You
  cannot acknowledge what you never previewed: the fingerprint only
  exists in a `/validate` response for those bytes. Swapping a file
  after previewing changes the fingerprint and fails closed.
- The frontend never pre-checks the acknowledgement box — and a
  fabricated one wouldn't matter, per the above.
- Role gate: `/validate` and `/run` both require admin/manager
  (Sprint 05's `SYNC_RUN_ROLES`), negative-tested for every role.

## 10. Manual preview flow (the operator's view)

```text
Select reports → Validate Reports → per-report preview
  (detected type · records/valid/invalid/duplicates · previous
   comparable + change · issues at severity)
→ resolve rejections (re-export, right file, right slot)
→ tick acknowledgement if warnings
→ Run Sync (header button enables only now)
→ existing engine, then baselines recorded
```

Changing any selected file clears the preview and the acknowledgement
immediately (and the server would reject the stale fingerprint
anyway). A runtime failure *after* validation reports in dealership
language with per-source transactional integrity — completed sources
keep their committed results and say so in Recent Sync Runs; the
failing source rolled back and is marked failed; no half-success
banner (the "no partial mutation" guarantee is scoped to validation
failures, which reject before anything runs).

## 11. Operator troubleshooting

| Symptom | Meaning | Fix |
|---|---|---|
| "Wrong report type" | The file's columns identify a different report than the slot expects | Upload it in the named slot, or export the intended report |
| "No vehicle records were found…" | Headers-only/empty export — the classic no-vehicles-selected Tekion mistake | Re-export with records selected; DealerDOH will not treat it as "zero vehicles" |
| "…looks like a Keyper export, but not the Full Key Inventory report" | Likely a Keyper Event/history export | Export the Full Key Inventory report; the Event report is not yet supported (§6) |
| "…required column(s) missing" | Incomplete/modified export | Re-export without customizing columns |
| "…byte-order mark (BOM)" / "…looks like an Excel workbook" | Wrong save format | Save/export as standard CSV (UTF-8, no BOM) |
| "rows vs … in the previous comparable report" warning | Count moved past the §8 thresholds | Verify the export is complete and store-scoped; acknowledge only if reality actually changed |
| Warning box must be ticked every time | By design — acknowledgements bind to the exact previewed bytes and never persist | Review, tick, run |

## 12. Boundary exclusions (recorded, not accidental)

- **`main.py` (CLI)** predates the API and bypasses this boundary.
  It is a developer/operator tool that reads the local
  `data/uploads/` folder, not a deployed surface; the deployed
  product's only ingestion path is the API. Folding the CLI into the
  boundary (or retiring it) is deliberately left for a future
  decision — do not treat its existence as a second sanctioned
  ingestion path.
- **Telemetry**: validation produces exactly the operational states
  Rail F/G will instrument (validated / rejected / needs-review /
  sync started / failed) but emits no telemetry itself — Sprint 11's
  job, not improvised here.
- **Notifications**: CONDITIONAL rail; the manual flow's immediate
  feedback is the v1.1 answer. The unattended-HOLD rule (§2) is the
  seam notifications would build on.
