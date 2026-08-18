"""
Sprint 11 -- the DEV-only Sentry verification trigger.

Rail F's evidence requires a REAL captured backend exception from the
deployed DEV stack, and the sprint brief forbids a permanent public
crash endpoint. This is the reconciliation: a deliberately raising
route that is DOUBLE-gated --

1. Environment gate: outside ENVIRONMENT=development the route
   answers 404 before doing anything -- on today's production posture
   (ENVIRONMENT unset) and any future production deployment it simply
   does not exist as a surface.
2. Authorization gate: same admin/manager restriction as the sync
   surface (and the include-time auth dependency in api/app.py) --
   in required mode an unauthenticated or under-privileged caller
   gets 401/403 from the dependency layer before the handler runs.

POST (never GET) so crawlers/prefetchers can't trip it. The raised
error is a distinctive type so a captured event is unambiguous in
Sentry and in the http_request record's error_type. Pinned by tests
in tests/test_observability.py (404 outside development; capture path
inside it) -- and documented in OBSERVABILITY.md's troubleshooting
section as THE sanctioned way to verify Sentry backend delivery.
"""

import os

from fastapi import APIRouter, Depends, HTTPException

from lotsync.api.auth import SYNC_RUN_ROLES, require_roles

router = APIRouter(prefix="/_observability", tags=["observability"])


class ObservabilityVerificationError(RuntimeError):
    """Deliberately raised by the DEV verification trigger."""


@router.post("/raise-test-error",
             dependencies=[Depends(require_roles(*SYNC_RUN_ROLES))])
def raise_test_error() -> dict:
    if os.environ.get("ENVIRONMENT", "").strip().lower() != "development":
        raise HTTPException(status_code=404, detail="Not Found")
    raise ObservabilityVerificationError(
        "dealerdoh-observability-verification (deliberate DEV test error)"
    )
