# Production Smoke - Post-Deployment Verification

Use only after production deployment or when explicitly asked to verify production.

Safety rules:

- Production is actively used by a dealership.
- Prefer read-only checks.
- Do not upload files, run syncs, complete tasks, delete rows, change vehicle state, or send external communications unless explicitly approved.
- Do not print secrets.

Record production URL, `master` SHA/tag, frontend deployment, backend deployment, database target, and release PR/tag.

Repo reality: production frontend is `https://lotsync-nu.vercel.app`,
production backend is `https://lotsync-api.onrender.com` (health:
`GET /health`), production database is `/var/data/lotsync.db` on the
Render disk. Baseline and lock state: `PRODUCTION_BASELINE.md`. There
is currently no login — the app has no authentication (a known,
accepted beta condition), so session checks reduce to "public routes
behave as expected."

Verify:

- app loads,
- login/session works or public route behaves as expected,
- dashboard loads,
- inventory list loads,
- vehicle detail loads,
- task/work queue loads,
- critical reports/PDF route loads if safe,
- API health endpoint responds if present,
- no obvious frontend runtime crash.

If release changed database or environment, verify expected database target, migration state, and narrow row-count/schema checks.

Report status, version/SHA, frontend, backend, database, flows checked, issues, data changed, and rollback point.
