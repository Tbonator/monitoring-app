# Architecture decision log

## ADR-001: Use the existing folder as the project root
- **Date:** 2026-11-25
- **Decision:** The project is built in the current workspace folder, which already contained `CLAUDE.md`, instead of a nested `application-monitoring/` folder. The Compose project name is `application-monitoring`.
- **Reason:** This avoids duplicating `CLAUDE.md` and matches the structure in CLAUDE.md §7, which puts `CLAUDE.md` at the project root.

## ADR-002: Pinned image versions
- **Date:** 2026-11-25
- **Decision:** Prometheus `v3.16.0`, Grafana OSS `13.3.2` and Uptime Kuma `2.5.12`.
- **Reason:** These were the latest stable, non-RC releases on Docker Hub on the decision date. Uptime Kuma 3.0 is still in beta, so the stable 2.x line was chosen.

## ADR-003: Uptime Kuma uses embedded SQLite
- **Decision:** Choose Embedded SQLite in the Uptime Kuma 2.x setup wizard. Do not run a MariaDB container.
- **Reason:** It uses the least resources and avoids an extra container, which matters on a laptop with limited RAM. Revisit for production if needed.

## ADR-004: Use the image's built-in Uptime Kuma health check
- **Decision:** Do not override the healthcheck defined in the Uptime Kuma image.
- **Reason:** The upstream healthcheck is maintained alongside the application.

## ADR-005: Localhost-only bindings and host.docker.internal
- **Decision:** Bind every port to `127.0.0.1`. Prometheus and Uptime Kuma map `host.docker.internal` to `host-gateway` so they can reach applications running directly on Windows.
- **Reason:** This keeps admin interfaces off the LAN. Django on Windows is not containerised, and `localhost` inside a container does not refer to the host.

## ADR-006: Phase 1 dashboard scope
- **Decision:** Phase 1 ships only a "Monitoring Platform Health" dashboard, which shows real Prometheus scrape data. The full Application Overview dashboard is built in Phase 2, when application metrics exist.
- **Reason:** CLAUDE.md §11 forbids presenting placeholder or demo values as monitoring results.

## ADR-008: Grafana memory limit of 768 MB
- **Decision:** Grafana's memory limit is 768 MB. Prometheus and Uptime Kuma are limited to 512 MB each.
- **Reason:** Grafana 13.3.2 was measured at about 420 MiB shortly after its first start, which leaves too little headroom under 512 MB.

## ADR-007: Empty alert rule files in Phase 1
- **Decision:** The rule files exist with `groups: []`. Alertmanager is not deployed.
- **Reason:** Alertmanager is approved for Phase 2. Rules without application metrics would be meaningless.
