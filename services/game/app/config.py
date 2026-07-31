"""Environment-backed configuration for the game service."""

import os

DATABASE_URL = os.getenv("GAME_DATABASE_URL", "sqlite:///./data/game.db")
VERSION = os.getenv("GIT_SHA", "dev")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
