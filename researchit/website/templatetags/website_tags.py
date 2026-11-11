from django import template
from wagtail.models import Page, Site

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
