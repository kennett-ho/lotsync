<#
.SYNOPSIS
    Read-only environment diagnostics for LotSync. Checks everything
    tools/launch.ps1 depends on without starting or stopping anything.

.DESCRIPTION
    Run this first when something's wrong, or any time you just want a
    status check. It never installs, kills, or writes anything except
    (if missing) the tools/.state directory itself.
#>

$ErrorActionPreference = "Continue"
. "$PSScriptRoot\common.ps1"

$RepoRoot = Get-RepoRoot

Write-Host ""
Write-Host "=== LotSync Doctor ===" -ForegroundColor Magenta
Write-Info "Repo root: $RepoRoot"
Write-Host ""

$problems = 0

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------
Write-Step "Repo layout"
$leaf = Split-Path $RepoRoot -Leaf
if ($leaf -eq "lotsync") {
    Write-Ok "Folder is named 'lotsync' (required for the 'import lotsync.*' / PYTHONPATH=.. convention)."
} else {
    Write-ErrMsg "Folder is named '$leaf', not 'lotsync' -- launch.ps1 will refuse to run. See README.md's 'Running LotSync' section."
    $problems++
}

if (Test-Path (Join-Path $RepoRoot ".git")) {
    Write-Ok "This is a git repository."
} else {
    Write-WarnMsg "No .git directory found -- tools/update.ps1 needs this to be a git checkout."
}
Write-Host ""

# ---------------------------------------------------------------------------
# Toolchain
# ---------------------------------------------------------------------------
Write-Step "Toolchain"

$pythonCmd = Get-PythonCommand
if ($pythonCmd) {
    Write-Ok "Python: $(Get-CommandOutputText -FilePath $pythonCmd -ArgumentList @('--version')) (via '$pythonCmd')"
} else {
    Write-ErrMsg "No usable Python found on PATH."
    $problems++
}

if (Test-CommandAvailable "node") {
    Write-Ok "Node: $(node --version)"
} else {
    Write-ErrMsg "Node.js not found on PATH."
    $problems++
}

if (Test-CommandAvailable "npm") {
    Write-Ok "npm: $(npm --version)"
} else {
    Write-ErrMsg "npm not found on PATH."
    $problems++
}

if (Test-CommandAvailable "git") {
    Write-Ok "git: $(git --version)"
} else {
    Write-WarnMsg "git not found on PATH -- only needed for tools/update.ps1."
}
Write-Host ""

# ---------------------------------------------------------------------------
# Backend environment
# ---------------------------------------------------------------------------
Write-Step "Backend (.venv)"
$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Write-Ok "Virtual environment exists ($venvPython)."
    if (Test-BackendDepsSatisfied -VenvPython $venvPython) {
        Write-Ok "fastapi, uvicorn, python-multipart, pandas, openpyxl, httpx all importable."
    } else {
        Write-WarnMsg "One or more backend dependencies are missing. Run tools\launch.ps1 or tools\update.ps1 to install them."
    }
} else {
    Write-WarnMsg "No .venv found yet -- tools\launch.ps1 will create one on first run."
}

if (Test-Path (Join-Path $RepoRoot "requirements.txt")) {
    Write-Ok "requirements.txt present."
} else {
    Write-ErrMsg "requirements.txt is missing from the repo root."
    $problems++
}
Write-Host ""

# ---------------------------------------------------------------------------
# Frontend environment
# ---------------------------------------------------------------------------
Write-Step "Frontend"
$frontendDir = Join-Path $RepoRoot "frontend"
if (Test-FrontendDepsSatisfied -FrontendDir $frontendDir) {
    Write-Ok "node_modules present and installed via npm."
} else {
    Write-WarnMsg "frontend/node_modules is missing or incomplete -- tools\launch.ps1 will run npm install."
}

$hasPnpmLock = Test-Path (Join-Path $frontendDir "pnpm-lock.yaml")
if ($hasPnpmLock) {
    Write-Info "pnpm-lock.yaml is also present in frontend/ -- expected, not a problem. npm is the standard for local dev (this tooling uses it); pnpm-lock.yaml and .mise.toml's pnpm pin are kept only because frontend/.figma/make/* (Figma Make's hosted dev-container/deploy pipeline) hardcodes pnpm and depends on both. See tools/README.md."
}
Write-Host ""

# ---------------------------------------------------------------------------
# Ports / running state
# ---------------------------------------------------------------------------
Write-Step "Current session"
$backendHostName = Get-BackendHostName
$backendPort = Get-BackendPort
$frontendPort = Get-FrontendPort

foreach ($pair in @(@("backend", $backendHostName, $backendPort), @("frontend", "127.0.0.1", $frontendPort))) {
    $name = $pair[0]; $h = $pair[1]; $p = $pair[2]
    $tracked = Get-TrackedProcess -RepoRoot $RepoRoot -Name $name
    $portOpen = Test-TcpPort -HostName $h -Port $p

    if ($tracked -and $portOpen) {
        Write-Ok "${name}: running (PID $($tracked.Pid), ${h}:${p}, started $($tracked.StartedAt))"
    } elseif ($tracked -and -not $portOpen) {
        Write-WarnMsg "${name}: tracked (PID $($tracked.Pid)) but port $p is not responding -- may have crashed. Check tools\.state\${name}.log."
    } elseif ((-not $tracked) -and $portOpen) {
        Write-WarnMsg "${name}: something is listening on ${h}:${p} but this tooling didn't start it."
    } else {
        Write-Info "${name}: not running."
    }
}
Write-Host ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
if ($problems -eq 0) {
    Write-Host "=== No blocking problems found ===" -ForegroundColor Green
} else {
    Write-Host "=== $problems blocking problem(s) found -- see [FAIL] lines above ===" -ForegroundColor Red
}
Write-Host ""
