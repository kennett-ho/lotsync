"""
Sprint 3.7 (v0.7.3, "Event Fidelity") verification.

Covers this sprint's three real, code-level changes: source-provided
event_time (Keyper Out / Tekion observed+sold), the Wholesale/AT
AUCTION RecovR-install exclusion restored into the live pipeline
(build_tracker_install_tasks), and Keyper departure (silence) leaving a
vehicle's last-known state untouched. RapidRecon's duplicate-observation
fix has its own dedicated regression test in test_database_slice3.py
(it directly replaced an existing test asserting the old, buggy
behavior, so it stayed there rather than splitting the before/after
story across two files).

Uses the same synthetic fixtures as test_regression.py where a fixture
row already fits; hand-built minimal DataFrames where a specific
scenario (a RapidRecon Step value paired with a specific VIN) isn't
covered by the shared fixture set -- deliberately not added to the
shared fixtures, to avoid rippling into every other test that already
asserts exact counts against them.
"""

import os
import unittest

import pandas as pd

from lotsync.config.settings import load_settings, load_day_out_buckets
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.database.repository import connect, get_event_freshness
from lotsync.sync.reconciler import (
    reconcile_keyper_tekion, persist_tekion_observations,
    build_tracker_install_tasks, generate_install_tasks,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")


def _load_keyper_tekion_sold():
    settings = load_settings(CONFIG)
    day_out_buckets = load_day_out_buckets(CONFIG)
    keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    return keyper_df, tekion_df, sold_df, settings["sync_date"], day_out_buckets


class KeyperEventTimeTest(unittest.TestCase):
    """
    Keyper's "Checkout Date" is only a confirmed timestamp for Status=Out
    (the existing days-out calculation already trusts it for exactly
    that). Status=In deliberately does NOT get an inferred event_time --
    see _persist_keyper_observation's docstring for why guessing what
    "Checkout Date" means on an In row was rejected during this sprint's
    review.
    """

    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = \
            _load_keyper_tekion_sold()
        self.conn = connect(":memory:")

    def test_out_status_event_time_matches_checkout_date(self):
        # K30002 -- Out, matches Tekion stock K30002 / 1TESTVIN000000002,
        # Checkout Date "7/20/2026 10:00" (see keyper.csv).
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )
        row = self.conn.execute(
            "SELECT event_time, observed_at FROM event "
            "WHERE vin = '1TESTVIN000000002' AND event_type = 'keyper_observed'"
        ).fetchone()
        self.assertIsNotNone(row, "expected a keyper_observed Event for this VIN")
        event_time, observed_at = row
        self.assertEqual(event_time, "2026-07-20T10:00:00")
        self.assertIsNotNone(observed_at, "observed_at (audit trail) must still always be populated")

    def test_in_status_event_time_is_null(self):
        # K30001 -- In, matches Tekion stock K30001 / 1TESTVIN000000001.
        # Checkout Date is still populated in the export ("7/20/2026
        # 10:00"), but nothing confirms what it means on an In row, so
        # event_time must stay null rather than guess.
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )
        row = self.conn.execute(
            "SELECT event_time, observed_at FROM event "
            "WHERE vin = '1TESTVIN000000001' AND event_type = 'keyper_observed'"
        ).fetchone()
        self.assertIsNotNone(row, "expected a keyper_observed Event for this VIN")
        event_time, observed_at = row
        self.assertIsNone(event_time, "In status must not infer a return timestamp from Checkout Date")
        self.assertIsNotNone(observed_at, "observed_at (audit trail) must still always be populated")


class TekionEventTimeTest(unittest.TestCase):
    """
    Unlike Keyper's Checkout Date, Tekion's Stocked In Date and Sold
    Date are each unambiguously tied to exactly one claim -- see
    persist_tekion_observations' docstring.
    """

    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = \
            _load_keyper_tekion_sold()
        self.conn = connect(":memory:")

    def test_stocked_in_event_time_matches_stocked_in_date(self):
        # 1TESTVIN000000001 -- Stocked In Date "Jul 18 2026" (tekion_master.csv).
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn, sync_run_id="run-1")
        row = self.conn.execute(
            "SELECT event_time, observed_at FROM event "
            "WHERE vin = '1TESTVIN000000001' AND event_type = 'tekion_observed'"
        ).fetchone()
        self.assertIsNotNone(row)
        event_time, observed_at = row
        self.assertEqual(event_time, "2026-07-18T00:00:00")
        self.assertIsNotNone(observed_at)

    def test_sold_event_time_matches_sold_date(self):
        # 1TESTVIN000030005 -- Sold Date "Jul 10 2026" (tekion_sold.csv).
        persist_tekion_observations(self.tekion_df, self.sold_df, db_conn=self.conn, sync_run_id="run-1")
        row = self.conn.execute(
            "SELECT event_time, observed_at FROM event "
            "WHERE vin = '1TESTVIN000030005' AND event_type = 'tekion_sold'"
        ).fetchone()
        self.assertIsNotNone(row)
        event_time, observed_at = row
        self.assertEqual(event_time, "2026-07-10T00:00:00")
        self.assertIsNotNone(observed_at)


def _tekion_df(vin, stock="K90001"):
    return pd.DataFrame([{
        "Stock #": stock, "VIN #": vin, "Status": "Stocked In",
        "Year Make Model": "2024 Test Sedan", "Stocked In Date": "Jul 18 2026",
        "is_internal_fleet": False,
    }])


_EMPTY_SOLD = pd.DataFrame(columns=["Stock #", "VIN #", "Status", "Sold Date", "Year Make Model"])
_EMPTY_MDD = pd.DataFrame(columns=["vin", "stock", "year", "make", "model", "Dealership", "Geofence"])


def _recovr_not_paired_df(vin, stock="K90001"):
    return pd.DataFrame([{
        "VIN": vin, "Stock Number": stock, "Paired": "No",
        "Year": "2024", "Make": "Test", "Model": "Sedan",
    }])


def _rapidrecon_df(vin, step):
    return pd.DataFrame([{"VIN": vin, "Step": step}])


class WholesaleExclusionTest(unittest.TestCase):
    """
    Sprint 3.7 -- restores a real gap between this project's stated
    intent and the live pipeline's actual behavior (see
    build_tracker_install_tasks' docstring for the full comparison
    against build_recovr_install_from_keyper, the dead-code function
    this exclusion criterion was verified against and reused from).
    """

    VIN = "1TESTVIN000090001"

    def test_wholesale_step_excludes_recovr_install_task(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(self.VIN), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(self.VIN),
            "TestStore", rapidrecon_df=_rapidrecon_df(self.VIN, "WHOLESALE"),
        )
        self.assertTrue(tasks.empty, "a Wholesale-bound vehicle must not get a RecovR install task")

    def test_at_auction_step_excludes_recovr_install_task(self):
        tasks = build_tracker_install_tasks(
            _tekion_df(self.VIN), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(self.VIN),
            "TestStore", rapidrecon_df=_rapidrecon_df(self.VIN, "AT AUCTION"),
        )
        self.assertTrue(tasks.empty, "an At-Auction-bound vehicle must not get a RecovR install task")

    def test_non_wholesale_step_still_generates_recovr_task(self):
        # Regression guard against over-exclusion: only WHOLESALE/AT
        # AUCTION are excluded -- every other Step value (77 distinct
        # values in real data, per ARCHITECTURE.md) must not be treated
        # as an exclusion signal.
        tasks = build_tracker_install_tasks(
            _tekion_df(self.VIN), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(self.VIN),
            "TestStore", rapidrecon_df=_rapidrecon_df(self.VIN, "Inspection"),
        )
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks.iloc[0]["vin"], self.VIN)

    def test_missing_rapidrecon_data_still_generates_recovr_task(self):
        # Regression guard: a vehicle RapidRecon has never mentioned at
        # all must not be treated as excluded -- absence of a Step is
        # not evidence of Wholesale status (DECISION_FRAMEWORK.md:
        # silence isn't a claim).
        tasks = build_tracker_install_tasks(
            _tekion_df(self.VIN), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(self.VIN),
            "TestStore", rapidrecon_df=pd.DataFrame(columns=["VIN", "Step"]),
        )
        self.assertEqual(len(tasks), 1)

    def test_rapidrecon_df_omitted_entirely_still_generates_recovr_task(self):
        # rapidrecon_df defaults to None -- every pre-Sprint-3.7 caller
        # (and any test with no reason to care about RapidRecon) must
        # keep working exactly as before, with no exclusion applied.
        tasks = build_tracker_install_tasks(
            _tekion_df(self.VIN), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(self.VIN),
            "TestStore",
        )
        self.assertEqual(len(tasks), 1)

    def test_wholesale_exclusion_applies_through_task_generation_too(self):
        # generate_install_tasks (the actual live Task-generation path,
        # not just the CSV-facing function) must honor the same
        # exclusion -- confirms rapidrecon_df is correctly threaded
        # through, not just accepted by build_tracker_install_tasks in
        # isolation.
        conn = connect(":memory:")
        persist_tekion_observations(_tekion_df(self.VIN), _EMPTY_SOLD, db_conn=conn, sync_run_id="run-1")
        generate_install_tasks(
            _tekion_df(self.VIN), _EMPTY_SOLD, _EMPTY_MDD, _recovr_not_paired_df(self.VIN),
            "TestStore", db_conn=conn, rapidrecon_df=_rapidrecon_df(self.VIN, "WHOLESALE"),
        )
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM task WHERE vin = ? AND task_type = 'install_recovr_device'",
            (self.VIN,),
        ).fetchone()
        self.assertEqual(count, 0)

    def test_wholesale_vehicle_may_still_have_an_active_keyper_record(self):
        """
        The other half of this project's stated Wholesale rule: a
        vehicle correctly excluded from RecovR-install candidates
        because RapidRecon reports it Wholesale-bound must still be
        able to carry a real, active Keyper record (it's still
        physically on the lot) without the pipeline treating that as a
        contradiction or exception -- nothing in reconcile_keyper_tekion
        or persist_rapidrecon_observations is aware of the other's
        output, by design (see ARCHITECTURE.md's "RapidRecon:
        contextual enrichment only" section), so this just confirms
        that isolation holds in practice, not only in theory.
        """
        conn = connect(":memory:")
        full_keyper_df, _, sold_df, sync_date, buckets = _load_keyper_tekion_sold()
        # Isolated to just the one relevant row -- the full fixture's
        # other rows include identifiers ("784", "#ODD1") that are
        # unconditionally data_quality_exceptions regardless of Tekion
        # content, which would make this test's exception-count
        # assertion meaningless.
        keyper_df = full_keyper_df[full_keyper_df["identifier_raw"] == "K30002"].reset_index(drop=True)
        # K30002 / 1TESTVIN000000002 -- a real, matched, "Out" Keyper record.
        tekion_df = _tekion_df("1TESTVIN000000002", stock="K30002")

        fully_verified, key_out_aging, flag_to_controller, exceptions, _ = reconcile_keyper_tekion(
            keyper_df, tekion_df, sold_df, sync_date, buckets, db_conn=conn, sync_run_id="run-1",
        )
        self.assertEqual(len(exceptions), 0, "a matched Keyper record must not become a data-quality exception")

        vehicle = conn.execute(
            "SELECT keyper_status FROM vehicle WHERE vin = '1TESTVIN000000002'"
        ).fetchone()
        self.assertIsNotNone(vehicle, "the Keyper-matched vehicle must exist")
        self.assertEqual(vehicle[0], "Out", "an active Keyper record must persist regardless of Wholesale status")


class KeyperDepartureTest(unittest.TestCase):
    """
    "Only after the vehicle physically leaves should the Keyper record
    disappear" -- this project has no active removal/deletion logic for
    this (nothing calls it), and this test confirms that's correct, not
    a gap: a VIN silently missing from a later Keyper export is treated
    as silence, not a claim (DECISION_FRAMEWORK.md) -- its last-known
    keyper_status is left untouched, and no spurious "removed" Event is
    invented. This mirrors test_sync_pipeline.py's existing
    test_a_vehicle_not_reasserted_keeps_its_last_known_state, which
    covers the same principle for Tekion -- this is Keyper's own
    dedicated version, since the sprint brief named it specifically.
    """

    def test_keyper_going_silent_preserves_last_known_status(self):
        conn = connect(":memory:")
        keyper_df, tekion_df, sold_df, sync_date, buckets = _load_keyper_tekion_sold()

        reconcile_keyper_tekion(
            keyper_df, tekion_df, sold_df, sync_date, buckets, db_conn=conn, sync_run_id="run-1",
        )
        before = conn.execute(
            "SELECT keyper_status FROM vehicle WHERE vin = '1TESTVIN000000002'"
        ).fetchone()
        self.assertEqual(before[0], "Out")
        (events_before,) = conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin = '1TESTVIN000000002'"
        ).fetchone()

        # Second sync: Keyper's own export no longer mentions K30002 at
        # all (the physical key -- and the export row -- is gone, e.g.
        # the vehicle left for auction and the key was removed from
        # Keyper's system). No Keyper row => no Keyper claim this run.
        keyper_df_without_k30002 = keyper_df[keyper_df["identifier_raw"] != "K30002"].reset_index(drop=True)
        reconcile_keyper_tekion(
            keyper_df_without_k30002, tekion_df, sold_df, sync_date, buckets,
            db_conn=conn, sync_run_id="run-2",
        )

        after = conn.execute(
            "SELECT keyper_status FROM vehicle WHERE vin = '1TESTVIN000000002'"
        ).fetchone()
        self.assertEqual(after[0], "Out", "silence must not reset or null the last-known Keyper status")

        (events_after,) = conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin = '1TESTVIN000000002'"
        ).fetchone()
        self.assertEqual(events_after, events_before,
                          "no new Event may be invented for a vehicle Keyper simply stopped mentioning")
