"""
Unit tests for sync/state_engine.py -- the generic day-count-to-label
evaluator. Boundary values get the most attention here since the
original requested scale had overlapping endpoints (see
rules/aging.py) and an off-by-one in bucket boundaries is exactly the
kind of bug that's easy to introduce silently.
"""

import unittest

from lotsync.sync.state_engine import day_out_bucket

BUCKETS = [
    (0, "Should be here"),
    (1, "Might be here"),
    (3, "Investigate"),
    (7, "High Priority Investigate"),
    (14, "Possibly Sold, Verify"),
    (25, "Likely Sold, Verify to Remove from OMS"),
]


class TestDayOutBucket(unittest.TestCase):
    def test_exact_lower_boundaries(self):
        self.assertEqual(day_out_bucket(0, BUCKETS), "Should be here")
        self.assertEqual(day_out_bucket(1, BUCKETS), "Might be here")
        self.assertEqual(day_out_bucket(3, BUCKETS), "Investigate")
        self.assertEqual(day_out_bucket(7, BUCKETS), "High Priority Investigate")
        self.assertEqual(day_out_bucket(14, BUCKETS), "Possibly Sold, Verify")
        self.assertEqual(day_out_bucket(25, BUCKETS), "Likely Sold, Verify to Remove from OMS")

    def test_day_just_before_next_boundary_stays_in_current_tier(self):
        self.assertEqual(day_out_bucket(2, BUCKETS), "Might be here")
        self.assertEqual(day_out_bucket(6, BUCKETS), "Investigate")
        self.assertEqual(day_out_bucket(13, BUCKETS), "High Priority Investigate")
        self.assertEqual(day_out_bucket(24, BUCKETS), "Possibly Sold, Verify")

    def test_far_past_last_boundary_stays_in_last_tier(self):
        self.assertEqual(day_out_bucket(1000, BUCKETS), "Likely Sold, Verify to Remove from OMS")

    def test_single_bucket_scale(self):
        single = [(0, "Only Label")]
        self.assertEqual(day_out_bucket(0, single), "Only Label")
        self.assertEqual(day_out_bucket(999, single), "Only Label")


if __name__ == "__main__":
    unittest.main()
