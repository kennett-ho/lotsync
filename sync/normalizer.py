"""
Structural normalization -- turning raw source-specific identifier
formats into a consistent shape. This is deliberately separate from
rules/inventory.py: normalizer.py answers "what kind of identifier IS
this and what's its value," a format question; rules/inventory.py
answers "what kind of VEHICLE is this," a business question. The two
get confused easily since both operate on the same stock-number string,
which is exactly why they're split.

Moved verbatim from the original reconcile.py -- no logic changes.
See ARCHITECTURE.md for why identifier classification looks the way it
does (Keyper has no VIN column, Tekion's Stock # sometimes IS a VIN
fragment, etc.).
"""

import re


def last6(vin: str) -> str:
    vin = str(vin).strip()
    return vin[-6:] if len(vin) >= 6 else vin


def stock_prefix(value: str) -> str:
    m = re.match(r"^([A-Za-z]+)", str(value).strip())
    return m.group(1).upper() if m else ""


def classify_keyper_identifier(name: str):
    """Return (identifier_type, normalized_value) for a Keyper 'name' field."""
    from lotsync.rules.inventory import NON_VEHICLE_KEY_NAMES

    raw = str(name).strip()
    if raw.upper() in NON_VEHICLE_KEY_NAMES:
        return "non_vehicle", None
    if re.match(r"^\d+$", raw):
        if len(raw) == 6:
            return "last6_vin", raw
        return "tekion_auto_generated_stock_number", raw
    if re.match(r"^[A-Za-z]", raw):
        return "stock_number", raw.upper()
    return "unrecognized", raw


def classify_tekion_stock(stock: str, vin: str):
    """Return (identifier_type, normalized_value) for a Tekion 'Stock #' field."""
    stock = str(stock).strip()
    if re.match(r"^\d+$", stock):
        if stock == last6(vin):
            return "last6_vin", stock
        return "tekion_auto_generated_stock_number", stock
    if re.match(r"^[A-Za-z]", stock):
        return "stock_number", stock.upper()
    return "unrecognized", stock
