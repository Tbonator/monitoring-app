"""Shared panel helpers for the provisioned Grafana dashboard generators."""

DS = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}
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


def var(name, label, query):
    return {"name": name, "label": label, "type": "query", "datasource": DS,
            "query": {"query": query, "refId": name}, "definition": query,
            "refresh": 2, "includeAll": True, "multi": True, "sort": 1,
            "current": {"text": "All", "value": "$__all"}}


def write(dash, path):
    import json
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dash, fh, indent=2)
        fh.write("\n")
