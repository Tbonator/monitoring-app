#Requires -Version 5.1
<#
.SYNOPSIS
  Backs up all monitoring data volumes to .\backups\<timestamp>\ as tar.gz
  archives and records the outcome as Prometheus metrics.
.NOTES
  * Services are briefly stopped so SQLite databases (Grafana, Uptime Kuma),
    PostgreSQL (GlitchTip) and the Prometheus/Loki TSDBs are copied
    consistently, then restarted. Expect ~1-2 minutes of monitoring downtime.
  * The volume list comes from docker-compose.yml, so new services are included
    automatically.
  * Status metrics are written to exporters\textfile\monitoring_backup.prom and
    read by node-exporter (alerts: BackupMissing, BackupFailed, BackupStatusMissing).
  * Backups contain password hashes, monitor configuration and (redacted)
    error events and logs: store them securely. They are git-ignored.
  * Old backups are NOT deleted automatically; watch disk usage (DiskSpaceCritical).
#>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$started = Get-Date
$stamp = $started.ToString('yyyyMMdd-HHmmss')
$dest = Join-Path (Get-Location) "backups\$stamp"
$textfile = Join-Path (Get-Location) 'exporters\textfile\monitoring_backup.prom'

function Write-BackupMetrics([bool]$success, [long]$sizeBytes) {
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $lastSuccess = 0
    if ($success) { $lastSuccess = $now }
    elseif (Test-Path $textfile) {
        # Preserve the previous success timestamp on failure.
        $m = Select-String -Path $textfile -Pattern '^monitoring_backup_last_success_timestamp_seconds (\d+)'
        if ($m) { $lastSuccess = [long]$m.Matches[0].Groups[1].Value }
    }
    $duration = [int]((Get-Date) - $started).TotalSeconds
    $lines = @(
        '# HELP monitoring_backup_last_run_timestamp_seconds Unix time the last backup run finished.'
        '# TYPE monitoring_backup_last_run_timestamp_seconds gauge'
        "monitoring_backup_last_run_timestamp_seconds $now"
        '# HELP monitoring_backup_last_run_success 1 if the last backup run succeeded, else 0.'
        '# TYPE monitoring_backup_last_run_success gauge'
        "monitoring_backup_last_run_success $([int]$success)"
        '# HELP monitoring_backup_last_duration_seconds Duration of the last backup run.'
        '# TYPE monitoring_backup_last_duration_seconds gauge'
        "monitoring_backup_last_duration_seconds $duration"
        '# HELP monitoring_backup_last_size_bytes Total size of the last successful backup.'
        '# TYPE monitoring_backup_last_size_bytes gauge'
        "monitoring_backup_last_size_bytes $sizeBytes"
    )
    if ($lastSuccess -gt 0) {
        $lines += '# HELP monitoring_backup_last_success_timestamp_seconds Unix time of the last successful backup.'
        $lines += '# TYPE monitoring_backup_last_success_timestamp_seconds gauge'
        $lines += "monitoring_backup_last_success_timestamp_seconds $lastSuccess"
    }
    # Atomic replace; Unix newlines; file must end with a newline.
    $tmp = "$textfile.tmp"
    [IO.File]::WriteAllText($tmp, (($lines -join "`n") + "`n"), (New-Object Text.UTF8Encoding $false))
    Move-Item -Force $tmp $textfile
}

$cfg = docker compose config --format json | ConvertFrom-Json
$volumes = @($cfg.volumes.PSObject.Properties | ForEach-Object { $_.Value.name })
$tarImage = @(docker compose config --images | Where-Object { $_ -like 'prom/prometheus:*' })[0]
if (-not $tarImage) { $tarImage = 'prom/prometheus:v3.16.0' }

$success = $false
$size = 0
New-Item -ItemType Directory -Force $dest | Out-Null
Write-Host "Backing up $($volumes.Count) volumes to $dest"
Write-Host 'Stopping services for a consistent backup...'
docker compose stop
try {
    foreach ($v in $volumes) {
        Write-Host "  $v"
        docker run --rm --user root --entrypoint tar -v "${v}:/source:ro" -v "${dest}:/backup" $tarImage czf "/backup/$v.tar.gz" -C /source .
        if ($LASTEXITCODE -ne 0) { throw "Backup of $v failed" }
    }
    $size = (Get-ChildItem $dest -File | Measure-Object Length -Sum).Sum
    $success = $true
} catch {
    Write-Host "BACKUP FAILED: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    Write-Host 'Restarting services...'
    docker compose start
    Write-BackupMetrics $success $size
}
if (-not $success) { exit 1 }
Write-Host ("Backup complete: {0} ({1:N1} MB)" -f $dest, ($size / 1MB))
