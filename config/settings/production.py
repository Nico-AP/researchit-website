"""Production settings, as run by the `web` stack of researchit-deploy.

Environment variables (set by the deploy repo, stacks/web/app.env.j2):
DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS,
DATABASE_URL, EMAIL_URL, DEFAULT_FROM_EMAIL. Optional: UMAMI_SCRIPT_URL,
UMAMI_WEBSITE_ID, ADMINS, ADMIN_URL, WAGTAILADMIN_BASE_URL.
"""

from urllib.parse import urlsplit

import dj_email_url
from csp.constants import NONE, SELF

from .base import *  # noqa: F403
from .base import (
    MIDDLEWARE,
    UMAMI_SCRIPT_URL,
    UMAMI_WEBSITE_ID,
    WAGTAILADMIN_URL,
    env,
)

# Database
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Postgres runs next to the app on an internal Docker network (no TLS needed).

DATABASES = {
    "default": env.dj_db_url("DATABASE_URL", conn_max_age=60, conn_health_checks=True),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True


# Static files (served by whitenoise; collected at image build time)
# ------------------------------------------------------------------------------

MIDDLEWARE = [
    *MIDDLEWARE[:2],  # health check + SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[2:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# Security
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/5.2/topics/security/
# https://owasp.org/Top10/2025/
# TLS terminates at Caddy, which sets X-Forwarded-Proto.

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_AGE = 86400  # 1 day
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = 31536000  # = 1 year
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"  # matches CSP frame-ancestors 'none'
# (Wagtail's live-preview views override this with SAMEORIGIN for their iframe.)

# django-axes: the client IP comes from the X-Forwarded-For entry Caddy appended.
AXES_CLIENT_IP_CALLABLE = "researchit.core.client_ip.get_client_ip"

# django-csp - https://django-csp.readthedocs.io/en/latest/configuration.html

_analytics = []
if UMAMI_SCRIPT_URL and UMAMI_WEBSITE_ID:
    _parts = urlsplit(UMAMI_SCRIPT_URL)
    _analytics = [f"{_parts.scheme}://{_parts.netloc}"]

CONTENT_SECURITY_POLICY = {
    # The Wagtail admin relies on inline scripts/styles, so the strict policy
    # is not applied there. It is login-protected; public pages keep the CSP.
    "EXCLUDE_URL_PREFIXES": [f"/{WAGTAILADMIN_URL}"],
    "DIRECTIVES": {
        "default-src": [NONE],
        "script-src": [SELF, *_analytics],
        "style-src": [SELF],
        "img-src": [SELF],
        "media-src": [SELF],
        "font-src": [SELF],
        "connect-src": [SELF, *_analytics],
        "frame-ancestors": [NONE],
        "base-uri": [NONE],
        "form-action": [SELF],
    },
}


# Email
# ------------------------------------------------------------------------------
# EMAIL_URL, e.g. smtp://user:password@smtp.example.com:587 (the same DSN Kimai
# uses). Empty -> mails are only logged to stdout.

_email = dj_email_url.parse(env.str("EMAIL_URL", default="") or "console://")
EMAIL_BACKEND = _email["EMAIL_BACKEND"]
EMAIL_HOST = _email["EMAIL_HOST"]
EMAIL_PORT = _email["EMAIL_PORT"]
EMAIL_HOST_USER = _email["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = _email["EMAIL_HOST_PASSWORD"]
EMAIL_USE_SSL = _email["EMAIL_USE_SSL"] or EMAIL_PORT == 465  # noqa: PLR2004
# Port 587 is submission with STARTTLS (Symfony-style smtp:// DSNs imply it).
EMAIL_USE_TLS = (_email["EMAIL_USE_TLS"] or EMAIL_PORT == 587) and not EMAIL_USE_SSL  # noqa: PLR2004

# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env.str(
    "DEFAULT_FROM_EMAIL",
    default="contact <noreply@example.com>",
)

# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env.str("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env.str(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="",
)
