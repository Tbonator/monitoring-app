# Production deployment

> **Status:** the configuration is ready and has been tested locally (the HTTPS overlay, a restore drill and failure simulation). It has **not been deployed** yet: no production server exists. Placeholders (`example.co.za`, `10.0.0.x`) must be replaced.

## 1. Target architecture

```text
            Internet (HTTPS only)
                  │ 443
        ┌─────────▼──────────────── MONITORING SERVER (Linux, Docker Engine) ──┐
        │  Caddy ──► Grafana        (grafana.example.co.za)                    │
        │        └─► GlitchTip      (errors.example.co.za)                     │
        │  Prometheus · Alertmanager · Loki · Uptime Kuma · exporters          │
        │  (127.0.0.1 only; administrators connect with an SSH tunnel)         │
        │  Loki :3100 also on the PRIVATE IP (log pushes from the app server)  │
        └─────────▲──────────────────────────▲─────────────────────────────────┘
                  │ private network / VPN     │ scrape :8000/metrics, :9100, :12345
        ┌─────────┴──────────────────────────┴── APP SERVER ───────────────────┐
        │  Funeral Back Office (Django) ── errors ──► https://errors.example…  │
        │  deploy/app-server: Alloy (logs → Loki), node-exporter (host metrics)│
        └──────────────────────────────────────────────────────────────────────┘
```

The monitoring server is **separate** from the app server, so a failure of one doesn't take down the other (CLAUDE.md §5).

## 2. Sizing (starting point)

| | Monitoring server | App server agents |
|---|---|---|
| CPU / RAM | 2 vCPU / 4 GB | about 0.3 GB for Alloy and node-exporter |
| Disk | 60 GB SSD: Prometheus up to 20 GB, Loki and GlitchTip about 10 GB, plus backups | logs (7 days) |
| OS | Ubuntu 24.04 LTS or Debian 12, Docker Engine and the Compose plugin | same |

## 3. Network and firewall

| Port | Monitoring server allows | App server allows |
|---|---|---|
| 22 | admin IPs only | admin IPs only |
| 80, 443 | internet (Caddy, for Let's Encrypt and HTTPS) | per the app's own needs |
| 3100 | **app server private IP only** (Loki push) | none |
| 8000, 9100, 12345 | none | **monitoring server private IP only** |

Everything else is closed. Prometheus, Alertmanager, Loki (public side) and Uptime Kuma are reached through an SSH tunnel:

```bash
ssh -L 9090:127.0.0.1:9090 -L 9093:127.0.0.1:9093 -L 3001:127.0.0.1:3001 admin@monitoring-server
```

DNS: `grafana.example.co.za` and `errors.example.co.za` point to the monitoring server's public IP (A/AAAA records).

## 4. Install the monitoring server

```bash
git clone <repo> /opt/application-monitoring && cd /opt/application-monitoring
cp deploy/production.env.example .env.prod && chmod 600 .env.prod
# Edit .env.prod: domains, ACME e-mail, private IP, retention and fresh random credentials
#   (openssl rand -base64 32 | tr -dc A-Za-z0-9 | head -c 32)
mkdir -p secrets && chmod 700 secrets
openssl rand -hex 24 > secrets/funeral-back-office-metrics.token   # same value goes in the app's MONITORING_METRICS_TOKEN
openssl rand -hex 24 > secrets/pg-monitor-password
printf '%s' '<smtp password>' > secrets/smtp-password
chmod 600 secrets/*
# Edit prometheus/targets/production/*.yml (APP_SERVER_PRIVATE_IP, hostnames)
# Edit alertmanager/alertmanager.prod.yml (SMTP host, from address, recipients)

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod"
$COMPOSE config --quiet && $COMPOSE up -d
```

First-time setup after the containers start:

1. **GlitchTip:** run `scripts/glitchtip-bootstrap.py` (see its docstring). This creates the admin, organization and project, and prints the DSN.
2. **PostgreSQL monitoring user:** run `scripts/postgres-monitoring-user.sql` against `glitchtip-postgres` (see the comment at the top of the file).
3. **Uptime Kuma:** open it through the SSH tunnel at <http://localhost:3001>, choose Embedded SQLite, create the admin, and add monitors for the app's `/health/live/` and `/health/ready/`.
4. **Grafana:** log in at `https://grafana.example.co.za` and change the admin password. Create named user accounts; the default role is Viewer.

## 5. Install the app-server agents

```bash
cd deploy/app-server && cp app-server.env.example app-server.env   # edit IPs and APP_LOG_DIR
docker compose --env-file app-server.env up -d
```

Configure the Django app (see `docs/application-integration.md`):

| Variable | Production value |
|---|---|
| `MONITORING_METRICS_TOKEN` | The contents of `secrets/funeral-back-office-metrics.token` |
| `GLITCHTIP_DSN` | The DSN from the bootstrap, using `https://errors.example.co.za/...` |
| `MONITORING_ENVIRONMENT` | `production` |
| `APP_LOG_DIR` | Same as `APP_LOG_DIR` in `app-server.env` |

Django must listen on the private interface (or behind its own reverse proxy) so that Prometheus can scrape `:8000/metrics` over the private network.

## 6. Verify

```bash
$COMPOSE ps                                   # all healthy
curl -I https://grafana.example.co.za         # 200/302 over a valid certificate
# Through the SSH tunnel: http://localhost:9090/targets -> every target up
# Alertmanager: send ONE controlled test alert only with approval (CLAUDE.md §13)
```

Locally, `tests/test_https_prod_overlay.ps1` exercises the same overlay with `tls internal`.

## 7. Retention (production defaults; review for POPIA)

| Data | Setting | Production | Development |
|---|---|---|---|
| Metrics | `PROMETHEUS_RETENTION_TIME` / `_SIZE` | 30 days / 20 GB | 15 days / 5 GB |
| Logs | `LOKI_RETENTION_PERIOD` | 336h (14 days) | 168h (7 days) |
| Error events | `GLITCHTIP_RETENTION_DAYS` | 30 days | 30 days |
| App log files | `APP_LOG_RETENTION_DAYS` (Django) | 7 days | 7 days |
| Backups | `KEEP_DAYS` (`backup.sh`) | 14 days | manual |

Logs and error events are redacted at the source (Phase 3), but they're still operational records about how a system handling personal information is used. Confirm these periods with whoever is responsible for POPIA compliance.

## 8. Backups

```bash
# Daily at 02:30 (cron on the monitoring server). Monitoring pauses for about 1-3 min.
30 2 * * * cd /opt/application-monitoring && COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod" ./scripts/backup.sh >> /var/log/monitoring-backup.log 2>&1
```

- **Contents:** every volume, including Caddy's certificates and GlitchTip's database. Archives are `chmod 600`.
- **Alerts:** `BackupMissing` (more than 24 h), `BackupFailed` and `BackupStatusMissing`.
- **Off-host copies:** these are **still needed** (security review O2). Archives on the same server don't survive the loss of the server.

## 9. Restore procedure

1. **Rehearse first.** Copy the backup folder to a workstation and run a drill:
   ```powershell
   .\scripts\restore.ps1 -BackupDir <folder>
   ```
   The drill restores into temporary volumes and verifies the data: Prometheus WAL replay, PostgreSQL start, SQLite integrity. Live data isn't touched.
2. **On the server:** run
   ```bash
   COMPOSE="..." ./scripts/restore.sh backups/<timestamp> [volume ...]
   ```
   It asks you to type `RESTORE`, then stops the stack, replaces the volumes and starts the stack again.
3. **Verify:** check that targets are up, the Grafana login works, GlitchTip issues are present and Uptime Kuma monitors exist.
4. If restoring onto a **new server**, follow sections 4-5 first. DNS must point to the new IP before Caddy can get certificates.

The tested drill result is recorded in TASKS.md.

## 10. Updates and rollback

1. Read the release notes. Change the pinned version in `.env.prod` or the Compose defaults.
2. Run `./scripts/backup.sh`, then `$COMPOSE pull && $COMPOSE up -d`.
3. Verify (section 6) and re-run the privacy tests from a workstation after any update to the SDK or exporters.
4. **To roll back:** restore the previous version string, then run `$COMPOSE up -d`. If the data format changed, restore the pre-update backup (section 9).

## 11. Operating notes

- Never run `docker compose down -v`; it deletes all data volumes.
- Never simulate failures against production. Use the local `tests/failure_simulation.ps1`.
- If Prometheus or Alertmanager itself fails, **nothing alerts** until an external heartbeat exists (security review O1).
