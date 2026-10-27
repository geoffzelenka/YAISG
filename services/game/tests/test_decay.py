"""Live hunger, reversible weakening and irreversible asset loss."""

import random
import uuid
from dataclasses import replace
from datetime import timedelta
from types import MappingProxyType

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_engine import START, make_active, make_state
from test_projects import _hero
from test_realm_ticks import FORM, ITEM, REALM, estate, tick_content
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.content.schemas import DecayStage, GaugeConfig, Selector, TagUpkeep
from app.engine import can_start, resolve, resolve_caps
from app.engine.core import modifier_groups, unmet_requirements
from app.engine.decay import advance_gauge, advance_shed, gauge_stage
from app.engine.stores import line_key
from app.models import (
    Estate,
    EstateOwnershipHistory,
    EstateUpgrade,
    RealmState,
    RealmTag,
)
from app.services.actions import resolve_character
from app.services.realm_ticks import (
    RealmTickContext,
    complete_tick_transition,
    load_context,
    persist_context,
    step_1_production,
    step_8_gauges,
    step_9_decay,
    step_10_lines,
)
from app.services.realms import push_realm_tag, resolve_realm, start_transition
from app.services.seed_check import check_seed


def test_strained_has_no_engine_effect() -> None:
    """Every available action, bonus, cap and deterministic reward stays equal."""
    fed = make_state(form_id="form.homestead")
    strained = replace(
        fed, realm_stage=DecayStage.STRAINED, estate_stage=DecayStage.STRAINED
    )
    assert resolve_caps(fed, CONTENT) == resolve_caps(strained, CONTENT)
    assert modifier_groups(fed, CONTENT) == modifier_groups(strained, CONTENT)
    for action in CONTENT._actions_by_id.values():
        assert can_start(action.id, fed, CONTENT) == can_start(
            action.id, strained, CONTENT
        )
        assert unmet_requirements(action, fed, CONTENT) == unmet_requirements(
            action, strained, CONTENT
        )
        active = make_active(action.id)
        if action.resolver == "travel":
            from test_travel import journey

            active = journey()
        left = resolve(
            fed,
            active,
            CONTENT,
            START + timedelta(hours=1),
            random.Random(15),
        )
        right = resolve(
            strained,
            active,
            CONTENT,
            START + timedelta(hours=1),
            random.Random(15),
        )
        assert replace(
            left[0], realm_stage=DecayStage.FED, estate_stage=DecayStage.FED
        ) == replace(right[0], realm_stage=DecayStage.FED, estate_stage=DecayStage.FED)
        assert left[1] == right[1]
        assert replace(left[2], state=None) == replace(right[2], state=None)


@pytest.mark.parametrize(
    "gauge,stage",
    [
        (0, "fed"),
        (0.5, "fed"),
        (0.50001, "strained"),
        (2, "strained"),
        (2.00001, "faltering"),
        (4, "faltering"),
        (4.00001, "failing"),
    ],
)
def test_stage_boundaries(gauge: float, stage: str) -> None:
    """Thresholds are strictly greater than, including the grace interval."""
    assert gauge_stage(gauge, CONTENT.economy.gauge) == stage


@given(st.integers(min_value=1, max_value=9), st.integers(min_value=1, max_value=96))
def test_recovery_cancels_hunger_day_for_day(days: int, ticks: int) -> None:
    """A fed day cancels a fully missing day independent of tick cadence."""
    gauge = 0.0
    for _ in range(days * ticks):
        gauge = advance_gauge(gauge, 100, 100, ticks, GaugeConfig())
    assert gauge == pytest.approx(days)
    for _ in range(days * ticks):
        gauge = advance_gauge(gauge, 100, 0, ticks, GaugeConfig())
    assert gauge == pytest.approx(0, abs=1e-10)
    assert advance_gauge(10, 1, 1, ticks, GaugeConfig()) == 10


def test_reference_weighting_and_estate_independence(realm_session: Session) -> None:
    """An expensive missing good dominates; estate hunger never enters realm due."""
    content = tick_content()
    cheap, expensive = content.items[:2]
    content = content.with_overrides(
        items=(
            cheap.model_copy(update={"reference_price": 1}),
            expensive.model_copy(update={"reference_price": 9}),
        )
    )
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    first, second = (
        line_key(Selector(item=cheap.id)),
        line_key(Selector(item=expensive.id)),
    )
    node = content.development_node(realm.current_node_id).model_copy(
        update={
            "upkeep": (
                TagUpkeep(selector=Selector(item=cheap.id), per_day=1),
                TagUpkeep(selector=Selector(item=expensive.id), per_day=1),
            )
        }
    )
    content = replace(
        content, _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node})
    )
    context = RealmTickContext(
        None,
        realm_due={first: 1000, second: 1000},
        realm_unmet={first: 0, second: 1000},
    )
    step_10_lines(context, realm, NOW, content)
    step_8_gauges(context, realm, NOW, content)
    assert realm.gauge == pytest.approx(0.9)
    realm.gauge = 0
    context.realm_unmet = {first: 1000, second: 0}
    step_8_gauges(context, realm, NOW, content)
    assert realm.gauge == pytest.approx(0.1)
    e = estate(realm_session)
    context = load_context(realm_session, realm, None, content)
    context.owed = {line_key(Selector(item=ITEM)): [(e.id, 2000)]}
    step_8_gauges(context, realm, NOW + timedelta(days=1), content)
    assert e.gauge == 1
    assert realm.gauge == 0  # realm_due is empty, despite the starving estate


def test_shed_order_rate_transition_pause_and_recovery(realm_session: Session) -> None:
    """Highest current-node seq falls first; transitions freeze loss and rate."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    first = push_realm_tag(realm_session, realm, "bonus.fake", NOW)
    second = push_realm_tag(realm_session, realm, "access.fake", NOW)
    realm_session.flush()
    content = tick_content()
    context = load_context(realm_session, realm, None, content)
    realm.gauge = 5
    realm.shed_progress = 0.25
    step_9_decay(context, realm, NOW, content)
    assert context.stack == [first]
    assert context.removed_tags == [second]
    assert realm.shed_progress == pytest.approx(0.25)
    start_transition(realm, "node.verdant_t2", "upgrade", NOW, content)
    step_9_decay(context, realm, NOW, content)
    assert context.stack == [first]
    assert realm.shed_progress == pytest.approx(0.25)
    realm.gauge = 3
    step_9_decay(context, realm, NOW, content)
    assert realm.shed_progress == 0
    assert context.stack == [first]
    assert advance_shed(0, 4.5, 1, 4, content.economy.shed) == 0.75
    persist_context(realm_session, realm, context)
    realm_session.flush()
    assert realm_session.get(RealmTag, (REALM, second.tag_id)) is None


@pytest.mark.parametrize("completion", ["context", "session"])
def test_d4_upgrade_survivors_regress_and_restamp(
    realm_session: Session, completion: str
) -> None:
    """A carried tag cannot block regression; restamping waits for completion."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    carried = push_realm_tag(realm_session, realm, "bonus.fake", NOW)
    start_transition(realm, "node.verdant_t2", "upgrade", NOW, CONTENT)
    resolve_realm(realm_session, realm, NOW + timedelta(days=7), CONTENT)
    assert carried.node_id == "node.verdant_t1"
    assert realm.current_node_id == "node.verdant_t2"
    current = push_realm_tag(
        realm_session, realm, "access.fake", NOW + timedelta(days=7)
    )
    realm_session.flush()
    context = load_context(realm_session, realm, None, tick_content())
    realm.gauge, realm.shed_progress = 5, 0
    step_9_decay(context, realm, NOW + timedelta(days=8), tick_content())
    assert current not in context.stack
    assert realm.pending_transition is not None
    assert realm.decay_stage == "regressed"
    assert carried.node_id == "node.verdant_t1"
    # A carried tag may have been acquired several tiers earlier. Its stamp
    # must actually change here, rather than already matching the target.
    carried.node_id = "node.verdant_t0_stub"
    assert carried.node_id != realm.pending_transition["to_node"]
    if completion == "context":
        complete_tick_transition(context, realm, NOW + timedelta(days=15), CONTENT)
    else:
        from app.services.realms import _finalize_locked_realm

        persist_context(realm_session, realm, context)
        realm_session.flush()
        _finalize_locked_realm(realm_session, realm, NOW + timedelta(days=15), CONTENT)
    assert realm.current_node_id == "node.verdant_t1"
    assert realm.gauge == realm.shed_progress == 0
    assert carried.node_id == realm.current_node_id
    assert current not in context.stack


def test_estate_chain_and_replacement_retains_history(realm_session: Session) -> None:
    """Upgrades fall newest first, then forms; destruction gives a present camp."""
    content = tick_content()
    content = replace(
        content,
        _forms_by_id=MappingProxyType(
            {
                key: form.model_copy(
                    update={
                        "upkeep": (TagUpkeep(selector=Selector(item=ITEM), per_day=1),)
                    }
                )
                for key, form in content._forms_by_id.items()
            }
        ),
    )
    hero = _hero(realm_session)
    hero.current_realm_id = "realm.ashen_reach"
    e = realm_session.get(Estate, hero.home_estate_id)
    realm = realm_session.get(RealmState, REALM)
    assert e is not None and realm is not None
    e.form_id = "form.homestead"
    history = EstateOwnershipHistory(
        estate_id=e.id, character_id=hero.id, acquired_at=NOW
    )
    realm_session.add(history)
    from app.models import EstateLarder

    realm_session.add(EstateLarder(estate_id=e.id, item_id=ITEM, quantity_milli=4321))
    for slot in range(2):
        realm_session.add(
            EstateUpgrade(
                estate_id=e.id,
                slot_index=slot,
                upgrade_id=CONTENT.upgrades[0].id,
                purchased_at=NOW + timedelta(hours=slot),
            )
        )
    realm_session.flush()
    context = load_context(realm_session, realm, None, content)
    e.gauge = 5
    step_9_decay(context, realm, NOW + timedelta(days=1), content)
    assert [u.slot_index for u in context.upgrades] == [0]
    step_9_decay(context, realm, NOW + timedelta(days=2), content)
    assert not context.upgrades
    assert e.form_id == "form.camp" and e.gauge == 0
    e.gauge = 5
    step_9_decay(context, realm, NOW + timedelta(days=3), content)
    persist_context(realm_session, realm, context)
    realm_session.flush()
    assert e.status == "destroyed" and e.owner_character_id is None
    assert context.larders[e.id][ITEM] == 0
    assert realm_session.get(EstateLarder, (e.id, ITEM)) is None
    assert history.relinquished_at == NOW + timedelta(days=3)
    new = context.replacements[0]
    assert new.owner_character_id == hero.id
    assert new.realm_id == hero.current_realm_id
    assert new.form_id == content.progression.basic_mobile_form
    # No owner write inside realm catch-up: the already-locked character repairs it.
    # Seed the absent destination without interfering with the existing test realm.
    realm_session.add(
        RealmState(
            id=hero.current_realm_id,
            template_id=hero.current_realm_id,
            current_node_id="node.ashen_t1",
            last_tick_at=NOW,
        )
    )
    realm.last_tick_at = NOW
    resolve_character(realm_session, hero.id, NOW, content)
    assert hero.home_estate_id == new.id
    assert realm_session.get(EstateOwnershipHistory, history.id) is history
    assert len(list(realm_session.scalars(select(EstateOwnershipHistory)))) == 2


def test_live_faltering_production_and_strained_equality(
    realm_session: Session,
) -> None:
    """Estate production changes only after Faltering, then recovers."""
    content = CONTENT
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    e = estate(realm_session)
    context = load_context(realm_session, realm, None, content)
    amounts = []
    for stage in ("fed", "strained", "faltering", "failing"):
        e.decay_stage = stage
        context.stores = {}
        step_1_production(context, realm, NOW + timedelta(days=1), content)
        amounts.append(context.stores[ITEM])
    assert amounts == [84, 84, 42, 42]


def test_seed_check_healthy_and_starving_fixture() -> None:
    """Exercise thirty daily ticks and stop a starving world on first Faltering."""
    content = replace(
        CONTENT,
        economy=CONTENT.economy.model_copy(
            update={
                "tick": CONTENT.economy.tick.model_copy(update={"per_day": 1}),
            }
        ),
    )
    assert all(not r.reached_faltering for r in check_seed(content))
    nodes = {
        key: node.model_copy(
            update={"upkeep": (TagUpkeep(selector=Selector(item=ITEM), per_day=1000),)}
        )
        for key, node in CONTENT._nodes_by_id.items()
    }
    starving = replace(content, _nodes_by_id=MappingProxyType(nodes))
    from unittest.mock import patch

    with patch(
        "app.services.seed_check.resolve_realm", wraps=resolve_realm
    ) as resolved:
        assert any(r.reached_faltering for r in check_seed(starving))
    assert resolved.call_count < 5 * len(content.world_seed.realms)


@given(days=st.integers(min_value=13, max_value=30))
@settings(
    max_examples=8,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_decay_catchup_matches_split_and_is_idempotent(
    realm_session: Session, days: int
) -> None:
    """Regression started inside catch-up completes exactly as daily resolves do."""
    content = tick_content()
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "tick": content.economy.tick.model_copy(update={"max_catchup": 100}),
            }
        ),
    )
    root = content.development_node("node.verdant_t0_stub").model_copy(
        update={"inherent_tags": ("access.fake",)}
    )
    content = replace(
        content,
        _nodes_by_id=MappingProxyType(
            {
                **content._nodes_by_id,
                root.id: root,
            }
        ),
    )
    # Hypothesis reuses the fixture: start each example with fresh realm state.
    from sqlalchemy import delete

    realm_session.execute(delete(RealmTag))
    realm_session.execute(delete(RealmState).where(RealmState.id == "split"))
    single = realm_session.get(RealmState, REALM)
    assert single is not None
    single.current_node_id = "node.verdant_t1"
    single.last_tick_at = NOW
    single.gauge = single.shed_progress = 0
    single.decay_stage = "fed"
    single.pending_transition = None
    split = RealmState(
        id="split",
        template_id=REALM,
        current_node_id=single.current_node_id,
        last_tick_at=NOW,
    )
    realm_session.add(split)
    for realm in (single, split):
        push_realm_tag(realm_session, realm, "bonus.fake", NOW)
    realm_session.flush()
    resolve_realm(realm_session, single, NOW + timedelta(days=days), content)
    for day in range(1, days + 1):
        resolve_realm(realm_session, split, NOW + timedelta(days=day), content)

    def snapshot(realm: RealmState) -> tuple[object, ...]:
        return (
            realm.current_node_id,
            realm.gauge,
            realm.decay_stage,
            realm.shed_progress,
            realm.pending_transition,
            realm.last_tick_at,
            [
                (t.tag_id, t.node_id)
                for t in realm_session.scalars(
                    select(RealmTag).where(RealmTag.realm_id == realm.id)
                )
            ],
        )

    assert snapshot(single) == snapshot(split)
    assert single.current_node_id == "node.verdant_t0_stub"
    assert not snapshot(single)[-1]
    assert "bonus.fake" not in {
        t.id for t in load_context(realm_session, single, None, content).tags
    }
    before = snapshot(single)
    resolve_realm(realm_session, single, NOW + timedelta(days=days), content)
    assert snapshot(single) == before


def test_no_tick_profile_and_isolation_exemptions(realm_session: Session) -> None:
    """Basic mobile estates skip the tick; isolated realm hunger never advances."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    hero = _hero(realm_session)
    basic = realm_session.get(Estate, hero.home_estate_id)
    assert basic is not None
    context = load_context(realm_session, realm, None, CONTENT)
    assert basic not in context.estates
    realm.isolated = True
    realm.gauge, realm.shed_progress = 5, 0.75
    e = estate(realm_session)
    context = load_context(realm_session, realm, None, CONTENT)
    e.gauge, e.shed_progress = 5, 0.75
    step_8_gauges(context, realm, NOW, CONTENT)
    step_9_decay(context, realm, NOW, CONTENT)
    assert (realm.gauge, realm.shed_progress) == (5, 0.75)
    assert (e.gauge, e.shed_progress, e.status) == (5, 0.75, "active")


def test_barren_root_remains_failing(realm_session: Session) -> None:
    """Inherent tags cannot be shed, and a root without an edge stays Failing."""
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    root = CONTENT.development_node("node.verdant_t0_stub").model_copy(
        update={"inherent_tags": ("access.fake",)}
    )
    content = replace(
        CONTENT,
        _nodes_by_id=MappingProxyType(
            {
                **CONTENT._nodes_by_id,
                root.id: root,
            }
        ),
    )
    realm.current_node_id = root.id
    realm.gauge, realm.decay_stage = 5, "failing"
    context = load_context(realm_session, realm, None, content)
    realm.gauge = 10
    for tick in range(30 * content.economy.tick.per_day):
        step_9_decay(context, realm, NOW + timedelta(hours=tick), content)
        assert realm.shed_progress <= 1
    # A day of rescue drains the one pending loss before rebuilding.
    realm.gauge = 0
    for tick in range(content.economy.tick.per_day):
        step_9_decay(context, realm, NOW + timedelta(days=30, hours=tick), content)
    assert realm.shed_progress == 0
    realm.current_node_id = "node.verdant_t1"
    context.stack = [
        RealmTag(
            realm_id=REALM,
            tag_id=tag_id,
            node_id=realm.current_node_id,
            seq=seq,
            acquired_at=NOW,
        )
        for seq, tag_id in enumerate(("bonus.fake", "facility.fake_node"), start=1)
    ]
    realm.gauge = 5
    step_9_decay(context, realm, NOW + timedelta(days=32), content)
    assert len(context.stack) == 2
    assert realm.pending_transition is None
    realm.current_node_id = root.id
    context.stack = []
    realm.decay_stage = "failing"
    step_9_decay(context, realm, NOW, content)
    assert realm.decay_stage == "failing" and realm.pending_transition is None
    assert {t.id for t in context.tags} == set(
        content.development_node(realm.current_node_id).inherent_tags
    )


def test_postgres_decay_and_owner_resolve_do_not_deadlock(
    realm_session: Session,
) -> None:
    """Realm decay creates one replacement while an owner holds its character lock."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic, sleep

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from app.models import Character

    engine = realm_session.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL row-lock contention")
    hero = _hero(realm_session)
    e = realm_session.get(Estate, hero.home_estate_id)
    assert e is not None
    e.form_id, e.gauge = FORM, 6
    # Starve the workshop instead of allowing its normal production to feed it.
    content = tick_content()
    realm_session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    character_locked, proceed, finished = Event(), Event(), Event()
    owner_pid: list[int] = []

    def owner() -> None:
        with factory.begin() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            session.scalar(
                select(Character)
                .where(Character.id == hero.id)
                .with_for_update(key_share=True)
            )
            owner_pid.append(session.scalar(text("SELECT pg_backend_pid()")))
            character_locked.set()
            assert proceed.wait(5)
            resolve_character(session, hero.id, NOW + timedelta(days=1), content)
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(owner)
        assert character_locked.wait(5)
        with factory.begin() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            realm = session.scalar(
                select(RealmState).where(RealmState.id == REALM).with_for_update()
            )
            assert realm is not None
            proceed.set()
            deadline = monotonic() + 5
            while not session.scalar(
                text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"),
                {"pid": owner_pid[0]},
            ):
                assert monotonic() < deadline, "owner did not block on the realm"
                sleep(0.01)
            resolve_realm(session, realm, NOW + timedelta(days=1), content)
            assert not finished.is_set()
        pending.result(timeout=10)
    realm_session.expire_all()
    actual = realm_session.get(Character, hero.id)
    assert actual is not None and actual.home_estate_id != e.id
    replacement = realm_session.get(Estate, actual.home_estate_id)
    assert replacement is not None
    assert replacement.form_id == content.progression.basic_mobile_form
    assert (
        len(
            list(
                realm_session.scalars(
                    select(Estate).where(
                        Estate.owner_character_id == hero.id, Estate.status == "active"
                    )
                )
            )
        )
        == 1
    )


def test_seed_check_cli_exit_and_report(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The operator command reports private holdings and exits nonzero on failure."""
    from app.services import seed_check

    report = seed_check.SeedReport(REALM, 3, 1000, {ITEM: 4000}, True)
    monkeypatch.setattr(seed_check, "check_seed", lambda content: [report])
    with pytest.raises(SystemExit, match="reached Faltering"):
        seed_check.main()
    output = capsys.readouterr().out
    assert "gauge=3.000000" in output and "treasury=1000" in output
    assert "stores_milli=" in output and ITEM in output
    report = replace(report, reached_faltering=False)
    seed_check.main()


def test_fractional_ticks_do_not_cross_stage_boundaries_early() -> None:
    """Hourly rounding cannot make exactly two days Faltering, or delay a shed."""
    gauge = progress = 0.0
    for _ in range(48):
        gauge = advance_gauge(gauge, 1000, 1000, 24, CONTENT.economy.gauge)
    assert gauge == 2 and gauge_stage(gauge, CONTENT.economy.gauge) == "strained"
    for _ in range(24):
        progress = advance_shed(progress, 5, 24, 4, CONTENT.economy.shed)
    assert progress == 1


@pytest.mark.parametrize("transition_hour", [1, 2])
def test_catchup_build_precedes_transition_and_keeps_credits(
    realm_session: Session, transition_hour: int
) -> None:
    """Same-tick exact events keep source stamps, tie order and immutable credits."""
    from test_projects import _run

    from app.models import RealmContribution, RealmProjectRun
    from app.services.realm_ticks import complete_tick_events

    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    run = _run(realm_session, realm)
    run.status = "building"
    run.build_completes_at = NOW + timedelta(hours=1)
    credit = RealmContribution(
        run_id=run.id, item_id=ITEM, quantity_milli=1000, contributed_at=NOW
    )
    realm_session.add(credit)
    realm_session.flush()
    start_transition(realm, "node.verdant_t2", "upgrade", NOW, CONTENT)
    assert realm.pending_transition is not None
    realm.pending_transition = {
        **realm.pending_transition,
        "completes_at": (NOW + timedelta(hours=transition_hour)).isoformat(),
    }
    context = load_context(realm_session, realm, run, CONTENT)
    complete_tick_events(context, realm, NOW + timedelta(hours=3), CONTENT)
    tag = context.stack[0]
    assert tag.acquired_at == NOW + timedelta(hours=1)
    assert tag.node_id == "node.verdant_t1"
    assert realm.current_node_id == "node.verdant_t2"
    # Restamp to make the newly built tag eligible for this node's decay.
    tag.node_id = realm.current_node_id
    realm.gauge, realm.shed_progress = 5, 1
    step_9_decay(context, realm, NOW + timedelta(hours=4), CONTENT)
    assert not context.stack and not context.acquired_tags
    persist_context(realm_session, realm, context)
    realm_session.flush()
    assert (
        realm_session.get(RealmProjectRun, run.id) is run and run.status == "complete"
    )
    assert realm_session.get(RealmContribution, credit.id) is credit
    assert credit.quantity_milli == 1000
    assert realm_session.get(RealmTag, (REALM, tag.tag_id)) is None


def test_strained_has_no_realm_tick_effect() -> None:
    """Full tick holdings, allocation, emissions and demand stay identical."""
    from app.services.realm_ticks import TICK_STEPS, refresh_tags

    content = tick_content()
    outputs = []
    estate_id = uuid.uuid4()
    for stage, gauge in (("fed", 0.0), ("strained", 0.75)):
        realm = RealmState(
            id=REALM,
            template_id=REALM,
            current_node_id="node.verdant_t1",
            last_tick_at=NOW,
            gauge=gauge,
            decay_stage=stage,
            shed_progress=0,
            isolated=False,
        )
        e = Estate(
            id=estate_id,
            realm_id=REALM,
            form_id=FORM,
            gauge=gauge,
            decay_stage=stage,
            shed_progress=0,
            status="active",
        )
        context = RealmTickContext(
            None, estates=[e], stores={ITEM: 10000}, larders={e.id: {ITEM: 1000}}
        )
        refresh_tags(context, realm, content)
        step_10_lines(context, realm, NOW, content)
        for step in TICK_STEPS:
            step(context, realm, NOW + timedelta(days=1), content)
        outputs.append(
            (
                context.stores,
                context.larders,
                context.tags,
                context.lines,
                context.owed,
                context.realm_due,
                context.realm_unmet,
                context.removed_tags,
                context.removed_upgrades,
                context.acquired_tags,
                context.contributions,
                e.form_id,
                e.status,
                e.shed_progress,
                realm.shed_progress,
                realm.pending_transition,
            )
        )
    assert outputs[0] == outputs[1]


def test_faltering_weakens_numeric_economy_tag_effects() -> None:
    """Reserve and route-loss bonuses weaken; access and upkeep remain available."""
    from app.content.schemas import Tag, TagEffects
    from app.engine.tags import TagHolder, economy_tags

    bonus = Tag(
        id="bonus",
        name="Fake",
        kind="bonus",
        effects=TagEffects(reserve_days_delta=4, edge_loss_reduction_pct=20),
    )
    access = Tag(
        id="access",
        name="Fake access",
        kind="access",
        effects=TagEffects(market_access=True, caravan_access=True),
    )
    holder = TagHolder((bonus, access), 0.5)
    assert economy_tags(holder, DecayStage.FED) == economy_tags(
        holder, DecayStage.STRAINED
    )
    weakened = economy_tags(holder, DecayStage.FALTERING)
    assert weakened[0].effects.reserve_days_delta == 2
    assert weakened[0].effects.edge_loss_reduction_pct == 10
    assert weakened[1].effects == access.effects
    assert bonus.effects.reserve_days_delta == 4


def test_gauge_weights_are_cached_until_line_membership_changes(
    realm_session: Session,
) -> None:
    """Repeated gauges and stock-only line refreshes never rescan item definitions."""
    from unittest.mock import patch

    content = tick_content()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    context = load_context(realm_session, realm, None, content)
    key = line_key(Selector(item=ITEM))
    context.realm_due = {key: 1000}
    context.realm_unmet = {key: 1000}
    weight = content.item(ITEM).reference_price
    assert context.line_weights[key] == weight
    with patch.object(
        Selector, "matches", side_effect=AssertionError("rescanned items")
    ):
        for _ in range(4):
            step_8_gauges(context, realm, NOW, content)
            step_10_lines(context, realm, NOW, content)
    assert context.line_weights[key] == weight
