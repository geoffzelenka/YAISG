"""Environment-backed configuration for the game service."""

import os

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
