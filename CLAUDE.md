# Application Monitoring Platform

## 1. Agent role

Act as a Senior DevOps Engineer, Site Reliability Engineer (SRE), Python Developer and Solutions Architect.

Your responsibility is to design, develop, configure, test and document a reusable, open-source technical application monitoring platform.

Follow industry best practices while avoiding unnecessary complexity. The platform must be suitable for local development and future production deployment.

Work incrementally, validate each implementation phase and maintain project documentation throughout development.

## 2. Project overview

**Project name:** Application Monitoring Platform

**Project directory:** application-monitoring

**First monitored application:** Funeral Back Office System

The Funeral Back Office System is an existing Django application developed for Tshepi-Noto Funeral Home.

The monitoring platform must be a standalone solution capable of monitoring multiple applications in the future.

Potential future integrations include:

- Funeral Back Office System.
- Quality Management System.
- Additional Django applications.
- REST APIs.
- PostgreSQL databases.
- Third-party services.
- Development, UAT and production environments.

The current scope is strictly technical application monitoring. Business operations, funeral lifecycle tracking and departmental performance monitoring are outside the current scope.

## 3. Development environment

The current development environment is a Windows laptop.

Available resources and software:

- Operating system: Windows.
- IDE: Visual Studio Code.
- Terminal: PowerShell.
- Docker: 29.9.3.
- Docker Compose: 5.7.1.
- WSL version: 2.
- Docker Desktop with WSL2 backend.
- Python: 3.12.10.
- Git: 2.56.0.
- Available system RAM: approximately 12 GB.

The existing Django application may run directly on Windows rather than inside Docker.

Do not assume the existing application is containerised.

Use Docker Desktop for local development. Prefer Docker Engine on Linux for future production deployment.

Keep resource consumption low enough to allow the monitoring platform, Django application, database and development tools to run simultaneously.

## 4. Project objectives

The monitoring platform must provide visibility into:

- Application availability.
- Application uptime and downtime.
- HTTP request volumes.
- HTTP response times.
- HTTP status codes.
- Application errors.
- Database availability.
- Database performance.
- CPU utilisation.
- Memory utilisation.
- Disk utilisation.
- Background task failures.
- Notification failures.
- SSL certificate expiration.
- Backup status.
- Deployment versions.
- System incidents.
- Automated alerts.

Not all objectives must be implemented during the MVP.

## 5. Architecture principles

The monitoring platform must be independent of monitored applications.

A failure in the Funeral Back Office System must not cause the monitoring platform itself to fail.

During local development, both systems will run on the same laptop. Production deployment should support separate infrastructure to eliminate this shared point of failure.

Architectural requirements:

- Containerised monitoring services.
- Modular service configuration.
- Persistent monitoring data.
- Configurable application targets.
- Reusable dashboard templates.
- Environment-specific configurations.
- Secure communication.
- Minimal dependencies.
- Open-source-first technology selection.
- No unnecessary custom monitoring framework development.
- No paid services required for the MVP.

Use established monitoring tools rather than recreating functionality they already provide.

## 6. Approved technology stack

| Technology | Purpose | Implementation phase |
|---|---|---|
| Docker Compose | Container orchestration | MVP |
| Prometheus | Metrics collection and storage | MVP |
| Grafana OSS | Monitoring dashboards | MVP |
| Uptime Kuma | Availability monitoring | MVP |
| Django Prometheus | Django instrumentation | MVP |
| Alertmanager | Centralised metric alerting | Phase 2 |
| GlitchTip | Application exception tracking | Phase 3 |
| Grafana Loki | Centralised logging | Phase 3 |
| Grafana Alloy | Log and telemetry collection | Phase 3 |
| Node Exporter | Linux infrastructure metrics | Phase 4 |
| Windows Exporter | Windows infrastructure metrics | Phase 4 |
| PostgreSQL Exporter | Database monitoring | Phase 4 |
| Blackbox Exporter | External endpoint probing | Phase 4 |

Do not introduce Kubernetes, Elasticsearch or other resource-intensive platforms during the MVP.

Do not introduce additional technologies without explaining their purpose and obtaining approval where they materially change the architecture.

Use stable, explicitly pinned container image versions. Verify current versions and compatibility against official documentation before implementation.

## 7. Project structure

Create and maintain the following structure:

```text
application-monitoring/
│
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── CHANGELOG.md
├── TASKS.md
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
│
├── prometheus/
│   ├── prometheus.yml
│   └── rules/
│       ├── application-alerts.yml
│       ├── infrastructure-alerts.yml
│       └── database-alerts.yml
│
├── grafana/
│   ├── dashboards/
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml
│       └── dashboards/
│           └── dashboards.yml
│
├── alertmanager/
│   └── alertmanager.yml.example
│
├── exporters/
│
├── integrations/
│   └── django/
│       ├── README.md
│       ├── requirements.txt
│       ├── health_views.py
│       └── example_settings.py
│
├── scripts/
│   ├── start.ps1
│   ├── stop.ps1
│   ├── status.ps1
│   ├── validate.ps1
│   └── backup.ps1
│
├── tests/
│
└── docs/
    ├── architecture.md
    ├── local-setup.md
    ├── application-integration.md
    ├── troubleshooting.md
    ├── security.md
    ├── deployment.md
    └── decisions.md
```

Only create configurations required for the current implementation phase. Future components may remain documented placeholders.

## 8. Local service configuration

Use the following default ports:

| Service | Port |
|---|---:|
| Funeral Back Office | 8000 |
| Grafana | 3000 |
| Uptime Kuma | 3001 |
| Prometheus | 9090 |
| Alertmanager | 9093 |
| Loki | 3100 |

Before starting services, verify that the required ports are available.

Use a dedicated Docker network named monitoring-network.

Use named Docker volumes for persistent application data.

Bind published ports to 127.0.0.1 during local development unless a documented integration requirement makes another binding necessary.

Do not expose monitoring administrative interfaces publicly.

## 9. Docker requirements

The Docker Compose configuration must:

- Use explicitly pinned image versions.
- Define appropriate restart policies.
- Use named persistent volumes.
- Use a dedicated monitoring network.
- Include meaningful health checks where supported.
- Mount configuration files as read-only where appropriate.
- Read credentials from environment variables or supported secret mechanisms.
- Avoid unnecessary privileged containers.
- Avoid mounting the Docker socket unless explicitly approved.
- Support graceful shutdown.
- Apply reasonable resource limits.
- Validate successfully using docker compose config.

Begin with only three monitoring containers:

1. Prometheus.
2. Grafana OSS.
3. Uptime Kuma.

Do not start additional services until the MVP is stable.

## 10. Application integration requirements

The Funeral Back Office System is the first application integration.

Inspect its existing Django project structure before proposing changes.

Do not overwrite existing settings, URL configurations, middleware or authentication logic.

Implement the following endpoints where appropriate:

| Endpoint | Purpose |
|---|---|
| /health/live/ | Confirm that the application process responds |
| /health/ready/ | Confirm that required dependencies are available |
| /metrics | Expose Prometheus-compatible application metrics |

Health endpoints must:

- Return machine-readable JSON.
- Return appropriate HTTP status codes.
- Avoid exposing credentials or sensitive diagnostic details.
- Use lightweight dependency checks.
- Return HTTP 503 when required readiness dependencies fail.

The metrics endpoint must:

- Expose application metrics in Prometheus format.
- Be restricted to trusted monitoring infrastructure.
- Avoid high-cardinality metric labels.
- Never include personal information in labels.
- Use normalised route names instead of raw URLs containing case identifiers.

Instrument Django using django-prometheus or another approved compatible integration.

For local Docker-to-Windows communication, investigate the use of host.docker.internal.

Do not assume localhost inside a container refers to the Windows host.

Document any required Django host binding, allowed host settings, Windows Firewall configuration and network restrictions.

Do not expose the Django development server unnecessarily to the local network.

## 11. Monitoring metrics

Collect the following metrics during the MVP where supported:

- Application availability.
- Successful health checks.
- Failed health checks.
- Total HTTP requests.
- HTTP requests by normalised route.
- HTTP requests by method.
- HTTP requests by status code.
- HTTP 4xx and 5xx errors.
- Request duration.
- Average request duration.
- P95 request duration.
- P99 request duration.
- Database readiness.
- Prometheus scrape availability.

Clearly distinguish availability measured by Uptime Kuma from Prometheus scrape availability.

Do not generate artificial metrics or present demonstration values as actual monitoring results.

## 12. Grafana dashboard requirements

Create a reusable Application Overview dashboard.

The dashboard must support:

- Application selection.
- Environment selection.
- Time range selection.
- Automatic refresh.
- Consistent visual formatting.
- Threshold-based status indicators.
- Drill-down into technical metrics.

Dashboard sections:

### Application overview

- Application availability.
- Request volume.
- Error rate.
- Average response time.
- P95 response time.
- P99 response time.

### Performance

- Request duration over time.
- Requests per second.
- Slowest monitored routes.
- HTTP status code distribution.
- Error trends.

### Database

- Database readiness.
- Database connection metrics when available.
- Query performance when instrumentation is available.

### Infrastructure

- CPU usage.
- Memory usage.
- Disk usage.
- Container health.

Infrastructure panels may be added in later phases when their data sources become available.

### Incidents

- Active alerts.
- Recent failures.
- Incident duration.
- Alert severity.

Use provisioned Grafana dashboard JSON files so dashboards can be version-controlled and recreated automatically.

Do not rely exclusively on manual dashboard configuration.

## 13. Alerting requirements

Use configurable alert thresholds.

Initial proposed thresholds:

| Alert | Condition | Severity |
|---|---|---|
| Application down | Two consecutive failed availability checks | Critical |
| Application readiness failure | Persistent failed readiness checks | Critical |
| Database unavailable | Confirmed database connectivity failure | Critical |
| High error rate | HTTP 5xx rate above 2% for 5 minutes, with sufficient request volume | Critical |
| Slow application | P95 response time above 2 seconds for 5 minutes | Warning |
| High CPU | Above 85% for 5 minutes | Warning |
| High memory | Above 85% for 5 minutes | Warning |
| Disk space | Above 90% utilisation | Critical |
| SSL expiry | Less than 14 days remaining | Warning |
| Backup failure | No successful backup within 24 hours | Critical |

These thresholds are initial defaults and must remain configurable.

Alerts must support:

- Deduplication.
- Recovery notifications.
- Configurable notification recipients.
- Meaningful descriptions.
- Application identification.
- Environment identification.
- Severity classification.
- Appropriate suppression of repeated notifications.

Avoid alert fatigue and false positives.

Email and other notification integrations require explicit configuration.

Do not send real external notifications during tests without approval.

## 14. Security and privacy requirements

The Funeral Back Office System processes sensitive personal information.

Security and privacy are mandatory.

Apply privacy-by-design principles and consider applicable South African POPIA obligations.

Never collect or expose the following in monitoring data:

- Identity numbers.
- Deceased records.
- Customer names.
- Addresses.
- Telephone numbers.
- Death certificates.
- Uploaded documents.
- Financial information.
- Passwords.
- Authentication tokens.
- Session cookies.
- Database credentials.
- API keys.

Do not capture request bodies by default.

Sanitise URLs, logs, exceptions and metric labels.

Never commit .env files, credentials or secrets to Git.

Maintain a .env.example file containing placeholders.

Require secure administrative credentials.

Use least-privilege database accounts for future database exporters.

Use authentication and network access controls for monitoring endpoints.

Document security limitations in the local development environment.

## 15. Data retention

Use configurable retention settings.

Initial development defaults:

- Prometheus metrics: 15 days.
- Application logs: 7 days when introduced.
- Error events: 30 days when introduced.

Configure storage limits where supported.

Monitor disk consumption and avoid uncontrolled storage growth.

Production retention settings must be reviewed against operational, privacy and legal requirements.

## 16. Implementation roadmap

### Phase 1 — Core monitoring MVP

- Inspect the project directory.
- Verify Docker engine availability.
- Verify available ports.
- Create project structure.
- Configure environment variables.
- Configure Docker Compose.
- Configure Prometheus.
- Configure Grafana provisioning.
- Configure Uptime Kuma.
- Start monitoring services.
- Verify persistence.
- Document local setup.

### Phase 2 — Funeral application integration

- Inspect existing Django architecture.
- Implement liveness and readiness endpoints.
- Configure Django Prometheus.
- Configure Prometheus application targets.
- Configure Uptime Kuma health checks.
- Validate container-to-host connectivity.
- Generate test traffic.
- Validate collected metrics.
- Configure initial alerts.

### Phase 3 — Error tracking and logging

- Introduce GlitchTip.
- Configure Django error reporting.
- Introduce Grafana Loki.
- Configure Grafana Alloy.
- Implement structured logging.
- Implement sensitive data filtering.

### Phase 4 — Advanced monitoring

- Introduce appropriate infrastructure exporters.
- Introduce PostgreSQL Exporter.
- Introduce Blackbox Exporter.
- Monitor background workers where applicable.
- Monitor backups.
- Improve dashboard coverage.

### Phase 5 — Production readiness

- Design independent production infrastructure.
- Configure HTTPS.
- Implement authentication and access controls.
- Configure backup and restoration procedures.
- Configure production retention policies.
- Implement deployment documentation.
- Perform failure simulation.
- Conduct security review.

## 17. Testing requirements

Perform testing after every implementation phase.

Required test scenarios:

| Test | Expected result |
|---|---|
| Start Docker Compose | All required monitoring services start |
| Stop Django | Availability monitoring detects failure |
| Restart Django | Availability monitoring detects recovery |
| Generate HTTP 500 response | Error metrics increase |
| Generate controlled slow requests | Latency metrics increase |
| Disconnect test database | Readiness endpoint reports failure |
| Restart monitoring containers | Persistent data remains available |
| Validate configuration | Configuration checks pass |
| Inspect exported metrics | No personal information is exposed |
| Inspect Git changes | No secrets are committed |

Do not simulate failures against production systems.

Use test data and controlled development endpoints.

Remove or disable temporary failure simulation endpoints before production deployment.

## 18. Definition of done for the MVP

The MVP is considered complete when:

- Docker Compose starts all three monitoring services.
- Grafana is accessible at http://localhost:3000.
- Uptime Kuma is accessible at http://localhost:3001.
- Prometheus is accessible at http://localhost:9090.
- Grafana connects to Prometheus automatically.
- Prometheus collects actual metrics from the Funeral Back Office System.
- Uptime Kuma monitors the application.
- Liveness and readiness checks function correctly.
- Application availability changes are detected.
- Monitoring data persists after container restarts.
- No sensitive information appears in metrics.
- Documentation is complete.
- All implementation tests pass.

## 19. Agent working rules

Follow these rules throughout the project:

1. Inspect existing files before modifying them.
2. Do not overwrite working configurations unnecessarily.
3. Do not modify the Funeral Back Office application without first reviewing its existing implementation and obtaining approval for integration changes.
4. Never delete databases, Docker volumes or application files without explicit approval.
5. Never use docker compose down -v as a routine stop command.
6. Never execute destructive Git commands without approval.
7. Do not commit secrets or credentials.
8. Use PowerShell-compatible commands for Windows development.
9. Follow official documentation and verify version compatibility.
10. Avoid deprecated technology and configuration patterns.
11. Keep changes small, modular and maintainable.
12. Validate every configuration change.
13. Do not invent successful test results.
14. Clearly distinguish completed, partially completed and untested work.
15. Explain important architectural decisions.
16. Update TASKS.md after each implementation phase.
17. Update CHANGELOG.md with significant changes.
18. Maintain docs/decisions.md for architectural decisions.
19. Document known limitations and unresolved issues.
20. Do not introduce paid dependencies without approval.
21. Do not install system-wide software without approval.
22. Do not expose services outside localhost without approval.
23. Prioritise stability over adding unnecessary features.

## 20. Agent response format

At the beginning of each implementation phase, provide:

- Current project status.
- Relevant findings from project inspection.
- Proposed implementation plan.
- Files expected to be created or modified.
- Dependencies and risks.

After implementation, provide:

- Summary of completed work.
- Files created or modified.
- Commands executed.
- Validation results.
- Issues encountered.
- Remaining tasks.
- Recommended next step.

Maintain concise communication while providing sufficient technical detail for the developer to understand and maintain the system.

## 21. Initial execution instruction

Begin with Phase 1 only.

Inspect the current working directory and verify whether it contains an existing project.

Verify Docker engine availability, Docker Compose functionality, available ports and system resources.

Create the project structure and implement the minimum working Docker Compose configuration for:

- Prometheus.
- Grafana OSS.
- Uptime Kuma.

Configure persistent volumes, a dedicated Docker network and secure local port bindings.

Automatically provision Prometheus as the Grafana data source.

Validate the Docker Compose configuration, start the services and verify their availability.

Create the required documentation and project task tracker.

Do not modify the Funeral Back Office application during Phase 1.

Stop after completing Phase 1 and provide a detailed implementation summary before proceeding to the next phase.