# Exporters (Phase 4)

| Exporter | Runs | Scrape target | Measures |
|---|---|---|---|
| Node Exporter v1.13.1 | Container | `node-exporter:9100` | Docker Desktop VM (host of the monitoring stack): CPU, memory, disk. Also reads backup status from `textfile/` |
| Blackbox Exporter v0.29.1 | Container, config `blackbox/blackbox.yml` | `blackbox-exporter:9115` | HTTP probes of health endpoints. Checks TLS certificate expiry for targets in `prometheus/targets/tls-targets.yml` |
| PostgreSQL Exporter v0.21.1 | Container | `postgres-exporter:9187` | GlitchTip's PostgreSQL, through the read-only `pg_monitor` user `monitoring` |
| Windows Exporter v0.32.1 | Windows service (MSI) | `host.docker.internal:9182` | The Windows laptop where Django runs: CPU, memory, disk, network |
