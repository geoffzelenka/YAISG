"""Integration tests for account and token lifecycle behavior."""

import asyncio
import itertools
import os
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
    database_url = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{database_path}")
    engine = create_engine(
        database_url,
        **(
            {"connect_args": {"check_same_thread": False}}
            if database_url.startswith("sqlite:")
            else {}
        ),
    )
    Base.metadata.drop_all(engine)
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
    Base.metadata.drop_all(engine)
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


@pytest.mark.anyio
async def test_guest_claims_upgrade_identity_and_refresh(
    client: AsyncClient,
    signing_keys: SigningKeys,
) -> None:
    """Upgrade and the following refresh retain the guest id with full claims."""
    created = await client.post("/auth/guest")
    assert created.status_code == 201
    token = created.json()["access_token"]
    guest_claims = jwt.decode(
        token, signing_keys.public_key, algorithms=["RS256"], issuer=JWT_ISSUER
    )
    assert guest_claims["kind"] == "guest"
    upgraded = await client.post(
        "/auth/upgrade",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "Guest@example.com", "password": "long-enough-password"},
    )
    assert upgraded.status_code == 200
    refreshed = await client.post("/auth/refresh")
    claims = jwt.decode(
        refreshed.json()["access_token"],
        signing_keys.public_key,
        algorithms=["RS256"],
        issuer=JWT_ISSUER,
    )
    assert claims["kind"] == "full"
    assert claims["sub"] == guest_claims["sub"]
    logged_in = await client.post(
        "/auth/login",
        json={"email": "guest@example.com", "password": "long-enough-password"},
    )
    assert logged_in.status_code == 200


@pytest.mark.anyio
async def test_guest_upgrade_duplicate_email_and_validation(
    client: AsyncClient,
) -> None:
    """Existing credential rules apply and a conflict leaves the guest intact."""
    await _register(client)
    created = await client.post("/auth/guest")
    headers = {"Authorization": f"Bearer {created.json()['access_token']}"}
    for body, code in (
        ({"email": "new@example.com", "password": "short"}, "WEAK_PASSWORD"),
        ({"email": "bad", "password": "long-enough-password"}, "INVALID_EMAIL"),
        (
            {"email": "PLAYER@example.com", "password": "long-enough-password"},
            "EMAIL_TAKEN",
        ),
    ):
        response = await client.post("/auth/upgrade", headers=headers, json=body)
        assert response.json()["error"]["code"] == code
    refreshed = await client.post("/auth/refresh")
    assert (
        jwt.decode(
            refreshed.json()["access_token"], options={"verify_signature": False}
        )["kind"]
        == "guest"
    )


@pytest.mark.anyio
async def test_guest_creation_rate_limit(client: AsyncClient) -> None:
    """Guest creation uses the shared per-IP credential limiter."""
    for _ in range(5):
        assert (await client.post("/auth/guest")).status_code == 201
    response = await client.post("/auth/guest")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"


def test_auth_purge_only_inactive_guests(
    session_factory: sessionmaker[Session],
) -> None:
    """Full users and recent guests survive; sessions do not extend inactivity TTL."""
    from app.guest_purge import purge_guests
    from app.guest_settings import GuestSettings
    from app.models import User

    now = datetime(2026, 1, 1, tzinfo=UTC)
    old = now - timedelta(days=15)
    with session_factory() as session:
        users = [
            User(kind=kind, created_at=old, last_activity_at=activity, status="active")
            for kind, activity in (
                ("guest", old),
                ("guest", now),
                ("full", old),
                ("guest", old),
            )
        ]
        session.add_all(users)
        session.flush()
        session.add(
            RefreshToken(
                user_id=users[3].id,
                token_hash="live",
                expires_at=now + timedelta(days=1),
            )
        )
        session.commit()
        assert (
            purge_guests(
                session,
                GuestSettings(guest_ttl_days=14, activity_write_interval_minutes=60),
                now,
            )
            == 2
        )
        session.commit()
        assert session.get(User, users[0].id) is None
        assert session.get(User, users[3].id) is None
        assert all(session.get(User, user.id) is not None for user in users[1:3])
        assert (
            purge_guests(
                session,
                GuestSettings(guest_ttl_days=14, activity_write_interval_minutes=60),
                now,
            )
            == 0
        )


def test_postgres_auth_purge_rechecks_concurrent_activity(
    session_factory: sessionmaker[Session],
) -> None:
    """A waiting purge cannot delete a guest whose activity just committed."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import text

    from app.guest_purge import purge_guests
    from app.guest_settings import GuestSettings
    from app.models import User

    factory = session_factory
    with factory() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("Requires PostgreSQL row locks")
        now = datetime(2026, 1, 1, tzinfo=UTC)
        user = User(kind="guest", created_at=now - timedelta(days=15), status="active")
        session.add(user)
        session.commit()
        identifier = user.id
    started = Event()
    worker_pids: list[int] = []

    def purge() -> int:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            worker_pids.append(
                session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            started.set()
            count = purge_guests(
                session,
                GuestSettings(guest_ttl_days=14, activity_write_interval_minutes=60),
                now,
            )
            session.commit()
            return count

    with ThreadPoolExecutor(max_workers=1) as pool, factory() as blocker:
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        active_user = blocker.scalar(
            select(User).where(User.id == identifier).with_for_update()
        )
        assert active_user is not None
        future = pool.submit(purge)
        try:
            assert started.wait(timeout=5)
            deadline = time.monotonic() + 5
            with factory() as observer:
                while time.monotonic() < deadline:
                    blockers = observer.execute(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": worker_pids[0]}
                    ).scalar_one()
                    if blocker_pid in blockers:
                        break
                    time.sleep(0.01)
                else:
                    pytest.fail("Purge did not wait for the active user lock")
            active_user.last_activity_at = now
            blocker.commit()
        finally:
            blocker.rollback()
        assert future.result(timeout=10) == 0
    with factory() as session:
        assert session.get(User, identifier) is not None


def test_auth_purge_job_rolls_back_and_logs(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The daily auth job logs failures and rolls back its transaction."""
    from app import guest_purge
    from app.guest_settings import GuestSettings
    from app.models import User

    now = datetime(2026, 1, 1, tzinfo=UTC)
    with session_factory() as session:
        user = User(kind="guest", created_at=now - timedelta(days=15), status="active")
        session.add(user)
        session.commit()
        identifier = user.id

    def fail(session: Session, settings: GuestSettings, now: datetime) -> int:
        del settings, now
        user = session.get(User, identifier)
        assert user is not None
        session.delete(user)
        session.flush()
        raise RuntimeError("Injected auth purge failure")

    monkeypatch.setattr(guest_purge, "purge_guests", fail)
    guest_purge.run_guest_purge(
        session_factory,
        GuestSettings(guest_ttl_days=14, activity_write_interval_minutes=60),
        now,
    )
    assert "Auth guest purge failed" in caplog.text
    with session_factory() as session:
        assert session.get(User, identifier) is not None


def test_auth_guest_migration_schema_and_downgrade(tmp_path: Path) -> None:
    """The independent auth chain rebuilds and matches its mapped schema."""
    import subprocess
    import sys

    directory = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "AUTH_DATABASE_URL": f"sqlite:///{tmp_path / 'migration.db'}",
    }
    for arguments in (
        ("upgrade", "head"),
        ("check",),
        ("downgrade", "base"),
        ("upgrade", "head"),
    ):
        subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=directory,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )


@pytest.mark.anyio
async def test_auth_lifespan_purges_and_stops_worker(
    client: AsyncClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot runs cleanup and shutdown joins the daily worker without leaking it."""
    from threading import Event
    from threading import enumerate as threads

    from app import main
    from app.guest_purge import run_guest_purge
    from app.guest_settings import GuestSettings
    from app.models import User

    completed = Event()
    with session_factory() as session:
        user = User(
            kind="guest",
            created_at=datetime.now(UTC) - timedelta(days=15),
            status="active",
        )
        session.add(user)
        session.commit()
        identifier = user.id

    def observed(
        factory: sessionmaker[Session], settings: GuestSettings, now: datetime
    ) -> None:
        run_guest_purge(factory, settings, now)
        completed.set()

    monkeypatch.setattr(main, "SessionLocal", session_factory)
    monkeypatch.setattr(main, "run_guest_purge", observed)
    async with main.app.router.lifespan_context(main.app):
        assert completed.wait(timeout=5)
        with session_factory() as session:
            assert session.get(User, identifier) is None
        assert (await client.post("/auth/guest")).status_code == 201
    assert not any(thread.name == "auth_guest_purge" for thread in threads())


@pytest.mark.anyio
async def test_real_guest_purge_uses_inactivity_ttl(
    client: AsyncClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A newly issued guest survives TTL-1 and is removed at TTL+1."""
    from app import api
    from app.guest_purge import purge_guests
    from app.guest_settings import load_guest_settings
    from app.models import User
    from app.security import ensure_utc

    now = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(api, "utc_now", lambda: now)
    settings = load_guest_settings()
    response = await client.post("/auth/guest")
    assert response.status_code == 201
    claims = jwt.decode(
        response.json()["access_token"], options={"verify_signature": False}
    )
    identifier = uuid.UUID(claims["sub"])
    with session_factory() as session:
        token = session.scalar(
            select(RefreshToken).where(RefreshToken.user_id == identifier)
        )
        assert token is not None
        assert ensure_utc(token.expires_at) == now + timedelta(
            days=settings.guest_ttl_days
        )
        assert (
            f"Max-Age={settings.guest_ttl_days * 86400}"
            in response.headers["set-cookie"]
        )
        assert (
            purge_guests(
                session, settings, now + timedelta(days=settings.guest_ttl_days - 1)
            )
            == 0
        )
        session.commit()
        assert session.get(User, identifier) is not None
        assert (
            purge_guests(
                session, settings, now + timedelta(days=settings.guest_ttl_days + 1)
            )
            == 1
        )
        session.commit()
        assert session.get(User, identifier) is None
        assert (
            session.scalar(
                select(RefreshToken).where(RefreshToken.user_id == identifier)
            )
            is None
        )


@pytest.mark.anyio
async def test_guest_refresh_rotation_counts_as_activity_and_caps_expiry(
    client: AsyncClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rotation restarts the inactivity window and never grants a longer credential."""
    from app import api
    from app.guest_purge import purge_guests
    from app.guest_settings import load_guest_settings
    from app.models import User
    from app.security import ensure_utc

    clock = [datetime(2026, 1, 1, tzinfo=UTC)]
    monkeypatch.setattr(api, "utc_now", lambda: clock[0])
    settings = load_guest_settings()
    response = await client.post("/auth/guest")
    identifier = uuid.UUID(
        jwt.decode(
            response.json()["access_token"], options={"verify_signature": False}
        )["sub"]
    )
    clock[0] += timedelta(days=settings.guest_ttl_days - 1)
    assert (await client.post("/auth/refresh")).status_code == 200
    with session_factory() as session:
        user = session.get(User, identifier)
        assert user is not None and user.last_activity_at is not None
        assert ensure_utc(user.last_activity_at) == clock[0]
        live = session.scalar(
            select(RefreshToken).where(
                RefreshToken.user_id == identifier, RefreshToken.revoked_at.is_(None)
            )
        )
        assert live is not None
        assert ensure_utc(live.expires_at) == clock[0] + timedelta(
            days=settings.guest_ttl_days
        )
        session.rollback()
        assert purge_guests(session, settings, clock[0] + timedelta(days=2)) == 0


@pytest.mark.anyio
async def test_full_account_upgrade_cannot_replace_credentials(
    client: AsyncClient,
) -> None:
    """Even the owner's valid bearer cannot replace full-account credentials."""
    token = await _register(client)
    response = await client.post(
        "/auth/upgrade",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "replacement@example.com", "password": "replacement-password"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_ALREADY_FULL"
    assert (
        await client.post(
            "/auth/login",
            json={"email": "player@example.com", "password": "long-enough-password"},
        )
    ).status_code == 200
    assert (
        await client.post(
            "/auth/login",
            json={
                "email": "replacement@example.com",
                "password": "replacement-password",
            },
        )
    ).status_code == 401
    assert (
        await client.post(
            "/auth/login",
            json={"email": "player@example.com", "password": "replacement-password"},
        )
    ).status_code == 401


@pytest.mark.anyio
@pytest.mark.parametrize("invalid", ["missing", "non_bearer", "expired", "tampered"])
async def test_upgrade_rejects_invalid_bearer(
    client: AsyncClient,
    signing_keys: SigningKeys,
    invalid: str,
) -> None:
    """Upgrade requires a current, correctly signed bearer identity."""
    created = await client.post("/auth/guest")
    token = created.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if invalid == "missing":
        headers = {}
    elif invalid == "non_bearer":
        headers = {"Authorization": f"Basic {token}"}
    elif invalid == "expired":
        claims = jwt.decode(token, options={"verify_signature": False})
        claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
        token = jwt.encode(claims, signing_keys.private_key, algorithm="RS256")
        headers = {"Authorization": f"Bearer {token}"}
    else:
        parts = token.split(".")
        parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        headers = {"Authorization": f"Bearer {'.'.join(parts)}"}
    response = await client.post(
        "/auth/upgrade",
        headers=headers,
        json={"email": "upgrade@example.com", "password": "long-enough-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.anyio
async def test_upgrade_rate_limit(client: AsyncClient) -> None:
    """Upgrade attempts share the existing credential IP allowance."""
    for _ in range(5):
        response = await client.post(
            "/auth/upgrade",
            json={"email": "upgrade@example.com", "password": "long-enough-password"},
        )
        assert response.status_code == 401
    response = await client.post(
        "/auth/upgrade",
        json={"email": "upgrade@example.com", "password": "long-enough-password"},
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"


def test_auth_content_directory_error_is_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    """An image without the shared content mount fails clearly, without IndexError."""
    from app import guest_settings

    monkeypatch.delenv("CONTENT_DIR", raising=False)
    monkeypatch.setattr(guest_settings, "__file__", "/app/app/guest_settings.py")
    with pytest.raises(RuntimeError, match="Set CONTENT_DIR"):
        guest_settings.load_guest_settings()


def test_bad_auth_guest_does_not_block_another_purge(
    session_factory: sessionmaker[Session],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An individual deletion failure rolls back and leaves later guests eligible."""
    from sqlalchemy import event

    from app.guest_purge import purge_guests
    from app.guest_settings import load_guest_settings
    from app.models import User

    now = datetime(2026, 1, 1, tzinfo=UTC)
    with session_factory() as session:
        bad = User(
            id=uuid.UUID(int=1),
            kind="guest",
            created_at=now - timedelta(days=15),
            status="active",
        )
        good = User(
            id=uuid.UUID(int=2),
            kind="guest",
            created_at=now - timedelta(days=15),
            status="active",
        )
        session.add_all([bad, good])
        session.flush()
        session.add_all(
            [
                RefreshToken(
                    user_id=bad.id, token_hash="bad", expires_at=now + timedelta(days=1)
                ),
                RefreshToken(
                    user_id=good.id,
                    token_hash="good",
                    expires_at=now + timedelta(days=1),
                ),
            ]
        )
        session.commit()

        def reject_bad(
            session: Session, flush_context: object, instances: object
        ) -> None:
            if any(
                isinstance(row, User) and row.id == uuid.UUID(int=1)
                for row in session.deleted
            ):
                raise ValueError("Malformed auth guest")

        event.listen(session, "before_flush", reject_bad)
        try:
            assert purge_guests(session, load_guest_settings(), now) == 1
            session.commit()
        finally:
            event.remove(session, "before_flush", reject_bad)
        assert "Auth guest purge failed" in caplog.text
        assert session.get(User, uuid.UUID(int=1)) is not None
        assert session.get(User, uuid.UUID(int=2)) is None
        assert (
            session.scalar(
                select(RefreshToken).where(RefreshToken.user_id == uuid.UUID(int=1))
            )
            is not None
        )
        assert (
            session.scalar(
                select(RefreshToken).where(RefreshToken.user_id == uuid.UUID(int=2))
            )
            is None
        )


@pytest.mark.parametrize("interval", [0, -1, 841])
def test_auth_activity_interval_must_be_well_under_ttl(interval: int) -> None:
    """Both zero writes and an interval near retention are rejected by content."""
    from pydantic import ValidationError

    from app.guest_settings import GuestSettings

    with pytest.raises(ValidationError):
        GuestSettings(guest_ttl_days=14, activity_write_interval_minutes=interval)
