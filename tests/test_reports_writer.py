"""
Unit tests for reports/writer.py's write_reports -- specifically the
non-existent-out_dir case (a fresh deployment's persistent disk starts
empty; nothing else creates this directory ahead of time). See
PROJECT: Inventory Sync failed in production with "Cannot save file
into a non-existent directory: /var/data/outputs" -- write_reports
never created out_dir itself, relying entirely on it already existing.
"""

import os
import shutil
import tempfile
import unittest

import pandas as pd

from lotsync.reports.writer import write_reports


class WriteReportsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def test_creates_out_dir_when_it_does_not_exist(self):
        out_dir = os.path.join(self.tmpdir, "does", "not", "exist", "yet")
        self.assertFalse(os.path.isdir(out_dir))

        outputs = {"report.csv": pd.DataFrame({"vin": ["1TESTVIN000000001"]})}
        write_reports(outputs, out_dir)

        written_path = os.path.join(out_dir, "report.csv")
        self.assertTrue(os.path.isfile(written_path))
        with open(written_path) as f:
            self.assertIn("1TESTVIN000000001", f.read())

    def test_still_works_when_out_dir_already_exists(self):
        out_dir = os.path.join(self.tmpdir, "already_here")
        os.makedirs(out_dir)

        outputs = {"report.csv": pd.DataFrame({"vin": ["1TESTVIN000000002"]})}
        write_reports(outputs, out_dir)

        self.assertTrue(os.path.isfile(os.path.join(out_dir, "report.csv")))

    def test_writes_every_output_file(self):
        out_dir = os.path.join(self.tmpdir, "multi")
        outputs = {
            "a.csv": pd.DataFrame({"x": [1]}),
            "b.csv": pd.DataFrame({"y": [2]}),
        }
        write_reports(outputs, out_dir)

        self.assertEqual(
            sorted(os.listdir(out_dir)),
            ["a.csv", "b.csv"],
        )


if __name__ == "__main__":
    unittest.main()
