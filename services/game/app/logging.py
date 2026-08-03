"""Structured request logging middleware."""

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

LOGGER = logging.getLogger("yaisg.requests")


async def log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Log request metadata and return a correlation identifier."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    status_code = 500
    exception_type: str | None = None
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as error:
        # Returning the standard public 500 response here lets us attach the request ID.
        exception_type = type(error).__name__
        response = JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal Server Error",
                }
            },
        )

    response.headers["X-Request-Id"] = request_id
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    log_record: dict[str, str | int | float] = {
        "duration_ms": duration_ms,
        "method": request.method,
        "path": request.url.path,
        "request_id": request_id,
        "status": status_code,
    }
    if exception_type is not None:
        log_record["exception_type"] = exception_type
    LOGGER.info(json.dumps(log_record))
    return response
