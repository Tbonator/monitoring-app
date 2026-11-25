#Requires -Version 5.1
<#
.SYNOPSIS
  Validates configuration, checks ports, and starts the monitoring stack.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path '.env')) {
    Write-Error '.env not found. Copy .env.example to .env and set secure credentials.'
}

docker info *> $null
if ($LASTEXITCODE -ne 0) { Write-Error 'Docker engine is not running. Start Docker Desktop.' }

# Only check ports not already held by our own running containers.
$running = docker compose ps --services --status running 2>$null
if (-not $running) {
    $busy = @()
    foreach ($p in 3000, 3001, 9090, 9093) {
        if (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) { $busy += $p }
    }
    if ($busy.Count -gt 0) { Write-Error "Port(s) already in use: $($busy -join ', ')" }
}

& "$PSScriptRoot\validate.ps1"
if ($LASTEXITCODE -ne 0) { Write-Error 'Validation failed; not starting.' }

docker compose up -d
if ($LASTEXITCODE -ne 0) { Write-Error 'docker compose up failed.' }

Write-Host ''
Write-Host 'Started. URLs:'
Write-Host '  Grafana:     http://localhost:3000'
Write-Host '  Uptime Kuma: http://localhost:3001'
Write-Host '  Prometheus:  http://localhost:9090'
Write-Host '  Alertmanager: http://localhost:9093'
Write-Host 'Run scripts\status.ps1 to check health.'
