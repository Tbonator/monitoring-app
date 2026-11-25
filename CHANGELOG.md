# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-11-25 - Phase 2: Funeral Back Office integration

### Added
- Funeral Back Office instrumentation: `django-prometheus==2.6.0.dev26`, `/health/live/` and `/health/ready/` (which returns 503 when the DB is unavailable), and a bearer-token-protected `/metrics`.
- Prometheus job `funeral-back-office`, using `host.docker.internal:8000` and a token read from `secrets/`.
- Alertmanager v0.35.1 (127.0.0.1:9093) with a `null` receiver, grouping, inhibition and repeat suppression.
- Alert rules: `ApplicationDown`, `ApplicationReadinessFailure`, `DatabaseUnavailable`, `HighErrorRate` and `SlowApplication`. Thresholds are kept in recording rules.
- Provisioned *Application Overview* dashboard with five sections: overview, performance, database, infrastructure and incidents.
- An out-of-tree Django test harness, plus scripts for readiness, traffic and dashboard-query testing.
- Reusable Django integration in `integrations/django/`.

### Changed
- `validate.ps1` mirrors the Compose mounts and also runs `amtool check-config`.
- `alertmanager/alertmanager.yml` is now committed. It contains no secrets.

### Funeral Back Office side effects
- `pipenv install` re-locked the Pipfile, where Django is `*`, and upgraded Django from 6.1.2 to **6.1.3**. The owner chose to keep 6.1.3, and `requirements.txt` was updated to `Django==6.1.3`.

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
