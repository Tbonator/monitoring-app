#Requires -Version 5.1
<#
.SYNOPSIS
  Validates Compose, Prometheus config/rules, dashboard JSON, and checks for secrets.
#>
Set-Location (Split-Path -Parent $PSScriptRoot)
$failed = 0

function Write-Result($ok, $msg) {
    if ($ok) { Write-Host "[PASS] $msg" -ForegroundColor Green }
    else { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:failed++ }
}

# 1. Docker Compose
docker compose config --quiet
Write-Result ($LASTEXITCODE -eq 0) 'docker compose config'

# 2. Prometheus config and rules (promtool from the pinned image)
$promVersion = (Select-String -Path .env -Pattern '^PROMETHEUS_VERSION=(.+)$').Matches.Groups[1].Value
if (-not $promVersion) { $promVersion = 'v3.16.0' }
$mount = "$((Get-Location).Path)\prometheus:/etc/prometheus:ro"
docker run --rm --entrypoint promtool -v $mount "prom/prometheus:$promVersion" check config /etc/prometheus/prometheus.yml
Write-Result ($LASTEXITCODE -eq 0) 'promtool check config (includes rule files)'

# 3. Grafana dashboard JSON syntax
foreach ($f in Get-ChildItem grafana\dashboards -Filter *.json) {
    try { Get-Content $f.FullName -Raw | ConvertFrom-Json | Out-Null; Write-Result $true "dashboard JSON $($f.Name)" }
    catch { Write-Result $false "dashboard JSON $($f.Name): $($_.Exception.Message)" }
}

# 4. .env must exist and must not contain placeholder passwords
if (Test-Path .env) {
    Write-Result (-not (Select-String -Path .env -Pattern 'CHANGE_ME' -Quiet)) '.env has no placeholder secrets'
} else { Write-Result $false '.env exists' }

# 5. .env must be git-ignored
Write-Result ((Get-Content .gitignore) -contains '.env') '.env is listed in .gitignore'

# 6. Published ports bound to localhost only
$cfg = docker compose config --format json | ConvertFrom-Json
$exposed = @()
foreach ($svc in $cfg.services.PSObject.Properties) {
    foreach ($p in $svc.Value.ports) { if ($p.host_ip -ne '127.0.0.1') { $exposed += "$($svc.Name):$($p.published)" } }
}
Write-Result ($exposed.Count -eq 0) "all published ports bound to 127.0.0.1 $($exposed -join ' ')"

Write-Host ''
if ($failed -eq 0) { Write-Host 'All validation checks passed.' -ForegroundColor Green }
else { Write-Host "$failed validation check(s) failed." -ForegroundColor Red }
exit $failed
