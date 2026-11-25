# Architecture

## Phase 1 components

```text
 Windows host (127.0.0.1 only)
 ┌──────────────────────────────────────────────────────────────┐
 │  Docker Desktop (WSL2)        network: monitoring-network    │
 │                                                              │
 │  ┌────────────┐   PromQL   ┌─────────────┐                   │
 │  │  Grafana   │──────────▶│ Prometheus  │── self-scrape      │
 │  │   :3000    │           │   :9090     │                    │
 │  └────────────┘           └──────┬──────┘                    │
 │  ┌────────────┐                  │ (Phase 2) scrape /metrics │
 │  │ Uptime Kuma│── HTTP checks ───┤                           │
 │  │   :3001    │   (Phase 2)      │                           │
 │  └────────────┘                  ▼                           │
 │                      host.docker.internal:8000               │
 └──────────────────────────────────┼───────────────────────────┘
                                    ▼
                 Funeral Back Office (Django, runs on Windows)
```

| Component | Responsibility | Persistent volume |
|---|---|---|
| Prometheus | Collects and stores metrics using pull-based scraping | `monitoring-prometheus-data` |
| Grafana OSS | Shows dashboards. Its data source and dashboards are provisioned from files. | `monitoring-grafana-data` |
| Uptime Kuma | Runs external availability checks (HTTP, TCP) and stores the up/down history | `monitoring-uptime-kuma-data` |
| Alertmanager (Phase 2) | Receives alerts from Prometheus, then groups, deduplicates, inhibits and suppresses repeats. Has no notification receivers yet. | `monitoring-alertmanager-data` |

| Loki (Phase 3) | Log storage with 7-day retention, enforced by the compactor | `monitoring-loki-data` |
| Alloy (Phase 3) | Tails the app's `logs\*-YYYY-MM-DD.log` through a read-only bind mount, redacts a second time, and pushes to Loki | `monitoring-alloy-data` (read positions) |
| GlitchTip and PostgreSQL (Phase 3) | Exception tracking. Web and worker run in one container; the queue and cache live in Postgres. | `monitoring-glitchtip-postgres-data`, `monitoring-glitchtip-uploads` |

Phase 3 data flow:
- **Logs:** Django on Windows passes each record through `RedactingFilter`, then `JsonFormatter`, then into a daily file. Alloy reads the file through a read-only mount, redacts again and sends to Loki. Grafana queries Loki.
- **Errors:** Django runs sentry-sdk with `data_collection` off and a `before_send` that redacts. It sends errors to `http://localhost:8001`, the GlitchTip port published on Windows loopback.

Phase 2 data flow: Prometheus scrapes `http://host.docker.internal:8000/metrics` every 15 s using a bearer token. It evaluates `prometheus/rules/*.yml` and sends firing alerts to `alertmanager:9093`. Grafana's *Application Overview* dashboard queries Prometheus, filtered by the `application` and `environment` labels.

## Two kinds of availability

- **Uptime Kuma availability** asks whether the application answers its health endpoint from the outside. Use it as the user-facing up/down signal.
- **Prometheus scrape availability** (the `up` metric) asks whether Prometheus could scrape the target's `/metrics` endpoint. It shows whether metrics are being collected. It is not proof that users can reach the application.

Dashboards label these two signals separately.

## Independence

- The monitoring stack runs in its own Compose project, network and volumes. Nothing from it is installed into the monitored application except the Phase 2 instrumentation library.
- A failure of a monitored application only makes its target go `down`. The monitoring stack keeps running.
- Limitation: during local development everything runs on one laptop, so a host failure takes down both systems. Production should use separate infrastructure. See [deployment.md](deployment.md).

## Configuration layout

- `prometheus/prometheus.yml`: scrape targets, identified by `application` and `environment` labels
- `prometheus/rules/*.yml`: alert rules (empty in Phase 1)
- `grafana/provisioning/`: data source and dashboard provider
- `grafana/dashboards/*.json`: version-controlled dashboards
- `.env`: versions, ports, retention and credentials (not committed)
