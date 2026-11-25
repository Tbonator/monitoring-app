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

# Resolved, pinned image references come from Compose (no direct .env parsing).
$images = @{}
foreach ($img in (docker compose config --images)) { $images[($img -split ':')[0]] = $img }
function Get-Image($repo, $fallback) { if ($images[$repo]) { $images[$repo] } else { $fallback } }

# 2. Prometheus config and rules (promtool from the pinned image)
# Mirror the docker-compose.yml mounts so referenced paths resolve identically.
$here = (Get-Location).Path
if (-not (Test-Path secrets)) { New-Item -ItemType Directory secrets | Out-Null }
docker run --rm --entrypoint promtool `
    -v "$here\prometheus\prometheus.yml:/etc/prometheus/prometheus.yml:ro" `
    -v "$here\prometheus\rules:/etc/prometheus/rules:ro" `
    -v "$here\prometheus\targets\development:/etc/prometheus/targets:ro" `
    -v "$here\secrets:/etc/prometheus/secrets:ro" `
    (Get-Image 'prom/prometheus' 'prom/prometheus:v3.16.0') check config /etc/prometheus/prometheus.yml
Write-Result ($LASTEXITCODE -eq 0) 'promtool check config (includes rule files)'

# 2-env. Every job's file_sd targets parse in BOTH environments.
$jobs = (Select-String -Path prometheus\prometheus.yml -Pattern '^\s*- job_name:\s*(\S+)').Matches | ForEach-Object { $_.Groups[1].Value }
foreach ($envName in 'development', 'production') {
    $bad = @()
    foreach ($job in $jobs) {
        $out = docker run --rm --entrypoint promtool `
            -v "$here\prometheus\prometheus.yml:/etc/prometheus/prometheus.yml:ro" `
            -v "$here\prometheus\targets\${envName}:/etc/prometheus/targets:ro" `
            -v "$here\secrets:/etc/prometheus/secrets:ro" `
            (Get-Image 'prom/prometheus' 'prom/prometheus:v3.16.0') check service-discovery --timeout=5s /etc/prometheus/prometheus.yml $job 2>&1 | Out-String
        # Match promtool error lines only (a hostname like "errors.example" is not an error).
        if ($LASTEXITCODE -ne 0 -or $out -match '(?im)^\s*(error|level=error|failed)\b') { $bad += $job }
    }
    Write-Result ($bad.Count -eq 0) "scrape targets parse ($envName, $($jobs.Count) jobs) $($bad -join ' ')"
}

# 2a. Alert rule unit tests (synthetic series; prometheus/tests/*.test.yml)
foreach ($t in Get-ChildItem prometheus\tests -Filter *.test.yml -ErrorAction SilentlyContinue) {
    docker run --rm --entrypoint promtool -v "$here\prometheus:/etc/prometheus:ro" `
        (Get-Image 'prom/prometheus' 'prom/prometheus:v3.16.0') test rules "/etc/prometheus/tests/$($t.Name)" | Out-Null
    Write-Result ($LASTEXITCODE -eq 0) "promtool test rules $($t.Name)"
}

# 2b. Alertmanager config (amtool from the pinned image)

docker run --rm --entrypoint amtool `
    -v "$here\alertmanager\alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" `
    (Get-Image 'prom/alertmanager' 'prom/alertmanager:v0.35.1') check-config /etc/alertmanager/alertmanager.yml
Write-Result ($LASTEXITCODE -eq 0) 'amtool check-config'

# 2c. Loki config (loki -verify-config from the pinned image)

docker run --rm -v "$here\loki\loki-config.yml:/etc/loki/loki-config.yml:ro" `
    (Get-Image 'grafana/loki' 'grafana/loki:3.7.10') '-config.file=/etc/loki/loki-config.yml' '-config.expand-env=true' '-verify-config' 2>&1 | Out-Null
Write-Result ($LASTEXITCODE -eq 0) 'loki -verify-config'

# 2d. Alloy config syntax (alloy fmt parses the file)

docker run --rm -v "$here\alloy\config.alloy:/etc/alloy/config.alloy:ro" `
    (Get-Image 'grafana/alloy' 'grafana/alloy:v1.22.0') fmt /etc/alloy/config.alloy | Out-Null
Write-Result ($LASTEXITCODE -eq 0) 'alloy fmt (config syntax)'

# 2e. PRODUCTION configuration (Phase 5) - validated with the template env file.
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env --env-file deploy/production.env.example config --quiet
Write-Result ($LASTEXITCODE -eq 0) 'production overlay: docker compose config'
docker run --rm -e GRAFANA_DOMAIN=grafana.example.co.za -e GLITCHTIP_DOMAIN=errors.example.co.za -e CADDY_TLS=ops@example.co.za `
    -v "$here\caddy\Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2.11.9-alpine `
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | Out-Null
Write-Result ($LASTEXITCODE -eq 0) 'production: caddy validate'
$smtp = if (Test-Path secrets\smtp-password) { "$here\secrets\smtp-password" } else { "$here\alertmanager\alertmanager.prod.yml" }
docker run --rm --entrypoint amtool `
    -v "$here\alertmanager\alertmanager.prod.yml:/etc/alertmanager/alertmanager.yml:ro" `
    -v "${smtp}:/etc/alertmanager/secrets/smtp-password:ro" `
    (Get-Image 'prom/alertmanager' 'prom/alertmanager:v0.35.1') check-config /etc/alertmanager/alertmanager.yml | Out-Null
Write-Result ($LASTEXITCODE -eq 0) 'production: amtool check-config (alertmanager.prod.yml)'
docker compose -f deploy\app-server\docker-compose.yml --env-file deploy\app-server\app-server.env.example config --quiet
Write-Result ($LASTEXITCODE -eq 0) 'app-server bundle: docker compose config'
docker run --rm -v "$here\deploy\app-server\config.alloy:/etc/alloy/config.alloy:ro" `
    (Get-Image 'grafana/alloy' 'grafana/alloy:v1.22.0') fmt /etc/alloy/config.alloy | Out-Null
Write-Result ($LASTEXITCODE -eq 0) 'app-server bundle: alloy fmt'

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
