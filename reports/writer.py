"""
Writes report dataframes to CSV. Deliberately trivial right now --
this is the seam where a future dashboard/API would plug in an
alternate renderer (JSON over HTTP, a database write, etc.) without
touching anything upstream in sync/ or rules/.
"""

import os

import pandas as pd


def write_reports(outputs: dict, out_dir: str):
    # out_dir isn't guaranteed to exist yet -- e.g. a fresh deployment's
    # persistent disk has nothing on it until something creates it. Same
    # convention as database/repository.py's connect() for LOTSYNC_DB_PATH.
    os.makedirs(out_dir, exist_ok=True)
    for filename, df in outputs.items():
        df.to_csv(f"{out_dir}/{filename}", index=False)


def print_summary(outputs: dict, key_out_aging: pd.DataFrame,
                   flag_to_controller: pd.DataFrame, sold_report: pd.DataFrame,
                   incoming_or_missing: pd.DataFrame):
    print("=== Report row counts ===")
    for filename, df in outputs.items():
        print(f"{filename}: {len(df)}")

    print()
    print("=== Key Out aging buckets ===")
    if len(key_out_aging):
        print(key_out_aging["aging_bucket"].value_counts())

    print()
    print("=== Flag to Controller reasons ===")
    if len(flag_to_controller):
        print(flag_to_controller["reason"].value_counts())

    print()
    print("=== Sold vehicles: overall status ===")
    if len(sold_report):
        print(sold_report["overall_status"].value_counts())

    print()
    print("=== Incoming / Missing investigate: vehicle type breakdown ===")
    if len(incoming_or_missing):
        print(incoming_or_missing["vehicle_type"].value_counts())
    print()
    print("=== Incoming / Missing investigate: priority breakdown ===")
    if len(incoming_or_missing):
        print(incoming_or_missing.groupby(["vehicle_type", "priority"]).size())
