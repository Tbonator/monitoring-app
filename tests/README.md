# Tests

These tests are for development only. Never run them against production.

| Test | Command |
|---|---|
| Configuration validation | `.\scripts\validate.ps1` |
| Service health | `.\scripts\status.ps1` |
| Dashboard queries return data | `python -I tests\check_dashboard_queries.py` |
| Django settings snippet only appends, wraps all middleware, accepts tuples, safe to re-apply | `python -I tests\test_example_settings.py` |
| Uptime Kuma monitor and heartbeat state (read-only) | `Get-Content tests\kuma_status.js -Raw \| docker exec -i uptime-kuma node -` |
| Redaction rules (fake data) | `& $py tests\test_redaction.py`, with `$env:FUNERAL_APP_DIR` set |
| Daily log files: switch, prune, ingest | `& $py tests\test_log_rotation.py`, with `$env:FUNERAL_APP_DIR` set |
| End-to-end privacy (GlitchTip and Loki) | Start the app with `.\scripts\run-funeral-app.ps1 -TestMode`, then run `python -I tests\test_privacy_end_to_end.py` |
| Readiness reports a database failure (503, no leaks) | see below |
| HTTP 500 and slow-request metrics and alerts | see below |

Throughout this guide, `$py` is the funeral app's pipenv Python:

```powershell
$py = "$env:USERPROFILE\.virtualenvs\funeral_app-RXgBHIcv\Scripts\python.exe"
```

## Readiness database-failure test

```powershell
$env:FUNERAL_APP_DIR = "$env:USERPROFILE\Desktop\funeral app\funeralmanagementsystem"
& $py tests\test_readiness_db_failure.py
```

## Error and latency test

1. Run Django in test mode, which adds the harness routes. The app code is not changed.

   ```powershell
   $env:MONITORING_METRICS_TOKEN = Get-Content secrets\funeral-back-office-metrics.token -Raw
   $env:PYTHONPATH = "$PWD\tests\django_harness"
   $env:DJANGO_SETTINGS_MODULE = "monitoring_test_settings"
   & $py "$env:FUNERAL_APP_DIR\manage.py" runserver 127.0.0.1:8000 --noreload
   ```

2. In a second terminal, run `python -I tests\generate_test_traffic.py 7.5`. It refuses non-local targets.
3. After about 6 minutes, `HighErrorRate` and `SlowApplication` should be firing. Check http://localhost:9093.
4. Stop the test-mode server, then restart Django normally.

Results are recorded in [TASKS.md](../TASKS.md).
