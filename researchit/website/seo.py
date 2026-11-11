"""Search-engine plumbing: absolute page URLs, robots.txt.

Absolute URLs are built from the request's host, not from the Wagtail Site record:
the seed migration creates the Site as localhost:80, and Wagtail's own full_url /
sitemap would publish http://localhost/... until someone edits it in the admin.
The request host is safe to use: Django only accepts ALLOWED_HOSTS, Caddy redirects
www to the bare domain, and SECURE_PROXY_SSL_HEADER makes the scheme https.
"""

import json

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import SafeString, mark_safe
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


def static_redirect(path: str):
    """View for files browsers request at the site root (/favicon.ico, ...).

    A temporary redirect: the static file's hashed name changes with each deploy.
    """

    @require_GET
    def view(request: HttpRequest) -> HttpResponse:
        response = HttpResponseRedirect(static(path))
        response["Cache-Control"] = "public, max-age=86400"
        return response

    return view


@require_GET
def robots_txt(request: HttpRequest) -> HttpResponse:
    lines = [
        "User-agent: *",
        "Disallow:",
        f"Sitemap: {request.build_absolute_uri(reverse('sitemap'))}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


# Characters that could end the <script> element or start an HTML comment.
_JSON_SCRIPT_ESCAPES = {ord("<"): "\\u003C", ord(">"): "\\u003E", ord("&"): "\\u0026"}


def structured_data(request: HttpRequest, home, biz) -> SafeString:
    """schema.org JSON-LD for the business, built from the CMS content.

    `home` is the HomePage, `biz` the BusinessSettings. A data block, not a script:
    browsers don't execute it, so the strict CSP doesn't need to allow it.
    """
    site_url = absolute_url(request, home)
    business = {
        "@context": "https://schema.org",
        # Organization: ProfessionalService is deprecated by schema.org, and Google
        # requires a street address for LocalBusiness types. There is no storefront.
        "@type": "Organization",
        "@id": f"{site_url}#business",
        "name": biz.business_name,
        "url": site_url,
        "logo": request.build_absolute_uri(
            static("core/img/favicons/rit_favicon_512x512.png")
        ),
    }
    if home.search_description:
        business["description"] = home.search_description
    if biz.contact_email:
        business["email"] = biz.contact_email
    if biz.cvr_number:
        business["taxID"] = biz.cvr_number
    if biz.country:
        business["address"] = {"@type": "PostalAddress", "addressCountry": biz.country}

    services = list(home.services.all())
    if services:
        business["hasOfferCatalog"] = {
            "@type": "OfferCatalog",
            "name": "Services",
            "itemListElement": [
                {
                    "@type": "Offer",
                    "itemOffered": {
                        "@type": "Service",
                        "name": s.title,
                        "description": s.description,
                    },
                }
                for s in services
            ],
        }

    if biz.owner_name:
        same_as = [u for u in [biz.github_url, *biz.profile_url_list] if u]
        founder = {"@type": "Person", "name": biz.owner_name}
        if same_as:
            founder["sameAs"] = same_as
        business["founder"] = founder

    data = json.dumps(business, ensure_ascii=False).translate(_JSON_SCRIPT_ESCAPES)
    return mark_safe(f'<script type="application/ld+json">{data}</script>')  # noqa: S308
