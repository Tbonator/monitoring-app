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


urlpatterns = [
    path("_monitoring-test/error/", simulated_error, name="monitoring_test_error"),
    path("_monitoring-test/slow/", simulated_slow, name="monitoring_test_slow"),
    path("", include("funeralmanagementsystem.urls")),
]
