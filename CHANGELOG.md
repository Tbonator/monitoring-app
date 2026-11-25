# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] - 2026-11-25 - Phase 1: Core monitoring MVP

### Added
- Docker Compose stack with Prometheus v3.16.0, Grafana OSS 13.3.2 and Uptime Kuma 2.5.12.
- Dedicated `monitoring-network` bridge network, and named volumes for every service's data.
- All published ports bound to `127.0.0.1`.
- Health checks, restart policies, resource limits, log rotation and graceful stop periods.
- Prometheus configuration with self-scrape, retention of 15 days / 5 GB, and placeholder rule files.
- Prometheus provisioned automatically as Grafana's default data source.
- Provisioned "Monitoring Platform Health" dashboard showing Prometheus scrape availability.
- PowerShell scripts: `start`, `stop`, `status`, `validate`, `backup`.
- `.env.example`, `.gitignore`, and documentation in `docs/`.
