"""Shared content contract for guest retention, loaded by each service locally."""

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class GuestSettings(BaseModel):
    """Auth-owned retention content; both databases use the same pack."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    guest_ttl_days: int = Field(gt=0)


def load_guest_settings() -> GuestSettings:
    """Load and validate the shared auth content pack."""
    configured = os.environ.get("CONTENT_DIR")
    directory = (
        Path(configured)
        if configured is not None
        else Path(__file__).resolve().parents[3] / "content"
    )
    return GuestSettings.model_validate_json((directory / "auth.json").read_bytes())
