from pathlib import Path

from .base import *  # noqa: F403
from .base import BASE_DIR, DEBUG, INSTALLED_APPS, LOGGING, MIDDLEWARE, env

# Cache
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}


# Email
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)


# Logging
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging

# Locally, additionally write rotating JSON log files to BASE_DIR / "logs".

LOG_DIR = BASE_DIR / "logs"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)


def _file_handler(filename, level, max_mb, backups):
    return {
        "level": level,
        "class": "logging.handlers.RotatingFileHandler",
        "filename": LOG_DIR / filename,
        "maxBytes": 1024 * 1024 * max_mb,
        "backupCount": backups,
        "formatter": "json",
    }


LOGGING["handlers"].update(
    {
        "general": _file_handler("general.log", "INFO", 15, 5),
        "error_file": _file_handler("errors.log", "ERROR", 15, 5),
        "security_file": _file_handler("security.log", "WARNING", 10, 10),
    },
)
LOGGING["root"]["handlers"] += ["general", "error_file"]
LOGGING["loggers"]["django"]["handlers"] += ["general", "error_file"]
LOGGING["loggers"]["django.request"]["handlers"] += ["error_file"]
LOGGING["loggers"]["django.security"]["handlers"] += ["security_file"]


# django-debug-toolbar - https://github.com/django-commons/django-debug-toolbar
# ------------------------------------------------------------------------------
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    DEBUG_TOOLBAR_CONFIG = {
        "DISABLE_PANELS": [
            "debug_toolbar.panels.redirects.RedirectsPanel",
            # Disable profiling panel due to an issue with Python 3.12:
            # https://github.com/jazzband/django-debug-toolbar/issues/1875
            "debug_toolbar.panels.profiling.ProfilingPanel",
        ],
        "SHOW_TEMPLATE_CONTEXT": True,
    }
    INTERNAL_IPS = ["127.0.0.1"]
