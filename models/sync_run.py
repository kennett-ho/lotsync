"""
Identified during the frontend discovery review as effectively
foundational to Phase 2, not a later addition -- every Event needs to
trace back to which sync run detected it, both for auditability and
for the "Connected Systems" dashboard panel (per-source record count
and last-sync time), which is a derived view over SyncRun rather than
its own separate model (see ARCHITECTURE.md -- SystemStatus was
proposed as a distinct model in the original review request and
deliberately rejected in favor of this, to avoid two sources of truth
that can drift apart).

Built and in real use as of Phase 2 Sprint 3 (see
database/migrations/0003_sync_run.sql and
database/repository.py's sync_run()) -- this dataclass is now a stale-
docstring fix, not scaffolding: sync_run_id is a real autoincrement
integer (not a string) once persisted, and `status` gained a fourth
value, "in_progress" (see DATA_MODEL.md, added under the same
"genuine architectural flaw" trigger that added Event.event_id --
the original three values had no way to describe a row between
INSERT and completion).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SyncRun:
    sync_run_id: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    source: Optional[str] = None          # e.g. "tekion", "keyper", "mdd", "recovr", "rapidrecon"
    dealership_id: Optional[str] = None   # which dealership's export this run processed
    records_processed: Optional[int] = None
    issues_found: Optional[int] = None
    tasks_generated: Optional[int] = None
    status: Optional[str] = None          # "in_progress" / "complete" / "delayed" / "failed"
