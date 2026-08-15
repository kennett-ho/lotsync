# DealerDOH Agent Process

Use this file as the primary Fable/Claude project instruction for DealerDOH/LotSync work.

DealerDOH is the successor identity for the production app currently known as LotSync. Current LotSync production is a protected baseline. Mark Kia may actively rely on it.

> **Repository reality note (added at install, 2026-08-15):** in this
> repository the production branch is currently **`master`**, not
> `main` — read every `main` reference below and in
> `.claude/workflows/` as `master` until an approved, planned rename
> happens. Both Render and Vercel auto-deploy every push to `master`,
> so a push to `master` IS a production deployment. See
> `PRODUCTION_BASELINE.md`.

## Branch and Release Model

```text
feature/* or fix/*
  -> dev
  -> dev deployment and QA
  -> main
  -> production deployment
```

- `main` represents production.
- `dev` represents integrated next-release work.
- Normal work happens on task branches.
- Merge to `dev` requires explicit user approval.
- Production release requires explicit production-release approval.
- Do not rename production, migrate production data, change production env vars, or restructure deployment as a side effect of normal feature work.

## Workflow Files

Use `.claude/workflows/`:

- `start-task.md`
- `pr.md`
- `review-comments.md`
- `merge-dev.md`
- `release-readiness.md`
- `release-train.md`
- `verification.md`
- `smoke-test.md`
- `data-migration.md`
- `production-smoke.md`
- `handoff-report.md`
- `specialists.md`

## Core Rules

- Read governing docs before editing: `AGENTS.md`, `CLAUDE.md`, `.claude/workflows/`, `.codex/workflows/`, architecture docs, deployment docs, and relevant code.
- Keep edits scoped to the planned task.
- Protect unrelated local changes.
- Stage specific files only. Do not use broad add commands.
- Do not blindly implement AI review comments; verify each one against code.
- Never print secrets.
- If production workflow fails, stop and report. Do not bypass checks or manually patch production.
