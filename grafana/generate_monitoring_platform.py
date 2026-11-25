"""
Generates grafana/dashboards/monitoring-platform.json (provisioned dashboard):
health of the monitoring platform itself - scrape targets, the Docker host,
component probes, GlitchTip's PostgreSQL and backups.

    python -I grafana/generate_monitoring_platform.py grafana/dashboards/monitoring-platform.json
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard_lib import *  # noqa: E402,F401,F403

P = 'application="monitoring-platform"'
PCT = steps(("green", None), ("orange", 70), ("red", 85))
panels = []
y = 0

# ---- Scrape targets ---------------------------------------------------------
panels.append(row("Scrape targets (Prometheus 'up')", y)); y += 1
panels += [
    stat("Targets up", 'sum(up)', 0, y, w=4, desc="All Prometheus scrape targets, all applications."),
    stat("Targets down", 'count(up == 0) or vector(0)', 4, y, w=4, th=steps(("green", None), ("red", 1))),
    table("Scrape target status", 'up', 8, y, w=16, h=8,
          hide=["Time", "__name__", "monitor"], rename={"job": "Job", "instance": "Instance", "Value": "Up (1/0)"},
          desc="Prometheus scrape availability. User-facing availability is measured by Uptime Kuma."),
]
panels.append(ts("Scrape duration", [tgt('scrape_duration_seconds', "{{job}}")], 0, y + 4, w=8, h=4, unit="s"))
y += 8

# ---- Monitoring host (Docker Desktop VM / Linux host) -----------------------
panels.append(row("Monitoring host (node-exporter)", y)); y += 1
panels += [
    stat("CPU", f'max(instance:cpu_utilisation:percent{{{P}}})', 0, y, w=4, unit="percent", decimals=0, th=PCT),
    stat("Memory", f'max(instance:memory_utilisation:percent{{{P}}})', 4, y, w=4, unit="percent", decimals=0, th=PCT),
    stat("Data disk", f'max(instance:disk_utilisation:percent{{{P}}})', 8, y, w=4, unit="percent", decimals=0,
         th=steps(("green", None), ("orange", 80), ("red", 90)),
         desc="Docker Desktop: virtual disk (grows on demand). The physical limit is the Windows C: drive."),
    stat("Data disk used", f'max((node_filesystem_size_bytes{{{P}}} - node_filesystem_avail_bytes{{{P}}}))',
         12, y, w=4, unit="bytes", decimals=1),
    stat("Monitoring components healthy", f'sum(probe_success{{job="blackbox-http", {P}}}) / count(probe_success{{job="blackbox-http", {P}}})',
         16, y, w=8, unit="percentunit", decimals=0, th=steps(("red", None), ("orange", 0.99), ("green", 1))),
]
y += 4
panels += [
    ts("Host CPU and memory", [tgt(f'instance:cpu_utilisation:percent{{{P}}}', "CPU", "A"),
                               tgt(f'instance:memory_utilisation:percent{{{P}}}', "Memory", "B")],
       0, y, w=12, unit="percent", th=steps(("green", None), ("red", 85))),
    table("Component health probes", f'probe_success{{job="blackbox-http", {P}}}', 12, y, w=12, h=8,
          hide=["Time", "__name__", "job", "module", "application", "environment", "endpoint"],
          rename={"instance": "Component", "Value": "Healthy (1/0)"}),
]
y += 8

# ---- GlitchTip PostgreSQL ---------------------------------------------------
panels.append(row("PostgreSQL (GlitchTip database, postgres-exporter)", y)); y += 1
PG = 'job="postgres"'
panels += [
    stat("PostgreSQL", f'min(pg_up{{{PG}}})', 0, y, w=4, mappings=UPDOWN, th=steps(("red", None), ("green", 1))),
    stat("Connections in use", f'100 * sum(pg_stat_database_numbackends{{{PG}}}) / max(pg_settings_max_connections{{{PG}}})',
         4, y, w=4, unit="percent", decimals=0, th=steps(("green", None), ("orange", 60), ("red", 80))),
    stat("Database size", f'sum(pg_database_size_bytes{{{PG}, datname="glitchtip"}})', 8, y, w=4, unit="bytes", decimals=1),
    ts("Transactions per second", [tgt(f'sum(rate(pg_stat_database_xact_commit{{{PG}, datname="glitchtip"}}[$__rate_interval]))', "commits", "A"),
                                   tgt(f'sum(rate(pg_stat_database_xact_rollback{{{PG}, datname="glitchtip"}}[$__rate_interval]))', "rollbacks", "B")],
       12, y, w=12, h=6, unit="ops"),
]
y += 6

# ---- Backups ----------------------------------------------------------------
panels.append(row("Backups (scripts/backup.ps1)", y)); y += 1
panels += [
    stat("Last successful backup", 'max(monitoring_backup_last_success_timestamp_seconds) * 1000', 0, y, w=6,
         unit="dateTimeFromNow", desc="Alert if older than 24 hours (BackupMissing)."),
    stat("Backup age", '(time() - max(monitoring_backup_last_success_timestamp_seconds)) / 3600', 6, y, w=4,
         unit="h", decimals=1, th=steps(("green", None), ("orange", 20), ("red", 24))),
    stat("Last run", 'max(monitoring_backup_last_run_success)', 10, y, w=4,
         mappings=[{"type": "value", "options": {"0": {"text": "FAILED", "color": "red"},
                                                 "1": {"text": "OK", "color": "green"}}}],
         th=steps(("red", None), ("green", 1))),
    stat("Backup size", 'max(monitoring_backup_last_size_bytes)', 14, y, w=5, unit="bytes", decimals=1),
    stat("Backup duration", 'max(monitoring_backup_last_duration_seconds)', 19, y, w=5, unit="s", decimals=0,
         desc="Monitoring services are stopped during the backup."),
]
y += 4

# ---- Prometheus self ---------------------------------------------------------
panels.append(row("Prometheus", y)); y += 1
panels += [
    ts("TSDB head series", [tgt('prometheus_tsdb_head_series{job="prometheus"}', "head series")], 0, y, w=12, h=6),
    ts("TSDB storage", [tgt('prometheus_tsdb_storage_blocks_bytes{job="prometheus"}', "blocks")], 12, y, w=12, h=6, unit="bytes"),
]

dash = {
    "uid": "monitoring-platform",
    "title": "Monitoring Platform Health",
    "description": "Health of the monitoring platform itself. Application dashboards: Application Overview.",
    "tags": ["monitoring-platform"],
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 2,
    "editable": False,
    "graphTooltip": 1,
    "refresh": "30s",
    "time": {"from": "now-6h", "to": "now"},
    "templating": {"list": []},
    "panels": panels,
}
write(dash, sys.argv[1])
print("panels:", len(panels))
