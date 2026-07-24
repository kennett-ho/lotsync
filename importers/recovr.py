"""
RecovR (GPS device tracking) importer. Unlike MDD's export, this is
the full list -- both paired and unpaired vehicles -- filtered down to
"not paired" by the callers that need it (sync/reconciler.py). Kept as
the full list here rather than pre-filtering at import time, since
sold_vehicles_report.csv also needs to check Paired == 'Yes' cases.
"""

import pandas as pd

from lotsync.utils.file_resolution import find_upload


def load_recovr_full(path: str = None) -> pd.DataFrame:
    if path is None:
        # As of the "Kia umbrella" RecovR account being set up, exports
        # can arrive as two files: a full multi-brand umbrella export
        # and a store-specific one (confirmed against real data: the
        # Kia-named file is a clean subset of the umbrella file, not a
        # duplicate or a divergent copy). Prefer the store-specific one
        # when both are present -- it's already correctly scoped, no
        # prefix filtering needed. Falls back to a plain "RecovR" match
        # for the older single-file convention.
        try:
            path = find_upload(require_all=["RecovR", "Kia"], exclude="MARK_AUTO")
        except FileNotFoundError:
            path = find_upload("RecovR", exclude="MARK_AUTO")
    return pd.read_csv(path)
