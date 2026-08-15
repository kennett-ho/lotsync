# /release-readiness - Decide Whether Dev Can Release

Return `Ready for production train`, `Not ready`, or `Ready with explicit caveats`.

Check:

1. `master` still represents production (this repo's production branch is `master`, not `main`; see `PRODUCTION_BASELINE.md`).
2. Current production tag/SHA/deployment are known (baseline: `PRODUCTION_BASELINE.md`; locked at `v1.0.0-beta.6` / `13c4f815` until a release train moves it).
3. `dev` contains only intended release work.
4. CI is green.
5. Dev deployment completed.
6. Dev smoke-test evidence is current.
7. Migrations are understood and tested.
8. Environment changes are documented by name and owner, not values.
9. Production backup/rollback plan exists when data changes.
10. Review comments and blockers are resolved.
11. Release notes are accurate.

Do not merge or deploy from this workflow.
