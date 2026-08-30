"""Django settings for the Medical Handover Quality Agent API.

The backend reuses the existing engine package at <repo>/src/medical_handover
as an analysis service. No engine code is copied; the repo `src` directory is
added to ``sys.path`` here so Django can import it directly.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Python path: allow Django to import the existing engine package.
# settings.py lives at <repo>/backend/config/settings.py.
#   parents[0] = config, parents[1] = backend, parents[2] = <repo>
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Optional local environment file (gitignored, holds GEMINI_API_KEY /
# MH_EMITTER_BACKEND / MH_EMITTER_MODEL). Loaded with setdefault so the backend
# starts fine without it (defaults to the offline mock emitter). Credentials are
# never hardcoded and never exposed here.
_ENV_PATH = REPO_ROOT / ".env"
if _ENV_PATH.is_file():
    for _line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _value = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _value.strip())
    del _line, _key, _value

BASE_DIR = BACKEND_ROOT

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "rest_framework",
    "handovers",
]

MIDDLEWARE = ["config.middleware.DemoCORSMiddleware"]

ROOT_URLCONF = "config.urls"

TEMPLATES = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

# ---------------------------------------------------------------------------
# Database: production uses the Supabase Postgres URI from DATABASE_URL; local
# development and the test suite keep the zero-dependency SQLite file when the
# variable is absent. The engine/models make no SQLite-specific assumptions, so
# nothing else needs to differ between the two backends.
# ---------------------------------------------------------------------------
import dj_database_url  # noqa: E402

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
    )
}
# psycopg + managed/pooled connections (Supabase): never use server-side
# cursors so each request commits cleanly. Harmless for the local SQLite default.
DISABLE_SERVER_SIDE_CURSORS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    # No authentication in this milestone: requests carry no identity. Set the
    # unauthenticated user to None so DRF does not reach for django.contrib.auth.
    "UNAUTHENTICATED_USER": None,
    "UNAUTHENTICATED_TOKEN": None,
}

# Analysis emitter backend. Mirrors medical_handover.llm.get_client():
#   MH_EMITTER_BACKEND=mock    -> deterministic MockClient (default, offline)
#   MH_EMITTER_BACKEND=gemini  -> real GeminiClient (needs GEMINI_API_KEY)
EMITTER_BACKEND = os.environ.get("MH_EMITTER_BACKEND", "mock")