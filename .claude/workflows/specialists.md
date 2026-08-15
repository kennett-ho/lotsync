# Specialists - DealerDOH Self-Review Checklist

Review the diff against `origin/dev`. Fix every Critical or Important finding before continuing.

## Product Scope

- Requested scope is complete.
- No unplanned rename, migration, auth, deployment, or production behavior change.
- LotSync production baseline remains protected.

## Dealership Workflow

- Inventory, task, RecovR, key, RapidRecon, MDD, and work-order flows remain coherent.
- Empty states explain what is missing and how staff should respond.
- Errors are actionable.
- No mock dealership data appears in production UI.

## Frontend

- Existing component patterns are followed.
- Loading, error, and empty states exist.
- Forms validate input.
- Tables/search/filter/sort remain usable.
- Interactive elements are keyboard-accessible.

## Backend/API

- FastAPI errors are handled and surfaced.
- Database calls check failures.
- Sync/import logic handles malformed, duplicate, and missing source data.
- Long-running operations do not silently fail.

## Data and Schema

- Migrations are scoped and tested.
- Production data changes require explicit approval.
- SQLite/Postgres differences are handled.
- Indexes, foreign keys, RLS, and auth policies are appropriate.

## Security

- No secrets in code, logs, screenshots, PR bodies, or reports.
- User input is validated.
- Auth checks exist where needed.
- Service-role credentials are server-only.

## Tests and Handoff

- Changed behavior has tests or documented smoke evidence.
- Caveats are explicit.
- Next step is clear.
