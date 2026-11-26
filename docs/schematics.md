# Schematics index

Every diagram in the documentation, grouped by question. All diagrams are [Mermaid](https://mermaid.js.org/) source inside the Markdown files, so they are versioned with the configuration they describe. When you change a component, update its diagram in the same commit.

**Viewing:** GitHub renders Mermaid directly. In VS Code, install the *Markdown Preview Mermaid Support* extension (`bierner.markdown-mermaid`) and open the Markdown preview (`Ctrl+Shift+V`).

## How is the platform built?

| Schematic | File |
|---|---|
| System context: operators, platform, monitored apps | [architecture.md §1](architecture.md#1-system-context) |
| Local topology: every container, port and connection | [architecture.md §3](architecture.md#3-local-deployment-topology-development) |
| Container startup order | [architecture.md §4](architecture.md#4-startup-order) |
| Signal pipelines overview | [architecture.md §5](architecture.md#5-data-flows) |
| Labelling model | [architecture.md §6](architecture.md#6-labelling-model) |
| Volumes and backups | [architecture.md §7](architecture.md#7-persistent-storage-and-backups) |
| Configuration map: repository file → service | [architecture.md §8](architecture.md#8-configuration-map) |
| Failure domains, development and production | [architecture.md §9](architecture.md#9-failure-domains) |

## How does data move?

| Schematic | File |
|---|---|
| Metrics scrape sequence (bearer token, readiness refresh) | [architecture.md §5.1](architecture.md#51-metrics-pull) |
| The three availability signals | [architecture.md §5.2](architecture.md#52-three-availability-signals) |
| Log pipeline: Django → file → Alloy → Loki → Grafana | [architecture.md §5.3](architecture.md#53-logs) |
| Error event sequence: Django → GlitchTip | [architecture.md §5.4](architecture.md#54-errors) |
| Alerting overview | [architecture.md §5.5](architecture.md#55-alerting) |

## How are alerts handled?

| Schematic | File |
|---|---|
| Alert pipeline: rules → Alertmanager → receivers | [alerting.md §1](alerting.md#1-pipeline) |
| Alert lifecycle state machine | [alerting.md §2](alerting.md#2-alert-lifecycle) |
| Grouping and inhibition | [alerting.md §3](alerting.md#3-grouping-inhibition-and-repeat-suppression) |
| Routing, development and production | [alerting.md §4](alerting.md#4-routing) |
| Backup status metrics → alerts | [alerting.md §5](alerting.md#backups-prometheusrulesinfrastructure-alertsyml-group-backup-alerts) |

## How is an application connected?

| Schematic | File |
|---|---|
| What the integration adds to a Django app | [application-integration.md](application-integration.md#what-the-integration-adds-to-the-application) |
| `/health/live/`, `/health/ready/` and `/metrics` decision logic | [application-integration.md](application-integration.md#endpoint-decision-logic) |
| How a request is measured (middleware sequence) | [application-integration.md](application-integration.md#how-a-request-is-measured) |
| Docker to Windows networking (`host.docker.internal`) | [application-integration.md](application-integration.md#networking-docker-to-windows) |
| Onboarding another application | [application-integration.md](application-integration.md#adding-another-application) |

## How is it secured?

| Schematic | File |
|---|---|
| Trust boundaries (development) | [security.md](security.md#trust-boundaries-development) |
| Personal data: defence in depth | [security.md](security.md#personal-data-defence-in-depth) |
| Where secrets live | [security.md](security.md#where-secrets-live) |

## How is it run and deployed?

| Schematic | File |
|---|---|
| First run on the laptop | [local-setup.md](local-setup.md#first-run) |
| `start.ps1` flow | [local-setup.md](local-setup.md#what-the-scripts-do) |
| Production target architecture | [deployment.md §1](deployment.md#1-target-architecture) |
| Production network and firewall | [deployment.md §3](deployment.md#3-network-and-firewall) |
| Production install order | [deployment.md §4](deployment.md#4-install-the-monitoring-server) |
| Backup sequence | [deployment.md §8](deployment.md#8-backups) |
| Restore procedure | [deployment.md §9](deployment.md#9-restore-procedure) |
| Update and rollback | [deployment.md §10](deployment.md#10-updates-and-rollback) |

## When something is wrong

| Schematic | File |
|---|---|
| Target down or empty dashboard | [troubleshooting.md](troubleshooting.md#a-prometheus-target-is-down-or-a-dashboard-shows-no-data) |
| Logs missing in Grafana | [troubleshooting.md](troubleshooting.md#logs-dont-appear-in-grafana) |
| Errors missing in GlitchTip | [troubleshooting.md](troubleshooting.md#errors-dont-appear-in-glitchtip) |
| Test coverage map | [tests/README.md](../tests/README.md#what-each-test-covers) |
