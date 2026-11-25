"""
Readiness test: with the database unavailable, /health/ready/ must return 503,
/health/live/ must still return 200, and no error details may leak.

Run with the funeral app's virtualenv Python (see tests/README.md).
"""
import json
import os
import sys
from pathlib import Path

APP_DIR = os.environ["FUNERAL_APP_DIR"]
sys.path[:0] = [str(Path(__file__).parent / "django_harness"), APP_DIR]
os.environ["DJANGO_SETTINGS_MODULE"] = "monitoring_test_settings"
os.environ["MONITORING_TEST_DB_FAIL"] = "1"

import django  # noqa: E402

django.setup()
from django.test import Client  # noqa: E402

c = Client()
failures = []

live = c.get("/health/live/")
if live.status_code != 200:
    failures.append(f"live expected 200, got {live.status_code}")

ready = c.get("/health/ready/")
body = ready.content.decode()
if ready.status_code != 503:
    failures.append(f"ready expected 503, got {ready.status_code}")
if json.loads(body) != {"status": "fail", "checks": {"database": "fail"}}:
    failures.append(f"unexpected ready body: {body}")
for leak in ("Z:", "sqlite", "Traceback", "OperationalError", "unable to open"):
    if leak.lower() in body.lower():
        failures.append(f"ready body leaks diagnostic detail: {leak}")

print(f"live  -> {live.status_code} {live.content.decode()}")
print(f"ready -> {ready.status_code} {body}")
if failures:
    print("FAIL:", *failures, sep="\n  ")
    sys.exit(1)
print("PASS: readiness reports database failure without leaking details")
