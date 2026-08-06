"""Character API integration tests."""

import asyncio
import base64
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient, Response
from jwt import PyJWK
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import jwks_cache
from app.db import Base, get_db
from app.main import app
from app.models import (
    Character,
    CharacterSkill,
    Currency,
    Estate,
    EstateUpgrade,
    RealmState,
)

pytestmark = pytest.mark.anyio
_KEY_ID = "character-test-key"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def anyio_backend() -> str:
    """Run API tests on the application's asyncio runtime."""
    return "asyncio"


def _encode_int(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _public_jwk() -> PyJWK:
    numbers = _PRIVATE_KEY.public_key().public_numbers()
    return PyJWK.from_dict(
        {
            "kty": "RSA",
            "kid": _KEY_ID,
            "alg": "RS256",
            "use": "sig",
            "n": _encode_int(numbers.n),
            "e": _encode_int(numbers.e),
        }
    )


def _token(subject: uuid.UUID | None = None) -> str:
    return jwt.encode(
        {
            "sub": str(subject or uuid.uuid4()),
            "iss": "yaisg-auth",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        _PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": _KEY_ID},
    )


@pytest.fixture
async def client(
    tmp_path: Path,
) -> AsyncGenerator[tuple[AsyncClient, sessionmaker[Session]], None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'characters.db'}",
        connect_args={"check_same_thread": False},
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


async def _post(client: AsyncClient, token: str, name: str, realm: str) -> Response:
    return await client.post(
        "/characters",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": name, "realm_id": realm},
    )


async def test_creation_builds_complete_profile(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    response = await _post(client[0], _token(), "Demo Hero", "realm.verdant_vale")

    assert response.status_code == 201
    profile = response.json()
    assert profile["character"]["name"] == "Demo Hero"
    assert profile["gold"] == 100
    assert profile["realm"]["name"] == "Verdant Vale"
    assert profile["estate"]["upgrade_slots"] == 2
    assert profile["estate"]["installed_upgrades"] == []
    assert profile["caps"]["inventory_slots"] == {"base": 30.0, "effective": 30.0}
    assert profile["caps"]["estate_upgrade_slots"] == {
        "base": 2.0,
        "effective": 4.0,
    }
    assert all(
        skill["level"] == 1 and skill["xp_to_next"] == 100
        for skill in profile["skills"]
    )
    with client[1]() as session:
        assert session.scalar(select(func.count()).select_from(CharacterSkill)) == 4
        assert session.scalar(select(func.count()).select_from(Currency)) == 1
        assert session.scalar(select(func.count()).select_from(Estate)) == 1


async def test_profile_caps_include_installed_upgrade_bonus(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    """Profile cap exposure includes an active installed upgrade."""
    token = _token()
    created = await _post(client[0], token, "Upgraded Hero", "realm.verdant_vale")
    estate_id = uuid.UUID(created.json()["estate"]["id"])
    with client[1]() as session:
        session.add(
            EstateUpgrade(
                estate_id=estate_id,
                slot_index=0,
                upgrade_id="upgrade.alarm_clock",
                purchased_at=datetime.now(UTC),
            )
        )
        session.commit()

    response = await client[0].get(
        "/characters/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["caps"]["offline_hours"] == {
        "base": 12.0,
        "effective": 14.0,
    }


@pytest.mark.parametrize(
    ("name", "realm", "code"),
    [
        ("x", "realm.verdant_vale", "INVALID_NAME"),
        ("Bad_Name", "realm.verdant_vale", "INVALID_NAME"),
        ("   ", "realm.verdant_vale", "INVALID_NAME"),
        ("Valid Name", "realm.missing", "UNKNOWN_REALM"),
    ],
)
async def test_creation_validation_errors(
    client: tuple[AsyncClient, sessionmaker[Session]],
    name: str,
    realm: str,
    code: str,
) -> None:
    response = await _post(client[0], _token(), name, realm)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


async def test_name_is_trimmed_and_globally_unique_case_insensitively(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    first = await _post(client[0], _token(), "  Unique Hero  ", "realm.verdant_vale")
    second = await _post(client[0], _token(), "unique hero", "realm.ashen_reach")

    assert first.status_code == 201
    assert first.json()["character"]["name"] == "Unique Hero"
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "NAME_TAKEN"


async def test_one_character_rule(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    token = _token()
    first = await _post(client[0], token, "First Hero", "realm.verdant_vale")
    second = await _post(client[0], token, "Second Hero", "realm.ashen_reach")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CHARACTER_EXISTS"


async def test_concurrent_double_submit_creates_exactly_one_character(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    token = _token()
    responses = await asyncio.gather(
        _post(client[0], token, "Concurrent One", "realm.verdant_vale"),
        _post(client[0], token, "Concurrent Two", "realm.verdant_vale"),
    )

    assert sorted(response.status_code for response in responses) == [201, 409]
    conflict = next(response for response in responses if response.status_code == 409)
    assert conflict.json()["error"]["code"] == "CHARACTER_EXISTS"
    with client[1]() as session:
        assert session.scalar(select(func.count()).select_from(Character)) == 1


async def test_concurrent_first_characters_share_realm_initialization(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    """A realm-state initialization race does not become a name error."""
    responses = await asyncio.gather(
        _post(client[0], _token(), "Realm First", "realm.verdant_vale"),
        _post(client[0], _token(), "Realm Second", "realm.verdant_vale"),
    )

    assert [response.status_code for response in responses] == [201, 201]
    with client[1]() as session:
        assert session.scalar(select(func.count()).select_from(RealmState)) == 1
        assert session.scalar(select(func.count()).select_from(Character)) == 2


async def test_missing_character_and_empty_inventory(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}
    missing = await client[0].get("/characters/me", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NO_CHARACTER"

    created = await _post(client[0], token, "Inventory Hero", "realm.verdant_vale")
    inventory = await client[0].get("/characters/me/inventory", headers=headers)
    assert created.status_code == 201
    assert inventory.json() == {"items": []}


async def test_profile_xp_to_next_and_repairs_cached_level(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    token = _token()
    created = await _post(client[0], token, "Math Hero", "realm.verdant_vale")
    character_id = uuid.UUID(created.json()["character"]["id"])
    with client[1]() as session:
        skill = session.get(CharacterSkill, (character_id, "gathering"))
        assert skill is not None
        skill.xp = 100
        skill.level = 99
        session.commit()

    profile = await client[0].get(
        "/characters/me", headers={"Authorization": f"Bearer {token}"}
    )
    gathering = next(
        skill for skill in profile.json()["skills"] if skill["id"] == "gathering"
    )
    assert gathering["level"] == 2
    assert gathering["xp_into_level"] == 0
    assert gathering["xp_to_next"] == 112
    with client[1]() as session:
        repaired = session.get(CharacterSkill, (character_id, "gathering"))
        assert repaired is not None
        assert repaired.level == 2


async def test_profile_seeds_a_missing_content_skill_row(
    client: tuple[AsyncClient, sessionmaker[Session]],
) -> None:
    token = _token()
    created = await _post(client[0], token, "Backfill Hero", "realm.verdant_vale")
    character_id = uuid.UUID(created.json()["character"]["id"])
    with client[1]() as session:
        session.execute(
            delete(CharacterSkill).where(
                CharacterSkill.character_id == character_id,
                CharacterSkill.skill_id == "crafting",
            )
        )
        session.commit()

    profile = await client[0].get(
        "/characters/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert profile.status_code == 200
    crafting = next(
        skill for skill in profile.json()["skills"] if skill["id"] == "crafting"
    )
    assert crafting["level"] == 1
    assert crafting["xp"] == 0
    with client[1]() as session:
        assert session.get(CharacterSkill, (character_id, "crafting")) is not None
