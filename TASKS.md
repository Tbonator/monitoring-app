# Tasks

Status key: ✅ done and verified · 🟡 partially done · ⬜ not started

## Phase 1: Core monitoring MVP

| Task | Status | Notes |
|---|---|---|
| Inspect project directory | ✅ | Contained only `CLAUDE.md`. Used as the project root (ADR-001). |
| Verify Docker engine and Compose | ✅ | Docker 29.9.3, Compose v5.7.1, Docker Desktop VM with 4 CPUs and about 5.7 GiB RAM |
| Verify ports | ✅ | 3000, 3001, 8000, 9090, 9093 and 3100 were all free |
| Check system resources | ✅ | 11.9 GB total RAM, but only about 0.5 GB free at inspection time. 266 GB of free disk. |
| Create project structure | ✅ | Follows CLAUDE.md §7. Future components are placeholders. |
| Configure environment variables | ✅ | `.env.example` committed. `.env` has a generated random password and is git-ignored. |
| Configure Docker Compose | ✅ | Pinned images, `monitoring-network`, named volumes, 127.0.0.1 bindings, health checks, resource limits |
| Configure Prometheus | ✅ | Self-scrape, 15-day / 5 GB retention, `promtool` check passes |
| Configure Grafana provisioning | ✅ | Data source health is OK. Dashboard provisioned into the "Application Monitoring" folder. |
| Configure Uptime Kuma | ✅ | Wizard completed with Embedded SQLite and an admin account. |
| Start monitoring services | ✅ | All three containers report `healthy` |
| Verify persistence | ✅ | Prometheus samples and a Grafana test folder survived `docker compose down` and `up`. Uptime Kuma monitors and heartbeats survived a container restart. |
| Document local setup | ✅ | `docs/` |

### Phase 1 test results (2026-11-25)

| Test | Result |
|---|---|
| `docker compose config` | PASS |
| `promtool check config` (3 rule files, 0 rules) | PASS |
| Ports bound to 127.0.0.1 only | PASS |
| Prometheus `/-/healthy` and `/-/ready`, Grafana `/api/health`, Uptime Kuma `/` | PASS (HTTP 200) |
| Grafana data source health check | PASS |
| Grafana rejects unauthenticated API | PASS (401) |
| Prometheus target `up` = 1 | PASS |
| Persistence after container recreation (Prometheus, Grafana) | PASS |
| Persistence of Uptime Kuma | PASS (verified in Phase 2) |
| Grafana password not found in any file other than `.env` | PASS |
| No privileged containers | PASS |
| Git secret check | NOT APPLICABLE. The folder is not a Git repository yet. |

## Phase 2: Funeral application integration

| Task | Status | Notes |
|---|---|---|
| Review the Django project (read-only) and get approval | ✅ | Active copy: `Desktop\funeral app\funeralmanagementsystem` (untracked). Changes approved by the owner on 2026-11-25. |
| `/health/live/` and `/health/ready/` | ✅ | JSON responses. Ready returns 503 when the DB fails. |
| django-prometheus, with `/metrics` restricted | ✅ | `2.6.0.dev26` pre-release (ADR-009). Protected by a bearer token (ADR-010). |
| Prometheus target `funeral-back-office` | ✅ | `up` = 1 through `host.docker.internal:8000` |
| Validate container-to-host connectivity | ✅ | Works with Django bound to `127.0.0.1` only. No firewall rule needed. |
| Application Overview dashboard | ✅ | 24 panels. Every query verified by `tests/check_dashboard_queries.py`. |
| Alertmanager and initial alert rules | ✅ | 5 alerts and 6 recording rules. `null` receiver, so no notifications are sent. |
| Uptime Kuma monitors | ✅ | `Funeral Back Office - Live` (30 s) and `- Ready` (60 s, 2 retries), via `host.docker.internal:8000` |
| §17 test scenarios | ✅ | All pass. See below. |

### Phase 2 test results (2026-11-25)

| Test (CLAUDE.md §17) | Result | Evidence |
|---|---|---|
| Stop Django: failure detected | PASS (Prometheus) | Stopped 21:05:15. `ApplicationDown` pending at 21:05:28, firing at 21:05:58, and in Alertmanager as critical. |
| Restart Django: recovery detected | PASS (Prometheus) | `up` = 1 and the alert resolved at about 21:07:10 |
| Stop/restart detected by Uptime Kuma | PASS | Stopped 20:02:29 UTC. Live went Down, and Ready went Pending, Pending, Down. Restarted 20:06:08 UTC. Ready was Up at 20:06:47, and Live recovered in one interval. Checked with `tests/kuma_status.js`. |
| Generate HTTP 500: error metrics increase | PASS | 430 HTTP 500s gave a 5xx ratio of 17%. `HighErrorRate` (critical) fired at 21:17:42 and resolved after the traffic stopped. |
| Controlled slow requests: latency increases | PASS | 298 requests of 3 s each gave a P95 of 3.9 s. `SlowApplication` (warning) fired at 21:17:42 and resolved. |
| Database disconnect: readiness fails | PASS | `tests/test_readiness_db_failure.py`: ready 503, live 200, no leaked details |
| Monitoring container restart: data persists | PASS | Prometheus and Grafana (Phase 1). Uptime Kuma monitors and history (Phase 2). |
| Validate configuration | PASS | `validate.ps1`: Compose, promtool, amtool, dashboards, `.env`, ports |
| Exported metrics contain no personal data | PASS | All 345 series audited. Labels are view names only. |
| No secrets in Git | PASS | No secret files in history. Token and Grafana password not found in `git log -p`. |
| Real notifications not sent | PASS | Only the `null` receiver is configured |

### Phase 2 open items
- Uptime Kuma: set **Retries = 1** on the Live monitor. It is currently 0, so one failed check marks it down, while CLAUDE.md asks for two consecutive failures. Optionally switch Ready to the HTTP(s) - Keyword type.
- ~~Django 6.1.2 to 6.1.3 upgrade~~ Resolved: the owner kept 6.1.3, and the funeral app's `requirements.txt` was updated to match.
- django-prometheus is a pre-release. Move to 2.6.0 stable when it is published.
- Funeral app hygiene (not changed): hardcoded `SECRET_KEY`, `DEBUG=True`, and an active source tree that is untracked by Git.
- The DB query-metrics wrapper (`django_prometheus.db.backends.sqlite3`) is not enabled, so the dashboard's query-performance panel shows a notice instead of data.

## Phase 3: Error tracking and logging

| Task | Status | Notes |
|---|---|---|
| Introduce GlitchTip | ✅ | 6.2.6 all-in-one with PostgreSQL 18.7, on 127.0.0.1:8001. Healthy. Bootstrapped with `scripts/glitchtip-bootstrap.py`. |
| Configure Django error reporting | ✅ | sentry-sdk 3.0.1. Enabled only when `GLITCHTIP_DSN` is set. Every `data_collection` category is off (ADR-016). |
| Introduce Grafana Loki | ✅ | 3.7.10, 7-day retention, Grafana data source provisioned |
| Configure Grafana Alloy | ✅ | v1.22.0. Tails the daily JSON files through a read-only mount and adds a second redaction pass. |
| Structured logging | ✅ | `JsonFormatter` and `DailyFileHandler` (ADR-019) |
| Sensitive data filtering | ✅ | `RedactingFilter` in the app, Alloy `stage.replace`, and `before_send` for GlitchTip |
| Dashboard Logs section | ✅ | 28 panels. Every query verified, including Loki. |

### Phase 3 test results (2026-11-25)

| Test | Result | Evidence |
|---|---|---|
| Configuration validation | PASS | `validate.ps1` adds `loki -verify-config` and `alloy fmt` |
| Redaction unit test | PASS (12/12) | `tests/test_redaction.py`. Its first run **found a bearer-token leak**, which is now fixed. |
| Logs reach Loki through Alloy | PASS | Real request logs queryable, with paths shown as `/arrangements/:id/` and query strings removed |
| Exceptions reach GlitchTip | PASS | `ValueError: Simulated failure for ID [REDACTED_ID] / [REDACTED_EMAIL]` |
| End-to-end privacy (9 fake values: IDs, email, phone, name, cookies, bearer token) | PASS | `tests/test_privacy_end_to_end.py`. None in GlitchTip or Loki, no frame variables, and the request carries only method and URL. |
| Rename-based log rotation | **FAIL, design changed** | 0 of 60 lines shipped after rotation through the Docker Desktop mount. Replaced by daily files (ADR-019). |
| Daily file handler | PASS | `tests/test_log_rotation.py`: day switch, 7-day pruning, today's lines in Loki, and Alloy read the new file completely |
| Persistence after restarting Loki, Alloy and GlitchTip | PASS | GlitchTip still had 3 events, and Loki lines only increased (126 to 154) |
| All Prometheus targets up | PASS | alertmanager, alloy, funeral-back-office, loki, prometheus |

### Phase 3 open items
- Backdated test lines dated "yesterday" were not yet queryable when the test ran, because Loki only queries its in-memory ingesters for the last 3 hours. They are expected to appear after the chunk flushes. **Not yet re-verified.** This only affects backdated data.
- GlitchTip admin: `GLITCHTIP_ADMIN_EMAIL` / `GLITCHTIP_ADMIN_PASSWORD` in `.env`. Change the password after the first login.
- The old rotation-test files `funeral-back-office.log` and `.log.1` to `.log.5` remain in the app's `logs\` folder. They are no longer written to and are safe to delete.

## Phase 4: Advanced monitoring

| Task | Status | Notes |
|---|---|---|
| Infrastructure exporters: Docker VM | ✅ | Node Exporter v1.13.1. Read-only mounts, not privileged. CPU, memory and data disk. WSL mount noise filtered out. |
| Infrastructure exporters: Windows host | ✅ | Windows Exporter v0.32.1 runs as a service (Automatic), listening on **127.0.0.1:9182 only** with **0 firewall rules**. The first install attempt created an empty product because of an MSI quirk (ADR-027); the script is fixed. |
| PostgreSQL Exporter | ✅ | v0.21.1 on GlitchTip's DB, using the `monitoring` role (`pg_monitor`, read-only). Least privilege verified. |
| Blackbox Exporter | ✅ | v0.29.1. Probes 2 app endpoints and 5 platform components, all passing. TLS-expiry job is ready (no HTTPS targets yet). |
| Background workers | N/A | The funeral app has no workers, scheduled jobs or email sending |
| Backups monitored | ✅ | `backup.ps1` covers all 8 volumes and writes status metrics. First real run: 91 MB in 177 s, status OK. |
| Dashboard coverage | ✅ | Application Overview has an Infrastructure section (36 panels). Monitoring Platform Health is regenerated with host, PostgreSQL, backup and probe panels (27 panels). |
| WSL memory cap | 🟡 | `%UserProfile%\.wslconfig` sets `memory=4GB`. **Not applied yet:** the owner will run `wsl --shutdown` when convenient. |

### Phase 4 test results (2026-11-25)

| Test | Result | Evidence |
|---|---|---|
| Configuration validation | PASS | `validate.ps1`, which now also runs promtool unit tests and resolves images through Compose |
| Alert rule unit tests | PASS | HighCpu, HighMemory, DiskSpace, SslExpiry, BackupMissing, BackupFailed, ApplicationEndpointDown, PostgresDown and the ApplicationDown regression |
| Scrape targets up | PASS (16/16) | Includes `windows` after the install |
| Blackbox probes | PASS (7/7) | The Uptime Kuma probe first failed on its `/` to `/dashboard` redirect and was fixed with a redirect-following module |
| PostgreSQL monitoring user is least privilege | PASS | `pg_monitor` only. Reading table data was denied and writing was denied. |
| Backup run writes metrics, and Prometheus reads them | PASS | Backup age is visible. The textfile is atomic and git-ignored. |
| Dashboard queries | PASS | All return data except the 6 Windows-host panels, which wait on the install |
| **Bug found:** `ApplicationDown` fired for a down infrastructure exporter | FIXED | The rule now matches `kind="application"` only. Covered by a regression unit test. |
| Windows host metrics | PASS | CPU about 100%, matching Windows' own `Win32_Processor.LoadPercentage` (99-100%). Memory 95%, matching `Win32_OperatingSystem`. C: at 44.5%. All laptop panels show data in both dashboards. |
| Real alert, end to end | PASS | `HighCpuUsage` (dev-laptop) **fired at 23:52:45** under real load, was sent to Alertmanager (35 sent, 0 errors, 0 dropped) and resolved when CPU fell below 85% |

### Phase 4 open items
- **The laptop really is saturated:** CPU 80-100% and memory about 95% with the full stack, Chrome and VS Code running. Expect `HighCpuUsage` and `HighMemoryUsage` to fire. Applying the WSL cap will help.
- ~~CPU alert flaps near the threshold~~ Resolved: HighCpuUsage and HighMemoryUsage use `keep_firing_for: 5m`, covered by a unit test (still firing 3 min after recovery, resolved after 7 min).
- Right after the `windows` target came up, the memory and disk panels returned no data for about 2 minutes, then worked. Not reproducible since.
- Run `wsl --shutdown` to apply the 4 GB cap. This briefly stops all containers, including artex.
- Backups aren't scheduled. A daily Windows scheduled task needs owner approval. Note that the monitoring stack stops for about 3 minutes during each backup.
- Old backups are never deleted automatically.
- Docker Desktop's VM disk is a 1 TB virtual disk that grows on demand, while the physical C: drive is 498 GB. The Windows C: disk alert is the real guard against running out of space.

## Phase 5: Production readiness

| Task | Status | Notes |
|---|---|---|
| Design independent production infrastructure | ✅ | `docs/deployment.md`: a separate monitoring server, a private network to the app server, sizing and firewall (ADR-028) |
| Configure HTTPS | ✅ (tested locally) | Caddy 2.11.9 for Grafana and GlitchTip. Tested with Caddy's internal CA; Let's Encrypt needs a real domain. |
| Authentication and access controls | ✅ | Only Grafana and GlitchTip are public, both behind logins. Secure cookies, HSTS and sign-up disabled. Everything else is behind an SSH tunnel. |
| Backup and restore procedures | ✅ | `backup.sh` (Linux, retention), `restore.ps1` drill and live, and `restore.sh`. **The restore drill passed.** |
| Production retention | ✅ (configurable) | Metrics 30 d / 20 GB, logs 14 d, errors 30 d, backups 14 d. **The POPIA review of these periods is open.** |
| Deployment documentation | ✅ | Install, verify, update, rollback, restore and operating notes |
| Failure simulation | ✅ | Local only: exporter, database and Loki outages, alerts, recovery and no log loss |
| Security review | ✅ | `docs/security-review.md`: 2 high and 2 medium findings fixed, 1 low fixed, 3 medium and 5 low open |
| Actual production deployment | ⬜ | No server, domain or SMTP details yet. Placeholders must be filled in. |

### Phase 5 test results (2026-11-26)

| Test | Result | Evidence |
|---|---|---|
| Production configs validate | PASS | Prod overlay, Caddyfile, `alertmanager.prod.yml`, app-server bundle, and target files for both environments (11 jobs each) |
| Scrape-target refactor changes nothing in dev | PASS | 16 of 16 targets identical before and after |
| HTTPS overlay, local | PASS (16/16) | 308 redirect, certificate verifies, 4 security headers, `Server` header removed, API 401, GlitchTip over HTTPS, Prometheus not served, access log free of query strings, cookies and tokens, secure cookies, Caddy healthy |
| **Bug found:** access log leaked query strings | FIXED | Fake name and ID number were visible before the fix, absent after |
| Restore drill (backup of 2026-11-25 23:28) | PASS | 8 of 8 volumes restored. Prometheus replayed its WAL with 481 app series. PostgreSQL started with 3 events, 1 user and 1 project. Grafana and Kuma SQLite integrity OK, with 2 monitors and 268 heartbeats. Drill volumes removed. |
| Failure simulation | PASS | PostgresDown, InfrastructureExporterDown (node) and MonitoringComponentDown (loki) fired and reached Alertmanager, then resolved about 50 s after restart. All targets came back up. |
| **Bug found:** Alloy drops logs after about 8.5 min of Loki outage | FIXED | After the fix, a line logged during the outage arrived in Loki with 0 drops |
| **Finding:** GlitchTip `/_health/` is liveness-only | ACCEPTED | It stays 200 during a database outage; PostgresDown covers it |
| Hardening applied | PASS | 11 of 11 containers have `no-new-privileges` and are healthy. Blackbox runs as `nobody`. |

### Phase 5 open items
- Provide the production server, domains, SMTP details and recipients, then deploy following `docs/deployment.md`.
- Security review: **O1** monitoring of the monitoring (external heartbeat), **O2** encrypted off-host backups, **O3** funeral app hygiene.
- POPIA review of the retention periods.
- Schedule backups (cron on the server, or a Windows scheduled task in development). Both need owner approval.
- The WSL 4 GB cap still needs `wsl --shutdown`.

## Open issues

- **Low host memory:** 0.31 GB free with the full stack, Django and dev tools running. The stack itself uses about 887 MiB; most of the pressure comes from the Docker Desktop/WSL2 VM. Consider capping WSL2 memory in `%UserProfile%\.wslconfig`. That is a system-wide change, so it needs owner approval.
- The Uptime Kuma image runs as root. Evaluate the `-rootless` variant.
- ~~The project is not under Git version control yet.~~ Resolved: Git was initialised on 2026-11-25.
