"""
Builds lookup indexes used to match a Keyper identifier against Tekion
or Sold records. Separated from reconciler.py because these are pure
index-construction -- no business decisions happen here, just "what
row does this stock number or last-6-VIN fragment point to."

Moved verbatim from the original reconcile.py -- no logic changes.
"""

import pandas as pd

from lotsync.sync.normalizer import last6, stock_prefix


def build_tekion_lookup(tekion_df: pd.DataFrame):
    by_stock, by_last6, prefixes = {}, {}, set()
    for idx, row in tekion_df.iterrows():
        stock_key = str(row["Stock #"]).strip().upper()
        by_stock[stock_key] = idx
        by_last6.setdefault(last6(row["VIN #"]), []).append(idx)
        p = stock_prefix(stock_key)
        if p:
            prefixes.add(p)
    return by_stock, by_last6, prefixes


def build_sold_lookup(sold_df: pd.DataFrame):
    by_stock, by_last6 = {}, {}
    for idx, row in sold_df.iterrows():
        by_stock[str(row["Stock #"]).strip().upper()] = idx
        by_last6.setdefault(last6(row["VIN #"]), []).append(idx)
    return by_stock, by_last6
