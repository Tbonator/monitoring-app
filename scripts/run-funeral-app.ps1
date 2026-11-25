#Requires -Version 5.1
<#
.SYNOPSIS
  Runs the Funeral Back Office (Django dev server) with monitoring enabled:
  metrics token, GlitchTip DSN and environment label. Bound to 127.0.0.1 only.
.PARAMETER AppDir
  Django project directory (contains manage.py).
.PARAMETER Python
  Python interpreter of the app's pipenv environment.
.PARAMETER TestMode
  Adds the out-of-tree failure-simulation routes (tests/django_harness).
  Development only.
#>
param(
    [string]$AppDir = "$env:USERPROFILE\Desktop\funeral app\funeralmanagementsystem",
    [string]$Python = "$env:USERPROFILE\.virtualenvs\funeral_app-RXgBHIcv\Scripts\python.exe",
    [switch]$TestMode
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

$tokenFile = Join-Path $root 'secrets\funeral-back-office-metrics.token'
$dsnFile = Join-Path $root 'secrets\funeral-back-office-glitchtip.dsn'
if (Test-Path $tokenFile) { $env:MONITORING_METRICS_TOKEN = (Get-Content $tokenFile -Raw).Trim() }
else { Write-Warning "No metrics token at $tokenFile - /metrics will be disabled (404)." }
if (Test-Path $dsnFile) { $env:GLITCHTIP_DSN = (Get-Content $dsnFile -Raw).Trim() }
else { Write-Warning "No GlitchTip DSN at $dsnFile - error tracking disabled." }
$env:MONITORING_ENVIRONMENT = 'development'

if ($TestMode) {
    Write-Warning 'TEST MODE: failure-simulation routes enabled. Development only.'
    $env:PYTHONPATH = Join-Path $root 'tests\django_harness'
    $env:DJANGO_SETTINGS_MODULE = 'monitoring_test_settings'
}

Set-Location $AppDir
& $Python manage.py runserver 127.0.0.1:8000 --noreload
