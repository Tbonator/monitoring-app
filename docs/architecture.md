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
