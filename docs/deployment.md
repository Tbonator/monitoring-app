# Deployment

> Status: Phase 5. These notes are a plan and have not been implemented.

## Target production shape

- A dedicated Linux host or VM running Docker Engine, separate from the application servers, so a failure of one does not take down the other.
- A reverse proxy such as Caddy or nginx that terminates TLS for Grafana and Uptime Kuma, with authentication in front. Prometheus is not exposed publicly.
- Prometheus scrapes applications over a private network or VPN, using TLS and authentication on `/metrics` where possible.
- Environment-specific `.env` files: development, UAT and production.
- Off-host backups, with restore procedures that have been tested.
- Retention reviewed against operational, privacy and legal (POPIA) requirements.

## Reusing this repository

The same `docker-compose.yml` is used everywhere. Per-environment differences live in `.env`. A Compose override file is used only where needed, for example to add the reverse proxy.
