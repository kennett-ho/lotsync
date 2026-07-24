"""
Validation rules that operate purely on Tekion's own exports against
each other -- not Keyper matching. These are cleanly separable from
sync/reconciler.py because they don't participate in the Keyper
walk-and-route logic at all.

Note: the OTHER exception cases (tekion_auto_generated_stock_number,
unrecognized identifier, ambiguous_last6_vin_multiple_matches) are
still generated inline inside sync/reconciler.py's
reconcile_keyper_tekion(), not here -- they're interleaved with the
per-row matching control flow in a way that would need the Phase 2
Vehicle-object rewrite to cleanly separate without restructuring
working logic. Documented in ARCHITECTURE.md rather than forced apart
prematurely.

Moved verbatim from the original reconcile.py -- no logic changes.
"""

import pandas as pd


def find_tekion_sync_conflicts(tekion_df: pd.DataFrame, sold_df: pd.DataFrame) -> pd.DataFrame:
    conflicts = []
    # Build VIN -> row-index lookups once, rather than rescanning the
    # entire dataframe (astype/str.strip over every row) for each VIN
    # in the intersection. Found during code review -- with real data
    # (14 conflicts, 3009 sold rows) this didn't matter, but the
    # original was O(intersection_size * len(sold_df)) and would have
    # gotten slow with multi-store or historical data.
    # setdefault, not a dict comprehension -- a dict comprehension keeps
    # the LAST occurrence of a duplicate key, which would silently
    # change behavior for a VIN that's both duplicate-sold and also
    # still-stocked-in. The original code used .iloc[0] (first match);
    # setdefault preserves that.
    sold_vin_idx = {}
    for i, v in sold_df["VIN #"].items():
        sold_vin_idx.setdefault(str(v).strip(), i)
    master_vin_idx = {}
    for i, v in tekion_df["VIN #"].items():
        master_vin_idx.setdefault(str(v).strip(), i)

    sold_vins = set(sold_vin_idx.keys())
    master_vins = set(master_vin_idx.keys())
    for vin in sorted(sold_vins & master_vins):
        srow = sold_df.loc[sold_vin_idx[vin]]
        mrow = tekion_df.loc[master_vin_idx[vin]]
        conflicts.append({
            "conflict_type": "sold_but_still_stocked_in", "vin": vin,
            "sold_stock": srow["Stock #"], "sold_date": srow["Sold Date"],
            "master_stock": mrow["Stock #"], "master_stocked_in_date": mrow["Stocked In Date"],
        })
    dupe_vins = sold_df[sold_df["VIN #"].duplicated(keep=False)]
    for vin, group in dupe_vins.groupby("VIN #"):
        entries = "; ".join(f"{r['Stock #']} sold {r['Sold Date']}" for _, r in group.iterrows())
        conflicts.append({"conflict_type": "duplicate_sold_vin", "vin": vin, "details": entries})
    return pd.DataFrame(conflicts)
