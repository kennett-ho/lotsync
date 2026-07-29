<#
.SYNOPSIS
    Stops the LotSync backend/frontend processes started by
    tools/launch.ps1, if any.

.DESCRIPTION
    Only ever touches processes this tooling itself started (tracked via
    tools/.state/*.pid, verified by matching the live process's command
    line before killing anything) -- never a blanket "kill all python /
    kill all node". Safe to run even if nothing is running.
#>

$ErrorActionPreference = "Stop"
. "$PSScriptRoot\common.ps1"

$RepoRoot = Get-RepoRoot

Write-Host ""
Write-Host "=== Stopping LotSync ===" -ForegroundColor Magenta

$anyStopped = $false
foreach ($name in @("backend", "frontend")) {
    $result = Stop-TrackedProcess -RepoRoot $RepoRoot -Name $name
    switch ($result) {
        "stopped" {
            Write-Ok "Stopped $name."
            $anyStopped = $true
        }
        "not-running"        { Write-Info "$name was tracked but already not running." }
        "not-tracked"        { Write-Info "$name is not running (nothing tracked)." }
        "signature-mismatch" { Write-WarnMsg "$name's tracked PID was reused by an unrelated process -- left it alone." }
    }
}

Write-Host ""
if (-not $anyStopped) {
    Write-Info "Nothing to stop."
}
Write-Host ""
