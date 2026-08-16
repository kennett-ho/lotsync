"""
Sprint 04 -- replays the QA dealership through the real pipeline.

Both QA days run through sync/pipeline.py's run_inventory_sync() --
the exact code path behind the production Inventory Sync API, which
itself reuses everything main.py drives. Nothing here inserts rows
directly; the standing database is the pipeline's own honest output
over deterministic source files, so the seed can never assert an
outcome the product wouldn't actually produce.

Bucket scales come from rules/aging.py's dealership-confirmed defaults
directly (not a config workbook) -- the seed asserts the shipped
rules, and reading them from the one canonical place means a future
retuning changes the seed's behavior the same run it changes the
product's.

Used by three callers with one shared code path:
- seed_dev.py (the operator seed for the deployed dev environment)
- tests/test_qa_dataset.py (the dual-engine assertion suite)
- the missing-source-day harness (run_single_day with a source subset)
"""

import shutil
import tempfile

from lotsync.rules.aging import (
    KEY_OUT_AGING_DEFAULT, INCOMING_MISSING_DEFAULT, NEW_CAR_DEFAULT,
)
from lotsync.sync.pipeline import run_inventory_sync
from lotsync.dev_seed.scenarios import (
    DAY1_SYNC_DATE, DAY2_SYNC_DATE, INTERNAL_FLEET_VINS, STORE_NAME,
    write_source_files,
)

_SYNC_DATES = {1: DAY1_SYNC_DATE, 2: DAY2_SYNC_DATE}
_ALL_SLOTS = ("tekion", "sold", "keyper", "mdd", "recovr", "rapidrecon")


def run_single_day(db_conn, day: int, sources=None, sync_date=None,
                   out_dir: str = None) -> dict:
    """
    Run ONE QA day through run_inventory_sync. `sources` limits which
    upload slots are present (None = all six) -- the missing-source-day
    scenarios (SYNTHETIC_QA_MATRIX.md family M) pass a subset here,
    exactly how the API behaves when an operator uploads a partial set.
    Returns run_inventory_sync's summary dict unchanged.
    """
    include = _ALL_SLOTS if sources is None else tuple(sources)
    unknown = set(include) - set(_ALL_SLOTS)
    if unknown:
        raise ValueError(f"unknown source slots: {sorted(unknown)}")

    workdir = tempfile.mkdtemp(prefix=f"dealerdoh-qa-day{day}-")
    try:
        paths = write_source_files(day, workdir)
        file_paths = {slot: paths[slot] for slot in include}
        return run_inventory_sync(
            file_paths,
            store_name=STORE_NAME,
            sync_date=sync_date if sync_date is not None else _SYNC_DATES[day],
            day_out_buckets=KEY_OUT_AGING_DEFAULT,
            incoming_missing_buckets=INCOMING_MISSING_DEFAULT,
            new_car_buckets=NEW_CAR_DEFAULT,
            internal_fleet_vins=INTERNAL_FLEET_VINS,
            db_conn=db_conn,
            out_dir=out_dir,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def run_qa_seed(db_conn, out_dir: str = None) -> list:
    """
    The full standing seed: Day 1 then Day 2 against an empty (or
    just-reset) database. CSV reports are written only for Day 2 (the
    current day) when out_dir is given -- Day 1 exists to establish
    history, not to leave stale reports around.

    Returns both days' summary dicts, in order.
    """
    day1 = run_single_day(db_conn, 1)
    day2 = run_single_day(db_conn, 2, out_dir=out_dir)
    return [day1, day2]
