"""Shared content contract for guest retention, loaded by each service locally."""

from pydantic import BaseModel, ConfigDict, Field


class GuestSettings(BaseModel):
    """Auth-owned retention content; both databases use the same pack."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    guest_ttl_days: int = Field(gt=0)
