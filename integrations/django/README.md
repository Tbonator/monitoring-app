# Django integration

This folder holds the reusable integration for Django applications. It was first applied to the Funeral Back Office System in Phase 2.

| File | Purpose |
|---|---|
| `requirements.txt` | Pinned `django-prometheus` version |
| `health_views.py` | `/health/live/`, `/health/ready/` and the token-protected `/metrics`. Copy it into the project package as `monitoring.py`. |
| `example_settings.py` | The settings and URL additions to make, in order |

## Steps for a new Django application

1. Install the dependency in the app's environment, for example with `pipenv install "django-prometheus==2.6.0.dev26"`.
2. Copy `health_views.py` to `<project_package>/monitoring.py`.
3. Apply the additions in `example_settings.py` to `settings.py` and `urls.py`.
4. Generate a token in `monitoring-app/secrets/<app>-metrics.token`, and set `MONITORING_METRICS_TOKEN` in the app's environment.
5. Add a Prometheus job with `application` and `environment` labels and `authorization.credentials_file`.
6. Add Uptime Kuma monitors for `/health/live/` and `/health/ready/`.

Endpoint behaviour, privacy rules and networking are described in [docs/application-integration.md](../../docs/application-integration.md).
