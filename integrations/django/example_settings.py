"""
Example settings ADDITIONS for integrating a Django project with the
Application Monitoring Platform. Append to the project's settings.py; do not
replace existing values.

Reference implementation: Funeral Back Office System (Phase 2).
"""

# 1. Instrumentation app
INSTALLED_APPS += ["django_prometheus"]  # noqa: F821

# 2. django-prometheus must wrap ALL other middleware (first and last).
MIDDLEWARE = (  # noqa: F821
    ["django_prometheus.middleware.PrometheusBeforeMiddleware"]
    + MIDDLEWARE  # noqa: F821
    + ["django_prometheus.middleware.PrometheusAfterMiddleware"]
)

# 3. Allow the monitoring containers to reach the app via Docker Desktop.
ALLOWED_HOSTS += ["localhost", "127.0.0.1", "[::1]", "host.docker.internal"]  # noqa: F821

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
