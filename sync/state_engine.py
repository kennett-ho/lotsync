"""
Generic day-count-to-label evaluation. Deliberately has no knowledge of
WHICH scale it's evaluating (key-out aging, incoming/missing, new-car
dropoff) -- that's what makes it reusable across all three. The actual
threshold values live in rules/aging.py and config/settings.py, not
here.

This is the seam Phase 2 will grow into an actual state-transition
engine (Pending DMS Entry -> Vehicle Appears -> Generate Task, etc.);
right now it's a single pure function because that's all the current
business rules need. See ARCHITECTURE.md.
"""


def day_out_bucket(days: int, buckets) -> str:
    """
    buckets: list of (minimum_days, label) tuples, sorted ascending.
    Returns the label of the highest-threshold bucket that days
    qualifies for.
    """
    label = buckets[0][1]
    for lower, name in buckets:
        if days >= lower:
            label = name
    return label
