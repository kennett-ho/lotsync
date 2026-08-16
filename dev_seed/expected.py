"""
Sprint 04 -- machine-readable expected outcomes for the QA dealership.

This module is SYNTHETIC_QA_MATRIX.md's assertion form: every value
here restates a row of that document, keyed by scenario ID, and
tests/test_qa_dataset.py enforces it against a freshly seeded database
on whichever engine the suite is running. A regression cannot hide
behind coincidentally matching totals -- the per-scenario tables are
exhaustive (a scenario absent from OPEN_TASKS is asserted to have ZERO
open tasks, and per-vehicle event counts are asserted for every
vehicle, not summed).

If a deliberate business-rule change alters one of these values,
update the matrix document FIRST, then this module to match -- never
the other way around.
"""

from lotsync.dev_seed.scenarios import VEHICLES, REFERENCE_DATE  # noqa: F401

# ---------------------------------------------------------------------------
# Open (outstanding) tasks per scenario after Day 2. Scenarios not
# listed are asserted to hold zero open tasks -- the absence claims
# (Wholesale/At-Auction exclusions, the no-Keyper-evidence RecovR
# candidate, sold vehicles, the fleet vehicle...) are as load-bearing
# as the presence claims.
# ---------------------------------------------------------------------------
OPEN_TASKS = {
    "QA-RECOVR-001": ["install_recovr_device"],
    "QA-RECOVR-002": ["investigate_key_for_recovr"],
    "QA-RECOVR-003": ["investigate_checked_out_key", "investigate_key_for_recovr"],
    "QA-RECOVR-005": ["install_recovr_device"],
    "QA-KEY-003":    ["investigate_checked_out_key"],
    "QA-KEY-007":    ["investigate_checked_out_key"],
    "QA-KEY-014":    ["investigate_checked_out_key"],
    "QA-KEY-025":    ["investigate_checked_out_key"],
    "QA-KEY-030":    ["investigate_checked_out_key"],
    "QA-KEY-PAIRED": ["investigate_checked_out_key"],
    "QA-WHOLESALE-001": ["install_mdd_beacon"],
    "QA-ARCHIVE-001": ["install_recovr_device"],
    "QA-MDD-001":    ["install_mdd_beacon"],
    "QA-MULTI-001":  ["install_mdd_beacon", "install_recovr_device"],
}

# Terminal (Reality-discharged) tasks in the standing seed -- each
# produced by the real discharge path, never fabricated.
TERMINAL_TASKS = {
    "QA-RECOVR-006": ("install_recovr_device", "honored"),  # RecovR paired flip
    "QA-SOLD-002":   ("install_recovr_device", "moot"),     # sold before install
}

OPEN_TASK_TOTALS_BY_TYPE = {
    "install_recovr_device": 4,
    "investigate_key_for_recovr": 2,
    "investigate_checked_out_key": 7,
    "install_mdd_beacon": 3,
}

# Scenarios whose key-out-aging recommendation must exist (open,
# severity High, rule_source key_out_aging) -- the >=25-day
# most-severe-bucket rule. QA-KEY-025 sits exactly ON the boundary.
RECOMMENDATION_SCENARIOS = {"QA-KEY-025", "QA-KEY-030"}

# tekion_status='Sold' after Day 2 -> hidden from the default vehicle
# list, still fully reachable individually.
SOLD_SCENARIOS = {
    "QA-ARCHIVE-002", "QA-SOLD-001", "QA-SOLD-002",
    "QA-CONFLICT-001", "QA-CONFLICT-002", "QA-AMB-B",
}

# ---------------------------------------------------------------------------
# Standing event counts per scenario after Day 2, by event_type --
# the dedup contract in its most literal form: Day 2 re-observes every
# unchanged vehicle and these counts prove it added no Timeline noise.
# QA-CONFLICT-002's 4 tekion_sold events are the documented, accepted
# re-fire limitation for an internally contradictory sold export
# (persist_tekion_observations' docstring) -- asserted as-is.
# ---------------------------------------------------------------------------
EVENTS = {
    "QA-BASE-001":      {"keyper_observed": 1, "tekion_observed": 1,
                          "recovr_observed": 1, "rapidrecon_observed": 1},
    "QA-BASE-002":      {"keyper_observed": 1, "tekion_observed": 1,
                          "recovr_observed": 1, "rapidrecon_observed": 2},
    "QA-BASE-003":      {"keyper_observed": 1, "tekion_observed": 1},
    "QA-RECOVR-001":    {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1},
    "QA-RECOVR-002":    {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1},
    "QA-RECOVR-003":    {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1},
    "QA-RECOVR-004":    {"tekion_observed": 1, "recovr_observed": 1},
    "QA-RECOVR-005":    {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1},
    "QA-RECOVR-006":    {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 2},
    "QA-KEY-000":       {"keyper_observed": 2, "tekion_observed": 1},
    "QA-KEY-001":       {"keyper_observed": 1, "tekion_observed": 1},
    "QA-KEY-003":       {"keyper_observed": 1, "tekion_observed": 1},
    "QA-KEY-007":       {"keyper_observed": 1, "tekion_observed": 1},
    "QA-KEY-014":       {"keyper_observed": 1, "tekion_observed": 1},
    "QA-KEY-025":       {"keyper_observed": 1, "tekion_observed": 1},
    "QA-KEY-030":       {"keyper_observed": 1, "tekion_observed": 1},
    "QA-KEY-PAIRED":    {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1},
    "QA-WHOLESALE-001": {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1,
                          "mdd_observed": 1, "rapidrecon_observed": 1},
    "QA-WHOLESALE-002": {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1,
                          "rapidrecon_observed": 1},
    "QA-AUCTION-001":   {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1,
                          "rapidrecon_observed": 1},
    "QA-ARCHIVE-001":   {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1,
                          "rapidrecon_observed": 1},
    "QA-ARCHIVE-002":   {"tekion_sold": 1, "rapidrecon_observed": 1},
    "QA-SOLD-001":      {"keyper_observed": 1, "tekion_sold": 1, "recovr_observed": 1,
                          "mdd_observed": 1},
    "QA-SOLD-002":      {"keyper_observed": 1, "tekion_observed": 1, "recovr_observed": 1,
                          "tekion_sold": 1},
    "QA-CONFLICT-001":  {"tekion_observed": 1, "tekion_sold": 1},
    "QA-CONFLICT-002":  {"tekion_sold": 4},
    "QA-AMB-A":         {"tekion_observed": 1, "keyper_observed": 1,
                          "pending_identity_resolved": 1},
    "QA-AMB-B":         {"tekion_observed": 1, "tekion_sold": 1},
    "QA-INCOMING-001":  {"tekion_observed": 1},
    "QA-INCOMING-002":  {"tekion_observed": 1},
    "QA-FLEET-001":     {"tekion_observed": 1},
    "QA-MDD-001":       {"keyper_observed": 1, "tekion_observed": 1, "mdd_observed": 1},
    "QA-MULTI-001":     {"keyper_observed": 1, "tekion_observed": 1, "mdd_observed": 1,
                          "recovr_observed": 1},
    "QA-MDD-003":       {"keyper_observed": 1, "tekion_observed": 1, "mdd_observed": 1},
}

# Pending identities after Day 2: raw identifier -> (identifier_type
# recorded at capture, final status, scenario the resolution attached
# to or None). '888555' resolves on Day 2 when QA-AMB-B's sale makes
# the last-6 unambiguous; the other two have no resolution path.
PENDING_IDENTITIES = {
    "9755":    ("tekion_auto_generated_stock_number", "pending", None),
    "#QA-ODD": ("unrecognized", "pending", None),
    "888555":  ("ambiguous_last6_vin_multiple_matches", "resolved", "QA-AMB-A"),
}

# Scenarios carrying a RapidRecon row -> exactly these vehicles hold an
# event_freshness row for rapidrecon_observed, and Day 2's run must
# have refreshed every one of them (freshness updates even when the
# unchanged observation writes no new Event).
RAPIDRECON_FRESHNESS_SCENARIOS = {
    "QA-BASE-001", "QA-BASE-002", "QA-WHOLESALE-001", "QA-WHOLESALE-002",
    "QA-AUCTION-001", "QA-ARCHIVE-001", "QA-ARCHIVE-002",
}

TOTALS = {
    # Sprint 05 access-model identity rows (dev_seed/seeder.py's
    # seed_qa_access_identity) -- memberships are per-environment
    # (provisioning script), so none stand in the seed itself.
    "organizations": 1,
    "dealerships": 1,
    "user_memberships": 0,
    "vehicles": 34,
    "active_vehicles": 28,
    "sold_vehicles": 6,
    "tasks_total": 18,
    "tasks_outstanding": 16,
    "tasks_honored": 1,
    "tasks_moot": 1,
    "recommendations_open": 2,
    "pending_identities": 3,
    "sync_runs": 10,          # 5 sources x 2 days, all 'complete'
    "events": sum(sum(counts.values()) for counts in EVENTS.values()),  # 98
    # Distinct vehicles holding at least one outstanding task -- drives
    # queries/dashboard.py's inventory health figure (34 - 14 = 20).
    "vehicles_with_open_tasks": 14,
}


def vin_of(scenario_id: str) -> str:
    return VEHICLES[scenario_id][0]


def scenario_of(vin: str) -> str:
    for scenario_id, (candidate, _stock, _name) in VEHICLES.items():
        if candidate == vin:
            return scenario_id
    return f"<unknown vin {vin}>"
