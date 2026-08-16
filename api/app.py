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
import sqlite3
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lotsync.api.auth import AccessContext, auth_mode, get_access_context
from lotsync.api.dependencies import get_db
from lotsync.api.routers import activity, dashboard, inventory_sync, recommendations, reports, tasks, vehicles

app = FastAPI(
    title="LotSync API",
    description="See API_CONTRACTS.md for the DTOs this serves.",
    version="0.2.0",
)


# Deployment health check (Render's health check path, and a quick
# post-deploy sanity check -- see DEPLOYMENT.md). Goes through the same
# get_db()/connect() path every real route uses, so a DB the app can't
# reach or write to (e.g. a misconfigured/unmounted persistent disk)
# fails this too, not just a bare "process is running" check.
@app.get("/health")
def health(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    conn.execute("SELECT 1")
    # Sprint 02 (DealerDOH dev environment): deployments identify
    # themselves via the ENVIRONMENT env var (the dev Render service
    # sets ENVIRONMENT=development) so an operator hitting /health can
    # always tell which environment answered. Deployments that predate
    # this variable (current production) report "unspecified" rather
    # than guessing.
    # Sprint 03: database_engine says which persistence engine served
    # this response (the SELECT 1 above went through it, so "ok" +
    # engine name is real connectivity evidence, not configuration
    # echo). Never includes DSN/host/credential material.
    from lotsync.database.engine import get_engine

    return {
        "status": "ok",
        "environment": os.environ.get("ENVIRONMENT", "unspecified"),
        "database_engine": get_engine(),
    }

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

# Sprint 05: who the verified caller is, per the access model -- the
# frontend's identity chip reads this instead of trusting anything
# client-side. Under AUTH_MODE=disabled it reports that plainly (the
# production posture: an unauthenticated beta), rather than inventing
# an identity.
@app.get("/me")
def me(context: Optional[AccessContext] = Depends(get_access_context)) -> dict:
    if context is None:
        return {"authenticated": False, "auth_mode": auth_mode()}
    return {
        "authenticated": True,
        "auth_mode": "required",
        "email": context.email,
        "role": context.role,
        "organization": {"id": context.organization_id, "name": context.organization_name},
        "dealership": {"id": context.dealership_id, "name": context.dealership_name},
    }


# Sprint 05: every operational router requires an authenticated,
# membership-backed caller when AUTH_MODE=required (see api/auth.py --
# under the default AUTH_MODE=disabled the dependency is inert and
# these routes behave exactly as before this sprint). Applied at
# include time so a future router added here inherits protection by
# default instead of shipping accidentally public. /health (above) is
# the ONE deliberately public endpoint -- Render's health checking
# depends on it and it exposes no dealership data. /me carries the
# same dependency inline, so in required mode it 401s/403s exactly
# like an operational route; only under AUTH_MODE=disabled does it
# report the unauthenticated posture plainly.
_OPERATIONAL_ROUTERS = (
    dashboard.router, vehicles.router, tasks.router, recommendations.router,
    activity.router, reports.router, inventory_sync.router,
)
for _router in _OPERATIONAL_ROUTERS:
    app.include_router(_router, dependencies=[Depends(get_access_context)])
