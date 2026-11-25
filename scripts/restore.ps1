#Requires -Version 5.1
<#
.SYNOPSIS
  Restores a backup made by backup.ps1.
.DESCRIPTION
  -Mode Drill (default): SAFE. Restores every archive into temporary volumes
      named "restoredrill-<volume>", verifies the data inside them using the
      already-pulled images (Prometheus promtool, PostgreSQL, Python sqlite3),
      prints a report, then removes ONLY those drill volumes. Live data and
      running services are not touched.
  -Mode Live -Force: DESTRUCTIVE. Stops the stack, replaces the contents of the
      real volumes with the backup, then starts the stack. Use only for real
      recovery, with approval. Take a fresh backup first if the current data
      may still be needed.
.EXAMPLE
  .\scripts\restore.ps1 -BackupDir .\backups\20261125-232802
.EXAMPLE
  .\scripts\restore.ps1 -BackupDir .\backups\20261125-232802 -Mode Live -Force
#>
param(
    [Parameter(Mandatory)] [string]$BackupDir,
    [ValidateSet('Drill', 'Live')] [string]$Mode = 'Drill',
    [switch]$Force,
    [switch]$KeepDrillVolumes
)
# 'Continue': PowerShell 5.1 turns native stderr into terminating errors under 'Stop';
# exit codes are checked explicitly instead.
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot)
$BackupDir = (Resolve-Path $BackupDir -ErrorAction Stop).Path
$archives = Get-ChildItem $BackupDir -Filter '*.tar.gz'
if (-not $archives) { throw "No *.tar.gz archives in $BackupDir" }

$images = @{}
foreach ($img in (docker compose config --images)) { $images[($img -split ':')[0]] = $img }
$prom = $images['prom/prometheus']; $pg = $images['postgres']; $gt = $images['glitchtip/glitchtip']

function Restore-Archive($archive, $volume) {
    docker volume create $volume | Out-Null
    # Empty the volume, then extract (tar keeps ownership/permissions).
    docker run --rm --user root --entrypoint sh -v "${volume}:/target" -v "${BackupDir}:/backup:ro" $prom `
        -c "find /target -mindepth 1 -delete && tar xzf /backup/$($archive.Name) -C /target"
    if ($LASTEXITCODE -ne 0) { throw "Restore of $($archive.Name) into $volume failed" }
}

if ($Mode -eq 'Live') {
    if (-not $Force) { throw 'Live restore replaces real data. Re-run with -Force if this is intended.' }
    Write-Host "LIVE RESTORE from $BackupDir" -ForegroundColor Yellow
    docker compose stop
    try {
        foreach ($a in $archives) {
            $vol = $a.Name -replace '\.tar\.gz$', ''
            Write-Host "  restoring $vol"
            Restore-Archive $a $vol
        }
    } finally { docker compose start }
    Write-Host 'Live restore complete. Verify with scripts\status.ps1.'
    exit 0
}

# ------------------------------- Drill ---------------------------------------
$results = [ordered]@{}
$created = @()
try {
    foreach ($a in $archives) {
        $vol = 'restoredrill-' + ($a.Name -replace '\.tar\.gz$', '')
        Restore-Archive $a $vol
        $created += $vol
        $files = docker run --rm --user root --entrypoint sh -v "${vol}:/v:ro" $prom -c 'find /v -type f | wc -l'
        $results[$vol] = "restored ($($files.Trim()) files)"
    }

    # Prometheus TSDB: blocks are readable.
    $v = 'restoredrill-monitoring-prometheus-data'
    if ($created -contains $v) {
        $out = docker run --rm --user root --entrypoint promtool -v "${v}:/prometheus" $prom tsdb list /prometheus 2>&1 | Out-String
        $blocks = ([regex]::Matches($out, '(?m)^[0-9A-Z]{26}')).Count
        $results[$v] += "; promtool tsdb list OK, $blocks persisted block(s)" + $(if ($blocks -eq 0) { ' (head/WAL only)' } else { '' })
        # Recent data lives in the WAL and is only replayed at startup, so start a
        # throw-away Prometheus (no network) on the restored volume and query it.
        $name = 'restoredrill-prometheus'
        docker run -d --rm --name $name --network none --user root -v "${v}:/prometheus" $prom `
            --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus `
            --storage.tsdb.retention.time=100y | Out-Null
        try {
            $series = $null
            for ($i = 0; $i -lt 40 -and -not $series; $i++) {
                Start-Sleep 3
                # Series API (no aggregation): count_over_time would drop __name__ and
                # make different metrics with equal labels collide (HTTP 422).
                $since = [DateTimeOffset]::UtcNow.AddDays(-2).ToUnixTimeSeconds()
                $q = docker exec $name wget -qO- "http://localhost:9090/api/v1/series?match%5B%5D=%7Bjob%3D%22funeral-back-office%22%7D&start=$since" 2>$null
                if ($q -match '"status":"success"') { $n = ([regex]::Matches($q, '"__name__"')).Count; if ($n -gt 0) { $series = $n } }
            }
            if ($series) { $results[$v] += "; started from restored WAL, funeral-back-office series restored=$series" }
            else { $results[$v] += '; FAILED: restored Prometheus returned no funeral-back-office series' }
        } finally { docker stop $name *> $null }
    }

    # Grafana + Uptime Kuma SQLite databases: open read-only, count rows.
    $sqlite = @"
import sqlite3, sys
def q(path, sql):
    c = sqlite3.connect('file:' + path + '?immutable=1', uri=True)  # read-only mount, WAL-safe
    ok = c.execute('pragma integrity_check').fetchone()[0]
    return ok, c.execute(sql).fetchone()[0]
which = sys.argv[1]
if which == 'grafana':
    ok, n = q('/v/grafana.db', 'select count(*) from dashboard')
    _, u = q('/v/grafana.db', 'select count(*) from user')
    print(f'integrity={ok}; dashboards={n}; users={u}')
else:
    ok, n = q('/v/kuma.db', 'select count(*) from monitor')
    _, h = q('/v/kuma.db', 'select count(*) from heartbeat')
    print(f'integrity={ok}; monitors={n}; heartbeats={h}')
"@
    foreach ($pair in @(@('restoredrill-monitoring-grafana-data', 'grafana'), @('restoredrill-monitoring-uptime-kuma-data', 'kuma'))) {
        if ($created -contains $pair[0]) {
            $out = docker run --rm --user root --entrypoint python -v "$($pair[0]):/v:ro" $gt -c $sqlite $pair[1] 2>&1 | Select-Object -Last 1
            $results[$pair[0]] += "; $out"
        }
    }

    # GlitchTip PostgreSQL: start a throw-away server on the restored volume
    # (no network, no published ports) and query it.
    $v = 'restoredrill-monitoring-glitchtip-postgres-data'
    if ($created -contains $v) {
        $name = 'restoredrill-postgres'
        docker run -d --rm --name $name --network none -e POSTGRES_PASSWORD=drill-only -v "${v}:/var/lib/postgresql" $pg | Out-Null
        try {
            $ready = $false
            for ($i = 0; $i -lt 30 -and -not $ready; $i++) { Start-Sleep 2; docker exec $name pg_isready -U glitchtip -d glitchtip *> $null; $ready = ($LASTEXITCODE -eq 0) }
            if ($ready) {
                $n = docker exec $name psql -U glitchtip -d glitchtip -tAc "select (select count(*) from issue_events_issueevent) || ' events; ' || (select count(*) from users_user) || ' users; ' || (select count(*) from projects_project) || ' projects'"
                $results[$v] += "; PostgreSQL started; $($n.Trim())"
            } else { $results[$v] += '; FAILED: PostgreSQL did not become ready' }
        } finally { docker stop $name *> $null }
    }
}
finally {
    if (-not $KeepDrillVolumes) {
        foreach ($v in $created) { if ($v -like 'restoredrill-*') { docker volume rm $v *> $null } }
    }
}

Write-Host "Restore drill report for $BackupDir" -ForegroundColor Cyan
foreach ($k in $results.Keys) { Write-Host ("  {0,-48} {1}" -f $k, $results[$k]) }
$failed = @($results.Values | Where-Object { $_ -match 'FAILED|integrity=(?!ok)' }).Count
if ($failed) { Write-Host "$failed check(s) failed" -ForegroundColor Red; exit 1 }
Write-Host 'Restore drill passed.' -ForegroundColor Green
