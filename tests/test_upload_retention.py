"""
D4 bounded-retention boundary tests (DATA_RETENTION.md section 3,
owner-ratified 2026-08-21) -- api/upload_retention.py and its wiring
in api/routers/inventory_sync.py.

Pins the ratified windows (accepted 7d, rejected/unacknowledged 30d,
validate-orphans 24h), the outcome.json marker on every terminal
/run outcome (and its deliberate ABSENCE on the 500 path), the
never-delete-inside-window rule, conservative handling of unmarked/
malformed markers and unrecognized entries, the kill-switch, the
in-flight-batch safety property, and the one-structured-record-per-
sweep telemetry contract.

Ages are driven through directory NAMES (the sweep's age basis) and
validate-* mtimes -- no clock mocking anywhere.
"""

import datetime
import json
import logging
import os
import tempfile
import time
import unittest
from unittest import mock

from lotsync.api import upload_retention
from lotsync.api.routers import inventory_sync

from tests.test_api_inventory_sync import (
    ApiTestCase, KEYPER_PATH, MDD_HEADERS_ONLY, TEKION_HEADERS_ONLY, TEKION_PATH,
)


def make_batch(root, age: datetime.timedelta, outcome=None, marker_bytes=None):
    """A batch directory aged via its NAME (the sweep's age basis),
    holding one server-named slot file, optionally marked."""
    ts = (datetime.datetime.now() - age).strftime(upload_retention._BATCH_NAME_FORMAT)
    path = os.path.join(root, ts)
    os.makedirs(path)
    with open(os.path.join(path, "tekion.csv"), "w", encoding="utf-8") as f:
        f.write("VIN\n")
    if outcome is not None:
        upload_retention.record_outcome(path, outcome)
    if marker_bytes is not None:
        with open(os.path.join(path, upload_retention.OUTCOME_MARKER), "w",
                  encoding="utf-8") as f:
            f.write(marker_bytes)
    return path


class SweepUnitTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name

    def test_accepted_batches_age_out_after_seven_days(self):
        expired = make_batch(self.root, datetime.timedelta(days=8),
                             upload_retention.OUTCOME_ACCEPTED)
        fresh = make_batch(self.root, datetime.timedelta(days=6),
                           upload_retention.OUTCOME_ACCEPTED)
        upload_retention.sweep(self.root)
        self.assertFalse(os.path.exists(expired))
        self.assertTrue(os.path.exists(fresh))

    def test_rejected_and_unacknowledged_batches_keep_thirty_days(self):
        kept_rejected = make_batch(self.root, datetime.timedelta(days=29),
                                   upload_retention.OUTCOME_REJECTED)
        gone_rejected = make_batch(self.root, datetime.timedelta(days=31),
                                   upload_retention.OUTCOME_REJECTED)
        kept_unacked = make_batch(self.root, datetime.timedelta(days=28),
                                  upload_retention.OUTCOME_WARNINGS_UNACKNOWLEDGED)
        gone_unacked = make_batch(self.root, datetime.timedelta(days=32),
                                  upload_retention.OUTCOME_WARNINGS_UNACKNOWLEDGED)
        upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(kept_rejected))
        self.assertFalse(os.path.exists(gone_rejected))
        self.assertTrue(os.path.exists(kept_unacked))
        self.assertFalse(os.path.exists(gone_unacked))

    def test_unmarked_batches_age_under_the_conservative_window(self):
        # Pre-feature legacy and crash-before-marker directories: the
        # LONGER window, never the accepted one.
        kept = make_batch(self.root, datetime.timedelta(days=8))
        gone = make_batch(self.root, datetime.timedelta(days=31))
        upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(kept))
        self.assertFalse(os.path.exists(gone))

    def test_malformed_or_unknown_markers_are_conservative(self):
        kept_garbage = make_batch(self.root, datetime.timedelta(days=8),
                                  marker_bytes="not json at all")
        gone_garbage = make_batch(self.root, datetime.timedelta(days=31),
                                  marker_bytes="not json at all")
        kept_unknown = make_batch(self.root, datetime.timedelta(days=8),
                                  marker_bytes=json.dumps({"outcome": "hold"}))
        upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(kept_garbage))
        self.assertFalse(os.path.exists(gone_garbage))
        self.assertTrue(os.path.exists(kept_unknown))

    def test_unrecognized_entries_are_never_deleted(self):
        # Deletion only under positively recognized names -- an alien
        # directory or stray file survives at ANY age.
        alien = os.path.join(self.root, "legacy-stuff")
        os.makedirs(alien)
        stray = os.path.join(self.root, "notes.txt")
        with open(stray, "w", encoding="utf-8") as f:
            f.write("operator scratch file")
        ancient = time.time() - 400 * 24 * 3600
        os.utime(alien, (ancient, ancient))
        os.utime(stray, (ancient, ancient))
        upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(alien))
        self.assertTrue(os.path.exists(stray))

    def test_validate_orphans_age_out_after_24_hours(self):
        fresh = os.path.join(self.root, "validate-fresh123")
        os.makedirs(fresh)
        orphan = os.path.join(self.root, "validate-orphan99")
        os.makedirs(orphan)
        old = time.time() - 25 * 3600
        os.utime(orphan, (old, old))
        upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(fresh))
        self.assertFalse(os.path.exists(orphan))

    def test_kill_switch_and_unrecognized_values_disable_the_sweep(self):
        # Deletion is irreversible; a skipped sweep is always
        # recoverable -- so anything but unset/"enabled" fails toward
        # keeping data.
        expired = make_batch(self.root, datetime.timedelta(days=40),
                             upload_retention.OUTCOME_REJECTED)
        with mock.patch.dict(os.environ, {"UPLOAD_RETENTION_SWEEP": "disabled"}):
            self.assertFalse(upload_retention.sweep_enabled())
            upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(expired))
        with mock.patch.dict(os.environ, {"UPLOAD_RETENTION_SWEEP": "oops-typo"}):
            self.assertFalse(upload_retention.sweep_enabled())
            upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(expired))
        with mock.patch.dict(os.environ, {"UPLOAD_RETENTION_SWEEP": "enabled"}):
            self.assertTrue(upload_retention.sweep_enabled())
        env_without = {k: v for k, v in os.environ.items()
                       if k != "UPLOAD_RETENTION_SWEEP"}
        with mock.patch.dict(os.environ, env_without, clear=True):
            self.assertTrue(upload_retention.sweep_enabled())

    def test_missing_uploads_root_is_a_noop(self):
        upload_retention.sweep(os.path.join(self.root, "never-created"))

    def test_sweep_emits_one_structured_record_with_counts_only(self):
        expired = make_batch(self.root, datetime.timedelta(days=8),
                             upload_retention.OUTCOME_ACCEPTED)
        make_batch(self.root, datetime.timedelta(days=1),
                   upload_retention.OUTCOME_ACCEPTED)
        orphan = os.path.join(self.root, "validate-orphan99")
        os.makedirs(orphan)
        old = time.time() - 25 * 3600
        os.utime(orphan, (old, old))
        with open(os.path.join(self.root, "stray.txt"), "w", encoding="utf-8") as f:
            f.write("x")
        with mock.patch.object(upload_retention.observability, "log_event") as le:
            upload_retention.sweep(self.root)
        le.assert_called_once()
        level, event = le.call_args.args
        fields = le.call_args.kwargs
        self.assertEqual(level, logging.INFO)
        self.assertEqual(event, "upload_retention_sweep")
        self.assertEqual(fields["scanned"], 3)
        self.assertEqual(fields["kept"], 1)
        self.assertEqual(fields["deleted_batches"], [os.path.basename(expired)])
        self.assertEqual(fields["deleted_validate_orphans"], 1)
        self.assertEqual(fields["delete_errors"], 0)

    def test_a_failed_deletion_does_not_stop_the_sweep(self):
        blocked = make_batch(self.root, datetime.timedelta(days=31),
                             upload_retention.OUTCOME_REJECTED)
        deletable = make_batch(self.root, datetime.timedelta(days=32),
                               upload_retention.OUTCOME_REJECTED)
        real_rmtree = upload_retention.shutil.rmtree

        def flaky_rmtree(path, **kwargs):
            if path == blocked:
                raise OSError("simulated in-use directory")
            return real_rmtree(path, **kwargs)

        with mock.patch.object(upload_retention.shutil, "rmtree",
                               side_effect=flaky_rmtree):
            with mock.patch.object(upload_retention.observability, "log_event") as le:
                upload_retention.sweep(self.root)
        self.assertTrue(os.path.exists(blocked))
        self.assertFalse(os.path.exists(deletable))
        self.assertEqual(le.call_args.kwargs["delete_errors"], 1)

    def test_record_outcome_writes_the_marker_and_never_raises(self):
        batch = make_batch(self.root, datetime.timedelta(days=0))
        upload_retention.record_outcome(batch, upload_retention.OUTCOME_ACCEPTED)
        with open(os.path.join(batch, upload_retention.OUTCOME_MARKER),
                  encoding="utf-8") as f:
            marker = json.load(f)
        self.assertEqual(marker["outcome"], "accepted")
        self.assertIn("recorded_at", marker)
        # A marker that cannot be written leaves the batch unmarked
        # (conservative window) -- it must never raise into /run.
        upload_retention.record_outcome(
            os.path.join(self.root, "does-not-exist"),
            upload_retention.OUTCOME_ACCEPTED)


class RetentionEndpointTest(ApiTestCase):
    """The HTTP surface writes the right marker for every terminal
    /run outcome, and both endpoints actually sweep."""

    def _batch_dirs(self):
        root = inventory_sync.UPLOADS_DIR
        if not os.path.isdir(root):
            return []
        return sorted(d for d in os.listdir(root) if not d.startswith("validate-"))

    def _newest_batch(self):
        dirs = self._batch_dirs()
        self.assertTrue(dirs, "expected /run to have created a batch directory")
        return os.path.join(inventory_sync.UPLOADS_DIR, dirs[-1])

    def _marker(self, batch_path):
        with open(os.path.join(batch_path, upload_retention.OUTCOME_MARKER),
                  encoding="utf-8") as f:
            return json.load(f)["outcome"]

    def test_successful_run_marks_accepted(self):
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=TEKION_PATH, keyper=KEYPER_PATH),
        )
        self.assertEqual(resp.status_code, 200)
        batch = self._newest_batch()
        self.assertEqual(self._marker(batch), "accepted")
        self.assertTrue(os.path.exists(os.path.join(batch, "tekion.csv")))

    def test_validation_failure_marks_rejected_and_keeps_the_evidence(self):
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=TEKION_HEADERS_ONLY),
        )
        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["detail"]["code"], "REPORT_VALIDATION_FAILED")
        batch = self._newest_batch()
        self.assertEqual(self._marker(batch), "rejected")
        self.assertTrue(os.path.exists(os.path.join(batch, "tekion.csv")))

    def test_unacknowledged_warning_marks_unacknowledged(self):
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(mdd=MDD_HEADERS_ONLY),
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "WARNINGS_NOT_ACKNOWLEDGED")
        self.assertEqual(self._marker(self._newest_batch()), "warnings_unacknowledged")

    def test_stale_fingerprint_marks_unacknowledged(self):
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(mdd=MDD_HEADERS_ONLY),
            data={"acknowledge_warnings": "true",
                  "validation_fingerprint": "deadbeef"},
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"]["code"], "STALE_VALIDATION")
        self.assertEqual(self._marker(self._newest_batch()), "warnings_unacknowledged")

    def test_sync_failure_leaves_the_batch_unmarked(self):
        # The 500 path writes NO marker on purpose: the batch ages
        # under the conservative 30-day window rather than a window
        # presuming an outcome it never reached.
        with mock.patch.object(inventory_sync, "run_inventory_sync",
                               side_effect=RuntimeError("boom")):
            resp = self.client.post(
                "/inventory-sync/run",
                files=self._files(tekion_unsold=TEKION_PATH),
            )
        self.assertEqual(resp.status_code, 500)
        batch = self._newest_batch()
        self.assertFalse(
            os.path.exists(os.path.join(batch, upload_retention.OUTCOME_MARKER)))

    def test_run_sweeps_expired_batches(self):
        expired = make_batch(inventory_sync.UPLOADS_DIR, datetime.timedelta(days=8),
                             upload_retention.OUTCOME_ACCEPTED)
        fresh = make_batch(inventory_sync.UPLOADS_DIR, datetime.timedelta(days=6),
                           upload_retention.OUTCOME_ACCEPTED)
        resp = self.client.post(
            "/inventory-sync/run",
            files=self._files(tekion_unsold=TEKION_PATH),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(os.path.exists(expired))
        self.assertTrue(os.path.exists(fresh))

    def test_validate_sweeps_while_staying_zero_mutation(self):
        expired = make_batch(inventory_sync.UPLOADS_DIR, datetime.timedelta(days=31),
                             upload_retention.OUTCOME_REJECTED)
        fresh = make_batch(inventory_sync.UPLOADS_DIR, datetime.timedelta(days=29),
                           upload_retention.OUTCOME_REJECTED)
        before = self._mutation_counts()
        resp = self.client.post(
            "/inventory-sync/validate",
            files=self._files(tekion_unsold=TEKION_PATH),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(os.path.exists(expired))
        self.assertTrue(os.path.exists(fresh))
        self.assert_zero_mutation(before)
        # /validate's own upload stays deleted-pre-response, sweep or not.
        self.assertEqual(
            [d for d in os.listdir(inventory_sync.UPLOADS_DIR)
             if d.startswith("validate-")], [])

    def test_inflight_batches_survive_the_next_sweep(self):
        # Back-to-back runs: the second request's sweep sees the first
        # batch (marked accepted, seconds old) and must keep it.
        for _ in range(2):
            resp = self.client.post(
                "/inventory-sync/run",
                files=self._files(tekion_unsold=TEKION_PATH),
            )
            self.assertEqual(resp.status_code, 200)
        dirs = self._batch_dirs()
        self.assertEqual(len(dirs), 2)
        for d in dirs:
            self.assertEqual(
                self._marker(os.path.join(inventory_sync.UPLOADS_DIR, d)),
                "accepted")

    def test_kill_switch_holds_at_the_endpoint(self):
        expired = make_batch(inventory_sync.UPLOADS_DIR, datetime.timedelta(days=40),
                             upload_retention.OUTCOME_REJECTED)
        with mock.patch.dict(os.environ, {"UPLOAD_RETENTION_SWEEP": "disabled"}):
            resp = self.client.post(
                "/inventory-sync/run",
                files=self._files(tekion_unsold=TEKION_PATH),
            )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(os.path.exists(expired))


if __name__ == "__main__":
    unittest.main()
