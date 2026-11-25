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
- **Superseded in Phase 2** by ADR-011.

## ADR-009: django-prometheus 2.6.0.dev26 (pre-release)
- **Date:** 2026-11-25. **Approved by:** project owner.
- **Context:** The latest stable release, 2.5.0, requires `Django<6.1`. The app runs Django 6.1.x. 2.6.0.dev26 is the first release that declares Django 6.1 support (`Django<6.2`).
- **Decision:** Pin `==2.6.0.dev26` exactly. Upgrade to 2.6.0 stable once it is released.
- **Rejected:** A custom middleware built on `prometheus-client`, because it means more code to maintain and loses the DB metrics option.

## ADR-010: Token-protected /metrics
- **Decision:** `/metrics` is served by a wrapper view that requires `Authorization: Bearer <token>`, compared in constant time. The token comes from the `MONITORING_METRICS_TOKEN` environment variable. Prometheus reads it from `secrets/<app>-metrics.token` through `credentials_file`. With no token set, the endpoint returns 404.
- **Reason:** CLAUDE.md §10 requires restricting `/metrics` to monitoring infrastructure. An IP allowlist does not work reliably here: Docker Desktop's forwarding makes container traffic appear to come from the host. A token keeps working when production moves to separate infrastructure.

## ADR-011: Alertmanager with no notification receivers
- **Decision:** Deploy Alertmanager v0.35.1 with a `null` default receiver, grouped by `alertname`, `application` and `environment`, with `repeat_interval: 4h` and inhibition rules. Commit `alertmanager.yml`, which contains no secrets. Future credentials go through `*_file` settings that point into `secrets/`.
- **Reason:** It gives deduplication, grouping and suppression now. No real notifications are sent until they are approved (CLAUDE.md §13).

## ADR-012: Thresholds as recording rules
- **Decision:** Alert thresholds are recording rules (`app:threshold:*`) and alerts compare against them with `scalar()`.
- **Reason:** Thresholds can be tuned in one place without editing alert expressions. Per-application overrides can be added later.

## ADR-013: Out-of-tree failure-simulation harness
- **Decision:** The HTTP 500, slow-request and database-failure simulations live in `monitoring-app/tests/django_harness` and are activated only through `DJANGO_SETTINGS_MODULE`.
- **Reason:** No temporary failure endpoints exist in the application code, so there is nothing to remove before production. The real SQLite database, which holds personal records, is never altered.

## ADR-014: Alerting uses Prometheus scrape availability
- **Decision:** `ApplicationDown` is based on `up == 0` for 30 s, which is two failed scrapes at a 15 s interval. Uptime Kuma independently tracks user-facing availability.
- **Reason:** Uptime Kuma notifications would duplicate the Alertmanager routing. A single alert pipeline avoids alert fatigue.

## ADR-015: GlitchTip 6.2.6, all-in-one, without Valkey
- **Date:** 2026-11-25. **Approved by:** project owner (version and port 8001).
- **Decision:** Run GlitchTip 6.2.6 with `SERVER_ROLE=all_in_one`, so the web server and worker share one container. It uses its own PostgreSQL 18.7 with a password, which is not published, and no Valkey (`VALKEY_URL=""`, so the queue and cache live in Postgres). It listens on `127.0.0.1:8001`. Sign-up and organization creation are disabled, email goes to the console only (`consolemail://`), retention is 30 days, and `ALLOWED_HOSTS=localhost,127.0.0.1`.
- **Reason:** GlitchTip documents Valkey as optional, and leaving it out saves a container and memory. 7.0.0 was too new to adopt. The official sample's passwordless "trust" database auth was rejected.
- **Bootstrap:** `scripts/glitchtip-bootstrap.py` creates the admin, the organization and a project with IP scrubbing enabled, and writes the DSN to `secrets/`.

## ADR-016: sentry-sdk 3.0 configured through `data_collection`
- **Context:** sentry-sdk 3.0 removed `send_default_pii`, `include_local_variables`, `event_scrubber` and `DjangoIntegration(transaction_style=...)`. Its new `data_collection` defaults are **permissive**: user info, all HTTP bodies, stack-frame variables and DB query data are collected unless disabled.
- **Decision:** Set every `data_collection` category explicitly to off or empty. Add `max_request_body_size="never"`, a `before_send` that drops user, request data, cookies, headers, query, env, frame vars and extra and then runs `redact()` over the whole event, and a `before_breadcrumb` that drops SQL and HTTP breadcrumbs. Report 5xx responses except 503, which is the intended readiness response.
- **Verified by:** `tests/test_privacy_end_to_end.py`.

## ADR-017: Redact at the source, with Alloy as a second layer
- **Decision:** The app's `RedactingFilter` and `JsonFormatter` remove ID numbers, phone numbers, emails, card or account numbers, credentials, bearer tokens and cookies. They strip query strings and replace numeric path segments with `:id` before anything is written. Alloy applies a second `stage.replace` pass. Only `level` becomes a Loki label; `logger` and `exception_type` are structured metadata.
- **Limitation:** Pattern-based redaction is best effort. Code must still avoid logging personal data.

## ADR-018: No Docker healthcheck for Loki
- **Decision:** The Loki 3.x image is distroless, with no shell, wget or curl. Its health is monitored through Prometheus (`up{job="loki"}`) and `status.ps1` (`/ready`). Alloy starts once Loki has *started* and retries pushes.

## ADR-019: Daily append-only log files instead of rename-based rotation
- **Context:** A test showed that when `RotatingFileHandler` renamed the file, Alloy, reading through the Docker Desktop bind mount, stopped tracking it. Its saved offset stayed past the end of the new file, and **no lines were shipped after rotation** (0 of 60).
- **Decision:** `DailyFileHandler` writes `funeral-back-office-YYYY-MM-DD.log` (UTC date), only appends, and deletes files older than `APP_LOG_RETENTION_DAYS` (default 7). Alloy matches `funeral-back-office-*.log`.
- **Verified by:** `tests/test_log_rotation.py`, which checks the day switch, pruning, ingestion and that Alloy reads a new file completely.
- **Trade-off:** There is no size cap within a day. That's acceptable at local-development volumes; review for production.

## ADR-020: Pin Django in the Pipfile
- **Decision:** `django = "==6.1.3"` in `Desktop\funeral app\Pipfile`.
- **Reason:** With `"*"`, every `pipenv install` re-locks and can upgrade Django silently, which already happened once in Phase 2.

## ADR-021: Ruflo tooling stays out of Git
- **Date:** 2026-11-25. **Decided by:** project owner.
- **Decision:** `.claude/`, `.claude-flow/`, `.agents/`, `.swarm/` and `.mcp.json` are git-ignored.
- **Reason:** These are personal developer tooling that `ruflo init` can regenerate. Committing `.claude/settings.json` and `.mcp.json` would make every clone run Ruflo hooks and an `npx` MCP server. `.swarm/memory.db` can contain session content, and several Ruflo files hold absolute local paths.
