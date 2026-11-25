"""
Example settings ADDITIONS for integrating a Django project with the
Application Monitoring Platform. Append to the project's settings.py; do not
replace existing values.

Reference implementation: Funeral Back Office System (Phase 2).
"""

# Each block below accepts list OR tuple settings and is safe to apply twice.

# 1. Instrumentation app
INSTALLED_APPS = list(INSTALLED_APPS)  # noqa: F821
if "django_prometheus" not in INSTALLED_APPS:
    INSTALLED_APPS.append("django_prometheus")

# 2. django-prometheus must wrap ALL other middleware (first and last).
#    Any existing (possibly misplaced) copies are removed, then re-added
#    in the correct positions.
_PROM_BEFORE = "django_prometheus.middleware.PrometheusBeforeMiddleware"
_PROM_AFTER = "django_prometheus.middleware.PrometheusAfterMiddleware"
MIDDLEWARE = (
    [_PROM_BEFORE]
    + [m for m in MIDDLEWARE if m not in (_PROM_BEFORE, _PROM_AFTER)]  # noqa: F821
    + [_PROM_AFTER]
)

# 3. Allow the monitoring containers to reach the app via Docker Desktop.
ALLOWED_HOSTS = list(ALLOWED_HOSTS)  # noqa: F821
for _host in ["localhost", "127.0.0.1", "[::1]", "host.docker.internal"]:
    if _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)
del _PROM_BEFORE, _PROM_AFTER, _host

# 4. urls.py (project-level) - add BEFORE existing includes:
#
#     from <project_package> import monitoring   # copy of health_views.py
#     urlpatterns = [
#         path("health/live/", monitoring.health_live, name="health_live"),
#         path("health/ready/", monitoring.health_ready, name="health_ready"),
#         path("metrics", monitoring.metrics, name="prometheus_metrics"),
#         ...existing patterns...
#     ]
#
# Do NOT use include("django_prometheus.urls"): it exposes /metrics without
# authentication. monitoring.metrics requires a bearer token.

# 5. Environment (not a setting): the Django process must have
#     MONITORING_METRICS_TOKEN=<same value as monitoring-app/secrets/<app>-metrics.token>
#   If unset, /metrics returns 404 (disabled).
