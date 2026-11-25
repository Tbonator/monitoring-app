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

## Phases 4–5

See CLAUDE.md §16.

## Open issues

- **Low host memory:** 0.31 GB free with the full stack, Django and dev tools running. The stack itself uses about 887 MiB; most of the pressure comes from the Docker Desktop/WSL2 VM. Consider capping WSL2 memory in `%UserProfile%\.wslconfig`. That is a system-wide change, so it needs owner approval.
- The Uptime Kuma image runs as root. Evaluate the `-rootless` variant.
- ~~The project is not under Git version control yet.~~ Resolved: Git was initialised on 2026-11-25.
