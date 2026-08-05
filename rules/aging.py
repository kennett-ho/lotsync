"""
Default threshold scales for the three aging/priority reports. These
are the actual business rules; config/settings.py is only responsible
for reading overrides of these from oms_config.xlsx and falling back
to what's defined here if the workbook is missing or a sheet is empty.

If you're changing dealership behavior, prefer editing oms_config.xlsx
over editing these -- these are the fallback of last resort, not the
place day-to-day tuning should happen. These exist so the system still
runs sensibly even with no config file present.
"""

# Key Out Aging: Keyper "Out" + matched in Tekion, by days checked out.
# Resolves an overlap in the originally requested scale ("3-7" then
# "7-14" both included day 7) into non-overlapping tiers.
KEY_OUT_AGING_DEFAULT = [
    (0, "Should be here"),
    (1, "Might be here"),
    (3, "Investigate"),
    (7, "High Priority Investigate"),
    (14, "Possibly Sold, Verify"),
    (25, "Likely Sold, Verify to Remove from OMS"),
]

# Sprint 3.8 (Friday MVP task-generation refinements) -- the threshold at
# which sync/reconciler.py's build_tracker_install_tasks generates an
# "Investigate Checked-Out Key" Task. Deliberately the SAME 3 as
# KEY_OUT_AGING_DEFAULT's own "Investigate" tier above, not a separately
# invented number: that request's own prose ("keys should normally be
# returned within a day or two") would suggest 1-2 days, but this
# dealership's own already-confirmed scale explicitly still calls day 1
# "Might be here" -- not yet actionable. Day 3 is the first tier this
# dealership has already agreed is worth a human looking at. One
# consistent definition of "investigation-worthy," not two numbers that
# happen to start out equal -- if KEY_OUT_AGING_DEFAULT's tiers are ever
# retuned, review this constant alongside it.
#
# A plain constant "for now," per the original request's own framing --
# not yet a real oms_config.xlsx knob like KEY_OUT_AGING_DEFAULT itself
# can become (see config/settings.py). Promote it the same way if this
# dealership ever wants Task-generation timing decoupled from the
# aging-bucket display scale.
KEY_OUT_INVESTIGATE_THRESHOLD_DAYS = 3

# Incoming/Missing (Trade/Other): active in Tekion, no Keyper key,
# vehicle is presumed already physically on the lot. Grounded in the
# real workflow: fresh trades are checked every morning and stocked
# into Keyper by midshift, normally within 2 days.
INCOMING_MISSING_DEFAULT = [
    (0, "Within Normal Turnaround"),
    (3, "Overdue - Investigate (missed fresh trade or possible unmarked sale)"),
]

# New Car (Awaiting Dropoff): active in Tekion under a bare 'K' + digits
# stock number, no Keyper key expected until transport delivers the
# physical vehicle.
NEW_CAR_DEFAULT = [
    (0, "Awaiting Transport Dropoff"),
    (7, "Investigate"),
]
