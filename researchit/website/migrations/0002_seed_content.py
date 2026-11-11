"""Seed the CMS with the content the site had when it was still hardcoded.

Replaces Wagtail's default "Welcome" page with a HomePage at the same place in
the tree and points the default Site at it. Everything here can be edited in
the CMS afterwards; this only runs once, on a fresh database.
"""

from django.db import migrations

ABOUT_TEXT = (
    "<p>I'm Nico Pfiffner, PhD, a researcher and developer with expertise in "
    "participant-centered data collection methods.</p>"
    '<p>I created the <a href="https://github.com/uzh/ddm">Data Donation Module</a>, '
    "an open-source data donation collection tool, and wrote "
    '<a href="https://doi.org/10.5167/uzh-262837">my dissertation</a> on the opportunities, '
    "challenges, and applications of data donation for studying digital media use and other "
    'phenomena. <a href="https://scholar.google.com/citations?user=pr4z_hoAAAAJ&amp;hl=de">My research</a> '
    "is published in peer-reviewed journals.</p>"
    "<p>I work with universities and research teams to build reliable, ethical data collection "
    "infrastructure — bridging academic methodology and working software.</p>"
)

SERVICES = [
    (
        "Research Infrastructure Development",
        "Custom tools and pipelines for participant data collection — data donation systems, "
        "digital trace capture, survey integrations, and study platform development.",
    ),
    (
        "Research Consulting",
        "Study design, methodology guidance, and ethical data collection planning for academic "
        "and applied research.",
    ),
    (
        "Privacy-Centered Data Methods",
        "Designing data collection that puts participants first. Expertise in consent-driven "
        "flows, data minimization, and GDPR-compliant architectures.",
    ),
    (
        "Technical Implementation",
        "End-to-end development of data collection tools — from prototype to production-ready "
        "systems. Available for project-based or ongoing engagements.",
    ),
]

FACTS = [
    ("Registered as", "Pfiffner Research IT v/Nico Pfiffner"),
    ("CVR-nr", "45784924"),
    ("Location", "Denmark · Remote"),
    ("Languages", "English · German"),
]


def seed(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")
    Locale = apps.get_model("wagtailcore", "Locale")
    HomePage = apps.get_model("researchit_website", "HomePage")
    ServiceItem = apps.get_model("researchit_website", "ServiceItem")
    FactItem = apps.get_model("researchit_website", "FactItem")
    BusinessSettings = apps.get_model("researchit_website", "BusinessSettings")

    if HomePage.objects.exists():
        return

    # Wagtail's own initial migration creates a plain "Welcome" page at depth 2.
    # Remove it (this also removes the Site pointing at it) to free its tree slot.
    Page.objects.filter(depth=2, content_type__app_label="wagtailcore", content_type__model="page").delete()
    if Page.objects.filter(depth=2).exists():
        return  # someone already built a tree here; don't touch it

    root = Page.objects.get(depth=1)
    homepage_ct, _ = ContentType.objects.get_or_create(app_label="researchit_website", model="homepage")

    home = HomePage.objects.create(
        title="Home",
        draft_title="Home",
        seo_title="Pfiffner Research IT",
        search_description=(
            "Research infrastructure development and research consulting: data donation and "
            "digital trace data collection, from study design to technical implementation."
        ),
        slug="home",
        content_type=homepage_ct,
        locale=Locale.objects.order_by("pk").first(),
        path=f"{root.path}0001",
        depth=2,
        numchild=0,
        url_path="/home/",
        live=True,
        hero_tagline="Research Infrastructure Development & Research Consulting",
        hero_headline="Data collection systems\nbuilt on research expertise.",
        hero_text=(
            "Specialized in data donation and digital trace data collection — "
            "from study design to technical implementation."
        ),
        cta_label="Get in touch",
        about_text=ABOUT_TEXT,
        about_availability="Available for project-based engagements.",
        contact_text="Feel free to reach out if you'd like to discuss a project.",
    )
    root.numchild = 1
    root.save(update_fields=["numchild"])

    for i, (title, description) in enumerate(SERVICES):
        ServiceItem.objects.create(page=home, sort_order=i, title=title, description=description)
    for i, (label, value) in enumerate(FACTS):
        FactItem.objects.create(page=home, sort_order=i, label=label, value=value)

    # Hostname doesn't matter while it is the only (default) site.
    Site.objects.create(
        hostname="localhost", port=80, root_page=home, is_default_site=True, site_name="Pfiffner Research IT"
    )

    BusinessSettings.objects.get_or_create(
        defaults={
            "business_name": "Pfiffner Research IT",
            "contact_email": "nico@pfiffner-researchit.com",
            "github_url": "https://github.com/Nico-AP",
            "cvr_number": "45784924",
            "country": "Denmark",
        }
    )


class Migration(migrations.Migration):
    dependencies = [
        ("researchit_website", "0001_initial"),
        ("wagtailcore", "0098_apitoken"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
