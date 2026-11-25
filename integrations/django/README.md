# Django integration (Phase 2 placeholder)

This folder will hold the reusable Django integration for the Funeral Back Office System and later Django applications.

It is not implemented yet. Phase 2 starts by reviewing the existing Funeral Back Office code. No changes will be made to that application without approval.

Planned contents:

| File | Purpose |
|---|---|
| `requirements.txt` | Pinned `django-prometheus` version |
| `health_views.py` | `/health/live/` and `/health/ready/` views. They return JSON, return HTTP 503 when the database is unavailable, and expose no sensitive details. |
| `example_settings.py` | Example settings changes: apps, middleware, and how to restrict `/metrics` |

See [docs/application-integration.md](../../docs/application-integration.md).
