# /start-task - Start DealerDOH Work

Use this workflow to begin feature, fix, chore, docs, test, or refactor work safely.

1. Understand the smallest valid scope.
2. Check repo state with branch and status.
3. Protect unrelated local changes.
4. Start normal work from updated `dev`; use `master` (this repo's production branch — auto-deploys on push) only for approved hotfix or production-baseline work.
5. Create a typed branch: `fix/<description>`, `feature/<description>`, `chore/<description>`, `docs/<description>`, `test/<description>`, or `refactor/<description>`.
6. Read `AGENTS.md`, `CLAUDE.md`, `.claude/workflows/`, `.codex/workflows/`, architecture docs, deployment docs, migration docs, and relevant code.
7. Plan briefly for non-trivial work.
8. Implement only the planned scope.
9. Run focused checks first, then broader checks based on risk.
10. Report branch, files changed, checks run, smoke status, risks, and next step.

Do not open a PR unless the user asks or invokes `/pr`.
