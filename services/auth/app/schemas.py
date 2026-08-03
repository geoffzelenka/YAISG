"""Request and response schemas for authentication routes."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

Password = Annotated[str, StringConstraints(max_length=1024)]


class Credentials(BaseModel):
    """Email and password credentials."""

    email: str
    password: Password


class AccessTokenResponse(BaseModel):
    """A short-lived bearer token response."""

    access_token: str
    expires_in: int
