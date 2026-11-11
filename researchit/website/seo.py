"""Search-engine plumbing: absolute page URLs, robots.txt.

Absolute URLs are built from the request's host, not from the Wagtail Site record:
the seed migration creates the Site as localhost:80, and Wagtail's own full_url /
sitemap would publish http://localhost/... until someone edits it in the admin.
The request host is safe to use: Django only accepts ALLOWED_HOSTS, Caddy redirects
www to the bare domain, and SECURE_PROXY_SSL_HEADER makes the scheme https.
"""

from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from wagtail.models import Page


def absolute_url(request: HttpRequest, page: Page | None = None) -> str:
    """Canonical absolute URL of `page`, or of the current path (no query string)."""
    path = page.get_url(request) if page is not None else None
    return request.build_absolute_uri(path or request.path)


class RequestHostSitemapMixin:
    """List the page in sitemap.xml under the request's host (see module docstring)."""

    def get_sitemap_urls(self, request=None):
        if request is None:
            return super().get_sitemap_urls(request)
        return [
            {
                "location": absolute_url(request, self),
                "lastmod": self.last_published_at or self.latest_revision_created_at,
            },
        ]


@require_GET
def robots_txt(request: HttpRequest) -> HttpResponse:
    lines = [
        "User-agent: *",
        "Disallow:",
        f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
