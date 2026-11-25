"""
Technical monitoring endpoints for the Application Monitoring Platform.

  /health/live/   process responds                          -> 200
  /health/ready/  required dependencies (database) available -> 200 / 503
  /metrics        Prometheus metrics, bearer-token protected

Privacy: responses contain no personal data, credentials, hostnames or
exception details. Metric labels use Django view names, never raw URLs.
"""

import hmac
import logging
import os

from django.db import connections
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django_prometheus.exports import ExportToDjangoView
from prometheus_client import Gauge

logger = logging.getLogger(__name__)

METRICS_TOKEN_ENV = "MONITORING_METRICS_TOKEN"

DEPENDENCY_UP = Gauge(
    "app_dependency_up",
    "1 if a required dependency passed its readiness check, else 0.",
    ["dependency"],
)


def _check_database():
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        ok = True
    except Exception:  # noqa: BLE001 - any failure means "not ready"
        # Log the exception type only; messages may contain paths or credentials.
        logger.warning("Readiness check failed: database unavailable")
        ok = False
    DEPENDENCY_UP.labels(dependency="database").set(1 if ok else 0)
    return ok


@never_cache
@require_GET
def health_live(request):
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def health_ready(request):
    checks = {"database": "ok" if _check_database() else "fail"}
    ready = all(v == "ok" for v in checks.values())
    return JsonResponse(
        {"status": "ok" if ready else "fail", "checks": checks},
        status=200 if ready else 503,
    )


@never_cache
@require_GET
def metrics(request):
    token = os.environ.get(METRICS_TOKEN_ENV, "")
    if not token:
        # Endpoint disabled unless a token is configured.
        return HttpResponse(status=404)
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
        return HttpResponse(status=401, headers={"WWW-Authenticate": "Bearer"})
    _check_database()  # refresh app_dependency_up at scrape time
    return ExportToDjangoView(request)
