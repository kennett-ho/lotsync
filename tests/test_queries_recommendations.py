"""
Phase 3, Sprint 2 verification -- queries/recommendations.py.
"""

import unittest

from lotsync.database.repository import (
    connect, upsert_vehicle, insert_recommendation, dismiss_recommendation,
)
from lotsync.queries.recommendations import list_recommendations


class ListRecommendationsTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "VIN1", stock_number="A48291", year=2023, make="Honda", model="Accord")
        upsert_vehicle(self.conn, "VIN2", stock_number="B93021", year=2022, make="Ford", model="F-150")
        self.conn.commit()

    def test_empty_dataset_returns_empty_list(self):
        self.assertEqual(list_recommendations(self.conn), [])

    def test_returns_a_recommendation_with_embedded_vehicle_summary(self):
        insert_recommendation(self.conn, "VIN1", "High", "RecovR missing", "42 days untracked", "recovr_missing")
        self.conn.commit()

        recs = list_recommendations(self.conn)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["vin"], "VIN1")
        self.assertEqual(rec["status"], "open")
        self.assertEqual(rec["vehicle"], {
            "vin": "VIN1", "stock_number": "A48291", "year": 2023, "make": "Honda", "model": "Accord",
        })
        self.assertNotIn("stock_number", rec)

    def test_ordered_newest_first(self):
        first_id = insert_recommendation(self.conn, "VIN1", "High", "t1", "d1", "rule_a")
        second_id = insert_recommendation(self.conn, "VIN2", "Medium", "t2", "d2", "rule_b")
        self.conn.commit()
        recs = list_recommendations(self.conn)
        self.assertEqual([r["recommendation_id"] for r in recs], [second_id, first_id])

    def test_vin_filter_scopes_to_one_vehicle(self):
        insert_recommendation(self.conn, "VIN1", "High", "t1", "d1", "rule_a")
        insert_recommendation(self.conn, "VIN2", "High", "t2", "d2", "rule_a")
        self.conn.commit()

        recs = list_recommendations(self.conn, vin="VIN1")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["vin"], "VIN1")

    def test_status_filter_excludes_dismissed(self):
        rec_id = insert_recommendation(self.conn, "VIN1", "High", "t1", "d1", "rule_a")
        self.conn.commit()
        dismiss_recommendation(self.conn, rec_id)
        self.conn.commit()

        open_recs = list_recommendations(self.conn, status="open")
        dismissed_recs = list_recommendations(self.conn, status="dismissed")
        self.assertEqual(open_recs, [])
        self.assertEqual(len(dismissed_recs), 1)


if __name__ == "__main__":
    unittest.main()
