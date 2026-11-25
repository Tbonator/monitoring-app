#Requires -Version 5.1
<#
.SYNOPSIS
  Shows container state and probes each service's health endpoint.
#>
Set-Location (Split-Path -Parent $PSScriptRoot)

docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}'
Write-Host ''

$checks = [ordered]@{
    'Prometheus  /-/healthy'  = 'http://127.0.0.1:9090/-/healthy'
    'Prometheus  /-/ready'    = 'http://127.0.0.1:9090/-/ready'
    'Alertmanager /-/healthy' = 'http://127.0.0.1:9093/-/healthy'
    'Grafana     /api/health' = 'http://127.0.0.1:3000/api/health'
    'Uptime Kuma /'           = 'http://127.0.0.1:3001/'
    'Loki        /ready'      = 'http://127.0.0.1:3100/ready'
    'GlitchTip   /'           = 'http://127.0.0.1:8001/'
}
$failed = 0
foreach ($name in $checks.Keys) {
    try {
        $r = Invoke-WebRequest -Uri $checks[$name] -UseBasicParsing -TimeoutSec 5 -MaximumRedirection 5
        Write-Host ("[OK]   {0} -> HTTP {1}" -f $name, $r.StatusCode) -ForegroundColor Green
    } catch {
        Write-Host ("[FAIL] {0} -> {1}" -f $name, $_.Exception.Message) -ForegroundColor Red
        $failed++
    }
}

try {
    $t = Invoke-RestMethod -Uri 'http://127.0.0.1:9090/api/v1/targets' -TimeoutSec 5
    Write-Host ''
    Write-Host 'Prometheus scrape targets:'
    foreach ($a in $t.data.activeTargets) {
        Write-Host ("  {0,-25} {1,-6} {2}" -f $a.labels.job, $a.health, $a.scrapeUrl)
    }
} catch { Write-Host 'Could not query Prometheus targets.' -ForegroundColor Yellow }

exit $failed
