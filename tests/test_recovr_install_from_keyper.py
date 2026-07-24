"""
Unit tests for build_recovr_install_from_keyper -- the Keyper-driven
RecovR install list (starts from "we have a physical key," not from
Tekion's Stocked-In status).
"""

import unittest
import pandas as pd

from lotsync.sync.reconciler import build_recovr_install_from_keyper


def _matched_row(vin, stock, status="In"):
    return {
        "keyper_identifier": stock, "keyper_status": status,
        "tekion_stock": stock, "tekion_vin": vin, "tekion_vehicle": "2024 Test",
    }


class TestBuildRecovrInstallFromKeyper(unittest.TestCase):
    def test_vehicle_with_no_recovr_and_no_wholesale_step_is_included(self):
        fully_verified = pd.DataFrame([_matched_row("VIN0000000000001", "K1")])
        key_out_aging = pd.DataFrame(columns=fully_verified.columns)
        recovr = pd.DataFrame(columns=["VIN", "Paired"])
        rapidrecon = pd.DataFrame(columns=["VIN", "Step"])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 1)
        self.assertEqual(len(review), 0)

    def test_vehicle_already_paired_in_recovr_is_excluded(self):
        fully_verified = pd.DataFrame([_matched_row("VIN0000000000002", "K2")])
        key_out_aging = pd.DataFrame(columns=fully_verified.columns)
        recovr = pd.DataFrame([{"VIN": "VIN0000000000002", "Paired": "Yes"}])
        rapidrecon = pd.DataFrame(columns=["VIN", "Step"])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 0)

    def test_wholesale_step_excludes_vehicle(self):
        fully_verified = pd.DataFrame([_matched_row("VIN0000000000003", "K3")])
        key_out_aging = pd.DataFrame(columns=fully_verified.columns)
        recovr = pd.DataFrame(columns=["VIN", "Paired"])
        rapidrecon = pd.DataFrame([{"VIN": "VIN0000000000003", "Step": "WHOLESALE"}])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 0)

    def test_at_auction_step_excludes_vehicle(self):
        fully_verified = pd.DataFrame([_matched_row("VIN0000000000004", "K4")])
        key_out_aging = pd.DataFrame(columns=fully_verified.columns)
        recovr = pd.DataFrame(columns=["VIN", "Paired"])
        rapidrecon = pd.DataFrame([{"VIN": "VIN0000000000004", "Step": "AT AUCTION"}])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 0)

    def test_archive_step_goes_to_needs_review_not_auto_excluded_or_included(self):
        fully_verified = pd.DataFrame([_matched_row("VIN0000000000005", "K5")])
        key_out_aging = pd.DataFrame(columns=fully_verified.columns)
        recovr = pd.DataFrame(columns=["VIN", "Paired"])
        rapidrecon = pd.DataFrame([{"VIN": "VIN0000000000005", "Step": "Archive"}])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 0)
        self.assertEqual(len(review), 1)

    def test_other_recon_step_does_not_exclude(self):
        # A step that isn't WHOLESALE/AT AUCTION/Archive shouldn't
        # affect inclusion at all -- only the two confirmed exclusion
        # steps and the one review step have any effect.
        fully_verified = pd.DataFrame([_matched_row("VIN0000000000006", "K6")])
        key_out_aging = pd.DataFrame(columns=fully_verified.columns)
        recovr = pd.DataFrame(columns=["VIN", "Paired"])
        rapidrecon = pd.DataFrame([{"VIN": "VIN0000000000006", "Step": "MARK FRONTLINE"}])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 1)

    def test_short_recovr_vin_fragment_resolves_via_unique_last6_match(self):
        fully_verified = pd.DataFrame([_matched_row("AAAAAAAAAAA123456", "K7")])
        key_out_aging = pd.DataFrame(columns=fully_verified.columns)
        recovr = pd.DataFrame([{"VIN": "123456", "Paired": "Yes"}])
        rapidrecon = pd.DataFrame(columns=["VIN", "Step"])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 0)  # correctly excluded via fragment match

    def test_key_out_aging_vehicles_also_included_in_population(self):
        fully_verified = pd.DataFrame(columns=["keyper_identifier", "keyper_status",
                                                 "tekion_stock", "tekion_vin", "tekion_vehicle"])
        key_out_aging = pd.DataFrame([_matched_row("VIN0000000000008", "K8", status="Out")])
        recovr = pd.DataFrame(columns=["VIN", "Paired"])
        rapidrecon = pd.DataFrame(columns=["VIN", "Step"])
        install, review, _ = build_recovr_install_from_keyper(
            fully_verified, key_out_aging, pd.DataFrame(), recovr, rapidrecon)
        self.assertEqual(len(install), 1)
        self.assertEqual(install.iloc[0]["keyper_status"], "Out")


if __name__ == "__main__":
    unittest.main()
