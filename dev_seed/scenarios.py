"""
Sprint 04 -- the QA dealership's scenario roster and source files.

Every table below is a direct transcription of SYNTHETIC_QA_MATRIX.md;
the scenario ID in each row's comment is the traceability link. The
seed is TWO consecutive sync days replayed through the real pipeline:

    Day 1  sync date 2026-07-20   baseline state
    Day 2  sync date 2026-07-21   the QA REFERENCE DATE -- transitions

Deterministic time strategy (matrix, "Deterministic time strategy"):
every date the business rules read (checkout dates, stocked-in dates,
sold dates, both sync dates) is a fixed calendar value expressed here
as days-before-REFERENCE_DATE. Aging math runs against the sync date
passed to the pipeline, never the wall clock, so "7 days out" stays
7 days out no matter when the seed is executed. Only display-oriented
columns the rules never read (observed_at, created_at, sync-run
timing) carry wall-clock values.

Source-file column layouts replicate each importer's real contract
exactly (importers/*.py) -- these stand-ins must be indistinguishable,
column-wise, from real exports, the same standard sync/pipeline.py's
_EMPTY_COLUMNS already sets.
"""

import datetime

import pandas as pd

REFERENCE_DATE = datetime.datetime(2026, 7, 21)   # Day 2's sync date
DAY1_SYNC_DATE = datetime.datetime(2026, 7, 20)
DAY2_SYNC_DATE = REFERENCE_DATE

STORE_NAME = "Mark Kia"  # the deployment's own configured store identity
OTHER_STORE_NAME = "QA Other Store"  # QA-MDD-003's store-filter probe

# QA-FLEET-001 -- excluded from active_vins by load_tekion, the same
# mechanism the real config workbook's Excluded VINs sheet feeds.
INTERNAL_FLEET_VINS = {"1QATEST0000000081"}


def _ago(days: int) -> datetime.datetime:
    return REFERENCE_DATE - datetime.timedelta(days=days)


def _keyper_date(days_before_reference: int) -> str:
    # Keyper export format: %m/%d/%Y %H:%M (importers/keyper.py).
    # Checkouts sit at midnight so days-out math is exact integers
    # against the midnight sync dates.
    dt = _ago(days_before_reference)
    return f"{dt.month}/{dt.day}/{dt.year} 0:00"


def _tekion_date(days_before_reference: int) -> str:
    # Tekion export format: %b %d %Y (sync/reconciler.py's parses).
    return _ago(days_before_reference).strftime("%b %d %Y")


# ---------------------------------------------------------------------------
# Vehicle identities: scenario ID -> (VIN, stock, display name).
# VINs are 1QATEST + 10 digits (17 chars) -- see the matrix's synthetic
# identity rules. Last-6 suffixes are unique except the deliberate
# QA-AMB pair (both end 888555, the ambiguity under test).
# ---------------------------------------------------------------------------
VEHICLES = {
    "QA-BASE-001":      ("1QATEST0000000001", "QA1001",  "2024 QA Sedan LX"),
    "QA-BASE-002":      ("1QATEST0000000002", "QA1002",  "2024 QA Sedan EX"),
    "QA-BASE-003":      ("1QATEST0000000003", "QA1003",  "2023 QA Hatch S"),
    "QA-RECOVR-001":    ("1QATEST0000000011", "QA1011",  "2024 QA SUV LX"),
    "QA-RECOVR-002":    ("1QATEST0000000012", "QA1012",  "2024 QA SUV EX"),
    "QA-RECOVR-003":    ("1QATEST0000000013", "QA1013",  "2024 QA SUV GT"),
    "QA-RECOVR-004":    ("1QATEST0000000014", "QA1014",  "2022 QA Truck LT"),
    "QA-RECOVR-005":    ("1QATEST0000777666", "QA1015",  "2023 QA Coupe R"),
    "QA-RECOVR-006":    ("1QATEST0000000016", "QA1016",  "2024 QA Coupe S"),
    "QA-KEY-000":       ("1QATEST0000000020", "QA1020",  "2024 QA Mini A"),
    "QA-KEY-001":       ("1QATEST0000000021", "QA1021",  "2024 QA Mini B"),
    "QA-KEY-003":       ("1QATEST0000000022", "QA1022",  "2024 QA Mini C"),
    "QA-KEY-007":       ("1QATEST0000000023", "QA1023",  "2024 QA Mini D"),
    "QA-KEY-014":       ("1QATEST0000000024", "QA1024",  "2024 QA Mini E"),
    "QA-KEY-025":       ("1QATEST0000000025", "QA1025",  "2024 QA Mini F"),
    "QA-KEY-030":       ("1QATEST0000000026", "QA1026",  "2024 QA Mini G"),
    "QA-KEY-PAIRED":    ("1QATEST0000000027", "QA1027",  "2024 QA Mini H"),
    "QA-WHOLESALE-001": ("1QATEST0000000031", "QA1031",  "2021 QA Wagon W1"),
    "QA-WHOLESALE-002": ("1QATEST0000000032", "QA1032",  "2021 QA Wagon W2"),
    "QA-AUCTION-001":   ("1QATEST0000000033", "QA1033",  "2021 QA Wagon A1"),
    "QA-ARCHIVE-001":   ("1QATEST0000000034", "QA1034",  "2022 QA Van V1"),
    "QA-ARCHIVE-002":   ("1QATEST0000000035", "QA1035",  "2022 QA Van V2"),
    "QA-SOLD-001":      ("1QATEST0000000041", "QA1041",  "2023 QA Sport S1"),
    "QA-SOLD-002":      ("1QATEST0000000042", "QA1042",  "2023 QA Sport S2"),
    "QA-CONFLICT-001":  ("1QATEST0000000051", "QA1051",  "2024 QA Conflict C1"),
    "QA-CONFLICT-002":  ("1QATEST0000000052", "QA1052",  "2024 QA Conflict C2"),
    "QA-AMB-A":         ("1QATEST0000888555", "QA1061",  "2024 QA Twin Alpha"),
    "QA-AMB-B":         ("1QATEST0001888555", "QA1062",  "2024 QA Twin Beta"),
    "QA-INCOMING-001":  ("1QATEST0000000071", "K91001",  "2026 QA New Order"),
    "QA-INCOMING-002":  ("1QATEST0000000072", "QA903DM", "2026 QA Damaged Arrival"),
    "QA-FLEET-001":     ("1QATEST0000000081", "QA1081",  "2024 QA Shuttle"),
    "QA-MDD-001":       ("1QATEST0000000091", "QA1091",  "2024 QA Crossover X1"),
    "QA-MULTI-001":     ("1QATEST0000000092", "QA1092",  "2024 QA Crossover X2"),
    "QA-MDD-003":       ("1QATEST0000000093", "QA1093",  "2024 QA Crossover X3"),
}


def _vin(scenario_id: str) -> str:
    return VEHICLES[scenario_id][0]


def _stock(scenario_id: str) -> str:
    return VEHICLES[scenario_id][1]


def _name(scenario_id: str) -> str:
    return VEHICLES[scenario_id][2]


# ---------------------------------------------------------------------------
# Tekion Master/Unsold list.
# (scenario_id, stocked-in days before reference)
# Day 1 = everything except the three never-active records
# (QA-ARCHIVE-002 / QA-SOLD-001 / QA-CONFLICT-002 live only in the sold
# export). Day 2 removes QA-SOLD-002 and QA-AMB-B -- they sell.
# QA-CONFLICT-001 stays in BOTH lists BOTH days: that contradiction is
# the scenario.
# ---------------------------------------------------------------------------
_MASTER_DAY1 = [
    ("QA-BASE-001", 6), ("QA-BASE-002", 6), ("QA-BASE-003", 6),
    ("QA-RECOVR-001", 6), ("QA-RECOVR-002", 6), ("QA-RECOVR-003", 6),
    ("QA-RECOVR-004", 5),   # no Keyper key; 5 days -> Trade/Other "Overdue"
    ("QA-RECOVR-005", 6), ("QA-RECOVR-006", 6),
    ("QA-KEY-000", 6), ("QA-KEY-001", 6), ("QA-KEY-003", 6),
    ("QA-KEY-007", 6), ("QA-KEY-014", 15), ("QA-KEY-025", 26),
    ("QA-KEY-030", 31), ("QA-KEY-PAIRED", 11),
    ("QA-WHOLESALE-001", 6), ("QA-WHOLESALE-002", 11),
    ("QA-AUCTION-001", 6), ("QA-ARCHIVE-001", 6),
    ("QA-SOLD-002", 6),
    ("QA-CONFLICT-001", 10),
    ("QA-AMB-A", 6), ("QA-AMB-B", 6),
    ("QA-INCOMING-001", 2),  # K-digits stock -> New Car (Awaiting Dropoff)
    ("QA-INCOMING-002", 11), # DM stock -> New (Damaged - In Repair)
    ("QA-FLEET-001", 6),
    ("QA-MDD-001", 6), ("QA-MULTI-001", 6), ("QA-MDD-003", 6),
]
_MASTER_DAY2 = [row for row in _MASTER_DAY1
                if row[0] not in ("QA-SOLD-002", "QA-AMB-B")]

# ---------------------------------------------------------------------------
# Tekion Sold list. (scenario_id, stock override or None, sold days
# before reference). QA-CONFLICT-002 appears TWICE with two different
# stock numbers -- the internally contradictory export whose accepted
# re-fire behavior the matrix documents.
# ---------------------------------------------------------------------------
_SOLD_DAY1 = [
    ("QA-ARCHIVE-002", None, 11),
    ("QA-SOLD-001", None, 11),
    ("QA-CONFLICT-001", None, 2),
    ("QA-CONFLICT-002", "QA1052", 20),
    ("QA-CONFLICT-002", "QA1052B", 16),
]
_SOLD_DAY2 = _SOLD_DAY1 + [
    ("QA-SOLD-002", None, 1),   # sells between the two syncs -> Moot
    ("QA-AMB-B", None, 1),      # sells -> the 888555 ambiguity resolves
]

# ---------------------------------------------------------------------------
# Keyper. (name, status, checkout days before reference)
# Names are stock numbers except the three identity-family records.
# Checkout dates only carry business meaning on "Out" rows (the aging
# clock); "In" rows get a fixed nominal date the rules never read.
# ---------------------------------------------------------------------------
_KEYPER_DAY1 = [
    ("QA1001", "In", 6),        # QA-BASE-001
    ("QA1002", "In", 6),        # QA-BASE-002
    ("QA1003", "In", 6),        # QA-BASE-003
    ("QA1011", "In", 6),        # QA-RECOVR-001
    ("QA1012", "Out", 1),       # QA-RECOVR-002 -- 1 day out at reference
    ("QA1013", "Out", 7),       # QA-RECOVR-003 -- 7 days out
    ("QA1015", "In", 6),        # QA-RECOVR-005
    ("QA1016", "In", 6),        # QA-RECOVR-006
    ("QA1020", "In", 6),        # QA-KEY-000 -- flips Out on Day 2
    ("QA1021", "Out", 1),       # QA-KEY-001 -- 1 day
    ("QA1022", "Out", 3),       # QA-KEY-003 -- 3 days (crosses on Day 2)
    ("QA1023", "Out", 7),       # QA-KEY-007
    ("QA1024", "Out", 14),      # QA-KEY-014
    ("QA1025", "Out", 25),      # QA-KEY-025 -- exact >=25 boundary
    ("QA1026", "Out", 30),      # QA-KEY-030
    ("QA1027", "Out", 10),      # QA-KEY-PAIRED
    ("QA1031", "In", 6),        # QA-WHOLESALE-001
    ("QA1032", "Out", 10),      # QA-WHOLESALE-002
    ("QA1033", "In", 6),        # QA-AUCTION-001
    ("QA1034", "In", 6),        # QA-ARCHIVE-001
    ("QA1041", "In", 6),        # QA-SOLD-001 -- sold key never removed
    ("QA1042", "In", 6),        # QA-SOLD-002 -- removed on Day 2
    ("QA1091", "In", 6),        # QA-MDD-001
    ("QA1092", "In", 6),        # QA-MULTI-001
    ("QA1093", "In", 6),        # QA-MDD-003
    ("888555", "In", 6),        # QA-PEND-003 -- ambiguous last-6 (Day 1)
    ("9755", "In", 6),          # QA-PEND-001 -- auto-generated numeric
    ("#QA-ODD", "In", 6),       # QA-PEND-002 -- unrecognized
    ("GOLF CART", "Out", 40),   # non-vehicle key -- skipped entirely
]


def _keyper_day2():
    rows = []
    for name, status, days in _KEYPER_DAY1:
        if name == "QA1042":
            continue            # QA-SOLD-002 sold; key correctly removed
        if name == "QA1020":
            # QA-KEY-000: In -> Out, checked out ON the reference date
            # (0 days out -- "Should be here", no task, but a real
            # keyper_observed transition with event_time populated).
            rows.append(("QA1020", "Out", 0))
            continue
        rows.append((name, status, days))
    return rows


# ---------------------------------------------------------------------------
# RecovR full list. (scenario_id or raw fragment, stock, paired day1,
# paired day2). QA-RECOVR-005 is reported under a 6-char VIN fragment
# -- the unique-last-6 resolution path.
# ---------------------------------------------------------------------------
_RECOVR = [
    ("QA-BASE-001",   None,     "Yes", "Yes"),
    ("QA-BASE-002",   None,     "Yes", "Yes"),
    ("QA-RECOVR-001", None,     "No",  "No"),
    ("QA-RECOVR-002", None,     "No",  "No"),
    ("QA-RECOVR-003", None,     "No",  "No"),
    ("QA-RECOVR-004", None,     "No",  "No"),
    ("QA-RECOVR-005", "777666", "No",  "No"),   # fragment, resolves uniquely
    ("QA-RECOVR-006", None,     "No",  "Yes"),  # pairs on Day 2 -> Honored
    ("QA-KEY-PAIRED", None,     "Yes", "Yes"),
    ("QA-WHOLESALE-001", None,  "No",  "No"),
    ("QA-WHOLESALE-002", None,  "No",  "No"),
    ("QA-AUCTION-001", None,    "No",  "No"),
    ("QA-ARCHIVE-001", None,    "No",  "No"),
    ("QA-SOLD-001",   None,     "Yes", "Yes"),
    ("QA-SOLD-002",   None,     "No",  "No"),
    ("QA-MULTI-001",  None,     "No",  "No"),
]

# ---------------------------------------------------------------------------
# MDD "not paired" exception list. (scenario_id, dealership)
# QA-SOLD-001's row proves sold VINs never generate MDD work;
# QA-MDD-003's other-store row proves the task-generation store filter
# while the persist path (deliberately VIN-trust-based, not
# store-filtered) still records the observation.
# ---------------------------------------------------------------------------
_MDD = [
    ("QA-WHOLESALE-001", STORE_NAME),
    ("QA-MDD-001", STORE_NAME),
    ("QA-MULTI-001", STORE_NAME),
    ("QA-SOLD-001", STORE_NAME),
    ("QA-MDD-003", OTHER_STORE_NAME),
]

# ---------------------------------------------------------------------------
# RapidRecon. (scenario_id, step day1, step day2)
# Steps compare case-insensitively; WHOLESALE / AT AUCTION are the two
# confirmed exclusion values, Archive is confirmed NOT an exclusion.
# ---------------------------------------------------------------------------
_RAPIDRECON = [
    ("QA-BASE-001", "Inspection", "Inspection"),  # unchanged -> freshness only
    ("QA-BASE-002", "Inspection", "Detail"),      # Step change -> one new event
    ("QA-WHOLESALE-001", "WHOLESALE", "WHOLESALE"),
    ("QA-WHOLESALE-002", "WHOLESALE", "WHOLESALE"),
    ("QA-AUCTION-001", "AT AUCTION", "AT AUCTION"),
    ("QA-ARCHIVE-001", "Archive", "Archive"),
    ("QA-ARCHIVE-002", "Archive", "Archive"),
]


# ---------------------------------------------------------------------------
# DataFrame builders -- exact importer column contracts.
# ---------------------------------------------------------------------------

def _master_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "Stock #": _stock(sid), "VIN #": _vin(sid), "Status": "Stocked In",
            "Year Make Model": _name(sid),
            "Stocked In Date": _tekion_date(days),
        } for sid, days in rows],
        columns=["Stock #", "VIN #", "Status", "Year Make Model", "Stocked In Date"],
    )


def _sold_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "Stock #": stock if stock is not None else _stock(sid),
            "VIN #": _vin(sid), "Status": "Sold",
            "Year Make Model": _name(sid),
            "Sold Date": _tekion_date(days),
        } for sid, stock, days in rows],
        columns=["Stock #", "VIN #", "Status", "Year Make Model", "Sold Date"],
    )


def _keyper_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "name": name, "description": "USED", "Status": status, "User": "QA",
            "Removal Type": "Legal", "Cabinet": "C1", "System": "QA-Keyper",
            "Location": "QA", "Reason": "",
            "Checkout Date": _keyper_date(days),
        } for name, status, days in rows],
        columns=["name", "description", "Status", "User", "Removal Type",
                 "Cabinet", "System", "Location", "Reason", "Checkout Date"],
    )


def _recovr_frame(day: int) -> pd.DataFrame:
    records = []
    for sid, raw_vin, paired1, paired2 in _RECOVR:
        year, rest = _name(sid).split(" ", 1)
        make, model = rest.split(" ", 1)
        records.append({
            "VIN": raw_vin if raw_vin is not None else _vin(sid),
            "Stock Number": _stock(sid),
            "Paired": paired1 if day == 1 else paired2,
            "Year": year, "Make": make, "Model": model,
        })
    return pd.DataFrame(
        records, columns=["VIN", "Stock Number", "Paired", "Year", "Make", "Model"]
    )


def _mdd_frame() -> pd.DataFrame:
    records = []
    for sid, dealership in _MDD:
        year, rest = _name(sid).split(" ", 1)
        make, model = rest.split(" ", 1)
        records.append({
            "vin": _vin(sid), "stock": _stock(sid),
            "year": year, "make": make, "model": model,
            "Dealership": dealership, "Geofence": "Not Paired",
        })
    return pd.DataFrame(
        records, columns=["vin", "stock", "year", "make", "model", "Dealership", "Geofence"]
    )


def _rapidrecon_frame(day: int) -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "VIN": _vin(sid), "Step": step1 if day == 1 else step2,
            "DIS": 10, "DIR": 5, "Priority": "Medium", "Recall": 0,
            "New/Used": "Used",
        } for sid, step1, step2 in _RAPIDRECON],
        columns=["VIN", "Step", "DIS", "DIR", "Priority", "Recall", "New/Used"],
    )


def source_frames(day: int) -> dict:
    """The six source exports for one QA day, keyed by upload-slot name."""
    if day not in (1, 2):
        raise ValueError(f"QA seed has exactly two days; got day={day}")
    return {
        "tekion": _master_frame(_MASTER_DAY1 if day == 1 else _MASTER_DAY2),
        "sold": _sold_frame(_SOLD_DAY1 if day == 1 else _SOLD_DAY2),
        "keyper": _keyper_frame(_KEYPER_DAY1 if day == 1 else _keyper_day2()),
        "mdd": _mdd_frame(),
        "recovr": _recovr_frame(day),
        "rapidrecon": _rapidrecon_frame(day),
    }


_FILENAMES = {
    # Names chosen to satisfy utils/file_resolution.py's conventions
    # too, should anyone point LOTSYNC_UPLOADS_DIR at a dump of these;
    # the seeder itself always passes explicit paths.
    "tekion": "QA_Tekion_Unsold_Report.csv",
    "sold": "QA_Tekion_Sold_Report.csv",
    "keyper": "QA_Keyper_Export.csv",
    "mdd": "QA_MDD_Not_Paired.csv",
    "recovr": "QA_RecovR_Kia_Export.csv",
    "rapidrecon": "QA_RapidRecon_Export.csv",
}


def write_source_files(day: int, directory: str) -> dict:
    """Write one QA day's six source CSVs; returns {slot: path}."""
    import os
    paths = {}
    for slot, frame in source_frames(day).items():
        path = os.path.join(directory, f"day{day}_{_FILENAMES[slot]}")
        frame.to_csv(path, index=False)
        paths[slot] = path
    return paths
