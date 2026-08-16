"""
provision_dev_auth.py -- Sprint 05: synthetic development auth users.

Creates (idempotently) the DealerDOH DEV synthetic accounts in
Supabase Auth and their user_membership rows in the development
database, per AUTH_ARCHITECTURE.md's access model:

    admin@qa.dealerdoh.example          admin          qa-motors
    manager@qa.dealerdoh.example        manager        qa-motors
    lotstaff@qa.dealerdoh.example       lot_staff      qa-motors
    salesmanager@qa.dealerdoh.example   sales_manager  qa-motors
    outsider@qa.dealerdoh.example       manager        qa-store-b   (ONLY)

`outsider` exists so the deployed store-isolation proof is one curl
away: a fully valid manager of Store B must get 403 from the qa-motors
deployment. No real employee or customer identity appears anywhere --
the addresses are reserved-for-documentation `.example` names, created
pre-confirmed via the admin API so no email is ever sent.

Safety:
- refuses ENVIRONMENT=production
- never prints the service key, the DSN, or any password
- generated passwords go ONLY to the file named by
  --write-passwords-to (store them in a password manager, then delete
  the file); alternatively supply your own via --passwords-file (JSON
  {email: password})
- re-running is safe: existing users are matched by email and kept
  (pass --rotate-passwords to set fresh ones); memberships are
  upserted in place. Run AFTER any `seed_dev.py --reset` (the reset
  drops membership rows; Auth users are untouched by resets and are
  simply re-linked).

Env required:
    SUPABASE_URL           the dev project URL
    SUPABASE_SECRET_KEY    service-role key -- SERVER-SIDE SECRET;
                           stage it like the DSN (env/file), never
                           commit or print it
    DATABASE_ENGINE / DATABASE_URL (or LOTSYNC_DB_PATH for a local
    SQLite experiment) -- where membership rows are written.

Usage:
    PYTHONPATH=.. python tools/provision_dev_auth.py --write-passwords-to <file>
"""

import argparse
import json
import os
import secrets
import sys
import urllib.error
import urllib.request

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

QA_USERS = (
    # (email, role, dealership_id)
    ("admin@qa.dealerdoh.example", "admin", "qa-motors"),
    ("manager@qa.dealerdoh.example", "manager", "qa-motors"),
    ("lotstaff@qa.dealerdoh.example", "lot_staff", "qa-motors"),
    ("salesmanager@qa.dealerdoh.example", "sales_manager", "qa-motors"),
    ("outsider@qa.dealerdoh.example", "manager", "qa-store-b"),
)


def _refuse_if_production() -> None:
    if os.environ.get("ENVIRONMENT", "").strip().lower() == "production":
        sys.exit("provision_dev_auth: refusing to run -- ENVIRONMENT=production. "
                 "Development environments only; production has no Supabase Auth.")


def _admin_request(supabase_url: str, secret_key: str, method: str, path: str,
                    body: dict = None) -> dict:
    request = urllib.request.Request(
        f"{supabase_url.rstrip('/')}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Surface GoTrue's error message -- it never echoes the key.
        detail = error.read().decode(errors="replace")[:300]
        sys.exit(f"provision_dev_auth: Supabase admin API {method} {path} "
                 f"failed with HTTP {error.code}: {detail}")


def _find_user_by_email(supabase_url: str, secret_key: str, email: str):
    result = _admin_request(supabase_url, secret_key, "GET",
                             f"/auth/v1/admin/users?page=1&per_page=50&email={email}")
    for user in result.get("users", []):
        if user.get("email", "").lower() == email.lower():
            return user
    return None


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Provision DealerDOH DEV synthetic auth users + memberships.")
    parser.add_argument("--passwords-file",
                        help="JSON file of {email: password} to use instead of generating")
    parser.add_argument("--write-passwords-to",
                        help="where generated passwords are written (required unless "
                             "--passwords-file is given and covers every user)")
    parser.add_argument("--rotate-passwords", action="store_true",
                        help="set a fresh password on users that already exist")
    args = parser.parse_args(argv)

    _refuse_if_production()

    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    secret_key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not supabase_url or not secret_key:
        sys.exit("provision_dev_auth: SUPABASE_URL and SUPABASE_SECRET_KEY are required "
                 "(stage the key like the DSN -- never commit it).")

    supplied = {}
    if args.passwords_file:
        with open(args.passwords_file, encoding="utf-8") as f:
            supplied = json.load(f)

    generated = {}

    def password_for(email: str) -> str:
        if email in supplied:
            return supplied[email]
        generated[email] = secrets.token_urlsafe(14)
        return generated[email]

    # Membership rows go through the same engine-dispatched repository
    # the app uses. Import after env is final (repo convention).
    sys.path.insert(0, os.path.dirname(_REPO_ROOT))
    from lotsync.database.repository import (
        connect, ensure_dealership, ensure_organization, upsert_user_membership,
    )
    from lotsync.dev_seed.scenarios import (
        QA_DEALERSHIP_BRAND, QA_DEALERSHIP_ID, QA_DEALERSHIP_NAME,
        QA_ORGANIZATION_ID, QA_ORGANIZATION_NAME,
    )

    engine = os.environ.get("DATABASE_ENGINE", "sqlite").strip().lower()
    db_path = os.environ.get("LOTSYNC_DB_PATH") if engine == "sqlite" else None
    conn = connect(db_path)
    try:
        ensure_organization(conn, QA_ORGANIZATION_ID, QA_ORGANIZATION_NAME)
        ensure_dealership(conn, QA_DEALERSHIP_ID, QA_DEALERSHIP_NAME,
                           brand=QA_DEALERSHIP_BRAND, organization_id=QA_ORGANIZATION_ID)
        # The second store exists exactly so cross-store denial stays
        # provable against the live environment, not only in tests.
        ensure_dealership(conn, "qa-store-b", "DealerDOH QA Store B",
                           brand="QA", organization_id=QA_ORGANIZATION_ID)

        report = []
        for email, role, dealership_id in QA_USERS:
            user = _find_user_by_email(supabase_url, secret_key, email)
            if user is None:
                user = _admin_request(supabase_url, secret_key, "POST", "/auth/v1/admin/users", {
                    "email": email,
                    "password": password_for(email),
                    "email_confirm": True,
                })
                status = "created"
            elif args.rotate_passwords or email in supplied:
                _admin_request(supabase_url, secret_key, "PUT",
                                f"/auth/v1/admin/users/{user['id']}",
                                {"password": password_for(email)})
                status = "existing (password set)"
            else:
                status = "existing"
            upsert_user_membership(conn, user["id"], QA_ORGANIZATION_ID,
                                    dealership_id, role, active=1)
            report.append((email, role, dealership_id, status))
        conn.commit()
    finally:
        conn.close()

    if generated:
        if not args.write_passwords_to:
            sys.exit("provision_dev_auth: passwords were generated but "
                     "--write-passwords-to was not given; refusing to print them. "
                     "Re-run with --write-passwords-to <file>.")
        with open(args.write_passwords_to, "w", encoding="utf-8") as f:
            json.dump(generated, f, indent=2)
        print(f"provision_dev_auth: {len(generated)} generated password(s) written to "
              f"{args.write_passwords_to} -- store in a password manager, then delete the file.")

    print("\nprovision_dev_auth complete (synthetic development identities only):")
    for email, role, dealership_id, status in report:
        print(f"  {email:38s} {role:14s} {dealership_id:12s} {status}")
    print("  (no passwords or keys are ever printed)")


if __name__ == "__main__":
    main()
