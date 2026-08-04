"""JWT verification and player auto-provisioning tests."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient, Response
from jwt import PyJWK
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import JwksCache, jwks_cache
from app.db import Base, get_db
from app.main import app
from app.models import Player

ISSUER = "yaisg-auth"
KEY_ID = "test-key"
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pytestmark = pytest.mark.anyio


def _public_jwk_data() -> dict[str, str]:
    numbers = PRIVATE_KEY.public_key().public_numbers()

    def encode(value: int) -> str:
        import base64

        raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return {
        "kty": "RSA",
        "kid": KEY_ID,
        "alg": "RS256",
        "use": "sig",
        "n": encode(numbers.n),
        "e": encode(numbers.e),
    }


def _public_jwk() -> PyJWK:
    return PyJWK.from_dict(_public_jwk_data())


def _token(
    *,
    expires_at: datetime | None = None,
    issuer: str = ISSUER,
    signing_key: rsa.RSAPrivateKey = PRIVATE_KEY,
) -> str:
    return jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iss": issuer,
            "exp": expires_at or datetime.now(UTC) + timedelta(minutes=5),
        },
        signing_key,
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )


@pytest.fixture
async def client() -> AsyncGenerator[tuple[AsyncClient, sessionmaker[Session]], None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    async def test_db() -> AsyncGenerator[Session, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    original = jwks_cache.get_key
    jwks_cache.get_key = AsyncMock(return_value=_public_jwk())  # type: ignore[method-assign]
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client, factory
    finally:
        jwks_cache.get_key = original  # type: ignore[method-assign]
        app.dependency_overrides.clear()
        engine.dispose()


async def _get_me(client: AsyncClient, token: str) -> Response:
    return await client.get("/players/me", headers={"Authorization": f"Bearer {token}"})


async def test_valid_token_returns_player(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    response = await _get_me(client[0], _token())

    assert response.status_code == 200
    assert response.json()["id"]


@pytest.mark.parametrize(
    "token",
    [
        _token(expires_at=datetime.now(UTC) - timedelta(seconds=1)),
        _token(issuer="wrong-issuer"),
        _token(signing_key=OTHER_PRIVATE_KEY),
    ],
    ids=["expired", "bad-issuer", "bad-signature"],
)
async def test_invalid_token_is_rejected(
    client: tuple[AsyncClient, sessionmaker[Session]], token: str
) -> None:
    response = await _get_me(client[0], token)

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHORIZED",
            "message": "A valid access token is required",
        }
    }


async def test_missing_authorization_is_rejected(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    response = await client[0].get("/players/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


async def test_authentication_401_includes_cors_headers(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    response = await client[0].get(
        "/players/me",
        headers={
            "Authorization": f"Bearer {_token(expires_at=datetime.now(UTC))}",
            "Origin": "http://localhost:5173",
        },
    )

    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_player_provisioning_is_idempotent(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    token = _token()

    first = await _get_me(client[0], token)
    second = await _get_me(client[0], token)

    assert first.json()["id"] == second.json()["id"]
    with client[1]() as session:
        assert session.scalar(select(func.count()).select_from(Player)) == 1


@pytest.fixture
def anyio_backend() -> str:
    """Run async cache tests on the service's asyncio runtime."""
    return "asyncio"


async def test_jwks_cache_hits_within_ttl() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"keys": [_public_jwk_data()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        cache = JwksCache("https://auth.test/jwks", 60, client=client)
        await cache.get_key(KEY_ID)
        await cache.get_key(KEY_ID)

    assert requests == 1


async def test_jwks_cache_refetches_after_ttl() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"keys": [_public_jwk_data()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        cache = JwksCache("https://auth.test/jwks", -1, client=client)
        await cache.get_key(KEY_ID)
        await cache.get_key(KEY_ID)

    assert requests == 2


async def test_jwks_cache_refetches_unknown_kid_once() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json={"keys": [_public_jwk_data()]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        cache = JwksCache(
            "https://auth.test/jwks",
            60,
            unknown_kid_refresh_floor_seconds=0,
            client=client,
        )
        await cache.get_key(KEY_ID)
        with pytest.raises(jwt.InvalidTokenError):
            await cache.get_key("unknown")
        with pytest.raises(jwt.InvalidTokenError):
            await cache.get_key("unknown")

    assert requests == 2


@pytest.mark.parametrize("response_status", [200, 503])
async def test_jwks_cache_maps_malformed_and_http_errors(
    response_status: int,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload: dict[str, list[object]] = (
            {"not_keys": []} if response_status == 200 else {}
        )
        return httpx.Response(response_status, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        cache = JwksCache("https://auth.test/jwks", 60, client=client)
        with pytest.raises(jwt.InvalidTokenError):
            await cache.get_key(KEY_ID)
