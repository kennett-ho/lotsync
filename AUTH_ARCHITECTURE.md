# DealerDOH Authentication & Authorization Architecture

Sprint 05. The first identity and access boundary in the codebase.
This document is the reference for how a request becomes an
authorized dealership operation — and for the deliberately loud
difference between the two deployed environments:

```
Identity Provider:        Supabase Auth (dev project dealerdoh-dev)
Authorization Boundary:   FastAPI (api/auth.py) — server-side, always
Tenant Model:             Organization → Dealership → Membership → Role
DEV:                      AUTH_MODE=required — authenticated synthetic users only
PROD:                     AUTH_MODE unset (disabled) — still the unauthenticated
                          LotSync beta, byte-for-byte pre-Sprint-05 behavior
```

## Request flow (DEV)

```
Browser (React)
  └─ supabase-js: email/password sign-in → session (localStorage,
     auto-refreshed) → access token attached as Bearer by the single
     fetch boundary (frontend/src/api/client.ts)
        ↓
FastAPI (api/auth.py :: get_access_context — on every operational route)
  1. Parse Bearer token (absent/malformed → 401 + WWW-Authenticate)
  2. Verify signature against the Supabase project's public JWKS —
     algorithm pinned to ES256 (the project signs with an ECC P-256
     key; HS256/none are rejected outright), issuer + audience + exp
     checked, sub required
  3. Resolve user_membership(auth_user_id, serving dealership) —
     the serving dealership is the DEPLOYMENT'S OWN configuration
     (DEALERDOH_DEALERSHIP_ID=qa-motors), never client input
  4. No active membership for exactly that dealership → 403
  5. Routes receive a typed AccessContext(role, organization,
     dealership, email) — role comes from the membership row ONLY
        ↓
Business data (unchanged by this sprint)
```

**Intentionally public:** `GET /health` (Render health checks; no
dealership data). `GET /me` carries the same dependency — it 401/403s
like any operational route in required mode and reports
`{"authenticated": false, "auth_mode": "disabled"}` honestly
otherwise. Everything else — vehicles, tasks, work-order,
recommendations, activity, dashboard, reports, inventory-sync — is
protected at router-include time, so a future router inherits
protection by default.

## Access model

Schema: `database/migrations/0009_access_model.sql` (+ PostgreSQL
dialect). This executed DATA_MODEL.md's long-standing "Tenant vs
Dealership" resolution — *"Dealership gains a tenant_id and becomes a
child of Tenant — that's the whole migration"* — introducing that
parent as `organization` and reusing the **existing** `dealership`
table as the store entity (no duplicate "store" table was created).

- `organization` — the auto group. QA row: `qa-auto-group`
  ("DealerDOH QA Auto Group").
- `dealership.organization_id` — the anticipated parent link
  (nullable; production-path rows never populate it).
- `user_membership(auth_user_id, organization_id, dealership_id,
  role, active)` — the authorization row. `auth_user_id` is the
  Supabase Auth UUID as TEXT (no FK — identity remains Supabase's;
  DealerDOH stores no passwords, no tokens, no profile duplicates).
  One row per (user, dealership), role CHECK-constrained to exactly
  `admin | manager | lot_staff | sales_manager`, deactivated-not-
  deleted via `active`.

## Roles (deliberately minimal)

| Role | This sprint |
|---|---|
| `admin` | Full access to current operational features + sync run |
| `manager` | Same as admin today (the distinction is reserved, not invented) |
| `lot_staff` | All shared operational reads/workflows; **cannot** trigger a sync run |
| `sales_manager` | Authenticated + store-scoped shared data access; exists to reserve the architecture for future sales modules — no commission features |

The **only** enforced role difference is `POST /inventory-sync/run`
(admin/manager — grounded in the governed role definitions: running a
sync mutates dealership state). Every read stays shared across all
active members, per the sprint rule against inventing restrictions.
Role spoofing is structurally impossible: the API never reads a role
from token metadata, query params, or bodies — only from the
membership row (proven in `tests/test_auth.py`).

## Store boundary — what is and isn't true yet

**True now:** every request is authorized against the deployment's
serving dealership. A member of only `qa-store-b` gets 403 from the
`qa-motors` deployment no matter what store IDs they claim
(automated: `tests/test_auth.py::test_cross_store_denial`; live: the
provisioned `outsider@…` account).

**Not true yet — mandatory before a second real store:** business
rows (`vehicle`, `task`, `event`, …) are not per-row store-scoped;
the dealership_id columns that already exist on several tables remain
unpopulated (their attribution logic is the importer-level work
`models/dealership.py` describes). The current deployment model is
one-store-per-deployment, made explicit rather than implicit. Before
any deployment serves two stores' data from one database, per-row
scoping + query filters must land first — this is recorded as a
blocking prerequisite, not an optional improvement.

## Token verification without live Supabase (CI)

The verifier's key source is injectable: deployed, it fetches the
project JWKS (cached) from `SUPABASE_URL`; under test, `AUTH_JWKS`
carries an inline JWKS for an ephemeral P-256 keypair generated at
test time, and tokens are minted locally. Same code path, same
algorithm pin, zero cloud dependency, zero secrets in GitHub Actions.

## RLS decision (assessed, deferred)

Row Level Security is **not** enabled this sprint, deliberately:

1. The browser never talks to the database — the Data API exposes no
   app tables (Sprint 02 choice, unchanged), so there is no
   browser-to-database path for RLS to guard.
2. The API connects via the session pooler as the table owner; RLS
   does not constrain a role with BYPASSRLS-equivalent ownership, so
   enabling it today would be decoration, not defense.
3. FastAPI is the single, tested authorization boundary (this
   document; 25 auth tests on both engines).

**Before any direct browser-to-database access is ever allowed**, all
of the following must happen first: RLS policies expressing the
membership/store model, a non-owner database role for client access,
and tests proving policy behavior — treat that as a design sprint,
not a toggle. Until then, the frontend must not begin querying
Supabase tables directly merely because supabase-js makes it easy.

## Synthetic identities

Provisioned by `tools/provision_dev_auth.py` (idempotent; refuses
production; passwords go to an operator-named file only — password
manager, then delete). Accounts use reserved `.example` addresses,
admin-created pre-confirmed (no email delivery), public signups
disabled in the Supabase project. Roster + usage: `DEV_QA_GUIDE.md`.

## Secrets inventory

| Value | Class | Lives |
|---|---|---|
| Supabase anon key (`VITE_SUPABASE_ANON_KEY`) | Public by design | Vercel DEV env (baked into bundle) |
| `SUPABASE_URL` / JWKS / issuer | Public | Render DEV env |
| `DATABASE_URL` (pooler DSN) | **Secret** | Render DEV env + owner's password manager |
| Service-role key (`SUPABASE_SECRET_KEY`) | **Secret** | Operator-staged for provisioning only; never in git, browser, or CI |
| Synthetic user passwords | Dev-only credentials | Password manager (file deleted after provisioning) |

The API never logs Authorization headers or token contents, and every
401 body is the same generic message.

## Sprint 09 addendum — account lifecycle

Rail A added the user-administration surface (`api/routers/users.py`:
roster, invite, deactivate, reactivate) on top of this architecture
without changing any invariant: role policy is enforced from the
caller's membership row; the target dealership is always the caller's
own; the GoTrue Admin API is reached only through the server-side
`api/supabase_admin.py` boundary (`SUPABASE_SECRET_KEY` — Render env
only, never VITE_*, never logged); and under `AUTH_MODE=disabled` the
entire surface answers 404, so the unauthenticated production posture
gains no dormant admin endpoints. Deactivation is effective on the
target's next request — authorization remains current membership
state, never stale token claims. Display name rides the verified
token's `user_metadata` into `AccessContext`/`GET /me` (Supabase Auth
owns profile identity; no schema change). Password recovery and the
full lifecycle model: `ACCOUNT_LIFECYCLE.md`.
