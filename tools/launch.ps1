<#
.SYNOPSIS
    Starts LotSync end-to-end: verifies tooling, installs missing
    dependencies, stops any previous LotSync backend/frontend this
    tooling started, starts both fresh, waits for them to come up, and
    opens the browser.

.DESCRIPTION
    Safe to run repeatedly (e.g. double-clicking "Launch LotSync.bat"
    several times a day). It only ever stops processes it previously
    started itself -- see Stop-TrackedProcess in common.ps1 -- so it
    will not touch unrelated python.exe / node.exe processes on your
    machine.

.PARAMETER SkipDeps
    Skip the dependency-install checks (backend venv / frontend
    node_modules). Useful for a fast relaunch when you know nothing
    changed.

.PARAMETER NoBrowser
    Don't open a browser tab once the frontend is up.
#>
param(
    [switch]$SkipDeps,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$RepoRoot = Get-RepoRoot
Assert-RepoLayout -RepoRoot $RepoRoot

Write-Host ""
Write-Host "=== LotSync Developer Launcher ===" -ForegroundColor Magenta
Write-Info "Repo root: $RepoRoot"
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Verify toolchain
# ---------------------------------------------------------------------------
Write-Step "Checking required tools ..."

$pythonCmd = Get-PythonCommand
if (-not $pythonCmd) {
    Write-ErrMsg "No usable Python found on PATH ('python' or 'py')."
    Write-Info "Install Python 3.11+ from https://python.org and re-run."
    exit 1
}
Write-Ok "Python: $(Get-CommandOutputText -FilePath $pythonCmd -ArgumentList @('--version'))"

if (-not (Test-CommandAvailable "node")) {
    Write-ErrMsg "Node.js not found on PATH."
    Write-Info "Install Node.js from https://nodejs.org and re-run."
    exit 1
}
Write-Ok "Node: $(node --version)"

if (-not (Test-CommandAvailable "npm")) {
    Write-ErrMsg "npm not found on PATH (usually ships with Node.js)."
    exit 1
}
Write-Ok "npm: $(npm --version)"

if (Test-CommandAvailable "git") {
    Write-Ok "git: $(git --version)"
} else {
    Write-WarnMsg "git not found on PATH -- not required to run LotSync, but tools/update.ps1 needs it."
}

Write-Host ""

# ---------------------------------------------------------------------------
# 2. Dependencies
# ---------------------------------------------------------------------------
$venvPython = Ensure-Venv -RepoRoot $RepoRoot -PythonCmd $pythonCmd
$frontendDir = Join-Path $RepoRoot "frontend"

if ($SkipDeps) {
    Write-WarnMsg "Skipping dependency checks (-SkipDeps)."
} else {
    Write-Step "Checking backend dependencies ..."
    Ensure-BackendDeps -RepoRoot $RepoRoot -VenvPython $venvPython

    Write-Step "Checking frontend dependencies ..."
    Ensure-FrontendDeps -FrontendDir $frontendDir
}
Write-Host ""

# ---------------------------------------------------------------------------
# 3. Stop any previous LotSync processes this tooling started
# ---------------------------------------------------------------------------
Write-Step "Checking for a previous LotSync session ..."
$backendStopResult = Stop-TrackedProcess -RepoRoot $RepoRoot -Name "backend"
$frontendStopResult = Stop-TrackedProcess -RepoRoot $RepoRoot -Name "frontend"

foreach ($pair in @(@("backend", $backendStopResult), @("frontend", $frontendStopResult))) {
    $name = $pair[0]; $result = $pair[1]
    switch ($result) {
        "stopped"             { Write-Ok "Stopped previous $name process." }
        "not-running"         { Write-Info "No running $name process from a previous session." }
        "not-tracked"         { Write-Info "No previous $name session tracked." }
        "signature-mismatch"  { Write-WarnMsg "Previous $name PID was reused by an unrelated process -- left it alone." }
    }
}
Write-Host ""

# ---------------------------------------------------------------------------
# 4. Confirm ports are actually free before starting
# ---------------------------------------------------------------------------
$backendHostName = Get-BackendHostName
$backendPort = Get-BackendPort
$frontendPort = Get-FrontendPort

if (Test-TcpPort -HostName $backendHostName -Port $backendPort) {
    Write-ErrMsg "Port $backendPort is already in use by something this tooling didn't start."
    Write-Info "Free it manually, or set `$env:LOTSYNC_BACKEND_PORT to use a different port."
    exit 1
}
if (Test-TcpPort -HostName "127.0.0.1" -Port $frontendPort) {
    Write-ErrMsg "Port $frontendPort is already in use by something this tooling didn't start."
    Write-Info "Free it manually, or set `$env:LOTSYNC_FRONTEND_PORT to use a different port."
    exit 1
}

# ---------------------------------------------------------------------------
# 5. Start backend
# ---------------------------------------------------------------------------
$stateDir = Get-StateDir -RepoRoot $RepoRoot
$backendLog = Join-Path $stateDir "backend.log"
$backendRunScript = Join-Path $stateDir "run-backend.ps1"

@"
`$host.UI.RawUI.WindowTitle = 'LotSync Backend'
Set-Location '$RepoRoot'
`$env:PYTHONPATH = '..'
& '$venvPython' -m uvicorn lotsync.api.app:app --reload --host $backendHostName --port $backendPort 2>&1 | Tee-Object -FilePath '$backendLog'
"@ | Set-Content -Path $backendRunScript -Encoding UTF8

Write-Step "Starting backend (FastAPI/uvicorn) on http://$backendHostName`:$backendPort ..."
$backendProc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $backendRunScript) `
    -WindowStyle Normal -PassThru
Save-TrackedProcess -RepoRoot $RepoRoot -Name "backend" -ProcessId $backendProc.Id -RunScriptPath $backendRunScript

if (-not (Wait-ForPort -HostName $backendHostName -Port $backendPort -Label "backend" -TimeoutSeconds 30)) {
    Write-ErrMsg "Backend did not come up within 30s. Last log lines:"
    if (Test-Path $backendLog) { Get-Content $backendLog -Tail 20 | ForEach-Object { Write-Host "     $_" } }
    Write-Info "The backend window is still open -- check it directly, then run tools\stop.ps1 when done."
    exit 1
}
Write-Ok "Backend is up."
Write-Host ""

# ---------------------------------------------------------------------------
# 6. Start frontend
# ---------------------------------------------------------------------------
$frontendLog = Join-Path $stateDir "frontend.log"
$frontendRunScript = Join-Path $stateDir "run-frontend.ps1"

@"
`$host.UI.RawUI.WindowTitle = 'LotSync Frontend'
Set-Location '$frontendDir'
`$env:PORT = '$frontendPort'
npm run dev 2>&1 | Tee-Object -FilePath '$frontendLog'
"@ | Set-Content -Path $frontendRunScript -Encoding UTF8

Write-Step "Starting frontend (Vite) on http://localhost:$frontendPort ..."
$frontendProc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList @("-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $frontendRunScript) `
    -WindowStyle Normal -PassThru
Save-TrackedProcess -RepoRoot $RepoRoot -Name "frontend" -ProcessId $frontendProc.Id -RunScriptPath $frontendRunScript

if (-not (Wait-ForPort -HostName "127.0.0.1" -Port $frontendPort -Label "frontend" -TimeoutSeconds 45)) {
    Write-ErrMsg "Frontend did not come up within 45s. Last log lines:"
    if (Test-Path $frontendLog) { Get-Content $frontendLog -Tail 20 | ForEach-Object { Write-Host "     $_" } }
    Write-Info "The backend is still running. The frontend window is still open -- check it directly."
    exit 1
}
Write-Ok "Frontend is up."
Write-Host ""

# ---------------------------------------------------------------------------
# 7. Open browser + summary
# ---------------------------------------------------------------------------
$frontendUrl = "http://localhost:$frontendPort"
$backendUrl = "http://$backendHostName`:$backendPort"

if (-not $NoBrowser) {
    Start-Process $frontendUrl
}

Write-Host "=== LotSync is running ===" -ForegroundColor Magenta
Write-Host ("  {0,-10} {1}" -f "Frontend:", $frontendUrl)
Write-Host ("  {0,-10} {1}" -f "Backend:", $backendUrl)
Write-Host ("  {0,-10} {1}/docs" -f "API docs:", $backendUrl)
Write-Host ""
Write-Host ("  {0,-10} {1}" -f "Logs:", $stateDir)
Write-Host ("  {0,-10} tools\stop.ps1" -f "Stop:")
Write-Host ""
