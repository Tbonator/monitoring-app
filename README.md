# Application Monitoring Platform

A standalone, open-source technical monitoring platform. The first application it will monitor is the **Funeral Back Office System** (a Django application).

**Current phase:** Phase 1, the core monitoring MVP. It provides the monitoring stack only. No application is integrated yet.

| Service | URL (local only) | Purpose |
|---|---|---|
| Grafana OSS 13.3.2 | http://localhost:3000 | Dashboards |
| Uptime Kuma 2.5.12 | http://localhost:3001 | Availability checks |
| Prometheus v3.16.0 | http://localhost:9090 | Metrics collection and storage |

## Quick start (PowerShell)

```powershell
Copy-Item .env.example .env      # then set GRAFANA_ADMIN_PASSWORD to a long random value
.\scripts\validate.ps1           # validate configuration
.\scripts\start.ps1              # check ports, validate, start
.\scripts\status.ps1             # health of each service and Prometheus targets
.\scripts\stop.ps1               # graceful stop; data volumes are kept
.\scripts\backup.ps1             # back up volumes to .\backups\<timestamp>\
```

If PowerShell blocks the scripts, run them with `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1`.

## Documentation

- [docs/local-setup.md](docs/local-setup.md): installation and first-run steps
- [docs/architecture.md](docs/architecture.md): components and data flow
- [docs/application-integration.md](docs/application-integration.md): how to connect an application (Phase 2)
- [docs/security.md](docs/security.md): security and privacy controls
- [docs/troubleshooting.md](docs/troubleshooting.md): common problems and fixes
- [docs/deployment.md](docs/deployment.md): notes for future production deployment
- [docs/decisions.md](docs/decisions.md): architecture decision log
- [TASKS.md](TASKS.md) and [CHANGELOG.md](CHANGELOG.md)
