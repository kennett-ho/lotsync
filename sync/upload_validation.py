"""
Phase 3, Sprint 4 -- validates an uploaded file belongs in the upload
slot it was dropped into, before sync/pipeline.py touches it.

"Identify report types" (per this sprint's brief) is answered by the
upload slot itself -- the Inventory Sync page has six distinct,
explicitly labeled slots (Tekion Unsold, Tekion Sold, Keyper, MDD,
RecovR, RapidRecon), so which report a file *is* comes from which slot
the person uploading it chose, not from guessing at filename or content
patterns. "Validate reports" is this module's job: a cheap, header-only
check (pd.read_csv(path, nrows=0), no full parse) that the file actually
has the columns its slot's importer and the reconciliation engine
require -- catching a file dropped in the wrong slot with a specific,
readable error instead of a downstream KeyError or silently-wrong
reconciliation.

REQUIRED_COLUMNS is deliberately not every column each source's real
export carries (see README.md/importers/*.py for the full shape) -- only
the columns something in importers/*.py or sync/reconciler.py actually
reads by name. A real export always has more columns than this; a file
missing any of these specific ones is not that report.
"""

import pandas as pd

REQUIRED_COLUMNS = {
    "tekion": ["Stock #", "VIN #", "Status", "Stocked In Date", "Year Make Model"],
    "sold": ["Stock #", "VIN #", "Status", "Sold Date", "Year Make Model"],
    "keyper": ["name", "Status", "System", "Checkout Date"],
    "mdd": ["vin", "stock", "year", "make", "model", "Dealership"],
    "recovr": ["VIN", "Stock Number", "Paired", "Year", "Make", "Model"],
    # VIN is the only column anything actually requires present (see
    # sync/reconciler.py's enrich_with_rapidrecon and
    # persist_rapidrecon_observations) -- every other RapidRecon column
    # used downstream is already read through an `if c in df.columns`
    # guard, on purpose, per ARCHITECTURE.md's "RapidRecon: contextual
    # enrichment only" section.
    "rapidrecon": ["VIN"],
}

SLOT_LABELS = {
    "tekion": "Tekion Unsold Inventory", "sold": "Tekion Sold Inventory",
    "keyper": "Keyper", "mdd": "MDD", "recovr": "RecovR", "rapidrecon": "RapidRecon",
}


def validate_upload(source: str, path: str) -> list:
    """
    Returns a list of human-readable problems (empty if the file looks
    right for `source`'s slot). Never raises for a malformed/unreadable
    file -- that's reported as a problem too, not an exception the
    caller has to catch.
    """
    label = SLOT_LABELS.get(source, source)
    try:
        header_df = pd.read_csv(path, nrows=0)
    except Exception as exc:
        return [f"{label}: couldn't be read as a CSV file ({exc})."]

    missing = [c for c in REQUIRED_COLUMNS[source] if c not in header_df.columns]
    if missing:
        return [f"{label}: missing expected column(s) {missing} -- "
                f"is this the right report for this slot?"]
    return []
