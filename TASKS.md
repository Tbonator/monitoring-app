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

- ⬜ Locate and review the Funeral Back Office Django project (read-only), then request approval for changes
- ⬜ Implement `/health/live/` and `/health/ready/`
- ⬜ Install and configure django-prometheus, and restrict `/metrics`
- ⬜ Add the Prometheus target `funeral-back-office`
- ⬜ Add Uptime Kuma monitors for the health endpoints
- ⬜ Validate container-to-host connectivity (`host.docker.internal`)
- ⬜ Build the Application Overview dashboard
- ⬜ Introduce Alertmanager and the initial alert rules
- ⬜ Run the §17 test scenarios

## Phases 3–5

See CLAUDE.md §16.

## Open issues

- Free host RAM was low (about 0.5 GB) at inspection time. Monitor this while Django, the database and the stack all run together.
- The Uptime Kuma image runs as root. Evaluate the `-rootless` variant.
- The project is not under Git version control yet.
