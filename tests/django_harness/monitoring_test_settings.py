"""
Out-of-tree TEST settings for the Funeral Back Office monitoring tests.

Layers on top of the real settings WITHOUT modifying the application:
  * MONITORING_TEST_DB_FAIL=1  -> point the DB at a non-existent directory
                                  (simulates database unavailability; the real
                                  db.sqlite3 is never touched)
  * Adds /_monitoring-test/error/ and /_monitoring-test/slow/ routes.

Development only. Never use against production.
"""
import os

from funeralmanagementsystem.settings import *  # noqa: F401,F403

ROOT_URLCONF = "monitoring_test_urls"
ALLOWED_HOSTS = ALLOWED_HOSTS + ["testserver"]  # noqa: F405

if os.environ.get("MONITORING_TEST_DB_FAIL") == "1":
    DATABASES = {  # noqa: F811
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "Z:/monitoring-test-nonexistent-dir/unavailable.sqlite3",
        }
    }
