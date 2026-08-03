"""Authentication service application."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.config import CORS_ORIGINS, VERSION
from app.logging import log_request

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="YAISG Auth")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.middleware("http")(log_request)
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, error: HTTPException
) -> JSONResponse:
    """Render intentional errors without FastAPI's additional detail wrapper."""
    del request
    if isinstance(error.detail, dict) and "error" in error.detail:
        content = error.detail
    else:
        content = {"error": {"code": "HTTP_ERROR", "message": str(error.detail)}}
    return JSONResponse(status_code=error.status_code, content=content)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Render request validation failures in the standard error envelope."""
    del request, error
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "INVALID_REQUEST", "message": "Request is invalid"}},
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Report service health and build version."""
    return {"status": "ok", "service": "auth", "version": VERSION}
