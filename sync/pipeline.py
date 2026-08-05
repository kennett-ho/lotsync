"""
Phase 3, Sprint 4 -- thin orchestration layer behind the Inventory Sync
API endpoint (api/routers/inventory_sync.py). Reuses the exact same
importer/sync/rules/reports functions main.py already drives -- this
module does not reimplement or duplicate any reconciliation logic. It
exists only to answer two questions main.py never had to: which of the
six sources were actually uploaded this run, and how do six independent
per-source SyncRuns become one coherent "sync" response.

Sources not uploaded this run are represented by an empty DataFrame
carrying that source's real columns (see _EMPTY_COLUMNS below) rather
than omitted entirely. This is a valid-input-shape decision, not new
business logic: every function in sync/reconciler.py that only accesses
columns inside an iterrows() loop already behaves correctly on a
zero-row DataFrame regardless of its columns (the loop body never runs).
The exceptions are build_tracker_install_tasks (called by
generate_install_tasks) and find_tekion_sync_conflicts, which each do a
handful of *vectorized* column accesses outside any loop
(tekion_df["is_internal_fleet"], sold_df["VIN #"], mdd_df["Dealership"],
recovr_df["Paired"]) that would KeyError on a truly columnless empty
DataFrame -- and enrich_with_rapidrecon, which needs rapidrecon_df to
have a "VIN" column for its own rename/drop_duplicates step even when
empty. _EMPTY_COLUMNS matches each importer's actual real-column output
(raw CSV columns plus the handful of derived columns each importer adds)
so these stand-ins are indistinguishable, column-wise, from "that source
was uploaded and happened to contain zero rows."

sync/reconciler.py, sync/matcher.py, rules/validation.py, and main.py are
NOT modified by this module.
"""

import datetime

import pandas as pd

from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.importers.mdd import load_mdd_not_paired
from lotsync.importers.recovr import load_recovr_full
from lotsync.importers.rapidrecon import load_rapidrecon
from lotsync.sync.reconciler import (
    reconcile_keyper_tekion, build_incoming_or_missing_investigate,
    build_sold_vehicles_report, build_tracker_install_tasks,
    enrich_with_rapidrecon, persist_tekion_observations,
    persist_mdd_observations, persist_recovr_observations,
    persist_rapidrecon_observations, generate_install_tasks,
    generate_key_out_aging_recommendations,
)
from lotsync.rules.validation import find_tekion_sync_conflicts
from lotsync.reports.writer import write_reports
from lotsync.database.repository import sync_run as sync_run_ctx

# One entry per upload slot. Matches each importer's real output columns
# exactly (raw CSV columns, plus load_tekion()'s derived
# "is_internal_fleet" and load_rapidrecon()'s upper-cased "New/Used") --
# see this module's docstring for why. "keyper" needs no derived
# identifier_type/identifier_value/checkout_dt columns: nothing in
# sync/reconciler.py ever accesses keyper_df's columns outside an
# iterrows() loop, so an empty keyper_df is safe with only its raw
# columns present.
_EMPTY_COLUMNS = {
    "tekion": ["Stock #", "VIN #", "Status", "Stocked In Date", "Year Make Model",
               "is_internal_fleet"],
    "sold": ["Stock #", "VIN #", "Status", "Sold Date", "Year Make Model"],
    "keyper": ["name", "description", "Status", "User", "Removal Type", "Cabinet",
               "System", "Location", "Reason", "Checkout Date"],
    "mdd": ["vin", "stock", "year", "make", "model", "Dealership", "Geofence"],
    "recovr": ["VIN", "Stock Number", "Paired", "Year", "Make", "Model"],
    "rapidrecon": ["VIN", "Step", "DIS", "DIR", "Priority", "Recall", "New/Used"],
}

# Upload-slot name -> the vehicle-identifying column used to count
# "vehicles processed" (see run_inventory_sync's vehicles_processed note).
_VIN_COLUMN = {
    "tekion": "VIN #", "sold": "VIN #", "mdd": "vin", "recovr": "VIN", "rapidrecon": "VIN",
}


def _empty_df(source: str) -> pd.DataFrame:
    return pd.DataFrame(columns=_EMPTY_COLUMNS[source])


def _count(db_conn, table: str) -> int:
    return db_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _sync_run_row(db_conn, sync_run_id: int) -> dict:
    row = db_conn.execute(
        "SELECT sync_run_id, source, status, started_at, completed_at, records_processed "
        "FROM sync_run WHERE sync_run_id = ?",
        (sync_run_id,),
    ).fetchone()
    keys = ("sync_run_id", "source", "status", "started_at", "completed_at", "records_processed")
    return dict(zip(keys, row))


def run_inventory_sync(file_paths: dict, *, store_name: str, sync_date,
                        day_out_buckets, incoming_missing_buckets, new_car_buckets,
                        internal_fleet_vins, db_conn, out_dir: str = None) -> dict:
    """
    file_paths: dict with any subset of the keys "tekion", "sold",
    "keyper", "mdd", "recovr", "rapidrecon" -> filesystem path of that
    source's uploaded file this run. A missing/None key means that
    source was not uploaded this run.

    Returns a plain dict (the API router turns it into SyncSummaryDTO):
        {
            "triggered_at": ISO timestamp shared by every SyncRun this
                run created,
            "sync_runs": [{"sync_run_id", "source", "status",
                "started_at", "completed_at", "records_processed"}, ...],
                one per source that was actually uploaded -- a source not
                uploaded gets no SyncRun row at all, matching how
                Phase 2's persist_* functions have always treated "no
                data" (a no-op, not a zero-value claim).
            "vehicles_processed": count of distinct VINs seen across
                every uploaded source this run (an implementation
                decision -- see this function's docstring),
            "exceptions_found": len(exceptions) from
                reconcile_keyper_tekion's own return value,
            "tasks_generated": task rows inserted during this run,
            "recommendations_generated": recommendation rows inserted
                during this run,
            "warnings": [str, ...] -- see generate_install_tasks'
                docstring; currently populated only when "keyper" is
                not in uploaded, since RecovR-related task generation
                requires Keyper as evidence and is skipped entirely
                rather than silently producing zero tasks.
        }
    """
    triggered_at = datetime.datetime.now().isoformat()
    uploaded = {k for k, v in file_paths.items() if v}

    keyper_df = load_keyper(path=file_paths["keyper"]) if "keyper" in uploaded else _empty_df("keyper")
    tekion_df = (load_tekion(internal_fleet_vins, path=file_paths["tekion"])
                 if "tekion" in uploaded else _empty_df("tekion"))
    sold_df = load_tekion_sold(path=file_paths["sold"]) if "sold" in uploaded else _empty_df("sold")
    mdd_df = load_mdd_not_paired(path=file_paths["mdd"]) if "mdd" in uploaded else _empty_df("mdd")
    recovr_df = load_recovr_full(path=file_paths["recovr"]) if "recovr" in uploaded else _empty_df("recovr")
    rapidrecon_df = load_rapidrecon(path=file_paths["rapidrecon"]) if "rapidrecon" in uploaded else _empty_df("rapidrecon")

    source_frames = {
        "tekion": tekion_df, "sold": sold_df, "keyper": keyper_df,
        "mdd": mdd_df, "recovr": recovr_df, "rapidrecon": rapidrecon_df,
    }
    vehicles_processed = set()
    for source, col in _VIN_COLUMN.items():
        if source in uploaded:
            vehicles_processed.update(str(v).strip() for v in source_frames[source][col])

    sync_runs = []

    def _persist(source: str, records_len: int, work):
        if source not in uploaded:
            return
        with sync_run_ctx(db_conn, source, records_processed=records_len,
                           started_at=triggered_at) as run_id:
            work(run_id)
        sync_runs.append(_sync_run_row(db_conn, run_id))

    # Keyper's own reconciliation walk also needs Tekion/Sold regardless
    # of whether either was uploaded this run -- an un-uploaded source's
    # empty stand-in makes every Keyper record route to
    # flag_to_controller/data_quality_exceptions the same way main.py
    # already treats a genuinely unmatched record. Called exactly once
    # either way (unlike the other four sources' simple skip-if-absent
    # _persist calls below): reconcile_keyper_tekion's return values feed
    # the CSV reports regardless of whether Keyper was uploaded, and
    # calling it twice would double-persist (its db_conn=None guard is
    # per db_conn, not per sync_run_id -- passing a real db_conn with
    # sync_run_id=None still writes, it just tags the Event with no
    # provenance).
    if "keyper" in uploaded:
        with sync_run_ctx(db_conn, "keyper", records_processed=len(keyper_df),
                           started_at=triggered_at) as run_id:
            fully_verified, key_out_aging, flag_to_controller, exceptions, matched_idx = \
                reconcile_keyper_tekion(keyper_df, tekion_df, sold_df, sync_date,
                                         day_out_buckets, db_conn=db_conn, sync_run_id=run_id)
        sync_runs.append(_sync_run_row(db_conn, run_id))
    else:
        fully_verified, key_out_aging, flag_to_controller, exceptions, matched_idx = \
            reconcile_keyper_tekion(keyper_df, tekion_df, sold_df, sync_date,
                                     day_out_buckets, db_conn=None, sync_run_id=None)

    # Tekion Unsold and Tekion Sold are independent upload slots (per this
    # sprint's own instruction), but persist_tekion_observations already
    # walks both dataframes as two independent loops within one function
    # -- so this fires whenever EITHER is present, not only when both
    # are, and the empty stand-in for whichever wasn't uploaded makes its
    # loop correctly do nothing. Both still land under one "tekion"
    # SyncRun, matching main.py's existing single combined SyncRun for
    # this source.
    if "tekion" in uploaded or "sold" in uploaded:
        with sync_run_ctx(db_conn, "tekion", records_processed=len(tekion_df) + len(sold_df),
                           started_at=triggered_at) as run_id:
            persist_tekion_observations(tekion_df, sold_df, db_conn=db_conn, sync_run_id=run_id)
        sync_runs.append(_sync_run_row(db_conn, run_id))

    _persist("mdd", len(mdd_df),
              lambda run_id: persist_mdd_observations(mdd_df, db_conn=db_conn, sync_run_id=run_id))
    _persist("recovr", len(recovr_df),
              lambda run_id: persist_recovr_observations(recovr_df, db_conn=db_conn, sync_run_id=run_id))
    _persist("rapidrecon", len(rapidrecon_df),
              lambda run_id: persist_rapidrecon_observations(rapidrecon_df, db_conn=db_conn, sync_run_id=run_id))

    tasks_before = _count(db_conn, "task")
    recommendations_before = _count(db_conn, "recommendation")

    # Sprint 3.8: fully_verified/key_out_aging are only passed through
    # when Keyper was actually uploaded this run -- "keyper" not in
    # uploaded must produce None, not reconcile_keyper_tekion's own
    # (real, just built from an empty keyper_df) empty DataFrames, or
    # generate_install_tasks couldn't tell "Keyper ran and found
    # nothing" apart from "Keyper wasn't part of this sync" -- see
    # that function's own docstring for why the distinction matters.
    warnings = generate_install_tasks(
        tekion_df, sold_df, mdd_df, recovr_df, store_name, db_conn=db_conn,
        rapidrecon_df=rapidrecon_df,
        fully_verified_df=fully_verified if "keyper" in uploaded else None,
        key_out_aging_df=key_out_aging if "keyper" in uploaded else None,
    )
    # Guarded on len(), not called unconditionally like main.py's
    # equivalent line: key_out_aging is built via pd.DataFrame(list) in
    # reconcile_keyper_tekion, which returns a genuinely COLUMNLESS empty
    # DataFrame when the list is empty (no Keyper file this run, or zero
    # Out-and-matched records) -- generate_key_out_aging_recommendations
    # then KeyErrors on key_out_aging_df["aging_bucket"], a real gap this
    # sprint's partial-source testing surfaced (main.py never hits this,
    # since every real sync has at least one Keyper "Out" record so far).
    # Not fixed in sync/reconciler.py itself -- see PHASE_3_SPRINT_4_REVIEW.md.
    if len(key_out_aging):
        generate_key_out_aging_recommendations(key_out_aging, day_out_buckets, db_conn=db_conn)

    tasks_generated = _count(db_conn, "task") - tasks_before
    recommendations_generated = _count(db_conn, "recommendation") - recommendations_before

    if out_dir is not None:
        incoming_or_missing = build_incoming_or_missing_investigate(
            tekion_df, matched_idx, sync_date, incoming_missing_buckets, new_car_buckets)
        incoming_or_missing = enrich_with_rapidrecon(incoming_or_missing, "tekion_vin", rapidrecon_df)
        sold_report = build_sold_vehicles_report(sold_df, keyper_df, recovr_df, sync_date)
        tracker_tasks = build_tracker_install_tasks(
            tekion_df, sold_df, mdd_df, recovr_df, store_name,
            rapidrecon_df=rapidrecon_df,
            fully_verified_df=fully_verified if "keyper" in uploaded else None,
            key_out_aging_df=key_out_aging if "keyper" in uploaded else None,
        )
        sync_conflicts = find_tekion_sync_conflicts(tekion_df, sold_df)

        write_reports({
            "fully_verified_report.csv": fully_verified,
            "key_out_aging_report.csv": key_out_aging,
            "flag_to_controller_report.csv": flag_to_controller,
            "data_quality_exceptions.csv": exceptions,
            "incoming_or_missing_investigate_report.csv": incoming_or_missing,
            "sold_vehicles_report.csv": sold_report,
            "tracker_install_tasks.csv": tracker_tasks,
            "tekion_sync_conflicts.csv": sync_conflicts,
        }, out_dir)

    return {
        "triggered_at": triggered_at,
        "sync_runs": sync_runs,
        "vehicles_processed": len(vehicles_processed),
        "exceptions_found": len(exceptions),
        "tasks_generated": tasks_generated,
        "recommendations_generated": recommendations_generated,
        "warnings": warnings,
    }
