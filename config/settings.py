"""
All reading of oms_config.xlsx lives here. This module's job is I/O --
translating spreadsheet cells into plain Python values -- not deciding
what the business rules should be. Default/fallback threshold values
come from lotsync.rules.aging, not from constants defined here.

Moved verbatim from the original reconcile.py -- no logic changes.
"""

import datetime
import os
import pandas as pd

from lotsync.rules.aging import (
    KEY_OUT_AGING_DEFAULT,
    INCOMING_MISSING_DEFAULT,
    NEW_CAR_DEFAULT,
)

# Overridable via LOTSYNC_CONFIG_PATH; defaults to a repo-relative
# location. (Previously hardcoded to /mnt/user-data/uploads/, this
# project's original development sandbox path -- see
# utils/file_resolution.py for the same adjustment and why.)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.environ.get(
    "LOTSYNC_CONFIG_PATH", os.path.join(_REPO_ROOT, "data", "uploads", "oms_config.xlsx")
)


def load_settings(path: str = CONFIG_PATH):
    """
    Reads Store Name and Sync Date from the Settings sheet. Sync Date
    left blank means "use today's date" -- only fill it in when
    re-running against older, saved exports rather than a live pull.
    """
    defaults = {"store_name": "Mark Kia", "sync_date": datetime.datetime.now()}
    try:
        df = pd.read_excel(path, sheet_name="Settings", header=3)
    except FileNotFoundError:
        print(f"WARNING: {path} not found -- using default settings "
              f"(store_name='{defaults['store_name']}', sync_date=today).")
        return defaults

    values = dict(zip(df["Setting"], df["Value"]))
    store_name = values.get("Store Name")
    if pd.isna(store_name) or not str(store_name).strip():
        store_name = defaults["store_name"]

    sync_date_raw = values.get("Sync Date")
    if pd.isna(sync_date_raw) or not str(sync_date_raw).strip():
        sync_date = datetime.datetime.now()
    else:
        sync_date = pd.to_datetime(sync_date_raw)

    return {"store_name": str(store_name).strip(), "sync_date": sync_date}


def _load_bucket_sheet(path, sheet_name, header, column_name, fallback):
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=header)
    except FileNotFoundError:
        print(f"WARNING: {path} not found -- using default {sheet_name}.")
        return fallback

    df = df.dropna(subset=[column_name, "Label"])
    if df.empty:
        return fallback
    return sorted(
        (int(r[column_name]), str(r["Label"]).strip())
        for _, r in df.iterrows()
    )


def load_day_out_buckets(path: str = CONFIG_PATH):
    """Key Out Aging bucket thresholds: (minimum_days_out, label) pairs."""
    return _load_bucket_sheet(path, "Key Out Aging Buckets", 4,
                               "Minimum Days Out", KEY_OUT_AGING_DEFAULT)


def load_incoming_missing_buckets(path: str = CONFIG_PATH):
    """Incoming/Missing (Trade/Other) priority thresholds."""
    return _load_bucket_sheet(path, "Incoming Missing Buckets", 5,
                               "Minimum Days Since Stocked In", INCOMING_MISSING_DEFAULT)


def load_new_car_buckets(path: str = CONFIG_PATH):
    """New Car (Awaiting Dropoff) priority thresholds."""
    return _load_bucket_sheet(path, "New Car Buckets", 5,
                               "Minimum Days Since Stocked In", NEW_CAR_DEFAULT)


def load_internal_fleet_vins(path: str = CONFIG_PATH) -> set:
    """
    Reads the internal-fleet exclusion list from the 'Excluded VINs'
    sheet instead of a hardcoded list in code -- lets the VIN list be
    maintained from the spreadsheet without touching code.

    Header row is expected on row 5 (VIN, Vehicle, Reason, Date Added).
    Only cells that look like a real 17-character VIN are accepted, and
    any row whose Reason starts with "Example" is skipped outright --
    the template row's VIN happens to be validly formatted, so format
    checks alone wouldn't catch someone leaving it in place by accident.
    """
    try:
        df = pd.read_excel(path, sheet_name="Excluded VINs", header=4)
    except FileNotFoundError:
        print(f"WARNING: {path} not found -- proceeding with an empty "
              f"internal-fleet exclusion list.")
        return set()

    if "VIN" not in df.columns:
        print(f"WARNING: {path} has no 'VIN' column under the expected "
              f"header row -- proceeding with an empty exclusion list.")
        return set()

    vins = set()
    for _, row in df.iterrows():
        raw = row.get("VIN")
        if pd.isna(raw):
            continue
        reason = str(row.get("Reason", "")).strip().lower()
        if reason.startswith("example"):
            continue
        v = str(raw).strip().upper()
        if len(v) == 17 and v.isalnum():
            vins.add(v)
        elif v:
            print(f"NOTE: skipping '{v}' in {path} -- doesn't look like a "
                  f"valid 17-character VIN.")
    return vins
