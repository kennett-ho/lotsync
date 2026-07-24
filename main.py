"""
LotSync OMS - entry point.

This function should stay thin -- it orchestrates, it doesn't decide
anything. If you're adding a business rule, it almost certainly belongs
in rules/ or sync/, not here. See ARCHITECTURE.md before extending.
"""

import os

from lotsync.config.settings import (
    load_settings, load_day_out_buckets, load_incoming_missing_buckets,
    load_new_car_buckets, load_internal_fleet_vins,
)
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.importers.mdd import load_mdd_not_paired
from lotsync.importers.recovr import load_recovr_full
from lotsync.importers.rapidrecon import load_rapidrecon
from lotsync.sync.reconciler import (
    reconcile_keyper_tekion, build_incoming_or_missing_investigate,
    build_sold_vehicles_report, build_tracker_install_tasks,
    enrich_with_rapidrecon,
)
from lotsync.rules.validation import find_tekion_sync_conflicts
from lotsync.reports.writer import write_reports, print_summary
from lotsync.database.repository import connect as db_connect

# Overridable via LOTSYNC_OUT_DIR; defaults to a repo-relative
# location. (Previously hardcoded to /mnt/user-data/outputs, this
# project's original development sandbox path -- see
# utils/file_resolution.py for the same adjustment and why.)
OUT_DIR = os.environ.get(
    "LOTSYNC_OUT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "outputs")
)


def main():
    settings = load_settings()
    day_out_buckets = load_day_out_buckets()
    incoming_missing_buckets = load_incoming_missing_buckets()
    new_car_buckets = load_new_car_buckets()
    internal_fleet_vins = load_internal_fleet_vins()

    print(f"Using store_name='{settings['store_name']}', "
          f"sync_date={settings['sync_date'].date()}\n")

    keyper_df = load_keyper()
    tekion_df = load_tekion(internal_fleet_vins)
    sold_df = load_tekion_sold()
    mdd_df = load_mdd_not_paired()
    recovr_df = load_recovr_full()
    rapidrecon_df = load_rapidrecon()

    # Phase 2 Slice 1 (see IMPLEMENTATION_PLAN.md): additionally persist
    # Keyper's contribution to Vehicle/Event alongside the unchanged CSV
    # pipeline below. sync_run_id stays None until Slice 4 introduces the
    # SyncRun table -- not invented speculatively here.
    db_conn = db_connect()

    fully_verified, key_out_aging, flag_to_controller, exceptions, matched_idx = \
        reconcile_keyper_tekion(keyper_df, tekion_df, sold_df,
                                 settings["sync_date"], day_out_buckets,
                                 db_conn=db_conn, sync_run_id=None)

    incoming_or_missing = build_incoming_or_missing_investigate(
        tekion_df, matched_idx, settings["sync_date"],
        incoming_missing_buckets, new_car_buckets)
    incoming_or_missing = enrich_with_rapidrecon(
        incoming_or_missing, "tekion_vin", rapidrecon_df)
    sold_report = build_sold_vehicles_report(sold_df, keyper_df, recovr_df, settings["sync_date"])
    tracker_tasks = build_tracker_install_tasks(
        tekion_df, sold_df, mdd_df, recovr_df, settings["store_name"])
    sync_conflicts = find_tekion_sync_conflicts(tekion_df, sold_df)

    outputs = {
        "fully_verified_report.csv": fully_verified,
        "key_out_aging_report.csv": key_out_aging,
        "flag_to_controller_report.csv": flag_to_controller,
        "data_quality_exceptions.csv": exceptions,
        "incoming_or_missing_investigate_report.csv": incoming_or_missing,
        "sold_vehicles_report.csv": sold_report,
        "tracker_install_tasks.csv": tracker_tasks,
        "tekion_sync_conflicts.csv": sync_conflicts,
    }

    write_reports(outputs, OUT_DIR)
    print_summary(outputs, key_out_aging, flag_to_controller, sold_report, incoming_or_missing)
    db_conn.close()


if __name__ == "__main__":
    main()
