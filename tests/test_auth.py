"""
Sprint 05 -- the authentication/authorization boundary (api/auth.py).

Every test here runs with AUTH_MODE=required and a locally minted
ES256 keypair injected through AUTH_JWKS -- the exact verification
code path the deployed dev API uses against Supabase's JWKS, with no
live Supabase anywhere (the CI constraint: self-contained,
deterministic, no cloud secrets). Tokens are signed with
`cryptography`-generated P-256 keys at test time; nothing here is a
mock of the verifier itself.

The matrix, per the Sprint 05 spec:
- unauthenticated  -> 401 (vehicles, tasks, work-order, sync run)
- invalid tokens   -> 401 (garbage, wrong key, unknown kid, alg=none,
                      wrong issuer, wrong audience, expired, no sub)
- valid + no membership / inactive membership -> 403
- valid + active membership -> 200, /me reports the membership truth
- STORE BOUNDARY: a member of only Store B is denied Store A's data
- roles: sync run allowed for admin/manager, denied for lot_staff /
  sales_manager; role comes from the membership row, so token-claim
  spoofing changes nothing
- AUTH_MODE=disabled (the default, production path) stays exactly
  pre-Sprint-05 -- also re-proven by the entire pre-existing suite,
  which runs with no auth env at all.
"""

import datetime
import json
import os
import unittest
import uuid
from unittest import mock

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from lotsync.api.app import app
from lotsync.api.dependencies import get_db
from lotsync.database.repository import (
    connect, ensure_dealership, ensure_organization, upsert_user_membership,
    upsert_vehicle,
)

ISSUER = "https://qa-issuer.invalid/auth/v1"
AUDIENCE = "authenticated"
KID = "qa-test-key-1"

# One keypair for the whole module -- generating EC keys is cheap but
# there's no reason to do it per test.
_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
_PUBLIC_JWK = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(_PRIVATE_KEY.public_key()))
_PUBLIC_JWK.update({"kid": KID, "alg": "ES256", "use": "sig"})
JWKS_JSON = json.dumps({"keys": [_PUBLIC_JWK]})

# A second, WRONG keypair: its signatures must never verify against
# the JWKS above even when the token claims the right kid.
_WRONG_KEY = ec.generate_private_key(ec.SECP256R1())

AUTH_ENV = {
    "AUTH_MODE": "required",
    "AUTH_JWKS": JWKS_JSON,
    "AUTH_JWT_ISSUER": ISSUER,
}

USERS = {
    # auth_user_id -> (role, dealership) seeded in setUp
    "admin": (str(uuid.uuid4()), "admin", "qa-motors"),
    "manager": (str(uuid.uuid4()), "manager", "qa-motors"),
    "lot_staff": (str(uuid.uuid4()), "lot_staff", "qa-motors"),
    "sales_manager": (str(uuid.uuid4()), "sales_manager", "qa-motors"),
    "outsider": (str(uuid.uuid4()), "manager", "qa-store-b"),  # Store B ONLY
    "inactive": (str(uuid.uuid4()), "manager", "qa-motors"),   # active=0
    "nobody": (str(uuid.uuid4()), None, None),                  # no membership
}


def mint(auth_user_id: str, *, key=_PRIVATE_KEY, kid: str = KID,
         issuer: str = ISSUER, audience: str = AUDIENCE,
         expires_in: int = 3600, email: str = "user@qa.dealerdoh.example",
         extra_claims: dict = None, algorithm: str = "ES256") -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    claims = {
        "sub": auth_user_id,
        "aud": audience,
        "iss": issuer,
        "iat": now,
        "exp": now + datetime.timedelta(seconds=expires_in),
        "email": email,
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, key, algorithm=algorithm, headers={"kid": kid})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class AuthTestCase(unittest.TestCase):
    """Required-mode app over an in-memory DB with the access model seeded."""

    def setUp(self):
        self.conn = connect(":memory:")
        ensure_organization(self.conn, "qa-auto-group", "DealerDOH QA Auto Group")
        ensure_dealership(self.conn, "qa-motors", "DealerDOH QA Motors",
                           organization_id="qa-auto-group")
        # The second store the cross-store denial proves against --
        # created here in tests exactly so the boundary is proven long
        # before a second real store exists (Sprint 05 spec, Phase 12).
        ensure_dealership(self.conn, "qa-store-b", "DealerDOH QA Store B",
                           organization_id="qa-auto-group")
        for name, (user_id, role, dealership) in USERS.items():
            if role is None:
                continue
            upsert_user_membership(
                self.conn, user_id, "qa-auto-group", dealership, role,
                active=0 if name == "inactive" else 1,
            )
        upsert_vehicle(self.conn, "1QATESTAUTH000001", tekion_status="Stocked In")
        self.conn.commit()

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self._env = mock.patch.dict(os.environ, AUTH_ENV)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        app.dependency_overrides.clear()
        self.conn.close()

    def token_for(self, name: str, **kwargs) -> str:
        return mint(USERS[name][0], **kwargs)


class UnauthenticatedTest(AuthTestCase):
    def test_health_stays_public(self):
        # Render's health checking must keep working with no token.
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_operational_routes_reject_missing_token(self):
        for method, path in (("GET", "/vehicles"), ("GET", "/tasks"),
                              ("GET", "/tasks/work-order"), ("GET", "/dashboard"),
                              ("GET", "/activity"), ("GET", "/recommendations"),
                              ("GET", "/inventory-sync/history"),
                              ("POST", "/inventory-sync/run")):
            resp = self.client.request(method, path)
            self.assertEqual(resp.status_code, 401, f"{method} {path}")
            self.assertEqual(resp.headers.get("WWW-Authenticate"), "Bearer",
                             f"{method} {path} must challenge with Bearer")

    def test_me_rejects_missing_token_in_required_mode(self):
        self.assertEqual(self.client.get("/me").status_code, 401)

    def test_non_bearer_scheme_rejected(self):
        resp = self.client.get("/vehicles",
                                headers={"Authorization": "Basic dXNlcjpwYXNz"})
        self.assertEqual(resp.status_code, 401)


class InvalidTokenTest(AuthTestCase):
    def _assert_401(self, token: str, note: str):
        resp = self.client.get("/vehicles", headers=bearer(token))
        self.assertEqual(resp.status_code, 401, note)
        # Generic body -- no token material, no failure specifics.
        self.assertEqual(resp.json()["detail"], "Not authenticated", note)

    def test_garbage_token(self):
        self._assert_401("not-a-jwt-at-all", "garbage string")

    def test_wrong_signing_key_same_kid(self):
        self._assert_401(self.token_for("manager", key=_WRONG_KEY),
                          "signature from a different keypair")

    def test_unknown_kid(self):
        self._assert_401(self.token_for("manager", kid="some-other-kid"),
                          "kid not present in JWKS")

    def test_alg_none_rejected(self):
        # An unsigned token must never pass -- ES256 is pinned.
        now = datetime.datetime.now(datetime.timezone.utc)
        unsigned = jwt.encode(
            {"sub": USERS["manager"][0], "aud": AUDIENCE, "iss": ISSUER,
             "iat": now, "exp": now + datetime.timedelta(hours=1)},
            key=None, algorithm="none", headers={"kid": KID},
        )
        self._assert_401(unsigned, "alg=none")

    def test_wrong_issuer(self):
        self._assert_401(self.token_for("manager", issuer="https://evil.invalid/auth/v1"),
                          "issuer mismatch")

    def test_wrong_audience(self):
        self._assert_401(self.token_for("manager", audience="something-else"),
                          "audience mismatch")

    def test_expired_token(self):
        self._assert_401(self.token_for("manager", expires_in=-60), "expired")

    def test_missing_sub_claim(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        token = jwt.encode(
            {"aud": AUDIENCE, "iss": ISSUER, "iat": now,
             "exp": now + datetime.timedelta(hours=1)},
            _PRIVATE_KEY, algorithm="ES256", headers={"kid": KID},
        )
        self._assert_401(token, "no sub claim")


class MembershipAuthorizationTest(AuthTestCase):
    def test_valid_token_without_membership_is_403(self):
        resp = self.client.get("/vehicles", headers=bearer(self.token_for("nobody")))
        self.assertEqual(resp.status_code, 403)

    def test_inactive_membership_is_403(self):
        resp = self.client.get("/vehicles", headers=bearer(self.token_for("inactive")))
        self.assertEqual(resp.status_code, 403)

    def test_active_member_is_allowed(self):
        resp = self.client.get("/vehicles", headers=bearer(self.token_for("lot_staff")))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_cross_store_denial(self):
        # THE store boundary: a fully valid, fully active manager of
        # Store B gets nothing from this deployment, which serves
        # qa-motors. Authorization is the deployment's own membership
        # check -- not the caller's assertion of a store.
        resp = self.client.get("/vehicles", headers=bearer(self.token_for("outsider")))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "No active membership for this dealership")

    def test_client_supplied_store_parameters_change_nothing(self):
        # Even explicitly claiming a store in the query string moves
        # nothing -- there is no code path that reads it.
        resp = self.client.get(
            "/vehicles", params={"store_id": "qa-store-b", "dealership_id": "qa-store-b"},
            headers=bearer(self.token_for("outsider")),
        )
        self.assertEqual(resp.status_code, 403)

    def test_me_reports_membership_truth(self):
        resp = self.client.get("/me", headers=bearer(self.token_for("manager")))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["authenticated"], True)
        self.assertEqual(body["role"], "manager")
        self.assertEqual(body["dealership"],
                         {"id": "qa-motors", "name": "DealerDOH QA Motors"})
        self.assertEqual(body["organization"],
                         {"id": "qa-auto-group", "name": "DealerDOH QA Auto Group"})

    def test_display_name_is_length_clamped(self):
        # Sprint 13 (F4): display_name is self-set in user_metadata and
        # rendered in the UI/roster -- an over-long value is bounded when
        # it crosses into DealerDOH (it never affects authorization).
        token = self.token_for("manager", extra_claims={
            "user_metadata": {"display_name": "A" * 500}})
        body = self.client.get("/me", headers=bearer(token)).json()
        self.assertEqual(body["role"], "manager")  # authz unaffected
        self.assertLessEqual(len(body["display_name"]), 100)

    def test_display_name_control_characters_stripped(self):
        token = self.token_for("manager", extra_claims={
            "user_metadata": {"display_name": "Real\nName\r\x00Here"}})
        body = self.client.get("/me", headers=bearer(token)).json()
        self.assertNotIn("\n", body["display_name"])
        self.assertNotIn("\x00", body["display_name"])
        self.assertIn("Real", body["display_name"])


class DisplayNameClampUnitTest(unittest.TestCase):
    def test_clamp_rules(self):
        from lotsync.api.auth import clamp_display_name
        self.assertIsNone(clamp_display_name(None))
        self.assertIsNone(clamp_display_name(12345))       # non-string
        self.assertIsNone(clamp_display_name("   "))        # blank after strip
        self.assertEqual(clamp_display_name("  Kennett Ho  "), "Kennett Ho")
        self.assertEqual(len(clamp_display_name("x" * 250)), 100)
        self.assertEqual(clamp_display_name("A\x07B\x1fC"), "ABC")  # control chars
        self.assertEqual(clamp_display_name("Tab\tOK"), "Tab\tOK")   # tab kept


class RoleTest(AuthTestCase):
    def test_every_role_reads_shared_dealership_data(self):
        # Per the spec: no invented read restrictions -- all four roles
        # see the shared operational data.
        for name in ("admin", "manager", "lot_staff", "sales_manager"):
            resp = self.client.get("/tasks", headers=bearer(self.token_for(name)))
            self.assertEqual(resp.status_code, 200, name)

    def test_sync_run_requires_admin_or_manager(self):
        for name, expected in (("admin", "allowed"), ("manager", "allowed"),
                                ("lot_staff", "denied"), ("sales_manager", "denied")):
            resp = self.client.post("/inventory-sync/run",
                                     headers=bearer(self.token_for(name)))
            if expected == "denied":
                self.assertEqual(resp.status_code, 403, name)
            else:
                # The role gate passes and the request proceeds to the
                # route's own validation, which rejects the empty
                # upload -- anything but 401/403 proves authorization
                # succeeded without actually running a sync here.
                self.assertNotIn(resp.status_code, (401, 403), name)

    def test_validate_endpoint_shares_the_sync_role_gate(self):
        # Sprint 10: the pre-sync preview is part of the sync surface
        # -- same admin/manager restriction, same 401 unauthenticated.
        resp = self.client.post("/inventory-sync/validate")
        self.assertEqual(resp.status_code, 401, "unauthenticated")
        for name, expected in (("admin", "allowed"), ("manager", "allowed"),
                                ("lot_staff", "denied"), ("sales_manager", "denied"),
                                ("outsider", "denied"), ("inactive", "denied"),
                                ("nobody", "denied")):
            resp = self.client.post("/inventory-sync/validate",
                                     headers=bearer(self.token_for(name)))
            if expected == "denied":
                self.assertEqual(resp.status_code, 403, name)
            else:
                # Role gate passed; the route's own empty-upload 422
                # proves authorization succeeded without validating
                # anything real here.
                self.assertNotIn(resp.status_code, (401, 403), name)

    def test_role_cannot_be_spoofed_from_token_claims(self):
        # A lot_staff member self-asserting admin in every plausible
        # claim location still gets the membership row's role.
        token = self.token_for("lot_staff", extra_claims={
            "role": "admin",
            "app_metadata": {"role": "admin"},
            "user_metadata": {"role": "admin"},
        })
        me = self.client.get("/me", headers=bearer(token)).json()
        self.assertEqual(me["role"], "lot_staff")
        resp = self.client.post("/inventory-sync/run", headers=bearer(token))
        self.assertEqual(resp.status_code, 403,
                         "spoofed claims must not unlock the sync run")

    def test_unknown_role_is_rejected_at_write_time(self):
        # The CHECK constraint makes an unknown role unrepresentable --
        # the earliest, safest failure point (api/auth.py's own
        # unknown-role guard is unreachable belt-and-suspenders).
        from lotsync.database.repository import IntegrityError
        with self.assertRaises(IntegrityError):
            upsert_user_membership(self.conn, str(uuid.uuid4()),
                                    "qa-auto-group", "qa-motors", "superuser")
        self.conn.rollback()


class MisconfigurationFailsClosedTest(AuthTestCase):
    def test_required_mode_without_key_source_is_500_not_open(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("AUTH_JWKS", "SUPABASE_URL")}
        env["AUTH_MODE"] = "required"
        with mock.patch.dict(os.environ, env, clear=True):
            resp = self.client.get("/vehicles",
                                    headers=bearer(self.token_for("manager")))
        self.assertEqual(resp.status_code, 500)
        self.assertIn("misconfigured", resp.json()["detail"])


class AuthDisabledTest(unittest.TestCase):
    """
    The default posture -- the production path. No auth env set: every
    route behaves exactly as before Sprint 05 (the rest of the suite
    re-proves this at full breadth; these are the targeted checks).
    """

    def setUp(self):
        self.conn = connect(":memory:")
        upsert_vehicle(self.conn, "1QATESTAUTH000002")
        self.conn.commit()

        def override_get_db():
            yield self.conn

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        # Explicitly strip any auth env the outer process might carry.
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("AUTH_", "SUPABASE_"))}
        self._env = mock.patch.dict(os.environ, env, clear=True)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        app.dependency_overrides.clear()
        self.conn.close()

    def test_routes_are_open_and_unchanged(self):
        self.assertEqual(self.client.get("/vehicles").status_code, 200)
        self.assertEqual(self.client.get("/tasks").status_code, 200)

    def test_me_reports_disabled_posture_honestly(self):
        self.assertEqual(self.client.get("/me").json(),
                         {"authenticated": False, "auth_mode": "disabled"})


if __name__ == "__main__":
    unittest.main()
