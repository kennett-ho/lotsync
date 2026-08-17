# DealerDOH Account Lifecycle

**Established:** Infrastructure Sprint 09 (2026-08-16). The reference
for how a dealership person becomes, remains, and stops being a
DealerDOH user — and for every Profile & Settings decision the
release contract's "no decorative controls" rule required. Governing
rail: `V1_1_RELEASE_READINESS.md` §5.A.

```
Invited ──(sets password via emailed link)──> Active
Active ──(admin/manager deactivates)────────> Disabled
Disabled ──(admin/manager reactivates)──────> Active
```

## Two systems, two responsibilities

| | Supabase Auth owns | DealerDOH membership owns |
|---|---|---|
| What | Email identity, password, credential verification, recovery/invite tokens, the browser session | Organization, dealership, role, active/inactive authorization |
| Where | The Supabase project | `user_membership` (migration 0009) |
| Rule | DealerDOH stores no passwords, tokens, or profile duplicates | An Auth identity existing grants NOTHING — only an **active membership in the serving dealership** authorizes a request (re-read per request; `api/auth.py`) |

**Display name** lives in Supabase Auth `user_metadata` (the person
sets it in Settings via `supabase.auth.updateUser`) — Auth owns
profile identity, so no new schema, **no migration 0010**, and the
production-migration tooling/rehearsal assumptions are untouched this
sprint. It reaches the API inside the verified JWT and is surfaced by
`GET /me`; the roster reads it from the admin user record.

## Provisioning (no public signup — ever)

Manager/Admin → Settings → User Management → email + role → the API
(`POST /users/invite`):

1. derives organization and dealership **from the caller's own
   membership** (request bodies carry neither; extra keys are ignored
   — tested),
2. checks the role policy below,
3. looks up the email in Auth: existing identity → membership row
   only, **no re-invite email**; new identity → GoTrue invite
   (`POST /auth/v1/invite`) whose emailed link lands on
   `/auth/reset-password` to set a first password,
4. writes the membership row.

Idempotency: an active member → 409 "already a member" (nothing
re-sent, nothing duplicated); a deactivated member → 409 pointing at
**Reactivate** (never a duplicate row). Supabase signups stay
disabled project-wide; the invite flow is the only account-creation
path.

## Role policy (least privilege; server-enforced in `api/routers/users.py`)

| Caller | May grant / administer |
|---|---|
| `admin` | admin, manager, lot_staff, sales_manager |
| `manager` | lot_staff, sales_manager only |
| `lot_staff`, `sales_manager` | nothing (no roster access) |

Hard rules, each covered by `tests/test_user_management.py`:
management endpoints are server-authorized; client-supplied
dealership/role escalation is ignored/rejected; users cannot change
their own role or dealership (no such API exists; profile updates
touch `user_metadata` only); nobody self-deactivates; a manager
cannot create, promote, deactivate, or reactivate an admin **or
manager**; cross-store administrators are denied (404 — membership
existence elsewhere is not confirmed); unknown roles are rejected;
the last active admin cannot be deactivated (defense-in-depth on top
of the self-deactivation block, which already makes a zero-admin
state unreachable); a deactivated admin's own token fails at the
door. **Flagged-open product question:** whether managers should
manage other managers — the smaller policy ships until the owner
decides otherwise.

Under `AUTH_MODE=disabled` (production today) the entire `/users`
surface answers **404** — an unauthenticated deployment exposes no
user administration at all.

## Password recovery

- Login → **Forgot password?** → email →
  `supabase.auth.resetPasswordForEmail(email, redirectTo:
  <origin>/auth/reset-password)`.
- The confirmation is **enumeration-safe**: the same generic "If an
  account exists for that email…" renders whether or not the account
  exists; only rate-limit wording differs (reveals nothing about the
  account).
- The emailed link verifies at Supabase and lands on
  **`/auth/reset-password`** — a real route served on fresh
  navigation by the Vercel SPA rewrite (the Sprint 08-ratified
  deep-link requirement; pinned by `tests/test_frontend_config.py`)
  and rendered OUTSIDE the auth gate by `main.tsx`.
- Valid recovery session → new-password form (min 8 chars, confirm
  match). Invalid/expired/absent token → a safe dead-end with a path
  back to login; the operational app never mounts on this route.
- Passwords never touch logs or analytics.

**Session policy after a successful reset (the Sprint 09 decision):**
`updateUser({password})` then `signOut({scope: 'global'})` — Supabase
revokes **every refresh token** for the user; other devices die at
their next token refresh, and already-issued access tokens live only
to their short expiry. This is the strongest revocation the provider
supports and it is real, not faked. The person signs in fresh with
the new password.

Settings → Security offers **Send Password Reset Email** (the same
recovery flow, authenticated). A direct in-app change-password form
was assessed and deferred as non-blocking: it would duplicate the
recovery path's guarantees without adding security, and Supabase
remains the only password authority either way.

## Offboarding / disablement

Deactivating the membership (`active=false`) is the offboarding act:

- Authorization is **current membership state, not token claims** —
  the very next API request with a still-cryptographically-valid JWT
  gets 403 (proven by test with the same token before/after).
- Frontend: per-action 403s surface in place; when `/me` itself
  reports the account-level denial, the dedicated "Account access is
  disabled" screen renders with Sign Out — no loops, no crash, no
  internal detail.
- Reactivation restores access with history intact — memberships are
  never deleted.

**Auth ban/delete assessment (v1.1 decision):** membership
deactivation fully revokes dealership access, so Supabase-level
ban/deletion is deliberately **not** part of v1.1 offboarding — it
destroys identity/history for no additional access control. Revisit
if a person must be removed from the Auth project entirely (e.g.
legal request) — an operator action via the Supabase dashboard, not
app scope.

## Session lifecycle (Phase 17 review)

supabase-js owns the browser session: localStorage persistence
(survives refresh), automatic access-token refresh, `onAuthStateChange`
driving the gate. Verified behaviors: sign-out returns to login;
refresh keeps the session; an unrecoverable **401** from the API
(token invalid beyond silent refresh) triggers a clean global
sign-out (client → `AUTH_EXPIRED_EVENT` → AuthGate); **403** is never
treated as "session expired" — it is authenticated-but-not-allowed,
page-level except for the `/me` account-level case above.
Role/membership changes mid-session take effect on the next request
(server re-reads the row) — the UI catches up at the next `/me`
refresh.

## Profile & Settings disposition (the honesty table)

| Control (pre-Sprint-09 page) | Was | Now |
|---|---|---|
| Display Name input | Fake (local state) | **Functional** (Auth user_metadata) |
| Email | — | **Read-only** with explanation |
| Role / Dealership / Organization | Hardcoded text | **Read-only** from `/me` |
| Phone, Employee ID, Default Zone | Fake | **Removed** (no governed backing) |
| Notification preference toggles (8) | Fake | **Removed** (Rail E is CONDITIONAL) |
| Theme / Density pickers | Fake | **Removed** (unimplemented) |
| Change Password ("3 months ago") | Fake | **Functional** as Send Password Reset Email |
| Two-Factor Enable | Fake | **Removed** (MFA is POST-v1.1) |
| Active-session count, session device card | Fabricated | **Removed** |
| Sign Out (Settings) | Fake (no handler) | **Functional** |
| Recent Activity feed | Fabricated | **Removed** |
| User Management | — | **New, functional** (admin/manager only) |
| Header notification bell + red dot | Fake | **Removed** (returns with real Rail E) |

## Operator notes (DEV)

- **Render DEV env additions:** `SUPABASE_SECRET_KEY` (service-role —
  SECRET, staged by the operator; the API's admin capability; without
  it user management answers 503 and all else works) and
  `DEALERDOH_FRONTEND_URL=https://dealerdoh-dev.vercel.app` (invite
  redirect base).
- **Supabase DEV config:** Redirect URLs must allowlist
  `https://dealerdoh-dev.vercel.app/auth/reset-password` (Site URL
  stays the frontend origin). Signups remain disabled.
- **Email delivery caveat:** Supabase's built-in email service only
  delivers reliably to the project's own team-member addresses and is
  rate-limited (a documented provider limitation) — synthetic
  `.example` accounts can never receive recovery/invite email. Invite
  to an undeliverable address still creates the account + membership
  (the email just never arrives); recovery for such accounts means
  re-provisioning via `tools/provision_dev_auth.py --rotate-passwords`.
  The real end-to-end email test therefore uses an
  operator-provided deliverable address; production email posture
  (custom SMTP vs. built-in) is a Release C-prep decision recorded in
  the migration plan's §22 register.
- Production migration implications: **none this sprint** — no schema
  change, no migration 0010, rehearsal assumptions intact. Release C
  gains: the same two env vars on production Render when auth
  arrives, and the production frontend origin in Supabase redirect
  URLs — recorded in `PRODUCTION_MIGRATION_PLAN.md`'s env matrix at
  execution time.
