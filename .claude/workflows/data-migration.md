# Data Migration - SQLite, Postgres, and Supabase Safeguards

Use for schema changes, data migration, Supabase setup, SQLite-to-Postgres conversion, auth/RLS work, and environment/database cutovers.

Hard rules:

- Default target is ALWAYS non-production (local SQLite at
  `data/lotsync.db`, or the future Supabase DEV). The production
  database — `/var/data/lotsync.db` on the Render disk — is never a
  target unless the user explicitly authorizes that specific operation
  in this conversation. Absence of an explicit environment means
  non-production.
- Do not modify production database state without explicit approval.
- Do not run destructive migrations without a verified backup and rollback plan.
- Do not commit database dumps or secrets.
- Do not assume dev and production schemas match.
- Do not perform LotSync -> DealerDOH production cutover as a side effect of feature work.

Before changing schema, record target environment, branch/SHA, schema state, backup status, affected tables, data volume, and whether the change is additive, backfill, destructive, or cutover.

For SQLite -> Postgres, check syntax, `lastrowid`, booleans, datetime handling, JSON, transactions, foreign keys, collation, ordering, and pagination.

For Supabase/Postgres, check RLS, indexes, foreign keys, migration rollback/restore, server-only service role usage, public key safety, and auth/session boundaries.

Production cutover requires explicit approval and a written plan with source DB, destination DB, backup, migration command, downtime, verification queries, rollback path, post-cutover smoke tests, and env var ownership.

If any step fails, stop and report.
