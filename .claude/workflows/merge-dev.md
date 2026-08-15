# /merge-dev - Verify PR and Merge to Dev

Requires explicit user approval.

1. Find the PR.
2. Confirm base is `dev`.
3. Confirm PR is open and not already merged.
4. Monitor checks until green.
5. Verify mergeability.
6. Resolve conflicts if needed, then rerun tests/checks.
7. Re-fetch PR comments, reviews, and unresolved threads.
8. Address valid findings.
9. After final green checks, wait 3-5 minutes and re-fetch feedback.
10. Merge with a merge commit unless repo policy says otherwise.
11. Pull latest `dev`.
12. Report changed backend/API files, frontend files, migrations, env/deployment config, and expected dev deployment.
