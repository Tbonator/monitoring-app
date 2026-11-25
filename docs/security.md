# Security and privacy

The monitored Funeral Back Office System processes sensitive personal information, so POPIA applies. The monitoring platform must never collect or expose that information.

## Controls in place (Phase 1)

| Control | Implementation |
|---|---|
| No network exposure | Every published port is bound to `127.0.0.1`. `validate.ps1` enforces this. |
| Secrets kept out of Git | Credentials live in `.env`, which is git-ignored. `.env.example` holds placeholders only. |
| No default passwords | Compose refuses to start if `GRAFANA_ADMIN_USER` or `GRAFANA_ADMIN_PASSWORD` is unset. `validate.ps1` rejects placeholder values. |
| Grafana hardening | Sign-up is disabled, anonymous access is disabled, telemetry and update checks are off, Gravatar is off, and cookies use SameSite=strict. |
| Read-only configuration | Prometheus and Grafana configuration is mounted `:ro`. |
| Least privilege | No privileged containers and no Docker socket mount. Prometheus runs as `nobody` and Grafana as UID 472. |
| Resource isolation | Memory limits are 512 MB for Prometheus, 768 MB for Grafana and 512 MB for Uptime Kuma. Each container is limited to 1 CPU, and logs are rotated (3 × 10 MB). |
| Retention | Prometheus keeps 15 days of data, capped at 5 GB. Both values are configurable in `.env`. |

## Controls added in Phase 2

| Control | Implementation |
|---|---|
| Metrics endpoint access | `/metrics` requires a bearer token, compared with `hmac.compare_digest`. It returns 401 without a valid token and 404 when no token is configured. The token lives in `secrets/`, which is git-ignored, and is mounted read-only into Prometheus. |
| No raw URLs in labels | Labels use Django view names. Verified: `/arrangements/<id>/` maps to `view="arrangement_detail"`. |
| Health endpoints leak nothing | They return fixed JSON only. A test confirms that no paths, engine names or exception text appear in the 503 body. |
| App not exposed to the LAN | Django is bound to `127.0.0.1:8000`, verified with `Get-NetTCPConnection`. |
| No external notifications | Alertmanager's only receiver is `null`. |
| Real data untouched by tests | The database-failure test uses an out-of-tree settings override and never touches `db.sqlite3`. |

## Funeral Back Office findings (outside monitoring scope; not changed)

- The active `settings.py` hardcodes `SECRET_KEY` and has `DEBUG=True`. The Git-tracked snapshot reads the key from `DJANGO_SECRET_KEY`. Treat the hardcoded key as compromised before any hosted use.
- The active source tree is not tracked by Git. Only an older nested snapshot is committed.

## Known limitations (local development)

- Traffic uses plain HTTP. This is acceptable on loopback only. Production needs HTTPS (Phase 5).
- Prometheus has no authentication and is protected only by the localhost binding. `--web.enable-lifecycle` allows reload and shutdown over HTTP from localhost.
- Uptime Kuma's admin account is created manually in the setup wizard.
- The standard `louislam/uptime-kuma` image runs as **root** inside the container. Upstream also publishes a `-rootless` variant. Evaluate switching to it before any data is created, or as a planned migration.
- Monitoring and the monitored application share one host, so this setup provides no failure isolation.
- Backups in `backups/` contain password hashes and must be stored securely. That folder is git-ignored.

## Rules for future phases

- Do not capture request bodies.
- Use normalised route or view names in labels, never raw URLs.
- Never put personal information in labels, logs or exception payloads.
- Restrict `/metrics` to monitoring hosts.
- Use least-privilege, read-only database accounts for exporters.
