"""Project lifecycle, exact timed events, conservation, and realm catch-up."""

import uuid
from dataclasses import replace
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import cast
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock
from test_actions import action_client as action_client
from test_actions import anyio_backend as anyio_backend
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.content.loader import ContentIndex
from app.content.schemas import ActionInput, Project, ProjectKickoff, Selector
from app.engine.projects import erode_project
from app.models import (
    Character,
    Currency,
    Estate,
    Inventory,
    RealmContribution,
    RealmProjectRun,
    RealmState,
    RealmTag,
)
from app.services import realm_ticks
from app.services.projects import contribute, kickoff
from app.services.realms import (
    _as_utc,
    finalize_realm,
    push_realm_tag,
    resolve_realm,
    start_transition,
)

PROJECT = "project.verdant_cardboard"
REALM = "realm.verdant_vale"
ApiFixture = tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]]


def _code(error: HTTPException) -> str:
    return cast(dict[str, dict[str, str]], error.detail)["error"]["code"]


def _content(project: Project) -> ContentIndex:
    return replace(
        CONTENT,
        _projects_by_id=MappingProxyType(
            {p.id: project if p.id == project.id else p for p in CONTENT.projects}
        ),
    )


def _run(session: Session, realm: RealmState, now: datetime = NOW) -> RealmProjectRun:
    run = RealmProjectRun(
        realm_id=realm.id,
        project_id=PROJECT,
        status="funding",
        kicked_off_by=_hero(session).id,
        kicked_off_at=now,
        required=[
            line.model_dump(mode="json", by_alias=True)
            for line in CONTENT.project(PROJECT).cost
        ],
        contributed=[50000, 12500],
        last_contribution_at=now,
    )
    session.add(run)
    session.flush()
    return run


def _hero(session: Session) -> Character:
    """Create the minimal persistent contributor without bypassing foreign keys."""
    from app.models import Player

    existing = session.scalar(select(Character))
    if existing is not None:
        return existing
    player = Player(auth_user_id=uuid.uuid4(), created_at=NOW)
    session.add(player)
    session.flush()
    hero = Character(
        player_id=player.id,
        name="Project Hero",
        name_normalized="project hero",
        current_realm_id=REALM,
        home_estate_id=uuid.uuid4(),
        created_at=NOW,
    )
    session.add(hero)
    session.flush()
    session.add(
        Estate(
            id=hero.home_estate_id,
            owner_character_id=hero.id,
            realm_id=REALM,
            form_id=CONTENT.estate_forms[0].id,
            upgrade_slots=1,
        )
    )
    session.add(Currency(character_id=hero.id, gold=100))
    session.flush()
    return hero


@pytest.mark.parametrize(
    "code",
    [
        "NOT_PRESENT",
        "RESIDENTS_ONLY",
        "PROJECT_NOT_OFFERED",
        "PROJECT_ACTIVE",
        "REALM_VOTING",
        "REALM_TRANSITIONING",
        "PROJECT_COOLDOWN",
        "KICKOFF_LIMIT",
        "MISSING_INPUTS",
    ],
)
def test_kickoff_codes_in_order(realm_session: Session, code: str) -> None:
    """Each gate wins over the later missing-payment gate."""
    session = realm_session
    realm = session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(session)
    project = CONTENT.project(PROJECT).model_copy(
        update={"kickoff": ProjectKickoff(gold=1000, who="residents")}
    )
    content = _content(project)
    if code == "NOT_PRESENT":
        hero.current_realm_id = "realm.ashen_reach"
    elif code == "RESIDENTS_ONLY":
        estate = session.get(Estate, hero.home_estate_id)
        assert estate is not None
        estate.realm_id = "realm.ashen_reach"
    elif code == "PROJECT_NOT_OFFERED":
        push_realm_tag(session, realm, project.grants_tag, NOW)
    elif code == "PROJECT_ACTIVE":
        _run(session, realm)
    elif code == "REALM_TRANSITIONING":
        start_transition(realm, "node.verdant_t2", "upgrade", NOW, content)
    elif code == "PROJECT_COOLDOWN":
        run = _run(session, realm)
        run.status, run.failed_at = "failed", NOW
        hero.last_kickoff_at = NOW
    elif code == "KICKOFF_LIMIT":
        hero.last_kickoff_at = NOW
    with (
        patch(
            "app.services.projects.has_open_vote", return_value=code == "REALM_VOTING"
        ),
        pytest.raises(HTTPException) as error,
    ):
        kickoff(session, hero, realm, PROJECT, NOW, content)
    assert _code(error.value) == code
    assert session.get(Currency, hero.id).gold == 100  # type: ignore[union-attr]
    assert realm.treasury == 0


@pytest.mark.parametrize("reason", ["node", "prerequisite", "held"])
def test_project_offering_rules(realm_session: Session, reason: str) -> None:
    """Node offering, prerequisites and already-held tags independently gate kickoff."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(realm_session)
    content = CONTENT
    if reason == "node":
        realm.current_node_id = "node.ashen_t1"
    elif reason == "prerequisite":
        content = _content(
            CONTENT.project(PROJECT).model_copy(
                update={"requires_tags": ("access.fake",)}
            )
        )
    else:
        push_realm_tag(realm_session, realm, "bonus.fake", NOW)
    with pytest.raises(HTTPException) as error:
        kickoff(realm_session, hero, realm, PROJECT, NOW, content)
    assert _code(error.value) == "PROJECT_NOT_OFFERED"


def test_kickoff_selector_payment_and_gold_conservation(realm_session: Session) -> None:
    """Payment moves gold, consumes goods, and avoids double spending."""
    session = realm_session
    realm = session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(session)
    session.add(Inventory(character_id=hero.id, item_id="item.demo_crate", quantity=10))
    line = ActionInput(selector=Selector(item="item.demo_crate"), quantity=6)
    project = CONTENT.project(PROJECT).model_copy(
        update={"kickoff": ProjectKickoff(gold=25, goods=(line, line), who="anyone")}
    )
    with pytest.raises(HTTPException):
        kickoff(session, hero, realm, PROJECT, NOW, _content(project))
    currency = session.get(Currency, hero.id)
    stack = session.get(Inventory, (hero.id, "item.demo_crate"))
    assert currency is not None and stack is not None
    assert (currency.gold, realm.treasury, stack.quantity) == (100, 0, 10)
    project = project.model_copy(
        update={"kickoff": ProjectKickoff(gold=25, goods=(line,), who="anyone")}
    )
    kickoff(session, hero, realm, PROJECT, NOW, _content(project))
    assert (currency.gold, realm.treasury, stack.quantity) == (75, 25, 4)
    assert _as_utc(hero.last_kickoff_at) == NOW  # type: ignore[arg-type]


def test_daily_kickoff_limit_across_realms(realm_session: Session) -> None:
    """The rolling day is character-wide and permits kickoff at exactly 24 hours."""
    session = realm_session
    realm = session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(session)
    kickoff(session, hero, realm, PROJECT, NOW, CONTENT)
    second = RealmState(
        id="realm.ashen_reach",
        template_id="realm.ashen_reach",
        current_node_id="node.ashen_t1",
        last_tick_at=NOW,
    )
    session.add(second)
    session.flush()
    hero.current_realm_id = second.id
    for hours in [0, 23.999]:
        with pytest.raises(HTTPException) as error:
            kickoff(
                session,
                hero,
                second,
                "project.ashen_placeholder",
                NOW + timedelta(hours=hours),
                CONTENT,
            )
        assert _code(error.value) == "KICKOFF_LIMIT"
    assert (
        kickoff(
            session,
            hero,
            second,
            "project.ashen_placeholder",
            NOW + timedelta(days=1),
            CONTENT,
        ).status
        == "funding"
    )


@pytest.mark.anyio
async def test_contribute_presence_clamping_and_credits(
    action_client: ApiFixture,
) -> None:
    """Visitors may fund; consumed goods equal logged payments."""
    client, factory, clock, headers = action_client
    url = f"/realms/{REALM}"
    started = await client.post(f"{url}/projects/{PROJECT}/kickoff", headers=headers)
    assert started.status_code == 200
    with factory() as session:
        hero = session.scalar(select(Character))
        assert hero is not None
        hero_id = hero.id
        estate = session.get(Estate, hero.home_estate_id)
        assert estate is not None
        estate.realm_id = "realm.ashen_reach"
        for item, quantity in [("item.demo_crate", 120), ("item.cardboard_badge", 30)]:
            session.add(
                Inventory(character_id=hero.id, item_id=item, quantity=quantity)
            )
        hero.current_realm_id = "realm.ashen_reach"
        session.commit()
    body = {"item_id": "item.demo_crate", "quantity": 110}
    absent = await client.post(f"{url}/project/contribute", headers=headers, json=body)
    assert absent.json()["error"]["code"] == "NOT_PRESENT"
    with factory() as session:
        hero = session.get(Character, hero_id)
        assert hero is not None
        hero.current_realm_id = REALM
        session.commit()
    for item in ["item.demo_crate", "item.cardboard_badge"]:
        result = await client.post(
            f"{url}/project/contribute",
            headers=headers,
            json={"item_id": item, "quantity": 1000},
        )
        assert result.status_code == 200
    assert result.json()["status"] == "building"
    with factory() as session:
        assert session.get(Inventory, (hero_id, "item.demo_crate")).quantity == 20  # type: ignore[union-attr]
        assert session.get(Inventory, (hero_id, "item.cardboard_badge")).quantity == 5  # type: ignore[union-attr]
        assert sum(session.scalars(select(RealmContribution.quantity_milli))) == 125000
    clock.advance(timedelta(seconds=60))
    detail = (await client.get(url, headers=headers)).json()
    assert detail["active_run"] is None
    assert "treasury" not in detail
    credits = (await client.get(f"{url}/tags/bonus.fake", headers=headers)).json()
    assert credits["kicked_off_by"] == str(hero_id)
    assert credits["contributions"] == {str(hero_id): 125}
    assert credits["realm_share"] == 0


def test_build_exact_due_time_before_ticks_and_transition(
    realm_session: Session,
) -> None:
    """Late resolution completes builds at their due time before ticks."""
    session = realm_session
    realm = session.get(RealmState, REALM)
    assert realm is not None
    run = _run(session, realm)
    run.status, run.build_completes_at = "building", NOW + timedelta(minutes=1)
    start_transition(realm, "node.verdant_t2", "upgrade", NOW, CONTENT)
    due = NOW + timedelta(days=8)
    seen = []

    def tick(
        session: Session, realm: RealmState, now: datetime, content: ContentIndex
    ) -> None:
        seen.append((run.status, realm.current_node_id))

    with patch.object(realm_ticks, "TICK_STEPS", (tick,)):
        finalize_realm(session, REALM, due, CONTENT)
    tag = session.get(RealmTag, (REALM, "bonus.fake"))
    assert tag is not None and _as_utc(tag.acquired_at) == NOW + timedelta(minutes=1)
    assert tag.node_id == "node.verdant_t1" and tag.project_run_id == run.id
    assert seen == [("complete", "node.verdant_t2")] * 72


def test_erosion_failure_cooldown_and_reset(realm_session: Session) -> None:
    """Erosion respects grace and payment resets, then fails with a cooldown."""
    session = realm_session
    realm = session.get(RealmState, REALM)
    assert realm is not None
    run = _run(session, realm)
    resolve_realm(session, realm, NOW + timedelta(days=2), CONTENT)
    assert run.contributed == [50000, 12500]
    resolve_realm(session, realm, NOW + timedelta(days=3), CONTENT)
    assert run.contributed == [30000, 7500]
    # A realm payment also resets the clock; it is recorded under null identity.
    contribute(
        session,
        realm,
        run,
        "item.demo_crate",
        1000,
        None,
        NOW + timedelta(days=3),
        CONTENT,
    )
    resolve_realm(session, realm, NOW + timedelta(days=5), CONTENT)
    assert run.contributed == [31000, 7500]
    for day in [6, 7]:
        resolve_realm(session, realm, NOW + timedelta(days=day), CONTENT)
    assert run.status == "failed" and run.contributed == [0, 0]
    assert run.failed_at is not None
    failed_at = _as_utc(run.failed_at)
    with pytest.raises(HTTPException) as error:
        kickoff(
            session,
            _hero(session),
            realm,
            PROJECT,
            failed_at + timedelta(hours=35),
            CONTENT,
        )
    assert _code(error.value) == "PROJECT_COOLDOWN"
    assert (
        kickoff(
            session,
            _hero(session),
            realm,
            PROJECT,
            failed_at + timedelta(hours=36),
            CONTENT,
        ).status
        == "funding"
    )


def test_resolve_realm_idempotence_and_bounded_catchup(realm_session: Session) -> None:
    """Catch-up is bounded; repeating a caught-up resolution does nothing."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    run = _run(realm_session, realm)
    due = NOW + timedelta(hours=200, minutes=30)
    for hours in [72, 144, 200, 200]:
        resolve_realm(realm_session, realm, due, CONTENT)
        assert _as_utc(realm.last_tick_at) == NOW + timedelta(hours=hours)
    before = (run.status, list(run.contributed), run.failed_at)
    resolve_realm(realm_session, realm, due, CONTENT)
    assert (run.status, run.contributed, run.failed_at) == before


@settings(derandomize=True)
@given(
    required=st.integers(min_value=1, max_value=100000),
    ticks=st.integers(min_value=1, max_value=24),
)
def test_erosion_rounding_conserves_daily_rate(required: int, ticks: int) -> None:
    """Fractional tick shares sum to the exact cumulative daily percentage."""
    held = [required * 1000]
    for index in range(ticks):
        held = erode_project(
            [required * 1000],
            held,
            NOW,
            NOW + timedelta(days=2, hours=index + 1),
            CONTENT.economy.project,
            24,
        )
    assert held == [required * 1000 - required * 1000 * ticks // 120]


def test_postgres_two_kickoffs_one_active_run(realm_session: Session) -> None:
    """Competing characters serialize on the realm and only the winner pays."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text
    from test_estates import _wait_for_postgres_blocker

    from app.models import Player
    from app.services.actions import resolve_character

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    first_hero = _hero(realm_session)
    player = Player(auth_user_id=uuid.uuid4(), created_at=NOW)
    realm_session.add(player)
    realm_session.flush()
    second_hero = Character(
        player_id=player.id,
        name="Second Hero",
        name_normalized="second hero",
        current_realm_id=REALM,
        home_estate_id=uuid.uuid4(),
        created_at=NOW,
    )
    realm_session.add(second_hero)
    realm_session.flush()
    realm_session.add(
        Estate(
            id=second_hero.home_estate_id,
            owner_character_id=second_hero.id,
            realm_id=REALM,
            form_id=CONTENT.estate_forms[0].id,
            upgrade_slots=1,
        )
    )
    realm_session.add(Currency(character_id=second_hero.id, gold=100))
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    ready = threading.Event()
    worker_pid: list[int] = []

    def second_kickoff() -> str:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            worker_pid.append(session.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            resolve_character(session, second_hero.id, NOW, CONTENT)
            hero = session.get(Character, second_hero.id)
            realm = session.get(RealmState, REALM)
            assert hero is not None and realm is not None
            try:
                kickoff(session, hero, realm, PROJECT, NOW, CONTENT)
            except HTTPException as error:
                return _code(error)
            session.commit()
            return "started"

    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        blocker_pid = first.scalar(text("SELECT pg_backend_pid()"))
        assert isinstance(blocker_pid, int)
        resolve_character(first, first_hero.id, NOW, CONTENT)
        hero = first.get(Character, first_hero.id)
        realm = first.get(RealmState, REALM)
        assert hero is not None and realm is not None
        kickoff(first, hero, realm, PROJECT, NOW, CONTENT)
        future = pool.submit(second_kickoff)
        try:
            assert ready.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pid[0], blocker_pid)
            assert not future.done()
        finally:
            first.commit()
        assert future.result(timeout=10) == "PROJECT_ACTIVE"
    realm_session.expire_all()
    assert len(list(realm_session.scalars(select(RealmProjectRun)))) == 1
    loser = realm_session.get(Character, second_hero.id)
    assert loser is not None and loser.last_kickoff_at is None


@settings(
    max_examples=25,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    held=st.integers(min_value=1, max_value=200),
    requested=st.integers(min_value=1, max_value=300),
)
def test_contribution_clamping_conserves_items(
    realm_session: Session, held: int, requested: int
) -> None:
    """Inventory loss equals the immutable credit, clamped by stock and remainder."""
    from app.services.projects import contribute_character

    realm_session.rollback()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(realm_session)
    run = _run(realm_session, realm)
    realm_session.add(
        Inventory(character_id=hero.id, item_id="item.demo_crate", quantity=held)
    )
    contribute_character(
        realm_session, hero, realm, "item.demo_crate", requested, NOW, CONTENT
    )
    realm_session.flush()
    stack = realm_session.get(Inventory, (hero.id, "item.demo_crate"))
    remaining = stack.quantity if stack else 0
    credit = realm_session.scalar(select(RealmContribution))
    assert credit is not None
    assert held - remaining == min(held, requested, 50) == credit.quantity_milli // 1000
    assert run.contributed[0] == 50000 + credit.quantity_milli
    realm_session.rollback()


def test_build_completes_at_exact_boundary(realm_session: Session) -> None:
    """The tag is absent one microsecond before completion and present exactly then."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    run = _run(realm_session, realm)
    run.status, run.build_completes_at = "building", NOW + timedelta(seconds=60)
    resolve_realm(
        realm_session, realm, NOW + timedelta(seconds=60, microseconds=-1), CONTENT
    )
    assert realm_session.get(RealmTag, (REALM, "bonus.fake")) is None
    resolve_realm(realm_session, realm, NOW + timedelta(seconds=60), CONTENT)
    tag = realm_session.get(RealmTag, (REALM, "bonus.fake"))
    assert tag is not None and tag.project_run_id == run.id
    assert run.status == "complete"


@pytest.mark.anyio
async def test_character_resolution_finishes_build_and_realm_credits(
    action_client: ApiFixture,
) -> None:
    """Character reads resolve builds; credits include realm goods."""
    client, factory, clock, headers = action_client
    response = await client.post(
        f"/realms/{REALM}/projects/{PROJECT}/kickoff", headers=headers
    )
    assert response.status_code == 200
    with factory() as session:
        realm = session.get(RealmState, REALM)
        run = session.scalar(select(RealmProjectRun))
        assert realm is not None and run is not None
        for item, quantity in [
            ("item.demo_crate", 100000),
            ("item.cardboard_badge", 25000),
        ]:
            contribute(session, realm, run, item, quantity, None, clock.now, CONTENT)
        session.commit()
    clock.advance(timedelta(seconds=60))
    profile = await client.get("/characters/me", headers=headers)
    assert profile.status_code == 200
    with factory() as session:
        assert session.scalar(select(RealmProjectRun.status)) == "complete"
    credits = (
        await client.get(f"/realms/{REALM}/tags/bonus.fake", headers=headers)
    ).json()
    assert credits["realm_share"] == 125 and credits["contributions"] == {}


@settings(
    max_examples=20,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    hours=st.integers(min_value=1, max_value=72),
    split=st.integers(min_value=0, max_value=72),
)
def test_realm_resolution_split_equals_single(
    realm_session: Session, hours: int, split: int
) -> None:
    """Within the catch-up bound, splitting and repeating resolution preserve state."""
    snapshots = []
    for boundaries in [[hours], [min(split, hours), hours, hours]]:
        realm_session.rollback()
        realm = realm_session.get(RealmState, REALM)
        assert realm is not None
        run = _run(realm_session, realm)
        for boundary in boundaries:
            resolve_realm(
                realm_session, realm, NOW + timedelta(hours=boundary), CONTENT
            )
        snapshots.append(
            (
                run.status,
                list(run.contributed),
                run.failed_at,
                _as_utc(realm.last_tick_at),
            )
        )
    assert snapshots[0] == snapshots[1]
    realm_session.rollback()


@pytest.mark.anyio
async def test_project_reads_and_contribution_errors(action_client: ApiFixture) -> None:
    """Snapshots expose stall and reset; invalid payments consume nothing."""
    client, factory, clock, headers = action_client
    url = f"/realms/{REALM}"
    assert (
        await client.post(f"{url}/projects/{PROJECT}/kickoff", headers=headers)
    ).status_code == 200
    for body in [
        {"item_id": "item.demo_crate", "quantity": 0},
        {"item_id": "item.demo_crate", "quantity": 1.5},
    ]:
        assert (
            await client.post(f"{url}/project/contribute", headers=headers, json=body)
        ).status_code == 422
    clock.advance(timedelta(hours=1))
    snapshot = (await client.get(url, headers=headers)).json()["active_run"]
    assert snapshot["stalled"] and snapshot["status"] == "funding"
    assert snapshot["contributed"] == [0, 0]
    assert snapshot["required"][0] == {
        "selector": {"item": "item.demo_crate"},
        "quantity": 100,
    }
    with factory() as session:
        hero = session.scalar(select(Character))
        assert hero is not None
        for item in ["item.demo_crate", "item.prototype_widget"]:
            session.add(Inventory(character_id=hero.id, item_id=item, quantity=10))
        session.commit()
    result = await client.post(
        f"{url}/project/contribute",
        headers=headers,
        json={"item_id": "item.prototype_widget", "quantity": 5},
    )
    assert result.json()["error"]["code"] == "PROJECT_ITEM_NOT_NEEDED"
    result = await client.post(
        f"{url}/project/contribute",
        headers=headers,
        json={"item_id": "item.cardboard_badge", "quantity": 5},
    )
    assert result.json()["error"]["code"] == "MISSING_INPUTS"
    result = await client.post(
        f"{url}/project/contribute",
        headers=headers,
        json={"item_id": "item.demo_crate", "quantity": 5},
    )
    assert result.status_code == 200 and not result.json()["stalled"]
    assert result.json()["contributed"] == [5, 0]
    unknown = await client.post(
        "/realms/unknown/projects/unknown/kickoff", headers=headers
    )
    assert unknown.json()["error"]["code"] == "UNKNOWN_REALM"
    absent = await client.post(
        "/realms/realm.ashen_reach/projects/unknown/kickoff", headers=headers
    )
    assert absent.json()["error"]["code"] == "NOT_PRESENT"


def test_fractional_remainder_consumes_one_whole_player_good(
    realm_session: Session,
) -> None:
    """Whole payments round up fractional remainders and log consumption."""
    from app.services.projects import contribute_character

    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    run = _run(realm_session, realm)
    run.contributed = [99500, 25000]
    hero = _hero(realm_session)
    realm_session.add(
        Inventory(character_id=hero.id, item_id="item.demo_crate", quantity=3)
    )
    contribute_character(realm_session, hero, realm, "item.demo_crate", 3, NOW, CONTENT)
    realm_session.flush()
    assert run.contributed == [100000, 25000] and run.status == "building"
    assert realm_session.get(Inventory, (hero.id, "item.demo_crate")).quantity == 2  # type: ignore[union-attr]
    assert realm_session.scalar(select(RealmContribution.quantity_milli)) == 1000
