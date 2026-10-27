"""Environment-backed configuration for the game service."""

import os
from pathlib import Path

DATABASE_URL = os.getenv("GAME_DATABASE_URL", "sqlite:///./data/game.db")
VERSION = os.getenv("GIT_SHA", "dev")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
AUTH_JWKS_URL = os.getenv(
    "AUTH_JWKS_URL", "http://localhost:8001/.well-known/jwks.json"
)
AUTH_JWKS_TTL_SECONDS = int(os.getenv("AUTH_JWKS_TTL_SECONDS", "300"))
JWT_ISSUER = os.getenv("JWT_ISSUER", "yaisg-auth")
_CONTENT_DIR = os.getenv("CONTENT_DIR")
CONTENT_DIR = (
    Path(_CONTENT_DIR)
    if _CONTENT_DIR is not None
    else Path(__file__).resolve().parents[3] / "content"
)

OPERATOR_AUTH_USER_IDS = frozenset(
    value.strip()
    for value in os.getenv("GAME_OPERATOR_AUTH_USER_IDS", "").split(",")
    if value.strip()
)
