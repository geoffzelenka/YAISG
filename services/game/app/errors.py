"""Uniform API error responses."""

from fastapi import HTTPException


def api_error(
    status_code: int, code: str, message: str, *, extra: dict[str, int] | None = None
) -> HTTPException:
    """Build an HTTP error using the public error envelope."""
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, **(extra or {})}},
    )
