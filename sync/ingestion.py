"""
Sprint 10 (Rail D, Inventory Ingestion Safety) -- the single
validation boundary between uploaded dealership reports and the
synchronization engine.

Every ingestion path converges here (V1_1_RELEASE_READINESS 5.D):
POST /inventory-sync/validate calls validate_report_set() to build
the pre-sync preview, and POST /inventory-sync/run calls the SAME
function again before any mutation -- the preview is UX, the
execution-time revalidation is the invariant. A direct API caller who
skips the preview endpoint still cannot reach sync/pipeline.py with
evidence this module rejects. Future acquisition paths (scheduled
email, vendor API -- V1_1_RELEASE_READINESS 6.2) MUST route their
attachments through validate_report_set() too; do not build a second
validation path.

Severity model (Rail D / Sprint 10 phase 15):

- ERROR: the file cannot be processed. The whole request is rejected;
  nothing mutates.
- WARNING: potentially valid but operationally suspicious. Processing
  requires explicit human acknowledgement (see the fingerprint-bound
  acknowledgement contract in api/routers/inventory_sync.py -- the
  server re-derives every fact; a client cannot assert its way past
  a warning it never saw).
- INFO: context worth showing (no prior baseline, e.g.); never blocks.

Standing rule for any future UNATTENDED ingestion (documented now,
enforced when that path exists): a report producing a WARNING
defaults to HOLD for human review -- automation may never
auto-acknowledge.

Safety property this module maintains deliberately: validation reads
files with the same parser and the same encoding posture the engine's
importers use (plain pandas read_csv, default utf-8, strict). That
keeps validation's acceptance a SUBSET of the engine's -- validation
may reject something the engine could technically parse (safe), but
must never accept a file the engine would then fail on mid-run
(unsafe: that failure would land after mutation had begun).
Do not "improve" the validation read with tolerant encodings or
delimiter sniffing without changing the importers in the same commit.

Raw parser/library error text never reaches a user message -- codes
and dealership-language messages only (raw text may leak paths or
internals; Rail F/G will want the raw detail in telemetry later --
it is deliberately not part of the DTO surface today).
"""

import csv
import datetime
import hashlib
import os
from dataclasses import dataclass, field

import pandas as pd

from lotsync.sync.report_classifier import classify_headers
from lotsync.sync.report_contracts import BY_CONTRACT_ID, SLOT_CONTRACTS, SLOT_LABELS

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

# --- Upload hardening limits (Sprint 10 phase 12) -------------------
# Real exports at production scale are well under 2 MB / 5,000 rows
# (the 2026-08-15 production backup holds 4,672 vehicles; the largest
# observed real export, RapidRecon, was 1,402 rows). These caps exist
# to make a mistaken or hostile upload fail fast and readably, not to
# ration legitimate use -- hence roughly 10x headroom over reality.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_DATA_ROWS = 50_000

# --- Suspicious count-change thresholds (Sprint 10 phase 14) --------
# PROPOSED DEFAULTS -- PENDING OWNER RATIFICATION at the Sprint 10 PR
# gate (V1_1_RELEASE_READINESS 5.D exit 7 assigns Sprint 10 the
# default; the sprint brief requires the owner to ratify it before it
# is treated as settled policy). Grounding for the proposal, absent
# any pre-existing governed threshold (none exists in docs, config,
# or code -- audited 2026-08-16):
# - The failure this catches is catastrophic-shrink (the register's
#   own example: a 14-row export against 987 tracked vehicles, -98%).
# - Ordinary day-over-day drift at this store's scale (tens of sales
#   or intakes against hundreds-to-thousands of rows) stays inside
#   +/-15%, so a >15% DROP that also removes at least 10 rows is
#   worth a human look without nagging on routine fluctuation.
# - Suspicious INCREASE exists for a real, observed failure shape:
#   the multi-brand RecovR "umbrella" export contains other stores'
#   rows (importers/recovr.py's MARK_AUTO exclusion is evidence);
#   uploading it in place of the store-specific file roughly doubles
#   the count. +50% and at least +25 rows flags that without firing
#   on genuine intake days.
# Zero-row files never reach these checks -- they are handled first,
# by each contract's own zero_row_policy (already a hard error for
# authoritative snapshots, no threshold decision required).
SUSPICIOUS_DROP_PCT = 15.0
SUSPICIOUS_DROP_MIN_ROWS = 10
SUSPICIOUS_INCREASE_PCT = 50.0
SUSPICIOUS_INCREASE_MIN_ROWS = 25

_VIN_SAMPLE_LIMIT = 5


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"severity": self.severity, "code": self.code, "message": self.message}


@dataclass
class ReportValidation:
    slot: str
    slot_label: str
    expected_contract_id: str
    fingerprint: str = ""
    detected_contract_id: str = ""
    classification_confidence: str = ""
    classification_reasons: tuple = ()
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0
    duplicate_identifiers: int = 0
    baseline: dict = None
    issues: list = field(default_factory=list)

    def add(self, severity: str, code: str, message: str):
        self.issues.append(Issue(severity, code, message))

    @property
    def has_errors(self) -> bool:
        return any(i.severity == SEVERITY_ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == SEVERITY_WARNING for i in self.issues)

    @property
    def status(self) -> str:
        if self.has_errors:
            return "rejected"
        if self.has_warnings:
            return "needs_review"
        return "ready"

    def to_dict(self) -> dict:
        expected = BY_CONTRACT_ID[self.expected_contract_id]
        detected = BY_CONTRACT_ID.get(self.detected_contract_id)
        return {
            "slot": self.slot,
            "slot_label": self.slot_label,
            "status": self.status,
            "fingerprint": self.fingerprint,
            "expected": {
                "contract_id": expected.contract_id,
                "vendor": expected.vendor_label,
                "report_type": expected.report_label,
                "ingestion_mode": expected.ingestion_mode,
            },
            "detected": None if detected is None else {
                "contract_id": detected.contract_id,
                "vendor": detected.vendor_label,
                "report_type": detected.report_label,
                "ingestion_mode": detected.ingestion_mode,
            },
            "classification": {
                "confidence": self.classification_confidence,
                "reasons": list(self.classification_reasons),
            },
            "stats": {
                "total_rows": self.total_rows,
                "valid_rows": self.valid_rows,
                "invalid_rows": self.invalid_rows,
                "duplicate_rows": self.duplicate_rows,
                "duplicate_identifiers": self.duplicate_identifiers,
            },
            "baseline": self.baseline,
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class ReportSetValidation:
    validated_at: str
    reports: list

    @property
    def fingerprint(self) -> str:
        joined = ";".join(
            f"{r.slot}:{r.fingerprint}" for r in sorted(self.reports, key=lambda r: r.slot)
        )
        return hashlib.sha256(joined.encode("utf-8")).hexdigest()

    @property
    def has_errors(self) -> bool:
        return any(r.has_errors for r in self.reports)

    @property
    def has_warnings(self) -> bool:
        return any(r.has_warnings for r in self.reports)

    def to_dict(self) -> dict:
        return {
            "validated_at": self.validated_at,
            "fingerprint": self.fingerprint,
            "status": ("rejected" if self.has_errors
                       else "needs_review" if self.has_warnings else "ready"),
            "requires_acknowledgement": (not self.has_errors) and self.has_warnings,
            "reports": [r.to_dict() for r in self.reports],
        }


def _sha256_and_size(path: str):
    h = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _looks_like_excel(path: str) -> bool:
    # .xlsx/.xlsm (and any ZIP container) begin with PK\x03\x04; legacy
    # .xls begins with the OLE2 magic D0 CF 11 E0.
    with open(path, "rb") as f:
        head = f.read(8)
    return head.startswith(b"PK\x03\x04") or head.startswith(b"\xd0\xcf\x11\xe0")


def _read_header(path: str):
    """First CSV record as raw cells, mirroring the engine's utf-8
    posture (see module docstring). Returns (cells, problem_code)."""
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for record in reader:
                if any(str(c).strip() for c in record):
                    return record, None
            return [], "no_header"
    except UnicodeDecodeError:
        return [], "encoding"
    except (csv.Error, OSError):
        return [], "unreadable"


def _validate_one(slot: str, path: str, db_conn) -> ReportValidation:
    contract = SLOT_CONTRACTS[slot]
    r = ReportValidation(
        slot=slot, slot_label=SLOT_LABELS[slot], expected_contract_id=contract.contract_id,
    )

    # --- File safety (phase 12) -- before any parsing ---------------
    try:
        r.fingerprint, size = _sha256_and_size(path)
    except OSError:
        r.add(SEVERITY_ERROR, "UNREADABLE_FILE",
              f"{r.slot_label}: the uploaded file could not be read.")
        return r

    if size == 0:
        r.add(SEVERITY_ERROR, "EMPTY_FILE",
              f"{r.slot_label}: the uploaded file is empty (0 bytes). "
              "The export likely failed before writing any data -- generate it again.")
        return r

    if size > MAX_UPLOAD_BYTES:
        r.add(SEVERITY_ERROR, "FILE_TOO_LARGE",
              f"{r.slot_label}: the file is larger than the "
              f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit. Real "
              f"{contract.vendor_label} exports are far smaller -- verify this "
              "is the right file.")
        return r

    if _looks_like_excel(path):
        r.add(SEVERITY_ERROR, "UNSUPPORTED_FORMAT",
              f"{r.slot_label}: this looks like an Excel workbook. DealerDOH "
              "ingests CSV exports only -- re-export the report as CSV.")
        return r

    header, header_problem = _read_header(path)
    if header_problem == "encoding":
        r.add(SEVERITY_ERROR, "UNREADABLE_FILE",
              f"{r.slot_label}: the file is not readable as standard CSV text. "
              "Re-export the report as a plain CSV file.")
        return r
    if header_problem is not None or not header:
        r.add(SEVERITY_ERROR, "UNREADABLE_FILE",
              f"{r.slot_label}: no CSV header row was found in the file. "
              "Re-export the report as a plain CSV file.")
        return r

    stripped = [str(c).strip() for c in header]
    if stripped and stripped[0].startswith("﻿"):
        # A BOM would make the engine read the first column name
        # wrong; reject with the actual remedy rather than a baffling
        # column mismatch. (See the module docstring's subset rule --
        # tolerating it here without changing the importers would let
        # validation pass a file the engine then fails on.)
        r.add(SEVERITY_ERROR, "UNREADABLE_FILE",
              f"{r.slot_label}: the file starts with a byte-order mark (BOM), "
              "which the sync engine does not accept. Re-export as standard "
              "CSV (UTF-8 without BOM).")
        return r

    named = [c for c in stripped if c]
    dupes = sorted({c for c in named if named.count(c) > 1})
    if dupes:
        r.add(SEVERITY_ERROR, "DUPLICATE_HEADER",
              f"{r.slot_label}: the file contains duplicate column headers "
              f"({', '.join(dupes)}), so its structure is ambiguous. "
              "Re-export the report.")
        return r

    # --- Classification (phase 5) + wrong-slot protection (phase 6) --
    cls = classify_headers(stripped)
    r.classification_confidence = cls.confidence
    r.classification_reasons = cls.reasons

    if cls.confidence == "exact":
        r.detected_contract_id = cls.contract_id
        if cls.contract_id != contract.contract_id:
            detected = BY_CONTRACT_ID[cls.contract_id]
            r.add(SEVERITY_ERROR, "WRONG_REPORT_TYPE",
                  f"{r.slot_label}: expected the {contract.vendor_label} "
                  f"{contract.report_label} report, but this file's columns "
                  f"identify it as the {detected.vendor_label} "
                  f"{detected.report_label} report. Upload it in the "
                  f"{SLOT_LABELS.get(detected.slot, detected.report_label)} slot "
                  "if that was intended.")
            return r
    elif cls.confidence == "ambiguous":
        r.add(SEVERITY_ERROR, "AMBIGUOUS_REPORT_TYPE",
              f"{r.slot_label}: {cls.reasons[0]} DealerDOH will not guess "
              "which one it is -- re-export the intended report.")
        return r
    elif cls.confidence == "variant":
        if cls.vendor == "keyper":
            # The Keyper Full-vs-Event boundary (Sprint 10 phase 22).
            # No Key Event sample exists, so recognition is honest:
            # "Keyper evidence, but not the Full Inventory contract."
            r.add(SEVERITY_ERROR, "REPORT_VARIANT_UNSUPPORTED",
                  f"{r.slot_label}: this looks like a Keyper export, but not "
                  "the Full Key Inventory report this slot requires. If it is "
                  "a Keyper Event/history report: that report type is not yet "
                  "supported and can never substitute for the full inventory "
                  "snapshot. Export the Full Key Inventory report instead.")
        else:
            r.add(SEVERITY_ERROR, "REPORT_VARIANT_UNSUPPORTED",
                  f"{r.slot_label}: this looks like a {cls.vendor_label} "
                  "export, but not a report type DealerDOH supports in this "
                  f"slot. Expected: {contract.vendor_label} "
                  f"{contract.report_label}.")
        return r
    else:
        r.add(SEVERITY_ERROR, "UNRECOGNIZED_REPORT",
              f"{r.slot_label}: the file's columns do not match any report "
              f"DealerDOH recognizes. Expected: {contract.vendor_label} "
              f"{contract.report_label}.")
        return r

    # --- Structural validation (phase 7) ----------------------------
    missing = [c for c in contract.required_columns if c not in stripped]
    if missing:
        r.add(SEVERITY_ERROR, "MISSING_REQUIRED_COLUMN",
              f"{r.slot_label}: required column(s) missing: "
              f"{', '.join(missing)}. Is this a complete "
              f"{contract.vendor_label} {contract.report_label} export?")
        # Classification already confirmed the report type; keep going
        # so the preview still shows row counts, but the ERROR stands.

    # --- Full parse for row-level facts (phases 8-11) ---------------
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False,
                         nrows=MAX_DATA_ROWS + 1)
    except Exception:
        r.add(SEVERITY_ERROR, "UNREADABLE_FILE",
              f"{r.slot_label}: the file's rows could not be parsed as CSV "
              "(a malformed row or truncated export). Re-export the report.")
        return r

    if len(df) > MAX_DATA_ROWS:
        r.add(SEVERITY_ERROR, "TOO_MANY_ROWS",
              f"{r.slot_label}: the file contains more than "
              f"{MAX_DATA_ROWS:,} data rows -- far beyond any real "
              f"{contract.vendor_label} export. Verify this is the right file.")
        return r

    df.columns = [str(c).strip() for c in df.columns]
    r.total_rows = len(df)
    r.valid_rows = r.total_rows

    # --- Zero-data protection (phases 8-9, per-contract policy) -----
    if r.total_rows == 0:
        severity = (SEVERITY_ERROR if contract.zero_row_policy == "error"
                    else SEVERITY_WARNING)
        r.add(severity, "NO_DATA_ROWS", contract.zero_row_message)
        r.baseline = _baseline_block(db_conn, contract, current_valid_rows=0,
                                     emit_issues_on=r)
        return r

    # --- Row-level validation (phase 10) ----------------------------
    if contract.vin_column and contract.vin_column in df.columns:
        vins = df[contract.vin_column].astype(str).str.strip()
        blank_lines = [i + 2 for i, v in vins.items() if v == ""]  # +2: header + 1-based
        malformed = [v for v in vins if v and not (len(v) == 17 and v.isalnum())]

        if blank_lines and contract.vin_required_per_row:
            # These rows would become Vehicle primary keys -- a blank
            # there is corrupting, so the FILE is rejected (the
            # recorded Rail D exit-5 decision: quarantine-file, never
            # silently drop rows -- evidence files are not edited).
            shown = ", ".join(map(str, blank_lines[:_VIN_SAMPLE_LIMIT]))
            more = ("" if len(blank_lines) <= _VIN_SAMPLE_LIMIT
                    else f" (and {len(blank_lines) - _VIN_SAMPLE_LIMIT} more)")
            r.add(SEVERITY_ERROR, "MISSING_VINS",
                  f"{r.slot_label}: {len(blank_lines)} row(s) have no VIN "
                  f"(file line {shown}{more}). Every "
                  f"{contract.vendor_label} {contract.report_label} row must "
                  "carry a VIN -- fix the export and try again.")

        if malformed or (blank_lines and not contract.vin_required_per_row):
            parts = []
            if malformed:
                samples = ", ".join(repr(v) for v in malformed[:_VIN_SAMPLE_LIMIT])
                parts.append(f"{len(malformed)} malformed (e.g. {samples})")
            if blank_lines and not contract.vin_required_per_row:
                parts.append(f"{len(blank_lines)} blank")
            bad = len(malformed) + (len(blank_lines) if not contract.vin_required_per_row else 0)
            r.add(SEVERITY_WARNING, "MALFORMED_VINS",
                  f"{r.slot_label}: {bad} row(s) do not carry a valid "
                  f"17-character VIN: {'; '.join(parts)}. These rows cannot "
                  "be matched to vehicles reliably.")

        invalid = len(blank_lines) + len(malformed)
        r.invalid_rows = invalid
        r.valid_rows = r.total_rows - invalid
    elif contract.contract_id == "keyper_full_inventory" and "name" in df.columns:
        names = df["name"].astype(str).str.strip()
        r.valid_rows = int((names != "").sum())
        r.invalid_rows = r.total_rows - r.valid_rows
        # No issue emitted: unresolvable Keyper identifiers are the
        # PendingIdentity machinery's designed input, not invalid
        # evidence (DECISION_FRAMEWORK.md's identity-resolution path).

    # --- Duplicate detection (phase 11) -----------------------------
    r.duplicate_rows = int(df.duplicated().sum())
    if r.duplicate_rows:
        r.add(SEVERITY_WARNING, "DUPLICATE_ROWS",
              f"{r.slot_label}: {r.duplicate_rows} row(s) are exact "
              "duplicates of another row in the same file.")

    key_col = contract.duplicate_key_column
    if key_col and key_col in df.columns:
        keys = df[key_col].astype(str).str.strip()
        keys = keys[keys != ""]
        counts = keys.value_counts()
        dup_values = counts[counts > 1]
        if len(dup_values):
            r.duplicate_identifiers = int(len(dup_values))
            samples = ", ".join(map(repr, dup_values.index[:_VIN_SAMPLE_LIMIT]))
            code = "DUPLICATE_VINS" if key_col == contract.vin_column else "DUPLICATE_IDENTIFIERS"
            r.add(SEVERITY_WARNING, code,
                  f"{r.slot_label}: {len(dup_values)} {key_col} value(s) "
                  f"appear more than once ({samples}). Review which row is "
                  "correct before syncing.")

    # --- Comparable-baseline count sanity (phases 13-14) ------------
    r.baseline = _baseline_block(db_conn, contract,
                                 current_valid_rows=r.valid_rows, emit_issues_on=r)
    return r


def _baseline_block(db_conn, contract, *, current_valid_rows: int, emit_issues_on):
    """
    Latest ACCEPTED comparable report's counts, scoped strictly by
    (vendor, report_type) -- a Tekion sold baseline can never judge a
    Tekion current file, and Keyper full evidence could never be
    compared against a (future) Keyper event report (Sprint 10 phase
    13). Baselines are recorded per executed sync by the run endpoint
    (see api/routers/inventory_sync.py), so the validation endpoint
    only ever READS here. No comparison exists yet -> "No prior
    baseline" INFO, never a blocker.
    """
    if db_conn is None:
        return None
    from lotsync.database.repository import latest_report_baseline

    previous = latest_report_baseline(db_conn, contract.vendor, contract.report_type)
    if previous is None:
        emit_issues_on.add(SEVERITY_INFO, "NO_PRIOR_BASELINE",
                           f"No prior {contract.vendor_label} "
                           f"{contract.report_label} sync to compare against.")
        return {"previous_rows": None, "previous_at": None,
                "change": None, "change_pct": None}

    prev = previous["valid_rows"]
    change = current_valid_rows - prev
    pct = (change / prev * 100.0) if prev else None
    block = {"previous_rows": prev, "previous_at": previous["sync_started_at"],
             "change": change, "change_pct": None if pct is None else round(pct, 1)}

    if current_valid_rows == 0:
        # Zero-row handling already produced its own (stronger)
        # per-contract outcome; the numbers above still render in the
        # preview for context.
        return block

    if pct is not None and change < 0:
        if -change >= SUSPICIOUS_DROP_MIN_ROWS and -pct > SUSPICIOUS_DROP_PCT:
            emit_issues_on.add(
                SEVERITY_WARNING, "SUSPICIOUS_COUNT_DROP",
                f"{contract.vendor_label} {contract.report_label}: "
                f"{current_valid_rows:,} rows vs {prev:,} in the previous "
                f"comparable report ({change:+,}, {pct:+.1f}%). A drop this "
                "large usually means an incomplete export -- verify before "
                "processing.")
    elif pct is not None and change > 0:
        if change >= SUSPICIOUS_INCREASE_MIN_ROWS and pct > SUSPICIOUS_INCREASE_PCT:
            emit_issues_on.add(
                SEVERITY_WARNING, "SUSPICIOUS_COUNT_INCREASE",
                f"{contract.vendor_label} {contract.report_label}: "
                f"{current_valid_rows:,} rows vs {prev:,} in the previous "
                f"comparable report ({change:+,}, {pct:+.1f}%). An increase "
                "this large can mean the wrong (e.g. multi-store) export was "
                "uploaded -- verify before processing.")
    return block


def validate_report_set(file_paths: dict, db_conn=None) -> ReportSetValidation:
    """
    file_paths: {slot_key: filesystem_path} for the slots provided in
    this request (same shape sync/pipeline.run_inventory_sync takes).
    db_conn is used ONLY to read comparison baselines; this function
    performs no writes of any kind.
    """
    reports = [
        _validate_one(slot, path, db_conn)
        for slot, path in sorted(file_paths.items())
        if path
    ]
    return ReportSetValidation(
        validated_at=datetime.datetime.now().isoformat(),
        reports=reports,
    )
