"""Liveness endpoint for the container healthcheck.

Placed first in MIDDLEWARE so it answers before ALLOWED_HOSTS validation and the
HTTPS redirect: the healthcheck calls http://127.0.0.1:8000/healthz from inside
the container, where neither the public host name nor X-Forwarded-Proto is set.
"""

from django.http import HttpResponse

HEALTH_PATH = "/healthz"


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH:
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)
