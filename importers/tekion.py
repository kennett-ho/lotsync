"""
Tekion Master List / Unsold report (currently Stocked In inventory)
importer.
"""

import pandas as pd

from lotsync.sync.normalizer import classify_tekion_stock
from lotsync.utils.file_resolution import find_upload


def load_tekion(internal_fleet_vins: set, path: str = None) -> pd.DataFrame:
    if path is None:
        # Seen under two different naming conventions across exports:
        # "Tekion_Master_List.csv" and "..._Tekion_Unsold_Report.csv".
        # "Unsold" also excludes it from the Sold importer's own match
        # (see importers/sold.py) since "sold" is a substring of
        # "unsold" and would otherwise wrongly overlap.
        path = find_upload(["Master", "Unsold"])
    df = pd.read_csv(path)
    parsed = df.apply(
        lambda r: classify_tekion_stock(r["Stock #"], r["VIN #"]), axis=1
    )
    df["identifier_type"] = parsed.apply(lambda t: t[0])
    df["identifier_value"] = parsed.apply(lambda t: t[1])
    df["is_internal_fleet"] = df["VIN #"].astype(str).str.strip().str.upper().isin(
        internal_fleet_vins
    )
    return df
