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
| Configure Uptime Kuma | 🟡 | Container is healthy. **The setup wizard and admin account must be completed manually.** Choose Embedded SQLite. |
| Start monitoring services | ✅ | All three containers report `healthy` |
| Verify persistence | 🟡 | Prometheus samples and a Grafana test folder survived `docker compose down` and `up`. Uptime Kuma persistence can only be tested after the wizard has run. |
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
| Persistence of Uptime Kuma | NOT TESTED (needs the wizard) |
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
| Uptime Kuma monitors | 🟡 | **Blocked: the setup wizard hasn't been run yet.** Monitor specs are in `docs/application-integration.md`. |
| §17 test scenarios | 🟡 | See below |

### Phase 2 test results (2026-11-25)

| Test (CLAUDE.md §17) | Result | Evidence |
|---|---|---|
| Stop Django: failure detected | PASS (Prometheus) | Stopped 21:05:15. `ApplicationDown` pending at 21:05:28, firing at 21:05:58, and in Alertmanager as critical. |
| Restart Django: recovery detected | PASS (Prometheus) | `up` = 1 and the alert resolved at about 21:07:10 |
| Stop/restart detected by Uptime Kuma | NOT TESTED | Needs the wizard and the monitors |
| Generate HTTP 500: error metrics increase | PASS | 430 HTTP 500s gave a 5xx ratio of 17%. `HighErrorRate` (critical) fired at 21:17:42 and resolved after the traffic stopped. |
| Controlled slow requests: latency increases | PASS | 298 requests of 3 s each gave a P95 of 3.9 s. `SlowApplication` (warning) fired at 21:17:42 and resolved. |
| Database disconnect: readiness fails | PASS | `tests/test_readiness_db_failure.py`: ready 503, live 200, no leaked details |
| Monitoring container restart: data persists | PASS (Phase 1) | Prometheus and Grafana only. Uptime Kuma is still pending. |
| Validate configuration | PASS | `validate.ps1`: Compose, promtool, amtool, dashboards, `.env`, ports |
| Exported metrics contain no personal data | PASS | All 345 series audited. Labels are view names only. |
| No secrets in Git | PASS | No secret files in history. Token and Grafana password not found in `git log -p`. |
| Real notifications not sent | PASS | Only the `null` receiver is configured |

### Phase 2 open items
- Run the Uptime Kuma setup wizard and add the two monitors, then run the stop/restart test through Kuma.
- ~~Django 6.1.2 to 6.1.3 upgrade~~ Resolved: the owner kept 6.1.3, and the funeral app's `requirements.txt` was updated to match.
- django-prometheus is a pre-release. Move to 2.6.0 stable when it is published.
- Funeral app hygiene (not changed): hardcoded `SECRET_KEY`, `DEBUG=True`, and an active source tree that is untracked by Git.
- The DB query-metrics wrapper (`django_prometheus.db.backends.sqlite3`) is not enabled, so the dashboard's query-performance panel shows a notice instead of data.

## Phases 3–5

See CLAUDE.md §16.

## Open issues

- Free host RAM was low (about 0.5 GB) at inspection time. Monitor this while Django, the database and the stack all run together.
- The Uptime Kuma image runs as root. Evaluate the `-rootless` variant.
- ~~The project is not under Git version control yet.~~ Resolved: Git was initialised on 2026-11-25.
