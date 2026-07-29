<#
.SYNOPSIS
    Shared helpers for LotSync's developer tooling (launch.ps1, stop.ps1,
    doctor.ps1, update.ps1). Dot-sourced, never run directly.

    Windows PowerShell 5.1 compatible on purpose -- no ternary/null-coalescing
    operators, no pipeline chain operators. See PowerShell tool notes in this
    repo's tooling docs if you're editing this file.
#>

# ---------------------------------------------------------------------------
# Console output
# ---------------------------------------------------------------------------

function Write-Step {
    param([string]$Message)
    Write-Host ">> $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "   $Message" -ForegroundColor Gray
}

function Write-Ok {
    param([string]$Message)
    Write-Host "   [OK] $Message" -ForegroundColor Green
}

function Write-WarnMsg {
    param([string]$Message)
    Write-Host "   [WARN] $Message" -ForegroundColor Yellow
}

function Write-ErrMsg {
    param([string]$Message)
    Write-Host "   [FAIL] $Message" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# Repository / layout
# ---------------------------------------------------------------------------

# tools/common.ps1 always lives at <repo root>/tools -- $PSScriptRoot here
# reflects THIS file's directory even when dot-sourced from another script.
function Get-RepoRoot {
    Split-Path $PSScriptRoot -Parent
}

# The backend is imported everywhere as `lotsync.*` (see main.py, api/app.py)
# with PYTHONPATH pointed at the repo root's PARENT directory (README.md /
# api/README.md / tests/README.md all document this convention). That only
# resolves if the repo root directory is literally named "lotsync". This is
# a real fragility in how the project is packaged today -- not something
# this tooling should silently paper over (e.g. by symlinking or mutating
# sys.path), since that would hide behavior the documented commands don't
# have. If this check fails, the fix is to rename/clone the repo into a
# folder named "lotsync", not to change this script.
function Assert-RepoLayout {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)

    $leaf = Split-Path $RepoRoot -Leaf
    if ($leaf -ne "lotsync") {
        throw "Repo root is named '$leaf', not 'lotsync'. The backend is " + `
              "imported as the 'lotsync' package with PYTHONPATH pointed " + `
              "at this directory's parent (see README.md's 'Running " + `
              "LotSync' section) -- that only works if this folder is " + `
              "named exactly 'lotsync'. Rename the folder (or re-clone " + `
              "into one named 'lotsync') and re-run."
    }
}

function Get-StateDir {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $stateDir = Join-Path (Join-Path $RepoRoot "tools") ".state"
    if (-not (Test-Path $stateDir)) {
        New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    }
    $stateDir
}

# ---------------------------------------------------------------------------
# Ports
# ---------------------------------------------------------------------------

function Get-BackendHostName {
    if ($env:LOTSYNC_BACKEND_HOST) { return $env:LOTSYNC_BACKEND_HOST }
    "127.0.0.1"
}

function Get-BackendPort {
    if ($env:LOTSYNC_BACKEND_PORT) { return [int]$env:LOTSYNC_BACKEND_PORT }
    8000
}

function Get-FrontendPort {
    if ($env:LOTSYNC_FRONTEND_PORT) { return [int]$env:LOTSYNC_FRONTEND_PORT }
    8443
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][int]$Port
    )
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $task = $client.ConnectAsync($HostName, $Port)
        $completed = $task.Wait(500)
        return ($completed -and $client.Connected)
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Wait-ForPort {
    param(
        [Parameter(Mandatory = $true)][string]$HostName,
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][string]$Label,
        [int]$TimeoutSeconds = 30
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    Write-Info "Waiting for $Label at $HostName`:$Port ..."
    while ((Get-Date) -lt $deadline) {
        if (Test-TcpPort -HostName $HostName -Port $Port) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# ---------------------------------------------------------------------------
# Environment tool checks (read-only)
# ---------------------------------------------------------------------------

function Test-CommandAvailable {
    param([Parameter(Mandatory = $true)][string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

# ---------------------------------------------------------------------------
# Native command helpers
# ---------------------------------------------------------------------------
#
# Neither helper below relies on the caller's script-scope
# $ErrorActionPreference: under "Stop" (set by launch.ps1 / update.ps1),
# redirecting a native command's stderr -- even just to merge it or send it
# to $null -- makes PowerShell 5.1 wrap each stderr line into an ErrorRecord
# and throw, regardless of exit code. Confirmed by direct testing against
# the real Microsoft Store Python alias stub (writes to stderr, exits 9009):
# under EAP=Stop, `& python --version 2>&1` throws a terminating
# RemoteException instead of just producing a non-zero exit code -- which
# would crash launch.ps1/update.ps1 on exactly the machines (no real Python
# installed, only the Store stub on PATH) this tooling is supposed to
# gracefully detect and report.

# Runs a native executable with its output discarded and returns its exit code.
function Invoke-Quiet {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $FilePath @ArgumentList *> $null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

# Runs a native executable and returns its combined stdout+stderr as text
# (trimmed), plus sets $LASTEXITCODE as usual -- for callers that need the
# actual output (e.g. a version string), not just success/failure.
function Get-CommandOutputText {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$ArgumentList = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $out = & $FilePath @ArgumentList 2>&1
    } finally {
        $ErrorActionPreference = $prevEap
    }
    ($out | Out-String).Trim()
}

function Get-PythonCommand {
    # Prefer `python`; some Windows setups only expose `py`. See the
    # "Native command helpers" comment above for why Get-CommandOutputText
    # (not a bare `2>&1`) is required here.
    if (Test-CommandAvailable "python") {
        $v = Get-CommandOutputText -FilePath "python" -ArgumentList @("--version")
        if ($LASTEXITCODE -eq 0 -and $v -notmatch "Microsoft Store") {
            return "python"
        }
    }
    if (Test-CommandAvailable "py") {
        return "py"
    }
    return $null
}

# ---------------------------------------------------------------------------
# Dependency installation (backend venv + frontend node_modules)
# ---------------------------------------------------------------------------

function Ensure-Venv {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$PythonCmd
    )
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Step "Creating virtual environment at .venv ..."
        & $PythonCmd -m venv (Join-Path $RepoRoot ".venv")
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment with '$PythonCmd -m venv'."
        }
        Write-Ok "Virtual environment created."
    }
    $venvPython
}

# Checks the venv can actually import every package requirements.txt lists,
# rather than diffing `pip freeze` -- cheaper and catches the case that
# actually bit this project (packages simply missing from .venv).
function Test-BackendDepsSatisfied {
    param([Parameter(Mandatory = $true)][string]$VenvPython)
    $probe = "import fastapi, uvicorn, multipart, pandas, openpyxl, httpx"
    $exitCode = Invoke-Quiet -FilePath $VenvPython -ArgumentList @("-c", $probe)
    return ($exitCode -eq 0)
}

function Ensure-BackendDeps {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$VenvPython,
        [switch]$Force
    )
    if ((-not $Force) -and (Test-BackendDepsSatisfied -VenvPython $VenvPython)) {
        Write-Ok "Backend dependencies already satisfied."
        return
    }
    $reqFile = Join-Path $RepoRoot "requirements.txt"
    Write-Step "Installing backend dependencies from requirements.txt ..."
    & $VenvPython -m pip install --quiet --upgrade pip
    & $VenvPython -m pip install --quiet -r $reqFile
    if ($LASTEXITCODE -ne 0) {
        throw "pip install -r requirements.txt failed. Re-run with 'python -m pip install -r requirements.txt' (using .venv's python) to see full output."
    }
    if (-not (Test-BackendDepsSatisfied -VenvPython $VenvPython)) {
        throw "Backend dependencies still not importable after install. Check the pip output above."
    }
    Write-Ok "Backend dependencies installed."
}

function Test-FrontendDepsSatisfied {
    param([Parameter(Mandatory = $true)][string]$FrontendDir)
    Test-Path (Join-Path $FrontendDir "node_modules\.package-lock.json")
}

function Ensure-FrontendDeps {
    param(
        [Parameter(Mandatory = $true)][string]$FrontendDir,
        [switch]$Force
    )
    if ((-not $Force) -and (Test-FrontendDepsSatisfied -FrontendDir $FrontendDir)) {
        Write-Ok "Frontend dependencies already satisfied."
        return
    }
    Write-Step "Installing frontend dependencies (npm install) ..."
    Push-Location $FrontendDir
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) {
            throw "npm install failed in $FrontendDir."
        }
    } finally {
        Pop-Location
    }
    Write-Ok "Frontend dependencies installed."
}

# ---------------------------------------------------------------------------
# Process tracking (used to start/stop only what this tooling started)
# ---------------------------------------------------------------------------

# Each tracked process gets a small generated wrapper script under
# tools/.state/ (run-<name>.ps1) that it was launched with. That wrapper's
# full path is unique to this tooling, so matching a live process's
# CommandLine against it is a safe way to confirm "this PID is one we
# started" before touching it -- protects unrelated python.exe / node.exe
# processes even if a PID happens to be reused after the tracked process
# already exited.
function Save-TrackedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [Parameter(Mandatory = $true)][string]$RunScriptPath
    )
    $stateDir = Get-StateDir -RepoRoot $RepoRoot
    $info = [ordered]@{
        Pid           = $ProcessId
        RunScriptPath = $RunScriptPath
        StartedAt     = (Get-Date).ToString("o")
    }
    $info | ConvertTo-Json | Set-Content -Path (Join-Path $stateDir "$Name.pid") -Encoding UTF8
}

function Get-TrackedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $stateDir = Get-StateDir -RepoRoot $RepoRoot
    $pidFile = Join-Path $stateDir "$Name.pid"
    if (-not (Test-Path $pidFile)) { return $null }
    try {
        Get-Content $pidFile -Raw | ConvertFrom-Json
    } catch {
        $null
    }
}

function Remove-TrackedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $stateDir = Get-StateDir -RepoRoot $RepoRoot
    $pidFile = Join-Path $stateDir "$Name.pid"
    if (Test-Path $pidFile) { Remove-Item $pidFile -Force }
    $runScript = Join-Path $stateDir "run-$Name.ps1"
    if (Test-Path $runScript) { Remove-Item $runScript -Force }
}

# Stops a tracked process gracefully (taskkill without /F, which lets a
# console app clean up) and escalates to a forced kill only if it's still
# alive after a short grace period. Returns one of:
#   "stopped"    -- was running and tracked by us; stopped it
#   "not-running" -- pid file existed but the process was already gone
#   "not-tracked" -- no pid file at all
#   "signature-mismatch" -- pid file's PID is alive but is NOT the process
#                           we started (stale/reused PID) -- left untouched
function Stop-TrackedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$Name,
        [int]$GraceSeconds = 6
    )
    $info = Get-TrackedProcess -RepoRoot $RepoRoot -Name $Name
    if (-not $info) { return "not-tracked" }

    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($info.Pid)" -ErrorAction SilentlyContinue
    if (-not $proc) {
        Remove-TrackedProcess -RepoRoot $RepoRoot -Name $Name
        return "not-running"
    }

    if ($proc.CommandLine -notlike "*$($info.RunScriptPath)*") {
        # PID was reused by something unrelated since we last ran -- do not touch it.
        Remove-TrackedProcess -RepoRoot $RepoRoot -Name $Name
        return "signature-mismatch"
    }

    # Polite attempt first (lets the console app run its shutdown handlers).
    Invoke-Quiet -FilePath "taskkill" -ArgumentList @("/PID", $info.Pid, "/T") | Out-Null

    $deadline = (Get-Date).AddSeconds($GraceSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-CimInstance Win32_Process -Filter "ProcessId=$($info.Pid)" -ErrorAction SilentlyContinue)) {
            break
        }
        Start-Sleep -Milliseconds 400
    }

    # Escalate if it's still alive.
    if (Get-CimInstance Win32_Process -Filter "ProcessId=$($info.Pid)" -ErrorAction SilentlyContinue) {
        Invoke-Quiet -FilePath "taskkill" -ArgumentList @("/PID", $info.Pid, "/T", "/F") | Out-Null
    }

    Remove-TrackedProcess -RepoRoot $RepoRoot -Name $Name
    return "stopped"
}
