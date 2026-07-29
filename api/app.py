"""
Phase 3, Sprint 2 -- the FastAPI application. This is the first web
framework dependency this project has ever added; ARCHITECTURE.md
anticipated exactly this moment ("a FastAPI layer would import from
sync/ and rules/ the same way main.py does now") and PRODUCT.md already
named FastAPI as the Phase 3 tech choice, so introducing it here isn't
a new architectural decision, just this sprint's execution of an
already-made one.

Run locally (see api/README.md for the full command):
    uvicorn lotsync.api.app:app --reload

Read-only through Sprint 3; still no authentication. Sprint 4 adds this
project's first write route, POST /inventory-sync/run (see
api/routers/inventory_sync.py) -- everything else stays read-only. See
PHASE_3_SPRINT_2_REVIEW.md / PHASE_3_SPRINT_4_REVIEW.md for scope and
reasoning.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lotsync.api.routers import activity, dashboard, inventory_sync, recommendations, reports, tasks, vehicles

app = FastAPI(
    title="LotSync API",
    description="See API_CONTRACTS.md for the DTOs this serves.",
    version="0.2.0",
)

# Phase 3, Sprint 3 -- the frontend (Vite dev server, a different origin)
# calls this API directly from the browser for the first time. Not a
# contract change (no route, DTO, or business logic here) -- purely the
# transport-level plumbing a cross-origin browser call requires, same
# category as Sprint 2's check_same_thread=False fix. Origins are read
# from LOTSYNC_CORS_ORIGINS (comma-separated) so this stays a local-dev
# convenience, not a hardcoded assumption about where the frontend runs.
_cors_origins = os.environ.get(
    "LOTSYNC_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8443,http://127.0.0.1:8443",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(vehicles.router)
app.include_router(tasks.router)
app.include_router(recommendations.router)
app.include_router(activity.router)
app.include_router(reports.router)
app.include_router(inventory_sync.router)
