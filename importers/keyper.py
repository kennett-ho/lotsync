"""
Keyper (key management) importer.
"""

import pandas as pd

from lotsync.sync.normalizer import classify_keyper_identifier
from lotsync.utils.file_resolution import find_upload


def load_keyper(path: str = None) -> pd.DataFrame:
    if path is None:
        path = find_upload("Keyper")
    df = pd.read_csv(path)
    df = df.rename(columns={"name": "identifier_raw"})
    parsed = df["identifier_raw"].apply(classify_keyper_identifier)
    df["identifier_type"] = parsed.apply(lambda t: t[0])
    df["identifier_value"] = parsed.apply(lambda t: t[1])
    df["checkout_dt"] = pd.to_datetime(
        df["Checkout Date"], format="%m/%d/%Y %H:%M", errors="coerce"
    )
    return df
