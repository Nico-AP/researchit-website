"""Client IP address behind the Caddy reverse proxy (used by django-axes).

Caddy is the only proxy in front of the app. It appends the address it received
the request from to X-Forwarded-For, so the *last* entry is the one we can trust;
anything before it was sent by the client and may be forged. REMOTE_ADDR is
Caddy's own container address and is only used when the header is missing.
"""

from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    last = forwarded_for.rsplit(",", 1)[-1].strip()
    return last or request.META.get("REMOTE_ADDR")
