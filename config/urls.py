from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from researchit.core import twofactor
from researchit.website.seo import robots_txt, static_redirect

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path(f"{settings.WAGTAILADMIN_URL}2fa/", include(twofactor.urlpatterns)),
    path(settings.WAGTAILADMIN_URL, include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("robots.txt", robots_txt),
    # Requested at the root by browsers and iOS regardless of the <link> tags.
    path("favicon.ico", static_redirect("core/img/favicons/favicon.ico")),
    path(
        "apple-touch-icon.png",
        static_redirect("core/img/favicons/apple-touch-icon.png"),
    ),
    path("sitemap.xml", sitemap, name="sitemap"),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls  # Must be imported here

    urlpatterns += debug_toolbar_urls()
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Wagtail serves every remaining URL from the page tree - keep this last.
urlpatterns += [
    path("", include(wagtail_urls)),
]
