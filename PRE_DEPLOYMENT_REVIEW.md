# LotSync v0.8.0 — Friday MVP Production Readiness Review

**Reviewer role:** Final pre-deployment engineering review (not a feature review, not a refactor).
**Scope:** Repository as of `cd2f384` (Friday Demo Build) plus the four uncommitted files in the working tree (`api/routers/vehicles.py`, `queries/vehicles.py`, and their tests — reviewed, low-risk, see Appendix).
**Method:** Direct source review of every backend route/router, the repository/persistence layer, upload/validation path, dev launch tooling, and the frontend's API integration layer; one full local test-suite run (358/358 passing); one empirical reproduction of the path-traversal finding below.

**Deployment model, confirmed from source:** LotSync is not deployed to a server — it runs on a Windows machine at the dealership (or the demo machine), started by double-clicking `Launch LotSync.bat`, which launches `uvicorn` (backend, `127.0.0.1:8000`) and `vite dev` (frontend, `0.0.0.0:8443`) as local processes. This framing matters: several things that would be "hardcoded localhost" bugs in a cloud-deployed app are *correct by design* here. Findings below are filtered accordingly — flagged only where they'd cause a real problem in *this* deployment model.

---

## 1. Deployment Risks

| # | Finding | Evidence |
|---|---|---|
| D1 | **Upload endpoint writes attacker-controlled filenames to disk with no sanitization** — see Security §S1 (cross-listed, it's also the top deployment blocker). | `api/routers/inventory_sync.py:71` |
| D2 | CORS origin allowlist is a static list of exactly four dev-port origins (`localhost`/`127.0.0.1` on `5173`/`8443`, `LOTSYNC_CORS_ORIGINS` env var to override). If port `8443` or `8000` is already taken on the demo machine and the launcher falls back / is manually run on different ports, every API call fails with a generic "Could not reach the LotSync API" message — nothing in that message hints that the real cause is CORS, not the backend being down. | `api/app.py:40-51`, `tools/common.ps1:91-98` (hardcoded defaults `8000`/`8443`) |
| D3 | No `.env.example` (backend or frontend) enumerating the ~7 environment variables a real deployment would touch: `LOTSYNC_DB_PATH`, `LOTSYNC_CONFIG_PATH`, `LOTSYNC_UPLOADS_DIR`, `LOTSYNC_API_UPLOADS_DIR`, `LOTSYNC_OUT_DIR`, `LOTSYNC_CORS_ORIGINS`, `VITE_API_BASE_URL`. Each is documented individually in a docstring/README paragraph, but there's no single checklist for "what do I set to run this on a different machine." | confirmed via `find . -name ".env*"` — none exist |
| D4 | `uvicorn ... --reload` (a development convenience flag — file-watcher, auto-restart-on-save) is the *only* backend launch path that exists; there is no production-mode invocation anywhere in the repo. | `tools/launch.ps1:137` |
| D5 | `data/api_uploads/` accumulates one new timestamped subfolder per sync run, forever — no retention policy or cleanup. Same for orphaned batches from failed uploads (see R3). Not urgent for one demo, but real if this machine runs syncs daily. | `api/routers/inventory_sync.py:66-67`, `.gitignore` confirms these are runtime-only, never pruned |
| D6 | SQLite is the only datastore, single file, default rollback-journal mode (no WAL, no `busy_timeout`). Fine at this scale; flagged jointly with Reliability R1 below since it's the same root cause. | `database/repository.py:85-87` |

**Not a finding, confirmed correct:** every filesystem path (`DEFAULT_DB_PATH`, `CONFIG_PATH`, `UPLOADS_DIR`, `OUT_DIR`) is repo-relative with an env-var override, and the code comments explicitly note these were *already* fixed from hardcoded sandbox paths (`/mnt/user-data/...`) in an earlier pass. No secrets or credentials found anywhere in tracked files or `.claude/settings.local.json`.

---

## 2. Reliability

| # | Finding | Evidence |
|---|---|---|
| R1 | **No `busy_timeout` set on the SQLite connection.** `connect()` opens with defaults; if two requests attempt a write at the same moment (e.g., someone double-clicks "Run Sync Now," or a sync is running while another browser tab loads a page that happens to write), SQLite raises `database is locked` immediately rather than waiting/retrying. FastAPI would surface this as a raw 500 to the browser. | `database/repository.py:85` |
| R2 | **Silent default-configuration fallback, confirmed live.** Running the test suite with no `oms_config.xlsx` present produced: `WARNING: ...oms_config.xlsx not found -- using default settings (store_name='Mark Kia', sync_date=today)` for every settings/bucket loader. This print goes to the **backend terminal only** — nothing surfaces it to the browser. If the demo machine's `oms_config.xlsx` is missing, in the wrong path, or simply not the dealership's real file, Inventory Sync will silently run against `store_name='Mark Kia'` and generic bucket thresholds, producing plausible-looking but wrong results with zero on-screen indication anything defaulted. | `config/settings.py:36-42`; reproduced via `python -m unittest discover` output |
| R3 | Uploaded files are written to disk **before** `validate_upload()` runs. A rejected upload (wrong file in wrong slot — the single most likely user error) still leaves its batch directory and partial file(s) on disk permanently; nothing cleans these up on the validation-failure path. | `api/routers/inventory_sync.py:69-83` |
| R4 | **No upload size limit.** `await upload.read()` loads the entire file into memory in one call, synchronously, with no cap. The Sold report is documented elsewhere in this repo as running to ~34K rows for a full historical pull — not huge, but there is no guard against a much larger or corrupted file stalling or exhausting memory on the single request thread. | `api/routers/inventory_sync.py:73` |
| R5 | **Task/recommendation counts can be misattributed under concurrent syncs.** `run_inventory_sync` computes `tasks_generated` as `COUNT(*) after − COUNT(*) before`, not scoped to the current run's own writes. If a second sync (or another concurrent write) lands between the "before" and "after" reads, the summary shown to the user attributes someone else's writes to this run. Data itself stays correct (each row still has its own real `sync_run_id`); only the *summary numbers* can be wrong. Low likelihood in a single-operator demo, real for two people using it at once. | `sync/pipeline.py:207-208, 235-236` |

**Handled correctly, worth noting:** the `sync_run()` context manager's transaction/rollback contract is sound (verified by reading, tests pass) — a failed source's writes roll back cleanly and the `SyncRun` is marked `failed`, never partially committed. The one previously-known gap (`generate_key_out_aging_recommendations` KeyError on a columnless empty DataFrame) is already guarded (`if len(key_out_aging):`) per `sync/pipeline.py:232`.

---

## 3. Security

| # | Finding | Severity | Evidence |
|---|---|---|---|
| S1 | **Arbitrary file write via unsanitized upload filename (path traversal).** `os.path.join(batch_dir, upload.filename)` uses the client-supplied `filename` from the multipart request verbatim. Reproduced empirically: `os.path.join(r'C:\data\api_uploads\<batch>', r'C:\Windows\evil.csv')` → `'C:\\Windows\\evil.csv'` — `os.path.join` silently **discards the base directory** when the second argument is an absolute path (also true of `../../..` relative traversal). A crafted `filename` in any of the six upload fields writes attacker-controlled bytes to an arbitrary path on the host filesystem, subject only to the OS permissions of whoever runs `uvicorn`. This happens **before** `validate_upload()` ever runs. | **Critical** | `api/routers/inventory_sync.py:71`; reproduced live in this review |
| S2 | S1 is exploitable **even with the backend bound to `127.0.0.1` only** (today's default). CORS only prevents JavaScript on another origin from *reading* the response — it does not prevent the request from being *sent and executed* server-side. Any web page open in a browser on the same machine during the demo (an ad, a compromised site, a malicious link) can fire a simple cross-origin `fetch`/form POST to `http://localhost:8000/inventory-sync/run` with a crafted filename; the file write happens regardless of whether the page can read the JSON response. This is a real drive-by risk on the demo machine itself, not just a theoretical "if this were ever exposed to the network" concern. | **Critical** (same root cause as S1) | analysis of `api/app.py`'s CORS config + S1 |
| S3 | No authentication anywhere in the API — every read route and the one write route (`POST /inventory-sync/run`) are open to any client that can reach the port. This is a known, previously-made, explicit product decision (auth was deliberately descoped until "a real multi-user access surface" exists) and is a reasonable call for a single-operator localhost demo. Flagging it here only so it's an explicit, re-confirmed decision for Friday, not an oversight — and as a hard gate: **if `LOTSYNC_BACKEND_HOST` is ever changed from `127.0.0.1` (e.g., to let a tablet on the lot floor reach the API), this stops being acceptable immediately**, especially combined with S1. | High (contextual) | `api/app.py`; `tools/common.ps1:86-89` (`127.0.0.1` default, env-overridable) |
| S4 | FastAPI's interactive docs (`/docs`, `/redoc`, `/openapi.json`) are enabled by default and not disabled anywhere. Combined with S3, anyone who can reach the port gets a full, clickable UI to browse the schema and fire `POST /inventory-sync/run` directly, no client code needed. Low incremental risk beyond S3 on localhost-only, but worth an explicit call before this ever leaves a single trusted machine. | Medium | `api/app.py:27-31` — no `docs_url=None` |
| S5 | No file-type/content enforcement server-side beyond the client-side `accept=".csv"` hint (trivially bypassed — it's a browser file-picker filter only) and a post-write "does it parse as CSV with the right columns" check. Any byte content reaches disk first. | Medium | `frontend/src/dashboards/InventorySync.tsx:252`; `sync/upload_validation.py` |

SQL injection: not found. Every query in `queries/*.py`, `database/repository.py`, and every router uses parameterized `?` placeholders; the one dynamic SQL construction (`queries/vehicles.py`'s `include_sold` filter, part of the uncommitted diff) interpolates a hardcoded constant string chosen by a Python `bool`, never user input directly into SQL text.

---

## 4. Production Readiness

| # | Finding | Evidence |
|---|---|---|
| P1 | No health-check endpoint. `tools/launch.ps1`'s `Wait-ForPort` confirms the TCP port is open, not that the app is actually serving correctly (migrations applied, DB reachable). No way to detect mid-demo degradation (e.g., disk full, DB file locked by another process) other than a request failing live. | `tools/common.ps1:118-131`; `api/app.py` has no `/health` route |
| P2 | No process supervision. If `uvicorn` (or its `--reload` watcher) crashes mid-demo, nothing restarts it — the operator has to notice and re-run `Launch LotSync.bat` manually. | `tools/launch.ps1` |
| P3 | Migrations are re-checked on **every single API request**: `get_db()` → `connect()` → `apply_migrations()` runs a `glob.glob()` of the migrations directory plus a `SELECT` against `schema_migrations` on every call, not once at process startup. Harmless once schema is current (returns immediately), but wasteful, and a subtle correctness risk under concurrency: if a migration were ever genuinely pending, two simultaneous requests could both see it as pending and both attempt `executescript()`, racing on `CREATE TABLE`. Low probability (migrations are static once deployed) but worth knowing. | `database/repository.py:57-88`, `api/dependencies.py:18-23` |
| P4 | No structured application logging — only ad hoc `print()` in `config/settings.py` (see R2) and uvicorn's own access log. Sync history/errors are recoverable from the `sync_run`/`event` tables, which is reasonable, but there's no log file to hand a support person after "the demo glitched." | `config/settings.py` |
| P5 | Backup: noted, not implemented (per review scope — flagging only). SQLite is a single file (`data/lotsync.db`) with no automated backup/rotation. Worth a manual copy of the DB file before and after Friday's demo, at minimum. | `database/repository.py:23` |

---

## 5. UX Risks (dealership-manager credibility lens)

| # | Finding | Evidence |
|---|---|---|
| U1 | **The Role Switcher changes nothing except the header avatar/name.** All 8 roles (Lot Staff, Lot Manager, Tower Manager, Controller, Sales Manager, Recon Manager, Service Advisor, Detail Team) map to the identical single nav group and identical screens — `roleConfig`'s `navGroup` is `'core'` for every one of them. If a dealership manager switches to "Controller" expecting a Controller-relevant view (as the UI strongly implies — it's labeled "Switch Role"), they'll see literally nothing change. It's explicitly labeled "Prototype" in the dropdown, which helps, but a live click-through during a demo is a real risk of looking unfinished. | `frontend/src/App.tsx:25-36, 67-74` |
| U2 | 13 built dashboard screens (Controller, DealerTrades, IncomingInventory, LotStaff, LotStaffing, Placeholder, Reports, Requests, Staging, TowerManager, TradeIns, Transportation, VehicleMovement) exist in the codebase but are **not reachable from any nav item** — only Dashboard, Vehicles, Tasks, Inventory Sync, and Profile are routed. This is good discipline (no fake-data screens visible to a real user), but if the presenter or an attendee has seen an earlier mockup/screenshot with a Reports or Requests tab, its absence needs to be a deliberate talking point ("that's post-MVP"), not a surprise mid-demo. | `frontend/src/App.tsx:300-311` vs. `Glob` of `frontend/src/dashboards/*.tsx` |
| U3 | The header search placeholder reads "Search VIN, Stock #, Customer…" but the handler only accepts `^[A-Z0-9]{4,17}$` — a customer name silently does nothing on Enter (no error, no feedback, input doesn't even clear). Looks like a dead feature if tried live. | `frontend/src/App.tsx:224-235, 261` |
| U4 | The notification bell is fully static — a permanently-on red "unread" dot with no click handler at all. An audience member clicking it live gets nothing. | `frontend/src/App.tsx:287-290` |
| U5 | Reliability R2 (silent config fallback) doubles as a UX risk: a misconfigured `oms_config.xlsx` produces confident-looking but wrong data with no on-screen warning — worth a pre-demo checklist item to confirm the real file is in place, not a code fix by Friday. | see R2 |

**Handled well, worth calling out positively:** `InventorySync.tsx` is honest about backend limitations — it shows real "Backend unreachable" / "No syncs recorded yet" / "Loading…" states rather than fabricating placeholder data, and the Sprint 3.8 fix that replaced a permanently-hardcoded "Systems Healthy" header pill with one actually driven by `GET /dashboard` (visible in the code comment at `App.tsx:205-210`) is exactly the right instinct for demo credibility.

---

## 6. Code Quality (deployment-relevant only)

| # | Finding | Evidence |
|---|---|---|
| C1 | 13 orphaned frontend components (listed in U2) carry zero backend integration and are unreachable — confirmed consistent with this project's own memory of `DealerTrades.tsx` being orphaned. Real risk: someone wires one back into nav later without noticing it still has no API calls, shipping a page that looks real but is 100% static mock data. | `frontend/src/dashboards/*.tsx` |
| C2 | `GET /reports` and `GET /dashboard` are byte-identical implementations (same imports, same four function calls, same DTO) — intentional per the docstring (API_CONTRACTS.md defines no separate Reports DTO yet), but it's literal duplicated code that will need to diverge or be merged once Reports gets real content. | `api/routers/reports.py` vs. `api/routers/dashboard.py` |
| C3 | Two local SQLite files sit in `data/` (`lotsync.db`, `lotsync-temp-dev-db.db`). Both are gitignored/machine-local, not a repo problem — but worth a manual sanity check before Friday that `LOTSYNC_DB_PATH` (if set at all on the demo machine) points at the real one, not the "temp-dev" leftover. | `data/` directory listing |

---

## 7. Release Recommendation

### Critical — must fix before deployment
- **S1/D1: Sanitize/derive the upload filename server-side** — do not use client-supplied `filename` in any filesystem path. (E.g., ignore the client filename entirely and always write as `f"{source}.csv"` inside the already-random, server-generated `batch_dir` — the code already has this as a *fallback* for a missing filename at `inventory_sync.py:71`; the fix is to stop treating the client filename as trustworthy at all, not just as an optional fallback.) This is exploitable today, on the default configuration, from a browser tab that isn't even the LotSync frontend.

### High — should fix before deployment if possible
- **R2: Surface the config-fallback warning to the browser**, not just the backend console — at minimum, include a `warnings` entry in `SyncSummaryDTO` (the field already exists and is used for the Keyper-missing case) when `oms_config.xlsx` wasn't found or a sheet was missing.
- **R1: Set a SQLite `busy_timeout`** (e.g., `PRAGMA busy_timeout = 5000`) in `connect()` so a momentary write collision retries instead of surfacing a raw 500.
- **R4: Cap upload size** (FastAPI/Starlette supports a max body size; even a simple manual check against `upload.size` before the read-into-memory would close this).
- **S4: Disable `/docs`/`/redoc`/`/openapi.json`** (or explicitly accept the risk in writing) before this ever runs anywhere other than a fully trusted single machine.
- **D2: Verify the actual demo machine's ports match the CORS allowlist** before Friday — a five-minute manual check, not a code change, but worth doing given the failure mode is a confusing generic error.

### Medium — safe to defer to v0.8.1
- R3 (orphaned upload batches on validation failure), R5 (concurrent-sync count misattribution), D3 (.env.example), D4/P2 (dev-only launch path, no process supervision), D5 (unbounded `api_uploads/` growth), P1/P3 (health endpoint, per-request migration check), U1 (cosmetic role switcher — or relabel it more clearly as prototype-only in the demo script), U3/U4 (dead search-by-customer, non-functional bell).

### Low — technical debt only
- C1 (orphaned frontend screens), C2 (Reports/Dashboard duplication), C3 (stray local DB file), P4 (no structured logging), P5 (no backup automation — noted per scope, not implemented here).

---

## Appendix: the four uncommitted files

`api/routers/vehicles.py` / `queries/vehicles.py` (plus their tests) add an `include_sold` query parameter to `GET /vehicles`, defaulting to excluding sold vehicles from the active-inventory list. Reviewed directly: the SQL filter is a hardcoded string chosen by a Python `bool` (`"" if include_sold else "WHERE v.tekion_status IS NOT 'Sold'"`), never user input — no injection surface. Logic correctly uses `IS NOT 'Sold'` (not `!=`) so NULL-status vehicles (RecovR/Keyper-only matches with no Tekion record) aren't silently dropped. No concerns; safe to commit independent of the findings above.
