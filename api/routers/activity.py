"""GET /activity -- API_CONTRACTS.md's ActivityDTO list, the global Activity screen. See queries/dashboard.py's recent_activity_feed."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends

from lotsync.api.dependencies import get_db
from lotsync.api.dtos import ActivityDTO
from lotsync.queries.dashboard import recent_activity_feed

router = APIRouter()


@router.get("/activity", response_model=list[ActivityDTO])
def get_activity(
    vin: Optional[str] = None,
    limit: int = 20,
    conn: sqlite3.Connection = Depends(get_db),
) -> list:
    return recent_activity_feed(conn, limit=limit, vin=vin)
