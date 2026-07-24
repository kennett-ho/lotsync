"""
Business rules for classifying what KIND of vehicle a Tekion record
represents, based on its stock number. Distinct from
sync/normalizer.py, which only asks whether an identifier is a stock
number or a VIN fragment -- a format question. This module asks a
business question: new car awaiting dropoff, damaged/in-repair, trade,
or a non-vehicle key entirely.

Moved verbatim from the original reconcile.py -- no logic changes.
"""

import re

# Keyper "name" values that are facility/equipment keys, not vehicles.
NON_VEHICLE_KEY_NAMES = {"GOLF", "GOLF CART", "NEW LOT KEY"}


def is_new_car_stock(stock: str) -> bool:
    """
    True only for a bare 'K' followed by digits and nothing else
    (e.g. K30707) -- confirmed against real data to align 100% with
    Tekion's own Stock Type = 'New', though it doesn't catch every New
    vehicle: some new-car stock numbers use a different format (letter
    suffix, different prefix) and fall through to the trade-vehicle
    bucket instead. This is the stock-number convention as described,
    not a reconstruction of Tekion's internal Stock Type field.

    Model year is deliberately NOT used as a signal here, even though
    it might seem intuitive -- this dealership also takes in current
    model-year vehicles (2026/27) as trade-ins, which get suffix-letter
    stock numbers (SL, A, etc.) same as any other trade. Year alone
    can't tell a new car apart from a same-year trade-in.
    """
    return bool(re.fullmatch(r"K\d+", str(stock).strip(), re.IGNORECASE))


def is_damaged_repair_stock(stock: str) -> bool:
    """
    True for a stock number ending in 'DM' -- a new vehicle that
    arrived damaged and went through repairs before it's ready for the
    lot. These aren't trade-ins and aren't awaiting transport either --
    they're physically at the dealership already, just not lot-ready,
    so neither existing bucket scale's assumptions fit them. No priority
    bucket is applied to this category yet; there's no dealership-
    confirmed typical repair duration to ground one against, so
    inventing a threshold here would repeat the same mistake made
    earlier with the original (unfounded) Incoming/Missing scale.
    """
    return bool(re.search(r"DM$", str(stock).strip(), re.IGNORECASE))
