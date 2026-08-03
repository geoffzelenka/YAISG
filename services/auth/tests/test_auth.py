"""Integration tests for account and token lifecycle behavior."""

import asyncio
import itertools
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import JWT_ISSUER, REFRESH_COOKIE_NAME
from app.db import Base, get_db
from app.main import app
from app.models import RefreshToken
from app.security import SigningKeys, provide_signing_keys

_client_ips = itertools.count(1)


@pytest.fixture
def signing_keys(tmp_path: Path) -> SigningKeys:
    """Create isolated signing keys without touching the repository data directory."""
    return SigningKeys(tmp_path / "keys")


@pytest.fixture
def session_factory(
    tmp_path: Path, signing_keys: SigningKeys
) -> Iterator[sessionmaker[Session]]:
    """Create an isolated auth database and override request sessions."""
    database_path = tmp_path / "auth-test.db"
    engine = create_engine(
        f"sqlite:///{database_path}", connect_args={"check_same_thread": False}
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    async def override_get_db() -> AsyncIterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async def override_signing_keys() -> SigningKeys:
        return signing_keys

    app.dependency_overrides[provide_signing_keys] = override_signing_keys
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
async def client(
    session_factory: sessionmaker[Session],
) -> AsyncIterator[AsyncClient]:
    """Provide a cookie-aware client with a unique rate-limit identity."""
    del session_factory
    ip = f"192.0.2.{next(_client_ips)}"
    transport = ASGITransport(app=app, client=(ip, 123))
    async with AsyncClient(transport=transport, base_url="http://test") as value:
        yield value


@pytest.fixture
def anyio_backend() -> str:
    """Run async integration tests with the installed asyncio backend."""
    return "asyncio"


async def _register(client: AsyncClient, email: str = "player@example.com") -> str:
    response = await client.post(
        "/auth/register", json={"email": email, "password": "long-enough-password"}
    )
    assert response.status_code == 201
    assert response.json()["expires_in"] == 900
    access_token = response.json()["access_token"]
    assert isinstance(access_token, str)
    return access_token


@pytest.mark.anyio
async def test_register_login_refresh_logout_happy_path(client: AsyncClient) -> None:
    """A user can complete the entire authentication lifecycle."""
    await _register(client)
    login = await client.post(
        "/auth/login",
        json={"email": "PLAYER@example.com", "password": "long-enough-password"},
    )
    assert login.status_code == 200
    assert login.cookies[REFRESH_COOKIE_NAME]
    refreshed = await client.post("/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    logout = await client.post("/auth/logout")
    assert logout.status_code == 204
    assert REFRESH_COOKIE_NAME not in client.cookies


@pytest.mark.anyio
async def test_duplicate_email_and_weak_password(client: AsyncClient) -> None:
    """Registration returns stable validation and conflict codes."""
    weak = await client.post(
        "/auth/register", json={"email": "weak@example.com", "password": "short"}
    )
    assert weak.status_code == 422
    assert weak.json()["error"]["code"] == "WEAK_PASSWORD"
    await _register(client)
    duplicate = await client.post(
        "/auth/register",
        json={"email": "PLAYER@example.com", "password": "another-long-password"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.anyio
async def test_wrong_password(client: AsyncClient) -> None:
    """Login does not accept an incorrect password."""
    await _register(client)
    response = await client.post(
        "/auth/login",
        json={"email": "player@example.com", "password": "incorrect-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    unknown = await client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "incorrect-password"},
    )
    malformed = await client.post(
        "/auth/login",
        json={"email": "not-an-email", "password": "incorrect-password"},
    )
    assert unknown.status_code == 401
    assert malformed.status_code == 401
    assert malformed.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.anyio
async def test_password_maximum_length_is_enforced(client: AsyncClient) -> None:
    """Oversized passwords are rejected before reaching Argon2."""
    response = await client.post(
        "/auth/register",
        json={"email": "large@example.com", "password": "x" * 1025},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.anyio
async def test_refresh_rotates_stored_token(
    client: AsyncClient, session_factory: sessionmaker[Session]
) -> None:
    """Refreshing revokes the old credential and stores a replacement."""
    await _register(client)
    old_token = client.cookies[REFRESH_COOKIE_NAME]
    response = await client.post("/auth/refresh")
    new_token = client.cookies[REFRESH_COOKIE_NAME]
    assert response.status_code == 200
    assert new_token != old_token
    with session_factory() as session:
        tokens = list(session.scalars(select(RefreshToken)))
    assert len(tokens) == 2
    assert sum(token.revoked_at is not None for token in tokens) == 1


@pytest.mark.anyio
async def test_refresh_reuse_revokes_all_user_tokens(client: AsyncClient) -> None:
    """Reusing a rotated credential invalidates every session for that user."""
    await _register(client)
    first_token = client.cookies[REFRESH_COOKIE_NAME]
    await client.post("/auth/refresh")
    second_token = client.cookies[REFRESH_COOKIE_NAME]
    await client.post(
        "/auth/login",
        json={"email": "player@example.com", "password": "long-enough-password"},
    )
    third_token = client.cookies[REFRESH_COOKIE_NAME]

    client.cookies.set(REFRESH_COOKIE_NAME, first_token)
    reuse = await client.post("/auth/refresh")
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

    for token in (second_token, third_token):
        client.cookies.set(REFRESH_COOKIE_NAME, token)
        response = await client.post("/auth/refresh")
        assert response.status_code == 401


@pytest.mark.anyio
async def test_expired_refresh_retry_does_not_revoke_other_tokens(
    client: AsyncClient, session_factory: sessionmaker[Session]
) -> None:
    """Retrying an expired credential does not trigger reuse handling."""
    await _register(client)
    expired_token = client.cookies[REFRESH_COOKIE_NAME]
    await client.post(
        "/auth/login",
        json={"email": "player@example.com", "password": "long-enough-password"},
    )
    active_token = client.cookies[REFRESH_COOKIE_NAME]
    with session_factory() as session:
        token_id = uuid.UUID(expired_token.split(".", maxsplit=1)[0])
        stored_token = session.get(RefreshToken, token_id)
        assert stored_token is not None
        stored_token.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    for _ in range(2):
        client.cookies.set(REFRESH_COOKIE_NAME, expired_token)
        response = await client.post("/auth/refresh")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "REFRESH_TOKEN_EXPIRED"

    client.cookies.set(REFRESH_COOKIE_NAME, active_token)
    assert (await client.post("/auth/refresh")).status_code == 200


@pytest.mark.anyio
async def test_concurrent_refresh_only_rotates_once(client: AsyncClient) -> None:
    """Atomic revocation prevents two rotations of one refresh credential."""
    await _register(client)
    token = client.cookies[REFRESH_COOKIE_NAME]
    transport = ASGITransport(app=app, client=("198.51.100.1", 123))
    async with (
        AsyncClient(transport=transport, base_url="http://test") as first,
        AsyncClient(transport=transport, base_url="http://test") as second,
    ):
        first.cookies.set(REFRESH_COOKIE_NAME, token)
        second.cookies.set(REFRESH_COOKIE_NAME, token)
        responses = await asyncio.gather(
            first.post("/auth/refresh"), second.post("/auth/refresh")
        )
    assert sorted(response.status_code for response in responses) == [200, 401]


@pytest.mark.anyio
async def test_jwks_validates_access_token_and_expiry(
    client: AsyncClient, signing_keys: SigningKeys
) -> None:
    """Published JWKS verifies issued claims and rejects an expired equivalent."""
    access_token = await _register(client)
    jwks_response = await client.get("/.well-known/jwks.json")
    jwk = jwks_response.json()["keys"][0]
    assert jwt.get_unverified_header(access_token)["kid"] == jwk["kid"]
    public_key = jwt.PyJWK.from_dict(jwk).key
    claims = jwt.decode(
        access_token,
        public_key,
        algorithms=["RS256"],
        issuer=JWT_ISSUER,
    )
    assert claims["iss"] == JWT_ISSUER
    assert claims["sub"]
    assert claims["exp"] - claims["iat"] == 900

    expired_claims = {
        **claims,
        "iat": datetime.now(UTC) - timedelta(minutes=16),
        "exp": datetime.now(UTC) - timedelta(minutes=1),
    }
    expired_token = jwt.encode(
        expired_claims, signing_keys.private_key, algorithm="RS256"
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(
            expired_token,
            public_key,
            algorithms=["RS256"],
            issuer=JWT_ISSUER,
        )


@pytest.mark.anyio
async def test_cors_allows_browser_credentials(client: AsyncClient) -> None:
    """Configured client origins can make credentialed browser requests."""
    response = await client.options(
        "/auth/refresh",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.anyio
async def test_rate_limiter_returns_standard_error(client: AsyncClient) -> None:
    """The sixth credential attempt from an IP is rate limited."""
    for attempt in range(6):
        response = await client.post(
            "/auth/login",
            json={"email": "absent@example.com", "password": "incorrect-password"},
        )
        if attempt < 5:
            assert response.status_code == 401
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
