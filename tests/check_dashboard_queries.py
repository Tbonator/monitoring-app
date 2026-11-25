"""
Executes every PromQL query in the provisioned dashboards against Prometheus
(with template variables substituted) and reports errors / empty results.

Usage: python -I tests/check_dashboard_queries.py [application] [environment]
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import time

PROM = "http://127.0.0.1:9090/api/v1/query"
LOKI = "http://127.0.0.1:3100/loki/api/v1/query_range"
app = sys.argv[1] if len(sys.argv) > 1 else "funeral-back-office"
env = sys.argv[2] if len(sys.argv) > 2 else "development"
subs = {"$application": app, "$environment": env,
        "$__rate_interval": "1m", "$__range": "1h", "$__auto": "1m"}


def build_url(target, expr):
    if (target.get("datasource") or {}).get("type") == "loki":
        now = time.time()
        return LOKI + "?" + urllib.parse.urlencode(
            {"query": expr, "start": int((now - 3600) * 1e9), "end": int(now * 1e9), "limit": 50})
    return PROM + "?" + urllib.parse.urlencode({"query": expr})


def walk(panels):
    for p in panels:
        yield p
        yield from walk(p.get("panels", []))


errors = 0
for f in sorted(Path(__file__).parent.parent.glob("grafana/dashboards/*.json")):
    print(f"== {f.name}")
    for p in walk(json.loads(f.read_text(encoding="utf-8"))["panels"]):
        for t in p.get("targets", []):
            expr = t["expr"]
            for k, v in subs.items():
                expr = expr.replace(k, v)
            url = build_url(t, expr)
            try:
                with urllib.request.urlopen(url, timeout=10) as r:
                    res = json.load(r)["data"]["result"]
                status = f"{len(res)} series" if res else "EMPTY"
            except urllib.error.HTTPError as e:
                status = "ERROR " + json.load(e).get("error", str(e))
                errors += 1
            print(f"  {status:<12} {p['title']} [{t['refId']}]")
sys.exit(1 if errors else 0)
