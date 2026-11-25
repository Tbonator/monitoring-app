#Requires -Version 5.1
<#
.SYNOPSIS
  Backs up the monitoring data volumes to .\backups\<timestamp>\ as tar.gz archives.
.NOTES
  All services are briefly stopped so the SQLite databases (Grafana, Uptime Kuma)
  and the Prometheus TSDB are copied consistently, then restarted.
  The pinned Prometheus image (busybox tar) is reused, so no extra image is pulled.
  Backups contain password hashes and monitor configuration: store them securely.
#>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$dest = Join-Path (Get-Location) "backups\$stamp"
New-Item -ItemType Directory -Force $dest | Out-Null

$promVersion = (Select-String -Path .env -Pattern '^PROMETHEUS_VERSION=(.+)$').Matches.Groups[1].Value
if (-not $promVersion) { $promVersion = 'v3.16.0' }
$volumes ='monitoring-prometheus-data', 'monitoring-grafana-data', 'monitoring-uptime-kuma-data'

Write-Host 'Stopping services for a consistent backup...'
docker compose stop
try {
    foreach ($v in $volumes) {
        Write-Host "Backing up $v"
        docker run --rm --user root --entrypoint tar -v "${v}:/source:ro" -v "${dest}:/backup" "prom/prometheus:$promVersion" czf "/backup/$v.tar.gz" -C /source .
        if ($LASTEXITCODE -ne 0) { throw "Backup of $v failed" }
    }
} finally {
    Write-Host 'Restarting services...'
    docker compose start
}
Write-Host "Backup complete: $dest"
