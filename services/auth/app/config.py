"""Environment-backed configuration for the authentication service."""

import os
from pathlib import Path

DATABASE_URL = os.getenv("AUTH_DATABASE_URL", "sqlite:///./data/auth.db")
VERSION = os.getenv("GIT_SHA", "dev")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
AUTH_KEYS_DIR = Path(os.getenv("AUTH_KEYS_DIR", "./data/keys"))
ACCESS_TOKEN_SECONDS = 15 * 60
REFRESH_TOKEN_SECONDS = 30 * 24 * 60 * 60
JWT_ISSUER = "yaisg-auth"
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
TRUSTED_PROXY_IPS = frozenset(
    value.strip()
    for value in os.getenv("AUTH_TRUSTED_PROXY_IPS", "").split(",")
    if value.strip()
)
