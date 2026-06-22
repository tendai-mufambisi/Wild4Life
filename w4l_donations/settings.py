"""
Django settings for w4l_donations project.

All secrets and environment-specific values are read from environment variables
via django-environ. The application will refuse to start (ImproperlyConfigured)
if any required variable is absent.
"""

from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

# Read .env file if present (silently ignored when absent — real envs inject vars directly)
environ.Env.read_env(BASE_DIR / ".env")

# ─── Required variables — fail loud if missing ───────────────────────────────

def _require(name: str) -> str:
    """Raise ImproperlyConfigured with a clear message if an env var is missing."""
    value = env.str(name, default=None)
    if not value:
        raise ImproperlyConfigured(
            f"Required environment variable '{name}' is not set. "
            f"Copy .env.example to .env and fill in all values before starting."
        )
    return value


SECRET_KEY = _require("SECRET_KEY")

PAYNOW_INTEGRATION_ID  = _require("PAYNOW_INTEGRATION_ID")
PAYNOW_INTEGRATION_KEY = _require("PAYNOW_INTEGRATION_KEY")
PAYNOW_RETURN_URL      = _require("PAYNOW_RETURN_URL")
PAYNOW_RESULT_URL      = _require("PAYNOW_RESULT_URL")
SITE_BASE_URL          = _require("SITE_BASE_URL")

# ─── Optional with sane defaults ─────────────────────────────────────────────

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

CSRF_TRUSTED_ORIGINS: list[str] = env.list("CSRF_TRUSTED_ORIGINS", default=[SITE_BASE_URL])

DEFAULT_CURRENCY = env.str("DEFAULT_CURRENCY", default="USD")
if DEFAULT_CURRENCY not in ("USD", "ZWG"):
    raise ImproperlyConfigured(
        f"DEFAULT_CURRENCY must be 'USD' or 'ZWG', got '{DEFAULT_CURRENCY}'."
    )

# ─── Database ─────────────────────────────────────────────────────────────────

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}
# Tells Django the MySQL server's clock is in Africa/Harare, so it skips
# CONVERT_TZ() calls that require timezone tables (unavailable on shared hosting).
DATABASES["default"]["TIME_ZONE"] = "Africa/Harare"

# ─── Application definition ──────────────────────────────────────────────────

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "donations",
]

MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "w4l_donations.urls"

_context_processors = [
    "django.template.context_processors.debug",
    "django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
    "donations.context_processors.site_settings",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": DEBUG,
        "OPTIONS": {
            "context_processors": _context_processors,
            **({} if DEBUG else {
                "loaders": [
                    ("django.template.loaders.cached.Loader", [
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                    ])
                ]
            }),
        },
    },
]

# ─── Caching ──────────────────────────────────────────────────────────────────

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

WSGI_APPLICATION = "w4l_donations.wsgi.application"

# ─── Auth password validators ─────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internationalisation ─────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Harare"
USE_I18N = True
USE_TZ = True

# ─── Static files ─────────────────────────────────────────────────────────────

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Email ────────────────────────────────────────────────────────────────────

if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST          = env.str("EMAIL_HOST", default="localhost")
    EMAIL_PORT          = env.int("EMAIL_PORT", default=587)
    EMAIL_USE_TLS       = env.bool("EMAIL_USE_TLS", default=True)
    EMAIL_HOST_USER     = env.str("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")

DEFAULT_FROM_EMAIL = env.str(
    "DEFAULT_FROM_EMAIL",
    default="Wild4Life Donations <donations@wild4life.org.zw>",
)

# ─── Logging ──────────────────────────────────────────────────────────────────

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "donations": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# ─── Security (production hardening) ─────────────────────────────────────────

if not DEBUG:
    SECURE_SSL_REDIRECT            = True
    SECURE_HSTS_SECONDS            = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
