"""Health endpoint tests."""

import asyncio
import json
import logging

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest import LogCaptureFixture

from app.config import VERSION
from app.logging import log_request
from app.main import app

failure_app = FastAPI()
failure_app.middleware("http")(log_request)


@failure_app.get("/failure")
async def failure() -> None:
    """Raise an error to exercise the middleware exception path."""
    raise RuntimeError("expected test failure")


async def _get_health() -> tuple[int, dict[str, str], str]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
    return response.status_code, response.json(), response.headers["X-Request-Id"]


def test_healthz() -> None:
    """The auth service reports its identity and health."""
    status_code, body, request_id = asyncio.run(_get_health())

    assert status_code == 200
    assert body == {"status": "ok", "service": "auth", "version": VERSION}
    assert request_id


def test_exception_is_logged_with_request_id(caplog: LogCaptureFixture) -> None:
    """Unhandled exceptions retain their request ID in the response and log."""
    with caplog.at_level(logging.INFO, logger="yaisg.requests"):
        transport = ASGITransport(app=failure_app)

        async def get_failure() -> tuple[int, str, dict[str, object]]:
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/failure")
            return (
                response.status_code,
                response.headers["X-Request-Id"],
                response.json(),
            )

        status_code, request_id, body = asyncio.run(get_failure())

    log_record = json.loads(caplog.records[-1].message)
    assert status_code == 500
    assert log_record["status"] == 500
    assert log_record["request_id"] == request_id
    assert log_record["exception_type"] == "RuntimeError"
    assert body == {
        "error": {"code": "INTERNAL_ERROR", "message": "Internal Server Error"}
    }
