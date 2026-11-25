"""
Generates grafana/dashboards/application-overview.json (provisioned dashboard).

Edit this script, not the JSON, then run:
    python -I grafana/generate_application_overview.py grafana/dashboards/application-overview.json
and verify with tests/check_dashboard_queries.py.
"""
import json, sys

DS = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
F = 'application=~"$application", environment=~"$environment"'
_id = [0]


def nid():
    _id[0] += 1
    return _id[0]


def tgt(expr, legend="", ref="A", instant=False, fmt=None):
    t = {"refId": ref, "expr": expr, "legendFormat": legend, "datasource": DS}
    if instant:
        t["instant"] = True
        t["range"] = False
    if fmt:
        t["format"] = fmt
    return t


def row(title, y):
    return {"id": nid(), "type": "row", "title": title, "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": y}, "panels": []}


def steps(*pairs):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for c, v in pairs]}


def stat(title, expr, x, y, w=4, h=4, unit="short", th=None, mappings=None, desc="", decimals=None, legend=""):
    d = {"unit": unit, "thresholds": th or steps(("text", None))}
    if mappings:
        d["mappings"] = mappings
    if decimals is not None:
        d["decimals"] = decimals
    return {"id": nid(), "type": "stat", "title": title, "description": desc, "datasource": DS,
            "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "targets": [tgt(expr, legend)],
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"colorMode": "background", "graphMode": "area", "justifyMode": "center",
                        "textMode": "value_and_name" if legend else "value",
                        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}}}


def ts(title, targets, x, y, w=12, h=8, unit="short", desc="", stack=False, th=None):
    custom = {"drawStyle": "line", "lineWidth": 1, "fillOpacity": 10, "showPoints": "never",
              "spanNulls": False}
    if stack:
        custom["stacking"] = {"mode": "normal", "group": "A"}
    d = {"unit": unit, "custom": custom}
    if th:
        d["thresholds"] = th
        custom["thresholdsStyle"] = {"mode": "dashed"}
    return {"id": nid(), "type": "timeseries", "title": title, "description": desc, "datasource": DS,
            "gridPos": {"h": h, "w": w, "x": x, "y": y}, "targets": targets,
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["mean", "max"]},
                        "tooltip": {"mode": "multi", "sort": "desc"}}}


def table(title, expr, x, y, w=12, h=8, unit="short", desc="", hide=None, rename=None):
    excl = {k: True for k in (hide or [])}
    return {"id": nid(), "type": "table", "title": title, "description": desc, "datasource": DS,
            "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "targets": [tgt(expr, instant=True, fmt="table")],
            "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
            "transformations": [{"id": "organize", "options": {"excludeByName": excl,
                                                                "renameByName": rename or {}}}],
            "options": {"showHeader": True, "sortBy": [{"displayName": (rename or {}).get("Value", "Value"), "desc": True}]}}


def text(title, content, x, y, w=24, h=3):
    return {"id": nid(), "type": "text", "title": title, "gridPos": {"h": h, "w": w, "x": x, "y": y},
            "options": {"mode": "markdown", "content": content}}


UPDOWN = [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"},
                                         "1": {"text": "UP", "color": "green"}}}]
READY = [{"type": "value", "options": {"0": {"text": "NOT READY", "color": "red"},
                                        "1": {"text": "READY", "color": "green"}}}]

RATE = f'sum(rate(django_http_requests_total_by_view_transport_method_total{{{F}}}[$__rate_interval]))'
ERR5 = f'sum(rate(django_http_responses_total_by_status_view_method_total{{{F}, status=~"5.."}}[$__rate_interval]))'
LAT = 'django_http_requests_latency_seconds_by_view_method'


def q(p):
    return f'histogram_quantile({p}, sum by (le) (rate({LAT}_bucket{{{F}}}[$__rate_interval])))'


AVG = f'sum(rate({LAT}_sum{{{F}}}[$__rate_interval])) / sum(rate({LAT}_count{{{F}}}[$__rate_interval]))'

panels = []
y = 0
panels.append(row("Application overview", y)); y += 1
panels += [
    stat("Scrape availability", f'min(up{{{F}}})', 0, y, mappings=UPDOWN,
         th=steps(("red", None), ("green", 1)),
         desc="Prometheus scrape availability ('up'). User-facing availability is measured separately by Uptime Kuma (http://localhost:3001)."),
    stat("Request rate", RATE, 4, y, unit="reqps", decimals=2),
    stat("5xx error rate", f'({ERR5} or vector(0)) / {RATE}', 8, y, unit="percentunit", decimals=2,
         th=steps(("green", None), ("orange", 0.01), ("red", 0.02)),
         desc="Share of requests returning HTTP 5xx. Alert threshold: 2%."),
    stat("Average response time", AVG, 12, y, unit="s", decimals=3,
         th=steps(("green", None), ("orange", 1), ("red", 2))),
    stat("P95 response time", q(0.95), 16, y, unit="s", decimals=3,
         th=steps(("green", None), ("orange", 1), ("red", 2)), desc="Alert threshold: 2 s for 5 min."),
    stat("P99 response time", q(0.99), 20, y, unit="s", decimals=3,
         th=steps(("green", None), ("orange", 2), ("red", 5))),
]
y += 4
panels.append(row("Performance", y)); y += 1
panels += [
    ts("Request duration (P50 / P95 / P99)",
       [tgt(q(0.5), "P50", "A"), tgt(q(0.95), "P95", "B"), tgt(q(0.99), "P99", "C")],
       0, y, unit="s", th=steps(("green", None), ("red", 2))),
    ts("Requests per second by route",
       [tgt(f'sum by (view) (rate(django_http_requests_total_by_view_transport_method_total{{{F}}}[$__rate_interval]))', "{{view}}")],
       12, y, unit="reqps", stack=True,
       desc="Routes are Django view names (normalised), never raw URLs."),
]
y += 8
panels += [
    table("Slowest routes (average, selected range)",
          f'topk(10, sum by (view) (rate({LAT}_sum{{{F}}}[$__range])) / sum by (view) (rate({LAT}_count{{{F}}}[$__range])) > 0)',
          0, y, unit="s", hide=["Time"], rename={"view": "Route (view)", "Value": "Avg duration"}),
    ts("HTTP status code distribution",
       [tgt(f'sum by (status) (rate(django_http_responses_total_by_status_view_method_total{{{F}}}[$__rate_interval]))', "{{status}}")],
       12, y, unit="reqps", stack=True),
]
y += 8
panels += [
    ts("Error trends (4xx / 5xx)",
       [tgt(f'sum(rate(django_http_responses_total_by_status_view_method_total{{{F}, status=~"4.."}}[$__rate_interval])) or vector(0)', "4xx", "A"),
        tgt(f'{ERR5} or vector(0)', "5xx", "B")],
       0, y, w=24, h=7, unit="reqps"),
]
y += 7
panels.append(row("Database", y)); y += 1
panels += [
    stat("Database readiness", f'min(app_dependency_up{{{F}, dependency="database"}})', 0, y, w=6, h=6,
         mappings=READY, th=steps(("red", None), ("green", 1)),
         desc="Result of the SELECT 1 readiness check, refreshed on every scrape."),
    ts("Database readiness over time",
       [tgt(f'min(app_dependency_up{{{F}, dependency="database"}})', "database ready")],
       6, y, w=10, h=6, th=steps(("red", None), ("green", 1))),
    text("Connection and query metrics",
         "Database connection and query-performance panels are **not yet available**.\n\n"
         "The Funeral Back Office uses SQLite (no server to export). Query metrics need the "
         "django-prometheus DB backend wrapper; server metrics need PostgreSQL Exporter (Phase 4).",
         16, y, w=8, h=6),
]
y += 6
panels.append(row("Logs (Loki, redacted at source)", y)); y += 1
LSEL = '{' + F + '}'


def ltgt(expr, legend="", ref="A", qtype="range"):
    return {"refId": ref, "expr": expr, "legendFormat": legend, "datasource": LOKI, "queryType": qtype}


lv = ts("Log volume by level",
        [ltgt(f'sum by (level) (count_over_time({LSEL}[$__auto]))', "{{level}}")],
        0, y, w=12, h=7, stack=True)
lv["datasource"] = LOKI
le = ts("Errors and warnings logged",
        [ltgt(f'sum by (level) (count_over_time({{{F}, level=~"error|warning|critical"}}[$__auto]))', "{{level}}")],
        12, y, w=12, h=7, stack=True,
        desc="Exceptions are tracked in detail in GlitchTip (http://localhost:8001).")
le["datasource"] = LOKI
panels += [lv, le]
y += 7
panels.append({
    "id": nid(), "type": "logs", "title": "Application logs",
    "description": "JSON logs shipped by Grafana Alloy. Personal data is redacted by the application and again by Alloy.",
    "datasource": LOKI, "gridPos": {"h": 10, "w": 24, "x": 0, "y": y},
    "targets": [ltgt(f'{LSEL} | json | line_format "{{{{.level | upper}}}} {{{{.logger}}}}: {{{{.message}}}}"')],
    "options": {"showTime": True, "wrapLogMessage": True, "sortOrder": "Descending",
                "enableLogDetails": True, "dedupStrategy": "none"},
})
y += 10
panels.append(row("Infrastructure", y)); y += 1
panels.append(text("Infrastructure",
                   "CPU, memory, disk and container-health panels are added in **Phase 4** when "
                   "Windows Exporter / Node Exporter data sources exist. No placeholder values are shown.",
                   0, y))
y += 3
panels.append(row("Incidents", y)); y += 1
panels += [
    stat("Firing alerts", f'count(ALERTS{{alertstate="firing", {F}}}) or vector(0)', 0, y, w=4, h=8,
         th=steps(("green", None), ("red", 1))),
    table("Active alerts", f'ALERTS{{alertstate=~"firing|pending", {F}}}', 4, y, w=20, h=8,
          hide=["Time", "Value", "__name__", "instance", "job", "monitor"],
          rename={"alertname": "Alert", "alertstate": "State", "severity": "Severity"}),
]
y += 8
panels += [
    ts("Alerts by severity (incident timeline)",
       [tgt(f'count by (severity) (ALERTS{{alertstate="firing", {F}}})', "{{severity}}")],
       0, y, w=12, unit="short", stack=True,
       desc="Width of each band shows incident duration."),
    ts("Recent failures: scrape and readiness",
       [tgt(f'1 - min(up{{{F}}})', "scrape failed", "A"),
        tgt(f'1 - min(app_dependency_up{{{F}}})', "readiness failed", "B")],
       12, y, w=12, unit="short", desc="1 = failing at that time."),
]


def var(name, label, query):
    return {"name": name, "label": label, "type": "query", "datasource": DS,
            "query": {"query": query, "refId": name}, "definition": query,
            "refresh": 2, "includeAll": True, "multi": True, "sort": 1,
            "current": {"text": "All", "value": "$__all"}}


dash = {
    "uid": "application-overview",
    "title": "Application Overview",
    "description": "Reusable technical overview for any application with application/environment labels.",
    "tags": ["application", "overview"],
    "timezone": "browser",
    "schemaVersion": 39,
    "version": 1,
    "editable": False,
    "graphTooltip": 1,
    "refresh": "30s",
    "time": {"from": "now-1h", "to": "now"},
    "timepicker": {"refresh_intervals": ["10s", "30s", "1m", "5m", "15m"]},
    "templating": {"list": [
        var("application", "Application", 'label_values(up{application!="monitoring-platform"}, application)'),
        var("environment", "Environment", 'label_values(up{application=~"$application"}, environment)'),
    ]},
    "links": [{"title": "Uptime Kuma", "type": "link", "url": "http://localhost:3001", "targetBlank": True},
              {"title": "GlitchTip (errors)", "type": "link", "url": "http://localhost:8001", "targetBlank": True},
              {"title": "Alertmanager", "type": "link", "url": "http://localhost:9093", "targetBlank": True}],
    "panels": panels,
}
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
    json.dump(dash, fh, indent=2)
    fh.write("\n")
print("panels:", len(panels))
