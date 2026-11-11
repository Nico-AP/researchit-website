from django.conf import settings


def analytics(request):
    """Expose the (optional) Umami configuration to templates."""
    enabled = bool(settings.UMAMI_SCRIPT_URL and settings.UMAMI_WEBSITE_ID)
    return {
        "umami_script_url": settings.UMAMI_SCRIPT_URL if enabled else "",
        "umami_website_id": settings.UMAMI_WEBSITE_ID if enabled else "",
    }
