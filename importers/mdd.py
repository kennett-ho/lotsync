"""
MDD "Not Paired" report importer. Note this is already MDD's own
pre-filtered exception list, not a raw beacon-assignment feed -- see
importers/mdd_history.py for the gap that leaves (no way to confirm a
sold vehicle's beacon was actually removed, only that it isn't
currently in this "not paired" list).
"""

import pandas as pd

from lotsync.utils.file_resolution import find_upload


def load_mdd_not_paired(path: str = None) -> pd.DataFrame:
    if path is None:
        path = find_upload("MDD")
    return pd.read_csv(path)
