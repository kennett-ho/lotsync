"""
Generates the printable Daily Work Order PDF (GET /tasks/work-order --
see api/routers/tasks.py for the thin routing layer, and
queries/tasks.list_tasks for where the task data itself comes from).
This module owns exactly two things: deciding what English text
represents each Task.task_type (mirroring frontend/src/taskDisplay.ts's
philosophy, so the printed sheet and the Dashboard describe the same
task the same way) and laying it out as a PDF with reportlab. No task
retrieval, no routing, no business-rule logic lives here.

Density, deliberately: a real dealership can have hundreds of open
tasks on one task_type (install_mdd_beacon especially), so entries
print as a compact checkbox+stock# list -- multiple per row for task
types with no per-vehicle fact worth printing, one per (tight) row for
the two task types that do have one (how many days a key's been out).
Whitespace is minimized throughout (margins, header, summary, section
spacing) so a big list stays a printable number of pages.

Pagination is deliberately simple for this first version: each vehicle
entry is wrapped in KeepTogether (or, for the compact grid, relies on
reportlab Table's own row-atomic splitting) so a single work item never
splits across a page break, and each task-type section starts on its
own page. Beyond that, reportlab's normal flow decides where pages
break -- if a large section spans multiple pages, it does so without a
repeated section header; a "Page X of Y" footer (present on every page
via the standard reportlab NumberedCanvas recipe) is what actually
matters if printed pages get separated on the lot.
"""

import io
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Flowable, HRFlowable, KeepTogether, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

PAGE_SIZE = letter
_MARGIN = 0.65 * inch
_INK = colors.HexColor("#0F172A")
_MUTED = colors.HexColor("#64748B")
_FAINT = colors.HexColor("#94A3B8")
_RULE = colors.HexColor("#CBD5E1")
_ACCENT = colors.HexColor("#1D4ED8")

# ─── task_type -> display text ──────────────────────────────────────────
# Mirrors frontend/src/taskDisplay.ts's TASK_TYPE_DISPLAY -- the printed
# work order and the Dashboard's Open Tasks accordion should describe
# the same task_type the same way. Kept as a second, Python-side copy
# rather than a shared file: there's no existing mechanism in this
# project for sharing display strings across the frontend/backend
# language boundary, and duplicating four short constants is far
# simpler than inventing one for this alone.
_TASK_TYPE_DISPLAY = {
    "install_recovr_device": {
        "summary_label": "Install RecovR",
        "section_title": "Install RecovR Devices",
    },
    "install_mdd_beacon": {
        "summary_label": "Install MDD",
        "section_title": "Install MDD Beacons",
    },
    "investigate_checked_out_key": {
        "summary_label": "Investigate Keys",
        "section_title": "Investigate Checked Out Keys",
    },
    "investigate_key_for_recovr": {
        "summary_label": "Investigate Key for RecovR",
        "section_title": "Investigate Key For RecovR",
    },
}

# Print order -- matches the Dashboard's own install-before-investigate
# grouping convention. Any future task_type this dict doesn't know about
# still prints (see _task_display's fallback below); it's just appended
# after these four rather than left out.
_TASK_TYPE_ORDER = list(_TASK_TYPE_DISPLAY.keys())

# Only these two task types have a per-vehicle "how long" fact worth
# printing (see _vehicle_detail) -- the two install task types have
# nothing that varies vehicle-to-vehicle beyond what the section header
# already says, so they print as a dense multi-column stock# grid
# instead (see _compact_grid) rather than one-per-row.
_DETAIL_TASK_TYPES = {"investigate_checked_out_key", "investigate_key_for_recovr"}

# Same pattern/rationale as frontend/src/taskDisplay.ts's parseDaysOut:
# requires a space before "day(s)", which deliberately excludes the
# hyphenated "3-day investigate threshold" phrase also present in
# investigate_checked_out_key's Task.reason text -- that's rule wording,
# never printed here.
_DAYS_OUT_PATTERN = re.compile(r"(\d+)\s+days?\b", re.IGNORECASE)

# How many checkbox+stock# pairs share one row in the dense grid (the
# two install task types). Stock codes are short (e.g. "KT4938A"), so
# this comfortably fits within an 8.5in page without crowding.
_GRID_COLUMNS = 4


def _humanize_task_type(task_type: str) -> str:
    words = task_type.replace("_", " ").title()
    return words.replace("Recovr", "RecovR").replace("Mdd", "MDD")


def _task_display(task_type: str) -> dict:
    known = _TASK_TYPE_DISPLAY.get(task_type)
    if known:
        return known
    title = _humanize_task_type(task_type)
    return {"summary_label": title, "section_title": title}


def _stock_of(task: dict) -> str:
    vehicle = task.get("vehicle") or {}
    return vehicle.get("stock_number") or task.get("vin", "")


def _vehicle_detail(task: dict) -> Optional[str]:
    """Per-vehicle operational line, e.g. "Key checked out 4 days ago"."""
    if task.get("task_type") not in _DETAIL_TASK_TYPES:
        return None
    reason = task.get("reason")
    if not reason:
        return None
    match = _DAYS_OUT_PATTERN.search(reason)
    if not match:
        return None
    days = int(match.group(1))
    return f"Key checked out {days} day{'' if days == 1 else 's'} ago"


def _group_tasks(tasks: list) -> list:
    """Returns [(task_type, [task, ...]), ...] in print order."""
    by_type: dict = {}
    for t in tasks:
        by_type.setdefault(t["task_type"], []).append(t)
    ordered_types = [t for t in _TASK_TYPE_ORDER if t in by_type]
    ordered_types += [t for t in by_type if t not in _TASK_TYPE_ORDER]
    return [(t, by_type[t]) for t in ordered_types]


# ─── Styles ──────────────────────────────────────────────────────────────

_STYLES = {
    "brand": ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=18, textColor=_INK, spaceAfter=1, leading=20),
    "doc_title": ParagraphStyle("doc_title", fontName="Helvetica", fontSize=11.5, textColor=_MUTED, spaceAfter=4, leading=13),
    "meta": ParagraphStyle("meta", fontName="Helvetica", fontSize=9, textColor=_MUTED, leading=11.5),
    "summary_heading": ParagraphStyle("summary_heading", fontName="Helvetica-Bold", fontSize=10.5, textColor=_INK, spaceBefore=10, spaceAfter=3),
    "summary_label": ParagraphStyle("summary_label", fontName="Helvetica", fontSize=10, textColor=_INK),
    "summary_count": ParagraphStyle("summary_count", fontName="Helvetica-Bold", fontSize=10, textColor=_ACCENT, alignment=2),
    "section_title": ParagraphStyle("section_title", fontName="Helvetica-Bold", fontSize=13, textColor=_INK, spaceAfter=1),
    "section_count": ParagraphStyle("section_count", fontName="Helvetica", fontSize=9, textColor=_MUTED, spaceAfter=5),
    "stock_line": ParagraphStyle("stock_line", fontName="Helvetica", fontSize=10, textColor=_INK, leading=12),
    "empty": ParagraphStyle("empty", fontName="Helvetica", fontSize=13, textColor=_MUTED, spaceBefore=28, alignment=1, leading=20),
}


class _Checkbox(Flowable):
    """A small hand-drawn checkbox -- vector, not a Unicode glyph, since
    the base-14 PDF fonts reportlab ships with don't reliably include a
    ballot-box character."""

    def __init__(self, size: float = 8):
        super().__init__()
        self.size = size
        self.width = size
        self.height = size

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(_FAINT)
        self.canv.setLineWidth(0.9)
        self.canv.rect(0, 0.5, self.size, self.size, stroke=1, fill=0)
        self.canv.restoreState()


def _detail_rows(group_tasks: list) -> list:
    """One checkbox+stock#(+detail) per (tight) row -- used for task
    types that have a per-vehicle fact worth printing."""
    story = []
    for task in group_tasks:
        stock = _stock_of(task)
        detail = _vehicle_detail(task)
        text = f"<b>{stock}</b>"
        if detail:
            text += f'&nbsp;&nbsp;&nbsp;<font color="#64748B">{detail}</font>'
        row = Table([[_Checkbox(), Paragraph(text, _STYLES["stock_line"])]], colWidths=[0.2 * inch, None])
        row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("LEFTPADDING", (1, 0), (1, 0), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(KeepTogether([row, HRFlowable(width="100%", thickness=0.3, color=_RULE)]))
    return story


def _compact_grid(group_tasks: list) -> list:
    """checkbox+stock# grid, _GRID_COLUMNS per row -- used for task types
    with nothing per-vehicle worth printing beyond the stock number, so
    hundreds of entries still fit in a printable number of pages. A
    bare Table, not wrapped in KeepTogether: reportlab splits a Table
    at row boundaries by default, which already guarantees no single
    checkbox+stock# pair is ever split (each is a whole cell within one
    row), while still letting the grid flow across as many pages as it
    actually needs."""
    checkbox_w = 0.16 * inch
    text_w = (PAGE_SIZE[0] - 2 * _MARGIN - _GRID_COLUMNS * checkbox_w) / _GRID_COLUMNS
    col_widths = [checkbox_w, text_w] * _GRID_COLUMNS

    rows = []
    for i in range(0, len(group_tasks), _GRID_COLUMNS):
        row_tasks = group_tasks[i:i + _GRID_COLUMNS]
        cells = []
        for task in row_tasks:
            cells.append(_Checkbox())
            cells.append(Paragraph(f"<b>{_stock_of(task)}</b>", _STYLES["stock_line"]))
        while len(cells) < _GRID_COLUMNS * 2:
            cells.append("")
        rows.append(cells)

    grid = Table(rows, colWidths=col_widths, repeatRows=0)
    grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, _RULE),
    ]))
    return [grid]


def _build_story(tasks: list, store_name: str, generated_at: datetime) -> list:
    story = [
        Paragraph("LotSync", _STYLES["brand"]),
        Paragraph("Daily Work Order", _STYLES["doc_title"]),
        Paragraph(store_name, _STYLES["meta"]),
        Paragraph(
            f"Generated: {generated_at.strftime('%B %d, %Y')} at "
            f"{generated_at.strftime('%I:%M %p').lstrip('0')}",
            _STYLES["meta"],
        ),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=1, color=_INK),
    ]

    if not tasks:
        story.append(Paragraph("No open tasks.", _STYLES["empty"]))
        story.append(Paragraph("No work is currently required.", _STYLES["empty"]))
        return story

    groups = _group_tasks(tasks)

    story.append(Paragraph("Summary &mdash; Open Tasks", _STYLES["summary_heading"]))
    summary_rows = [
        [Paragraph(_task_display(task_type)["summary_label"], _STYLES["summary_label"]),
         Paragraph(str(len(group_tasks)), _STYLES["summary_count"])]
        for task_type, group_tasks in groups
    ]
    summary_table = Table(summary_rows, colWidths=[4.3 * inch, 1.0 * inch], hAlign="LEFT")
    summary_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, _RULE),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    for index, (task_type, group_tasks) in enumerate(groups):
        display = _task_display(task_type)
        # The first section flows naturally right after the summary --
        # only later sections force a fresh page, so a short work order
        # (one or two task types) doesn't waste a whole page on nothing
        # but the summary.
        if index > 0:
            story.append(PageBreak())
        story.append(Paragraph(display["section_title"].upper(), _STYLES["section_title"]))
        story.append(Paragraph(
            f"{len(group_tasks)} vehicle{'' if len(group_tasks) == 1 else 's'}",
            _STYLES["section_count"],
        ))
        story.append(HRFlowable(width="100%", thickness=1.1, color=_INK, spaceAfter=6))
        if task_type in _DETAIL_TASK_TYPES:
            story.extend(_detail_rows(group_tasks))
        else:
            story.extend(_compact_grid(group_tasks))

    return story


def _numbered_canvas_factory(footer_date_label: str, page_count_out: dict):
    """
    Standard reportlab recipe for a "Page X of Y" footer: the total page
    count isn't known until the whole story has been laid out once, so
    this buffers every page's drawing state via showPage(), then -- once
    save() is finally called with the true total in hand -- replays each
    buffered page, draws the footer with that total, and only then
    actually emits it. page_count_out is a plain dict the caller reads
    after doc.build() returns, so build_work_order() can report the
    real page count without a second PDF-parsing dependency.
    """
    page_width, _ = PAGE_SIZE

    class _NumberedCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            pdfcanvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._saved_page_states)
            page_count_out["total"] = total
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total)
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)

        def _draw_footer(self, total_pages):
            self.saveState()
            self.setStrokeColor(_RULE)
            self.setLineWidth(0.5)
            self.line(_MARGIN, 0.5 * inch, page_width - _MARGIN, 0.5 * inch)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(_FAINT)
            self.drawString(_MARGIN, 0.34 * inch, f"Generated by LotSync · {footer_date_label}")
            self.drawRightString(page_width - _MARGIN, 0.34 * inch, f"Page {self._pageNumber} of {total_pages}")
            self.restoreState()

    return _NumberedCanvas


@dataclass
class WorkOrderResult:
    pdf_bytes: bytes
    page_count: int


def build_work_order(tasks: list, store_name: str, generated_at: Optional[datetime] = None) -> WorkOrderResult:
    """
    tasks: the shape queries/tasks.list_tasks(conn, commitment_standing='outstanding')
    already returns -- a list of dicts, each with task_type/reason/vin
    and a nested "vehicle" summary dict. No query, no HTTP, no
    reportlab-specific knowledge belongs in the caller.
    """
    if generated_at is None:
        generated_at = datetime.now()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=PAGE_SIZE,
        topMargin=0.6 * inch, bottomMargin=0.68 * inch,
        leftMargin=_MARGIN, rightMargin=_MARGIN,
        title="LotSync Daily Work Order",
    )
    story = _build_story(tasks, store_name, generated_at)

    page_count_out: dict = {}
    doc.build(
        story,
        canvasmaker=_numbered_canvas_factory(generated_at.strftime("%A, %B %d, %Y"), page_count_out),
    )
    return WorkOrderResult(pdf_bytes=buffer.getvalue(), page_count=page_count_out.get("total", 1))


def work_order_filename(generated_at: Optional[datetime] = None) -> str:
    if generated_at is None:
        generated_at = datetime.now()
    return f"Lotsync_Work_Order_{generated_at.strftime('%Y-%m-%d')}.pdf"
