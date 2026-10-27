"""Game service application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.middleware.base import RequestResponseEndpoint

from app.api.actions import router as actions_router
from app.api.characters import router as characters_router
from app.api.content import PUBLIC_CONTENT_PATHS
from app.api.content import router as content_router
from app.api.estates import router as estates_router
from app.api.players import router as players_router
from app.api.realms import router as realms_router
from app.api.travel import router as travel_router
from app.auth import verify_access_token
from app.config import CORS_ORIGINS, VERSION
from app.content.runtime import CONTENT
from app.logging import log_request

logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Seed the world after migrations and before accepting requests."""
    from app.db import SessionLocal
    from app.services.world import create_world

    try:
        with SessionLocal.begin() as session:
            create_world(session, application.state.content, datetime.now(UTC))
    except DBAPIError as error:
        missing_table = getattr(error.orig, "sqlstate", None) == "42P01" or (
            isinstance(error, OperationalError) and "no such table:" in str(error.orig)
        )
        if missing_table:
            logging.getLogger(__name__).error(
                "Database not migrated; run alembic upgrade head / make db-reset"
            )
        raise
    from app.services.scheduler import start_scheduler

    scheduler = start_scheduler(SessionLocal, application.state.content)
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(title="YAISG Game", lifespan=lifespan)
app.state.content = CONTENT
app.middleware("http")(log_request)
app.include_router(content_router)
app.include_router(players_router)
app.include_router(characters_router)
app.include_router(estates_router)
app.include_router(actions_router)
app.include_router(realms_router)
app.include_router(travel_router)


@app.middleware("http")
async def require_authentication(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    """Require a verified identity for every route other than service health."""
    if (
        request.url.path == "/healthz"
        or request.url.path == "/map"
        or request.url.path in PUBLIC_CONTENT_PATHS
        or request.method == "OPTIONS"
    ):
        return await call_next(request)
    try:
        request.state.identity = await verify_access_token(request)
    except HTTPException as error:
        content = (
            error.detail
            if isinstance(error.detail, dict) and "error" in error.detail
            else {"error": {"code": "UNAUTHORIZED", "message": str(error.detail)}}
        )
        return JSONResponse(status_code=error.status_code, content=content)
    return await call_next(request)


# Starlette's last-added middleware is outermost. CORS must wrap authentication so
# browser clients can inspect short-circuited 401 responses and refresh tokens.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, error: HTTPException
) -> JSONResponse:
    """Render intentional failures in the standard error envelope."""
    del request
    content = (
        error.detail
        if isinstance(error.detail, dict) and "error" in error.detail
        else {"error": {"code": "HTTP_ERROR", "message": str(error.detail)}}
    )
    return JSONResponse(
        status_code=error.status_code,
        content=content,
        headers=error.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Render validation failures in the standard error envelope."""
    del request, error
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_REQUEST", "message": "Request is invalid"}},
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Report service health and build version."""
    return {"status": "ok", "service": "game", "version": VERSION}
