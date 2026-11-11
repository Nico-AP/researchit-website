from django.test import Client, TestCase
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

    def test_only_one_homepage_allowed(self):
        assert not HomePage.can_create_at(Page.objects.get(depth=1))
