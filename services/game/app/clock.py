"""Server clock dependency, isolated so API tests can freeze time."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends


async def utc_now() -> datetime:
    """Return the current timezone-aware server time."""
    return datetime.now(UTC)


ServerNow = Annotated[datetime, Depends(utc_now)]
