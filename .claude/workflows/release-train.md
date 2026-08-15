# /release-train - Release Dev to Production (`master`)

Requires explicit production-release approval.

Repo reality: this repository's production branch is `master`, not
`main` (rename deferred; see `PRODUCTION_BASELINE.md`). Merging to
`master` IS the production deployment — Render and Vercel auto-deploy
every push to it; there is no separate deploy step or intermediate
gate. Production is locked at `v1.0.0-beta.6` until this workflow,
explicitly approved, moves it.

Failure policy: if anything fails, diagnose and stop. Do not bypass checks, force-push, use no-verify, manually patch production data, or retry risky steps without approval.

1. Confirm explicit production approval.
2. Record current production baseline: tag/version, `master` SHA, deployments, database, backup status (start from `PRODUCTION_BASELINE.md`).
3. Run release readiness.
4. Update `dev`.
5. Create or reuse release PR from `dev` to `master`.
6. Include release summary, PRs/commits, tests, smoke checks, migration/env notes, and rollback plan.
7. Monitor checks.
8. Verify mergeability.
9. Merge to `master` with a merge commit — this is the moment production deploys.
10. Tag version if repo practice uses tags and version is clear.
11. Back-merge `master` to `dev`.
12. Run production smoke after deployment.
13. Produce handoff report.
