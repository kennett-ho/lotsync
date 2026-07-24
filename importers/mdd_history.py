"""
NOT YET IMPLEMENTED -- no source file exists for this yet.

MDD currently only provides a "Not Paired" exception export (see
importers/mdd.py), not a full history of every beacon-to-vehicle
assignment. That gap means sold_vehicles_report.csv can flag a sold
vehicle's Keyper key and RecovR pairing as still-present, but cannot
confirm or deny whether its MDD beacon was removed -- it can only say
"unknown."

If a full MDD assignment/history export ever becomes available, this
module is where its import and normalization should live, and
sync/reconciler.py's build_sold_vehicles_report() is where the
"mdd_status: unknown" placeholder should be replaced with a real check
against it.
"""
