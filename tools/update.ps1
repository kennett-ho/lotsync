<#
.SYNOPSIS
    Pulls the latest changes and re-syncs backend/frontend dependencies.

.DESCRIPTION
    Refuses to pull over uncommitted local changes -- it surfaces that
    and stops rather than stashing or resetting anything for you. Once
    the working tree is clean and pulled, it re-runs the same dependency
    installation launch.ps1 does (backend .venv + frontend node_modules),
    forcing a re-check even if the quick "already satisfied" probe would
    normally skip it, since a pull may have changed requirements.txt or
    package.json.

    Does not start or stop any servers -- run tools\launch.ps1 after.
#>

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$RepoRoot = Get-RepoRoot
Assert-RepoLayout -RepoRoot $RepoRoot

Write-Host ""
Write-Host "=== LotSync Update ===" -ForegroundColor Magenta
Write-Host ""

if (-not (Test-CommandAvailable "git")) {
    Write-ErrMsg "git not found on PATH -- can't update."
    exit 1
}
if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    Write-ErrMsg "$RepoRoot is not a git repository."
    exit 1
}

Push-Location $RepoRoot
try {
    Write-Step "Checking working tree ..."
    $status = & git status --porcelain
    if ($status) {
        Write-ErrMsg "You have uncommitted changes. Commit or stash them first -- update.ps1 will not pull over local work."
        Write-Host ""
        git status --short
        exit 1
    }
    Write-Ok "Working tree is clean."

    Write-Step "Pulling latest changes ..."
    & git pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        Write-ErrMsg "git pull failed (see above) -- resolve manually. --ff-only refused to create a merge commit."
        exit 1
    }
} finally {
    Pop-Location
}
Write-Host ""

$pythonCmd = Get-PythonCommand
if (-not $pythonCmd) {
    Write-ErrMsg "No usable Python found on PATH -- can't sync backend dependencies."
    exit 1
}

$venvPython = Ensure-Venv -RepoRoot $RepoRoot -PythonCmd $pythonCmd
Write-Step "Re-syncing backend dependencies ..."
Ensure-BackendDeps -RepoRoot $RepoRoot -VenvPython $venvPython -Force

Write-Step "Re-syncing frontend dependencies ..."
Ensure-FrontendDeps -FrontendDir (Join-Path $RepoRoot "frontend") -Force

Write-Host ""
Write-Host "=== Update complete === (run tools\launch.ps1 to start LotSync)" -ForegroundColor Magenta
Write-Host ""
