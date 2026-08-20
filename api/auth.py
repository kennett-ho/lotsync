"""
Sprint 05 -- the authentication and authorization boundary.

Identity provider: Supabase Auth (email/password, dev only). This
module never sees a password and never stores a token -- it verifies
the SIGNATURE of the Supabase-issued access token (JWT) on every
request, then resolves the verified user against the DealerDOH access
model (user_membership -> role + dealership). See
AUTH_ARCHITECTURE.md for the full design.

Three security invariants, enforced here and nowhere else:

1. **The frontend is never the boundary.** A request is authorized by
   token signature + membership row, regardless of anything the UI
   claims. Role and dealership come from the membership row ONLY --
   token metadata, query params, and request bodies are never
   consulted for either, so they cannot be spoofed.
2. **The serving dealership is the deployment's own configuration**
   (DEALERDOH_DEALERSHIP_ID), never client input. A caller either
   holds an active membership in exactly that dealership or gets 403.
   (Business rows don't carry per-row store scoping yet -- see
   AUTH_ARCHITECTURE.md's "Before a second store" section for the
   mandatory follow-up this deliberately does not fake.)
3. **Nothing secret is ever logged or echoed**: no Authorization
   header contents, no token claims in error bodies, generic 401
   messages only.

AUTH_MODE selects the posture (read per-request, matching this
repo's env-driven-behavior convention):

- "disabled" (default): every route behaves exactly as before this
  sprint -- the production path. Production LotSync is a deliberately
  unauthenticated beta (see PRODUCTION_BASELINE.md); its deployment
  sets nothing and this module stays inert there.
- "required": operational routes demand a valid Bearer token AND an
  active membership. The DealerDOH DEV deployment runs this.

Verification mechanics: the dealerdoh-dev Supabase project signs with
an asymmetric ECC P-256 key (ES256) -- verified against the project's
public JWKS. The JWKS source is either SUPABASE_URL (deployed; fetched
+ cached from /auth/v1/.well-known/jwks.json) or AUTH_JWKS (inline
JSON -- how the test suite injects its own ephemeral keypair so CI
never depends on live Supabase). The accepted-algorithm list is
pinned to ES256: a token claiming any other alg -- including HS256
against the retired legacy secret, or "none" -- fails closed.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request

from lotsync.api import observability
from lotsync.api.dependencies import get_db
from lotsync.database.repository import get_active_membership

_ALLOWED_ALGORITHMS = ["ES256"]
_ROLES_ALL = ("admin", "manager", "lot_staff", "sales_manager")

# Sprint 13 (Rail H, finding F4): display_name is self-set by the user
# via Supabase `updateUser` and rides the verified token's
# user_metadata. It is NEVER authoritative for authorization (role and
# store come from the membership row only), but it IS rendered in the
# UI and the admin roster -- so an unbounded or control-character-laden
# value is a UI-spoofing vector (e.g. a very long name, or newlines
# breaking a roster row). The token's signature is still trusted; this
# only bounds the ONE free-text profile field the provider lets a user
# set, at the point it crosses into DealerDOH.
_MAX_DISPLAY_NAME = 100


def clamp_display_name(value) -> Optional[str]:
    """Bound and sanitize a self-set display_name from user_metadata.
    Non-strings and blanks -> None; strips control characters (keeping
    normal spaces) and truncates to _MAX_DISPLAY_NAME characters."""
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if ch >= " " or ch == "\t").strip()
    if not cleaned:
        return None
    return cleaned[:_MAX_DISPLAY_NAME]

# Roles allowed to trigger an inventory sync run (the one mutating
# operational endpoint). Grounded in the Sprint 05 role definitions:
# Manager explicitly "may run inventory sync"; lot staff and sales
# manager definitions don't include it. Every other current endpoint
# is shared dealership data -- readable by any active member -- per
# the same spec's "avoid inventing manager-only restrictions."
SYNC_RUN_ROLES = ("admin", "manager")


def auth_mode() -> str:
    mode = os.environ.get("AUTH_MODE", "disabled").strip().lower()
    if mode not in ("disabled", "required"):
        raise HTTPException(
            status_code=500,
            detail=f"AUTH_MODE must be 'disabled' or 'required', got {mode!r}",
        )
    return mode


def _serving_dealership_id() -> str:
    # The deployment's own store identity -- invariant #2. Defaults to
    # the QA dealership dev_seed always creates.
    return os.environ.get("DEALERDOH_DEALERSHIP_ID", "qa-motors").strip()


def _expected_issuer() -> str:
    issuer = os.environ.get("AUTH_JWT_ISSUER", "").strip()
    if issuer:
        return issuer
    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    if supabase_url:
        return f"{supabase_url}/auth/v1"
    raise HTTPException(
        status_code=500,
        detail="Authentication is misconfigured: AUTH_MODE=required needs "
               "SUPABASE_URL or AUTH_JWT_ISSUER",
    )


def _expected_audience() -> str:
    return os.environ.get("AUTH_JWT_AUDIENCE", "authenticated").strip()


# PyJWKClient instances cache fetched keys internally; keyed by URL so
# a long-lived process fetches the JWKS once per lifespan, not per
# request.
_jwks_clients: dict = {}


def _signing_key_for(token: str):
    """
    Resolve the public key that should verify this token, by `kid`.
    AUTH_JWKS (inline JWKS JSON) wins when set -- the test suite's
    injection point; otherwise the Supabase project's public JWKS
    endpoint derived from SUPABASE_URL.
    """
    inline = os.environ.get("AUTH_JWKS", "").strip()
    if inline:
        try:
            keys = json.loads(inline).get("keys", [])
            kid = jwt.get_unverified_header(token).get("kid")
        except (ValueError, jwt.PyJWTError):
            raise _unauthorized()
        for entry in keys:
            if entry.get("kid") == kid:
                return jwt.PyJWK(entry).key
        raise _unauthorized()

    supabase_url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    if not supabase_url:
        raise HTTPException(
            status_code=500,
            detail="Authentication is misconfigured: AUTH_MODE=required needs "
                   "SUPABASE_URL or AUTH_JWKS",
        )
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = jwt.PyJWKClient(jwks_url, cache_keys=True)
        _jwks_clients[jwks_url] = client
    try:
        return client.get_signing_key_from_jwt(token).key
    except jwt.exceptions.PyJWKClientConnectionError as exc:
        # Sprint 11 (phase 21): the Auth PROVIDER being unreachable is
        # an infrastructure failure, not a credential failure -- the
        # caller still gets the same non-leaking 401 (behavior
        # unchanged), but telemetry must distinguish the two. Never
        # logs the token; type name only.
        observability.log_event(
            logging.ERROR, "auth_infrastructure_failure",
            reason="jwks_unreachable", error_type=type(exc).__name__,
        )
        raise _unauthorized()
    except jwt.PyJWTError:
        # Ordinary credential/kid failures: expected, quiet -- the
        # request record's 401 is the trace (phase 21: normal
        # credential failure creates neither log spam nor Sentry
        # incidents).
        raise _unauthorized()


def _unauthorized() -> HTTPException:
    # One generic message for every verification failure -- which
    # check failed is not information an unauthenticated caller gets.
    # Never include token material.
    return HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_token(token: str) -> dict:
    """Signature + iss/aud/exp verification. Returns claims or raises 401."""
    key = _signing_key_for(token)
    try:
        return jwt.decode(
            token,
            key,
            algorithms=_ALLOWED_ALGORITHMS,
            audience=_expected_audience(),
            issuer=_expected_issuer(),
            options={"require": ["exp", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError:
        raise _unauthorized()


@dataclass(frozen=True)
class AccessContext:
    """
    The typed current-user context routes receive. Everything here is
    server-derived: auth_user_id/email from the VERIFIED token, role
    and organization/dealership from the membership row.
    """
    auth_user_id: str
    email: Optional[str]
    role: str
    organization_id: str
    organization_name: str
    dealership_id: str
    dealership_name: str
    # Sprint 09: from the verified token's user_metadata (Supabase Auth
    # owns profile identity; the person sets it in Settings). Optional
    # -- older tokens and users without one simply carry None.
    display_name: Optional[str] = None


def get_access_context(request: Request, conn=Depends(get_db)) -> Optional[AccessContext]:
    """
    The router-level dependency protecting every operational route.
    AUTH_MODE=disabled -> None (pre-Sprint-05 behavior, the production
    path). AUTH_MODE=required -> a verified, membership-backed
    AccessContext, or 401/403.
    """
    if auth_mode() == "disabled":
        return None

    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized()

    claims = verify_token(token.strip())
    auth_user_id = str(claims.get("sub", "")).strip()
    if not auth_user_id:
        raise _unauthorized()

    membership = get_active_membership(conn, auth_user_id, _serving_dealership_id())
    if membership is None:
        # Authenticated but not authorized for THIS dealership's data
        # -- covers "no membership anywhere," "membership only in a
        # different store," and "membership deactivated" identically.
        # Sprint 11: WARNING (an expected denial, operationally worth
        # seeing -- offboarded users still holding valid tokens land
        # here), never a Sentry event. auth_user_id is a stable
        # internal id, safe by the observability vocabulary.
        observability.log_event(
            logging.WARNING, "auth_denied",
            reason="no_active_membership", auth_user_id=auth_user_id,
        )
        raise HTTPException(
            status_code=403,
            detail="No active membership for this dealership",
        )
    if membership["role"] not in _ROLES_ALL:
        # Unreachable while the schema CHECK holds; fail closed anyway
        # rather than authorize an unknown role.
        raise HTTPException(status_code=403, detail="Membership role not recognized")

    # Sprint 11: publish the safe id-only context (on request.state --
    # see observability.py for why not a contextvar) so the finished
    # http_request record carries who/where. Stable internal ids only
    # -- email and display name are deliberately NOT part of the
    # logging context.
    observability.set_auth_log_context(
        request,
        auth_user_id=auth_user_id, role=membership["role"],
        organization_id=membership["organization_id"],
        dealership_id=membership["dealership_id"],
    )

    metadata = claims.get("user_metadata") or {}
    return AccessContext(
        auth_user_id=auth_user_id,
        email=claims.get("email"),
        role=membership["role"],
        organization_id=membership["organization_id"],
        organization_name=membership["organization_name"],
        dealership_id=membership["dealership_id"],
        dealership_name=membership["dealership_name"],
        display_name=clamp_display_name(metadata.get("display_name")),
    )


def require_roles(*roles: str):
    """
    Route-level role gate, layered on top of get_access_context (which
    FastAPI caches per-request, so the token/membership work runs
    once). In disabled mode the context is None and the gate is inert,
    same as everything else.
    """
    def _dependency(context: Optional[AccessContext] = Depends(get_access_context)) -> None:
        if context is not None and context.role not in roles:
            # Sprint 11: expected authorization denial -- WARNING with
            # explicit safe ids (this sync dependency runs in its own
            # threadpool context, so nothing implicit carries here),
            # never a Sentry event.
            observability.log_event(
                logging.WARNING, "auth_denied", reason="role_not_permitted",
                auth_user_id=context.auth_user_id, role=context.role,
                dealership_id=context.dealership_id,
            )
            raise HTTPException(
                status_code=403,
                detail="Your role does not permit this action",
            )
    return _dependency
