# Handoff Report

Use for task, QA, release, and production handoffs.

Task handoff:

- Objective.
- Branch and SHA.
- PR URL if any.
- Files changed.
- Behavior changed.
- Tests/checks run.
- Browser smoke result.
- Migration/env/deployment impact.
- Known risks.
- Next step.

QA report:

```markdown
**Fully Fixed**
- `<item>`: Evidence.

**Needs Attention**
- `<item>`: Failing behavior and reproduction.

**Partial / Not Verified**
- `<item>`: What was verified and what was not.

**Cleanup**
- Data created:
- Data removed:
- Remaining:
```

Release report:

- Release version/tag.
- Release PR.
- Included PRs/commits.
- Production deployment URLs/IDs.
- Database/migration status.
- Environment-variable changes by name and owner, not values.
- Smoke-test result.
- Rollback point.
- Follow-up work.
