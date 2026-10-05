# restart.ps1 - Restart MOM for meetings services

param(
    [switch]$NoBrowser,
    [switch]$NoWait
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "Restarting MOM for meetings..." -ForegroundColor Cyan

& (Join-Path $ScriptDir "stop.ps1")
Start-Sleep -Seconds 1
& (Join-Path $ScriptDir "start.ps1") @PSBoundParameters
