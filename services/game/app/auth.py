"""Bearer-token verification and player provisioning dependencies."""

import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, Request
from jwt import InvalidTokenError, PyJWK
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import ServerNow
from app.config import AUTH_JWKS_TTL_SECONDS, AUTH_JWKS_URL, JWT_ISSUER
from app.db import get_db
from app.errors import api_error
from app.guest_settings import GuestSettings
from app.models import Player
from app.services.realms import as_utc, prepare_sqlite_write


@dataclass(frozen=True)
class VerifiedIdentity:
    """Trusted identity extracted from a verified access token."""

    auth_user_id: uuid.UUID
    kind: str = "full"


class JwksCache:
    """Fetch and TTL-cache public signing keys from the auth service."""

    def __init__(
        self,
        url: str,
        ttl_seconds: int,
        *,
        unknown_kid_refresh_floor_seconds: float = 5.0,
        unknown_kid_ttl_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._url = url
        self._ttl_seconds = ttl_seconds
        self._unknown_kid_refresh_floor_seconds = unknown_kid_refresh_floor_seconds
        self._unknown_kid_ttl_seconds = unknown_kid_ttl_seconds
        self._client = client or httpx.AsyncClient(timeout=5.0)
        self._keys: dict[str, PyJWK] = {}
        self._unknown_kids: dict[str, float] = {}
        self._expires_at = 0.0
        self._last_refresh_at = 0.0
        self._lock = asyncio.Lock()

    async def get_key(self, key_id: str) -> PyJWK:
        """Return a key, refreshing expired data and once for an unknown id."""
        now = time.monotonic()
        if now >= self._expires_at:
            await self._refresh_if_expired()
        key = self._keys.get(key_id)
        if key is None and now >= self._unknown_kids.get(key_id, 0.0):
            await self._refresh_for_unknown_kid()
            key = self._keys.get(key_id)
        if key is None:
            self._prune_unknown_kids()
            self._unknown_kids[key_id] = (
                time.monotonic() + self._unknown_kid_ttl_seconds
            )
            raise InvalidTokenError("Token signing key is unknown")
        return key

    async def _refresh_if_expired(self) -> None:
        async with self._lock:
            if time.monotonic() < self._expires_at:
                return
            await self._refresh()

    async def _refresh_for_unknown_kid(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_refresh_at
            if elapsed < self._unknown_kid_refresh_floor_seconds:
                return
            await self._refresh()

    async def _refresh(self) -> None:
        """Replace cached keys; callers serialize and throttle refresh attempts."""
        attempt_at = time.monotonic()
        self._last_refresh_at = attempt_at
        try:
            response = await self._client.get(self._url)
            response.raise_for_status()
            payload = response.json()
            keys = payload.get("keys") if isinstance(payload, dict) else None
            if not isinstance(keys, list):
                raise ValueError("JWKS response does not contain a keys list")
            parsed = [PyJWK.from_dict(value) for value in keys]
            self._keys = {key.key_id: key for key in parsed if key.key_id}
            now = time.monotonic()
            self._expires_at = now + self._ttl_seconds
            self._unknown_kids.clear()
        except (httpx.HTTPError, ValueError, TypeError) as error:
            # Briefly back off both expiry and unknown-kid refresh attempts when
            # the auth service is unavailable or returns malformed data.
            self._expires_at = attempt_at + self._unknown_kid_refresh_floor_seconds
            raise InvalidTokenError("Unable to load token signing keys") from error

    def _prune_unknown_kids(self) -> None:
        """Bound the negative cache while discarding expired entries."""
        now = time.monotonic()
        self._unknown_kids = {
            key_id: expires_at
            for key_id, expires_at in self._unknown_kids.items()
            if expires_at > now
        }
        if len(self._unknown_kids) >= 1024:
            oldest_key = min(self._unknown_kids, key=self._unknown_kids.__getitem__)
            del self._unknown_kids[oldest_key]


jwks_cache = JwksCache(AUTH_JWKS_URL, AUTH_JWKS_TTL_SECONDS)


async def verify_access_token(request: Request) -> VerifiedIdentity:
    """Verify an RS256 bearer token and return its subject."""
    existing = getattr(request.state, "identity", None)
    if isinstance(existing, VerifiedIdentity):
        return existing
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token:
        raise api_error(401, "UNAUTHORIZED", "A valid access token is required")
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise InvalidTokenError("Invalid token header")
        key = await jwks_cache.get_key(header["kid"])
        claims: dict[str, Any] = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
            options={"require": ["sub", "exp", "iss"]},
        )
        subject = uuid.UUID(claims["sub"])
        kind = claims["kind"]
        if kind not in {"guest", "full"}:
            raise InvalidTokenError("Invalid account kind")
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise api_error(
            401, "UNAUTHORIZED", "A valid access token is required"
        ) from None
    return VerifiedIdentity(auth_user_id=subject, kind=kind)


Identity = Annotated[VerifiedIdentity, Depends(verify_access_token)]
DatabaseSession = Annotated[Session, Depends(get_db)]


def get_current_player(
    identity: Identity, session: DatabaseSession, now: ServerNow, request: Request
) -> Player:
    """Read identity first; write only for new, promoted or stale players."""
    statement = select(Player).where(Player.auth_user_id == identity.auth_user_id)
    player = session.scalar(statement)
    settings = request.app.state.content.auth
    if player is not None and not _needs_activity_write(
        player, identity, now, settings
    ):
        return player

    # End the read snapshot before acquiring SQLite writer intent, then reload
    # under the writer/row lock so concurrent provisioning and promotion are safe.
    prepare_sqlite_write(session)
    player = session.scalar(
        statement.with_for_update().execution_options(populate_existing=True)
    )
    if player is not None:
        if _needs_activity_write(player, identity, now, settings):
            _record_activity(player, identity, now)
        session.commit()
        return player
    player = Player(
        auth_user_id=identity.auth_user_id,
        created_at=now,
        kind=identity.kind,
        last_activity_at=now,
    )
    session.add(player)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            statement.with_for_update().execution_options(populate_existing=True)
        )
        if existing is None:
            raise
        if _needs_activity_write(existing, identity, now, settings):
            _record_activity(existing, identity, now)
        session.commit()
        return existing
    session.refresh(player)
    return player


def _needs_activity_write(
    player: Player, identity: VerifiedIdentity, now: datetime, settings: GuestSettings
) -> bool:
    return (player.kind == "guest" and identity.kind == "full") or (
        player.last_activity_at is None
        or now - as_utc(player.last_activity_at)
        >= timedelta(minutes=settings.activity_write_interval_minutes)
    )


def _record_activity(player: Player, identity: VerifiedIdentity, now: datetime) -> None:
    """Promote identity monotonically and stamp coarse activity."""
    if identity.kind == "full":
        player.kind = "full"
    player.last_activity_at = now


CurrentPlayer = Annotated[Player, Depends(get_current_player)]
