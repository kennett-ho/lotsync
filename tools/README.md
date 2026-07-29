# Developer Tooling

Scripts for running LotSync locally during development. None of these
change reconciliation logic, the API, or the frontend -- they only
automate the exact commands already documented in
[`README.md`](../README.md) ("Running LotSync") and
[`api/README.md`](../api/README.md).

Windows PowerShell only (this project develops on Windows). Written
against Windows PowerShell 5.1 for portability across machines that
haven't installed PowerShell 7.

## Files

| File | Purpose |
|---|---|
| [`../Launch LotSync.bat`](../Launch%20LotSync.bat) | Double-click entry point. Runs `launch.ps1`. |
| `launch.ps1` | Verifies tooling, installs missing dependencies, stops any previous session, starts backend + frontend, waits for both, opens the browser. |
| `stop.ps1` | Stops whatever `launch.ps1` started. Safe to run any time, including when nothing is running. |
| `doctor.ps1` | Read-only environment/status check. Run this first when something's wrong. |
| `update.ps1` | `git pull --ff-only` (refuses if the working tree is dirty), then re-syncs backend + frontend dependencies. Does not start/stop servers. |
| `common.ps1` | Shared functions the four scripts above dot-source. Not run directly. |

## Usage

```
tools\launch.ps1              # start everything
tools\launch.ps1 -SkipDeps    # fast relaunch, skip dependency checks
tools\launch.ps1 -NoBrowser   # don't auto-open a browser tab
tools\stop.ps1                # stop backend + frontend
tools\doctor.ps1              # check environment without changing anything
tools\update.ps1              # git pull + re-sync dependencies
```

Or just double-click **Launch LotSync.bat** at the repo root.

## How process tracking works

`launch.ps1` writes a small generated wrapper script per process to
`tools\.state\run-backend.ps1` / `run-frontend.ps1` (gitignored, not
committed), starts it in its own PowerShell window, and records the
resulting PID plus that wrapper script's path in
`tools\.state\backend.pid` / `frontend.pid`.

`stop.ps1` (and `launch.ps1`'s own pre-start cleanup) only ever stops a
PID if it's both (a) tracked in one of those `.pid` files and (b) its
live command line still references that same wrapper script path. If a
PID was reused by something unrelated since the last run, it's left
alone and reported as a mismatch rather than killed. **This tooling
never does a blanket "kill all python" / "kill all node".**

Logs for each process are tee'd to `tools\.state\backend.log` /
`frontend.log` as well as shown live in each process's own window.

## Ports

Backend defaults to `127.0.0.1:8000`, frontend to `localhost:8443`
(matching `vite.config.ts`'s own default). Override with environment
variables before running `launch.ps1`, following the same `LOTSYNC_*`
convention already used elsewhere in this project
(`LOTSYNC_OUT_DIR`, `LOTSYNC_CORS_ORIGINS`, etc.):

```
$env:LOTSYNC_BACKEND_HOST = "127.0.0.1"
$env:LOTSYNC_BACKEND_PORT = "8000"
$env:LOTSYNC_FRONTEND_PORT = "8443"
```

## Known gaps this tooling surfaced (not fixed here, on purpose)

Building this tooling required actually running the documented startup
commands end-to-end, which surfaced a pre-existing gap worth a
deliberate decision rather than a silent fix buried in a tooling PR:

- **`requirements.txt` didn't exist before this.** `.venv` had
  `fastapi` / `uvicorn` / `httpx` installed but was missing `pandas`,
  `openpyxl`, and `python-multipart` -- all three are real runtime
  dependencies (`config/settings.py` reads `oms_config.xlsx` via
  `pandas.read_excel`, which needs `openpyxl`; the inventory-sync
  upload route needs `python-multipart`). Separately, a *different*,
  non-project Python install on this machine had `pandas`/`openpyxl`
  installed globally, which is presumably how the CLI workflow (
  `python3 reconcile.py`) had been running. `requirements.txt` (repo
  root) now lists the actual dependency set in one place; `doctor.ps1`
  and `launch.ps1` check/install against it.

## npm vs. pnpm: an intentional split, not an oversight

`frontend/` has both `package-lock.json` and `pnpm-lock.yaml`. This is
deliberate, not stale cruft:

- **Local development uses npm.** This tooling, `README.md`, and
  `api/README.md` all standardize on `npm install` / `npm run dev`.
  `package-lock.json` is the lockfile that matters for local dev.
- **Figma Make's hosted dev-container/deploy pipeline uses pnpm.**
  `frontend/.figma/make/{dev,install,format,langserver,deploy,deploy-preview}`
  are six tracked scripts Figma Make's platform invokes directly, and
  every one of them calls `pnpm` (`pnpm install --prefer-offline
  --no-frozen-lockfile`, `pnpm run dev`, `pnpm run build`, etc.).
  `frontend/.figma/make/dev.json` explicitly watches `pnpm-lock.yaml`
  to know when to reinstall. `frontend/.mise.toml`'s `pnpm = "10.34.3"`
  pin exists so that hosted container has a pinned version to run
  those scripts with.

Deleting `pnpm-lock.yaml` or the `.mise.toml` pnpm pin would not
affect local dev (npm ignores both), but would destabilize Figma
Make's hosted pipeline -- an environment this tooling can't run or
test against. Both were deliberately left in place for that reason.
If Figma Make integration is ever dropped, `pnpm-lock.yaml`,
`frontend/.mise.toml`'s pnpm pin, and `frontend/.figma/make/*` should
be removed/rewritten together, not piecemeal.
