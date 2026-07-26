"""
Phase 2, Sprint 4, Slice 6 verification -- Recommendation repository
primitives (Milestone 1) and rule-evaluation wiring into
sync/reconciler.py (Milestone 2). See DATA_MODEL.md's Recommendation
entry, DECISION_FRAMEWORK.md's "Ontology, Architecture, Invariants, and
Reasoning Tools" section, and IMPLEMENTATION_PLAN.md's Slice 6.
"""

import os
import unittest

import pandas as pd

from lotsync.config.settings import load_settings, load_day_out_buckets
from lotsync.importers.keyper import load_keyper
from lotsync.importers.tekion import load_tekion
from lotsync.importers.sold import load_tekion_sold
from lotsync.database.repository import (
    connect, insert_recommendation, get_open_recommendation, get_latest_recommendation,
    get_recommendation, dismiss_recommendation, convert_recommendation_to_task,
    get_task, upsert_vehicle,
)
from lotsync.sync.reconciler import reconcile_keyper_tekion, generate_key_out_aging_recommendations

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "synthetic")
CONFIG = os.path.join(FIXTURES, "test_config.xlsx")

# 1TESTVIN000000003 (K30003) is the fixture's one VIN in the most severe
# key-out-aging bucket ("Likely Sold, Verify to Remove from OMS", 30
# days out) -- read directly off the fixture, not recomputed from the
# function under test.
MOST_SEVERE_VIN = "1TESTVIN000000003"


class RecommendationCreationTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()

    def test_new_recommendation_starts_open(self):
        rec_id = insert_recommendation(self.conn, "VIN1", "High", "Key out too long",
                                       "Checked out 25+ days", "key_out_aging")
        rec = get_recommendation(self.conn, rec_id)
        self.assertEqual(rec["status"], "open")
        self.assertIsNotNone(rec["created_at"])
        self.assertIsNone(rec["resolved_at"])
        self.assertIsNone(rec["resulting_task_id"])

    def test_get_open_recommendation_finds_it(self):
        insert_recommendation(self.conn, "VIN1", "High", "t", "d", "key_out_aging")
        rec = get_open_recommendation(self.conn, "VIN1", "key_out_aging")
        self.assertIsNotNone(rec)

    def test_get_open_recommendation_scoped_by_rule_source(self):
        insert_recommendation(self.conn, "VIN1", "High", "t", "d", "key_out_aging")
        self.assertIsNone(get_open_recommendation(self.conn, "VIN1", "some_other_rule"))

    def test_get_latest_recommendation_returns_most_recent_regardless_of_status(self):
        first_id = insert_recommendation(self.conn, "VIN1", "High", "t1", "d1", "key_out_aging")
        dismiss_recommendation(self.conn, first_id)
        second_id = insert_recommendation(self.conn, "VIN1", "High", "t2", "d2", "key_out_aging")

        latest = get_latest_recommendation(self.conn, "VIN1", "key_out_aging")
        self.assertEqual(latest["recommendation_id"], second_id)
        self.assertEqual(latest["status"], "open")


class DismissalTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        self.rec_id = insert_recommendation(self.conn, "VIN1", "High", "t", "d", "key_out_aging")

    def test_dismiss_sets_status_and_resolved_at(self):
        dismiss_recommendation(self.conn, self.rec_id)
        rec = get_recommendation(self.conn, self.rec_id)
        self.assertEqual(rec["status"], "dismissed")
        self.assertIsNotNone(rec["resolved_at"])

    def test_dismissed_recommendation_no_longer_open(self):
        dismiss_recommendation(self.conn, self.rec_id)
        self.assertIsNone(get_open_recommendation(self.conn, "VIN1", "key_out_aging"))

    def test_dismissing_twice_is_a_no_op(self):
        dismiss_recommendation(self.conn, self.rec_id)
        first_resolved_at = get_recommendation(self.conn, self.rec_id)["resolved_at"]
        dismiss_recommendation(self.conn, self.rec_id)
        second = get_recommendation(self.conn, self.rec_id)
        self.assertEqual(second["status"], "dismissed")
        self.assertEqual(second["resolved_at"], first_resolved_at)


class ConversionTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1")
        self.conn.commit()
        self.rec_id = insert_recommendation(self.conn, "VIN1", "High", "Key out too long",
                                            "Checked out 25+ days, likely sold", "key_out_aging")

    def test_convert_creates_a_ratified_task(self):
        task_id = convert_recommendation_to_task(self.conn, self.rec_id, "investigate_key_out",
                                                 ratified_by="emp123")
        task = get_task(self.conn, task_id)
        self.assertEqual(task["vin"], "VIN1")
        self.assertEqual(task["task_type"], "investigate_key_out")
        self.assertEqual(task["ratified_by"], "emp123")
        self.assertEqual(task["ratification_type"], "human")
        self.assertEqual(task["commitment_standing"], "outstanding")

    def test_convert_defaults_reason_to_recommendation_detail(self):
        task_id = convert_recommendation_to_task(self.conn, self.rec_id, "investigate_key_out",
                                                 ratified_by="emp123")
        task = get_task(self.conn, task_id)
        self.assertEqual(task["reason"], "Checked out 25+ days, likely sold")

    def test_convert_updates_recommendation_status_and_link(self):
        task_id = convert_recommendation_to_task(self.conn, self.rec_id, "investigate_key_out",
                                                 ratified_by="emp123")
        rec = get_recommendation(self.conn, self.rec_id)
        self.assertEqual(rec["status"], "converted_to_task")
        self.assertEqual(rec["resulting_task_id"], task_id)
        self.assertIsNotNone(rec["resolved_at"])

    def test_convert_allows_standing_policy_ratification(self):
        task_id = convert_recommendation_to_task(
            self.conn, self.rec_id, "investigate_key_out",
            ratified_by="standing_policy:auto_investigate_high_severity",
            ratification_type="standing_policy",
        )
        task = get_task(self.conn, task_id)
        self.assertEqual(task["ratification_type"], "standing_policy")

    def test_convert_unknown_recommendation_raises(self):
        with self.assertRaises(ValueError):
            convert_recommendation_to_task(self.conn, 999999, "investigate_key_out", ratified_by="emp1")

    def test_convert_already_dismissed_recommendation_raises(self):
        dismiss_recommendation(self.conn, self.rec_id)
        with self.assertRaises(ValueError):
            convert_recommendation_to_task(self.conn, self.rec_id, "investigate_key_out", ratified_by="emp1")

    def test_convert_already_converted_recommendation_raises(self):
        convert_recommendation_to_task(self.conn, self.rec_id, "investigate_key_out", ratified_by="emp1")
        with self.assertRaises(ValueError):
            convert_recommendation_to_task(self.conn, self.rec_id, "investigate_key_out", ratified_by="emp2")


def _load_key_out_aging_inputs():
    settings = load_settings(CONFIG)
    day_out_buckets = load_day_out_buckets(CONFIG)
    keyper_df = load_keyper(os.path.join(FIXTURES, "keyper.csv"))
    tekion_df = load_tekion(set(), os.path.join(FIXTURES, "tekion_master.csv"))
    sold_df = load_tekion_sold(os.path.join(FIXTURES, "tekion_sold.csv"))
    return keyper_df, tekion_df, sold_df, settings["sync_date"], day_out_buckets


class KeyOutAgingRecommendationGenerationTest(unittest.TestCase):
    """Milestone 2: generate_key_out_aging_recommendations, the most-severe-bucket trigger."""

    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = \
            _load_key_out_aging_inputs()
        self.conn = connect(":memory:")
        _, self.key_out_aging, _, _, _ = reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )

    def test_creates_recommendation_for_most_severe_bucket_vin(self):
        generate_key_out_aging_recommendations(self.key_out_aging, self.buckets, db_conn=self.conn)
        rec = get_open_recommendation(self.conn, MOST_SEVERE_VIN, "key_out_aging")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["severity"], "High")

    def test_no_recommendation_for_less_severe_bucket_vin(self):
        generate_key_out_aging_recommendations(self.key_out_aging, self.buckets, db_conn=self.conn)
        self.assertIsNone(get_open_recommendation(self.conn, "1TESTVIN000000002", "key_out_aging"))

    def test_rerun_does_not_create_duplicate_open_recommendation(self):
        generate_key_out_aging_recommendations(self.key_out_aging, self.buckets, db_conn=self.conn)
        generate_key_out_aging_recommendations(self.key_out_aging, self.buckets, db_conn=self.conn)
        (count,) = self.conn.execute(
            "SELECT COUNT(*) FROM recommendation WHERE vin = ? AND rule_source = 'key_out_aging'",
            (MOST_SEVERE_VIN,),
        ).fetchone()
        self.assertEqual(count, 1)

    def test_no_op_when_db_conn_omitted(self):
        generate_key_out_aging_recommendations(self.key_out_aging, self.buckets, db_conn=None)


class DismissedRecommendationReopeningTest(unittest.TestCase):
    """
    Milestone 2: IMPLEMENTATION_PLAN.md Slice 6's named risk -- "what
    counts as the underlying vehicle state genuinely changing." Resolved
    by reusing Slice 3's Event history: a dismissed Recommendation stays
    dismissed unless a NEW keyper_observed(status='Out') Event has been
    recorded since the dismissal.
    """

    def setUp(self):
        self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets = \
            _load_key_out_aging_inputs()
        self.conn = connect(":memory:")
        _, key_out_aging, _, _, _ = reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-1",
        )
        generate_key_out_aging_recommendations(key_out_aging, self.buckets, db_conn=self.conn)
        rec = get_open_recommendation(self.conn, MOST_SEVERE_VIN, "key_out_aging")
        dismiss_recommendation(self.conn, rec["recommendation_id"])

    def test_dismissed_recommendation_does_not_reappear_on_unchanged_rerun(self):
        # Same input, no new information -- days_out climbing further
        # on the SAME still-open checkout is not a new claim (Slice 3
        # never even writes a new keyper_observed Event for it, since
        # keyper_status hasn't changed).
        _, key_out_aging, _, _, _ = reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-2",
        )
        generate_key_out_aging_recommendations(key_out_aging, self.buckets, db_conn=self.conn)

        self.assertIsNone(get_open_recommendation(self.conn, MOST_SEVERE_VIN, "key_out_aging"))
        latest = get_latest_recommendation(self.conn, MOST_SEVERE_VIN, "key_out_aging")
        self.assertEqual(latest["status"], "dismissed")

    def test_dismissed_recommendation_reappears_after_a_genuine_new_out_transition(self):
        # Simulate the key coming back "In" (a new, diffed observation),
        # then going back "Out" again under a fresh checkout -- a
        # genuinely new occurrence, not the same checkout's days_out
        # continuing to climb.
        target_mask = self.keyper_df["identifier_raw"] == "K30003"

        back_in = self.keyper_df.copy(deep=True)
        back_in.loc[target_mask, "Status"] = "In"
        reconcile_keyper_tekion(
            back_in, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-2",
        )

        # New checkout, still comfortably past the most-severe threshold
        # (25+ days) relative to this fixture's sync_date -- both the
        # display string and the pre-parsed checkout_dt need updating,
        # since load_keyper() parses "Checkout Date" into checkout_dt
        # once at load time; only the display string would do nothing.
        checked_out_again = self.keyper_df.copy(deep=True)
        new_checkout_str = "6/10/2026 09:00"
        checked_out_again.loc[target_mask, "Checkout Date"] = new_checkout_str
        checked_out_again.loc[target_mask, "checkout_dt"] = pd.to_datetime(
            new_checkout_str, format="%m/%d/%Y %H:%M"
        )
        _, key_out_aging_3, _, _, _ = reconcile_keyper_tekion(
            checked_out_again, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-3",
        )
        self.assertIn(MOST_SEVERE_VIN, key_out_aging_3["tekion_vin"].values,
                      "test setup check -- the new checkout must still land in the most severe bucket")

        generate_key_out_aging_recommendations(key_out_aging_3, self.buckets, db_conn=self.conn)

        rec = get_open_recommendation(self.conn, MOST_SEVERE_VIN, "key_out_aging")
        self.assertIsNotNone(rec, "a genuinely new Out-transition after dismissal must reopen the recommendation")

    def test_unrelated_vin_recommendation_history_is_untouched(self):
        # Sanity check -- rerunning must not disturb an unrelated VIN's
        # (non-existent, in this fixture) recommendation state.
        _, key_out_aging, _, _, _ = reconcile_keyper_tekion(
            self.keyper_df, self.tekion_df, self.sold_df, self.sync_date, self.buckets,
            db_conn=self.conn, sync_run_id="run-2",
        )
        generate_key_out_aging_recommendations(key_out_aging, self.buckets, db_conn=self.conn)
        self.assertIsNone(get_open_recommendation(self.conn, "1TESTVIN000000002", "key_out_aging"))


if __name__ == "__main__":
    unittest.main()
