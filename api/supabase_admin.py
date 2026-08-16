"""
Sprint 09 -- the server-only Supabase Auth admin boundary.

The user-management endpoints (api/routers/users.py) need a privileged
Supabase capability: look up Auth users, and invite new ones. That
capability is the GoTrue Admin API, authenticated with the project's
service key -- a SERVER-SIDE SECRET with the same handling rules as
DATABASE_URL:

- lives ONLY in the deployment's environment (Render secret env:
  SUPABASE_SECRET_KEY) and the operator's password manager
- never a VITE_* variable, never delivered to a browser, never
  committed, never logged, never echoed in a response or error body
- absent entirely from deployments that don't manage users
  (production today runs AUTH_MODE=disabled and never loads this)

This module is the ONLY place the key is read. Everything above it
(routes) sees plain dicts with the few fields the roster actually
needs. tools/provision_dev_auth.py established the raw-urllib admin
pattern this module follows; tests replace these functions at the
module boundary (unittest.mock.patch) so CI never needs a live
Supabase or a real key.

GoTrue admin surface used (deliberately minimal -- no generic
passthrough):
  GET  /auth/v1/admin/users?email=...   find a user by email
  GET  /auth/v1/admin/users/{id}        fetch one user
  POST /auth/v1/invite                  invite (sends the invite email)
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import HTTPException


class SupabaseAdminUnavailable(HTTPException):
    """Raised when the admin capability is not configured or the
    provider call failed -- as a 503, never leaking configuration
    detail beyond the generic message."""

    def __init__(self):
        super().__init__(
            status_code=503,
            detail="User administration is not available right now",
        )


def _admin_config() -> tuple:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not url or not key:
        raise SupabaseAdminUnavailable()
    return url, key


def _request(method: str, path: str, body: Optional[dict] = None) -> dict:
    url, key = _admin_config()
    request = urllib.request.Request(
        f"{url}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as error:
        # GoTrue's error body never contains the key; still, nothing
        # from it reaches an API response -- callers get a typed
        # failure and the detail stays server-side only.
        raise _provider_error(error.code)
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise SupabaseAdminUnavailable()


def _provider_error(status: int) -> HTTPException:
    if status in (401, 403):
        # OUR credential was rejected -- a deployment configuration
        # problem, not the caller's fault.
        return SupabaseAdminUnavailable()
    if status == 422:
        return HTTPException(status_code=422,
                             detail="The identity provider rejected the request")
    if status == 429:
        return HTTPException(status_code=429,
                             detail="Too many requests -- try again shortly")
    return SupabaseAdminUnavailable()


def _safe_user(raw: dict) -> dict:
    """Reduce a GoTrue admin user record to the fields the roster is
    allowed to see. Nothing else leaves this module."""
    metadata = raw.get("user_metadata") or {}
    return {
        "auth_user_id": str(raw.get("id", "")),
        "email": raw.get("email"),
        "display_name": metadata.get("display_name"),
        # "invited" until the person has ever completed sign-in /
        # confirmation; the roster shows this so an operator can tell
        # a pending invite from an established account.
        "confirmed": bool(raw.get("email_confirmed_at")
                          or raw.get("last_sign_in_at")),
    }


def find_user_by_email(email: str) -> Optional[dict]:
    quoted = urllib.parse.quote(email)
    result = _request("GET", f"/auth/v1/admin/users?page=1&per_page=50&email={quoted}")
    for user in result.get("users", []):
        if (user.get("email") or "").lower() == email.lower():
            return _safe_user(user)
    return None


def get_user(auth_user_id: str) -> Optional[dict]:
    quoted = urllib.parse.quote(auth_user_id)
    try:
        raw = _request("GET", f"/auth/v1/admin/users/{quoted}")
    except HTTPException:
        return None
    return _safe_user(raw) if raw.get("id") else None


def invite_user(email: str, redirect_to: str) -> dict:
    """Create + invite via GoTrue's invite flow: the user receives an
    email whose action link lands on our /auth/reset-password page to
    set their first password. Returns the safe user record."""
    body = {"email": email}
    path = "/auth/v1/invite"
    if redirect_to:
        path += "?redirect_to=" + urllib.parse.quote(redirect_to, safe="")
    raw = _request("POST", path, body)
    return _safe_user(raw)


def is_configured() -> bool:
    """Whether this deployment has the admin capability at all --
    routes use this to fail fast with the generic 503."""
    return bool(os.environ.get("SUPABASE_URL", "").strip()
                and os.environ.get("SUPABASE_SECRET_KEY", "").strip())
