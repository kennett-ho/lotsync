"""GET /recommendations -- API_CONTRACTS.md's RecommendationDTO list. See queries/recommendations.py's list_recommendations."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends

from lotsync.api.dependencies import get_db
from lotsync.api.dtos import RecommendationDTO
from lotsync.queries.recommendations import list_recommendations

router = APIRouter()


@router.get("/recommendations", response_model=list[RecommendationDTO])
def get_recommendations(
    status: Optional[str] = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> list:
    return list_recommendations(conn, status=status)
