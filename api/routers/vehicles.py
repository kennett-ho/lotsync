"""
GET /vehicles -- API_CONTRACTS.md's VehicleDTO list (Vehicles List
screen).
GET /vehicles/{vin} -- VehicleDetailDTO, this sprint's named reference
implementation for how a detail page is assembled. All the actual
aggregation (Tasks + Recommendations + Timeline + Connected Systems,
without duplicating any of those four queries) already happened in
queries/vehicles.py's get_vehicle_detail -- this router's only added
responsibility is the 404 for an unknown vin, and stripping the
redundant nested `vehicle` field from each Task/Recommendation/Activity
entry before handing the whole thing to VehicleDetailDTO (per
API_CONTRACTS.md's documented reasoning: redundant with the Vehicle
this response is already about).
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from lotsync.api.dependencies import get_db
from lotsync.api.dtos import VehicleDTO, VehicleDetailDTO
from lotsync.queries.vehicles import list_vehicles, get_vehicle_detail

router = APIRouter()


def _without_vehicle(row: dict) -> dict:
    return {**row, "vehicle": None}


@router.get("/vehicles", response_model=list[VehicleDTO])
def get_vehicles(conn: sqlite3.Connection = Depends(get_db)) -> list:
    return list_vehicles(conn)


@router.get("/vehicles/{vin}", response_model=VehicleDetailDTO)
def get_vehicle(vin: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    detail = get_vehicle_detail(conn, vin)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No vehicle with vin={vin!r}")

    return {
        **detail,
        "tasks": [_without_vehicle(t) for t in detail["tasks"]],
        "recommendations": [_without_vehicle(r) for r in detail["recommendations"]],
        "timeline": [_without_vehicle(e) for e in detail["timeline"]],
    }
