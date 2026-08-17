"""
Sprint 10 (Rail D, Inventory Ingestion Safety) -- the canonical report
contract registry. One entry per report type DealerDOH knows how to
recognize, whether or not it can ingest it yet.

A ReportContract answers, per report type: who produces it, what kind
of evidence it is (snapshot vs event vs exception list), what columns
it must carry, what columns identify it, what a zero-row file means,
and what constitutes a duplicate. Every ingestion path -- today's
manual upload, any future scheduled-email or vendor-API acquisition --
classifies and validates against THIS registry (V1_1_RELEASE_READINESS
5.D: "one classification/validation boundary that all ingestion paths
converge on"). Do not add a second column-requirements table anywhere;
sync/upload_validation.py's REQUIRED_COLUMNS moved here and that
module was retired in the same change.

Column facts below are taken from the real importers and fixtures
(importers/*.py, tests/fixtures/synthetic/*.csv, sync/pipeline.py's
_EMPTY_COLUMNS) -- not from vendor documentation we don't have. The
one deliberately unsupported entry, Keyper's Key Event report, has NO
column facts at all because no real sample exists in this repository;
see KEYPER_KEY_EVENT below for what that entry is for.

Ingestion modes (only categories the current product actually has):

- authoritative_snapshot: "the complete current state from this
  source" -- absence semantics MAY apply per existing engine rules
  once validated (Tekion current inventory, Keyper full inventory,
  RecovR full device list).
- historical_snapshot: a window of past facts (Tekion sold report).
  Rows assert history; absence of a vehicle asserts nothing.
- exception_snapshot: the source's own pre-filtered exception list
  (MDD "Not Paired"). A row is an exception claim; an empty list is
  plausibly legitimate ("no exceptions right now").
- contextual_snapshot: multi-store/contextual enrichment feed
  (RapidRecon). Never originates vehicle identity.
- incremental_event: "these specific changes occurred" -- absence of
  a vehicle means NOTHING about that vehicle, and such a report can
  never satisfy a snapshot evidence requirement. No supported
  contract uses this mode yet; it exists so the Keyper Event report
  (vendor discovery pending, V1_1_RELEASE_READINESS 6.2) lands in an
  architecture that already refuses to confuse it with a snapshot.

Zero-row policy (per-contract, decided Sprint 10 -- see
INGESTION_ARCHITECTURE.md for the full rationale table):

- "error": a zero-row file is invalid evidence, hard-rejected. All
  snapshot-class reports from sources that always have records at
  this dealership (Tekion current: a car lot is never empty; Tekion
  sold: the export window always contains sales; Keyper full: the key
  cabinet is never empty; RecovR: the store always has devices
  deployed). "Invalid evidence != valid zero."
- "warning": zero rows is plausible but suspicious enough to require
  explicit human confirmation before processing (MDD not-paired: an
  empty exception list could genuinely mean "every vehicle is
  paired"; RapidRecon: an empty recon board is conceivable). The
  warning-acknowledgement flow in sync/ingestion.py enforces the
  confirmation.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportContract:
    contract_id: str          # stable identifier, e.g. "tekion_current_inventory"
    vendor: str               # source system key, e.g. "tekion"
    vendor_label: str         # human name, e.g. "Tekion"
    report_type: str          # e.g. "current_inventory"
    report_label: str         # human name, e.g. "Current (Unsold) Inventory"
    ingestion_mode: str       # one of the modes documented above
    slot: str                 # upload-slot key this contract is accepted in ("" = none)
    supported: bool           # False = recognized concept, no ingestion path
    # Columns the slot's importer/reconciler actually read by name --
    # absence is a hard MISSING_REQUIRED_COLUMN error. (The successor
    # of upload_validation.REQUIRED_COLUMNS, same evidence base.)
    required_columns: tuple = ()
    # The minimal distinctive column set that identifies this report
    # type during classification. May be smaller than required_columns
    # (identity needs less than ingestion) or carry columns that are
    # not individually required (RapidRecon's "Step": optional to the
    # guarded reconciler reads, but a bare VIN-only file is not
    # recognizable AS RapidRecon -- that anonymity is exactly the
    # wrong-report hole Sprint 10 closes).
    signature_columns: tuple = ()
    # Column holding a full 17-char VIN where the contract has one
    # ("" = no VIN column; Keyper identifies by key name).
    vin_column: str = ""
    # Whether a null/blank value in vin_column corrupts identity
    # downstream (Tekion current/sold rows become the Vehicle table's
    # primary key -- a blank VIN there is a hard error; RecovR/MDD/
    # RapidRecon never originate identity, so their bad VINs are
    # surfaced as warnings and stay inert downstream).
    vin_required_per_row: bool = False
    # Column whose duplication within one file is worth surfacing
    # ("" = only exact duplicate rows are checked). Severity is always
    # WARNING -- a duplicate identifier is a real-world contradiction
    # the product exists to surface to humans, not to silently block
    # (the Tekion sold report legitimately repeats a VIN when a
    # vehicle was sold twice under different stock numbers -- see
    # rules/validation.py's duplicate_sold_vin conflict machinery).
    duplicate_key_column: str = ""
    zero_row_policy: str = "error"      # "error" | "warning"
    zero_row_message: str = ""
    columns_note: str = ""              # provenance note for the registry table


# Upload-slot key -> slot label, exactly the six slots the Inventory
# Sync page has always had (labels match sync/upload_validation.py's
# retired SLOT_LABELS verbatim).
SLOT_LABELS = {
    "tekion": "Tekion Unsold Inventory",
    "sold": "Tekion Sold Inventory",
    "keyper": "Keyper",
    "mdd": "MDD",
    "recovr": "RecovR",
    "rapidrecon": "RapidRecon",
}


TEKION_CURRENT = ReportContract(
    contract_id="tekion_current_inventory",
    vendor="tekion", vendor_label="Tekion",
    report_type="current_inventory", report_label="Current (Unsold) Inventory",
    ingestion_mode="authoritative_snapshot",
    slot="tekion", supported=True,
    required_columns=("Stock #", "VIN #", "Status", "Stocked In Date", "Year Make Model"),
    signature_columns=("Stock #", "VIN #", "Stocked In Date"),
    vin_column="VIN #", vin_required_per_row=True,
    duplicate_key_column="VIN #",
    zero_row_policy="error",
    zero_row_message=(
        "No vehicle records were found in the Tekion current-inventory report. "
        "Verify that vehicles were selected when generating this report, then "
        "export it again. DealerDOH will not treat an empty export as \"the "
        "lot has zero vehicles.\""
    ),
    columns_note="importers/tekion.py + fixtures/synthetic/tekion_master.csv",
)

TEKION_SOLD = ReportContract(
    contract_id="tekion_sold_inventory",
    vendor="tekion", vendor_label="Tekion",
    report_type="sold_inventory", report_label="Sold Inventory",
    ingestion_mode="historical_snapshot",
    slot="sold", supported=True,
    required_columns=("Stock #", "VIN #", "Status", "Sold Date", "Year Make Model"),
    signature_columns=("Stock #", "VIN #", "Sold Date"),
    vin_column="VIN #", vin_required_per_row=True,
    # Duplicate VINs are legitimate sold history (same vehicle sold
    # twice under different stock numbers) -- only exact duplicate
    # rows are flagged, per the registry-level duplicate policy note.
    duplicate_key_column="",
    zero_row_policy="error",
    zero_row_message=(
        "No sold-vehicle records were found in the Tekion sold report. Verify "
        "the date range and filters used when generating the export, then "
        "export it again."
    ),
    columns_note="importers/sold.py + fixtures/synthetic/tekion_sold.csv",
)

KEYPER_FULL = ReportContract(
    contract_id="keyper_full_inventory",
    vendor="keyper", vendor_label="Keyper",
    report_type="full_inventory", report_label="Full Key Inventory",
    ingestion_mode="authoritative_snapshot",
    slot="keyper", supported=True,
    required_columns=("name", "Status", "System", "Checkout Date"),
    signature_columns=("name", "System", "Checkout Date"),
    vin_column="",  # Keyper identifies keys by name; VIN resolution is the reconciler's job
    duplicate_key_column="name",
    zero_row_policy="error",
    zero_row_message=(
        "No key records were found in the Keyper report. The key cabinet is "
        "never empty -- verify the export selection and generate the Full "
        "Inventory report again."
    ),
    columns_note="importers/keyper.py + fixtures/synthetic/keyper.csv",
)

# Recognized concept, deliberately UNSUPPORTED: Keyper's Key Event /
# history report. No real sample of this report exists in this
# repository, so this entry carries NO column facts -- inventing a
# schema here would be exactly the fabricated-vendor-semantics failure
# Sprint 10's brief prohibits. What this entry provides today:
#
# 1. The registry names the concept, so classification can say "a
#    Keyper export that is NOT the Full Inventory report" in real
#    product language (the classifier's keyper-variant path).
# 2. Its ingestion_mode is already "incremental_event", so the moment
#    vendor discovery (V1_1_RELEASE_READINESS 6.2) supplies the real
#    format, supporting it means filling in columns and flipping
#    supported=True.
#
# Evidence status, stated precisely (owner-corrected 2026-08-16):
# what IS proven is that nonmatching Keyper-shaped evidence fails
# safely (tests/test_ingestion_validation.py::KeyperEventBoundaryTest
# pins rejection in every slot). What is NOT proven -- and cannot be
# without the vendor format -- is that a real Event report is
# structurally distinguishable from Full Inventory: a real Event
# export could plausibly carry name/System/Checkout Date and would
# then satisfy the Full signature. PENDING VENDOR EVIDENCE
# (INGESTION_ARCHITECTURE.md section 6); when the real format
# arrives, re-verify the Full signature discriminates and add
# discriminating columns if the real formats overlap.
KEYPER_KEY_EVENT = ReportContract(
    contract_id="keyper_key_event",
    vendor="keyper", vendor_label="Keyper",
    report_type="key_event", report_label="Key Event Report",
    ingestion_mode="incremental_event",
    slot="", supported=False,
    zero_row_message=(
        # Documented for the future contract, unreachable until it is
        # supported: per-vendor semantics for "zero events in the
        # window" are UNKNOWN until a real sample exists, so the safe
        # policy will be decided with the real format, not guessed now.
        ""
    ),
    columns_note="NO SAMPLE EXISTS -- vendor discovery pending (V1_1_RELEASE_READINESS 6.2)",
)

MDD_NOT_PAIRED = ReportContract(
    contract_id="mdd_not_paired",
    vendor="mdd", vendor_label="MDD",
    report_type="not_paired", report_label="Not Paired (Exception List)",
    ingestion_mode="exception_snapshot",
    slot="mdd", supported=True,
    required_columns=("vin", "stock", "year", "make", "model", "Dealership"),
    signature_columns=("vin", "stock", "Dealership"),
    vin_column="vin", vin_required_per_row=False,
    duplicate_key_column="vin",
    zero_row_policy="warning",
    zero_row_message=(
        "The MDD report contains zero records. That could genuinely mean every "
        "vehicle has a paired beacon -- or the export was generated without "
        "selecting any records. Confirm the export is correct before running "
        "the sync."
    ),
    columns_note="importers/mdd.py + fixtures/synthetic/mdd_not_paired.csv",
)

RECOVR_DEVICE_STATE = ReportContract(
    contract_id="recovr_device_state",
    vendor="recovr", vendor_label="RecovR",
    report_type="device_state", report_label="Device / Pairing State",
    ingestion_mode="authoritative_snapshot",
    slot="recovr", supported=True,
    required_columns=("VIN", "Stock Number", "Paired", "Year", "Make", "Model"),
    signature_columns=("VIN", "Stock Number", "Paired"),
    vin_column="VIN", vin_required_per_row=False,
    duplicate_key_column="VIN",
    zero_row_policy="error",
    zero_row_message=(
        "No device records were found in the RecovR report. The store always "
        "has RecovR devices deployed -- verify the export (and that it is the "
        "store-specific file, not an empty filter result), then export it again."
    ),
    columns_note="importers/recovr.py + fixtures/synthetic/recovr.csv",
)

RAPIDRECON_RECON_STATUS = ReportContract(
    contract_id="rapidrecon_recon_status",
    vendor="rapidrecon", vendor_label="RapidRecon",
    report_type="recon_status", report_label="Reconditioning Status",
    ingestion_mode="contextual_snapshot",
    slot="rapidrecon", supported=True,
    # "VIN" is the only column the reconciler REQUIRES (every other
    # RapidRecon read is guarded with `if c in df.columns` in
    # sync/reconciler.py, per ARCHITECTURE.md's "RapidRecon:
    # contextual enrichment only"). But VIN alone cannot IDENTIFY a report
    # as RapidRecon: before Sprint 10, any VIN-bearing file (a RecovR
    # export, for instance) sailed through this slot and wrote junk
    # observations. Classification therefore additionally demands
    # "Step" -- present in the real export, the fixture, and
    # sync/pipeline.py's _EMPTY_COLUMNS -- a deliberate tightening,
    # recorded in INGESTION_ARCHITECTURE.md.
    required_columns=("VIN",),
    signature_columns=("VIN", "Step"),
    vin_column="VIN", vin_required_per_row=False,
    duplicate_key_column="VIN",
    zero_row_policy="warning",
    zero_row_message=(
        "The RapidRecon report contains zero records. An empty reconditioning "
        "board is unusual -- confirm the export is correct before running the "
        "sync."
    ),
    columns_note="importers/rapidrecon.py + fixtures/synthetic/rapidrecon.csv",
)


# The registry, in deterministic classification order. Order matters
# only for stable output; classification itself requires a unique
# exact match (see sync/report_classifier.py).
CONTRACTS = (
    TEKION_CURRENT,
    TEKION_SOLD,
    KEYPER_FULL,
    KEYPER_KEY_EVENT,
    MDD_NOT_PAIRED,
    RECOVR_DEVICE_STATE,
    RAPIDRECON_RECON_STATUS,
)

# slot key -> the contract expected in that slot (supported contracts
# only; KEYPER_KEY_EVENT has no slot on purpose).
SLOT_CONTRACTS = {c.slot: c for c in CONTRACTS if c.supported and c.slot}

BY_CONTRACT_ID = {c.contract_id: c for c in CONTRACTS}
