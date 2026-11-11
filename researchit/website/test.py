from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.views.csrf import csrf_failure
from django.views.defaults import permission_denied
from wagtail.models import Page, Site

from researchit.website.models import BusinessSettings, HomePage, StandardPage


class HttpsClient(Client):
    """Requests over HTTPS, so tests also pass with production's SSL redirect.

    Production trusts X-Forwarded-Proto from Caddy (SECURE_PROXY_SSL_HEADER).
    """

    def __init__(self, **defaults):
        https = {
            "wsgi.url_scheme": "https",
            "SERVER_PORT": "443",
            "HTTP_X_FORWARDED_PROTO": "https",
        }
        super().__init__(**https, **defaults)


class SeededContentTests(TestCase):
    """The seed migration replaces the hardcoded site; these pin its behaviour."""

    client_class = HttpsClient

    def test_homepage_is_site_root(self):
        home = HomePage.objects.get()
        assert Site.objects.get(is_default_site=True).root_page_id == home.pk
        assert home.services.count() == 4
        assert home.facts.count() == 4

    def test_homepage_renders_seeded_content(self):
        r = self.client.get("/")
        assert r.status_code == 200
        self.assertContains(r, "<title>Pfiffner Research IT</title>", html=False)
        self.assertContains(
            r, "Data collection systems<br>built on research expertise."
        )
        self.assertContains(r, "Research Infrastructure Development")
        self.assertContains(r, "45784924")
        self.assertContains(r, 'href="https://github.com/uzh/ddm"')
        self.assertContains(r, "mailto:nico@pfiffner-researchit.com")

    def test_settings_drive_contact_details(self):
        biz = BusinessSettings.load()
        biz.contact_email = "hello@example.com"
        biz.github_url = ""
        biz.save()
        r = self.client.get("/")
        self.assertContains(r, "mailto:hello@example.com")
        self.assertNotContains(r, "bi-github")

    def test_standard_page_renders_and_shows_in_footer(self):
        home = HomePage.objects.get()
        page = home.add_child(
            instance=StandardPage(
                title="Impressum",
                slug="impressum",
                body="<p>Legal text</p>",
                show_in_menus=True,
            )
        )
        r = self.client.get(page.url)
        assert r.status_code == 200
        self.assertContains(r, "Legal text")
        self.assertContains(self.client.get("/"), 'href="/impressum/"')

    def test_unknown_url_is_404(self):
        r = self.client.get("/does-not-exist/")
        assert r.status_code == 404
        self.assertContains(r, "Page not found", status_code=404)

    def test_pages_have_skip_link_and_landmarks(self):
        # WCAG 2.4.1 (bypass blocks) and 1.3.1 (structure).
        for url in ["/", "/does-not-exist/"]:
            html = self.client.get(url).content.decode()
            assert '<a class="skip-link" href="#main-content">' in html, url
            assert '<main id="main-content" tabindex="-1">' in html, url
            assert html.count("<h1") == 1, url
        home = self.client.get("/")
        self.assertContains(home, '<h2 class="section-label">Services</h2>')
        self.assertContains(home, '<dl class="meta-card">')

    def test_403_pages_render_their_message(self):
        request = RequestFactory().get("/", secure=True)
        r = permission_denied(request, PermissionDenied())
        self.assertContains(r, "<title>Access denied</title>", status_code=403)
        self.assertContains(r, '<main id="main-content"', status_code=403)
        r = csrf_failure(request, reason="test")
        self.assertContains(r, "<title>Request blocked</title>", status_code=403)

    def test_only_one_homepage_allowed(self):
        assert not HomePage.can_create_at(Page.objects.get(depth=1))
