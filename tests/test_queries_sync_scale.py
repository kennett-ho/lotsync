"""
Sprint 14 (Rail J) -- regression pins for the bounded sync_run reads.

connected_systems_status() and sync_run_history() previously read
EVERY sync_run row per call and reduced in Python -- linear unbounded
growth on hot paths (/dashboard and every /vehicles/{vin} pay the
first one; measured +6 ms per request by 5,000 rows locally, worse
over a network pooler). Both now aggregate in SQL.

These tests pin the BEHAVIORAL contract at a growth-shaped history
depth: latest-run-per-source with first-appearance key ordering, and
newest-N-batches with worst-status-wins -- exactly the semantics the
Python reductions had, so no consumer can tell the difference. No
timing assertions (CI machines vary); the bound is structural.
"""

import unittest

from lotsync.database.repository import connect

SOURCES = ["tekion", "keyper", "mdd", "recovr", "rapidrecon"]


def insert_run(conn, source, status, started_at, records):
    conn.execute(
        "INSERT INTO sync_run (source, status, started_at, completed_at, records_processed) "
        "VALUES (?, ?, ?, ?, ?)",
        (source, status, started_at, started_at, records),
    )


class SyncRunScaleTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        self.addCleanup(self.conn.close)

    def _seed_history(self, batches=400):
        """batches × 5 sources = 2,000 rows -- years of automated
        acquisition. Batch i stamps started_at 'T{i:04d}' so batch
        identity/order is unambiguous."""
        for i in range(batches):
            stamp = f"2026-01-01T{i:04d}"
            for source in SOURCES:
                insert_run(self.conn, source, "complete", stamp, 100 + i)
        self.conn.commit()

    def test_connected_systems_reports_each_sources_latest_run(self):
        from lotsync.queries.dashboard import connected_systems_status

        self._seed_history()
        # one late straggler: keyper's real latest run has a distinct count
        insert_run(self.conn, "keyper", "failed", "2026-01-02T0000", 7)
        self.conn.commit()

        status = connected_systems_status(self.conn)
        self.assertEqual(set(status), set(SOURCES))
        self.assertEqual(status["keyper"]["status"], "failed")
        self.assertEqual(status["keyper"]["records_processed"], 7)
        # every other source reports its final batch
        self.assertEqual(status["tekion"]["records_processed"], 100 + 399)

    def test_connected_systems_key_order_is_first_appearance(self):
        from lotsync.queries.dashboard import connected_systems_status

        # first-ever runs in a deliberate order; later batches shuffle
        for source in ["mdd", "tekion", "recovr"]:
            insert_run(self.conn, source, "complete", "2026-01-01T0000", 1)
        for source in ["recovr", "mdd", "tekion"]:
            insert_run(self.conn, source, "complete", "2026-01-01T0001", 2)
        self.conn.commit()

        # The pre-Sprint-14 Python reduction keyed the dict by each
        # source's FIRST appearance; consumers (header/system panels)
        # render in that order, so it is part of the contract.
        self.assertEqual(list(connected_systems_status(self.conn)),
                         ["mdd", "tekion", "recovr"])

    def test_history_returns_newest_limit_batches_with_grouping_intact(self):
        from lotsync.queries.inventory_sync import sync_run_history

        self._seed_history(batches=400)
        history = sync_run_history(self.conn, limit=20)

        self.assertEqual(len(history), 20)
        # newest batch first, each batch carrying all five sources
        self.assertEqual(history[0]["started_at"], "2026-01-01T0399")
        self.assertEqual(history[19]["started_at"], "2026-01-01T0380")
        self.assertEqual(len(history[0]["sources"]), 5)
        self.assertEqual({s["source"] for s in history[0]["sources"]}, set(SOURCES))

    def test_history_worst_status_wins_within_a_batch(self):
        from lotsync.queries.inventory_sync import sync_run_history

        self._seed_history(batches=3)
        insert_run(self.conn, "tekion", "complete", "2026-01-01T9999", 10)
        insert_run(self.conn, "keyper", "failed", "2026-01-01T9999", 0)
        self.conn.commit()

        history = sync_run_history(self.conn, limit=5)
        self.assertEqual(history[0]["started_at"], "2026-01-01T9999")
        self.assertEqual(history[0]["overall_status"], "failed")
        self.assertEqual(history[1]["overall_status"], "complete")


if __name__ == "__main__":
    unittest.main()
