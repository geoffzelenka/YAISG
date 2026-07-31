"""Game service application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, VERSION
from app.logging import log_request

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="YAISG Game")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_request)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Report service health and build version."""
    return {"status": "ok", "service": "game", "version": VERSION}
