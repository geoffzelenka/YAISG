"""Shared content contract for guest retention, loaded by each service locally."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GuestSettings(BaseModel):
    """Auth-owned retention content; both databases use the same pack."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    guest_ttl_days: int = Field(gt=0)
    activity_write_interval_minutes: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_activity_interval(self) -> "GuestSettings":
        """Allow at least 24 activity write intervals within the retention TTL."""
        if self.activity_write_interval_minutes > self.guest_ttl_days * 60:
            raise ValueError(
                "activity_write_interval_minutes must be at most 1/24 of the guest TTL"
            )
        return self
