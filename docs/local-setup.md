# Local setup (Windows)

## Prerequisites

- Docker Desktop with the WSL2 backend, running
- PowerShell 5.1 or later
- Ports 3000, 3001 and 9090 free on 127.0.0.1
- About 1.5 GB of RAM to spare. Each container is limited to 512 MB.

## First run

```powershell
cd application-monitoring
Copy-Item .env.example .env
# Edit .env and set GRAFANA_ADMIN_PASSWORD to a long random value. To generate one:
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 32 | % {[char]$_})

.\scripts\validate.ps1
.\scripts\start.ps1
.\scripts\status.ps1
```

## First login

| Service | Steps |
|---|---|
| Grafana, http://localhost:3000 | Log in with `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` from `.env`. The Prometheus data source and the *Application Monitoring → Monitoring Platform Health* dashboard are already provisioned. |
| Uptime Kuma, http://localhost:3001 | The first visit opens the setup wizard. Choose **Embedded SQLite** as the database (lowest resource use), then create an admin account with a strong password. Uptime Kuma has no environment variable for preseeding this account. |
| GlitchTip, http://localhost:8001 | Log in with `GLITCHTIP_ADMIN_EMAIL` and `GLITCHTIP_ADMIN_PASSWORD` from `.env`, then change the password. On a fresh install, run `scripts/glitchtip-bootstrap.py` first; the docstring explains how, and the DSN is written to `secrets/`. |
| Prometheus, http://localhost:9090 | No login. It is reachable from localhost only. Check **Status → Targets**. |

## Day-to-day commands

| Task | Command |
|---|---|
| Start | `.\scripts\start.ps1` |
| Stop (keeps data) | `.\scripts\stop.ps1` |
| Status | `.\scripts\status.ps1` |
| Validate config | `.\scripts\validate.ps1` |
| Back up volumes | `.\scripts\backup.ps1` |
| Reload Prometheus config | `Invoke-RestMethod -Method Post http://127.0.0.1:9090/-/reload` |
| View logs | `docker compose logs -f prometheus` |

> Never use `docker compose down -v`. The `-v` flag deletes all monitoring data. `docker compose down` without `-v` is safe, because it removes containers but keeps the volumes.

## Upgrading an image

1. Check the release notes for breaking changes.
2. Change the version in `.env`, and in `.env.example` and the Compose defaults.
3. Run `.\scripts\backup.ps1`, then `docker compose pull`, then `docker compose up -d`.
4. Run `.\scripts\status.ps1`, then update `CHANGELOG.md`.
