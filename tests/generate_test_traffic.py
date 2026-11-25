"""
Controlled test-traffic generator (development only).

Requires the Django app to run in test mode with the harness routes
(tests/django_harness). Produces a mix of normal, HTTP 500 and slow requests
so that error-rate and latency metrics/alerts can be validated.

Usage: python -I tests/generate_test_traffic.py [minutes] [base_url]
"""
import sys
import threading
import time
import urllib.error
import urllib.request

minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 7
base = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000"
if not base.startswith(("http://127.0.0.1", "http://localhost")):
    sys.exit("Refusing to generate test traffic against a non-local target.")
end = time.time() + minutes * 60
counts = {"ok": 0, "error": 0, "slow": 0, "fail": 0}
lock = threading.Lock()


def hit(path, key):
    try:
        urllib.request.urlopen(base + path, timeout=15).read()
        res = key
    except urllib.error.HTTPError as e:
        res = "error" if e.code == 500 else "fail"
    except Exception:
        res = "fail"
    with lock:
        counts[res] += 1


def fast_loop():
    while time.time() < end:
        for _ in range(4):
            hit("/health/live/", "ok")
        hit("/_monitoring-test/error/", "error")
        time.sleep(1)


def slow_loop():
    while time.time() < end:
        hit("/_monitoring-test/slow/?s=3", "slow")


threads = [threading.Thread(target=fast_loop)] + [threading.Thread(target=slow_loop) for _ in range(2)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print("requests:", counts)
