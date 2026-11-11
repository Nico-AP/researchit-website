from django import template
from wagtail.models import Page, Site

from researchit.website import seo
from researchit.website.models import BusinessSettings
from researchit.website.seo import absolute_url

register = template.Library()


@register.simple_tag(takes_context=True)
def footer_pages(context):
    """Live pages directly below the site root with "Show in menus" ticked."""
    request = context.get("request")
    site = Site.find_for_request(request) if request else None
    if site is None:
        return Page.objects.none()
    return site.root_page.get_children().live().in_menu().public()


@register.simple_tag(takes_context=True)
def canonical_url(context):
    """Absolute URL of the current page without query string (?utm_... etc.)."""
    return absolute_url(context["request"], context.get("page"))


@register.simple_tag(takes_context=True)
def full_title(context):
    """Page title with the business name appended: "Impressum | Pfiffner Research IT".

    Uses the page's SEO title if set (Promote tab), else its title; the name is not
    appended twice if the title already contains it.
    """
    request = context.get("request")
    brand = BusinessSettings.load(request_or_site=request).business_name
    page = context.get("page")
    title = (page.seo_title or page.title) if page is not None else ""
    if not title or brand.lower() in title.lower():
        return title or brand
    return f"{title} | {brand}"


@register.simple_tag(takes_context=True)
def business_structured_data(context):
    """JSON-LD describing the business (home page only)."""
    request = context["request"]
    return seo.structured_data(
        request, context["page"], BusinessSettings.load(request_or_site=request)
    )
