from __future__ import annotations

import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR.parent


def env_bool(name: str, default: bool) -> bool:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str]) -> list[str]:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default

    values = [item.strip() for item in raw_value.split(",")]
    return [item for item in values if item]


LOCAL_DB_DIR = Path(os.environ.get("LIQUID_PHOTOS_DATA_DIR", BASE_DIR / "Local_DB")).resolve()
LOCAL_DB_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_ROOT = LOCAL_DB_DIR / "media"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "liquid-photos-demo-secret-key")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["*"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "web.apps.WebConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "liquid_photos.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BACKEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "liquid_photos.wsgi.application"
ASGI_APPLICATION = "liquid_photos.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": LOCAL_DB_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Asia/Yekaterinburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "WebUI" / "frontend_build"]
STATIC_ROOT = BACKEND_DIR / "staticfiles"
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "liquid_photos.search": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
