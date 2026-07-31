"""Environment-backed configuration for the authentication service."""

import os

DATABASE_URL = os.getenv("AUTH_DATABASE_URL", "sqlite:///./data/auth.db")
VERSION = os.getenv("GIT_SHA", "dev")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
