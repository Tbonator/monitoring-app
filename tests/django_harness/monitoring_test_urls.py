"""TEST-ONLY routes for failure simulation. Development only."""
import time

from django.http import HttpResponse
from django.urls import include, path


def simulated_error(request):
    return HttpResponse("simulated server error", status=500)


def simulated_slow(request):
    seconds = min(float(request.GET.get("s", "2.5")), 10.0)
    time.sleep(seconds)
    return HttpResponse("slow ok")


def simulated_exception(request):
    """Unhandled exception carrying FAKE personal data in every channel.
    Used to prove that nothing sensitive reaches GlitchTip or Loki."""
    import logging

    fake_id_number = "9001015009087"          # local variable (must not be sent)
    fake_email = "jane.doe@example.com"
    logging.getLogger("funeralapp.test").warning(
        "Processing client %s, phone 082 555 0123, ID %s", fake_email, fake_id_number
    )
    raise ValueError(f"Simulated failure for ID {fake_id_number} / {fake_email}")


urlpatterns = [
    path("_monitoring-test/error/", simulated_error, name="monitoring_test_error"),
    path("_monitoring-test/exception/", simulated_exception, name="monitoring_test_exception"),
    path("_monitoring-test/slow/", simulated_slow, name="monitoring_test_slow"),
    path("", include("funeralmanagementsystem.urls")),
]
