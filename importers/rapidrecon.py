"""
RapidRecon importer -- tracks the reconditioning workflow for used
vehicles (inspection, detail, body work, auction/wholesale routing)
before they're lot-ready.

Unlike every other source in this pipeline, RapidRecon spans multiple
stores/brands in one export (confirmed against real data: only 1,005
of 1,402 rows share a stock-number prefix with the currently-loaded
Tekion scope). Store scoping reuses the same prefix-against-loaded-
Tekion-prefixes approach as everywhere else in this pipeline -- see
sync/reconciler.py's enrich_with_rapidrecon().

VIN is a clean, always-present 17-character column here -- no
identifier-type guessing needed, unlike Keyper.
"""

import pandas as pd

from lotsync.utils.file_resolution import find_upload


def load_rapidrecon(path: str = None) -> pd.DataFrame:
    if path is None:
        path = find_upload("RapidRecon")
    df = pd.read_csv(path)
    # "Used" vs "USED" casing inconsistency seen in real data -- normalize.
    if "New/Used" in df.columns:
        df["New/Used"] = df["New/Used"].astype(str).str.strip().str.upper()
    df["VIN"] = df["VIN"].astype(str).str.strip()
    return df
