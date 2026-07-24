"""
NOT YET SPLIT OUT -- tracker-install logic (build_tracker_install_tasks)
currently lives in sync/reconciler.py, not here.

Honest reason: the MDD/RecovR "missing device" logic is tightly
interleaved with cross-source matching mechanics (store scoping via
Tekion prefixes, sold-vehicle exclusion via VIN lookups) that belong to
sync/, not rules/. Splitting it here today would fragment working
logic across two files without actually decoupling anything -- the
matching and the business rule are still the same code, just in two
places.

This becomes a clean split once Vehicle objects exist (Phase 2): the
matching mechanics move fully into building a Vehicle's mdd_status and
recovr_status fields, and this module becomes the actual business rule
-- "given a Vehicle's current state, does it need a tracker install
task" -- operating on the object instead of raw dataframes.
"""
