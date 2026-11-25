# Security review: Phase 5

**Date:** 2026-11-26
**Scope:** the monitoring platform repository, in both the development and production Compose configurations, plus its integration with the Funeral Back Office System.
**Method:** an automated audit of the resolved Compose configs, plus live tests: the HTTPS overlay, privacy injection, a restore drill and failure simulation. Each finding below was reproduced by a test unless marked "review".

## Summary

| Severity | Found | Fixed in Phase 5 | Open (owner decision or later work) |
|---|---:|---:|---:|
| High | 2 | 2 | 0 |
| Medium | 5 | 2 | 3 |
| Low | 6 | 1 | 5 |

## Fixed

| ID | Severity | Finding | Fix | Verified by |
|---|---|---|---|---|
| F1 | High | The Caddy access log recorded **full query strings**, for example a search for a name and an ID number. The `query` filter has no wildcard, so `replace *` did nothing. | A `regexp` filter removes everything after `?`. Cookie and Authorization headers are deleted from the log. | `tests/test_https_prod_overlay.ps1`: 4 fake values are absent from the log |
| F2 | High | Alloy's default retries (10 attempts, backoff up to 5 min) **give up after about 8.5 minutes**. A longer Loki outage would silently drop application logs. | Both Alloy configs use `max_backoff_period=30s` and `max_backoff_retries=60`, giving about 30 minutes of tolerance. | `tests/failure_simulation.ps1`: a log line written during a Loki outage arrives afterwards (0 dropped) |
| F3 | Medium | No container had `no-new-privileges`. | Added to all services in the dev, production and app-server Compose files. | All 11 dev containers recreated and healthy, with 11 of 11 carrying the option |
| F4 | Medium | Blackbox Exporter ran as root (image default) without needing to. | `user: nobody` | All 7 probes still pass |
| F5 | Low | Caddy's health check probed `:80`, which redirects to HTTPS for every host, so the container was always "unhealthy". | An internal, unpublished `:8080/healthz` | HTTPS test: Caddy is healthy |

## Open

| ID | Severity | Finding | Recommendation |
|---|---|---|---|
| O1 | Medium | **No monitoring of the monitoring.** If Prometheus or Alertmanager is down, nothing alerts. | Add an external "dead man's switch": an always-firing Watchdog alert sent to an external heartbeat service, or a monitor on a separate host. This needs a new service, so it needs approval. |
| O2 | Medium | **Backups are unencrypted and stored on the same host** as the data. | Make encrypted off-host copies (for example restic or age to object storage) and schedule `backup.sh` daily. This is a new tool and storage, so it needs approval. |
| O3 | Medium | **Funeral app hygiene**, outside this platform's scope: a hard-coded `SECRET_KEY`, `DEBUG=True`, and an active source tree not tracked by Git. | Fix before any hosted use. Treat the current key as compromised. |
| O4 | Low | These images run as root by default: Uptime Kuma, Alloy and Caddy. PostgreSQL drops to its own user internally. | Uptime Kuma has a `-rootless` variant (migration needs testing). Caddy needs root for ports 80/443; consider `cap_add: NET_BIND_SERVICE` with a non-root user. Alloy needs read access to the log files. |
| O5 | Low | Pushes to Loki (app server to monitoring server) and `/metrics` scrapes use plain HTTP **on the private network**. | Acceptable when the private link is encrypted (WireGuard/Tailscale). Otherwise put Loki behind Caddy with basic auth or mTLS. |
| O6 | Low | GlitchTip's `/_health/` only checks that the process is alive, and stays 200 while its database is down. | Accepted: `PostgresDown` (critical) detects the database outage. Shown by the failure simulation. |
| O7 | Low | The Docker Desktop VM disk is a 1 TB virtual disk while the physical C: drive is 498 GB. | Use the Windows C: disk alert (`DiskSpaceCritical`). Development only. |
| O8 | Low | django-prometheus 2.6.0.dev26 and sentry-sdk 3.0.1 are new or pre-release. | Re-run `test_redaction.py` and `test_privacy_end_to_end.py` after every upgrade. Move to 2.6.0 stable when it's released. |

## Checks performed

| Area | Result |
|---|---|
| Privileged containers, added capabilities, Docker socket mounts | None, in dev and prod |
| Writable bind mounts | None. Every config and secret mount is `:ro`. |
| Image pinning | All images pinned to exact versions, in dev and prod |
| Port exposure (prod) | Only Caddy on 0.0.0.0:80/443. Loki on the private IP. Everything else on 127.0.0.1. |
| Port exposure (dev) | Everything on 127.0.0.1. `validate.ps1` enforces this. |
| HTTPS | 308 redirect, a valid certificate, HSTS, nosniff, frame and referrer headers, and the `Server` header removed |
| Authentication | Grafana API returns 401 without login. Sign-up is disabled in Grafana and GlitchTip. Secure cookies are on in prod. |
| Internal UIs not exposed | Prometheus, Alertmanager, Loki and Uptime Kuma get no TLS response through Caddy |
| Secrets in Git | None in history (checked by file name). `.env`, `secrets/`, `backups/` and `downloads/` are ignored. |
| Personal data in metrics, logs and errors | Phase 2 label audit, Phase 3 privacy injection (9 values), and the Phase 5 access-log test all pass |
| Least privilege, database | The `monitoring` role (`pg_monitor`) cannot read table data or write |
| Least privilege, Windows Exporter | 127.0.0.1 only and no firewall rule |
| Backups and restore | The restore drill restores all 8 volumes and verifies the data, including a Prometheus WAL replay (481 series) and a PostgreSQL start |
| Failure handling | Exporter, database and Loki outages raise alerts and recover. No log loss. See TASKS.md. |

## Local development limitations (accepted)

- **No failure isolation:** monitoring, the app and the database share one laptop.
- **Plain HTTP:** dev traffic uses HTTP on loopback only.
- **Host under pressure:** the laptop runs at 80-100% CPU and about 95% memory under the full stack, so the alerts fire genuinely.
