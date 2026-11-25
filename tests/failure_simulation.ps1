#Requires -Version 5.1
<#
.SYNOPSIS
  Failure simulation for the monitoring platform (LOCAL DEVELOPMENT ONLY).
.DESCRIPTION
  Stops node-exporter, glitchtip-postgres and loki together, verifies that the
  expected alerts fire, writes a marked application log line while Loki is
  down, restarts everything, then verifies recovery, alert resolution and
  that the log line arrived in Loki (no loss during the outage).
  Never run against production (CLAUDE.md section 17).
#>
$ErrorActionPreference = 'Continue'
Set-Location (Split-Path -Parent $PSScriptRoot)
$failed = 0
function Check($ok, $msg) { if ($ok) { Write-Host "[PASS] $msg" -ForegroundColor Green } else { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:failed++ } }
function Get-Alerts { (Invoke-RestMethod 'http://127.0.0.1:9090/api/v1/query?query=ALERTS{alertstate="firing"}').data.result | ForEach-Object { "$($_.metric.alertname)|$($_.metric.instance)|$($_.metric.job)" } }
function Wait-For($desc, [scriptblock]$cond, $seconds) {
    $waitStart = Get-Date
    while (((Get-Date) - $waitStart).TotalSeconds -lt $seconds) { if (& $cond) { return [int]((Get-Date) - $waitStart).TotalSeconds }; Start-Sleep 10 }
    return -1
}

$expect = @{
    'InfrastructureExporterDown (node)' = { (Get-Alerts) -match '^InfrastructureExporterDown\|.*\|node$' }
    'PostgresDown'                      = { (Get-Alerts) -match '^PostgresDown\|' }
    'MonitoringComponentDown (loki)'    = { (Get-Alerts) -match '^MonitoringComponentDown\|http://loki' }
}

$marker = 'failuresim' + -join ((97..122) | Get-Random -Count 10 | ForEach-Object { [char]$_ })
$t0 = Get-Date
Write-Host "$(Get-Date -Format HH:mm:ss) Stopping node-exporter, glitchtip-postgres, loki"
docker compose stop node-exporter glitchtip-postgres loki | Out-Null

# App log line while Loki is down (Django logs the 404 to its JSON file).
try { Invoke-WebRequest "http://127.0.0.1:8000/$marker/" -UseBasicParsing -TimeoutSec 5 | Out-Null } catch {}

foreach ($name in $expect.Keys) {
    $s = Wait-For $name $expect[$name] 300
    Check ($s -ge 0) ("{0} fired" -f $name) + $(if ($s -ge 0) { " (after ~$([int]((Get-Date)-$t0).TotalSeconds)s from stop)" } else { ' within 5 min' })
}
# Finding (Phase 5): GlitchTip's /_health/ is liveness-only and stays 200 while
# its database is down, so the DB outage is detected by PostgresDown instead.
$gp = (Invoke-RestMethod ('http://127.0.0.1:9090/api/v1/query?query=' + [uri]::EscapeDataString('probe_success{instance="http://glitchtip:8000/_health/"}'))).data.result
Write-Host "[INFO] GlitchTip /_health/ probe during DB outage: $($gp[0].value[1]) (liveness-only; covered by PostgresDown)"
$am = Invoke-RestMethod http://127.0.0.1:9093/api/v2/alerts
Check (@($am | Where-Object { $_.labels.alertname -in 'PostgresDown', 'InfrastructureExporterDown', 'MonitoringComponentDown' }).Count -ge 3) "alerts delivered to Alertmanager ($(@($am).Count) active)"

Write-Host "$(Get-Date -Format HH:mm:ss) Restarting"
$tr = Get-Date
docker compose start loki glitchtip-postgres node-exporter | Out-Null

$s = Wait-For 'all simulated alerts resolved' { -not ((Get-Alerts) -match '^(InfrastructureExporterDown\|.*\|node|PostgresDown\||MonitoringComponentDown\|http://(glitchtip|loki))') } 420
Check ($s -ge 0) "simulated alerts resolved after restart (~${s}s)"
$s = Wait-For 'targets up' { @((Invoke-RestMethod http://127.0.0.1:9090/api/v1/targets).data.activeTargets | Where-Object health -ne 'up').Count -eq 0 } 180
Check ($s -ge 0) 'all scrape targets up again'

# No log loss: the line written during the outage must reach Loki.
$s = Wait-For 'log line in Loki' {
    $q = [uri]::EscapeDataString("{application=`"funeral-back-office`"} |= `"$marker`"")
    $st = [DateTimeOffset]::new($script:t0).AddMinutes(-2).ToUnixTimeMilliseconds() * 1000000   # $script:t0 = outage start
    try { @((Invoke-RestMethod "http://127.0.0.1:3100/loki/api/v1/query_range?query=$q&start=$st").data.result).Count -gt 0 } catch { $false }
} 600   # Alloy retry backoff (max 30s) after Loki returns
Check ($s -ge 0) "log line written during Loki outage arrived after recovery (marker $marker)"

if ($failed) { Write-Host "$failed check(s) failed" -ForegroundColor Red; exit 1 }
Write-Host 'Failure simulation passed.' -ForegroundColor Green
