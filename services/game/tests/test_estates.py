"""Estate endpoint integration tests."""

import asyncio
import base64
import json
import logging
import os
import threading
import uuid
from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request
from httpx import ASGITransport, AsyncClient
from jwt import PyJWK
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.estates import purchase_upgrade
from app.auth import jwks_cache
from app.clock import utc_now
from app.content.schemas import CapBonus, CapType, FormTransformation, ItemQuantity
from app.db import Base, configure_sqlite_engine, get_db
from app.main import app
from app.models import Character, Estate, EstateUpgrade, Inventory, Player

pytestmark = pytest.mark.anyio
_KEY_ID = "estate-test-key"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def anyio_backend() -> str:
    """Run API tests on asyncio."""
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


def _token() -> str:
    return jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iss": "yaisg-auth",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        _PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": _KEY_ID},
    )


@pytest.fixture
async def estate_client(
    tmp_path: Path,
) -> AsyncGenerator[
    tuple[AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]],
    None,
]:
    """Create a character against either CI engine and freeze route time."""
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url:
        engine = create_engine(database_url)
    else:
        engine = create_engine(
            f"sqlite:///{tmp_path / 'estates.db'}",
            connect_args={"check_same_thread": False, "timeout": 10},
        )
        configure_sqlite_engine(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    async def test_db() -> AsyncGenerator[Session, None]:
        with factory() as session:
            yield session

    clock = {"now": datetime(2026, 1, 1, tzinfo=UTC)}

    async def frozen_now() -> datetime:
        return clock["now"]

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[utc_now] = frozen_now
    original_key = jwks_cache.get_key
    original_content = app.state.content
    jwks_cache.get_key = AsyncMock(return_value=_public_jwk())  # type: ignore[method-assign]
    headers = {"Authorization": f"Bearer {_token()}"}
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/characters",
                headers=headers,
                json={"name": "Estate Hero", "realm_id": "realm.verdant_vale"},
            )
            assert created.status_code == 201
            yield client, factory, headers, clock
    finally:
        app.state.content = original_content
        jwks_cache.get_key = original_key  # type: ignore[method-assign]
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _character_id(factory: sessionmaker[Session]) -> uuid.UUID:
    with factory() as session:
        value = session.scalar(select(Character.id))
        assert value is not None
        return value


def _give(factory: sessionmaker[Session], item_id: str, quantity: int) -> uuid.UUID:
    character_id = _character_id(factory)
    with factory() as session:
        session.add(
            Inventory(character_id=character_id, item_id=item_id, quantity=quantity)
        )
        session.commit()
    return character_id


async def test_estate_payload_and_inert_annotation(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    client, factory, headers, _ = estate_client
    content = app.state.content
    painted = content.upgrade("upgrade.painted_sign")
    app.state.content = content.with_overrides(
        upgrades=(painted.model_copy(update={"realm_tags": ("ashen",)}),)
    )
    with factory() as session:
        estate_id = session.scalar(select(Estate.id))
        assert estate_id is not None
        session.add(
            EstateUpgrade(
                estate_id=estate_id,
                slot_index=0,
                upgrade_id=painted.id,
                purchased_at=datetime.now(UTC),
            )
        )
        session.commit()

    response = await client.get("/estates/me", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["form"]["id"] == "form.camp"
    assert payload["form"]["name"] == "Camp"
    assert payload["realm_id"] == "realm.verdant_vale"
    assert payload["status"] == "active"
    assert payload["upgrade_slots"] == 4
    assert payload["relocating_to_realm_id"] is None
    assert payload["relocation_completes_at"] is None
    assert payload["installed_upgrades"] == [
        {
            "slot_index": 0,
            "upgrade_id": painted.id,
            "name": painted.name,
            "status": "inert",
            "inert_reason": "realm requirements not met",
        }
    ]


async def test_upgrade_changes_subsequent_action_resolution(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, factory, headers, clock = estate_client
    caplog.set_level(logging.INFO, logger="yaisg.audit")
    character_id = _give(factory, "item.demo_crate", 5)
    with factory() as session:
        session.add(
            Inventory(
                character_id=character_id,
                item_id="item.fake_plank",
                quantity=2,
            )
        )
        session.commit()

    purchased = await client.post(
        "/estates/me/upgrades/upgrade.painted_sign", headers=headers
    )
    started = await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "crafting.demo_crate"},
    )
    clock["now"] += timedelta(seconds=6)
    resolved = await client.get("/characters/me/action", headers=headers)

    assert purchased.status_code == 200
    assert purchased.json()["installed_upgrades"][0]["slot_index"] == 0
    assert started.status_code == 200
    assert resolved.json()["since_last"]["xp_gained"] == {"crafting": 29}
    audit = next(
        json.loads(record.message)
        for record in caplog.records
        if record.name == "yaisg.audit"
    )
    assert audit["event"] == "estate_changed"
    assert audit["change"] == "upgrade_installed"
    assert audit["character_id"] == str(character_id)
    assert audit["upgrade_id"] == "upgrade.painted_sign"
    assert audit["estate_id"] == purchased.json()["id"]
    with factory() as session:
        output = session.get(Inventory, (character_id, "item.demo_crate"))
        assert output is not None and output.quantity == 1


@pytest.mark.parametrize(
    ("upgrade_id", "setup", "code"),
    [
        ("upgrade.missing", "none", "UNKNOWN_UPGRADE"),
        ("upgrade.painted_sign", "none", "MISSING_INPUTS"),
        ("upgrade.painted_sign", "duplicate", "ALREADY_INSTALLED"),
        ("upgrade.painted_sign", "full", "NO_FREE_SLOT"),
        ("upgrade.painted_sign", "duplicate_full", "ALREADY_INSTALLED"),
    ],
)
async def test_upgrade_errors(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    upgrade_id: str,
    setup: str,
    code: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, factory, headers, _ = estate_client
    caplog.set_level(logging.INFO, logger="yaisg.audit")
    if setup != "none":
        with factory() as session:
            estate_id = session.scalar(select(Estate.id))
            assert estate_id is not None
            if setup == "duplicate":
                session.add(
                    EstateUpgrade(
                        estate_id=estate_id,
                        slot_index=0,
                        upgrade_id="upgrade.painted_sign",
                        purchased_at=datetime.now(UTC),
                    )
                )
            else:
                session.add_all(
                    [
                        EstateUpgrade(
                            estate_id=estate_id,
                            slot_index=slot,
                            upgrade_id=(
                                "upgrade.painted_sign"
                                if setup == "duplicate_full" and slot == 0
                                else "upgrade.alarm_clock"
                            ),
                            purchased_at=datetime.now(UTC),
                        )
                        for slot in range(4)
                    ]
                )
            session.commit()

    response = await client.post(f"/estates/me/upgrades/{upgrade_id}", headers=headers)

    assert response.status_code in {404, 409}
    assert response.json()["error"]["code"] == code
    assert not [record for record in caplog.records if record.name == "yaisg.audit"]


async def test_last_slot_concurrency_installs_exactly_once(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    client, factory, headers, clock = estate_client
    character_id = _give(factory, "item.demo_crate", 5)
    with factory() as session:
        estate_id = session.scalar(select(Estate.id))
        assert estate_id is not None
        session.add_all(
            [
                EstateUpgrade(
                    estate_id=estate_id,
                    slot_index=slot,
                    upgrade_id="upgrade.alarm_clock",
                    purchased_at=datetime.now(UTC),
                )
                for slot in range(3)
            ]
            + [
                Inventory(
                    character_id=character_id,
                    item_id="item.prototype_widget",
                    quantity=3,
                ),
            ]
        )
        session.commit()

    if factory.kw["bind"].dialect.name == "sqlite":
        # ASGI's synchronous SQLite work cannot yield mid-handler, so this checks
        # the final-slot outcome but not real lock contention. The PostgreSQL CI
        # branch below drives two sessions concurrently through the handler.
        http_responses = await asyncio.gather(
            client.post("/estates/me/upgrades/upgrade.painted_sign", headers=headers),
            client.post("/estates/me/upgrades/upgrade.painted_sign", headers=headers),
        )
        responses = [
            (
                response.status_code,
                response.json().get("error", {}).get("code"),
            )
            for response in http_responses
        ]
    else:
        barrier = threading.Barrier(2)

        def purchase_once() -> tuple[int, str | None]:
            with factory() as session:
                player = session.scalar(select(Player))
                assert player is not None
                request = Request({"type": "http", "app": app})
                barrier.wait()
                try:
                    asyncio.run(
                        purchase_upgrade(
                            "upgrade.painted_sign",
                            request,
                            clock["now"],
                            player,
                            session,
                        )
                    )
                except HTTPException as error:
                    assert isinstance(error.detail, dict)
                    return error.status_code, error.detail["error"]["code"]
                return 200, None

        responses = list(
            await asyncio.gather(
                asyncio.to_thread(purchase_once),
                asyncio.to_thread(purchase_once),
            )
        )

    assert sorted(status for status, _ in responses) == [200, 409]
    assert (
        next(code for status, code in responses if status == 409) == "ALREADY_INSTALLED"
    )
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(EstateUpgrade)) == 4


async def test_transform_consumes_cost_without_changing_other_estate_state(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, factory, headers, _ = estate_client
    caplog.set_level(logging.INFO, logger="yaisg.audit")
    character_id = _give(factory, "item.fake_plank", 7)
    with factory() as session:
        estate = session.scalar(select(Estate))
        assert estate is not None
        estate.level = 3
        session.add(
            EstateUpgrade(
                estate_id=estate.id,
                slot_index=1,
                upgrade_id="upgrade.alarm_clock",
                purchased_at=datetime.now(UTC),
            )
        )
        session.commit()

    response = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": "form.homestead"}
    )

    assert response.status_code == 200
    assert response.json()["form"]["id"] == "form.homestead"
    assert response.json()["level"] == 3
    assert response.json()["installed_upgrades"][0]["slot_index"] == 1
    audit = next(
        json.loads(record.message)
        for record in caplog.records
        if record.name == "yaisg.audit"
    )
    assert audit["change"] == "form_transformed"
    assert audit["character_id"] == str(character_id)
    assert audit["estate_id"] == response.json()["id"]
    assert audit["from_form_id"] == "form.camp"
    assert audit["to_form_id"] == "form.homestead"
    with factory() as session:
        stack = session.get(Inventory, (character_id, "item.fake_plank"))
        estate = session.scalar(select(Estate))
        assert stack is not None and stack.quantity == 2
        assert estate is not None and estate.realm_id == "realm.verdant_vale"


async def test_transform_errors_and_shrinking_slots(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    client, factory, headers, _ = estate_client
    invalid = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": "form.orchard"}
    )
    missing = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": "form.homestead"}
    )
    assert invalid.json()["error"]["code"] == "INVALID_TRANSFORMATION"
    assert missing.json()["error"]["code"] == "MISSING_INPUTS"

    with factory() as session:
        estate = session.scalar(select(Estate))
        character_id = session.scalar(select(Character.id))
        assert estate is not None and character_id is not None
        estate.form_id = "form.homestead"
        session.add(
            Inventory(character_id=character_id, item_id="item.fake_plank", quantity=1)
        )
        for slot in range(5):
            session.add(
                EstateUpgrade(
                    estate_id=estate.id,
                    slot_index=slot,
                    upgrade_id="upgrade.painted_sign",
                    purchased_at=datetime.now(UTC),
                )
            )
        session.commit()
    content = app.state.content
    painted = content.upgrade("upgrade.painted_sign")
    content = content.with_overrides(
        upgrades=(
            painted.model_copy(
                update={
                    "cap_bonuses": (
                        CapBonus(cap=CapType.ESTATE_UPGRADE_SLOTS, value=10),
                    )
                }
            ),
        )
    )
    app.state.content = replace(
        content,
        transformations=(
            *content.transformations,
            FormTransformation.model_validate(
                {
                    "from": "form.homestead",
                    "to": "form.camp",
                    "cost": [ItemQuantity(item_id="item.fake_plank", qty=1)],
                }
            ),
        ),
    )
    shrinking = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": "form.camp"}
    )
    assert shrinking.json()["error"]["code"] == "WOULD_ORPHAN_UPGRADES"


async def test_transform_rejects_busy_estate_before_charging(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    client, factory, headers, _ = estate_client
    character_id = _give(factory, "item.fake_plank", 5)
    with factory() as session:
        estate = session.scalar(select(Estate))
        assert estate is not None
        estate.status = "relocating"
        session.commit()

    response = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": "form.homestead"}
    )

    assert response.json()["error"]["code"] == "ESTATE_BUSY"
    with factory() as session:
        stack = session.get(Inventory, (character_id, "item.fake_plank"))
        assert stack is not None and stack.quantity == 5
