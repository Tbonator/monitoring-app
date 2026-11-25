"""
Observability for the Application Monitoring Platform (Phase 3).

  * redact()              - removes personal/sensitive data from free text
  * RedactingFilter       - logging filter applying redact() to every record
  * JsonFormatter         - one JSON object per line (for Grafana Alloy -> Loki)
  * init_error_tracking() - GlitchTip via sentry-sdk, privacy-restricted

Privacy (POPIA): request bodies, cookies, headers, query strings, user
identity, local variables and DB query data are never sent. All remaining
text passes through redact(). Redaction is best-effort pattern matching:
code must still avoid logging personal information in the first place.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone

APPLICATION = "funeral-back-office"

_REDACTIONS = [
    # Bearer / Basic authorization values. Must run BEFORE the key=value rule,
    # otherwise "Authorization: Bearer <tok>" redacts the word "Bearer" only.
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), r"\1 [REDACTED]"),
    # Credentials in key=value / key: value form (password=..., "token": "...")
    (re.compile(
        r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key|sessionid|csrftoken|"
        r"csrfmiddlewaretoken|cookie|authorization|dsn)\b(\"?'?\s*[:=]\s*\"?'?)(?!(?:Bearer|Basic) \[REDACTED\])([^\s\"'&,;]+)"),
     r"\1\2[REDACTED]"),
    # Email addresses
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[REDACTED_EMAIL]"),
    # South African identity numbers (13 digits)
    (re.compile(r"(?<!\d)\d{13}(?!\d)"), "[REDACTED_ID]"),
    # Long digit runs: card/account numbers (13-19 digits, optional separators)
    (re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"), "[REDACTED_NUMBER]"),
    # Telephone numbers: +27 / 0 prefixed SA numbers and other international forms
    (re.compile(r"(?<![\w])(?:\+\d{1,3}[\s-]?|0)\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)"),
     "[REDACTED_PHONE]"),
    # Query strings may carry search terms (names etc.): drop them entirely
    (re.compile(r"(/[^\s\"'?]*)\?[^\s\"']*"), r"\1?[QUERY_REMOVED]"),
    # Numeric path segments (case/record identifiers): /arrangements/123/ -> /arrangements/:id/
    (re.compile(r"(?<=/)\d+(?=/|\s|$|\"|')"), ":id"),
]


def redact(text):
    """Return text with sensitive values replaced. Non-strings are returned unchanged."""
    if not isinstance(text, str) or not text:
        return text
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


class RedactingFilter(logging.Filter):
    """Redacts the rendered message (and exception text) of every log record."""

    def filter(self, record):
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - malformed format args
            message = str(record.msg)
        record.msg = redact(message)
        record.args = None
        # Never let the HttpRequest object reach formatters/handlers.
        if hasattr(record, "request"):
            record.request = None
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line. Only allow-listed, non-personal fields."""

    def __init__(self, environment="development"):
        super().__init__()
        self.environment = environment

    def format(self, record):
        entry = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": redact(record.getMessage()),
            "application": APPLICATION,
            "environment": self.environment,
        }
        status_code = getattr(record, "status_code", None)
        if isinstance(status_code, int):
            entry["status_code"] = status_code
        if record.exc_info:
            entry["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            entry["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(entry, ensure_ascii=False)


class DailyFileHandler(logging.Handler):
    """
    Writes to <directory>/<prefix>-YYYY-MM-DD.log (UTC date), append-only.

    No renames: rename-based rotation (RotatingFileHandler) is not tracked
    reliably by Grafana Alloy across the Docker Desktop bind mount on Windows,
    and renaming open files on Windows is fragile. A new file is started each
    day; files older than retention_days are deleted.
    """

    def __init__(self, directory, prefix, retention_days=7, encoding="utf-8"):
        super().__init__()
        self.directory = directory
        self.prefix = prefix
        self.retention_days = int(retention_days)
        self.encoding = encoding
        self._date = None
        self._stream = None

    def _open_for(self, date_str):
        if self._stream:
            self._stream.close()
        path = os.path.join(self.directory, f"{self.prefix}-{date_str}.log")
        self._stream = open(path, "a", encoding=self.encoding)
        self._date = date_str
        self._prune()

    def _prune(self):
        cutoff = datetime.now(timezone.utc).timestamp() - self.retention_days * 86400
        try:
            for name in os.listdir(self.directory):
                if name.startswith(self.prefix + "-") and name.endswith(".log"):
                    full = os.path.join(self.directory, name)
                    if os.path.getmtime(full) < cutoff:
                        os.remove(full)
        except OSError:
            pass  # pruning must never break logging

    def emit(self, record):
        try:
            date_str = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%d")
            if date_str != self._date or self._stream is None:
                self._open_for(date_str)
            self._stream.write(self.format(record) + "\n")
            self._stream.flush()
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def close(self):
        self.acquire()
        try:
            if self._stream:
                self._stream.close()
                self._stream = None
        finally:
            self.release()
        super().close()


def build_logging_config(base_dir, environment="development"):
    """LOGGING dict: JSON file (rotated) + console, both redacted."""
    log_dir = os.environ.get("APP_LOG_DIR", str(base_dir / "logs"))
    os.makedirs(log_dir, exist_ok=True)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"redact": {"()": RedactingFilter}},
        "formatters": {
            "json": {"()": JsonFormatter, "environment": environment},
            "console": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
        },
        "handlers": {
            "json_file": {
                "()": DailyFileHandler,
                "directory": log_dir,
                "prefix": APPLICATION,
                "retention_days": int(os.environ.get("APP_LOG_RETENTION_DAYS", "7")),
                "formatter": "json",
                "filters": ["redact"],
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "filters": ["redact"],
            },
        },
        "root": {"handlers": ["console", "json_file"], "level": "INFO"},
        "loggers": {
            # Let these propagate to root; do not add handlers twice.
            "django": {"level": "INFO", "propagate": True},
            "django.server": {"level": "INFO", "propagate": True},
            # SQL text is never logged.
            "django.db.backends": {"level": "WARNING", "propagate": True},
        },
    }


# --------------------------------------------------------------------------
# Error tracking (GlitchTip, Sentry-protocol compatible)
# --------------------------------------------------------------------------

def _scrub(value, depth=0):
    if depth > 12:
        return value
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: _scrub(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v, depth + 1) for v in value]
    return value


def _before_send(event, hint):
    # Remove anything identifying the user or carrying request payloads.
    event.pop("user", None)
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("data", "cookies", "headers", "query_string", "env"):
            request.pop(key, None)
    # Strip local variables from every stack frame (defence in depth).
    for exc in (event.get("exception") or {}).get("values", []) or []:
        for frame in ((exc.get("stacktrace") or {}).get("frames") or []):
            frame.pop("vars", None)
    for thread in (event.get("threads") or {}).get("values", []) or []:
        for frame in ((thread.get("stacktrace") or {}).get("frames") or []):
            frame.pop("vars", None)
    event.pop("extra", None)
    return _scrub(event)


def _before_breadcrumb(crumb, hint):
    if crumb.get("category") in ("query", "httplib", "http"):
        return None  # SQL and outbound HTTP breadcrumbs may carry data
    crumb.pop("data", None)
    return _scrub(crumb)


def init_error_tracking(environment="development", release=None):
    """Enable GlitchTip reporting only when GLITCHTIP_DSN is set."""
    dsn = os.environ.get("GLITCHTIP_DSN", "").strip()
    if not dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        server_name=APPLICATION,      # never the machine hostname
        integrations=[DjangoIntegration(
            # Report 5xx responses except 503: /health/ready/ deliberately returns
            # 503 during dependency outages and must not flood GlitchTip.
            failed_request_status_codes=set(range(500, 600)) - {503},
        )],
        traces_sample_rate=None,      # error tracking only; no performance tracing
        max_request_body_size="never",
        data_collection={
            "user_info": False,
            "cookies": {"mode": "off"},
            "http_headers": {"request": {"mode": "off"}},
            "http_bodies": [],
            "url_query_params": {"mode": "off"},
            "graphql": {"document": False, "variables": False},
            "gen_ai": {"inputs": False, "outputs": False},
            "mcp": {"inputs": False, "outputs": False},
            "database_query_data": False,
            "queues": False,
            "stack_frame_variables": False,
            "frame_context_lines": 3,
        },
        before_send=_before_send,
        before_breadcrumb=_before_breadcrumb,
        send_client_reports=False,
    )
    return True
