"""Active-action API integration tests."""

import base64
import os
import threading
import time
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from jwt import PyJWK
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth import jwks_cache
from app.clock import utc_now
from app.db import Base, configure_sqlite_engine, get_db
from app.main import app
from app.models import CharacterSkill, Inventory, RewardLog
from app.services.actions import resolve_character

pytestmark = pytest.mark.anyio
_KEY_ID = "action-test-key"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@dataclass
class FakeClock:
    """Mutable route clock used to advance server time explicitly."""

    now: datetime

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        """Advance the server clock by a test-controlled duration."""
        self.now += delta


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
async def action_client(
    tmp_path: Path,
) -> AsyncGenerator[
    tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]], None
]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url:
        engine = create_engine(database_url)
    else:
        engine = create_engine(
            f"sqlite:///{tmp_path / 'actions.db'}",
            connect_args={"check_same_thread": False, "timeout": 10},
        )
        configure_sqlite_engine(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    async def test_db() -> AsyncGenerator[Session, None]:
        with factory() as session:
            yield session

    clock = FakeClock(datetime(2026, 1, 1, tzinfo=UTC))

    async def frozen_now() -> datetime:
        return clock.now

    from world_helpers import create_empty_world

    with factory() as session:
        create_empty_world(session, app.state.content, clock.now)

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[utc_now] = frozen_now
    original = jwks_cache.get_key
    jwks_cache.get_key = AsyncMock(return_value=_public_jwk())  # type: ignore[method-assign]
    headers = {"Authorization": f"Bearer {_token()}"}
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            created = await client.post(
                "/characters",
                headers=headers,
                json={"name": "Action Hero", "realm_id": "realm.verdant_vale"},
            )
            assert created.status_code == 201
            yield client, factory, clock, headers
    finally:
        jwks_cache.get_key = original  # type: ignore[method-assign]
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


async def test_start_poll_poll_stop_persists_matching_rewards(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, factory, clock, headers = action_client
    started = await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "gathering.fake_sprigs"},
    )
    assert started.status_code == 200
    assert started.json()["cycle_ms"] == 2727
    assert datetime.fromisoformat(started.json()["started_at"]).tzinfo is not None

    clock.advance(timedelta(milliseconds=2727))
    first = await client.get("/characters/me/action", headers=headers)
    clock.advance(timedelta(milliseconds=5454))
    second = await client.get("/characters/me/action", headers=headers)
    stopped = await client.delete("/characters/me/action", headers=headers)

    assert first.json()["since_last"]["cycles_completed"] == 1
    assert (
        datetime.fromisoformat(first.json()["active"]["started_at"]).tzinfo is not None
    )
    assert second.json()["since_last"]["cycles_completed"] == 2
    assert stopped.json()["active"] is None
    assert stopped.json()["since_last"]["cycles_completed"] == 0
    with factory() as session:
        gathering = session.scalar(
            select(CharacterSkill).where(CharacterSkill.skill_id == "gathering")
        )
        logs = list(session.scalars(select(RewardLog).order_by(RewardLog.resolved_at)))
        inventory_total = session.scalar(
            select(func.sum(Inventory.quantity)).where(
                Inventory.item_id == "item.fake_sprig"
            )
        )
        assert gathering is not None and gathering.xp == 30
        assert [log.cycles for log in logs] == [1, 2]
        assert sum(log.xp["gathering"] for log in logs) == gathering.xp
        assert inventory_total == sum(
            log.items["gained"].get("item.fake_sprig", 0) for log in logs
        )


async def test_switching_mid_cycle_resolves_old_action_without_rewards(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, factory, clock, headers = action_client
    await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "gathering.fake_sprigs"},
    )
    with factory() as session:
        character_id = session.scalar(select(CharacterSkill.character_id))
        assert character_id is not None
        session.add(
            Inventory(
                character_id=character_id,
                item_id="item.fake_sprig",
                quantity=2,
            )
        )
        session.commit()
    clock.advance(timedelta(seconds=1))

    switched = await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "refining.fake_plank"},
    )
    current = await client.get("/characters/me/action", headers=headers)

    assert switched.status_code == 200
    assert current.json()["active"]["action_id"] == "refining.fake_plank"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(RewardLog)) == 0


async def test_offline_cap_rewards_once_and_stops(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, factory, clock, headers = action_client
    await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "gathering.fake_sprigs"},
    )
    clock.advance(timedelta(hours=20))

    response = await client.get("/characters/me/action", headers=headers)

    feed = response.json()
    assert feed["active"] is None
    assert feed["stop_reason"] == "offline_cap"
    assert feed["since_last"]["cycles_completed"] == 16_283
    with factory() as session:
        log = session.scalar(select(RewardLog))
        assert log is not None and log.cycles == 16_283


async def test_available_actions_reflect_realm_level_and_empty_fixed_skills(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, _, _, headers = action_client
    response = await client.get("/characters/me/actions/available", headers=headers)

    groups = {group["skill_id"]: group for group in response.json()["skills"]}
    gathering = {
        action["action_id"]: action for action in groups["gathering"]["actions"]
    }
    assert gathering["gathering.mock_ore"]["blocked_by"] == [
        "INSUFFICIENT_LEVEL",
        "MISSING_REALM_TAG",
    ]
    assert groups["travel"]["actions"][0]["action_id"] == "action.fake_journey"
    assert gathering["gathering.fake_sprigs"]["startable"] is True
    assert gathering["gathering.test_crystal"]["blocked_by"] == ["INSUFFICIENT_LEVEL"]
    assert groups["melee"]["actions"][0]["action_id"] == "placeholder.fight"
    assert groups["exploration"]["actions"][0]["action_id"] == "placeholder.expedition"
    for skill_id in (
        "ranged",
        "magic",
        "accuracy",
        "defense",
        "vigor",
    ):
        assert groups[skill_id]["actions"] == []


async def test_journey_report_and_generic_start_share_destination_gate(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """The uniform report cannot advertise a journey as directly startable."""
    client, _, _, headers = action_client
    response = await client.get("/actions/available", headers=headers)
    assert response.status_code == 200
    travel = next(
        group for group in response.json()["skills"] if group["skill_id"] == "travel"
    )
    journey = travel["actions"][0]
    assert journey["startable"] is False
    assert journey["blocked_by"] == ["TRAVEL_DESTINATION_REQUIRED"]
    started = await client.post(
        "/actions/start", headers=headers, json={"action_id": journey["action_id"]}
    )
    assert started.status_code == 409
    assert started.json()["error"]["code"] == journey["blocked_by"][0]


async def test_profile_resolution_remains_in_reward_feed(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, _, clock, headers = action_client
    await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "gathering.fake_sprigs"},
    )
    clock.advance(timedelta(milliseconds=2727))
    profile = await client.get("/characters/me", headers=headers)
    clock.advance(timedelta(milliseconds=2727))

    poll = await client.get("/characters/me/action", headers=headers)

    assert profile.status_code == 200
    assert poll.json()["since_last"]["cycles_completed"] == 2
    assert poll.json()["since_last"]["xp_gained"] == {"gathering": 20}


async def test_zero_cycle_stop_reason_survives_prior_unclaimed_rewards(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, factory, clock, headers = action_client
    await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "gathering.fake_sprigs"},
    )
    clock.advance(timedelta(milliseconds=2727))
    await client.get("/characters/me", headers=headers)
    with factory() as session:
        stack = session.scalar(
            select(Inventory).where(Inventory.item_id == "item.fake_sprig")
        )
        assert stack is not None
        stack.quantity = 2
        session.commit()
    switched = await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "refining.fake_plank"},
    )
    assert switched.status_code == 200
    with factory() as session:
        stack = session.scalar(
            select(Inventory).where(Inventory.item_id == "item.fake_sprig")
        )
        assert stack is not None
        session.delete(stack)
        session.commit()
    clock.advance(timedelta(milliseconds=4500))

    poll = await client.get("/characters/me/action", headers=headers)

    assert poll.json()["since_last"]["cycles_completed"] == 1
    assert poll.json()["stop_reason"] == "inputs_exhausted"
    assert poll.json()["since_last"]["stop_reason"] == "inputs_exhausted"


async def test_concurrent_resolves_contend_and_do_not_double_reward(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, factory, clock, headers = action_client
    await client.post(
        "/characters/me/action",
        headers=headers,
        json={"action_id": "gathering.fake_sprigs"},
    )
    with factory() as session:
        character_id = session.scalar(select(CharacterSkill.character_id))
    assert character_id is not None
    clock.advance(timedelta(milliseconds=2727))
    first_has_lock = threading.Event()
    release_first = threading.Event()
    second_finished = threading.Event()
    thread_errors: list[BaseException] = []

    def first_resolve() -> None:
        with factory() as session:
            resolve_character(session, character_id, clock.now)
            first_has_lock.set()
            assert release_first.wait(timeout=5)
            session.commit()

    def second_resolve() -> None:
        assert first_has_lock.wait(timeout=5)
        with factory() as session:
            resolve_character(session, character_id, clock.now)
            session.commit()
        second_finished.set()

    def run_safely(operation: Callable[[], None]) -> None:
        try:
            operation()
        except BaseException as error:
            thread_errors.append(error)

    first_thread = threading.Thread(target=run_safely, args=(first_resolve,))
    second_thread = threading.Thread(target=run_safely, args=(second_resolve,))
    first_thread.start()
    assert first_has_lock.wait(timeout=5)
    second_thread.start()
    time.sleep(0.2)
    assert not second_finished.is_set()
    release_first.set()
    first_thread.join(timeout=5)
    second_thread.join(timeout=5)
    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert thread_errors == []

    with factory() as session:
        assert session.scalar(select(func.sum(RewardLog.cycles))) == 1


async def test_profile_and_available_report_same_effective_values(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Both reporting surfaces share server-computed rates and bonus figures."""
    client, _, _, headers = action_client
    profile = (await client.get("/characters/me", headers=headers)).json()
    available = (
        await client.get("/characters/me/actions/available", headers=headers)
    ).json()
    action = available["skills"][0]["actions"][0]
    report = profile["actions"][action["action_id"]]
    assert report == {key: action[key] for key in report}
    assert report == {
        "cycle_ms": 2727,
        "xp_per_cycle": 10,
        "xp_bonus_uncapped": 0,
        "xp_bonus_capped": 0,
        "proficiency_pct": 0,
        "taper_factor": 1,
    }


async def test_tag_availability_start_and_estate_presence(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Both routes use owner-only facilities and reload the estate realm column."""
    from app.content.schemas import Requirements
    from app.models import Estate, EstateUpgrade

    client, factory, _, headers = action_client
    original = app.state.content
    action = original.action("gathering.fake_sprigs")
    changed = action.model_copy(
        update={"requires": Requirements(facility="facility.fake_upgrade")}
    )
    app.state.content = original.with_overrides(actions=(changed,))
    try:

        async def blockers() -> list[str]:
            response = await client.get("/actions/available", headers=headers)
            assert response.status_code == 200
            return response.json()["skills"][0]["actions"][0]["blocked_by"]  # type: ignore[no-any-return]

        assert await blockers() == ["MISSING_FACILITY"]
        failed = await client.post(
            "/actions/start", headers=headers, json={"action_id": action.id}
        )
        assert failed.json()["error"]["code"] == "MISSING_FACILITY"
        with factory() as session:
            estate = session.scalar(select(Estate))
            assert estate is not None
            session.add(
                EstateUpgrade(
                    estate_id=estate.id,
                    upgrade_id="upgrade.painted_sign",
                    slot_index=0,
                    purchased_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )
            session.commit()
        assert await blockers() == []
        with factory() as session:
            estate = session.scalar(select(Estate))
            assert estate is not None
            estate.realm_id = "realm.ashen_reach"
            session.commit()
        assert await blockers() == ["MISSING_FACILITY"]
        with factory() as session:
            estate = session.scalar(select(Estate))
            assert estate is not None
            estate.realm_id = "realm.verdant_vale"
            session.commit()
        started = await client.post(
            "/actions/start", headers=headers, json={"action_id": action.id}
        )
        assert started.status_code == 200
    finally:
        app.state.content = original


async def test_requirement_lost_after_realm_node_change(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Persistent realm tag loss grants accrued rewards once and ends the action."""
    from app.models import RealmState

    client, factory, clock, headers = action_client
    started = await client.post(
        "/actions/start", headers=headers, json={"action_id": "gathering.fake_sprigs"}
    )
    assert started.status_code == 200
    clock.advance(timedelta(seconds=3))
    initial = await client.get("/characters/me/action", headers=headers)
    assert initial.json()["since_last"]["cycles_completed"] == 1
    with factory() as session:
        realm = session.get(RealmState, "realm.verdant_vale")
        assert realm is not None
        realm.current_node_id = "node.verdant_t0_stub"
        session.commit()
    clock.advance(timedelta(seconds=3))
    lost = await client.get("/characters/me/action", headers=headers)
    assert lost.json()["since_last"]["cycles_completed"] == 1
    assert lost.json()["stop_reason"] == "REQUIREMENT_LOST"
    assert lost.json()["active"] is None
    repeated = await client.get("/characters/me/action", headers=headers)
    assert repeated.json()["since_last"]["cycles_completed"] == 0


async def test_zero_cycle_requirement_loss_survives_availability_read(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """An intervening read cannot swallow a zero-cycle requirement-loss reason."""
    from app.models import RealmState

    client, factory, _, headers = action_client
    response = await client.post(
        "/actions/start", headers=headers, json={"action_id": "gathering.fake_sprigs"}
    )
    assert response.status_code == 200
    with factory() as session:
        realm = session.get(RealmState, "realm.verdant_vale")
        assert realm is not None
        realm.current_node_id = "node.verdant_t0_stub"
        session.commit()
    await client.get("/actions/available", headers=headers)
    feed = await client.get("/characters/me/action", headers=headers)
    assert feed.json()["stop_reason"] == "REQUIREMENT_LOST"
    assert feed.json()["since_last"]["cycles_completed"] == 0
    repeat = await client.get("/characters/me/action", headers=headers)
    assert repeat.json()["stop_reason"] is None


@pytest.mark.parametrize(
    "stage,realm_bonus,extra_slots", [("fed", 2, 7), ("faltering", 1, 0)]
)
async def test_profile_and_available_share_decay_stage_state(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    stage: str,
    realm_bonus: int,
    extra_slots: int,
) -> None:
    """Profiles share both holder stages for bonuses, caps and action values."""
    from dataclasses import replace

    from app.content.schemas import CapType
    from app.models import Estate, EstateUpgrade, RealmState

    client, factory, clock, headers = action_client
    original = app.state.content
    tags = tuple(
        tag.model_copy(update={"cap_bonuses": {CapType.INVENTORY_SLOTS: 7}})
        if tag.id == "facility.fake_upgrade"
        else tag
        for tag in original.tags
    )
    app.state.content = replace(original, tags=tags)
    try:
        with factory() as session:
            realm = session.get(RealmState, "realm.verdant_vale")
            estate = session.scalar(select(Estate))
            assert realm is not None and estate is not None
            realm.current_node_id = "node.verdant_t0_stub"
            realm.decay_stage = stage
            estate.decay_stage = stage
            session.add(
                EstateUpgrade(
                    estate_id=estate.id,
                    upgrade_id="upgrade.painted_sign",
                    slot_index=0,
                    purchased_at=clock.now,
                )
            )
            session.commit()
        response = await client.get("/characters/me", headers=headers)
        assert response.status_code == 200
        profile = response.json()
        available = (await client.get("/actions/available", headers=headers)).json()
        action = available["skills"][0]["actions"][0]
        report = profile["actions"][action["action_id"]]
        assert report == {key: action[key] for key in report}
        assert report["xp_bonus_uncapped"] == pytest.approx(
            (1 + realm_bonus / 100) * (1 + (5 if stage == "fed" else 2.5) / 100) * 100
            - 100
        )
        assert sorted(m["value"] for m in profile["realm"]["active_modifiers"]) == [
            realm_bonus,
            5 if stage == "fed" else 2.5,
        ]
        assert (
            profile["caps"]["inventory_slots"]["effective"]
            == original.caps.inventory_slots + extra_slots
        )
    finally:
        app.state.content = original


async def test_resolver_meta_and_details_round_trip(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resolver progress survives polls and its summary is logged and claimed once."""
    from dataclasses import replace

    from app.content.schemas import Action
    from app.engine import (
        CharacterState,
        RandomSource,
        ResolveContext,
        ResolveResult,
        UniformResolver,
    )
    from app.models import ActiveActionRecord

    original = UniformResolver.resolve

    def with_progress(
        self: UniformResolver,
        state: CharacterState,
        action: Action,
        ctx: ResolveContext,
        budget_ms: int,
        rng: RandomSource,
    ) -> ResolveResult:
        result = original(self, state, action, ctx, budget_ms, rng)
        if result.cycles_completed == 0:
            return result
        assert result.active is not None
        step = ctx.active.meta.get("step", 0) + 1
        return replace(
            result,
            active=replace(result.active, meta={"step": step}),
            details={"step": step, "nested": {"visited": ["synthetic"]}},
        )

    monkeypatch.setattr(UniformResolver, "resolve", with_progress)
    client, factory, clock, headers = action_client
    started = await client.post(
        "/actions/start",
        headers=headers,
        json={"action_id": "gathering.fake_sprigs"},
    )
    assert started.status_code == 200
    for step in (1, 2):
        clock.advance(timedelta(seconds=3))
        response = await client.get("/actions/poll", headers=headers)
        assert response.status_code == 200
        details = response.json()["since_last"]["details"]["resolutions"]
        assert len(details) == 1
        assert details[0]["step"] == step
        assert details[0]["nested"] == {"visited": ["synthetic"]}
        with factory() as session:
            active = session.scalar(select(ActiveActionRecord))
            assert active is not None and active.meta == {"step": step}
            logs = list(
                session.scalars(select(RewardLog).order_by(RewardLog.resolved_at))
            )
            assert logs[-1].details == details[0]
            assert all(log.claimed_at is not None for log in logs)
        repeated = await client.get("/actions/poll", headers=headers)
        assert repeated.json()["since_last"]["details"] == {}
    stopped = await client.post("/actions/stop", headers=headers)
    assert stopped.status_code == 200 and stopped.json()["active"] is None


@pytest.mark.parametrize("has_active", [False, True])
async def test_postgres_resolve_locks_character_with_or_without_action(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    has_active: bool,
) -> None:
    """The same parent lock serializes first starts and already active actions."""
    from sqlalchemy.exc import DBAPIError

    from app.models import Character

    client, factory, clock, headers = action_client
    with factory() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL row lock assertion")
        character_id = session.scalar(select(Character.id))
    assert character_id is not None
    if has_active:
        response = await client.post(
            "/actions/start",
            headers=headers,
            json={"action_id": "gathering.fake_sprigs"},
        )
        assert response.status_code == 200
    with factory() as first:
        resolve_character(first, character_id, clock.now)
        with factory() as second:
            with pytest.raises(DBAPIError) as error:
                second.execute(
                    select(Character.id)
                    .where(Character.id == character_id)
                    .with_for_update(nowait=True)
                )
            assert getattr(error.value.orig, "sqlstate", None) == "55P03"
            second.rollback()
        first.rollback()
