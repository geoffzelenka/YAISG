"""Realm eating order, conservation, batching, and scheduled liveness."""

import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from types import MappingProxyType
from unittest.mock import Mock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.content.loader import ContentIndex
from app.content.schemas import ProductionItem, Selector, TagUpkeep
from app.engine.realm_ticks import shares
from app.models import (
    Estate,
    EstateLarder,
    RealmContribution,
    RealmLine,
    RealmProjectRun,
    RealmState,
    RealmStore,
    RealmTag,
)
from app.services.realm_ticks import (
    RealmTickContext,
    load_context,
    step_1_production,
    step_2_larder_upkeep,
    step_3_estate_upkeep,
    step_4_realm_upkeep,
    step_6_spoilage,
    step_7_caps,
    step_10_lines,
)
from app.services.realms import as_utc, resolve_realm
from app.services.scheduler import run_realm_ticks, start_scheduler

REALM = "realm.verdant_vale"
ITEM = "item.fake_sprig"
FORM = "form.fake_workshop"


def tick_content() -> ContentIndex:
    """Use one daily tick and a one-day reserve for readable golden amounts."""
    upkeep = (TagUpkeep(selector=Selector(item=ITEM), per_day=2),)
    form = CONTENT.estate_form(FORM).model_copy(
        update={"upkeep": upkeep, "production": ()}
    )
    node = CONTENT.development_node("node.verdant_t1").model_copy(
        update={
            "upkeep": upkeep,
            "inherent_tags": (),
            "reserve_days": 1.0,
            "cap_days": 10.0,
        }
    )
    return replace(
        CONTENT,
        economy=CONTENT.economy.model_copy(
            update={"tick": CONTENT.economy.tick.model_copy(update={"per_day": 1})}
        ),
        _forms_by_id=MappingProxyType({**CONTENT._forms_by_id, FORM: form}),
        _nodes_by_id=MappingProxyType({**CONTENT._nodes_by_id, node.id: node}),
    )


def estate(session: Session) -> Estate:
    """Create a realm-owned producer without a player."""
    result = Estate(id=uuid.uuid4(), realm_id=REALM, form_id=FORM)
    session.add(result)
    session.flush()
    return result


def test_golden_reserve_estates_first_then_realm(realm_session: Session) -> None:
    """Above reserve estates eat first; only realm upkeep may cross reserve."""
    content = tick_content()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    e = estate(realm_session)
    realm_session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=9000))
    realm_session.add(EstateLarder(estate_id=e.id, item_id=ITEM, quantity_milli=1000))
    realm_session.flush()
    context = load_context(realm_session, realm, None, content)
    snapshots = []
    for day in range(1, 4):
        now = NOW + timedelta(days=day)
        step_2_larder_upkeep(context, realm, now, content)
        step_3_estate_upkeep(context, realm, now, content)
        step_4_realm_upkeep(context, realm, now, content)
        snapshots.append(
            (
                context.stores[ITEM],
                list(context.owed.values())[0][0][1],
                sum(context.realm_unmet.values()),
            )
        )
        step_10_lines(context, realm, now, content)
    assert snapshots == [(6000, 0, 0), (2000, 0, 0), (0, 2000, 0)]
    assert context.larders[e.id][ITEM] == 0


def test_estates_share_shortfall_pro_rata(realm_session: Session) -> None:
    """An estate with a stocked larder competes only for its remaining debt."""
    content = tick_content()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    first, second = estate(realm_session), estate(realm_session)
    context = RealmTickContext(
        None,
        estates=[first, second],
        stores={ITEM: 7500},
        larders={first.id: {ITEM: 1000}, second.id: {}},
    )
    step_10_lines(context, realm, NOW, content)  # reserve = 6000
    step_2_larder_upkeep(context, realm, NOW + timedelta(days=1), content)
    step_3_estate_upkeep(context, realm, NOW + timedelta(days=1), content)
    assert context.stores[ITEM] == 6000
    assert next(iter(context.owed.values())) == [(first.id, 500), (second.id, 1000)]


def test_production_realm_owned_player_owned_and_inert(realm_session: Session) -> None:
    """Production uses realm stores regardless of ownership and honors inertness."""
    from test_projects import _hero

    content = tick_content()
    form = content.estate_form(FORM).model_copy(
        update={"production": (ProductionItem(item_id=ITEM, per_day=7),)}
    )
    content = replace(
        content, _forms_by_id=MappingProxyType({**content._forms_by_id, FORM: form})
    )
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(realm_session)
    owned = realm_session.get(Estate, hero.home_estate_id)
    assert owned is not None
    owned.form_id = FORM
    unowned = estate(realm_session)
    context = load_context(realm_session, realm, None, content)
    step_1_production(context, realm, NOW + timedelta(days=1), content)
    assert context.stores == {ITEM: 14000}
    assert {e.id for e in context.estates} == {owned.id, unowned.id}
    inert = form.model_copy(update={"requires_realm_tags": ("missing",)})
    content = replace(
        content, _forms_by_id=MappingProxyType({**content._forms_by_id, FORM: inert})
    )
    step_1_production(context, realm, NOW + timedelta(days=2), content)
    assert context.stores == {ITEM: 14000}
    from app.models import Inventory

    assert list(realm_session.scalars(select(Inventory))) == []


def test_spoilage_stores_and_larders_and_most_plentiful_cap(
    realm_session: Session,
) -> None:
    """Spoilage precedes cap loss; excess is removed from the largest stack."""
    content = tick_content()
    item = content.item(ITEM).model_copy(update={"spoilage_pct_per_day": 25.0})
    other = content.item("item.worthless_button").model_copy(
        update={"reference_price": 1}
    )
    content = content.with_overrides(items=(item, other))
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    context = RealmTickContext(
        None,
        stores={ITEM: 80000, other.id: 10000},
        larders={uuid.uuid4(): {ITEM: 4000}},
    )
    step_6_spoilage(context, realm, NOW, content)
    assert context.stores[ITEM] == 60000
    assert next(iter(context.larders.values()))[ITEM] == 3000
    from app.engine.stores import Line

    context.lines = (
        Line(
            "plants",
            Selector.model_validate({"class": "fake_plant"}),
            2000,
            2000,
            20000,
            70000,
            False,
        ),
    )
    step_7_caps(context, realm, NOW, content)
    assert context.stores == {ITEM: 10000, other.id: 10000}


@settings(derandomize=True)
@given(
    owed=st.lists(st.integers(0, 100000), min_size=1, max_size=15),
    available=st.integers(0, 100000),
)
def test_pro_rata_conservation(owed: list[int], available: int) -> None:
    """Sharing neither creates stock nor pays an estate more than it is owed."""
    paid = shares(owed, available)
    assert sum(paid) == min(sum(owed), available)
    assert all(0 <= p <= q for p, q in zip(paid, owed, strict=True))


def test_resolve_tick_split_idempotence(realm_session: Session) -> None:
    """Catch-up and single ticks persist identical stores, larders and lines."""
    content = tick_content()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    e = estate(realm_session)
    realm_session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=20000))
    realm_session.add(EstateLarder(estate_id=e.id, item_id=ITEM, quantity_milli=5000))
    realm_session.commit()

    def snapshot() -> tuple[object, ...]:
        return (
            as_utc(realm.last_tick_at),
            tuple(realm_session.scalars(select(RealmStore.quantity_milli))),
            tuple(realm_session.scalars(select(EstateLarder.quantity_milli))),
            tuple(
                (r.stock, r.reserve, r.cap)
                for r in realm_session.scalars(select(RealmLine))
            ),
        )

    resolve_realm(realm_session, realm, NOW + timedelta(days=4), content)
    combined = snapshot()
    resolve_realm(realm_session, realm, NOW + timedelta(days=4), content)
    assert snapshot() == combined
    realm_session.rollback()
    for day in range(1, 5):
        resolve_realm(realm_session, realm, NOW + timedelta(days=day), content)
    assert snapshot() == combined


def test_scheduler_no_players_and_repeat(realm_session: Session) -> None:
    """The liveness job advances shared realms without players and is idempotent."""
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    now = NOW + timedelta(hours=2)
    assert run_realm_ticks(factory, CONTENT, now)
    assert run_realm_ticks(factory, CONTENT, now)
    realm_session.expire_all()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None and as_utc(realm.last_tick_at) == now


def test_postgres_two_scheduler_instances(realm_session: Session) -> None:
    """Only one of two overlapping jobs produces; repeating the timestamp is inert."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from app.services.realms import finalize_realm

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL advisory locks")
    content = tick_content()
    form = content.estate_form(FORM).model_copy(
        update={"production": (ProductionItem(item_id=ITEM, per_day=10),)}
    )
    content = replace(
        content, _forms_by_id=MappingProxyType({**content._forms_by_id, FORM: form})
    )
    estate(realm_session)
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    entered, release = threading.Event(), threading.Event()
    now = NOW + timedelta(days=1)

    def blocked_finalize(
        session: Session, realm_id: str, at: object, data: ContentIndex
    ) -> RealmState | None:
        entered.set()
        assert release.wait(10)
        return finalize_realm(session, realm_id, now, data)

    with (
        patch("app.services.scheduler.finalize_realm", side_effect=blocked_finalize),
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        first = pool.submit(run_realm_ticks, factory, content, now)
        try:
            assert entered.wait(10)
            assert (
                pool.submit(run_realm_ticks, factory, content, now).result(timeout=10)
                is False
            )
        finally:
            release.set()
        assert first.result(timeout=10) is True
    assert run_realm_ticks(factory, content, now)
    realm_session.expire_all()
    row = realm_session.get(RealmStore, (REALM, ITEM))
    assert row is not None and row.quantity_milli == 6000


def test_scheduler_cadence_and_lifecycle() -> None:
    """APScheduler is configured from content with coalescing and one running job."""
    with patch("apscheduler.schedulers.background.BackgroundScheduler") as constructor:
        scheduler = start_scheduler(Mock(), CONTENT)
        constructor.return_value.start.assert_called_once()
        calls = {
            call.kwargs["id"]: call
            for call in constructor.return_value.add_job.call_args_list
        }
        assert set(calls) == {"realm_tick", "market_lifecycle"}
        assert (
            calls["realm_tick"].kwargs["seconds"]
            == 86400 / CONTENT.economy.tick.per_day
        )
        assert (
            calls["market_lifecycle"].kwargs["seconds"]
            == CONTENT.economy.market.lifecycle_interval_seconds
        )
        for call in calls.values():
            assert call.kwargs["coalesce"] is True
            assert call.kwargs["max_instances"] == 1
        scheduler.shutdown()
        constructor.return_value.shutdown.assert_called_once()


def test_realm_overlay_completes_without_player_contributions(
    realm_session: Session,
) -> None:
    """At daily cadence the one-day overlay funds from stores and builds exactly."""
    from test_projects import PROJECT, _run

    from app.models import RealmTag

    content = tick_content()
    node = content.development_node("node.verdant_t1").model_copy(
        update={"reserve_days": 0.0}
    )
    project = content.project(PROJECT).model_copy(update={"realm_completion_days": 1.0})
    content = replace(
        content,
        _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node}),
        _projects_by_id=MappingProxyType(
            {**content._projects_by_id, project.id: project}
        ),
    )
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    run = _run(realm_session, realm)
    run.contributed = [0, 0]
    for raw in run.required:
        requirement = content.item(raw["selector"]["item"])
        realm_session.add(
            RealmStore(
                realm_id=REALM,
                item_id=requirement.id,
                quantity_milli=raw["quantity"] * 1000,
            )
        )
    realm_session.flush()
    resolve_realm(realm_session, realm, NOW + timedelta(days=2), content)
    assert run.status == "complete"
    assert run.build_completes_at is not None
    assert as_utc(run.build_completes_at) == NOW + timedelta(
        days=1, seconds=project.build_seconds
    )
    payments = list(realm_session.scalars(select(RealmContribution)))
    assert sum(p.quantity_milli for p in payments) == 125000
    assert all(p.character_id is None for p in payments)
    tag = realm_session.get(RealmTag, (REALM, project.grants_tag))
    assert tag is not None and tag.project_run_id == run.id
    assert as_utc(tag.acquired_at) == as_utc(run.build_completes_at)


def funding_fixture(
    session: Session, content: ContentIndex, *, days: float = 1.0
) -> tuple[ContentIndex, RealmState, RealmProjectRun]:
    """Start a single-item, 100-unit funding run without player payments."""
    from test_projects import PROJECT, _run

    realm = session.get(RealmState, REALM)
    assert realm is not None
    run = _run(session, realm)
    run.required = [{"selector": {"item": ITEM}, "quantity": 100}]
    run.contributed = [0]
    project = content.project(PROJECT).model_copy(
        update={"realm_completion_days": days}
    )
    content = replace(
        content,
        _projects_by_id=MappingProxyType({**content._projects_by_id, PROJECT: project}),
    )
    session.flush()
    return content, realm, run


def test_golden_tick_pipeline_order(realm_session: Session) -> None:
    """Observe the real resolver pipeline, including otherwise commuting steps."""
    from app.services import realm_ticks

    content = tick_content()
    form = content.estate_form(FORM).model_copy(
        update={"production": (ProductionItem(item_id=ITEM, per_day=2.5),)}
    )
    node = content.development_node("node.verdant_t1").model_copy(
        update={"cap_days": 1.5}
    )
    content = replace(
        content,
        _forms_by_id=MappingProxyType({**content._forms_by_id, FORM: form}),
        _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node}),
    )
    content = content.with_overrides(
        items=(content.item(ITEM).model_copy(update={"spoilage_pct_per_day": 25.0}),)
    )
    content, realm, _ = funding_fixture(realm_session, content, days=10.0)
    first, second = estate(realm_session), estate(realm_session)
    realm_session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=100000))
    realm_session.add(
        EstateLarder(estate_id=first.id, item_id=ITEM, quantity_milli=1000)
    )
    realm_session.flush()
    snapshots = []
    stages = []

    def observe(
        step: Callable[[RealmTickContext, RealmState, datetime, ContentIndex], None],
    ) -> Callable[[RealmTickContext, RealmState, datetime, ContentIndex], None]:
        def run(
            context: RealmTickContext,
            state: RealmState,
            now: datetime,
            data: ContentIndex,
        ) -> None:
            step(context, state, now, data)
            # Capture state after every real step: production and larder consumption
            # commute at tick end, but their specified ordering is observable here.
            stages.append(
                (context.stores[ITEM], context.larders[first.id].get(ITEM, 0))
            )
            if step is realm_ticks.step_10_lines:
                claims = {e: q for values in context.owed.values() for e, q in values}
                snapshots.append(
                    (
                        context.stores[ITEM],
                        context.larders[first.id].get(ITEM, 0),
                        claims[first.id],
                        claims[second.id],
                        sum(context.realm_unmet.values()),
                    )
                )

        return run

    with patch.object(
        realm_ticks,
        "TICK_STEPS",
        tuple(observe(step) for step in realm_ticks.TICK_STEPS),
    ):
        for day in range(1, 5):
            resolve_realm(realm_session, realm, NOW + timedelta(days=day), content)
    assert stages[:3] == [(100000, 1000), (105000, 1000), (105000, 0)]
    assert snapshots == [
        (24000, 0, 0, 0, 0),
        (11250, 0, 0, 0, 0),
        (9150, 0, 975, 975, 0),
        (9113, 0, 2000, 2000, 0),
    ]


@pytest.mark.parametrize("stock,paid", [(100000, 0), (99999, 0), (100123, 123)])
def test_overlay_respects_its_own_reserve(
    realm_session: Session, stock: int, paid: int
) -> None:
    """The overlay's full draw contributes to the reserve before any payment."""
    content = tick_content()
    node = content.development_node("node.verdant_t1").model_copy(update={"upkeep": ()})
    content = replace(
        content, _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node})
    )
    content, realm, run = funding_fixture(realm_session, content)
    realm_session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=stock))
    realm_session.flush()
    resolve_realm(realm_session, realm, NOW + timedelta(days=1), content)
    assert run.contributed == [paid]


def test_hourly_geometric_overlay_and_spreading(realm_session: Session) -> None:
    """Pin the existing shrinking overlay, including cumulative hourly rounding."""
    content = tick_content()
    node = content.development_node("node.verdant_t1").model_copy(
        update={"upkeep": (), "reserve_days": 0.0, "cap_days": 1000.0}
    )
    content = replace(
        content,
        economy=content.economy.model_copy(update={"tick": CONTENT.economy.tick}),
        _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node}),
    )
    content, realm, run = funding_fixture(realm_session, content)
    realm_session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=100000))
    realm_session.flush()
    remaining = 100000
    for n in range(24):
        payment = remaining * (n + 1) // 24 - remaining * n // 24
        remaining -= payment
        resolve_realm(realm_session, realm, NOW + timedelta(hours=n + 1), content)
        assert run.contributed == [100000 - remaining]
    assert abs(run.contributed[0] - 100000 * (1 - (23 / 24) ** 24)) < 24


def test_spoilage_floor_and_unassigned_warehouse_cap(realm_session: Session) -> None:
    """Fractional losses floor; unmatched goods still have a hard warehouse roof."""
    content = tick_content().with_overrides(
        items=(
            CONTENT.item(ITEM).model_copy(
                update={"spoilage_pct_per_day": 25.0, "warehouse_cap": 2}
            ),
        )
    )
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    context = RealmTickContext(
        None, stores={ITEM: 4001}, larders={uuid.uuid4(): {ITEM: 7}}
    )
    step_6_spoilage(context, realm, NOW, content)
    assert context.stores[ITEM] == 3001
    assert next(iter(context.larders.values()))[ITEM] == 6
    step_7_caps(context, realm, NOW, content)
    assert context.stores[ITEM] == 2000


def test_scheduler_isolation_and_failure_continuation(
    realm_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed realm rolls back alone; shared peers advance and isolated ones wait."""
    from app.services.realms import finalize_realm

    realm_session.add_all(
        [
            RealmState(
                id=i,
                template_id=REALM,
                current_node_id="node.verdant_t1",
                last_tick_at=NOW,
                isolated=isolated,
            )
            for i, isolated in [
                ("a-broken", False),
                ("z-shared", False),
                ("isolated", True),
            ]
        ]
    )
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())

    def fail_one(
        session: Session, realm_id: str, now: datetime, content: ContentIndex
    ) -> RealmState | None:
        result = finalize_realm(session, realm_id, NOW + timedelta(hours=1), content)
        if realm_id == "a-broken":
            session.flush()
            raise ValueError("synthetic tick failure")
        return result

    with patch("app.services.scheduler.finalize_realm", side_effect=fail_one):
        assert run_realm_ticks(factory, CONTENT, NOW + timedelta(hours=1))
    realm_session.expire_all()
    for realm_id in [REALM, "z-shared"]:
        row = realm_session.get(RealmState, realm_id)
        assert row is not None
        assert as_utc(row.last_tick_at) == NOW + timedelta(hours=1)
    for realm_id in ["a-broken", "isolated"]:
        row = realm_session.get(RealmState, realm_id)
        assert row is not None
        assert as_utc(row.last_tick_at) == NOW
    assert "realm_id=a-broken" in caplog.text


def test_final_now_completes_build_and_duplicate_guard(realm_session: Session) -> None:
    """A build due between the last tick and now completes with shared guarding."""
    from app.services.realms import build_realm_tag

    content, realm, run = funding_fixture(realm_session, tick_content())
    run.contributed = [0]
    node = content.development_node(realm.current_node_id).model_copy(
        update={"reserve_days": 0.0, "upkeep": ()}
    )
    content = replace(
        content, _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node})
    )
    realm_session.add(RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=100000))
    realm_session.flush()
    now = NOW + timedelta(days=1, minutes=2)
    resolve_realm(realm_session, realm, now, content)
    assert run.status == "complete"
    tag_id = content.project(run.project_id).grants_tag
    tag = realm_session.get(RealmTag, (REALM, tag_id))
    assert tag is not None and as_utc(tag.acquired_at) == NOW + timedelta(
        days=1, seconds=60
    )
    seq = realm.tag_seq
    with pytest.raises(ValueError, match="already holds tag"):
        build_realm_tag(realm, tag_id, {tag_id}, now, run.id)
    assert realm.tag_seq == seq


@settings(
    deadline=None,
    max_examples=8,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(cuts=st.lists(st.integers(1, 95), min_size=1, max_size=5, unique=True))
def test_hourly_split_idempotence_and_payment_conservation(
    realm_session: Session, cuts: list[int]
) -> None:
    """Hourly rounding, catch-up limits and every consumption payment conserve stock."""
    from app.services import realm_ticks

    # Each example uses a savepoint; replay starts from identical persisted inputs.
    with realm_session.begin_nested():
        content = tick_content()
        upkeep = (TagUpkeep(selector=Selector(item=ITEM), per_day=7),)
        form = content.estate_form(FORM).model_copy(
            update={
                "upkeep": upkeep,
                "production": (ProductionItem(item_id=ITEM, per_day=7),),
            }
        )
        node = content.development_node("node.verdant_t1").model_copy(
            update={"upkeep": upkeep, "reserve_days": 0.01, "cap_days": 1000.0}
        )
        content = replace(
            content,
            economy=content.economy.model_copy(update={"tick": CONTENT.economy.tick}),
            _forms_by_id=MappingProxyType({**content._forms_by_id, FORM: form}),
            _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node}),
        )
        content = content.with_overrides(
            items=(content.item(ITEM).model_copy(update={"spoilage_pct_per_day": 7.0}),)
        )
        content, realm, run = funding_fixture(realm_session, content, days=2.0)
        e = estate(realm_session)
        realm_session.add(
            RealmStore(realm_id=REALM, item_id=ITEM, quantity_milli=200000)
        )
        realm_session.add(
            EstateLarder(estate_id=e.id, item_id=ITEM, quantity_milli=10001)
        )
        realm_session.flush()
        original_steps = realm_ticks.TICK_STEPS
        production = []
        checks = []

        def instrument(
            step: Callable[
                [RealmTickContext, RealmState, datetime, ContentIndex], None
            ],
        ) -> Callable[[RealmTickContext, RealmState, datetime, ContentIndex], None]:
            def checked(
                context: RealmTickContext,
                state: RealmState,
                now: datetime,
                data: ContentIndex,
            ) -> None:
                before = sum(context.stores.values()) + sum(
                    sum(stock.values()) for stock in context.larders.values()
                )
                count = len(context.contributions)
                prior_owed = sum(
                    q for claims in context.owed.values() for _, q in claims
                )
                step(context, state, now, data)
                after = sum(context.stores.values()) + sum(
                    sum(stock.values()) for stock in context.larders.values()
                )
                assert all(
                    q >= 0
                    for stock in (context.stores, *context.larders.values())
                    for q in stock.values()
                )
                if step is realm_ticks.step_1_production:
                    production.append(after - before)
                if step is realm_ticks.step_2_larder_upkeep:
                    expected_due = (
                        7000 * ((now - NOW) // timedelta(hours=1)) // 24
                        - 7000 * (((now - NOW) // timedelta(hours=1)) - 1) // 24
                    )
                    assert before - after == expected_due - sum(
                        q for claims in context.owed.values() for _, q in claims
                    )
                elif step is realm_ticks.step_3_estate_upkeep:
                    assert before - after == prior_owed - sum(
                        q for claims in context.owed.values() for _, q in claims
                    )
                    checks.append(before - after)
                elif step is realm_ticks.step_4_realm_upkeep:
                    assert before - after == sum(context.realm_due.values()) - sum(
                        context.realm_unmet.values()
                    )
                elif step is realm_ticks.step_5_projects:
                    assert before - after == sum(
                        p.quantity_milli for p in context.contributions[count:]
                    )

            return checked

        def snapshot() -> tuple[object, ...]:
            realm_session.flush()
            return (
                tuple(
                    realm_session.scalars(
                        select(RealmStore.quantity_milli).order_by(RealmStore.item_id)
                    )
                ),
                tuple(
                    realm_session.scalars(
                        select(EstateLarder.quantity_milli).order_by(
                            EstateLarder.item_id
                        )
                    )
                ),
                tuple(
                    (r.line_key, r.stock, r.reserve, r.cap, r.draw_per_day)
                    for r in realm_session.scalars(
                        select(RealmLine).order_by(RealmLine.line_key)
                    )
                ),
                tuple(run.contributed),
                run.status,
            )

        results = []
        with patch.object(
            realm_ticks,
            "TICK_STEPS",
            tuple(instrument(step) for step in original_steps),
        ):
            for boundaries in ([96], [96, 96], sorted(cuts) + [96]):
                replay = realm_session.begin_nested()
                production.clear()
                for hours in boundaries:
                    target = NOW + timedelta(hours=hours)
                    # Drain the bounded backlog to the requested boundary.
                    resolve_realm(realm_session, realm, target, content)
                    while as_utc(realm.last_tick_at) < target:
                        resolve_realm(realm_session, realm, target, content)
                assert sum(production) == 28000
                results.append(snapshot())
                replay.rollback()
        assert results[0] == results[1] == results[2]
        assert checks and all(q >= 0 for q in checks)
        # Roll back the example's setup as well as its replayed ticks.
        realm_session.rollback()
