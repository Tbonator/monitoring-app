"""
Daily log-file handler test (development only).

Uses the app's DailyFileHandler + JsonFormatter on the real log directory
while Grafana Alloy tails it through the read-only bind mount. Checks:
  * a day change switches to a new file without errors (records dated
    "yesterday" then "today"; future dates would be rejected by Loki),
  * files older than the retention period are pruned,
  * every marked line reaches Loki.

Usage: $env:FUNERAL_APP_DIR=...; & $py tests\test_log_rotation.py
"""
import json
import logging
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

app_dir = os.environ["FUNERAL_APP_DIR"]
sys.path.insert(0, app_dir)
from funeralmanagementsystem.observability import DailyFileHandler, JsonFormatter  # noqa: E402

log_dir = os.path.join(app_dir, "logs")
run = uuid.uuid4().hex[:8]
now = datetime.now(timezone.utc)
yesterday = now - timedelta(days=1)

# Planted stale file: must be pruned (mtime 8 days ago).
stale = os.path.join(log_dir, "funeral-back-office-2000-01-01.log")
with open(stale, "w", encoding="utf-8") as fh:
    fh.write("")
old = time.time() - 8 * 86400
os.utime(stale, (old, old))

errors = []
handler = DailyFileHandler(log_dir, "funeral-back-office", retention_days=7)
handler.handleError = lambda record: errors.append(sys.exc_info()[1])
handler.setFormatter(JsonFormatter("development"))

N = 20
for i in range(N):
    when = yesterday if i < N // 2 else now
    rec = logging.LogRecord("rotation-test", logging.INFO, __file__, 0,
                            f"rotation-test run={run} seq={i:03d}", None, None)
    rec.created = when.timestamp()
    handler.handle(rec)
handler.close()

files = sorted(f for f in os.listdir(log_dir) if f.startswith("funeral-back-office-"))
print("files:", files)
print("handler errors:", errors)

deadline = time.time() + 90
seqs = set()
while time.time() < deadline:
    q = urllib.parse.urlencode({
        "query": f'{{application="funeral-back-office"}} |= "rotation-test run={run}"',
        "start": str(int((yesterday.timestamp() - 600) * 1e9)), "limit": "1000"})
    with urllib.request.urlopen(f"http://127.0.0.1:3100/loki/api/v1/query_range?{q}", timeout=10) as r:
        res = json.load(r)["data"]["result"]
    seqs = {json.loads(v[1])["message"].split("seq=")[1][:3] for s in res for v in s["values"]}
    if len(seqs) == N:
        break
    time.sleep(5)

missing = sorted({f"{i:03d}" for i in range(N)} - seqs)
today_missing = [s for s in missing if int(s) >= N // 2]

# Yesterday's (backdated) entries: Loki queries ingesters only for the last 3h
# (query_ingesters_within), so backdated entries are invisible until the chunk
# is flushed (~30 min idle). Verify instead that Alloy read the whole file.
import subprocess  # noqa: E402

yfile = f"funeral-back-office-{yesterday:%Y-%m-%d}.log"
ysize = os.path.getsize(os.path.join(log_dir, yfile))
positions = subprocess.run(
    ["docker", "exec", "alloy", "sh", "-c", "find /var/lib/alloy/data -name 'positions*' -exec cat {} \\;"],
    capture_output=True, text=True).stdout
lines = positions.splitlines()
ypos = next((lines[i + 2].split('"')[1] for i, ln in enumerate(lines)
             if ln.strip().endswith(yfile) and i + 2 < len(lines)), None)

checks = {
    "no handler errors": not errors,
    "yesterday + today files exist": all(
        f"funeral-back-office-{d:%Y-%m-%d}.log" in files for d in (yesterday, now)),
    "stale file pruned": not os.path.exists(stale),
    f"today's {N // 2} lines in Loki": not today_missing,
    f"Alloy read yesterday's new file completely ({ypos}/{ysize} bytes)": ypos == str(ysize),
}
if missing and not today_missing:
    print("note: backdated lines not yet queryable (expected until Loki flushes the chunk)")
for name, ok in checks.items():
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
if missing:
    print("missing seqs:", missing)
sys.exit(0 if all(checks.values()) else 1)
