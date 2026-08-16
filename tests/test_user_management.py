"""
Sprint 09 -- the user-administration authorization matrix (Rail A).

Builds on tests/test_auth.py's harness (required-mode app, in-memory
DB, locally minted ES256 tokens -- no live Supabase anywhere). The
GoTrue admin boundary (api/supabase_admin.py) is replaced at the
module seam with a fake in-process user store, so invite/roster flows
run for real EXCEPT the outbound provider call -- exactly the layer
the live DEV smoke covers instead.

Matrix (sprint spec Phase 19):
- unauthenticated / lot_staff / sales_manager / cross-store manager
  denied
- admin can grant all roles; manager only operational roles
- manager cannot create/promote admin (or manager -- smallest policy)
- client-supplied dealership/organization ignored
- unknown role rejected; role escalation rejected
- duplicate invite -> 409, no duplicate rows; deactivated -> 409
  pointing at reactivate
- deactivation: same still-valid JWT loses access on the next request;
  reactivation restores it
- self-deactivation refused; last-active-admin deactivation refused
- disabled admin cannot administer
- AUTH_MODE=disabled -> the entire surface answers 404
- roster/DTO contains no Auth internals
"""

import os
import unittest
import uuid
from unittest import mock

from lotsync.api import supabase_admin
from lotsync.database.repository import (
    get_membership_any_state, upsert_user_membership,
)

from tests.test_auth import USERS, AuthTestCase, bearer


class FakeSupabaseAdmin:
    """In-process stand-in for the GoTrue admin API."""

    def __init__(self):
        self.users = {}  # auth_user_id -> record
        self.invites_sent = []
        # Seed records for the membership users the harness creates.
        for name, (user_id, _role, _store) in USERS.items():
            self.users[user_id] = {
                "auth_user_id": user_id,
                "email": f"{name}@qa.dealerdoh.example",
                "display_name": None,
                "confirmed": True,
            }

    def find_user_by_email(self, email):
        for record in self.users.values():
            if record["email"].lower() == email.lower():
                return dict(record)
        return None

    def get_user(self, auth_user_id):
        record = self.users.get(auth_user_id)
        return dict(record) if record else None

    def invite_user(self, email, redirect_to):
        record = {
            "auth_user_id": str(uuid.uuid4()),
            "email": email,
            "display_name": None,
            "confirmed": False,
        }
        self.users[record["auth_user_id"]] = record
        self.invites_sent.append((email, redirect_to))
        return dict(record)


class UserManagementTestCase(AuthTestCase):
    def setUp(self):
        super().setUp()
        self.fake_admin = FakeSupabaseAdmin()
        self._patches = [
            mock.patch.object(supabase_admin, "is_configured", return_value=True),
            mock.patch.object(supabase_admin, "find_user_by_email",
                              side_effect=self.fake_admin.find_user_by_email),
            mock.patch.object(supabase_admin, "get_user",
                              side_effect=self.fake_admin.get_user),
            mock.patch.object(supabase_admin, "invite_user",
                              side_effect=self.fake_admin.invite_user),
        ]
        for patch in self._patches:
            patch.start()

    def tearDown(self):
        for patch in self._patches:
            patch.stop()
        super().tearDown()

    def auth(self, name: str) -> dict:
        return bearer(self.token_for(name))


class AccessDenialTest(UserManagementTestCase):
    def test_unauthenticated_401(self):
        for method, path in (("GET", "/users"), ("POST", "/users/invite"),
                              ("POST", "/users/x/deactivate"),
                              ("POST", "/users/x/reactivate")):
            self.assertEqual(self.client.request(method, path).status_code, 401,
                             f"{method} {path}")

    def test_non_admin_roles_403(self):
        for caller in ("lot_staff", "sales_manager"):
            self.assertEqual(
                self.client.get("/users", headers=self.auth(caller)).status_code,
                403, caller)
            self.assertEqual(
                self.client.post("/users/invite", headers=self.auth(caller),
                                 json={"email": "x@example.com", "role": "lot_staff"},
                                 ).status_code, 403, caller)

    def test_cross_store_manager_403(self):
        # outsider is a manager -- but only of Store B; the serving
        # dealership must deny the entire surface.
        self.assertEqual(
            self.client.get("/users", headers=self.auth("outsider")).status_code,
            403)

    def test_disabled_admin_membership_cannot_administer(self):
        # A deactivated membership fails at the front door (403 from
        # get_access_context), proving deactivation covers admins too.
        self.assertEqual(
            self.client.get("/users", headers=self.auth("inactive")).status_code,
            403)

    def test_disabled_mode_hides_surface_entirely(self):
        with mock.patch.dict(os.environ, {"AUTH_MODE": "disabled"}):
            for method, path in (("GET", "/users"), ("POST", "/users/invite")):
                self.assertEqual(self.client.request(method, path).status_code,
                                 404, f"{method} {path} must not exist unauthenticated")


class RosterTest(UserManagementTestCase):
    def test_admin_sees_serving_dealership_roster_only(self):
        resp = self.client.get("/users", headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 200)
        roster = resp.json()
        ids = {entry["auth_user_id"] for entry in roster}
        # qa-motors members (active + the inactive one) are present...
        self.assertIn(USERS["admin"][0], ids)
        self.assertIn(USERS["lot_staff"][0], ids)
        self.assertIn(USERS["inactive"][0], ids)
        # ...the Store-B-only manager is NOT.
        self.assertNotIn(USERS["outsider"][0], ids)

    def test_roster_exposes_only_safe_fields(self):
        resp = self.client.get("/users", headers=self.auth("manager"))
        self.assertEqual(resp.status_code, 200)
        allowed = {"auth_user_id", "email", "display_name", "role",
                   "active", "account_state"}
        for entry in resp.json():
            self.assertEqual(set(entry.keys()), allowed)


class InviteTest(UserManagementTestCase):
    def test_admin_invites_every_role(self):
        for role in ("admin", "manager", "lot_staff", "sales_manager"):
            resp = self.client.post(
                "/users/invite", headers=self.auth("admin"),
                json={"email": f"new-{role}@example.com", "role": role})
            self.assertEqual(resp.status_code, 200, role)
            self.assertEqual(resp.json()["role"], role)
            self.assertEqual(resp.json()["account_state"], "invited")

    def test_manager_invites_operational_roles_only(self):
        for role in ("lot_staff", "sales_manager"):
            resp = self.client.post(
                "/users/invite", headers=self.auth("manager"),
                json={"email": f"op-{role}@example.com", "role": role})
            self.assertEqual(resp.status_code, 200, role)
        for role in ("admin", "manager"):
            resp = self.client.post(
                "/users/invite", headers=self.auth("manager"),
                json={"email": f"blocked-{role}@example.com", "role": role})
            self.assertEqual(resp.status_code, 403, role)

    def test_unknown_role_rejected(self):
        resp = self.client.post(
            "/users/invite", headers=self.auth("admin"),
            json={"email": "x@example.com", "role": "superuser"})
        self.assertEqual(resp.status_code, 422)

    def test_bad_email_rejected(self):
        resp = self.client.post(
            "/users/invite", headers=self.auth("admin"),
            json={"email": "not-an-email", "role": "lot_staff"})
        self.assertEqual(resp.status_code, 422)

    def test_client_supplied_dealership_is_ignored(self):
        # Extra keys change nothing: membership lands in the CALLER's
        # dealership, not the claimed one.
        resp = self.client.post(
            "/users/invite", headers=self.auth("admin"),
            json={"email": "aimed@example.com", "role": "lot_staff",
                  "dealership_id": "qa-store-b",
                  "organization_id": "someone-elses-org"})
        self.assertEqual(resp.status_code, 200)
        created_id = resp.json()["auth_user_id"]
        self.assertIsNotNone(
            get_membership_any_state(self.conn, created_id, "qa-motors"))
        self.assertIsNone(
            get_membership_any_state(self.conn, created_id, "qa-store-b"))

    def test_duplicate_invite_conflicts_not_duplicates(self):
        body = {"email": "dupe@example.com", "role": "lot_staff"}
        first = self.client.post("/users/invite", headers=self.auth("admin"), json=body)
        self.assertEqual(first.status_code, 200)
        second = self.client.post("/users/invite", headers=self.auth("admin"), json=body)
        self.assertEqual(second.status_code, 409)
        # Exactly one invite email went out.
        emails = [email for email, _ in self.fake_admin.invites_sent]
        self.assertEqual(emails.count("dupe@example.com"), 1)

    def test_invite_existing_auth_user_adds_membership_without_reinvite(self):
        # outsider exists in Auth (Store B member) but has no
        # qa-motors membership -- inviting them here adds one and sends
        # no new invite email.
        resp = self.client.post(
            "/users/invite", headers=self.auth("admin"),
            json={"email": "outsider@qa.dealerdoh.example", "role": "lot_staff"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.fake_admin.invites_sent, [])
        membership = get_membership_any_state(
            self.conn, USERS["outsider"][0], "qa-motors")
        self.assertEqual(membership["role"], "lot_staff")

    def test_invite_deactivated_member_points_to_reactivate(self):
        resp = self.client.post(
            "/users/invite", headers=self.auth("admin"),
            json={"email": "inactive@qa.dealerdoh.example", "role": "manager"})
        self.assertEqual(resp.status_code, 409)
        self.assertIn("Reactivate", resp.json()["detail"])


class LifecycleTest(UserManagementTestCase):
    def test_deactivation_revokes_existing_token_immediately(self):
        staff_token = bearer(self.token_for("lot_staff"))
        self.assertEqual(
            self.client.get("/vehicles", headers=staff_token).status_code, 200)

        resp = self.client.post(
            f"/users/{USERS['lot_staff'][0]}/deactivate",
            headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["active"])

        # Same, still-cryptographically-valid JWT: access is gone,
        # because authorization is the membership row, not the token.
        self.assertEqual(
            self.client.get("/vehicles", headers=staff_token).status_code, 403)

        resp = self.client.post(
            f"/users/{USERS['lot_staff'][0]}/reactivate",
            headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            self.client.get("/vehicles", headers=staff_token).status_code, 200)

    def test_manager_can_administer_operational_only(self):
        self.assertEqual(
            self.client.post(f"/users/{USERS['lot_staff'][0]}/deactivate",
                             headers=self.auth("manager")).status_code, 200)
        self.assertEqual(
            self.client.post(f"/users/{USERS['lot_staff'][0]}/reactivate",
                             headers=self.auth("manager")).status_code, 200)
        # ...but not an admin.
        self.assertEqual(
            self.client.post(f"/users/{USERS['admin'][0]}/deactivate",
                             headers=self.auth("manager")).status_code, 403)

    def test_self_deactivation_refused(self):
        resp = self.client.post(
            f"/users/{USERS['admin'][0]}/deactivate", headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 403)
        self.assertIn("own membership", resp.json()["detail"])

    def test_last_active_admin_protected(self):
        from tests.test_auth import mint

        # Seed a SECOND active admin so pairs of (de)activations can be
        # exercised; the guard must always block the step that would
        # leave the dealership with zero active admins.
        second_admin = str(uuid.uuid4())
        self.fake_admin.users[second_admin] = {
            "auth_user_id": second_admin, "email": "admin2@example.com",
            "display_name": None, "confirmed": True}
        upsert_user_membership(self.conn, second_admin, "qa-auto-group",
                               "qa-motors", "admin", active=1)
        self.conn.commit()
        token2 = {"Authorization": f"Bearer {mint(second_admin)}"}

        # With two active admins, deactivating the first is allowed
        # (performed by the second -- self-deactivation is refused).
        resp = self.client.post(
            f"/users/{USERS['admin'][0]}/deactivate", headers=token2)
        self.assertEqual(resp.status_code, 200)

        # second_admin is now the LAST active admin. The deactivated
        # first admin's token fails at the door (proving deactivation
        # bites admins too)...
        resp = self.client.post(
            f"/users/{second_admin}/deactivate", headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 403)

        # ...and the zero-active-admins state is structurally
        # unreachable: reactivate the first, deactivate the second,
        # leaving first as the only active admin. First cannot
        # self-deactivate (403), a deactivated admin's token fails at
        # the door (403 above), and the count guard 409s the
        # remaining degenerate path (re-deactivating while only one
        # active admin exists) as defense-in-depth.
        self.client.post(f"/users/{USERS['admin'][0]}/reactivate", headers=token2)
        resp = self.client.post(f"/users/{second_admin}/deactivate",
                                headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(f"/users/{second_admin}/deactivate",
                                headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 409)
        self.assertIn("last active admin", resp.json()["detail"])

    def test_unknown_membership_404_covers_cross_store(self):
        # outsider's Store-B membership is invisible here: 404, not a
        # confirmation that a membership exists elsewhere.
        resp = self.client.post(
            f"/users/{USERS['outsider'][0]}/deactivate",
            headers=self.auth("admin"))
        self.assertEqual(resp.status_code, 404)


class MeDisplayNameTest(UserManagementTestCase):
    def test_me_carries_display_name_from_token_metadata(self):
        token = self.token_for(
            "manager",
            extra_claims={"user_metadata": {"display_name": "Casey QA"}})
        resp = self.client.get("/me", headers=bearer(token))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["display_name"], "Casey QA")

    def test_me_display_name_null_when_absent(self):
        resp = self.client.get("/me", headers=self.auth("manager"))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["display_name"])


if __name__ == "__main__":
    unittest.main()
