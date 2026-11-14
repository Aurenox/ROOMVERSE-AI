"""Isolated browser-test server: never uses the user's database or Gemini key."""
from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE":"django.db.backends.sqlite3", "NAME":BASE_DIR / "e2e.sqlite3", "OPTIONS":{"timeout":30,"transaction_mode":"IMMEDIATE"}}}
GEMINI_API_KEY = ""
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1:3120"]
PUBLIC_ORIGIN = "http://127.0.0.1:3120"
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES":{"anon":"10000/min","user":"10000/min"}}
