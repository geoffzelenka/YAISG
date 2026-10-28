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
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from jwt import PyJWK
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker
from world_helpers import create_world_character

from app.api.estates import purchase_upgrade
from app.api.realms import get_realms
from app.auth import jwks_cache
from app.clock import utc_now
from app.content.schemas import (
    CapBonus,
    CapType,
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
            "kind": "full",
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

    from world_helpers import create_empty_world

    with factory() as session:
        create_empty_world(session, app.state.content, clock["now"])

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
            created = await create_world_character(
                client,
                factory,
                headers=headers,
                name="Estate Hero",
                realm_id="realm.verdant_vale",
            )
            assert created.status_code == 201
            # Estate tests keep currency independent of new-player grants.
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
        estate.gauge = 3
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
    assert response.json()["tier"] == 2
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
        assert estate.gauge == 3


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
    form = content.estate_form("form.homestead").model_copy(
        update={"transforms_to": ("form.camp",)}
    )
    app.state.content = replace(
        content, _forms_by_id=MappingProxyType({**content._forms_by_id, form.id: form})
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
        estate.status = "inactive"
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
    assert response.json()["edges"][0]["base_time_s"] == 60
    for node in response.json()["nodes"]:
        assert node["node"]
        assert node["tier"] == 1
        assert node["decay_stage"] == "fed"
        assert node["treasury_band"] in {"0", "1", "2", "3", "4"}
        assert node["transition_pending"] is False
        assert "treasury" not in node


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
                setup.add(
                    RealmState(
                        id=realm.id,
                        template_id=realm.id,
                        last_tick_at=datetime(2026, 1, 1, tzinfo=UTC),
                        current_node_id=realm.starting_node_id,
                    )
                )
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
                select(RealmState).where(RealmState.id == lower_id).with_for_update()
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
                        .where(RealmState.id == higher_id)
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
        character.current_realm_id = "realm.ashen_reach"
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


@pytest.mark.parametrize("isolation_source", ["template", "instance"])
async def test_isolated_realms_absent_from_lists_and_map(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    isolation_source: str,
) -> None:
    """Both isolated templates and stored instances are excluded with their edges."""
    client, factory, headers, _ = estate_client
    isolated_id = "realm.verdant_vale"
    if isolation_source == "template":
        original = app.state.content
        app.state.content = replace(
            original,
            realms=tuple(
                r.model_copy(update={"isolated": True}) if r.id == isolated_id else r
                for r in original.realms
            ),
        )
    else:
        with factory() as session:
            state = session.get(RealmState, isolated_id)
            assert state is not None
            state.isolated = True
            session.commit()
    realms = await client.get("/realms", headers=headers)
    graph = await client.get("/map")
    assert realms.status_code == graph.status_code == 200
    assert isolated_id not in {r["id"] for r in realms.json()}
    assert isolated_id not in {n["realm_id"] for n in graph.json()["nodes"]}
    assert all(isolated_id not in (e["a"], e["b"]) for e in graph.json()["edges"])


async def test_realm_tag_stack_public_and_action_state(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Acquired tags feed public activation and the character's pure state."""
    from app.models import RealmTag
    from app.services.actions import load_character_state
    from app.services.realms import push_realm_tag

    client, factory, headers, clock = estate_client
    with factory() as session:
        character = session.scalar(select(Character))
        state = session.get(RealmState, "realm.verdant_vale")
        assert character is not None and state is not None
        tag = push_realm_tag(session, state, "access.fake", clock["now"])
        session.commit()
        assert (
            "access.fake"
            in load_character_state(session, character.id).realm_stack_tags
        )
        seq, stamp = tag.seq, tag.node_id
        assert session.get(RealmTag, (state.id, "access.fake")) is not None
    response = await client.get("/realms/realm.verdant_vale", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["tags"] == [{"tag_id": "access.fake", "seq": seq, "node_id": stamp}]
    assert "access.fake" in data["active_tags"]
    assert data["node"]["realm_type"] == "agrarian" and data["node"]["tier"] == 1
    assert data["gauge"] == 0 and data["decay_stage"] == "fed"
    assert "treasury" not in data


@pytest.mark.parametrize(
    "stage,expected_status,regressing",
    [("fed", "active", False), ("faltering", "inert", False), ("fed", "inert", True)],
)
async def test_absent_owner_estate_uses_stored_realm_stack(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    stage: str,
    expected_status: str,
    regressing: bool,
) -> None:
    """An estate's acquired facilities remain its own while its owner visits."""
    from app.services.realms import push_realm_tag, start_transition

    client, factory, headers, clock = estate_client
    original = app.state.content
    upgrade = original.upgrade("upgrade.painted_sign")
    app.state.content = original.with_overrides(
        upgrades=(
            upgrade.model_copy(
                update={"requires_realm_tags": ("facility.fake_upgrade",)}
            ),
        )
    )
    with factory() as session:
        character = session.scalar(select(Character))
        estate = session.scalar(select(Estate))
        realm = session.get(RealmState, "realm.verdant_vale")
        assert character is not None and estate is not None and realm is not None
        character.current_realm_id = "realm.ashen_reach"
        realm.decay_stage = stage
        push_realm_tag(session, realm, "facility.fake_upgrade", clock["now"])
        session.add(
            EstateUpgrade(
                estate_id=estate.id,
                slot_index=0,
                upgrade_id=upgrade.id,
                purchased_at=clock["now"],
            )
        )
        if regressing:
            start_transition(
                realm,
                "node.verdant_t0_stub",
                "regression",
                clock["now"] - timedelta(days=7),
                original,
            )
        session.commit()
    response = await client.get("/estates/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["installed_upgrades"][0]["status"] == expected_status


def assert_world_estate_invariant(session: Session) -> None:
    """Every world character owns exactly one estate, which is its home pointer."""
    for character in session.scalars(select(Character)):
        realm = session.get(RealmState, character.current_realm_id)
        if realm is not None and realm.isolated:
            continue
        owned = list(
            session.scalars(
                select(Estate).where(Estate.owner_character_id == character.id)
            )
        )
        assert len(owned) == 1
        assert owned[0].id == character.home_estate_id


@pytest.mark.parametrize("path", ["transform", "upgrades/upgrade.alarm_clock"])
async def test_estate_mutations_require_owner_presence(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    path: str,
) -> None:
    """An owner visiting another realm cannot change the estate or spend goods."""
    client, factory, headers, _ = estate_client
    character_id = _give(factory, "item.fake_plank", 20)
    with factory() as session:
        character = session.get(Character, character_id)
        assert character is not None
        character.current_realm_id = "realm.ashen_reach"
        session.commit()
    response = await client.post(
        f"/estates/me/{path}", headers=headers, json={"form_id": "form.homestead"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NOT_PRESENT"
    with factory() as session:
        stack = session.get(Inventory, (character_id, "item.fake_plank"))
        assert stack is not None and stack.quantity == 20
        assert_world_estate_invariant(session)


async def test_transform_mobility_guard(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Reject mobility-changing edges even in injected content."""
    client, factory, headers, _ = estate_client
    _give(factory, "item.fake_plank", 5)
    content = app.state.content
    destination = content.estate_form("form.homestead").model_copy(
        update={"mobility": "fixed", "travel_profile": None}
    )
    app.state.content = replace(
        content,
        _forms_by_id=MappingProxyType(
            {**content._forms_by_id, destination.id: destination}
        ),
    )
    response = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": destination.id}
    )
    assert response.json()["error"]["code"] == "INVALID_TRANSFORMATION"
    with factory() as session:
        assert session.scalar(select(Estate.form_id)) == "form.camp"
        assert session.scalar(select(Inventory.quantity)) == 5


@pytest.mark.parametrize(
    "gold,goods,success", [(17, 5, True), (16, 5, False), (17, 4, False)]
)
async def test_transform_selector_payment_and_treasury_conservation(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    gold: int,
    goods: int,
    success: bool,
) -> None:
    """Transfer gold and consume goods only on full payment."""
    from app.content.schemas import ActionInput, BuildCost, Selector

    client, factory, headers, _ = estate_client
    character_id = _give(factory, "item.fake_sprig", goods)
    original = app.state.content
    destination = original.estate_form("form.homestead").model_copy(
        update={
            "build_cost": BuildCost(
                gold=17,
                goods=(
                    ActionInput(
                        selector=Selector.model_validate({"class": "fake_plant"}),
                        quantity=5,
                    ),
                ),
            )
        }
    )
    app.state.content = replace(
        original,
        _forms_by_id=MappingProxyType(
            {**original._forms_by_id, destination.id: destination}
        ),
    )
    with factory() as session:
        currency = session.get(Currency, character_id)
        realm = session.get(RealmState, "realm.verdant_vale")
        assert currency is not None and realm is not None
        currency.gold = gold
        realm.treasury = 31
        session.commit()
    response = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": destination.id}
    )
    assert response.status_code == (200 if success else 409)
    if not success:
        assert response.json()["error"]["code"] == "MISSING_INPUTS"
    with factory() as session:
        currency = session.get(Currency, character_id)
        realm = session.get(RealmState, "realm.verdant_vale")
        assert currency is not None and realm is not None
        assert currency.gold + realm.treasury == gold + 31
        assert realm.treasury == (48 if success else 31)
        stack = session.get(Inventory, (character_id, "item.fake_sprig"))
        assert (stack.quantity if stack else 0) == (0 if success else goods)
        assert_world_estate_invariant(session)


async def test_realm_owned_estates_listed(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Public reads include realm ownership and condition without treasury balances."""
    client, factory, headers, _ = estate_client
    with factory() as session:
        realm_owned = Estate(
            realm_id="realm.verdant_vale",
            form_id="form.orchard",
            decay_stage="strained",
        )
        session.add(realm_owned)
        session.commit()
        realm_owned_id = str(realm_owned.id)
        assert_world_estate_invariant(session)
    response = await client.get("/realms/realm.verdant_vale/estates", headers=headers)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert next(row for row in rows if row["id"] == realm_owned_id) == {
        "id": realm_owned_id,
        "owner": "realm-owned",
        "form": "form.orchard",
        "decay_stage": "strained",
        "gauge": 0.0,
        "sale_price": None,
    }
    assert any(row["owner"] != "realm-owned" for row in rows)
    unknown = await client.get("/realms/missing/estates", headers=headers)
    assert unknown.json()["error"]["code"] == "UNKNOWN_REALM"
    home = await client.get("/estates/me", headers=headers)
    assert home.json()["tier"] == 1
    assert home.json()["mobility"] == "mobile"
    assert home.json()["tags"] == []
    assert home.json()["decay_stage"] == "fed"
    assert "level" not in home.json()


async def test_transform_requires_destination_realm_tags(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """A transform cannot enter an inert form lacking any authored requirement."""
    client, factory, headers, _ = estate_client
    _give(factory, "item.fake_plank", 5)
    original = app.state.content
    destination = original.estate_form("form.homestead").model_copy(
        update={"requires_realm_tags": ("access.fake",)}
    )
    app.state.content = replace(
        original,
        _forms_by_id=MappingProxyType(
            {**original._forms_by_id, destination.id: destination}
        ),
    )
    response = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": destination.id}
    )
    assert response.json()["error"]["code"] == "MISSING_REALM_TAGS"
    with factory() as session:
        assert session.scalar(select(Estate.form_id)) == "form.camp"
        assert session.scalar(select(Inventory.quantity)) == 5


async def test_postgres_concurrent_transforms_pay_once(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Character serialization prevents two transforms from charging one edge twice."""
    from app.api.estates import TransformRequest, transform_estate
    from app.content.schemas import BuildCost

    _, factory, _, clock = estate_client
    if factory.kw["bind"].dialect.name != "postgresql":
        pytest.skip("Concurrent row locking requires PostgreSQL")
    character_id = _give(factory, "item.fake_plank", 10)
    original = app.state.content
    destination = original.estate_form("form.homestead")
    destination = destination.model_copy(
        update={"build_cost": BuildCost(gold=7, goods=destination.build_cost.goods)}
    )
    app.state.content = replace(
        original,
        _forms_by_id=MappingProxyType(
            {**original._forms_by_id, destination.id: destination}
        ),
    )
    with factory() as session:
        currency = session.get(Currency, character_id)
        realm = session.get(RealmState, "realm.verdant_vale")
        assert currency is not None and realm is not None
        currency.gold = 14
        realm.treasury = 0
        session.commit()
    barrier = threading.Barrier(2, timeout=5)

    def transform_once() -> tuple[int, str | None]:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            player = session.scalar(select(Player))
            assert player is not None
            barrier.wait()
            try:
                asyncio.run(
                    transform_estate(
                        TransformRequest(form_id=destination.id),
                        Request({"type": "http", "app": app}),
                        clock["now"],
                        player,
                        session,
                    )
                )
            except HTTPException as error:
                assert isinstance(error.detail, dict)
                return error.status_code, error.detail["error"]["code"]
            return 200, None

    results = await asyncio.gather(
        asyncio.to_thread(transform_once), asyncio.to_thread(transform_once)
    )
    assert sorted(results, key=lambda result: result[0]) == [
        (200, None),
        (409, "INVALID_TRANSFORMATION"),
    ]
    with factory() as session:
        currency = session.get(Currency, character_id)
        realm = session.get(RealmState, "realm.verdant_vale")
        stack = session.get(Inventory, (character_id, "item.fake_plank"))
        assert currency is not None and realm is not None
        assert currency.gold == realm.treasury == 7
        assert stack is not None and stack.quantity == 5
        assert_world_estate_invariant(session)


@pytest.mark.parametrize("last_quantity,success", [(1, True), (2, False)])
async def test_transform_overlapping_selectors_are_atomic(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    last_quantity: int,
    success: bool,
) -> None:
    """Selectors pay cheapest first from one remainder; late failure spends nothing."""
    from app.content.schemas import BuildCost

    client, factory, headers, _ = estate_client
    character_id = _give(factory, "item.fake_sprig", 3)
    _give(factory, "item.worthless_button", 2)
    original = app.state.content
    destination = original.estate_form("form.homestead").model_copy(
        update={
            "build_cost": BuildCost.model_validate(
                {
                    "gold": 0,
                    "goods": (
                        {"selector": {"class": "fake_plant"}, "quantity": 2},
                        {
                            "selector": {"item": "item.fake_sprig"},
                            "quantity": last_quantity,
                        },
                    ),
                }
            )
        }
    )
    app.state.content = replace(
        original,
        _forms_by_id=MappingProxyType(
            {**original._forms_by_id, destination.id: destination}
        ),
    )
    response = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": destination.id}
    )
    assert response.status_code == (200 if success else 409)
    with factory() as session:
        holdings = {
            stack.item_id: stack.quantity
            for stack in session.scalars(
                select(Inventory).where(Inventory.character_id == character_id)
            )
        }
        assert holdings == (
            {"item.worthless_button": 2}
            if success
            else {"item.fake_sprig": 3, "item.worthless_button": 2}
        )


@pytest.mark.parametrize("path", ["transform", "upgrades/upgrade.alarm_clock"])
async def test_estate_mutations_reject_unowned_home_pointer(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    path: str,
) -> None:
    """A home pointer grants no right to change or pay for an unowned estate."""
    from app.content.schemas import BuildCost

    client, factory, headers, _ = estate_client
    character_id = _give(factory, "item.fake_plank", 5)
    _give(factory, "item.prototype_widget", 3)
    content = app.state.content
    form = content.estate_form("form.homestead")
    form = form.model_copy(
        update={"build_cost": BuildCost(gold=7, goods=form.build_cost.goods)}
    )
    app.state.content = replace(
        content, _forms_by_id=MappingProxyType({**content._forms_by_id, form.id: form})
    )
    with factory() as session:
        character = session.get(Character, character_id)
        currency = session.get(Currency, character_id)
        realm = session.get(RealmState, "realm.verdant_vale")
        assert character is not None and currency is not None and realm is not None
        other_estate = Estate(realm_id=realm.id, form_id="form.camp")
        session.add(other_estate)
        session.flush()
        character.home_estate_id = other_estate.id
        currency.gold = 7
        realm.treasury = 11
        other_estate_id = other_estate.id
        session.commit()
    response = await client.post(
        f"/estates/me/{path}", headers=headers, json={"form_id": form.id}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_ESTATE_OWNER"
    with factory() as session:
        holdings = {
            stack.item_id: stack.quantity
            for stack in session.scalars(
                select(Inventory).where(Inventory.character_id == character_id)
            )
        }
        assert holdings == {"item.fake_plank": 5, "item.prototype_widget": 3}
        currency = session.get(Currency, character_id)
        realm = session.get(RealmState, "realm.verdant_vale")
        estate = session.get(Estate, other_estate_id)
        assert currency is not None and currency.gold == 7
        assert realm is not None and realm.treasury == 11
        assert estate is not None and estate.form_id == "form.camp"
        assert session.scalar(select(func.count()).select_from(EstateUpgrade)) == 0


@pytest.mark.parametrize("bonus", [0, 3])
async def test_profile_estate_slots_use_form_base_plus_bonuses(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    bonus: int,
) -> None:
    """The profile's slot base and effective cap share the form-owned base."""
    client, factory, headers, clock = estate_client
    content = app.state.content
    form = content.estate_form("form.camp").model_copy(update={"upgrade_slots": 7})
    app.state.content = replace(
        content,
        _forms_by_id=MappingProxyType({**content._forms_by_id, form.id: form}),
    )
    if bonus:
        upgrade = content.upgrade("upgrade.alarm_clock").model_copy(
            update={
                "cap_bonuses": (
                    CapBonus(cap=CapType.ESTATE_UPGRADE_SLOTS, value=bonus),
                )
            }
        )
        app.state.content = app.state.content.with_overrides(upgrades=(upgrade,))
        with factory() as session:
            estate = session.scalar(select(Estate))
            assert estate is not None
            session.add(
                EstateUpgrade(
                    estate_id=estate.id,
                    slot_index=0,
                    upgrade_id=upgrade.id,
                    purchased_at=clock["now"],
                )
            )
            session.commit()
    response = await client.get("/characters/me", headers=headers)
    assert response.status_code == 200
    slots = response.json()["caps"]["estate_upgrade_slots"]
    assert slots == {"base": 7, "effective": 7 + bonus}
    assert slots["base"] + bonus == slots["effective"]


@pytest.mark.parametrize("donate", [False, True])
async def test_build_buy_surrender_and_larder(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    donate: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ownership flows conserve gold and preserve one home."""
    from app.models import EstateLarder, EstateOwnershipHistory

    caplog.set_level(logging.INFO, logger="yaisg.audit")
    client, factory, headers, clock = estate_client
    character_id = _give(factory, "item.fake_sprig", 10)
    with factory() as session:
        character = session.get(Character, character_id)
        assert character is not None
        old_id = character.home_estate_id
        session.add(
            EstateUpgrade(
                estate_id=old_id,
                slot_index=0,
                upgrade_id=app.state.content.upgrades[0].id,
                purchased_at=clock["now"],
            )
        )
        session.commit()
    built = await client.post(
        "/estates/build", headers=headers, json={"form_id": "form.fake_workshop"}
    )
    assert built.status_code == 200, built.text
    fixed_id = uuid.UUID(built.json()["id"])
    with factory() as session:
        tombstone = session.get(Estate, old_id)
        assert tombstone is not None and tombstone.status == "destroyed"
        assert tombstone.owner_character_id is None
        old_history = session.scalar(
            select(EstateOwnershipHistory).where(
                EstateOwnershipHistory.estate_id == old_id
            )
        )
        assert old_history is not None
        assert old_history.relinquished_at is not None
        assert old_history.relinquished_at.replace(tzinfo=UTC) == clock["now"]
        assert session.get(EstateUpgrade, (old_id, 0)) is None
        assert (
            session.scalar(
                select(EstateOwnershipHistory).where(
                    EstateOwnershipHistory.estate_id == fixed_id
                )
            )
            is not None
        )
        assert_world_estate_invariant(session)
        realm = session.get(RealmState, "realm.verdant_vale")
        assert realm is not None and realm.treasury == 20
        realm.treasury = 3
        session.commit()
    rejected = await client.post(
        "/estates/me/larder",
        headers=headers,
        json={"item_id": "item.fake_plank", "quantity": 1},
    )
    assert rejected.json()["error"]["code"] == "NOT_UPKEEP_ITEM"
    deposited = await client.post(
        "/estates/me/larder",
        headers=headers,
        json={"item_id": "item.fake_sprig", "quantity": 3},
    )
    assert deposited.status_code == 200
    assert deposited.json()["larder"] == {"item.fake_sprig": 3000}
    assert deposited.json()["surrender_value"] == built.json()["surrender_value"]
    assert deposited.json()["surrender_value"] > 3
    assert "surrender_payout" not in deposited.json()
    preview = await client.get("/estates/me", headers=headers)
    assert preview.json()["larder"] == {"item.fake_sprig": 3000}
    assert preview.json()["surrender_value"] == built.json()["surrender_value"]
    assert "surrender_payout" not in preview.json()
    assert "treasury" not in preview.json()
    assert (
        await client.delete("/estates/me/larder", headers=headers)
    ).status_code == 405
    surrendered = await client.post(
        "/estates/me/surrender", headers=headers, json={"donate": donate}
    )
    assert surrendered.status_code == 200
    assert surrendered.json()["surrender_value"] is None
    assert surrendered.json()["larder"] == {}
    surrendered_mobile_id = uuid.UUID(surrendered.json()["id"])
    with factory() as session:
        holding = session.get(EstateLarder, (fixed_id, "item.fake_sprig"))
        currency = session.get(Currency, character_id)
        realm = session.get(RealmState, "realm.verdant_vale")
        assert holding is not None and holding.quantity_milli == 3000
        assert currency is not None and currency.gold == 80 + (0 if donate else 3)
        assert realm is not None and realm.treasury == (3 if donate else 0)
        assert_world_estate_invariant(session)
    bought = await client.post(f"/estates/{fixed_id}/buy", headers=headers)
    assert bought.status_code == 200, bought.text
    with factory() as session:
        retired = session.get(Estate, surrendered_mobile_id)
        assert retired is not None and retired.status == "destroyed"
        assert retired.owner_character_id is None
        retired_history = session.scalar(
            select(EstateOwnershipHistory).where(
                EstateOwnershipHistory.estate_id == surrendered_mobile_id
            )
        )
        assert (
            retired_history is not None and retired_history.relinquished_at is not None
        )
        assert retired_history.relinquished_at.replace(tzinfo=UTC) == clock["now"]
        assert_world_estate_invariant(session)
    again = await client.post(f"/estates/{fixed_id}/buy", headers=headers)
    assert again.json()["error"]["code"] == "MOBILE_ESTATE_REQUIRED"
    changes = {
        json.loads(record.message)["change"]
        for record in caplog.records
        if record.name == "yaisg.audit"
    }
    assert {
        "estate_built",
        "estate_bought",
        "estate_surrendered",
        "larder_deposited",
    } <= changes


async def test_postgres_two_buyers_one_estate(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """The realm and estate locks serialize competing ownership transfers."""
    from app.api.estates import buy_estate

    client, factory, _, clock = estate_client
    if factory.kw["bind"].dialect.name != "postgresql":
        pytest.skip("Concurrent row locking requires PostgreSQL")
    created = await create_world_character(
        client,
        factory,
        headers={"Authorization": f"Bearer {_token()}"},
        name="Second Buyer",
        realm_id="realm.verdant_vale",
    )
    assert created.status_code == 201
    with factory() as session:
        players = list(session.scalars(select(Player.id)))
        for currency in session.scalars(select(Currency)):
            currency.gold = 100
        estate = Estate(form_id="form.fake_workshop", realm_id="realm.verdant_vale")
        session.add(estate)
        session.commit()
        estate_id = estate.id
    barrier = threading.Barrier(2, timeout=10)

    def buy_once(player_id: uuid.UUID) -> tuple[int, str | None]:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            player = session.get(Player, player_id)
            assert player is not None
            barrier.wait()
            try:
                asyncio.run(
                    buy_estate(
                        estate_id,
                        Request({"type": "http", "app": app}),
                        clock["now"],
                        player,
                        session,
                    )
                )
            except HTTPException as error:
                assert isinstance(error.detail, dict)
                return error.status_code, error.detail["error"]["code"]
            return 200, None

    results = await asyncio.gather(
        *(asyncio.to_thread(buy_once, player_id) for player_id in players)
    )
    assert sorted(results) == [(200, None), (409, "NOT_FOR_SALE")]
    with factory() as session:
        assert_world_estate_invariant(session)
        realm = session.get(RealmState, "realm.verdant_vale")
        assert realm is not None
        total = sum(currency.gold for currency in session.scalars(select(Currency)))
        assert total + realm.treasury == 200
        assert (
            session.scalar(
                select(func.count())
                .select_from(Estate)
                .where(Estate.id == estate_id, Estate.owner_character_id.is_not(None))
            )
            == 1
        )


async def test_ownership_flow_preconditions(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Invalid ownership requests preserve holdings."""
    client, factory, headers, _ = estate_client
    for form_id in ("missing", "form.camp", "form.homestead"):
        result = await client.post(
            "/estates/build", headers=headers, json={"form_id": form_id}
        )
        assert result.json()["error"]["code"] == "INVALID_BUILD_FORM"
    result = await client.post(
        "/estates/me/surrender", headers=headers, json={"donate": False}
    )
    assert result.json()["error"]["code"] == "CANNOT_SURRENDER_MOBILE"
    original = app.state.content
    form = original.estate_form("form.fake_workshop")
    app.state.content = replace(
        original,
        _forms_by_id=MappingProxyType(
            {
                **original._forms_by_id,
                form.id: form.model_copy(
                    update={"requires_realm_tags": ("missing.tag",)}
                ),
            }
        ),
    )
    result = await client.post(
        "/estates/build", headers=headers, json={"form_id": form.id}
    )
    assert result.json()["error"]["code"] == "MISSING_REALM_TAGS"
    app.state.content = original
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.current_realm_id = "realm.ashen_reach"
        session.commit()
    result = await client.post(
        "/estates/build", headers=headers, json={"form_id": form.id}
    )
    assert result.json()["error"]["code"] == "NOT_PRESENT"
    with factory() as session:
        currency = session.scalar(select(Currency))
        assert currency is not None and currency.gold == 100
        assert_world_estate_invariant(session)


@settings(
    deadline=None,
    max_examples=25,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    value=st.integers(min_value=1, max_value=10**8),
    treasury=st.integers(min_value=0, max_value=10**8),
)
async def test_buy_surrender_always_loses_gold(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    value: int,
    treasury: int,
) -> None:
    """Real ownership flows charge markup, cap payouts and conserve both balances."""
    from app.content.schemas import BuildCost
    from app.engine.estates import sale_price
    from app.models import EstateOwnershipHistory
    from app.services.estates import persisted_estate_value
    from app.services.realms import as_utc

    client, factory, headers, clock = estate_client
    original = app.state.content
    form = original.estate_form("form.fake_workshop").model_copy(
        update={"build_cost": BuildCost(gold=value)}
    )
    app.state.content = replace(
        original,
        estate_forms=tuple(
            form if entry.id == form.id else entry for entry in original.estate_forms
        ),
        _forms_by_id=MappingProxyType(
            {
                **original._forms_by_id,
                form.id: form,
            }
        ),
    )
    try:
        with factory() as session:
            character = session.scalar(select(Character))
            assert character is not None
            character_id = character.id
            currency = session.get(Currency, character_id)
            realm = session.get(RealmState, character.current_realm_id)
            assert currency is not None and realm is not None
            target = Estate(form_id=form.id, realm_id=realm.id)
            session.add(target)
            session.flush()
            rebuilt = persisted_estate_value(session, target, app.state.content).value
            assert rebuilt == value
            price = sale_price(
                rebuilt, app.state.content.economy.estate.sale_markup_pct
            )
            initial_gold = price + value
            currency.gold = initial_gold
            realm.treasury = treasury
            target_id, realm_id = target.id, realm.id
            session.commit()
        bought = await client.post(f"/estates/{target_id}/buy", headers=headers)
        assert bought.status_code == 200, bought.text
        with factory() as session:
            currency = session.get(Currency, character_id)
            realm = session.get(RealmState, realm_id)
            assert currency is not None and realm is not None
            assert initial_gold - currency.gold == price
            assert realm.treasury - treasury == price
            history = session.scalar(
                select(EstateOwnershipHistory).where(
                    EstateOwnershipHistory.estate_id == target_id
                )
            )
            assert history is not None and history.relinquished_at is None
            first_history_id = history.id
            assert_world_estate_invariant(session)
        surrendered = await client.post(
            "/estates/me/surrender", headers=headers, json={"donate": False}
        )
        assert surrendered.status_code == 200, surrendered.text
        with factory() as session:
            currency = session.get(Currency, character_id)
            realm = session.get(RealmState, realm_id)
            assert currency is not None and realm is not None
            # The buy proceeds alone exceed value: this exercises the payout cap.
            assert treasury + price > value
            assert currency.gold - (initial_gold - price) == value
            assert treasury + price - realm.treasury == value
            assert currency.gold < initial_gold
            assert currency.gold + realm.treasury == initial_gold + treasury
            history = session.get(EstateOwnershipHistory, first_history_id)
            assert history is not None and history.relinquished_at is not None
            assert as_utc(history.relinquished_at) == clock["now"]
            assert_world_estate_invariant(session)
        reacquired = await client.post(f"/estates/{target_id}/buy", headers=headers)
        assert reacquired.status_code == 200, reacquired.text
        with factory() as session:
            histories = list(
                session.scalars(
                    select(EstateOwnershipHistory).where(
                        EstateOwnershipHistory.estate_id == target_id
                    )
                )
            )
            assert len(histories) == 2
            fresh = next(row for row in histories if row.id != first_history_id)
            assert fresh.relinquished_at is None
            assert as_utc(fresh.acquired_at) == clock["now"]
    finally:
        # Keep generated examples independent, including during failure shrinking.
        try:
            with factory() as session:
                character = session.scalar(select(Character))
                assert character is not None
                home = session.get(Estate, character.home_estate_id)
                assert home is not None
                fixed_home = original.estate_form(home.form_id).mobility == "fixed"
            if fixed_home:
                cleanup = await client.post(
                    "/estates/me/surrender", headers=headers, json={"donate": True}
                )
                assert cleanup.status_code == 200
        finally:
            app.state.content = original


@pytest.mark.parametrize("target_kind", ["other_realm", "owned", "mobile"])
async def test_buy_rejects_targets_not_for_sale(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
    target_kind: str,
) -> None:
    """Only realm-owned fixed estates in the buyer's realm can be bought."""
    client, factory, headers, _ = estate_client
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        target = Estate(
            form_id="form.camp" if target_kind == "mobile" else "form.fake_workshop",
            realm_id="realm.ashen_reach"
            if target_kind == "other_realm"
            else character.current_realm_id,
            owner_character_id=character.id if target_kind == "owned" else None,
        )
        session.add(target)
        session.commit()
        target_id = target.id
    result = await client.post(f"/estates/{target_id}/buy", headers=headers)
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "NOT_FOR_SALE"


async def test_estate_listing_prices_only_fixed_and_does_not_write_valuations(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Public listings compute prices without estate locks or persisted paths."""
    from sqlalchemy import event

    from app.engine.estates import sale_price
    from app.services.estates import persisted_estate_value

    client, factory, headers, _ = estate_client
    with factory() as session:
        fixed = Estate(
            form_id="form.fake_workshop",
            realm_id="realm.verdant_vale",
            data={"custom": "retained"},
        )
        mobile = Estate(form_id="form.camp", realm_id="realm.verdant_vale")
        session.add_all([fixed, mobile])
        session.flush()
        value = persisted_estate_value(session, fixed, app.state.content)
        assert fixed.data == {"custom": "retained"}
        price = sale_price(
            value.value, app.state.content.economy.estate.sale_markup_pct
        )
        fixed_id, mobile_id = fixed.id, mobile.id
        session.commit()
    statements: list[str] = []

    def capture(
        connection: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        statements.append(statement.lower())

    engine = factory.kw["bind"]
    event.listen(engine, "before_cursor_execute", capture)
    try:
        response = await client.get(
            "/realms/realm.verdant_vale/estates", headers=headers
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.json()}
    assert rows[str(fixed_id)]["sale_price"] == price
    assert rows[str(mobile_id)]["sale_price"] is None
    assert not any("update estates" in statement for statement in statements)
    assert not any(
        "from estates" in statement and "for update" in statement
        for statement in statements
    )
    with factory() as session:
        saved = session.get(Estate, fixed_id)
        assert saved is not None and saved.data == {"custom": "retained"}


async def test_decay_gauge_visible_on_map_realm_and_estates(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """Strained days remain visible publicly and on the owner's home estate."""
    client, factory, headers, _ = estate_client
    with factory() as session:
        character = session.scalar(select(Character))
        realm = session.get(RealmState, "realm.verdant_vale")
        assert character is not None and realm is not None
        home = session.get(Estate, character.home_estate_id)
        assert home is not None
        realm.gauge = home.gauge = 0.75
        realm.decay_stage = home.decay_stage = "strained"
        session.commit()
    responses = [
        await client.get(path, headers=headers)
        for path in (
            "/map",
            "/realms/realm.verdant_vale",
            "/realms/realm.verdant_vale/estates",
            "/estates/me",
        )
    ]
    assert all(response.status_code == 200 for response in responses)
    graph, realm_json, estates, home_json = [response.json() for response in responses]
    node = next(n for n in graph["nodes"] if n["realm_id"] == "realm.verdant_vale")
    for row in (node, realm_json, estates[0], home_json):
        assert row["decay_stage"] == "strained" and row["gauge"] == 0.75
        assert "treasury" not in row


async def test_destroyed_estate_is_hidden_and_cannot_be_bought(
    estate_client: tuple[
        AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
    ],
) -> None:
    """History tombstones cannot reenter gameplay through the buy endpoint."""
    client, factory, headers, _ = estate_client
    with factory() as session:
        tombstone = Estate(
            realm_id="realm.verdant_vale",
            form_id="form.fake_workshop",
            status="destroyed",
        )
        session.add(tombstone)
        currency = session.scalar(select(Currency))
        character = session.scalar(select(Character))
        assert currency is not None and character is not None
        currency.gold = 1000
        home_id = character.home_estate_id
        session.commit()
        tombstone_id = tombstone.id
    listed = await client.get("/realms/realm.verdant_vale/estates", headers=headers)
    assert str(tombstone_id) not in {row["id"] for row in listed.json()}
    response = await client.post(f"/estates/{tombstone_id}/buy", headers=headers)
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "NOT_FOR_SALE"
    )
    with factory() as session:
        character = session.scalar(select(Character))
        currency = session.scalar(select(Currency))
        assert character is not None and character.home_estate_id == home_id
        assert currency is not None and currency.gold == 1000
        destroyed = session.get(Estate, tombstone_id)
        assert destroyed is not None and destroyed.owner_character_id is None
        assert destroyed.status == "destroyed"
