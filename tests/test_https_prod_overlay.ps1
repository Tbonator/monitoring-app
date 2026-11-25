#Requires -Version 5.1
<#
.SYNOPSIS
  Local test of the PRODUCTION overlay's HTTPS layer (Caddy, internal CA).
.DESCRIPTION
  Starts caddy + grafana + glitchtip with docker-compose.prod.yml and
  deploy/local-prod-test.env (127.0.0.1 only, "tls internal"), runs the checks,
  then restores the development configuration. Alertmanager is NOT switched to
  the production (e-mail) config during this test.
#>
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$prod = @('-f', 'docker-compose.yml', '-f', 'docker-compose.prod.yml', '--env-file', '.env', '--env-file', 'deploy/local-prod-test.env')
$failed = 0
function Check($ok, $msg) { if ($ok) { Write-Host "[PASS] $msg" -ForegroundColor Green } else { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:failed++ } }

docker compose @prod up -d caddy grafana glitchtip | Out-Null
try {
    $deadline = (Get-Date).AddMinutes(4)
    do { Start-Sleep 5; $h = (docker inspect grafana glitchtip --format '{{.State.Health.Status}}') -join ',' } until ($h -eq 'healthy,healthy' -or (Get-Date) -gt $deadline)
    $ca = Join-Path $env:TEMP 'caddy-local-root.crt'
    docker cp caddy:/data/caddy/pki/authorities/local/root.crt $ca | Out-Null
    $curlArgs = @('--resolve', 'grafana.localhost:443:127.0.0.1', '--resolve', 'grafana.localhost:80:127.0.0.1',
           '--resolve', 'errors.localhost:443:127.0.0.1', '--resolve', 'prometheus.localhost:443:127.0.0.1',
           '-m', '10', '--ssl-no-revoke', '-s')

    $r = curl.exe @curlArgs -o NUL -w '%{http_code} %{redirect_url}' http://grafana.localhost/
    Check ($r -eq '308 https://grafana.localhost/') "HTTP redirects to HTTPS ($r)"
    $r = curl.exe @curlArgs -o NUL -w '%{http_code}' --cacert $ca https://grafana.localhost/api/health
    Check ($r -eq '200') "Grafana over HTTPS, certificate verifies ($r)"
    $hdr = (curl.exe @curlArgs -D - -o NUL --cacert $ca https://grafana.localhost/login) -join "`n"
    foreach ($hname in 'Strict-Transport-Security', 'X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy') {
        Check ($hdr -match "(?im)^$hname\s*:") "header $hname"
    }
    Check (-not ($hdr -match '(?im)^Server\s*:')) 'Server header removed'
    $r = curl.exe @curlArgs -o NUL -w '%{http_code}' --cacert $ca https://grafana.localhost/api/datasources
    Check ($r -eq '401') "Grafana API refuses unauthenticated access ($r)"
    $r = curl.exe @curlArgs -w '%{http_code}' --cacert $ca https://errors.localhost/_health/
    Check ($r -match '200$') "GlitchTip over HTTPS ($r)"
    curl.exe @curlArgs -o NUL --cacert $ca https://prometheus.localhost/ 2>$null
    Check ($LASTEXITCODE -ne 0) "Unconfigured hosts (Prometheus) are not served (curl exit $LASTEXITCODE)"

    # Access log must not contain query strings, cookies or Authorization.
    curl.exe @curlArgs -o NUL --cacert $ca -H 'Authorization: Bearer fakeTOKEN123456789' -H 'Cookie: grafana_session=fakeSESSIONabc123' `
        'https://grafana.localhost/api/search?query=Thandi+Mokoena&id=9001015009087' | Out-Null
    Start-Sleep 2
    $log = (docker logs caddy --since 20s 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -match '/api/search' }) -join "`n"
    foreach ($v in 'Thandi', '9001015009087', 'fakeTOKEN123456789', 'fakeSESSIONabc123') {
        Check (-not $log.Contains($v)) "access log does not contain '$v'"
    }
    $grafanaEnv = (docker inspect grafana --format '{{range .Config.Env}}{{println .}}{{end}}') -join "`n"
    Check ($grafanaEnv -match 'GF_SECURITY_COOKIE_SECURE=true') 'Grafana secure cookies enabled'
    $deadline = (Get-Date).AddSeconds(90)
    do { Start-Sleep 5; $ch = docker inspect caddy --format '{{.State.Health.Status}}' } until ($ch -ne 'starting' -or (Get-Date) -gt $deadline)
    Check ($ch -eq 'healthy') "Caddy container healthcheck ($ch)"
}
finally {
    Write-Host 'Restoring development configuration...'
    docker compose @prod rm -sf caddy | Out-Null
    docker compose up -d grafana glitchtip prometheus | Out-Null
}
if ($failed) { Write-Host "$failed check(s) failed" -ForegroundColor Red; exit 1 }
Write-Host 'All HTTPS overlay checks passed.' -ForegroundColor Green
