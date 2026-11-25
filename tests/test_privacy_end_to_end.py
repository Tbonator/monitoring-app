"""
End-to-end privacy test (development only).

Prerequisite: Django running in TEST MODE with GLITCHTIP_DSN set
(see tests/README.md). The test:
  1. Calls /_monitoring-test/exception/ with FAKE personal data in the query
     string, cookies and Authorization header; the view itself logs and raises
     with fake ID/email/phone values.
  2. Fetches the newest GlitchTip event (via docker exec) and the last few
     minutes of Loki logs.
  3. Fails if any fake sensitive value appears in either store.

Run: python -I tests/test_privacy_end_to_end.py
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

FAKE_VALUES = [
    "9001015009087",            # ID number (local var + message + log)
    "8507125009081",            # ID number in query string
    "jane.doe@example.com",
    "082 555 0123",
    "Thandi", "Mokoena",        # name in query string
    "k3j4h5g6f7d8s9a0fake",     # session cookie
    "fakecsrf123456",           # csrf cookie
    "eyJhbGciOiJIUzI1NiJ9",     # bearer token
]

# 1. Trigger
url = "http://127.0.0.1:8000/_monitoring-test/exception/?name=Thandi+Mokoena&id=8507125009081"
req = urllib.request.Request(url, headers={
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.fakepayload.fakesig",
    "Cookie": "sessionid=k3j4h5g6f7d8s9a0fake; csrftoken=fakecsrf123456",
})
started = time.time()
try:
    urllib.request.urlopen(req, timeout=15)
    print("FAIL: expected HTTP 500 from the exception route")
    sys.exit(1)
except urllib.error.HTTPError as e:
    print(f"trigger -> HTTP {e.code}")

time.sleep(25)  # SDK flush + GlitchTip ingestion + Alloy poll

# 2a. Newest GlitchTip event
py = (
    "from apps.issue_events.models import IssueEvent; import json;"
    "e=IssueEvent.objects.order_by('-timestamp').first();"
    "print('EVENT_JSON=' + (json.dumps({'ts': e.timestamp.timestamp(), 'title': e.title, 'data': e.data}, default=str) if e else 'null'))"
)
out = subprocess.run(["docker", "exec", "glitchtip", "python", "manage.py", "shell", "--no-imports", "-c", py],
                     capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
line = next((ln[len("EVENT_JSON="):] for ln in out if ln.startswith("EVENT_JSON=")), "null")
event = json.loads(line) if line != "null" else None
if not event or event["ts"] < started - 5:
    print("FAIL: no new GlitchTip event received")
    sys.exit(1)
event_text = json.dumps(event, ensure_ascii=False)
print(f"glitchtip event: {event['title']}")

# 2b. Loki logs from the last 5 minutes
q = urllib.parse.urlencode({
    "query": '{application="funeral-back-office"}',
    "start": str(int((time.time() - 300) * 1e9)),
    "limit": "500",
})
with urllib.request.urlopen(f"http://127.0.0.1:3100/loki/api/v1/query_range?{q}", timeout=10) as r:
    loki = json.load(r)
lines = [v[1] for s in loki["data"]["result"] for v in s["values"]]
loki_text = "\n".join(lines)
print(f"loki lines (5 min): {len(lines)}")

# 3. Assertions
failures = []
for store, text in (("GlitchTip", event_text), ("Loki", loki_text)):
    for value in FAKE_VALUES:
        if value in text:
            failures.append(f"{store} contains '{value}'")
if '"vars"' in event_text:
    failures.append("GlitchTip event contains stack-frame local variables")
for marker in ("[REDACTED_ID]", "[REDACTED_EMAIL]"):
    if marker not in event_text:
        failures.append(f"GlitchTip event missing expected marker {marker}")
if "[REDACTED_PHONE]" not in loki_text:
    failures.append("Loki missing expected [REDACTED_PHONE] (log line not ingested?)")

print("\n--- GlitchTip title:", event["title"])
crumbs = (event["data"].get("breadcrumbs") or {})
crumbs = crumbs.get("values", crumbs) if isinstance(crumbs, dict) else crumbs
for c in (crumbs or [])[-3:]:
    print("--- breadcrumb:", c.get("message"))
req_data = event["data"].get("request") or {}
print("--- request keys sent:", sorted(req_data.keys()), "url:", req_data.get("url"))

if failures:
    print("\nFAIL:", *failures, sep="\n  ")
    sys.exit(1)
print("\nPASS: no fake sensitive value reached GlitchTip or Loki")
