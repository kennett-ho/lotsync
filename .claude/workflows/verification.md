# Verification - Evidence-Based Done

Done means current evidence from the current head SHA.

1. Confirm branch and SHA.
2. Review diff against `origin/dev`.
3. Map changed files to tests and smoke paths.
4. Run focused checks first.
5. Broaden based on blast radius.

This repo's actual checks (there is no pytest, no frontend test
runner, and no lint script today — CI runs exactly the first and third
commands below):

```bash
# Backend suite (385 tests), from the repo root:
PYTHONPATH=.. python -m unittest discover -s tests -p "test_*.py"

# Single test module:
PYTHONPATH=.. python -m unittest tests.test_work_order

# Frontend production build, from frontend/:
npm run build
```

Backend/API changes must verify route behavior, database failure handling, sync/import behavior, and error surfacing.

Frontend changes must verify rendering, loading/empty/error states, navigation, and browser behavior.

Data changes require migration tests or dry-run evidence.

Report checks run, result, untested areas, risks, and next step.
