"""Wagtail content models for the website.

- BusinessSettings: site-wide business details (Settings > Business details).
- HomePage: the one-page site (hero, services, about, contact).
- StandardPage: simple text pages such as the Impressum or privacy policy.
"""

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import RichTextField
from wagtail.models import Orderable, Page

from researchit.website.seo import RequestHostSitemapMixin

INLINE_FEATURES = ["bold", "italic", "link"]
BODY_FEATURES = [
    "h2",
    "h3",
    "bold",
    "italic",
    "link",
    "ol",
    "ul",
    "hr",
    "document-link",
]


@register_setting(icon="site")
class BusinessSettings(BaseGenericSetting):
    """Details used in several places: navbar, hero, contact chips, footer."""

    business_name = models.CharField(max_length=100, default="Pfiffner Research it")
    owner_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="The person behind the business (page author, search engines).",
    )
    contact_email = models.EmailField(blank=True)
    github_url = models.URLField("GitHub URL", blank=True)
    cvr_number = models.CharField("CVR number", max_length=20, blank=True)
    country = models.CharField(max_length=50, blank=True)
    profile_urls = models.TextField(
        "Profile links",
        blank=True,
        help_text=(
            "One URL per line, e.g. Google Scholar, ORCID, LinkedIn. Not shown on the "
            "page; tells search engines these profiles belong to the owner."
        ),
    )

    panels = [
        FieldPanel("business_name"),
        FieldPanel("owner_name"),
        MultiFieldPanel(
            [
                FieldPanel("contact_email"),
                FieldPanel("github_url"),
                FieldPanel("profile_urls"),
            ],
            heading="Contact",
        ),
        MultiFieldPanel(
            [FieldPanel("cvr_number"), FieldPanel("country")],
            heading="Legal (shown in the footer)",
        ),
    ]

    class Meta:
        verbose_name = "Business details"

    def __str__(self):
        return self.business_name

    @property
    def profile_url_list(self) -> list[str]:
        return [u.strip() for u in self.profile_urls.splitlines() if u.strip()]


class HomePage(RequestHostSitemapMixin, Page):
    """The one-page website. Exactly one, at the root of the site."""

    template = "website/home_page.html"
    max_count = 1
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["researchit_website.StandardPage"]

    # Hero
    hero_tagline = models.CharField(max_length=200, blank=True)
    hero_headline = models.TextField(
        blank=True,
        help_text="Line breaks are kept.",
    )
    hero_text = models.TextField(blank=True)
    cta_label = models.CharField(
        "Call-to-action label",
        max_length=50,
        default="Get in touch",
        help_text="Button in the navbar and hero; links to the contact e-mail.",
    )

    # About
    about_text = RichTextField(features=INLINE_FEATURES, blank=True)
    about_availability = models.CharField(max_length=200, blank=True)

    # Contact
    contact_text = models.TextField(blank=True)

    content_panels = [
        *Page.content_panels,
        MultiFieldPanel(
            [
                FieldPanel("hero_tagline"),
                FieldPanel("hero_headline"),
                FieldPanel("hero_text"),
                FieldPanel("cta_label"),
            ],
            heading="Hero",
        ),
        InlinePanel("services", heading="Services", label="Service"),
        MultiFieldPanel(
            [FieldPanel("about_text"), FieldPanel("about_availability")],
            heading="About",
        ),
        InlinePanel("facts", heading="About: facts card", label="Fact"),
        FieldPanel("contact_text", heading="Contact"),
    ]

    class Meta:
        verbose_name = "Home page"


class ServiceItem(Orderable):
    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="services")
    title = models.CharField(max_length=100)
    description = models.TextField()

    panels = [FieldPanel("title"), FieldPanel("description")]

    def __str__(self):
        return self.title


class FactItem(Orderable):
    """A key/value row in the about section, e.g. "Location: Denmark"."""

    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="facts")
    label = models.CharField(max_length=50)
    value = models.CharField(max_length=200)

    panels = [FieldPanel("label"), FieldPanel("value")]

    def __str__(self):
        return f"{self.label}: {self.value}"


class StandardPage(RequestHostSitemapMixin, Page):
    """A simple text page (Impressum, privacy policy, ...).

    Tick "Show in menus" (Promote tab) to link it in the footer.
    """

    template = "website/standard_page.html"
    parent_page_types = ["researchit_website.HomePage"]
    subpage_types: list[str] = []

    body = RichTextField(features=BODY_FEATURES, blank=True)

    content_panels = [*Page.content_panels, FieldPanel("body")]

    class Meta:
        verbose_name = "Standard page"
