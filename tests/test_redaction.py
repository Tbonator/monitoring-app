"""
Unit test for the funeral app's redact() function. All values are FAKE test data.

Run: $env:FUNERAL_APP_DIR=...; & $py tests\test_redaction.py
"""
import os
import sys

sys.path.insert(0, os.environ["FUNERAL_APP_DIR"])
from funeralmanagementsystem.observability import redact  # noqa: E402

CASES = [
    # (input, substrings that must NOT survive, substring that must appear)
    ("Lookup for ID 9001015009087 failed", ["9001015009087"], "[REDACTED_ID]"),
    ("Call +27 82 555 0123 or 082-555-0123", ["555 0123", "555-0123"], "[REDACTED_PHONE]"),
    ("Contact jane.doe@example.com", ["jane.doe@example.com"], "[REDACTED_EMAIL]"),
    ("Card 4111 1111 1111 1111 declined", ["4111 1111 1111 1111"], "[REDACTED_NUMBER]"),
    ("login password=Sup3rS3cret! user ok", ["Sup3rS3cret!"], "password=[REDACTED]"),
    ('{"token": "abc123def456ghi789"}', ["abc123def456ghi789"], "[REDACTED]"),
    ("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig", ["eyJhbGciOiJIUzI1NiJ9"], "Bearer [REDACTED]"),
    ("Cookie: sessionid=k3j4h5g6f7d8s9a0", ["k3j4h5g6f7d8s9a0"], "[REDACTED]"),
    ('"GET /arrangements/?q=Thandi+Mokoena HTTP/1.1" 200', ["Thandi", "Mokoena"], "?[QUERY_REMOVED]"),
    ("Not Found: /arrangements/4521/edit/", ["4521"], "/arrangements/:id/edit/"),
]
# Things that must be preserved (avoid over-redaction of operational data).
KEEP = [
    ('"GET /health/live/ HTTP/1.1" 200 16', '"GET /health/live/ HTTP/1.1" 200 16'),
    ("2026-11-25 20:01:11 request took 0.25s", "2026-11-25 20:01:11 request took 0.25s"),
]

failures = 0
for text, forbidden, expected in CASES:
    out = redact(text)
    leaked = [f for f in forbidden if f in out]
    ok = not leaked and expected in out
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {out}" + (f"   leaked={leaked}" if leaked else ""))
for text, expected in KEEP:
    out = redact(text)
    ok = out == expected
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  (unchanged) {out}")
print(f"\n{len(CASES) + len(KEEP) - failures}/{len(CASES) + len(KEEP)} passed")
sys.exit(1 if failures else 0)
