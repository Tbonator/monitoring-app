# Architecture

> **Status:** describes the platform as built through Phase 5 (2026-11-26). The development stack runs on the Windows laptop. The production layout is designed and tested locally but **not deployed yet** (see [deployment.md](deployment.md)).
>
> **Schematics** are [Mermaid](https://mermaid.js.org/) diagrams. GitHub renders them directly. In VS Code, install the *Markdown Preview Mermaid Support* extension to see them in the Markdown preview. A list of every schematic in the docs is in [schematics.md](schematics.md).

## 1. System context

Who and what the platform talks to. Dashed lines are production-only or future.

```mermaid
flowchart LR
    ops(["Developer / operator<br/>(browser on the laptop)"])

    subgraph platform["Application Monitoring Platform"]
        direction TB
        ui["Grafana · Uptime Kuma · GlitchTip<br/>Prometheus · Alertmanager"]
        collect["Prometheus · Blackbox · Alloy · Loki<br/>exporters"]
    end

    subgraph apps["Monitored applications"]
        fbo["Funeral Back Office<br/>(Django)"]
        future["Future: QMS, other Django apps,<br/>REST APIs, PostgreSQL, third parties"]
    end

    mail[("SMTP server<br/>(production only)")]

    ops -->|"dashboards, alerts, errors"| ui
    collect -->|"scrape /metrics, probe /health/*"| fbo
    fbo -->|"logs (files), error events"| collect
    collect -.->|"same contract"| future
    ui -.->|"alert e-mail"| mail
```

The platform is **independent** of the applications it watches. Nothing from the platform is installed into an application except the instrumentation in [integrations/django/](../integrations/django/). If an application fails, only its targets turn `down`.

## 2. Components

| Service | Version | Role | Local address | Persistent volume | Limits (CPU / RAM) | Health check |
|---|---|---|---|---|---|---|
| Prometheus | v3.16.0 | Pulls and stores metrics, evaluates alert rules | 127.0.0.1:9090 | `monitoring-prometheus-data` | 1.0 / 512M | `/-/healthy` |
| Alertmanager | v0.35.1 | Groups, deduplicates, inhibits and routes alerts | 127.0.0.1:9093 | `monitoring-alertmanager-data` | 0.5 / 128M | `/-/healthy` |
| Grafana OSS | 13.3.2 | Dashboards. Data sources and dashboards come from files. | 127.0.0.1:3000 | `monitoring-grafana-data` | 1.0 / 768M | `/api/health` |
| Uptime Kuma | 2.5.12 | User-facing up/down checks and history | 127.0.0.1:3001 | `monitoring-uptime-kuma-data` | 1.0 / 512M | image built-in |
| Loki | 3.7.10 | Log storage, 7-day retention | 127.0.0.1:3100 (API) | `monitoring-loki-data` | 1.0 / 384M | none (distroless). Probed by Blackbox. |
| Alloy | v1.22.0 | Tails the app's log files, redacts, pushes to Loki | internal `alloy:12345` | `monitoring-alloy-data` | 0.5 / 256M | scraped by Prometheus |
| GlitchTip | 6.2.6 | Exception tracking (Sentry protocol), web and worker in one container | 127.0.0.1:8001 | `monitoring-glitchtip-uploads` | 1.0 / 512M | `/_health/` |
| PostgreSQL | 18.7 | GlitchTip's database, queue and cache | internal only | `monitoring-glitchtip-postgres-data` | 1.0 / 256M | `pg_isready` |
| Node Exporter | v1.13.1 | Docker Desktop VM metrics, plus backup textfile metrics | internal `node-exporter:9100` | none | 0.25 / 64M | scraped |
| Blackbox Exporter | v0.29.1 | Prometheus-side HTTP and TLS probes | internal `blackbox-exporter:9115` | none | 0.25 / 64M | `/-/healthy` |
| PostgreSQL Exporter | v0.21.1 | GlitchTip database metrics (read-only `pg_monitor` role) | internal `postgres-exporter:9187` | none | 0.25 / 64M | scraped |
| Windows Exporter | v0.32.1 | Laptop CPU, memory and disk. **Windows service, not a container.** | 127.0.0.1:9182 | none | n/a | scraped |

Total container memory limits add up to about 3.5 GB. Measured idle use of the whole stack is about 0.9 GB.

## 3. Local deployment topology (development)

Everything runs on one Windows laptop. Containers share the `monitoring-network` bridge and reach each other by service name. Published ports are bound to `127.0.0.1` only. Containers reach native Windows processes through `host.docker.internal`, which Compose maps to the host gateway.

```mermaid
flowchart TB
    browser(["Browser on the laptop"])

    subgraph laptop["Windows laptop"]
        direction TB

        subgraph win["Native Windows processes (127.0.0.1)"]
            django["Funeral Back Office<br/>Django runserver<br/>127.0.0.1:8000"]
            logdir[("App log directory<br/>funeral-back-office-YYYY-MM-DD.log")]
            winexp["Windows Exporter service<br/>127.0.0.1:9182"]
            django -->|"JSON, redacted"| logdir
        end

        subgraph vm["Docker Desktop (WSL2 VM) · bridge network: monitoring-network"]
            direction TB
            prom["Prometheus :9090"]
            am["Alertmanager :9093"]
            graf["Grafana :3000"]
            kuma["Uptime Kuma :3001"]
            loki["Loki :3100"]
            alloy["Alloy :12345"]
            gt["GlitchTip :8000<br/>(published as 8001)"]
            pg[("glitchtip-postgres :5432")]
            node["node-exporter :9100"]
            bb["blackbox-exporter :9115"]
            pgexp["postgres-exporter :9187"]
        end
    end

    browser -->|"127.0.0.1:3000 / 3001 / 9090 / 9093 / 8001"| vm

    graf -->|"PromQL"| prom
    graf -->|"LogQL"| loki
    prom -->|"firing alerts"| am
    prom -->|"scrape"| node & bb & pgexp & loki & alloy & am
    prom -->|"scrape /metrics<br/>(bearer token)"| django
    prom -->|"scrape"| winexp
    bb -->|"probe /health/live/, /health/ready/"| django
    bb -->|"probe health URLs"| graf & am & loki & gt & kuma
    kuma -->|"HTTP checks"| django
    alloy -->|"read-only bind mount"| logdir
    alloy -->|"push"| loki
    django -->|"error events<br/>http://localhost:8001"| gt
    gt --> pg
    pgexp -->|"pg_monitor role"| pg
```

Arrows into `django` and `winexp` cross the VM boundary through `host.docker.internal`. Django still listens only on `127.0.0.1:8000`: Docker Desktop forwards container traffic to Windows loopback, so no `0.0.0.0` binding or firewall rule is needed (verified in Phase 2).

### Port map

| Port | Bound to | Service | Who uses it |
|---:|---|---|---|
| 3000 | 127.0.0.1 | Grafana | Operator browser |
| 3001 | 127.0.0.1 | Uptime Kuma | Operator browser |
| 9090 | 127.0.0.1 | Prometheus | Operator browser, scripts |
| 9093 | 127.0.0.1 | Alertmanager | Operator browser |
| 3100 | 127.0.0.1 | Loki (API) | Scripts, tests. Users browse logs through Grafana. |
| 8001 | 127.0.0.1 | GlitchTip | Operator browser, Django error reporting |
| 8000 | 127.0.0.1 | Django (not a container) | Users. Prometheus, Blackbox and Uptime Kuma through `host.docker.internal`. |
| 9182 | 127.0.0.1 | Windows Exporter (not a container) | Prometheus through `host.docker.internal` |
| 5432, 9100, 9115, 9187, 12345 | not published | PostgreSQL, exporters, Alloy | Other containers on `monitoring-network` only |

`scripts/validate.ps1` fails if any published port is bound to anything other than `127.0.0.1`.

## 4. Startup order

Compose starts services in dependency order. Services without arrows start immediately, and every service uses `restart: unless-stopped`.

```mermaid
flowchart LR
    prom["prometheus"] -->|"service_healthy"| graf["grafana"]
    loki["loki"] -->|"service_started<br/>(Alloy retries pushes)"| alloy["alloy"]
    pg[("glitchtip-postgres")] -->|"service_healthy"| gt["glitchtip"]
    pg -->|"service_healthy"| pgexp["postgres-exporter"]

    am["alertmanager"]
    kuma["uptime-kuma"]
    node["node-exporter"]
    bb["blackbox-exporter"]
```

Prometheus does not wait for Alertmanager: it queues alerts and retries the delivery.

## 5. Data flows

The platform has four independent signal pipelines and one alerting pipeline.

```mermaid
flowchart LR
    app["Funeral Back Office"]

    app -->|"1 · Metrics (pull, 15 s)"| prom["Prometheus"]
    app -->|"2 · Availability (probe)"| kuma["Uptime Kuma"]
    app -->|"2 · Availability (probe)"| bb["Blackbox"] --> prom
    app -->|"3 · Logs (files)"| alloy["Alloy"] --> loki["Loki"]
    app -->|"4 · Errors (push)"| gt["GlitchTip"]

    prom -->|"5 · Alerts"| am["Alertmanager"]
    prom --> graf["Grafana"]
    loki --> graf
```

### 5.1 Metrics (pull)

Prometheus scrapes every target every 15 seconds. Blackbox probes run every 30 seconds and TLS probes every hour. Targets and their labels come from `prometheus/targets/<environment>/<job>.yml` (file service discovery), and changes are picked up without a restart.

```mermaid
sequenceDiagram
    autonumber
    participant P as Prometheus
    participant D as Django /metrics
    participant DB as Database
    participant G as Grafana

    loop every 15 s
        P->>D: GET /metrics with Authorization Bearer token
        alt no token configured in Django
            D-->>P: 404, target shows down
        else token wrong or missing
            D-->>P: 401, target shows down
        else token valid
            D->>DB: SELECT 1
            DB-->>D: ok or error
            Note over D: app_dependency_up set to 1 or 0
            D-->>P: 200, Prometheus text format
        end
        Note over P: store samples in TSDB, set up = 1 or 0
    end
    loop every 15 s
        Note over P: evaluate recording and alert rules
    end
    G->>P: PromQL queries (dashboard refresh)
    P-->>G: series
```

### 5.2 Three availability signals

Availability is measured three different ways. The dashboards label them separately.

```mermaid
flowchart LR
    subgraph app["Funeral Back Office"]
        live["/health/live/"]
        ready["/health/ready/"]
        metrics["/metrics"]
    end

    kuma["Uptime Kuma<br/>Live 30 s · Ready 60 s"] --> live & ready
    bb["Blackbox Exporter<br/>http_2xx · http_ready, 30 s"] --> live & ready
    prom["Prometheus scrape, 15 s"] --> metrics

    kuma --> k_out["Up/down history and<br/>uptime percentage in Uptime Kuma"]
    bb --> b_out["probe_success<br/>alert: ApplicationEndpointDown"]
    prom --> p_out["up{kind=application}<br/>alert: ApplicationDown"]
```

| Signal | Question it answers | Where it shows | Alerts |
|---|---|---|---|
| Uptime Kuma | Does the app answer its health endpoints from outside? This is the **user-facing** up/down signal. | Uptime Kuma UI | Uptime Kuma notifications (none configured yet) |
| Blackbox `probe_success` | The same question, but recorded in Prometheus so it can alert and be graphed | Grafana *Infrastructure* and *Incidents* | `ApplicationEndpointDown`, `MonitoringComponentDown` |
| Prometheus `up` | Could Prometheus collect metrics? This is **not** proof that users can reach the app. | Grafana *Scrape availability* | `ApplicationDown` |

### 5.3 Logs

Logs are redacted twice: in the application before the line is written, and again in Alloy before it reaches Loki.

```mermaid
flowchart LR
    subgraph django["Django process (Windows)"]
        rec["logging call"] --> rf["RedactingFilter<br/>IDs, phones, e-mails,<br/>tokens, query strings"]
        rf --> jf["JsonFormatter<br/>ts, level, logger, message,<br/>application, environment"]
        jf --> dfh["DailyFileHandler<br/>one append-only file per day,<br/>7-day pruning"]
    end

    dfh --> file[("funeral-back-office-<br/>YYYY-MM-DD.log")]

    subgraph alloy["Alloy container"]
        fm["local.file_match<br/>every 10 s"] --> src["loki.source.file<br/>poll 1-5 s"]
        src --> proc["loki.process<br/>json → timestamp → label: level<br/>→ metadata: logger, exception_type<br/>→ 4 × stage.replace (redact)"]
        proc --> wr["loki.write<br/>60 retries, backoff ≤ 30 s<br/>(≈ 30 min outage tolerance)"]
    end

    file -->|"read-only bind mount"| fm
    wr -->|"HTTP push"| loki[("Loki<br/>retention 168 h")]
    loki -->|"LogQL"| graf["Grafana<br/>Logs section, Explore"]
```

Only `application`, `environment`, `source`, `collector` and `level` are indexed labels. `logger` and `exception_type` are structured metadata, which keeps stream cardinality low.

### 5.4 Errors

```mermaid
sequenceDiagram
    autonumber
    participant V as Django view
    participant S as sentry-sdk 3.0
    participant GT as GlitchTip (127.0.0.1:8001)
    participant PG as PostgreSQL

    V->>S: unhandled exception, or 5xx response other than 503
    Note over S: data_collection is off: no user, cookies,<br/>headers, bodies, query params or frame variables
    S->>S: before_send removes request data and redacts every string
    S->>GT: POST event (DSN from secrets/)
    GT->>PG: store issue and event (30-day retention)
    Note over GT: viewed in the GlitchTip UI, linked from Grafana
```

503 is excluded because `/health/ready/` returns it deliberately during a dependency outage, and that must not flood GlitchTip.

### 5.5 Alerting

Prometheus evaluates the rules in `prometheus/rules/*.yml` every 15 seconds and sends firing alerts to Alertmanager. The full alert catalogue, routing and inhibition are in [alerting.md](alerting.md).

```mermaid
flowchart LR
    rules["Rule files<br/>thresholds as recording rules"] --> eval{"Condition true<br/>for the 'for' period?"}
    eval -->|"no"| idle["inactive / pending"]
    eval -->|"yes"| firing["firing"]
    firing --> am["Alertmanager"]
    am --> group["group by alertname,<br/>application, environment"]
    group --> inhibit["inhibit:<br/>app down silences its other alerts,<br/>critical silences warning"]
    inhibit --> route{"Config file<br/>mounted"}
    route -->|"alertmanager.yml<br/>(development)"| null["receiver null<br/>(UI and Grafana only)"]
    route -->|"alertmanager.prod.yml<br/>(production)"| mail["receiver ops-email<br/>with recovery messages"]
```

## 6. Labelling model

Every target carries `application` and `environment`. The dashboards' variables, the alert annotations and Alertmanager's grouping all use these two labels, so a new application appears everywhere once its targets are labelled.

```mermaid
flowchart TB
    base["Every target<br/>application · environment"]
    base --> appm["Application /metrics<br/>+ kind=application"]
    base --> host["Host exporters (node, windows)<br/>+ host · role"]
    base --> probe["Blackbox HTTP probes<br/>+ module · endpoint"]
    base --> db["postgres-exporter<br/>+ database"]

    appm --> ad["ApplicationDown matches<br/>up{kind=application}"]
    host --> rr["Recording rules add platform=windows|linux"]
    base --> dash["Grafana variables:<br/>Application, Environment"]
    base --> amg["Alertmanager group_by and inhibit 'equal'"]
```

**Privacy rule:** labels hold only view names, HTTP methods, status codes and the values above. Raw URLs, IDs and personal data never become labels (verified across 345 series in Phase 2).

## 7. Persistent storage and backups

```mermaid
flowchart LR
    subgraph services["Services"]
        prom["Prometheus"]
        am["Alertmanager"]
        graf["Grafana"]
        kuma["Uptime Kuma"]
        loki["Loki"]
        alloy["Alloy"]
        pg["glitchtip-postgres"]
        gt["GlitchTip"]
    end

    subgraph vols["Named Docker volumes"]
        v1[("monitoring-prometheus-data<br/>TSDB, 15 d / 5 GB")]
        v2[("monitoring-alertmanager-data<br/>silences, notification log")]
        v3[("monitoring-grafana-data<br/>SQLite: users, preferences")]
        v4[("monitoring-uptime-kuma-data<br/>SQLite: monitors, heartbeats")]
        v5[("monitoring-loki-data<br/>chunks, index, 7 d")]
        v6[("monitoring-alloy-data<br/>file read positions")]
        v7[("monitoring-glitchtip-postgres-data<br/>issues, events, 30 d")]
        v8[("monitoring-glitchtip-uploads")]
    end

    prom --- v1
    am --- v2
    graf --- v3
    kuma --- v4
    loki --- v5
    alloy --- v6
    pg --- v7
    gt --- v8

    backup["scripts/backup.ps1"] -->|"stop, tar each volume, start"| out[("backups/#lt;timestamp#gt;/<br/>*.tar.gz (git-ignored)")]
    vols -.-> backup
    backup -->|"status metrics"| tf["exporters/textfile/<br/>monitoring_backup.prom"]
    tf --> node["node-exporter"] --> prom
```

Dashboards, data sources, alert rules and targets are **not** in volumes. They live in Git and are mounted read-only, so they are recreated on every start.

## 8. Configuration map

Which file in the repository feeds which service, and how.

```mermaid
flowchart LR
    subgraph repo["Repository (Git)"]
        env[".env<br/>(git-ignored)"]
        secrets["secrets/<br/>(git-ignored)"]
        promyml["prometheus/prometheus.yml"]
        rules["prometheus/rules/*.yml"]
        targets["prometheus/targets/<br/>development | production"]
        amyml["alertmanager/alertmanager.yml"]
        gprov["grafana/provisioning/"]
        gdash["grafana/dashboards/*.json<br/>(generated by grafana/generate_*.py)"]
        lokicfg["loki/loki-config.yml"]
        alloycfg["alloy/config.alloy"]
        bbcfg["exporters/blackbox/blackbox.yml"]
        tf["exporters/textfile/"]
    end

    compose["docker compose"]
    env -->|"versions, ports, retention,<br/>credentials, PROMETHEUS_TARGETS_DIR"| compose

    promyml & rules & targets -->|":ro"| prom["Prometheus"]
    secrets -->|"metrics token :ro"| prom
    secrets -->|"pg password :ro"| pgexp["postgres-exporter"]
    amyml -->|":ro"| am["Alertmanager"]
    gprov & gdash -->|":ro"| graf["Grafana"]
    lokicfg -->|":ro"| loki["Loki"]
    alloycfg -->|":ro"| alloy["Alloy"]
    bbcfg -->|":ro"| bb["Blackbox"]
    tf -->|":ro"| node["node-exporter"]
    compose --> prom & am & graf & loki & alloy & bb & node & pgexp
```

| Path | Contents |
|---|---|
| `prometheus/prometheus.yml` | Job definitions only (ADR-029) |
| `prometheus/targets/<env>/<job>.yml` | Targets and their labels, one file per job |
| `prometheus/rules/*.yml` | Thresholds, recording rules and alerts for applications, databases and infrastructure |
| `prometheus/tests/*.test.yml` | promtool unit tests for alerts that can't safely be triggered for real |
| `grafana/provisioning/` | Prometheus and Loki data sources, dashboard provider |
| `grafana/dashboards/*.json` | *Application Overview* and *Monitoring Platform Health*, generated by the Python scripts beside them |
| `docker-compose.prod.yml`, `caddy/`, `deploy/` | Production overlay and app-server agents (see [deployment.md](deployment.md)) |

## 9. Failure domains

What happens when each part fails, and what detects it. The first five rows were exercised in the Phase 2 to Phase 5 tests (results in [TASKS.md](../TASKS.md)). The last two are known gaps.

| Failure | Effect | Detected by |
|---|---|---|
| Django stops | No new metrics, logs or errors from the app. The platform keeps running. | `ApplicationDown`, `ApplicationEndpointDown`, Uptime Kuma |
| App database unavailable | `/health/ready/` returns 503. `app_dependency_up` = 0. | `DatabaseUnavailable`, `ApplicationReadinessFailure`, Uptime Kuma Ready monitor |
| Loki down | Alloy queues and retries for about 30 minutes, so no logs are lost | `MonitoringComponentDown` (Blackbox probe on `loki:3100/ready`) |
| GlitchTip database down | Error events can't be stored | `PostgresDown` (GlitchTip's own `/_health/` stays 200, see security review O6) |
| An exporter down | Gap in host or database metrics | `InfrastructureExporterDown` |
| Prometheus or Alertmanager down | **Nothing alerts.** Uptime Kuma keeps checking independently. | Not yet covered: needs an external heartbeat (security review O1) |
| Laptop or Docker Desktop down | Everything stops, monitoring included | Not covered in development. Production separates the servers. |

```mermaid
flowchart TB
    subgraph dev["Development: one failure domain"]
        direction LR
        d_app["Django + database"]
        d_mon["Monitoring stack"]
    end
    subgraph prod["Production: two failure domains"]
        direction LR
        p_app["App server<br/>Django + agents"]
        p_mon["Monitoring server<br/>full stack"]
        p_app <-->|"private network"| p_mon
    end
    dev -.->|"Phase 5 design"| prod
```

## 10. Development and production compared

| Aspect | Development (this laptop) | Production (designed, not deployed) |
|---|---|---|
| Hosts | One Windows laptop | Separate Linux monitoring server and app server |
| Compose files | `docker-compose.yml` | `docker-compose.yml` + `docker-compose.prod.yml`, plus `deploy/app-server/` on the app server |
| Targets | `prometheus/targets/development/` | `prometheus/targets/production/` |
| External access | None. Everything on 127.0.0.1. | Caddy on 443 for Grafana and GlitchTip only. SSH tunnel for the rest. |
| Log collector | Alloy container on the laptop | Alloy on the app server, pushing to Loki's private IP |
| Notifications | Alertmanager `null` receiver | E-mail through SMTP |
| Retention | Metrics 15 d / 5 GB, logs 7 d | Metrics 30 d / 20 GB, logs 14 d |

The production topology is drawn in [deployment.md](deployment.md#1-target-architecture).
