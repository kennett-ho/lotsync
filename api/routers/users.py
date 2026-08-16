"""
Sprint 09 -- dealership user administration (Rail A).

The smallest useful management surface over the Sprint 05 access
model: list the serving dealership's roster, invite/create a user,
deactivate, reactivate. Everything here obeys the hard authorization
rules from the sprint spec and AUTH_ARCHITECTURE.md:

- Server-side only: every endpoint requires an authenticated caller
  whose ACTIVE membership in the SERVING dealership carries a
  user-admin role. The serving dealership comes from the caller's own
  AccessContext (which api/auth.py derived from deployment config +
  membership) -- request bodies carry NO dealership and NO
  organization; a client cannot aim this surface at another store.
- Role policy is least-privilege and role-scoped:
      admin    -> may grant/administer: admin, manager, lot_staff,
                  sales_manager
      manager  -> may grant/administer: lot_staff, sales_manager only
  A manager can neither create/promote an admin or manager nor
  deactivate/reactivate one. (Whether managers should manage other
  managers is a flagged-open product question -- the smaller policy
  ships until the owner decides otherwise.)
- Nobody can administer THEIR OWN membership here (self-deactivation
  is a lockout footgun, self-role-change is escalation surface).
- The last active admin of the dealership cannot be deactivated.
- Membership state changes take effect on the target's NEXT request:
  authorization always re-reads the membership row (api/auth.py), so
  an existing, still-valid JWT stops working the moment its
  membership is deactivated. No token revocation is needed for
  dealership offboarding -- and none is pretended.
- Supabase Auth account deletion/banning is deliberately NOT part of
  v1.1 offboarding (assessed in ACCOUNT_LIFECYCLE.md): membership
  deactivation fully revokes dealership access while preserving both
  history and the person's identity.

Under AUTH_MODE=disabled every route here answers 404 -- an
unauthenticated deployment (production today) exposes no
user-administration surface, indistinguishable from the routes not
existing.
"""

import os
import re
from typing import Optional

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lotsync.api import supabase_admin
from lotsync.api.auth import AccessContext, get_access_context, require_roles
from lotsync.api.dependencies import get_db
from lotsync.database.repository import (
    count_active_admins, get_membership_any_state,
    list_memberships_for_dealership, set_membership_active,
    upsert_user_membership,
)

router = APIRouter(prefix="/users", tags=["users"])

USER_ADMIN_ROLES = ("admin", "manager")

# Which roles each administrator role may grant AND administer
# (deactivate/reactivate). Absence means 403.
GRANTABLE = {
    "admin": ("admin", "manager", "lot_staff", "sales_manager"),
    "manager": ("lot_staff", "sales_manager"),
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InviteRequest(BaseModel):
    email: str
    role: str
    # Deliberately NO dealership_id / organization_id fields: pydantic
    # ignores unknown keys, so a client supplying them changes nothing
    # (proven by test) -- the server derives both from the caller.


def _require_admin_context(
    context: Optional[AccessContext] = Depends(get_access_context),
) -> AccessContext:
    from lotsync.api.auth import auth_mode

    if auth_mode() == "disabled":
        # Production posture: an unauthenticated deployment must not
        # expose a user-administration surface AT ALL -- these routes
        # answer 404 there, indistinguishable from not existing. (The
        # router stays mounted so the test suite can exercise both
        # postures through the same app instance.)
        raise HTTPException(status_code=404, detail="Not found")
    if context is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return context


def _grantable_for(context: AccessContext) -> tuple:
    return GRANTABLE.get(context.role, ())


def _invite_redirect() -> str:
    frontend = os.environ.get("DEALERDOH_FRONTEND_URL", "").strip().rstrip("/")
    return f"{frontend}/auth/reset-password" if frontend else ""


def _membership_dto(membership: dict, user: Optional[dict]) -> dict:
    return {
        "auth_user_id": membership["auth_user_id"],
        "email": (user or {}).get("email"),
        "display_name": (user or {}).get("display_name"),
        "role": membership["role"],
        "active": bool(membership["active"]),
        # "invited" = has never completed a sign-in/confirmation;
        # UI shows a pending badge. Unknown when the identity provider
        # is unreachable -- the roster still renders from memberships.
        "account_state": (
            "unknown" if user is None
            else ("active" if user.get("confirmed") else "invited")
        ),
    }


@router.get("", dependencies=[Depends(require_roles(*USER_ADMIN_ROLES))])
def list_users(
    context: AccessContext = Depends(_require_admin_context),
    conn: sqlite3.Connection = Depends(get_db),
) -> list:
    memberships = list_memberships_for_dealership(conn, context.dealership_id)
    out = []
    for membership in memberships:
        user = supabase_admin.get_user(membership["auth_user_id"]) \
            if supabase_admin.is_configured() else None
        out.append(_membership_dto(membership, user))
    return out


@router.post("/invite", dependencies=[Depends(require_roles(*USER_ADMIN_ROLES))])
def invite_user(
    body: InviteRequest,
    context: AccessContext = Depends(_require_admin_context),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    email = body.email.strip().lower()
    role = body.role.strip().lower()

    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if role not in GRANTABLE["admin"]:
        # Unknown role: rejected regardless of caller privileges.
        raise HTTPException(status_code=422, detail="Unknown role")
    if role not in _grantable_for(context):
        raise HTTPException(
            status_code=403,
            detail="Your role does not permit assigning that role",
        )
    if not supabase_admin.is_configured():
        raise supabase_admin.SupabaseAdminUnavailable()

    existing = supabase_admin.find_user_by_email(email)

    if existing is not None:
        membership = get_membership_any_state(
            conn, existing["auth_user_id"], context.dealership_id)
        if membership is not None:
            if membership["active"]:
                # Idempotent-safe: repeat submissions neither re-invite
                # nor duplicate rows.
                raise HTTPException(
                    status_code=409,
                    detail="That person is already a member of this dealership",
                )
            raise HTTPException(
                status_code=409,
                detail="That person has a deactivated membership -- "
                       "use Reactivate instead of a new invite",
            )
        user = existing  # Existing Auth identity, new membership below.
    else:
        # New identity: GoTrue's invite flow creates the user and sends
        # the invite email whose action link lands on our
        # /auth/reset-password page for first-password setup.
        user = supabase_admin.invite_user(email, _invite_redirect())

    upsert_user_membership(
        conn, user["auth_user_id"], context.organization_id,
        context.dealership_id, role, active=1,
    )
    conn.commit()

    membership = get_membership_any_state(
        conn, user["auth_user_id"], context.dealership_id)
    return _membership_dto(membership, user)


def _administer_target(
    context: AccessContext,
    conn: sqlite3.Connection,
    auth_user_id: str,
) -> dict:
    """Shared guards for deactivate/reactivate."""
    if auth_user_id == context.auth_user_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot change your own membership",
        )
    membership = get_membership_any_state(conn, auth_user_id,
                                          context.dealership_id)
    if membership is None:
        # Covers both "no such user" and "member of a different store"
        # identically -- this surface never confirms other stores'
        # membership existence.
        raise HTTPException(status_code=404, detail="No such membership")
    if membership["role"] not in _grantable_for(context):
        raise HTTPException(
            status_code=403,
            detail="Your role does not permit administering that member",
        )
    return membership


@router.post("/{auth_user_id}/deactivate",
             dependencies=[Depends(require_roles(*USER_ADMIN_ROLES))])
def deactivate_user(
    auth_user_id: str,
    context: AccessContext = Depends(_require_admin_context),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    membership = _administer_target(context, conn, auth_user_id)
    if membership["role"] == "admin" and \
            count_active_admins(conn, context.dealership_id) <= 1:
        raise HTTPException(
            status_code=409,
            detail="Cannot deactivate the last active admin",
        )
    set_membership_active(conn, auth_user_id, context.dealership_id, False)
    conn.commit()
    membership = get_membership_any_state(conn, auth_user_id,
                                          context.dealership_id)
    user = supabase_admin.get_user(auth_user_id) \
        if supabase_admin.is_configured() else None
    return _membership_dto(membership, user)


@router.post("/{auth_user_id}/reactivate",
             dependencies=[Depends(require_roles(*USER_ADMIN_ROLES))])
def reactivate_user(
    auth_user_id: str,
    context: AccessContext = Depends(_require_admin_context),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    _administer_target(context, conn, auth_user_id)
    set_membership_active(conn, auth_user_id, context.dealership_id, True)
    conn.commit()
    membership = get_membership_any_state(conn, auth_user_id,
                                          context.dealership_id)
    user = supabase_admin.get_user(auth_user_id) \
        if supabase_admin.is_configured() else None
    return _membership_dto(membership, user)
