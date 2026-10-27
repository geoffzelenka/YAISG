"""Estate endpoint integration tests."""

import asyncio
import base64
import json
import logging
import os
import threading
import time
import uuid
from collections.abc import AsyncGenerator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from unittest.mock import AsyncMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException, Request
from httpx import ASGITransport, AsyncClient
from jwt import PyJWK
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.estates import purchase_upgrade
from app.api.realms import get_realms
from app.auth import jwks_cache
from app.clock import utc_now
from app.content.schemas import (
    CapBonus,
    CapType,
    FormTransformation,
    ItemQuantity,
    MapCost,
    MapEdge,
)
from app.db import Base, configure_sqlite_engine, get_db
from app.main import app
from app.models import (
    Character,
    Currency,
    Estate,
    EstateUpgrade,
    Inventory,
    Player,
    RealmContribution,
    RealmEdgeProgress,
    RealmProject,
    RealmState,
)

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
            # Relocation tests need spendable funds independently of new-player grants.
            with factory() as session:
                currency = session.scalar(select(Currency))
                assert currency is not None
                currency.gold = 100
                session.commit()
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
        upgrades=(painted.model_copy(update={"requires_realm_tags": ("ashen",)}),)
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


async def test_relocation_preview_returns_terms_without_changing_state(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Preview uses the relocation cost function but performs no charge or move."""
    client, factory, headers, _ = estate_client

    response = await client.get(
        "/characters/me/relocate/preview",
        headers=headers,
        params={"realm_id": "realm.ashen_reach"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "realm_id": "realm.verdant_vale",
        "destination_realm_id": "realm.ashen_reach",
        "cost": {"gold": 25, "items": [], "time_ms": 60000},
    }
    with factory() as session:
        estate = session.scalar(select(Estate))
        currency = session.scalar(select(Currency))
        assert estate is not None and currency is not None
        assert estate.realm_id == "realm.verdant_vale"
        assert estate.status == "active"
        assert currency.gold == 100


async def test_relocation_preview_finalizes_due_arrival_before_pricing(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """A preview read observes a completed prior trip before computing its route."""
    client, factory, headers, clock = estate_client
    with factory() as session:
        estate = session.scalar(select(Estate))
        assert estate is not None
        estate.status = "relocating"
        estate.relocating_to_realm_id = "realm.ashen_reach"
        estate.relocation_completes_at = clock["now"]
        session.commit()

    response = await client.get(
        "/characters/me/relocate/preview",
        headers=headers,
        params={"realm_id": "realm.verdant_vale"},
    )

    assert response.status_code == 200
    assert response.json()["realm_id"] == "realm.ashen_reach"
    with factory() as session:
        estate = session.scalar(select(Estate))
        character = session.scalar(select(Character))
        assert estate is not None and character is not None
        assert estate.status == "active"
        assert estate.realm_id == "realm.ashen_reach"
        assert character.realm_id == "realm.ashen_reach"


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
        json={"action_id": "manufacturing.demo_crate"},
    )
    clock["now"] += timedelta(seconds=6)
    resolved = await client.get("/characters/me/action", headers=headers)

    assert purchased.status_code == 200
    assert purchased.json()["installed_upgrades"][0]["slot_index"] == 0
    assert started.status_code == 200
    assert resolved.json()["since_last"]["xp_gained"] == {"manufacturing": 29}
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
                    "cost": (ItemQuantity(item_id="item.fake_plank", qty=1),),
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


async def test_map_is_public_and_returns_content_graph(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Map topology is available without a bearer token."""
    client, _, _, _ = estate_client

    response = await client.get("/map")

    assert response.status_code == 200
    assert {node["realm_id"] for node in response.json()["nodes"]} == {
        "realm.verdant_vale",
        "realm.ashen_reach",
    }
    assert response.json()["edges"][0]["cost"]["gold"] == 25


async def test_contribution_clamps_consumes_and_completes_with_one_award(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Contributions conserve inputs and completion awards its edge once."""
    client, factory, headers, _ = estate_client
    content = app.state.content
    definition = content.project("project.verdant_cardboard")
    multi_award = definition.model_copy(
        update={"awards": (definition.awards[0], definition.awards[0])}
    )
    projects = tuple(
        multi_award if project.id == definition.id else project
        for project in content.projects
    )
    app.state.content = replace(
        content,
        projects=projects,
        _projects_by_id=MappingProxyType({project.id: project for project in projects}),
    )
    character_id = _give(factory, "item.demo_crate", 150)
    _give(factory, "item.cardboard_badge", 25)

    crates = await client.post(
        "/realms/realm.verdant_vale/projects/project.verdant_cardboard/contribute",
        headers=headers,
        json={"item_id": "item.demo_crate", "quantity": 150},
    )
    badges = await client.post(
        "/realms/realm.verdant_vale/projects/project.verdant_cardboard/contribute",
        headers=headers,
        json={"item_id": "item.cardboard_badge", "quantity": 25},
    )

    assert crates.status_code == 200
    assert crates.json()["accepted_quantity"] == 100
    assert badges.status_code == 200
    assert badges.json()["completed"] is True
    with factory() as session:
        crates_left = session.get(Inventory, (character_id, "item.demo_crate"))
        assert crates_left is not None and crates_left.quantity == 50
        assert session.get(Inventory, (character_id, "item.cardboard_badge")) is None
        contributions = list(session.scalars(select(RealmContribution)))
        assert sum(value.quantity for value in contributions) == 125
        project = session.get(
            RealmProject,
            ("realm.verdant_vale", "project.verdant_cardboard"),
        )
        assert project is not None and project.status == "completed"
        progress = session.get(
            RealmEdgeProgress,
            ("realm.verdant_vale", "edge.verdant_t1_t2"),
        )
        # The first award opened a transition, so the duplicate later award was
        # skipped rather than escaping as INVALID_EDGE_AWARD.
        assert progress is not None and progress.progress == 100


async def test_contribution_rejects_pending_transition_without_consuming(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Projects cannot complete or consume goods while their node is leaving."""
    client, factory, headers, clock = estate_client
    character_id = _give(factory, "item.demo_crate", 1)
    with factory() as session:
        state = session.get(RealmState, "realm.verdant_vale")
        assert state is not None
        state.transition_to_node_id = "node.verdant_t2"
        state.transition_completes_at = clock["now"] + timedelta(minutes=5)
        session.commit()

    response = await client.post(
        "/realms/realm.verdant_vale/projects/project.verdant_cardboard/contribute",
        headers=headers,
        json={"item_id": "item.demo_crate", "quantity": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REALM_TRANSITIONING"
    with factory() as session:
        stack = session.get(Inventory, (character_id, "item.demo_crate"))
        assert stack is not None and stack.quantity == 1
        assert session.scalar(select(func.count()).select_from(RealmContribution)) == 0


async def test_delayed_relocation_charges_and_arrives_lazily(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """A normal map move charges now but retains origin identity until arrival."""
    client, factory, headers, clock = estate_client
    character_id = _character_id(factory)

    moved = await client.post(
        "/characters/me/relocate",
        headers=headers,
        json={"realm_id": "realm.ashen_reach"},
    )

    assert moved.status_code == 200
    assert moved.json()["cost"] == {"gold": 25, "items": [], "time_ms": 60000}
    assert moved.json()["realm_id"] == "realm.verdant_vale"
    assert moved.json()["relocating_to_realm_id"] == "realm.ashen_reach"
    with factory() as session:
        assert session.get(Currency, character_id).gold == 75  # type: ignore[union-attr]
        assert session.get(Character, character_id).realm_id == "realm.verdant_vale"  # type: ignore[union-attr]
    clock["now"] += timedelta(minutes=1)

    arrived = await client.get("/characters/me", headers=headers)

    assert arrived.status_code == 200
    assert arrived.json()["character"]["realm_id"] == "realm.ashen_reach"
    with factory() as session:
        estate = session.scalar(select(Estate))
        assert estate is not None
        assert estate.realm_id == "realm.ashen_reach"
        assert estate.status == "active"


async def test_instant_relocation_and_unreachable_rollback(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Zero-time paths arrive immediately; unreachable paths charge nothing."""
    client, factory, headers, _ = estate_client
    content = app.state.content
    edge = MapEdge(
        realms=("realm.verdant_vale", "realm.ashen_reach"),
        cost=MapCost(gold=25, items=(), time_ms=0),
    )
    app.state.content = replace(
        content, map=content.map.model_copy(update={"edges": (edge,)})
    )

    instant = await client.post(
        "/characters/me/relocate",
        headers=headers,
        json={"realm_id": "realm.ashen_reach"},
    )

    assert instant.status_code == 200
    assert instant.json()["realm_id"] == "realm.ashen_reach"
    assert instant.json()["relocating_to_realm_id"] is None

    with factory() as session:
        character = session.scalar(select(Character))
        currency = session.scalar(select(Currency))
        estate = session.scalar(select(Estate))
        assert character is not None and currency is not None and estate is not None
        character.realm_id = "realm.verdant_vale"
        estate.realm_id = "realm.verdant_vale"
        gold_before = currency.gold
        session.commit()
    app.state.content = replace(
        content, map=content.map.model_copy(update={"edges": ()})
    )

    unreachable = await client.post(
        "/characters/me/relocate",
        headers=headers,
        json={"realm_id": "realm.ashen_reach"},
    )

    assert unreachable.status_code == 409
    assert unreachable.json()["error"]["code"] == "UNREACHABLE"
    with factory() as session:
        currency = session.scalar(select(Currency))
        estate = session.scalar(select(Estate))
        assert currency is not None and currency.gold == gold_before
        assert estate is not None and estate.realm_id == "realm.verdant_vale"


def _wait_for_postgres_blocker(
    factory: sessionmaker[Session], blocked_pid: int, blocker_pid: int
) -> None:
    """Wait for PostgreSQL to confirm a lock wait, rather than guessing timing."""
    deadline = time.monotonic() + 5
    with factory() as observer:
        while time.monotonic() < deadline:
            blockers = observer.scalar(
                text("SELECT pg_blocking_pids(:pid)"), {"pid": blocked_pid}
            )
            if blocker_pid in blockers:
                return
            threading.Event().wait(0.01)
    pytest.fail("GET /realms did not block on the lower-id realm within five seconds")


async def test_get_realms_locks_in_id_order(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """A blocked list request leaves higher-id realms available to other writers."""
    _, factory, _, clock = estate_client
    if factory.kw["bind"].dialect.name != "postgresql":
        pytest.skip("Row lock ordering requires PostgreSQL")
    content = app.state.content
    lower_id, higher_id = sorted(realm.id for realm in content.realms)
    with factory() as setup:
        for realm in content.realms:
            if setup.get(RealmState, realm.id) is None:
                setup.add(RealmState(realm_id=realm.id, node_id=realm.starting_node_id))
        setup.commit()

    started = threading.Event()
    worker_pids: list[int] = []
    returned_ids: list[str] = []
    thread_errors: list[BaseException] = []

    def list_realms() -> None:
        try:
            with factory() as session:
                session.execute(text("SET LOCAL statement_timeout = '5s'"))
                worker_pids.append(
                    session.execute(text("SELECT pg_backend_pid()")).scalar_one()
                )
                started.set()
                request = Request({"type": "http", "app": app})
                response = asyncio.run(get_realms(request, clock["now"], session))
                returned_ids.extend(realm.id for realm in response)
        except BaseException as error:
            thread_errors.append(error)

    with factory() as blocker:
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        assert (
            blocker.scalar(
                select(RealmState)
                .where(RealmState.realm_id == lower_id)
                .with_for_update()
            )
            is not None
        )
        worker = threading.Thread(target=list_realms)
        worker.start()
        try:
            assert started.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pids[0], blocker_pid)
            # Content order is high then low in the baseline. The old route
            # already held the high row when it blocked, so NOWAIT would fail.
            with factory() as probe:
                assert (
                    probe.scalar(
                        select(RealmState)
                        .where(RealmState.realm_id == higher_id)
                        .with_for_update(nowait=True)
                    )
                    is not None
                )
        finally:
            blocker.rollback()
            worker.join(timeout=6)
    assert not worker.is_alive()
    assert thread_errors == []
    assert returned_ids == [realm.id for realm in content.realms]


@pytest.mark.parametrize(
    "stage,expected_status", [("fed", "active"), ("faltering", "inert")]
)
async def test_upgrade_annotation_uses_estate_realm_active_tags(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    stage: str,
    expected_status: str,
) -> None:
    """An absent owner's upgrade annotation follows facilities in the estate realm."""
    client, factory, headers, _ = estate_client
    original = app.state.content
    upgrade = original.upgrade("upgrade.painted_sign")
    app.state.content = original.with_overrides(
        upgrades=(
            upgrade.model_copy(update={"requires_realm_tags": ("facility.fake_node",)}),
        )
    )
    with factory() as session:
        estate = session.scalar(select(Estate))
        character = session.scalar(select(Character))
        realm = session.get(RealmState, "realm.verdant_vale")
        assert estate is not None and character is not None and realm is not None
        character.realm_id = "realm.ashen_reach"
        realm.decay_stage = stage
        session.add(
            EstateUpgrade(
                estate_id=estate.id,
                upgrade_id=upgrade.id,
                slot_index=0,
                purchased_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()
    response = await client.get("/estates/me", headers=headers)
    assert response.status_code == 200
    installed = response.json()["installed_upgrades"][0]
    assert installed["status"] == expected_status
    assert installed["inert_reason"] == (
        "realm requirements not met" if expected_status == "inert" else None
    )
