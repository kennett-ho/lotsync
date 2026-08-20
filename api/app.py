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

import logging
import os
import sqlite3
import time
import uuid
from typing import Optional

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lotsync.api import observability
from lotsync.api.auth import AccessContext, auth_mode, get_access_context
from lotsync.api.dependencies import get_db
from lotsync.api.routers import (
    activity, dashboard, inventory_sync, recommendations,
    reports, tasks, users, vehicles,
)

# Sprint 13 (Rail H): interactive API documentation is a deliberate,
# environment-gated decision, not security-through-obscurity. The
# OpenAPI schema and the Swagger/ReDoc explorers map every route and
# DTO -- useful for integration in DEV, unnecessary attack-surface on a
# production deployment that serves real dealership data. They stay ON
# for development/local (integration convenience) and are turned OFF
# only when a deployment explicitly identifies itself as production via
# ENVIRONMENT=production. Current production predates this variable and
# reports "unspecified", so this changes nothing there (the production
# baseline is untouched); a future production release train that sets
# ENVIRONMENT=production inherits the reduced surface automatically.
_DOCS_ENABLED = observability.observability_environment() != "production"

app = FastAPI(
    title="LotSync API",
    description="See API_CONTRACTS.md for the DTOs this serves.",
    version="0.2.0",
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
)

# Sprint 13 (Rail H): security response headers for the JSON API. These
# are the headers that matter for a Bearer-token JSON API that sets no
# cookies and renders no HTML of its own:
#   - nosniff: never let a browser MIME-sniff a JSON body into script.
#   - DENY framing (header + CSP frame-ancestors): the API is data, not
#     a page; it must never be embedded. Deliberately NOT a full
#     script/style CSP -- that would break the Swagger UI (/docs loads
#     its assets from a CDN) for no gain on non-executable JSON.
#   - no-referrer: an API response should never leak a referrer.
#   - no-store: authenticated dealership data must not be cached by the
#     browser, shared proxies, or CDNs (Phase 24). Health is tiny and
#     safe to include; it is never sensitive.
# The frontend's own richer CSP lives in frontend/vercel.json.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

# Sprint 11 (Rails F+G): structured logging is always on (JSON records
# on the "dealerdoh" logger -- see api/observability.py); Sentry
# initializes only when SENTRY_DSN is present and is a silent no-op
# otherwise. Neither can fail app startup.
observability.configure_logging()
observability.init_backend_sentry()


# Sprint 11: request correlation + the one place unexpected failures
# become responses. Registered BEFORE the CORS middleware below so
# CORS wraps it (later add_middleware = outer layer) and even this
# handler's 500s carry CORS headers a browser may read.
#
# Every request gets a SERVER-generated id (client input is never the
# authority), a structured "http_request" record with the ROUTE
# TEMPLATE (never the raw path -- /vehicles/{vin} carries a real VIN
# raw), and the X-Request-ID response header. An exception escaping
# the routers is captured to Sentry (when enabled), logged with type
# name only (exception MESSAGES can carry report data), and answered
# with a generic 500 that includes the request id as a support
# reference -- no traceback, no internals. Expected HTTPExceptions
# (401/403/404/409/422) are turned into responses by FastAPI before
# reaching this except path, so they are never Sentry material.
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    rid = uuid.uuid4().hex
    rid_token = observability.request_id_var.set(rid)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        route = request.scope.get("route")
        observability.log_event(
            logging.ERROR if response.status_code >= 500 else logging.INFO,
            "http_request",
            route=route.path if route is not None else "(unmatched)",
            method=request.method,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
            **observability.auth_log_context(request),
        )
        response.headers[observability.REQUEST_ID_HEADER] = rid
        # Sprint 13 (Rail H): stamp security headers on every response
        # the app produces. setdefault so a route that deliberately sets
        # its own value (e.g. a future cacheable public asset) wins.
        for _name, _value in _SECURITY_HEADERS.items():
            response.headers.setdefault(_name, _value)
        return response
    except Exception as exc:
        route = request.scope.get("route")
        event_id = observability.capture_unexpected(exc)
        fields = {
            "route": route.path if route is not None else "(unmatched)",
            "method": request.method,
            "status_code": 500,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "error_type": type(exc).__name__,
            **observability.auth_log_context(request),
        }
        if event_id:
            fields["sentry_event_id"] = event_id
        observability.log_event(logging.ERROR, "http_request", **fields)
        # Sprint 13 (Rail H): the generic 500 carries the same security
        # headers as every other response (this handler owns the 500
        # path inside CORS, so nothing else would add them here).
        return JSONResponse(
            status_code=500,
            content={"detail": {
                "code": "INTERNAL_ERROR",
                "message": "DealerDOH hit an unexpected internal error. "
                           "Share the reference below if this keeps happening.",
                "request_id": rid,
            }},
            headers={observability.REQUEST_ID_HEADER: rid, **_SECURITY_HEADERS},
        )
    finally:
        observability.request_id_var.reset(rid_token)


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
        # Sprint 11: the deployed code's identity (git SHA via
        # DEALERDOH_RELEASE/RENDER_GIT_COMMIT -- see
        # api/observability.py). Non-secret by definition; no host,
        # DSN, or provider configuration is ever exposed here.
        "release": observability.observability_release(),
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
    # Sprint 11: without this the BROWSER cannot read the request id
    # from cross-origin responses (found live in the deployed DEV
    # verification -- the header was set but invisible to fetch), and
    # ApiError.requestId would silently stay empty. Response headers
    # other than the CORS-safelisted ones must be exposed explicitly.
    expose_headers=[observability.REQUEST_ID_HEADER],
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
        # Sprint 11: the stable internal Supabase user UUID -- the
        # frontend's analytics identity (deliberately the internal id,
        # never email/display name; see OBSERVABILITY.md).
        "auth_user_id": context.auth_user_id,
        "email": context.email,
        # Sprint 09: the display name travels in the verified token's
        # user_metadata (Supabase Auth owns profile identity -- see
        # ACCOUNT_LIFECYCLE.md's display-name decision). Null until the
        # person sets one in Settings.
        "display_name": context.display_name,
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
    # Sprint 09: user administration. Same include-time protection;
    # additionally answers 404 in disabled mode (see routers/users.py)
    # so the unauthenticated production posture exposes no user-admin
    # surface at all.
    users.router,
)
for _router in _OPERATIONAL_ROUTERS:
    app.include_router(_router, dependencies=[Depends(get_access_context)])
