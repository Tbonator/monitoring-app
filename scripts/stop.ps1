#Requires -Version 5.1
<#
.SYNOPSIS
  Gracefully stops the monitoring stack. Volumes (data) are preserved.
  This script intentionally never uses "docker compose down -v".
#>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

docker compose stop
if ($LASTEXITCODE -ne 0) { Write-Error 'docker compose stop failed.' }
Write-Host 'Monitoring stack stopped. Data volumes preserved.'
