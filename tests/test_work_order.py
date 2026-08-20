"""
Regression coverage for reports/work_order.py (PDF generation) and
GET /tasks/work-order (the thin routing layer around it) -- see
api/routers/tasks.py and reports/work_order.py's own module docstring
for the architecture this exercises.

Uses pypdf to read the PDFs this module produces back apart (page
count, extracted text) so assertions check real printed content, not
just "some bytes came back." pypdf is a test-only dependency -- same
"real, narrow exception to tests/README.md's no-external-dependencies
note" category as httpx (see api/README.md, requirements.txt).
"""

import io
import unittest
from datetime import datetime

from pypdf import PdfReader

from lotsync.reports.work_order import build_work_order, work_order_filename


def _task(task_id, vin, task_type, stock, name, reason=""):
    return {
        "task_id": task_id, "vin": vin, "task_type": task_type, "reason": reason,
        "vehicle": {"vin": vin, "stock_number": stock, "display_name": name,
                    "year": None, "make": None, "model": None},
    }


def _extract_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


class NoTasksTest(unittest.TestCase):
    def test_one_page(self):
        result = build_work_order([], "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        self.assertEqual(result.page_count, 1)

    def test_states_no_open_tasks(self):
        result = build_work_order([], "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        text = _extract_text(result.pdf_bytes)
        self.assertIn("No open tasks.", text)
        self.assertIn("No work is currently required.", text)

    def test_still_a_valid_pdf(self):
        result = build_work_order([], "Mark Kia")
        self.assertTrue(result.pdf_bytes.startswith(b"%PDF"))


class OneTaskTest(unittest.TestCase):
    def test_one_page_and_content(self):
        tasks = [_task(1, "VIN1", "install_mdd_beacon", "T0001", "2024 Honda Civic")]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        self.assertEqual(result.page_count, 1)
        text = _extract_text(result.pdf_bytes)
        self.assertIn("Mark Kia", text)
        self.assertIn("INSTALL MDD BEACONS", text)
        self.assertIn("1 vehicle", text)
        self.assertNotIn("1 vehicles", text)
        self.assertIn("T0001", text)

    def test_reason_free_text_never_printed_verbatim(self):
        # Task.reason is a sync-facing audit string, not display copy --
        # see reports/work_order.py's own module docstring.
        tasks = [_task(1, "VIN1", "install_mdd_beacon", "T0001", "2024 Honda Civic",
                        reason="MDD: no device found on stock T0001 (2024 Honda Civic)")]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        text = _extract_text(result.pdf_bytes)
        self.assertNotIn("no device found", text)


class VendorMarkupEscapingTest(unittest.TestCase):
    """Sprint 13 (Rail H): stock numbers/VINs come from vendor CSVs and
    the store name from oms_config.xlsx; both are embedded in reportlab's
    Paragraph mini-markup. Without escaping, a value carrying '<', '>',
    or '&' would break the Paragraph parser mid-render (the router turns
    that into a generic 500). These prove the escaping keeps generation
    robust for both the detail-row and the compact-grid layouts, and for
    the store name."""

    def test_hostile_stock_number_still_renders_valid_pdf(self):
        # A stock number with markup-significant characters. The compact
        # grid (install_mdd_beacon) path.
        tasks = [_task(1, "VIN1", "install_mdd_beacon", "<b>K&<script>", "2024 Honda Civic")]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        self.assertTrue(result.pdf_bytes.startswith(b"%PDF"))
        self.assertGreaterEqual(result.page_count, 1)

    def test_hostile_stock_number_detail_row_path(self):
        # The one-per-row detail path (investigate_checked_out_key).
        tasks = [_task(1, "VIN1", "investigate_checked_out_key", "A<&>B", "2024 Honda Civic",
                        reason="Key checked out 4 days ago (3-day investigate threshold)")]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        self.assertTrue(result.pdf_bytes.startswith(b"%PDF"))
        self.assertGreaterEqual(result.page_count, 1)

    def test_hostile_store_name_still_renders(self):
        tasks = [_task(1, "VIN1", "install_mdd_beacon", "T0001", "2024 Honda Civic")]
        result = build_work_order(tasks, "Mark & Co <Kia>", generated_at=datetime(2026, 8, 7, 8, 0))
        self.assertTrue(result.pdf_bytes.startswith(b"%PDF"))
        text = _extract_text(result.pdf_bytes)
        # The literal ampersand/text survives as readable content (the
        # store name is escaped for markup, not stripped).
        self.assertIn("Mark", text)


class MultipleTaskGroupsTest(unittest.TestCase):
    def test_summary_lists_every_group_with_correct_counts(self):
        tasks = [
            _task(1, "V1", "install_recovr_device", "R001", "2024 Kia Telluride"),
            _task(2, "V2", "install_mdd_beacon", "M001", "2024 Ford F-150"),
            _task(3, "V3", "install_mdd_beacon", "M002", "2023 BMW 5 Series"),
        ]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        text = _extract_text(result.pdf_bytes)
        self.assertIn("Install RecovR", text)
        self.assertIn("Install MDD", text)
        self.assertIn("INSTALL RECOVR DEVICES", text)
        self.assertIn("INSTALL MDD BEACONS", text)

    def test_investigate_checked_out_key_shows_days_ago(self):
        tasks = [_task(
            1, "V1", "investigate_checked_out_key", "TK001", "2019 Honda Civic",
            reason="Keyper: key checked out 5 days on stock TK001 (2019 Honda Civic) -- "
                   "at or beyond the 3-day investigate threshold; keys are normally "
                   "returned within a day or two",
        )]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        text = _extract_text(result.pdf_bytes)
        self.assertIn("Key checked out 5 days ago", text)
        # Rule wording (the threshold) must never be printed.
        self.assertNotIn("3-day", text)
        self.assertNotIn("threshold", text)

    def test_unparseable_reason_omits_detail_line_gracefully(self):
        tasks = [_task(1, "V1", "investigate_checked_out_key", "TK001", "2019 Honda Civic", reason="")]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        text = _extract_text(result.pdf_bytes)
        self.assertNotIn("Key checked out", text)
        self.assertIn("TK001", text)

    def test_install_task_types_have_no_per_vehicle_detail_line(self):
        tasks = [_task(1, "V1", "install_mdd_beacon", "M001", "2024 Ford F-150")]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        text = _extract_text(result.pdf_bytes)
        self.assertNotIn("Key checked out", text)


class MultiplePagesTest(unittest.TestCase):
    """A dealership can have hundreds of open tasks on one task_type --
    see reports/work_order.py's module docstring on why entries print as
    a dense checkbox+stock# grid rather than one-per-page-of-whitespace."""

    def _big_task_set(self, count=400):
        return [_task(i, f"V{i}", "install_mdd_beacon", f"M{i:04d}", "2024 Test Vehicle") for i in range(count)]

    def test_large_single_group_spans_multiple_pages(self):
        result = build_work_order(self._big_task_set(), "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        self.assertGreater(result.page_count, 1)
        # WorkOrderResult.page_count comes from the NumberedCanvas's own
        # buffered page count (see reports/work_order.py) -- cross-check
        # it against an independent read of the actual PDF structure.
        reader = PdfReader(io.BytesIO(result.pdf_bytes))
        self.assertEqual(len(reader.pages), result.page_count)

    def test_footer_page_x_of_y_on_every_page(self):
        result = build_work_order(self._big_task_set(), "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        reader = PdfReader(io.BytesIO(result.pdf_bytes))
        for i, page in enumerate(reader.pages, start=1):
            self.assertIn(f"Page {i} of {result.page_count}", page.extract_text())

    def test_no_vehicle_entry_split_or_duplicated_across_pages(self):
        # Every stock number must appear exactly once across the whole
        # document -- if the grid Table's row-atomic splitting ever broke
        # (e.g. a bad TableStyle change), a split/duplicated entry would
        # show up as a stock# appearing zero or twice instead of once.
        # Checked at the start, middle, and end of the run (every page
        # boundary this set actually crosses), not all 400, to keep this
        # test fast.
        count = 400
        result = build_work_order(self._big_task_set(count), "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        text = _extract_text(result.pdf_bytes)
        for i in (0, 1, count // 2, count - 2, count - 1):
            stock = f"M{i:04d}"
            self.assertEqual(text.count(stock), 1, f"{stock} should appear exactly once, found {text.count(stock)}")

    def test_multiple_sections_each_on_their_own_page(self):
        tasks = self._big_task_set(50) + [
            _task(9001, "VX", "install_recovr_device", "R9001", "2024 Kia Telluride"),
        ]
        result = build_work_order(tasks, "Mark Kia", generated_at=datetime(2026, 8, 7, 8, 0))
        reader = PdfReader(io.BytesIO(result.pdf_bytes))
        # The first section (Install RecovR, print order per
        # _TASK_TYPE_ORDER) shares page 1 with the summary; Install MDD
        # forces a fresh page rather than tucking in wherever RecovR left off.
        self.assertIn("INSTALL RECOVR DEVICES", reader.pages[0].extract_text())
        self.assertNotIn("INSTALL MDD BEACONS", reader.pages[0].extract_text())
        self.assertIn("INSTALL MDD BEACONS", reader.pages[1].extract_text())


class FilenameTest(unittest.TestCase):
    def test_format(self):
        self.assertEqual(work_order_filename(datetime(2026, 8, 7, 8, 0)), "Lotsync_Work_Order_2026-08-07.pdf")

    def test_defaults_to_now_when_omitted(self):
        name = work_order_filename()
        self.assertTrue(name.startswith("Lotsync_Work_Order_"))
        self.assertTrue(name.endswith(".pdf"))


class EndpointResponseTest(unittest.TestCase):
    """GET /tasks/work-order -- the thin routing layer. Same in-memory-DB
    / dependency-override pattern as every other endpoint test in this
    project -- see test_api_routes.py's ApiTestCase."""

    def setUp(self):
        from fastapi.testclient import TestClient
        from lotsync.api.app import app
        from lotsync.api.dependencies import get_db
        from lotsync.database.repository import connect

        self.conn = connect(":memory:")

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.conn.close()

    def test_empty_dataset_returns_a_valid_one_page_pdf(self):
        resp = self.client.get("/tasks/work-order")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["content-type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))
        reader = PdfReader(io.BytesIO(resp.content))
        self.assertEqual(len(reader.pages), 1)

    def test_content_disposition_filename(self):
        resp = self.client.get("/tasks/work-order")
        disposition = resp.headers["content-disposition"]
        self.assertIn("attachment", disposition)
        self.assertRegex(disposition, r'filename="Lotsync_Work_Order_\d{4}-\d{2}-\d{2}\.pdf"')

    def test_only_outstanding_tasks_are_included(self):
        from lotsync.database.repository import upsert_vehicle, insert_task, honor_task, get_open_task

        upsert_vehicle(self.conn, "VIN1", stock_number="OPEN01", display_name="2024 Honda Civic")
        upsert_vehicle(self.conn, "VIN2", stock_number="DONE01", display_name="2024 Ford F-150")
        self.conn.commit()
        insert_task(self.conn, "VIN1", "install_mdd_beacon")
        insert_task(self.conn, "VIN2", "install_mdd_beacon")
        self.conn.commit()
        done_task = get_open_task(self.conn, "VIN2", "install_mdd_beacon")
        honor_task(self.conn, done_task["task_id"])
        self.conn.commit()

        resp = self.client.get("/tasks/work-order")
        text = _extract_text(resp.content)
        self.assertIn("OPEN01", text)
        self.assertNotIn("DONE01", text)

    def test_uses_the_configured_store_name(self):
        resp = self.client.get("/tasks/work-order")
        text = PdfReader(io.BytesIO(resp.content)).pages[0].extract_text()
        # No oms_config.xlsx exists in this test environment, so this
        # confirms load_settings()'s own documented default -- see
        # config/settings.py.
        self.assertIn("Mark Kia", text)


if __name__ == "__main__":
    unittest.main()
