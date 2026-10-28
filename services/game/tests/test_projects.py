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
from sqlalchemy import delete, event, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.interfaces import ExecutionContext
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock
from test_actions import action_client as action_client
from test_actions import anyio_backend as anyio_backend
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.content.loader import ContentIndex
from app.content.schemas import (
    ActionInput,
    Project,
    ProjectKickoff,
    Selector,
    TagUpkeep,
)
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
    as_utc,
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
        stance=CONTENT.progression.default_stance,
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
        )
    )
    session.add(Currency(character_id=hero.id, gold=100))
    session.flush()
    return hero


KICKOFF_CODES = (
    "NOT_PRESENT",
    "RESIDENTS_ONLY",
    "PROJECT_NOT_OFFERED",
    "PROJECT_ACTIVE",
    "REALM_VOTING",
    "REALM_TRANSITIONING",
    "PROJECT_COOLDOWN",
    "KICKOFF_LIMIT",
    "MISSING_INPUTS",
)


@pytest.mark.parametrize("code", KICKOFF_CODES)
def test_kickoff_codes_in_order(realm_session: Session, code: str) -> None:
    """Each gate wins while every later gate also rejects the kickoff."""
    session = realm_session
    realm = session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(session)
    blocked = set(KICKOFF_CODES[KICKOFF_CODES.index(code) :])
    project = CONTENT.project(PROJECT).model_copy(
        update={"kickoff": ProjectKickoff(gold=1000, who="residents")}
    )
    content = _content(project)
    if "NOT_PRESENT" in blocked:
        hero.current_realm_id = "realm.ashen_reach"
    if "RESIDENTS_ONLY" in blocked:
        estate = session.get(Estate, hero.home_estate_id)
        assert estate is not None
        estate.realm_id = "realm.ashen_reach"
    if "PROJECT_NOT_OFFERED" in blocked:
        push_realm_tag(session, realm, project.grants_tag, NOW)
    if "PROJECT_COOLDOWN" in blocked:
        failed = _run(session, realm)
        failed.status, failed.failed_at = "failed", NOW
        session.flush()
    if "PROJECT_ACTIVE" in blocked:
        _run(session, realm)
    if "REALM_TRANSITIONING" in blocked:
        start_transition(realm, "node.verdant_t2", "upgrade", NOW, content)
    if "KICKOFF_LIMIT" in blocked:
        hero.last_kickoff_at = NOW
    with (
        patch(
            "app.services.projects.has_open_vote",
            return_value="REALM_VOTING" in blocked,
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
    assert as_utc(hero.last_kickoff_at) == NOW  # type: ignore[arg-type]


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
        context: realm_ticks.RealmTickContext,
        realm: RealmState,
        now: datetime,
        content: ContentIndex,
    ) -> None:
        seen.append((run.status, realm.current_node_id))

    with patch.object(realm_ticks, "TICK_STEPS", (tick,)):
        finalize_realm(session, REALM, due, CONTENT)
    tag = session.get(RealmTag, (REALM, "bonus.fake"))
    assert tag is not None and as_utc(tag.acquired_at) == NOW + timedelta(minutes=1)
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
    failed_at = as_utc(run.failed_at)
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
        assert as_utc(realm.last_tick_at) == NOW + timedelta(hours=hours)
    before = (run.status, list(run.contributed), run.failed_at)
    resolve_realm(realm_session, realm, due, CONTENT)
    assert (run.status, run.contributed, run.failed_at) == before


@pytest.mark.parametrize("ticks", [2, CONTENT.economy.tick.max_catchup])
@pytest.mark.parametrize("paying", [False, True])
@pytest.mark.parametrize("decaying", [False, True])
def test_realm_catchup_statement_bound(
    realm_session: Session, ticks: int, paying: bool, decaying: bool
) -> None:
    """Catch-up loads and writes once, independent of the tick count."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    # Keep a node line after project failure, so both writes have the same shape.
    node = CONTENT.development_node(realm.current_node_id).model_copy(
        update={
            "upkeep": (TagUpkeep(selector=Selector(item="item.fake_sprig"), per_day=1),)
        }
    )
    content = replace(
        CONTENT, _nodes_by_id=MappingProxyType({**CONTENT._nodes_by_id, node.id: node})
    )
    run = _run(realm_session, realm)
    if paying:
        from app.models import RealmStore

        for raw in run.required:
            realm_session.add(
                RealmStore(
                    realm_id=REALM,
                    item_id=raw["selector"]["item"],
                    quantity_milli=10000000,
                )
            )

    if decaying:
        from app.models import EstateLarder, EstateUpgrade

        form = content.estate_form("form.fake_workshop").model_copy(
            update={"production": ()}
        )
        content = replace(
            content,
            _forms_by_id=MappingProxyType(
                {
                    **content._forms_by_id,
                    form.id: form,
                }
            ),
        )
        doomed = Estate(
            id=uuid.uuid4(),
            realm_id=REALM,
            form_id=form.id,
            gauge=10,
            shed_progress=2,
            decay_stage="failing",
        )
        realm_session.add(doomed)
        realm_session.flush()
        realm_session.add_all(
            [
                EstateUpgrade(
                    estate_id=doomed.id,
                    slot_index=slot,
                    upgrade_id=content.upgrades[0].id,
                    purchased_at=NOW,
                )
                for slot in range(2)
            ]
        )
        realm_session.add(
            EstateLarder(
                estate_id=doomed.id, item_id="item.fake_plank", quantity_milli=1000
            )
        )
    interval = timedelta(days=1) / CONTENT.economy.tick.per_day
    # Start after grace so both resolutions must persist eroded progress.
    realm.last_tick_at = NOW + timedelta(days=CONTENT.economy.project.idle_grace_days)
    realm_session.flush()
    due = as_utc(realm.last_tick_at) + ticks * interval
    statements: list[str] = []

    def record_statement(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    engine = realm_session.get_bind()
    assert isinstance(engine, Engine)
    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        resolve_realm(realm_session, realm, due, content)
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)
    # Open-ballot and preloaded-shipment queries are independent of tick count.
    # A destroyed estate, batched upgrade losses and a lost larder add three
    # writes total, equally for two ticks and full catch-up.
    assert len(statements) == (16 if paying else 14) + (3 if decaying else 0), (
        statements
    )
    if decaying:
        assert doomed.status == "destroyed" and doomed.owner_character_id is None
        assert realm_session.get(EstateLarder, (doomed.id, "item.fake_plank")) is None
        assert (
            list(
                realm_session.scalars(
                    select(EstateUpgrade).where(EstateUpgrade.estate_id == doomed.id)
                )
            )
            == []
        )
    if paying:
        assert run.contributed[0] > 50000
        assert list(realm_session.scalars(select(RealmContribution)))
    if not paying and ticks == content.economy.tick.max_catchup:
        assert run.status == "failed"
        assert run.failed_at is not None
        assert as_utc(run.failed_at) == NOW + timedelta(days=4, hours=12)
    assert as_utc(realm.last_tick_at) == due
    if not paying:
        assert run.contributed[0] < 50000
    # Verify the final flush persisted the computed state.
    snapshot = (
        run.status,
        list(run.contributed),
        as_utc(run.failed_at) if run.failed_at else None,
    )
    realm_session.expire_all()
    assert (
        run.status,
        run.contributed,
        as_utc(run.failed_at) if run.failed_at else None,
    ) == snapshot
    assert as_utc(realm.last_tick_at) == due


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
        stance=CONTENT.progression.default_stance,
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
    deadline=None,
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
    deadline=None,
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
                as_utc(realm.last_tick_at),
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
    assert not snapshot["stalled"] and snapshot["status"] == "funding"
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


def test_isolated_project_erodes_and_fails(realm_session: Session) -> None:
    """Tutorial instances use ordinary project erosion despite their decay exemption."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    realm.isolated = True
    run = _run(realm_session, realm)
    resolve_realm(realm_session, realm, NOW + timedelta(days=2), CONTENT)
    assert run.contributed == [50000, 12500] and run.status == "funding"
    resolve_realm(realm_session, realm, NOW + timedelta(days=3), CONTENT)
    assert run.contributed == [30000, 7500] and run.status == "funding"
    due = NOW + timedelta(days=4, hours=12)
    resolve_realm(realm_session, realm, due, CONTENT)
    assert run.contributed == [0, 0] and run.status == "failed"
    assert run.failed_at is not None and as_utc(run.failed_at) == due
    assert as_utc(realm.last_tick_at) == due


@pytest.mark.anyio
async def test_stalled_uses_content_grace_and_resets(action_client: ApiFixture) -> None:
    """Stalling starts strictly after the authored grace, and payment resets it."""
    from app.main import app

    client, factory, clock, headers = action_client
    content = replace(
        CONTENT,
        economy=CONTENT.economy.model_copy(
            update={
                "project": CONTENT.economy.project.model_copy(
                    update={"idle_grace_days": 0.25}
                ),
            }
        ),
    )
    with factory() as session:
        realm = session.get(RealmState, REALM)
        assert realm is not None
        run = _run(session, realm, clock.now)
        hero = _hero(session)
        session.add(
            Inventory(character_id=hero.id, item_id="item.demo_crate", quantity=5)
        )
        run_id = run.id
        born = clock.now
        session.commit()
    url = f"/realms/{REALM}"
    with patch.object(app.state, "content", content):
        for offset, stalled in [(-1, False), (0, False), (1, True)]:
            clock.now = born + timedelta(hours=6, microseconds=offset)
            response = await client.get(url, headers=headers)
            assert response.status_code == 200
            assert response.json()["active_run"]["stalled"] is stalled
        response = await client.post(
            f"{url}/project/contribute",
            headers=headers,
            json={"item_id": "item.demo_crate", "quantity": 1},
        )
        assert response.status_code == 200 and not response.json()["stalled"]
        with factory() as session:
            loaded_run = session.get(RealmProjectRun, run_id)
            assert loaded_run is not None
            loaded_run.status = "building"
            loaded_run.last_contribution_at = born
            loaded_run.build_completes_at = clock.now + timedelta(days=1)
            session.commit()
        response = await client.get(url, headers=headers)
        assert response.json()["active_run"]["status"] == "building"
        assert not response.json()["active_run"]["stalled"]


@pytest.mark.anyio
async def test_tag_credits_realm_errors_and_typed_response(
    action_client: ApiFixture,
) -> None:
    """Unknown realms differ from missing tags, and successful credits have a schema."""
    from app.main import app

    client, factory, _, headers = action_client
    unknown = await client.get("/realms/unknown/tags/bonus.fake", headers=headers)
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "UNKNOWN_REALM"
    missing = await client.get(f"/realms/{REALM}/tags/bonus.fake", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "UNKNOWN_REALM_TAG"
    with factory() as session:
        realm = session.get(RealmState, REALM)
        assert realm is not None
        push_realm_tag(session, realm, "bonus.fake", NOW)
        session.commit()
    response = await client.get(f"/realms/{REALM}/tags/bonus.fake", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "tag_id": "bonus.fake",
        "project_run_id": None,
        "kicked_off_by": None,
        "contributions": {},
        "realm_share": 0,
    }
    schema = app.openapi()["paths"]["/realms/{realm_id}/tags/{tag_id}"]["get"][
        "responses"
    ]["200"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/TagCreditsResponse"}


@pytest.mark.parametrize("isolated", [False, True])
def test_first_touch_never_instantiates_isolated_template(
    realm_session: Session, isolated: bool
) -> None:
    """Only world templates may become shared rows through first-touch resolution."""
    template = CONTENT.realm("realm.ashen_reach").model_copy(
        update={"isolated": isolated}
    )
    content = replace(
        CONTENT,
        _realms_by_id=MappingProxyType(
            {r.id: template if r.id == template.id else r for r in CONTENT.realms}
        ),
    )
    # A virgin world must contain no legacy realm rows before seeding.
    realm_session.execute(delete(RealmState))
    state = finalize_realm(realm_session, template.id, NOW, content)
    realm_session.flush()
    if isolated:
        assert state is None and realm_session.get(RealmState, template.id) is None
    else:
        assert state is not None and state.template_id == template.id


@pytest.mark.anyio
async def test_kickoff_availability_reports_gates_without_payment(
    action_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Availability shares mutation gates and never consumes kickoff holdings."""
    from app.main import app
    from app.models import RealmStore
    from app.services.stores import derive_realm_lines

    client, factory, clock, headers = action_client
    project = app.state.content.project(PROJECT)
    monkeypatch.setattr(
        app.state,
        "content",
        _content(
            project.model_copy(
                update={"kickoff": project.kickoff.model_copy(update={"gold": 1})}
            )
        ),
    )
    url = f"/realms/{REALM}/projects/availability"
    with factory() as session:
        hero = session.scalar(select(Character))
        assert hero is not None
        hero_id = hero.id
        realm = session.get(RealmState, REALM)
        assert realm is not None
        node = app.state.content.development_node(realm.current_node_id)
        node = node.model_copy(
            update={
                "upkeep": (
                    TagUpkeep(selector=Selector(item="item.fake_sprig"), per_day=1),
                )
            }
        )
        monkeypatch.setattr(
            app.state,
            "content",
            replace(
                app.state.content,
                _nodes_by_id=MappingProxyType(
                    {**app.state.content._nodes_by_id, node.id: node}
                ),
            ),
        )
        session.add(
            RealmStore(
                realm_id=REALM, item_id="item.fake_sprig", quantity_milli=1000000
            )
        )
        session.add(
            Inventory(character_id=hero_id, item_id="item.fake_sprig", quantity=7)
        )
        wallet = session.get(Currency, hero_id)
        assert wallet is not None
        wallet.gold = 10
        gold = wallet.gold
        session.commit()
    response = await client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.json()[PROJECT] is None
    with factory() as session:
        wallet = session.get(Currency, hero_id)
        assert wallet is not None and wallet.gold == gold
        assert session.scalar(select(RealmProjectRun)) is None
        realm = session.get(RealmState, REALM)
        assert realm is not None
        line = derive_realm_lines(session, realm, app.state.content)[0]
        for stock in session.scalars(
            select(RealmStore).where(RealmStore.realm_id == REALM)
        ):
            if line.selector.matches(app.state.content.item(stock.item_id)):
                stock.quantity_milli = 0
        session.commit()
        inventory_before = {
            row.item_id: row.quantity
            for row in session.scalars(
                select(Inventory).where(Inventory.character_id == hero_id)
            )
        }
        run_count_before = len(list(session.scalars(select(RealmProjectRun))))
    short = await client.get(url, headers=headers)
    assert short.json()[PROJECT]["code"] == "RESERVE_SHORT"
    with factory() as session:
        wallet = session.get(Currency, hero_id)
        assert wallet is not None and wallet.gold == gold
        assert {
            row.item_id: row.quantity
            for row in session.scalars(
                select(Inventory).where(Inventory.character_id == hero_id)
            )
        } == inventory_before
        assert len(list(session.scalars(select(RealmProjectRun)))) == run_count_before
        for stock in session.scalars(
            select(RealmStore).where(RealmStore.realm_id == REALM)
        ):
            stock.quantity_milli = 1000000
        wallet.gold = 0
        session.commit()
    unavailable = await client.get(url, headers=headers)
    assert unavailable.json()[PROJECT]["code"] == "MISSING_INPUTS"
    with factory() as session:
        hero = session.get(Character, hero_id)
        assert hero is not None
        hero.last_kickoff_at = clock.now
        session.commit()
    limited = await client.get(url, headers=headers)
    assert limited.json()[PROJECT]["code"] == "KICKOFF_LIMIT"
    missing = await client.get("/realms/unknown/projects/availability", headers=headers)
    assert missing.json()["error"]["code"] == "UNKNOWN_REALM"
