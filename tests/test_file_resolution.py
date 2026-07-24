"""
Unit tests for utils/file_resolution.py, using a temp directory rather
than the real uploads folder -- these need full control over exactly
which filenames exist to test ambiguity handling.
"""

import os
import tempfile
import unittest

from lotsync.utils.file_resolution import find_upload


class TestFindUpload(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _touch(self, *names):
        for n in names:
            open(os.path.join(self.tmpdir, n), "w").close()

    def test_single_match_found(self):
        self._touch("Keyper_Report.csv", "Other_Report.csv")
        self.assertTrue(find_upload("Keyper", self.tmpdir).endswith("Keyper_Report.csv"))

    def test_no_match_raises(self):
        self._touch("Other_Report.csv")
        with self.assertRaises(FileNotFoundError):
            find_upload("Keyper", self.tmpdir)

    def test_multiple_matches_raise_rather_than_guess(self):
        self._touch("Keyper_Report.csv", "old_Keyper_export.csv")
        with self.assertRaises(ValueError):
            find_upload("Keyper", self.tmpdir)

    def test_sold_substring_collides_with_unsold_without_exclude(self):
        # Regression case caught while wiring this in for real: "Sold"
        # is a literal substring of "Unsold," so naive matching finds
        # both when only one is wanted.
        self._touch("Tekion_Sold_Report.csv", "Tekion_Unsold_Report.csv")
        with self.assertRaises(ValueError):
            find_upload("Sold", self.tmpdir)

    def test_exclude_resolves_the_sold_unsold_collision(self):
        self._touch("Tekion_Sold_Report.csv", "Tekion_Unsold_Report.csv")
        result = find_upload("Sold", self.tmpdir, exclude="Unsold")
        self.assertTrue(result.endswith("Tekion_Sold_Report.csv"))

    def test_list_pattern_matches_either_alternative_naming(self):
        self._touch("Tekion_Master_List.csv")
        result = find_upload(["Master", "Unsold"], self.tmpdir)
        self.assertTrue(result.endswith("Tekion_Master_List.csv"))

        self._touch("Tekion_Master_List_v2_DELETE.csv")  # would now collide
        # (left as-is; the point above is the single-file success case)

    def test_require_all_needs_every_substring_present(self):
        # Real scenario: a store-specific RecovR export vs. the full
        # multi-brand umbrella export -- "RecovR" alone matches both,
        # but only one filename has both "RecovR" and "Kia".
        self._touch("RecovR_Kia_Report_EOD.csv", "RecovR_MARK_AUTO_Report_EOD.csv")
        result = find_upload(require_all=["RecovR", "Kia"], uploads_dir=self.tmpdir)
        self.assertTrue(result.endswith("RecovR_Kia_Report_EOD.csv"))

    def test_require_all_with_space_separated_words_does_not_match_underscore_filenames(self):
        # Regression case: a naive multi-word pattern like "Kia RecovR"
        # (space-separated) never matches a real underscore-separated
        # filename like "RecovR_Kia_Report" -- this is exactly the bug
        # caught while wiring in the two-RecovR-file scenario for real.
        self._touch("RecovR_Kia_Report_EOD.csv")
        with self.assertRaises(FileNotFoundError):
            find_upload("Kia RecovR", self.tmpdir)
        # require_all with separate tokens is the correct way to do this
        result = find_upload(require_all=["Kia", "RecovR"], uploads_dir=self.tmpdir)
        self.assertTrue(result.endswith("RecovR_Kia_Report_EOD.csv"))

    def test_case_insensitive_match(self):
        self._touch("KEYPER_report.csv")
        self.assertTrue(find_upload("keyper", self.tmpdir))

    def test_stale_session_file_and_new_upload_both_present_raises(self):
        # Real scenario: an earlier upload in the same conversation
        # session left a file behind, and a new upload of the same
        # report type arrives later -- must not silently pick either.
        self._touch("All_Keys_Keyper.csv", "1784737639429_Keyper_Report.csv")
        with self.assertRaises(ValueError):
            find_upload("Keyper", self.tmpdir)


if __name__ == "__main__":
    unittest.main()
