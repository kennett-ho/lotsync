"""
Sprint 10 (Rail D) -- deterministic, content-based report
classification. Given the column headers actually present in an
uploaded file, decide which ReportContract the file IS -- independent
of which upload slot it arrived in, what it is named, or what MIME
type the browser claimed. Those are hints the product deliberately
does not trust (the pre-Sprint-10 design note in the retired
sync/upload_validation.py -- "which report a file is comes from which
slot the person chose" -- is exactly the assumption Rail D retires).

Deliberately NOT probabilistic: a contract matches when every one of
its signature columns is present, full stop. One match = classified.
Multiple matches = AMBIGUOUS (fail loudly -- with the current
registry this requires a file carrying both "Stocked In Date" and
"Sold Date", which no real Tekion export does; if a future export
does, that surfaces as a vendor-discovery question, never a silent
guess). Zero matches = either a recognizable vendor VARIANT (some,
but not all, of one vendor's signature evidence -- the Keyper
Event-report case lands here by design, see report_contracts.
KEYPER_KEY_EVENT) or UNRECOGNIZED.

Classification never reads data rows -- headers are the structural
identity evidence. Row-level facts (counts, VIN validity, duplicates)
are sync/ingestion.py's job, after classification has decided which
contract's rules apply.
"""

from dataclasses import dataclass, field

from lotsync.sync.report_contracts import CONTRACTS


# How many of one vendor's signature columns a file must share before
# we call it a "variant" of that vendor rather than unrecognized.
# 2 keeps a lone generic column ("VIN" appears in three vendors'
# exports) from implying a vendor.
_VARIANT_MIN_HITS = 2


@dataclass(frozen=True)
class Classification:
    # "exact": exactly one contract's full signature is present.
    # "ambiguous": more than one contract's full signature is present.
    # "variant": no full signature, but >=_VARIANT_MIN_HITS of one
    #            vendor's signature columns -- a report from a known
    #            vendor that is not any supported report type.
    # "none": no contract evidence at all.
    confidence: str
    contract_id: str = ""       # set only when confidence == "exact"
    vendor: str = ""            # set for "exact" and "variant"
    vendor_label: str = ""
    candidates: tuple = ()      # contract_ids, set when "ambiguous"
    reasons: tuple = ()         # human-readable evidence statements


def classify_headers(headers) -> Classification:
    """
    headers: iterable of raw header cells from the file. Cells are
    matched after strip(); case is significant on purpose -- casing IS
    distinguishing evidence in the real exports (MDD's lowercase
    "vin"/"stock" vs RecovR's "VIN"/"Stock Number").
    """
    present = {str(h).strip() for h in headers if str(h).strip()}

    exact = [
        c for c in CONTRACTS
        if c.supported and c.signature_columns
        and all(col in present for col in c.signature_columns)
    ]

    if len(exact) == 1:
        c = exact[0]
        return Classification(
            confidence="exact", contract_id=c.contract_id,
            vendor=c.vendor, vendor_label=c.vendor_label,
            reasons=(
                f"Distinctive {c.vendor_label} {c.report_label} columns present: "
                + ", ".join(c.signature_columns),
            ),
        )

    if len(exact) > 1:
        ids = tuple(c.contract_id for c in exact)
        return Classification(
            confidence="ambiguous", candidates=ids,
            reasons=(
                "The file carries the distinctive columns of more than one "
                "report type: " + ", ".join(
                    f"{c.vendor_label} {c.report_label}" for c in exact
                ),
            ),
        )

    # No full signature. Is there partial evidence of a known vendor?
    # (Scores every registry contract's signature, including
    # unsupported ones -- though KEYPER_KEY_EVENT deliberately has no
    # signature columns, so Keyper variants are recognized via the
    # Full Inventory report's own partial evidence.)
    best_vendor, best_hits, best_label = "", 0, ""
    for c in CONTRACTS:
        if not c.signature_columns:
            continue
        hits = sum(1 for col in c.signature_columns if col in present)
        if hits > best_hits:
            best_vendor, best_hits, best_label = c.vendor, hits, c.vendor_label

    if best_hits >= _VARIANT_MIN_HITS:
        return Classification(
            confidence="variant", vendor=best_vendor, vendor_label=best_label,
            reasons=(
                f"Some, but not all, of the distinctive {best_label} report "
                f"columns are present ({best_hits} matched) -- this looks like "
                f"a {best_label} export, but not one of the report types "
                "DealerDOH supports.",
            ),
        )

    return Classification(
        confidence="none",
        reasons=("The file's columns do not match any report DealerDOH recognizes.",),
    )
