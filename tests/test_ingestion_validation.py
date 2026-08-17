"""
Sprint 10 (Rail D) -- unit tests for the ingestion boundary
(sync/report_contracts.py, sync/report_classifier.py,
sync/ingestion.py), one class per concern. Endpoint-level behavior
(revalidation at /run, acknowledgement/fingerprint gating, authz,
zero-mutation through HTTP) lives in tests/test_api_inventory_sync.py;
this module proves the boundary itself, directly.

Fixtures: tests/fixtures/synthetic/ (well-formed, the same files the
rest of the suite trusts) and tests/fixtures/ingestion/ (adversarial
-- see its README for the fixture-to-validation-class map). Byte-level
cases with no meaningful text representation are generated here at
runtime in temp dirs.
"""

import csv
import os
import tempfile
import time
import unittest
from unittest import mock

from lotsync.database.repository import connect, insert_report_baseline
from lotsync.sync import ingestion
from lotsync.sync.ingestion import validate_report_set
from lotsync.sync.report_classifier import classify_headers
from lotsync.sync.report_contracts import (
    BY_CONTRACT_ID, CONTRACTS, KEYPER_KEY_EVENT, SLOT_CONTRACTS, SLOT_LABELS,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
SYNTHETIC = os.path.join(FIXTURES, "synthetic")
ADVERSARIAL = os.path.join(FIXTURES, "ingestion")


def synthetic(name: str) -> str:
    return os.path.join(SYNTHETIC, name)


def adversarial(name: str) -> str:
    return os.path.join(ADVERSARIAL, name)


def validate_one(slot: str, path: str, conn=None):
    """One file through the full boundary; returns its ReportValidation."""
    return validate_report_set({slot: path}, db_conn=conn).reports[0]


def codes(report) -> list:
    return [i.code for i in report.issues]


def headers_of(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def write_tekion_csv(path: str, n_rows: int, start: int = 1):
    """A well-formed Tekion current-inventory file with n unique VINs
    (1TESTVIN + 9 digits = 17 chars, same shape as the fixtures)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Stock #", "VIN #", "Status", "Year Make Model", "Stocked In Date"])
        for i in range(start, start + n_rows):
            w.writerow([f"K{i:05d}", f"1TESTVIN{i:09d}", "Stocked In",
                        "2024 Test Sedan", "Jul 18 2026"])


class RegistryTest(unittest.TestCase):
    """The contract registry's own governed facts."""

    def test_slots_match_the_router_exactly(self):
        self.assertEqual(set(SLOT_CONTRACTS), {"tekion", "sold", "keyper", "mdd",
                                                "recovr", "rapidrecon"})
        self.assertEqual(set(SLOT_LABELS), set(SLOT_CONTRACTS))

    def test_zero_row_policies_are_the_recorded_sprint_10_decisions(self):
        expected = {
            "tekion": "error", "sold": "error", "keyper": "error",
            "recovr": "error", "mdd": "warning", "rapidrecon": "warning",
        }
        for slot, policy in expected.items():
            self.assertEqual(SLOT_CONTRACTS[slot].zero_row_policy, policy, slot)
            self.assertTrue(SLOT_CONTRACTS[slot].zero_row_message, slot)

    def test_keyper_event_is_recognized_but_carries_no_invented_schema(self):
        # The Sprint 10 brief's hard rule: no real sample exists, so
        # the entry may have NO column facts and NO ingestion path.
        self.assertFalse(KEYPER_KEY_EVENT.supported)
        self.assertEqual(KEYPER_KEY_EVENT.ingestion_mode, "incremental_event")
        self.assertEqual(KEYPER_KEY_EVENT.required_columns, ())
        self.assertEqual(KEYPER_KEY_EVENT.signature_columns, ())
        self.assertEqual(KEYPER_KEY_EVENT.slot, "")

    def test_signatures_are_unique_across_supported_contracts(self):
        # No supported contract's full signature may be a subset of
        # another's headers-universe such that one real fixture
        # matches two contracts -- the classifier test below proves it
        # against real files; this pins the registry-level intent.
        sigs = [set(c.signature_columns) for c in CONTRACTS if c.supported]
        for i, a in enumerate(sigs):
            for b in sigs[i + 1:]:
                self.assertFalse(a <= b or b <= a,
                                 f"signature subset collision: {a} vs {b}")


class ClassifierTest(unittest.TestCase):
    """Content-based identification of every real report shape."""

    MATRIX = [
        ("tekion_master.csv", "tekion_current_inventory"),
        ("tekion_sold.csv", "tekion_sold_inventory"),
        ("keyper.csv", "keyper_full_inventory"),
        ("mdd_not_paired.csv", "mdd_not_paired"),
        ("recovr.csv", "recovr_device_state"),
        ("rapidrecon.csv", "rapidrecon_recon_status"),
    ]

    def test_every_real_fixture_classifies_exactly(self):
        for fixture, contract_id in self.MATRIX:
            cls = classify_headers(headers_of(synthetic(fixture)))
            self.assertEqual(cls.confidence, "exact", fixture)
            self.assertEqual(cls.contract_id, contract_id, fixture)

    def test_classification_is_deterministic(self):
        headers = headers_of(synthetic("tekion_master.csv"))
        results = {classify_headers(headers).contract_id for _ in range(5)}
        self.assertEqual(results, {"tekion_current_inventory"})

    def test_case_is_distinguishing_evidence(self):
        # MDD's lowercase "vin"/"stock" vs RecovR's uppercase -- a
        # lowercased RecovR header must NOT classify as RecovR.
        lowered = [h.lower() for h in headers_of(synthetic("recovr.csv"))]
        cls = classify_headers(lowered)
        self.assertNotEqual(cls.contract_id, "recovr_device_state")

    def test_no_evidence_is_none(self):
        self.assertEqual(classify_headers(["Animal", "Sound"]).confidence, "none")


class WrongSlotTest(unittest.TestCase):
    """Phase 6: a recognized report in the wrong slot is rejected
    BEFORE synchronization, with the detection named."""

    def assert_wrong_type(self, slot: str, path: str, detected_id: str):
        report = validate_one(slot, path)
        self.assertEqual(report.status, "rejected")
        self.assertIn("WRONG_REPORT_TYPE", codes(report))
        self.assertEqual(report.detected_contract_id, detected_id)

    def test_tekion_sold_in_current_slot(self):
        self.assert_wrong_type("tekion", synthetic("tekion_sold.csv"),
                               "tekion_sold_inventory")

    def test_tekion_current_in_sold_slot(self):
        self.assert_wrong_type("sold", synthetic("tekion_master.csv"),
                               "tekion_current_inventory")

    def test_keyper_in_tekion_slot(self):
        self.assert_wrong_type("tekion", synthetic("keyper.csv"),
                               "keyper_full_inventory")

    def test_recovr_in_rapidrecon_slot(self):
        # THE pre-Sprint-10 hole: the RapidRecon slot required only a
        # VIN column, so a RecovR export sailed through and wrote junk
        # observations. Now its content identifies it and the slot
        # rejects it.
        self.assert_wrong_type("rapidrecon", synthetic("recovr.csv"),
                               "recovr_device_state")

    def test_ambiguous_tekion_is_rejected_not_guessed(self):
        report = validate_one("tekion", adversarial("ambiguous_tekion.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("AMBIGUOUS_REPORT_TYPE", codes(report))

    def test_unrecognized_report_is_rejected(self):
        report = validate_one("mdd", adversarial("unrecognized_report.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("UNRECOGNIZED_REPORT", codes(report))


class KeyperEventBoundaryTest(unittest.TestCase):
    """Phase 22: the Full-vs-Event safety case. Event ingestion is
    format-blocked (no real sample), so the provable half is the
    boundary: Keyper-like evidence that is NOT the Full Inventory
    contract is rejected explicitly and can never satisfy the keyper
    slot's snapshot requirement."""

    def test_keyper_variant_is_rejected_with_the_event_language(self):
        report = validate_one("keyper", adversarial("keyper_variant_stand_in.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("REPORT_VARIANT_UNSUPPORTED", codes(report))
        message = report.issues[0].message
        self.assertIn("not the Full Key Inventory report", message)
        self.assertIn("not yet supported", message)
        self.assertIn("never substitute", message)

    def test_keyper_variant_is_rejected_in_every_slot(self):
        # Not just the keyper slot -- there is NO slot this file can
        # enter the engine through.
        for slot in SLOT_CONTRACTS:
            report = validate_one(slot, adversarial("keyper_variant_stand_in.csv"))
            self.assertEqual(report.status, "rejected", slot)

    def test_full_inventory_still_satisfies_the_keyper_slot(self):
        report = validate_one("keyper", synthetic("keyper.csv"))
        self.assertEqual(report.status, "ready")
        self.assertEqual(report.detected_contract_id, "keyper_full_inventory")


class FileSafetyTest(unittest.TestCase):
    """Phase 12: user-controlled bytes fail fast and readably."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _path(self, name: str, data: bytes) -> str:
        p = os.path.join(self._tmp.name, name)
        with open(p, "wb") as f:
            f.write(data)
        return p

    def test_empty_file(self):
        report = validate_one("tekion", adversarial("empty.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("EMPTY_FILE", codes(report))

    def test_excel_workbook_magic_bytes(self):
        for magic in (b"PK\x03\x04junkjunk", b"\xd0\xcf\x11\xe0junkjunk"):
            report = validate_one("tekion", self._path("wb.bin", magic))
            self.assertIn("UNSUPPORTED_FORMAT", codes(report))
            self.assertIn("Excel", report.issues[0].message)

    def test_undecodable_binary(self):
        report = validate_one("tekion", self._path("junk.bin", b"\xff\xfe\x00\x01\x02"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("UNREADABLE_FILE", codes(report))

    def test_bom_prefixed_header_is_rejected_with_the_remedy(self):
        data = "﻿Stock #,VIN #,Status,Year Make Model,Stocked In Date\n".encode("utf-8")
        report = validate_one("tekion", self._path("bom.csv", data))
        self.assertEqual(report.status, "rejected")
        self.assertIn("UNREADABLE_FILE", codes(report))
        self.assertIn("byte-order mark", report.issues[0].message)

    def test_duplicate_header(self):
        report = validate_one("tekion", adversarial("tekion_duplicate_header.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("DUPLICATE_HEADER", codes(report))
        self.assertIn("Status", report.issues[0].message)

    def test_oversized_file(self):
        with mock.patch.object(ingestion, "MAX_UPLOAD_BYTES", 64):
            report = validate_one("tekion", synthetic("tekion_master.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("FILE_TOO_LARGE", codes(report))

    def test_row_bomb(self):
        with mock.patch.object(ingestion, "MAX_DATA_ROWS", 1):
            report = validate_one("tekion", synthetic("tekion_master.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("TOO_MANY_ROWS", codes(report))

    def test_no_raw_parser_text_reaches_messages(self):
        # Representative sweep: every rejection message on these
        # inputs is dealership language, never a Python/pandas
        # traceback fragment or a filesystem path.
        cases = [
            ("tekion", adversarial("empty.csv")),
            ("tekion", self._path("junk.bin", b"\xff\xfe\x00\x01")),
            ("tekion", adversarial("tekion_duplicate_header.csv")),
            ("mdd", adversarial("unrecognized_report.csv")),
        ]
        for slot, path in cases:
            for issue in validate_one(slot, path).issues:
                for fragment in ("Traceback", "pandas", "Error:", self._tmp.name,
                                 "\\", ".py"):
                    self.assertNotIn(fragment, issue.message, (slot, path))


class ZeroRowTest(unittest.TestCase):
    """Phases 8-9: empty evidence per contract policy -- authoritative
    snapshots hard-reject; exception/contextual lists warn and demand
    acknowledgement. 'Invalid evidence != valid zero.'"""

    def test_tekion_headers_only_is_rejected(self):
        report = validate_one("tekion", adversarial("tekion_headers_only.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("NO_DATA_ROWS", codes(report))
        self.assertIn("selected", report.issues[0].message)  # names the export mistake

    def test_mdd_headers_only_needs_review_not_rejection(self):
        report = validate_one("mdd", adversarial("mdd_headers_only.csv"))
        self.assertEqual(report.status, "needs_review")
        self.assertIn("NO_DATA_ROWS", codes(report))

    def test_all_authoritative_zero_rows_reject(self):
        # Generate a headers-only file for each error-policy contract.
        with tempfile.TemporaryDirectory() as tmp:
            for slot in ("tekion", "sold", "keyper", "recovr"):
                contract = SLOT_CONTRACTS[slot]
                path = os.path.join(tmp, f"{slot}.csv")
                with open(path, "w", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow(list(contract.required_columns))
                report = validate_one(slot, path)
                self.assertEqual(report.status, "rejected", slot)
                self.assertIn("NO_DATA_ROWS", codes(report), slot)


class RowLevelTest(unittest.TestCase):
    """Phase 10 + the recorded Rail D exit-5 decision: blank VINs in
    identity-originating reports reject the file; inert bad VINs
    elsewhere warn."""

    def test_blank_vin_in_tekion_rejects_the_file(self):
        report = validate_one("tekion", adversarial("tekion_blank_vin.csv"))
        self.assertEqual(report.status, "rejected")
        self.assertIn("MISSING_VINS", codes(report))
        self.assertIn("file line 2", report.issues[0].message)

    def test_malformed_vin_in_tekion_warns_with_counts(self):
        report = validate_one("tekion", adversarial("tekion_malformed_vin.csv"))
        self.assertEqual(report.status, "needs_review")
        self.assertIn("MALFORMED_VINS", codes(report))
        self.assertEqual(report.total_rows, 3)
        self.assertEqual(report.invalid_rows, 1)
        self.assertEqual(report.valid_rows, 2)

    def test_blank_vin_in_recovr_warns_only(self):
        # RecovR never originates Vehicle identity; its bad rows are
        # inert downstream and must not block the file.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "recovr.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["VIN", "Stock Number", "Paired", "Year", "Make", "Model"])
                w.writerow(["", "K30002", "No", "2024", "Test", "Sedan"])
                w.writerow(["1TESTVIN000000002", "K30003", "No", "2024", "Test", "Sedan"])
            report = validate_one("recovr", path)
        self.assertEqual(report.status, "needs_review")
        self.assertIn("MALFORMED_VINS", codes(report))
        self.assertNotIn("MISSING_VINS", codes(report))


class DuplicateTest(unittest.TestCase):
    """Phase 11: contract semantics decide what a duplicate is."""

    def test_duplicate_vins_in_current_snapshot_warn(self):
        report = validate_one("tekion", adversarial("tekion_duplicate_vins.csv"))
        self.assertEqual(report.status, "needs_review")
        self.assertIn("DUPLICATE_VINS", codes(report))
        self.assertEqual(report.duplicate_identifiers, 1)

    def test_sold_report_vin_repeats_are_legitimate_history(self):
        report = validate_one("sold", adversarial("sold_exact_duplicate_rows.csv"))
        # The exact duplicate row is flagged; the same-VIN
        # different-stock pair is NOT (rules/validation.py's conflict
        # machinery owns that question downstream).
        self.assertIn("DUPLICATE_ROWS", codes(report))
        self.assertNotIn("DUPLICATE_VINS", codes(report))
        self.assertEqual(report.duplicate_rows, 1)

    def test_clean_files_report_no_duplicates(self):
        report = validate_one("tekion", synthetic("tekion_master.csv"))
        self.assertEqual(report.duplicate_rows, 0)
        self.assertEqual(report.duplicate_identifiers, 0)


class BaselineTest(unittest.TestCase):
    """Phases 13-14: comparable-baseline scoping and the PROPOSED
    (pending owner ratification) suspicious-count thresholds."""

    def setUp(self):
        self.conn = connect(":memory:")
        self.addCleanup(self.conn.close)
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _baseline(self, valid_rows: int, vendor="tekion", report_type="current_inventory"):
        insert_report_baseline(self.conn, vendor=vendor, report_type=report_type,
                                slot="tekion", total_rows=valid_rows,
                                valid_rows=valid_rows,
                                sync_started_at="2026-08-15T08:00:00")
        self.conn.commit()

    def _validate_n_rows(self, n: int):
        path = os.path.join(self._tmp.name, f"tekion_{n}.csv")
        write_tekion_csv(path, n)
        return validate_one("tekion", path, conn=self.conn)

    def test_no_prior_baseline_is_info_not_a_blocker(self):
        report = self._validate_n_rows(30)
        self.assertEqual(report.status, "ready")
        self.assertIn("NO_PRIOR_BASELINE", codes(report))
        self.assertIsNone(report.baseline["previous_rows"])

    def test_ordinary_fluctuation_does_not_warn(self):
        self._baseline(100)
        report = self._validate_n_rows(95)   # -5%
        self.assertEqual(report.status, "ready")
        self.assertEqual(report.baseline["previous_rows"], 100)
        self.assertEqual(report.baseline["change"], -5)

    def test_catastrophic_drop_warns(self):
        self._baseline(100)
        report = self._validate_n_rows(14)   # the register's own example shape
        self.assertEqual(report.status, "needs_review")
        self.assertIn("SUSPICIOUS_COUNT_DROP", codes(report))

    def test_drop_threshold_boundaries(self):
        self._baseline(100)
        # Exactly -15% is NOT suspicious (strict >), one row further is.
        self.assertNotIn("SUSPICIOUS_COUNT_DROP", codes(self._validate_n_rows(85)))
        self.assertIn("SUSPICIOUS_COUNT_DROP", codes(self._validate_n_rows(84)))

    def test_small_absolute_drops_never_warn(self):
        self._baseline(40)
        report = self._validate_n_rows(31)   # -22.5% but only 9 rows
        self.assertNotIn("SUSPICIOUS_COUNT_DROP", codes(report))

    def test_suspicious_increase_warns(self):
        # The real observed failure shape: a multi-store umbrella
        # export roughly doubling the store-specific count.
        self._baseline(100)
        self.assertIn("SUSPICIOUS_COUNT_INCREASE", codes(self._validate_n_rows(160)))
        self.assertNotIn("SUSPICIOUS_COUNT_INCREASE", codes(self._validate_n_rows(140)))

    def test_baselines_are_scoped_per_report_type(self):
        # A Tekion SOLD baseline must never judge a Tekion CURRENT
        # file (phase 13's hard scoping rule).
        self._baseline(1000, report_type="sold_inventory")
        report = self._validate_n_rows(30)
        self.assertIn("NO_PRIOR_BASELINE", codes(report))
        self.assertEqual(report.status, "ready")

    def test_newest_baseline_wins(self):
        self._baseline(500)
        self._baseline(30)
        report = self._validate_n_rows(29)
        self.assertEqual(report.baseline["previous_rows"], 30)
        self.assertEqual(report.status, "ready")


class FingerprintTest(unittest.TestCase):
    """Phase 16/18's binding: acknowledgement can only refer to exact
    bytes."""

    def test_same_bytes_same_fingerprint(self):
        a = validate_report_set({"tekion": synthetic("tekion_master.csv")})
        b = validate_report_set({"tekion": synthetic("tekion_master.csv")})
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertTrue(a.reports[0].fingerprint)

    def test_different_bytes_different_fingerprint(self):
        a = validate_report_set({"tekion": synthetic("tekion_master.csv")})
        b = validate_report_set({"tekion": adversarial("tekion_duplicate_vins.csv")})
        self.assertNotEqual(a.fingerprint, b.fingerprint)

    def test_set_fingerprint_covers_every_slot(self):
        a = validate_report_set({"tekion": synthetic("tekion_master.csv"),
                                 "keyper": synthetic("keyper.csv")})
        b = validate_report_set({"tekion": synthetic("tekion_master.csv"),
                                 "keyper": adversarial("keyper_variant_stand_in.csv")})
        self.assertNotEqual(a.fingerprint, b.fingerprint)


class NoMutationTest(unittest.TestCase):
    """The validation boundary NEVER writes -- phase 17's contract,
    proven at the function level (the endpoint-level proof is in
    test_api_inventory_sync.py)."""

    TABLES = ("vehicle", "event", "sync_run", "task", "recommendation",
              "pending_identity", "report_baseline")

    def test_validation_writes_nothing(self):
        conn = connect(":memory:")
        self.addCleanup(conn.close)
        insert_report_baseline(conn, vendor="tekion", report_type="current_inventory",
                                slot="tekion", total_rows=5, valid_rows=5,
                                sync_started_at="2026-08-15T08:00:00")
        conn.commit()
        before = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in self.TABLES}
        validate_report_set(
            {"tekion": synthetic("tekion_master.csv"),
             "sold": synthetic("tekion_sold.csv"),
             "keyper": adversarial("keyper_variant_stand_in.csv"),
             "mdd": adversarial("mdd_headers_only.csv")},
            db_conn=conn,
        )
        after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                 for t in self.TABLES}
        self.assertEqual(before, after)


class PerformanceSanityTest(unittest.TestCase):
    """Phase 29: production-shaped scale (the 2026-08-15 production
    backup holds 4,672 vehicles). The bound is deliberately loose --
    this is a regression tripwire, not a benchmark; the measured
    number is printed for the sprint report."""

    def test_production_scale_validation_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tekion_prod_scale.csv")
            write_tekion_csv(path, 4700)
            conn = connect(":memory:")
            try:
                started = time.perf_counter()
                result = validate_report_set({"tekion": path}, db_conn=conn)
                elapsed = time.perf_counter() - started
            finally:
                conn.close()
        report = result.reports[0]
        self.assertEqual(report.status, "ready")
        self.assertEqual(report.total_rows, 4700)
        self.assertEqual(report.valid_rows, 4700)
        print(f"\n[perf] validate_report_set, 4,700-row Tekion current: {elapsed:.3f}s")
        self.assertLess(elapsed, 10.0)


if __name__ == "__main__":
    unittest.main()
