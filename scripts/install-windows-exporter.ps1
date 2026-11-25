#Requires -Version 5.1
<#
.SYNOPSIS
  Installs windows_exporter v0.32.1 as a Windows service (owner-approved, Phase 4).
.DESCRIPTION
  * Verifies the MSI's SHA-256 against the official release checksum.
  * Installs with a UAC prompt (msiexec needs administrator rights).
  * Binds to 127.0.0.1:9182 only - Prometheus reaches it via Docker Desktop's
    host.docker.internal loopback forwarding (same as Django on :8000).
  * Does NOT create a Windows Firewall exception (ADDLOCAL=DefaultFeature only).
  * Minimal collectors: cpu, logical_disk, memory, net, os, system.
  Uninstall: Settings > Apps > windows_exporter, or msiexec /x <msi>.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$version = '0.32.1'
$msi = Join-Path $root "downloads\windows_exporter-$version\windows_exporter-$version-amd64.msi"
$expected = '8e1ade6a2fbcdeb4774c300b598667cd7888246be8fcc4b586d11b3680433981'  # GitHub release v0.32.1
$log = Join-Path $root "downloads\windows_exporter-$version\install.log"

if (-not (Test-Path $msi)) {
    New-Item -ItemType Directory -Force (Split-Path $msi) | Out-Null
    Invoke-WebRequest "https://github.com/prometheus-community/windows_exporter/releases/download/v$version/windows_exporter-$version-amd64.msi" -OutFile $msi -UseBasicParsing
}
$actual = (Get-FileHash $msi -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) { throw "Checksum mismatch: $actual (expected $expected). Not installing." }
Write-Host "Checksum OK ($actual)"

# ADDLOCAL=DefaultFeature installs the exporter WITHOUT the FirewallException
# feature. Do NOT use REMOVE=FirewallException: with this MSI it becomes
# REMOVE=ALL and installs nothing (empty product, no service) - see ADR-027.
$installArgs = "/i `"$msi`" ADDLOCAL=DefaultFeature " +
    'ENABLED_COLLECTORS="cpu,logical_disk,memory,net,os,system" LISTEN_ADDR=127.0.0.1 LISTEN_PORT=9182 ' +
    "/qn /norestart /l*v `"$log`""
# If a previous attempt left an empty registration (no service), remove it first.
$needsCleanup = (-not (Get-Service windows_exporter -ErrorAction SilentlyContinue)) -and
    [bool](Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -eq 'windows_exporter' })

# Elevated steps go into a temporary script (avoids nested-quoting problems),
# so a single UAC prompt covers cleanup + install.
$step = Join-Path (Split-Path $msi) 'elevated-install.ps1'
$lines = @()
if ($needsCleanup) {
    Write-Host 'An earlier empty installation will be removed first.'
    $lines += "Start-Process msiexec.exe -ArgumentList '/x `"$msi`" /qn /norestart' -Wait"
}
$lines += "`$p = Start-Process msiexec.exe -ArgumentList '$($installArgs -replace "'", "''")' -Wait -PassThru"
$lines += 'exit $p.ExitCode'
Set-Content -Path $step -Value $lines -Encoding UTF8

Write-Host 'Installing (approve the UAC prompt)...'
try {
    $p = Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$step`"" -Verb RunAs -Wait -PassThru
} finally { Remove-Item $step -ErrorAction SilentlyContinue }
if ($p.ExitCode -ne 0) { throw "Installer exit code $($p.ExitCode). See $log" }

$svc = $null
for ($i = 0; $i -lt 20 -and -not ($svc -and $svc.Status -eq 'Running'); $i++) {
    Start-Sleep 1
    $svc = Get-Service windows_exporter -ErrorAction SilentlyContinue
}
if (-not $svc) { throw "Installer finished but no windows_exporter service exists. See $log" }
Write-Host "Service: $($svc.Status) ($($svc.StartType))"
Get-NetTCPConnection -LocalPort 9182 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Write-Host "Listening on $($_.LocalAddress):$($_.LocalPort)" }
$fw = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like '*windows_exporter*' }
Write-Host ("Firewall rules for windows_exporter: {0}" -f @($fw).Count)
try {
    $m = (Invoke-WebRequest http://127.0.0.1:9182/metrics -UseBasicParsing -TimeoutSec 5).Content
    Write-Host ("Metrics endpoint OK ({0} lines)" -f ($m -split "`n").Count)
} catch { Write-Warning "Metrics endpoint not reachable yet: $($_.Exception.Message)" }
