"""
Phase 3, Sprint 4 -- the Inventory Sync page's backend surface.

POST /inventory-sync/run is the one write endpoint this sprint adds
(everything else built through Sprint 3 was read-only). It's
deliberately synchronous and single-request per PHASE_3_SPRINT_4's own
plan: given real, employee-scale upload volume and Slice 7's already-
validated sub-second reconciliation performance, a background job queue
would be infrastructure ahead of real need (PRODUCT.md's standing rule).
This router's own job is narrow -- parse the six optional upload slots,
save them, validate them, and hand a plain dict of file paths to
sync/pipeline.run_inventory_sync, which is where the actual
orchestration lives. No reconciliation logic here.
"""

import datetime
import os
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from lotsync.api.dependencies import get_db
from lotsync.api.dtos import PendingIdentityDTO, SyncRunBatchDTO, SyncSummaryDTO
from lotsync.config.settings import (
    load_settings, load_day_out_buckets, load_incoming_missing_buckets,
    load_new_car_buckets, load_internal_fleet_vins,
)
from lotsync.queries.inventory_sync import list_pending_identities, sync_run_history
from lotsync.sync.pipeline import run_inventory_sync
from lotsync.sync.upload_validation import validate_upload

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


@router.post("/run", response_model=SyncSummaryDTO)
async def run_sync(
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

    batch_dir = os.path.join(UPLOADS_DIR, datetime.datetime.now().strftime("%Y%m%dT%H%M%S%f"))
    os.makedirs(batch_dir, exist_ok=True)

    file_paths = {}
    for source, upload in provided.items():
        dest = os.path.join(batch_dir, upload.filename or f"{source}.csv")
        with open(dest, "wb") as f:
            f.write(await upload.read())
        file_paths[source] = dest

    # Validate every provided file before persisting anything -- a bad
    # file in one slot fails the whole request with a specific reason
    # per slot, rather than a partial sync or a downstream KeyError.
    problems = []
    for source, path in file_paths.items():
        problems.extend(validate_upload(source, path))
    if problems:
        raise HTTPException(status_code=422, detail=problems)

    settings = load_settings()
    return run_inventory_sync(
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


@router.get("/history", response_model=list[SyncRunBatchDTO])
def get_sync_history(limit: int = 20, conn: sqlite3.Connection = Depends(get_db)) -> list:
    return sync_run_history(conn, limit=limit)


@router.get("/exceptions", response_model=list[PendingIdentityDTO])
def get_exceptions(conn: sqlite3.Connection = Depends(get_db)) -> list:
    return list_pending_identities(conn)
