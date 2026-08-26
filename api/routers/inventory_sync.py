"""
Phase 3, Sprint 4 -- the Inventory Sync page's backend surface.
Sprint 10 (Rail D, Inventory Ingestion Safety) -- the ingestion
boundary's two endpoints.

POST /inventory-sync/run is still the one mutating endpoint, and it is
deliberately synchronous and single-request per PHASE_3_SPRINT_4's own
plan. Sprint 10 adds POST /inventory-sync/validate -- the pre-sync
preview -- and, more importantly, makes /run revalidate everything
itself: the preview is UX, the run-time validation is the invariant.
A direct API caller who never calls /validate gets exactly the same
classification, validation, and warning gating, recomputed
server-side from the bytes actually uploaded (V1_1_RELEASE_READINESS
5.D: "only validated evidence can proceed to the sync engine").

The warning-acknowledgement contract (Sprint 10 phases 16/18/20):

- Validation ERRORs always reject (422 REPORT_VALIDATION_FAILED).
  Nothing mutates.
- Validation WARNINGs require BOTH acknowledge_warnings=true AND a
  validation_fingerprint matching the just-recomputed report set
  (409 WARNINGS_NOT_ACKNOWLEDGED / STALE_VALIDATION otherwise).
  The fingerprint is derived from the uploaded bytes (sha256 per
  file), so "I acknowledge" can only ever refer to the exact files
  the server is looking at -- swapping a file after previewing, or
  acknowledging blind without previewing, both fail closed. The
  frontend never auto-checks the acknowledgement box; the server
  would reject a fabricated one anyway.
- No warnings -> no acknowledgement needed; fingerprint is ignored.

This router's own job stays narrow -- parse the six optional upload
slots, save them (size-capped, fixed server-side names), validate
through sync/ingestion.py, and only then hand the same plain dict of
file paths to sync/pipeline.run_inventory_sync, which is unchanged by
Sprint 10. No reconciliation logic here, and no validation logic
either -- sync/ingestion.py is the single boundary both endpoints
(and any future acquisition path) share.

Sprint 15 follow-up (owner decision D4, ratified 2026-08-21): raw
upload batches are temporary operational evidence with bounded
retention -- each request end stamps an outcome.json marker, and an
opportunistic sweep at the start of both endpoints deletes batches
older than their outcome's window (api/upload_retention.py; policy
record DATA_RETENTION.md section 3).
"""

import datetime
import logging
import os
import shutil
import sqlite3
import tempfile
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from lotsync.api import observability, upload_retention
from lotsync.api.auth import SYNC_RUN_ROLES, require_roles
from lotsync.api.dependencies import get_db
from lotsync.api.dtos import (
    IngestionValidationDTO, PendingIdentityDTO, SyncRunBatchDTO, SyncSummaryDTO,
)
from lotsync.config.settings import (
    load_settings, load_day_out_buckets, load_incoming_missing_buckets,
    load_new_car_buckets, load_internal_fleet_vins,
)
from lotsync.queries.inventory_sync import list_pending_identities, sync_run_history
from lotsync.sync.ingestion import MAX_UPLOAD_BYTES, validate_report_set
from lotsync.sync.pipeline import run_inventory_sync
from lotsync.sync.report_contracts import SLOT_CONTRACTS

router = APIRouter(prefix="/inventory-sync", tags=["inventory-sync"])

# Kept entirely separate from main.py's LOTSYNC_UPLOADS_DIR (the CLI's
# find_upload()-scanned folder) so the CLI and API upload workflows never
# collide or race -- see sync/pipeline.py's module docstring.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.environ.get("LOTSYNC_API_UPLOADS_DIR", os.path.join(_REPO_ROOT, "data", "api_uploads"))

# Same env var main.py's OUT_DIR already uses -- the API path is meant to
# become the dealership's real sync mechanism (this sprint's Primary
# Objective), not a parallel test path, so it writes the same CSVs to the
# same place.
OUT_DIR = os.environ.get("LOTSYNC_OUT_DIR", os.path.join(_REPO_ROOT, "data", "outputs"))


async def _save_uploads(provided: dict, batch_dir: str) -> dict:
    """
    Streams each upload to batch_dir under this router's own fixed,
    per-slot filenames. Never uses the client-supplied filename as (or
    in) a filesystem path -- `source` is one of the router's fixed
    dict keys, not client input (see PRE_DEPLOYMENT_REVIEW.md's
    Critical finding and its regression test). Writing stops at
    MAX_UPLOAD_BYTES + 1 bytes: one byte past the limit is all
    validation needs to prove the file is oversized (FILE_TOO_LARGE),
    and a hostile multi-gigabyte body never lands on disk.
    """
    file_paths = {}
    for source, upload in provided.items():
        dest = os.path.join(batch_dir, f"{source}.csv")
        remaining = MAX_UPLOAD_BYTES + 1
        with open(dest, "wb") as f:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                if remaining > 0:
                    f.write(chunk[:remaining])
                    remaining -= min(len(chunk), remaining)
        file_paths[source] = dest
    return file_paths


def _reject(status_code: int, code: str, validation) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "validation": validation.to_dict()},
    )


def _log_validation(validation, duration_ms: float) -> None:
    """
    Sprint 11 (phase 20): one structured record per validation pass,
    from BOTH the preview endpoint and /run's revalidation. Carries
    classification/outcome facts only -- issue codes, report types,
    row counts, duration. Never filenames, report contents, rows,
    VINs, or raw parser text (sync/ingestion.py already normalizes
    parser failures into codes before anything reaches here).
    """
    event = ("inventory_validation_blocked" if validation.has_errors
             else "inventory_validation_warning" if validation.has_warnings
             else "inventory_validation_completed")
    level = logging.INFO if event == "inventory_validation_completed" else logging.WARNING
    observability.log_event(
        level, event,
        duration_ms=round(duration_ms, 1),
        reports=[{
            "slot": r.slot,
            "detected": r.detected_contract_id or None,
            "status": r.status,
            "total_rows": r.total_rows,
            "valid_rows": r.valid_rows,
            "codes": sorted({i.code for i in r.issues}),
        } for r in validation.reports],
    )


# Sprint 05: role-restricted -- running a sync mutates dealership
# state, and the governed role model gives that to admin/manager only
# (see api/auth.py's SYNC_RUN_ROLES note). Inert under
# AUTH_MODE=disabled, like the rest of the auth layer.
@router.post("/run", response_model=SyncSummaryDTO,
             dependencies=[Depends(require_roles(*SYNC_RUN_ROLES))])
async def run_sync(
    tekion_unsold: Optional[UploadFile] = File(None),
    tekion_sold: Optional[UploadFile] = File(None),
    keyper: Optional[UploadFile] = File(None),
    mdd: Optional[UploadFile] = File(None),
    recovr: Optional[UploadFile] = File(None),
    rapidrecon: Optional[UploadFile] = File(None),
    acknowledge_warnings: bool = Form(False),
    validation_fingerprint: Optional[str] = Form(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    uploads = {
        "tekion": tekion_unsold, "sold": tekion_sold, "keyper": keyper,
        "mdd": mdd, "recovr": recovr, "rapidrecon": rapidrecon,
    }
    provided = {source: upload for source, upload in uploads.items() if upload is not None}
    if not provided:
        raise HTTPException(status_code=422, detail=["At least one report file is required."])

    # D4 bounded retention (DATA_RETENTION.md §3): the opportunistic
    # sweep runs BEFORE this request's batch directory exists, so the
    # in-flight batch is structurally untouchable. Never raises.
    upload_retention.sweep(UPLOADS_DIR)

    batch_dir = os.path.join(UPLOADS_DIR, datetime.datetime.now().strftime("%Y%m%dT%H%M%S%f"))
    os.makedirs(batch_dir, exist_ok=True)
    file_paths = await _save_uploads(provided, batch_dir)

    # Sprint 10: the full ingestion boundary, recomputed HERE from the
    # uploaded bytes regardless of any prior /validate call -- classify,
    # validate, compare baselines, and gate warnings, all before
    # run_inventory_sync can touch anything. A failed validation leaves
    # zero operational mutation (no sync_run row, no event, no task, no
    # report CSVs) -- the uploaded files themselves remain in
    # UPLOADS_DIR as evidence of what was rejected, now bounded by
    # D4's 30-day rejected window (api/upload_retention.py).
    validation_started = time.perf_counter()
    validation = validate_report_set(file_paths, db_conn=conn)
    _log_validation(validation, (time.perf_counter() - validation_started) * 1000)
    # D4: each terminal outcome stamps the batch's outcome.json marker
    # so the retention sweep can apply the ratified window (accepted
    # 7d; rejected / unacknowledged-warning 30d). The 500 path below
    # deliberately writes NO marker -- a failed sync's batch ages
    # under the conservative 30-day unmarked window instead of a
    # window that presumes an outcome it never reached.
    if validation.has_errors:
        upload_retention.record_outcome(batch_dir, upload_retention.OUTCOME_REJECTED)
        raise _reject(422, "REPORT_VALIDATION_FAILED", validation)
    if validation.has_warnings:
        if not acknowledge_warnings:
            upload_retention.record_outcome(
                batch_dir, upload_retention.OUTCOME_WARNINGS_UNACKNOWLEDGED)
            raise _reject(409, "WARNINGS_NOT_ACKNOWLEDGED", validation)
        if validation_fingerprint != validation.fingerprint:
            upload_retention.record_outcome(
                batch_dir, upload_retention.OUTCOME_WARNINGS_UNACKNOWLEDGED)
            raise _reject(409, "STALE_VALIDATION", validation)

    observability.log_event(
        logging.INFO, "inventory_sync_started",
        slots=sorted(file_paths),
        warnings_acknowledged=bool(validation.has_warnings),
    )
    sync_started = time.perf_counter()
    settings = load_settings()
    try:
        summary = run_inventory_sync(
            file_paths,
            store_name=settings["store_name"],
            sync_date=settings["sync_date"],
            day_out_buckets=load_day_out_buckets(),
            incoming_missing_buckets=load_incoming_missing_buckets(),
            new_car_buckets=load_new_car_buckets(),
            internal_fleet_vins=load_internal_fleet_vins(),
            db_conn=conn,
            out_dir=OUT_DIR,
        )
    except Exception as exc:
        # Sprint 10 phase 25: a runtime failure AFTER validation passed
        # is reported in dealership language, never as a raw traceback.
        # Per-source transactional integrity is database/repository.py's
        # sync_run() contract: the failing source rolled back and is
        # marked failed; sources that completed before it kept their
        # results and say so in Recent Sync Runs.
        # Sprint 11: THE structured/Sentry moment for the sync engine --
        # an unexpected failure mid-sync is exactly what Rail F exists
        # to surface. Type name only in the log (exception messages can
        # carry report data); full stack goes to Sentry, which runs
        # with local variables disabled for the same reason.
        event_id = observability.capture_unexpected(exc)
        failure_fields = {
            "slots": sorted(file_paths),
            "duration_ms": round((time.perf_counter() - sync_started) * 1000, 1),
            "error_type": type(exc).__name__,
        }
        if event_id:
            failure_fields["sentry_event_id"] = event_id
        observability.log_event(logging.ERROR, "inventory_sync_failed", **failure_fields)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SYNC_EXECUTION_FAILED",
                "message": (
                    "The inventory sync failed while processing. Any source "
                    "that had already completed kept its results; the failing "
                    "source's changes were rolled back and its run is marked "
                    "failed. Check Recent Sync Runs for per-source status, "
                    "then run the sync again."
                ),
                "request_id": observability.current_request_id(),
            },
        )

    # Sprint 10 phases 13-14: record each accepted report's counts as
    # the next comparable-baseline row. Written only AFTER the sync
    # succeeded (a failed sync must not move the baseline), and keyed
    # by the run's own triggered_at so baseline rows correlate to
    # sync_run batches. One commit for all rows -- same
    # own-transaction convention as generate_install_tasks.
    from lotsync.database.repository import insert_report_baseline

    by_slot = {r.slot: r for r in validation.reports}
    for slot in file_paths:
        contract = SLOT_CONTRACTS[slot]
        report = by_slot[slot]
        insert_report_baseline(
            conn, vendor=contract.vendor, report_type=contract.report_type,
            slot=slot, total_rows=report.total_rows, valid_rows=report.valid_rows,
            sync_started_at=summary["triggered_at"],
        )
    conn.commit()

    # D4: "accepted" only after the sync succeeded AND its baselines
    # committed -- anything that fails before this line leaves the
    # batch unmarked (conservative 30-day window).
    upload_retention.record_outcome(batch_dir, upload_retention.OUTCOME_ACCEPTED)

    # Sprint 11 (phase 23): the request_id -> sync_run_id correlation
    # record. The browser operation, this log line, the SyncRun rows,
    # and any Sentry event now share ids without any schema change --
    # SyncRun's business meaning is untouched.
    observability.log_event(
        logging.INFO, "inventory_sync_completed",
        slots=sorted(file_paths),
        sync_run_ids=[r["sync_run_id"] for r in summary["sync_runs"]],
        vehicles_processed=summary["vehicles_processed"],
        exceptions_found=summary["exceptions_found"],
        tasks_generated=summary["tasks_generated"],
        recommendations_generated=summary["recommendations_generated"],
        pipeline_warnings=len(summary["warnings"]),
        duration_ms=round((time.perf_counter() - sync_started) * 1000, 1),
    )

    return summary


# Sprint 10 (Rail D): the pre-sync preview. Same role restriction as
# /run -- the preview exposes the same operational data the sync
# surface does, and it exists to serve that workflow. Performs NO
# operational mutation of any kind: no sync_run row, no event, no
# task, no recommendation, no report CSVs, no baseline write (it only
# READS baselines for comparison), and its uploaded files are deleted
# before the response returns.
@router.post("/validate", response_model=IngestionValidationDTO,
             dependencies=[Depends(require_roles(*SYNC_RUN_ROLES))])
async def validate_reports(
    tekion_unsold: Optional[UploadFile] = File(None),
    tekion_sold: Optional[UploadFile] = File(None),
    keyper: Optional[UploadFile] = File(None),
    mdd: Optional[UploadFile] = File(None),
    recovr: Optional[UploadFile] = File(None),
    rapidrecon: Optional[UploadFile] = File(None),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    uploads = {
        "tekion": tekion_unsold, "sold": tekion_sold, "keyper": keyper,
        "mdd": mdd, "recovr": recovr, "rapidrecon": rapidrecon,
    }
    provided = {source: upload for source, upload in uploads.items() if upload is not None}
    if not provided:
        raise HTTPException(status_code=422, detail=["At least one report file is required."])

    # D4 (DATA_RETENTION.md §3): same opportunistic sweep as /run --
    # this endpoint deletes its own uploads pre-response, but /run
    # batches and crash-orphaned validate-* directories age out here
    # too, so retention holds even if operators only ever preview.
    upload_retention.sweep(UPLOADS_DIR)

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    batch_dir = tempfile.mkdtemp(prefix="validate-", dir=UPLOADS_DIR)
    try:
        file_paths = await _save_uploads(provided, batch_dir)
        started = time.perf_counter()
        validation = validate_report_set(file_paths, db_conn=conn)
        _log_validation(validation, (time.perf_counter() - started) * 1000)
        return validation.to_dict()
    finally:
        shutil.rmtree(batch_dir, ignore_errors=True)


@router.get("/history", response_model=list[SyncRunBatchDTO])
def get_sync_history(limit: int = 20, conn: sqlite3.Connection = Depends(get_db)) -> list:
    return sync_run_history(conn, limit=limit)


@router.get("/exceptions", response_model=list[PendingIdentityDTO])
def get_exceptions(conn: sqlite3.Connection = Depends(get_db)) -> list:
    return list_pending_identities(conn)
