# Smoke Test - Local or Dev Browser Verification

Use for local, preview, or dev browser checks. Use production smoke for production.

Repo reality: no dev deployment exists yet (Sprint 02 will create
`dev.dealerdoh.com`). Until then the ONLY non-production target is the
local stack (`tools/launch.ps1` / `Launch LotSync.bat` — backend on
localhost, frontend on the Vite dev port). The production URLs —
`https://lotsync-nu.vercel.app` and `https://lotsync-api.onrender.com`
— are NEVER a smoke-test target for this workflow; production checks go
through `/production-smoke` only.

1. Confirm target environment and URL.
2. Confirm branch/SHA/deployment if available.
3. Use existing authenticated sessions when available.
4. Never print secrets.
5. Verify core paths:
   - login or dev-auth,
   - dashboard,
   - inventory list,
   - vehicle detail,
   - sync/status,
   - task/work queue,
   - RecovR/key/MDD/RapidRecon views if present,
   - printable work order/PDF if safe,
   - search/filter/sort.
6. For changed flows, verify URL, visible state, and data result after each action.
7. Check console/network errors when tooling allows it.
8. Report environment, flows tested, pass/fail evidence, bugs, data created, and cleanup status.

On dev, prefer synthetic dealership data. Do not use production as a test sandbox.
