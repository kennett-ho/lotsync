# /pr - Commit, Push, Open PR, Monitor Checks

Follow in order. Do not merge.

1. Confirm current branch is not `dev` or `master` (`master` is production in this repo and auto-deploys on push; read any `main` reference as `master` until an approved rename).
2. Confirm the branch has not already been merged.
3. Review diff against `origin/dev`.
4. Run the specialist checklist.
5. Run focused tests and relevant broad checks.
6. Run browser smoke if UI changed.
7. Stage specific files only.
8. Commit with a descriptive message.
9. Push the branch.
10. Create a PR against `dev`.
11. Monitor checks.
12. If checks fail, diagnose, fix, commit, push, and re-monitor.
13. Report PR URL, branch, SHA, checks, smoke status, and next step.

PR body must include summary, test plan, smoke status if applicable, migration/env/deployment notes, and deferred work.
