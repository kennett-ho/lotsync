"""
Phase 2, Slice 3 verification -- see IMPLEMENTATION_PLAN.md.

Historical diffing (change-detection, not re-recording) plus
PendingIdentity -> Vehicle promotion, the system's first genuine state
transition. Uses the same synthetic fixtures as test_regression.py /
test_database_slice1.py / test_database_slice2.py.
"""

import os
import unittest

import pandas as pd

from lotsync.config.settings import load_settings, load_day_out_buckets
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.importers.mdd import load_mdd_not_paired
from lotsync.importers.recovr import load_recovr_full
from lotsync.importers.rapidrecon import load_rapidrecon
from lotsync.sync.reconciler import (
    reconcile_keyper_tekion, persist_tekion_observations,
    persist_mdd_observations, persist_recovr_observations,
    persist_rapidrecon_observations,
)
from lotsync.database.repository import connect

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")

# The two Tekion VINs whose last-6 both read "555555" -- the ambiguous
# match pair this fixture set uses to exercise
# ambiguous_last6_vin_multiple_matches (see tests/fixtures/README.md).
AMBIGUOUS_VIN_A = "1TESTVIN000555555"  # K60001
AMBIGUOUS_VIN_B = "1TESTVIN111555555"  # K60002


def _load_inputs():
    settings = load_settings(CONFIG)
    day_out_buckets = load_day_out_buckets(CONFIG)
    keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    mdd_df = load_mdd_not_paired(os.path.join(FIXTURES, "mdd_not_paired.csv"))
    recovr_df = load_recovr_full(os.path.join(FIXTURES, "recovr.csv"))
    rapidrecon_df = load_rapidrecon(os.path.join(FIXTURES, "rapidrecon.csv"))
    return keyper_df, tekion_df, sold_df, mdd_df, recovr_df, rapidrecon_df, settings["sync_date"], day_out_buckets


def _run_full_pipeline(conn, keyper_df, tekion_df, sold_df, mdd_df, recovr_df, rapidrecon_df,
                        sync_date, buckets, sync_run_id):
    # Mirrors main.py's real ordering -- Keyper first, then the other
    # four sources, all against the same connection.
    reconcile_keyper_tekion(
        keyper_df, tekion_df, sold_df, sync_date, buckets,
        db_conn=conn, sync_run_id=sync_run_id,
    )
    persist_tekion_observations(tekion_df, sold_df, db_conn=conn, sync_run_id=sync_run_id)
    persist_mdd_observations(mdd_df, db_conn=conn, sync_run_id=sync_run_id)
    persist_recovr_observations(recovr_df, db_conn=conn, sync_run_id=sync_run_id)
    persist_rapidrecon_observations(rapidrecon_df, db_conn=conn, sync_run_id=sync_run_id)


class IdempotencyTest(unittest.TestCase):
    """
    IMPLEMENTATION_PLAN.md Slice 3 Definition of Done: running the
    pipeline twice on identical input produces zero new Events on the
    second run -- across all five diffed sources (tekion/keyper/mdd/
    recovr/rapidrecon -- RapidRecon joined the other four in Sprint 3.7,
    see persist_rapidrecon_observations' docstring), for every VIN in
    the SUPPORTED operational model: at most one observation per
    event_type per VIN per sync.

    KNOWN, DOCUMENTED EXCEPTION, not a silent gap: 1TESTVIN000080001
    (K80001/K80002) has TWO "tekion_sold" rows for the same VIN in one
    sync -- an internally contradictory Tekion export (same VIN sold
    under two different stock numbers), not a normal operational state.
    Diffing against "the last matching Event" is exact for one-
    observation-per-run VINs but re-fires both Events on every rerun of
    this specific pathological case -- see persist_tekion_observations'
    docstring for why this was deliberately left unresolved rather than
    building sequence-aware diffing for an upstream data contradiction
    that tekion_sync_conflicts.csv already surfaces to a human daily,
    independent of anything here. This VIN is therefore excluded from
    the strict zero-new-events assertion below and covered by its own,
    explicit test instead, so the exception stays visible rather than
    silently weakening the general guarantee.
    """

    def setUp(self):
        (self.keyper_df, self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
         self.rapidrecon_df, self.sync_date, self.buckets) = _load_inputs()
        self.conn = connect(":memory:")

    def test_second_identical_run_produces_zero_new_events_for_diffed_sources(self):
        # Scoped to VINs within the supported one-observation-per-
        # event_type-per-run model -- excludes 1TESTVIN000080001,
        # covered separately below. RapidRecon is included in this
        # blanket assertion as of Sprint 3.7 (previously excluded here
        # because it wasn't diffed at all -- see
        # test_second_identical_run_does_not_duplicate_rapidrecon_event
        # below for the dedicated regression test and why this changed).
        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-1")
        (count_after_first,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin != '1TESTVIN000080001'"
        ).fetchone()

        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-2")
        (count_after_second,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin != '1TESTVIN000080001'"
        ).fetchone()

        self.assertGreater(count_after_first, 0, "sanity check -- first run must actually write Events")
        self.assertEqual(count_after_second, count_after_first,
                          "identical rerun must not write any new Events for the supported operational model")

    def test_second_identical_run_does_not_duplicate_rapidrecon_event(self):
        """
        Sprint 3.7 regression test -- this project's own real-world
        example of the bug this sprint fixed (see
        persist_rapidrecon_observations' docstring): before this
        sprint, RapidRecon was the one source with no diff-before-write
        at all, so an identical second sync produced a second, fully
        redundant "rapidrecon_observed" Event for every VIN, unbounded,
        forever -- literally the "RapidRecon WHOLESALE / RapidRecon
        WHOLESALE" duplicate-Timeline-card case this sprint's own
        review named as the motivating example.

        This test used to assert the OLD behavior directly
        (test_second_identical_run_still_writes_a_new_rapidrecon_event,
        removed) -- kept as its own dedicated test, not folded silently
        into the blanket assertion above, because this is the specific
        regression this sprint exists to prevent recurring.
        """
        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-1")
        (rapidrecon_events_run_1,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE source = 'rapidrecon' AND sync_run_id = 'run-1'"
        ).fetchone()
        self.assertGreater(rapidrecon_events_run_1, 0, "sanity check -- first run must write RapidRecon Events")

        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-2")
        (rapidrecon_events_run_2,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE source = 'rapidrecon' AND sync_run_id = 'run-2'"
        ).fetchone()
        self.assertEqual(rapidrecon_events_run_2, 0,
                          "an unchanged RapidRecon observation must not create a duplicate Timeline event")

        # Audit integrity (Sprint 3.7 objective 4): the suppressed
        # observation must still be recorded as freshness metadata, not
        # silently dropped -- "was this vehicle's RapidRecon claim
        # reconfirmed by the most recent sync" must stay answerable even
        # when no new Event was written.
        freshness = self.conn.execute(
            "SELECT last_sync_run_id FROM event_freshness "
            "WHERE event_type = 'rapidrecon_observed' AND source = 'rapidrecon' "
            "ORDER BY vin LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(freshness, "event_freshness must be populated even for a suppressed observation")
        self.assertEqual(freshness[0], "run-2",
                          "freshness must reflect the most recent sync that reconfirmed the claim, "
                          "even though it wrote no new Event")

    def test_documented_limitation_duplicate_sold_vin_refires_on_rerun(self):
        # Pins down the known, accepted exception explicitly (see this
        # class's docstring and persist_tekion_observations') rather
        # than leaving it as an unexplained gap in the strict test
        # above. If this ever starts asserting 0 instead of 2, that
        # means sequence-aware diffing was added -- update this test
        # (and the accompanying docstrings) deliberately at that point,
        # don't just let it silently start passing differently.
        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-1")
        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-2")
        (refired,) = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE vin = '1TESTVIN000080001' AND sync_run_id = 'run-2'"
        ).fetchone()
        self.assertEqual(refired, 2, "known, documented exception -- an internally contradictory "
                                      "upstream Tekion export refires both events on rerun; see "
                                      "persist_tekion_observations' docstring for why this is accepted")

    def test_second_identical_run_does_not_change_vehicle_current_state(self):
        # Diffing must not affect what's persisted as current state --
        # only whether an Event gets written alongside it.
        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-1")
        before = self.conn.execute(
            "SELECT vin, tekion_status, keyper_status, mdd_status, recovr_status, stock_number "
            "FROM vehicle ORDER BY vin"
        ).fetchall()

        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-2")
        after = self.conn.execute(
            "SELECT vin, tekion_status, keyper_status, mdd_status, recovr_status, stock_number "
            "FROM vehicle ORDER BY vin"
        ).fetchall()

        self.assertEqual(before, after)


class SingleFieldDiffTest(unittest.TestCase):
    """
    IMPLEMENTATION_PLAN.md Slice 3 Definition of Done: a fixture with
    exactly one changed field produces exactly one new Event.
    """

    def setUp(self):
        (self.keyper_df, self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
         self.rapidrecon_df, self.sync_date, self.buckets) = _load_inputs()
        self.conn = connect(":memory:")

    def test_recovr_status_flip_for_one_vehicle_produces_exactly_one_new_event(self):
        # 1TESTVIN000000002 (K30002) is Paired=No in recovr.csv today --
        # flip it to Yes on the "second sync" and confirm exactly one
        # new Event appears, only for this vin/source, and nowhere else.
        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-1")
        (count_before,) = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()

        flipped_recovr = self.recovr_df.copy(deep=True)
        target = flipped_recovr["VIN"].astype(str).str.strip() == "1TESTVIN000000002"
        self.assertEqual(target.sum(), 1, "fixture assumption changed -- expected exactly one matching row")
        flipped_recovr.loc[target, "Paired"] = "Yes"

        persist_recovr_observations(flipped_recovr, db_conn=self.conn, sync_run_id="run-2")
        (count_after,) = self.conn.execute("SELECT COUNT(*) FROM event").fetchone()

        self.assertEqual(count_after - count_before, 1)
        new_events = self.conn.execute(
            "SELECT vin, source, event_type FROM event WHERE sync_run_id = 'run-2'"
        ).fetchall()
        self.assertEqual(new_events, [("1TESTVIN000000002", "recovr", "recovr_observed")])

        (status,) = self.conn.execute(
            "SELECT recovr_status FROM vehicle WHERE vin = ?", ("1TESTVIN000000002",)
        ).fetchone()
        self.assertEqual(status, "paired")

    def test_unrelated_vehicles_are_untouched_by_the_flip(self):
        _run_full_pipeline(self.conn, self.keyper_df, self.tekion_df, self.sold_df,
                            self.mdd_df, self.recovr_df, self.rapidrecon_df,
                            self.sync_date, self.buckets, sync_run_id="run-1")

        flipped_recovr = self.recovr_df.copy(deep=True)
        target = flipped_recovr["VIN"].astype(str).str.strip() == "1TESTVIN000000002"
        flipped_recovr.loc[target, "Paired"] = "Yes"
        persist_recovr_observations(flipped_recovr, db_conn=self.conn, sync_run_id="run-2")

        other_vin_events = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE sync_run_id = 'run-2' AND vin != '1TESTVIN000000002'"
        ).fetchone()[0]
        self.assertEqual(other_vin_events, 0)


class PendingIdentityPromotionTest(unittest.TestCase):
    """
    IMPLEMENTATION_PLAN.md Slice 3: the first genuine state transition
    in the system. Keyper's raw identifier "555555" matches TWO Tekion
    VINs' last-6 in the base fixture (K60001/K60002, both ending in
    555555) -- ambiguous, captured as PendingIdentity, neither VIN
    touched. Dropping K60002 from a later sync's Tekion export makes
    "555555" resolve uniquely to K60001's VIN -- exactly the kind of
    later Tekion-side correction DATA_MODEL.md's PendingIdentity entry
    describes.
    """

    def setUp(self):
        (self.keyper_df, self.tekion_df, self.sold_df, self.mdd_df, self.recovr_df,
         self.rapidrecon_df, self.sync_date, self.buckets) = _load_inputs()
        self.conn = connect(":memory:")

    def test_ambiguous_identifier_stays_pending_and_unmatched_on_first_run(self):
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )
        (status,) = self.conn.execute(
            "SELECT status FROM pending_identity WHERE source = 'keyper' AND raw_identifier = '555555'"
        ).fetchone()
        self.assertEqual(status, "pending")
        for vin in (AMBIGUOUS_VIN_A, AMBIGUOUS_VIN_B):
            row = self.conn.execute("SELECT * FROM vehicle WHERE vin = ?", (vin,)).fetchone()
            self.assertIsNone(row, f"{vin} must stay untouched while the match is still ambiguous")

    def test_later_resolution_promotes_pending_identity_to_vehicle(self):
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )

        # "Next sync": K60002 no longer in Tekion's master export, so
        # 555555's last-6 now resolves uniquely to K60001.
        resolved_tekion_df = self.tekion_df[self.tekion_df["VIN #"] != AMBIGUOUS_VIN_B].reset_index(drop=True)
        reconcile_keyper_tekion(
            self.keyper_df, resolved_tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-2",
        )

        pending = self.conn.execute(
            "SELECT status, resolved_vin, resolved_at FROM pending_identity "
            "WHERE source = 'keyper' AND raw_identifier = '555555'"
        ).fetchone()
        self.assertEqual(pending[0], "resolved")
        self.assertEqual(pending[1], AMBIGUOUS_VIN_A)
        self.assertIsNotNone(pending[2])

        vehicle_row = self.conn.execute(
            "SELECT keyper_status FROM vehicle WHERE vin = ?", (AMBIGUOUS_VIN_A,)
        ).fetchone()
        self.assertIsNotNone(vehicle_row, "promotion must upsert a real Vehicle row")
        self.assertEqual(vehicle_row[0], "In")

        promotion_events = self.conn.execute(
            "SELECT vin, source, event_type FROM event "
            "WHERE event_type = 'pending_identity_resolved'"
        ).fetchall()
        self.assertEqual(promotion_events, [(AMBIGUOUS_VIN_A, "keyper", "pending_identity_resolved")])

    def test_promotion_does_not_repeat_on_a_third_run(self):
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )
        resolved_tekion_df = self.tekion_df[self.tekion_df["VIN #"] != AMBIGUOUS_VIN_B].reset_index(drop=True)
        reconcile_keyper_tekion(
            self.keyper_df, resolved_tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-2",
        )
        reconcile_keyper_tekion(
            self.keyper_df, resolved_tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-3",
        )

        promotion_events = self.conn.execute(
            "SELECT COUNT(*) FROM event WHERE event_type = 'pending_identity_resolved'"
        ).fetchone()[0]
        self.assertEqual(promotion_events, 1, "resolution is a one-time transition, not repeated every run")

    def test_still_ambiguous_pair_untouched_by_unrelated_promotion(self):
        # Sanity check that dropping K60002 doesn't itself count as a
        # "resolution" for some OTHER pending identifier -- only 555555
        # should ever move to resolved.
        reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )
        resolved_tekion_df = self.tekion_df[self.tekion_df["VIN #"] != AMBIGUOUS_VIN_B].reset_index(drop=True)
        reconcile_keyper_tekion(
            self.keyper_df, resolved_tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-2",
        )
        others = self.conn.execute(
            "SELECT raw_identifier, status FROM pending_identity WHERE raw_identifier != '555555'"
        ).fetchall()
        self.assertTrue(all(status == "pending" for _, status in others))


if __name__ == "__main__":
    unittest.main()
