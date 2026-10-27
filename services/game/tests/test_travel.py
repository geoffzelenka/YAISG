"""Journey routing, deterministic progress and transactional API contracts."""

import random
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType

import pytest
from httpx import AsyncClient
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from test_engine import START, make_state
from test_estates import _give
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client

from app.content.loader import ContentIndex, load_content
from app.content.schemas import MapEdge, MapPack, Modifier, ModifierType, TravelProfile
from app.engine import ActiveAction, CharacterState, StopReason, resolve
from app.engine.travel import route, step_cost
from app.main import app
from app.models import (
    ActiveActionRecord,
    Character,
    CharacterSkill,
    Estate,
    Inventory,
    RealmState,
)
from app.services.actions import resolve_character

CONTENT = load_content(Path(__file__).parents[3] / "content")
ORIGIN = "realm.verdant_vale"
DESTINATION = "realm.ashen_reach"
JOURNEY = CONTENT.actions_for_skill("travel")[0].id
ApiFixture = tuple[
    AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
]


def edge(
    identifier: str, a: str, b: str, seconds: float = 60, **fields: object
) -> MapEdge:
    """Build validated map content for routing cases."""
    return MapEdge.model_validate(
        {
            "id": identifier,
            "a": a,
            "b": b,
            "terrain": "land",
            "base_time_s": seconds,
            "min_travel_level": 1,
            "one_way": False,
            "base_loss_pct": 0,
            **fields,
        }
    )


def traveller(supplies: int = 20) -> CharacterState:
    """Build a traveller with a present mobile estate."""
    return replace(
        make_state(inventory={"item.fake_sprig": supplies}),
        skills_xp={"travel": 0},
        skill_levels={"travel": 1},
        current_realm_id=ORIGIN,
        estate_realm_id=ORIGIN,
    )


def journey(mode: str = "relocate", count: int = 3) -> ActiveAction:
    """Use repeated edges to test progress independently of route selection."""
    return ActiveAction(
        JOURNEY,
        START,
        START,
        {
            "mode": mode,
            "route": [
                {
                    "edge_id": CONTENT.map.edges[0].id,
                    "destination_realm_id": DESTINATION if i % 2 == 0 else ORIGIN,
                }
                for i in range(count)
            ],
        },
    )


def advance(
    state: CharacterState,
    active: ActiveAction,
    ms: int,
    content: ContentIndex = CONTENT,
) -> tuple[CharacterState, ActiveAction | None]:
    """Resolve at an absolute deterministic timestamp."""
    state, next_active, _ = resolve(
        state, active, content, START + timedelta(milliseconds=ms), random.Random(7)
    )
    return state, next_active


def test_routing_terrain_level_one_way_and_tie_breaks() -> None:
    """Filter terrain and level, honoring all three path ordering keys."""
    profile = CONTENT.progression.visit_profile
    graph = replace(
        CONTENT,
        map=MapPack(
            edges=(
                edge("z", "a", "d", 120),
                edge("b", "a", "b"),
                edge("c", "b", "d"),
                edge("a", "a", "c"),
                edge("d", "c", "d"),
                edge("shortcut", "a", "d", 10, min_travel_level=5, one_way=True),
            )
        ),
    )
    assert [s["edge_id"] for s in route("a", "d", profile, 1, graph)] == ["z"]
    assert [s["edge_id"] for s in route("a", "d", profile, 5, graph)] == ["shortcut"]
    assert [s["edge_id"] for s in route("d", "a", profile, 5, graph)] == ["z"]
    graph = replace(
        graph, map=graph.map.model_copy(update={"edges": graph.map.edges[1:]})
    )
    assert [s["edge_id"] for s in route("a", "d", profile, 1, graph)] == ["a", "d"]
    water = profile.model_copy(update={"terrains": ("water",)})
    with pytest.raises(ValueError, match="No route"):
        route("a", "d", water, 100, graph)


def test_supplies_paid_at_step_start_and_shortfall_stays_at_start() -> None:
    """The first payment is immediate; a later shortfall cannot move presence."""
    state, active, first = resolve(
        traveller(2), journey(), CONTENT, START, random.Random(1)
    )
    assert state.inventory == {}
    assert first.items_consumed == {"item.fake_sprig": 2}
    assert state.current_realm_id == ORIGIN
    assert active is not None
    state, active, result = resolve(
        state, active, CONTENT, START + timedelta(seconds=60), random.Random(1)
    )
    assert active is None and result.stop_reason == StopReason.OUT_OF_SUPPLIES
    assert state.current_realm_id == DESTINATION
    assert result.cycles_completed == 1 and result.xp_gained == {"travel": 60}


@given(st.integers(min_value=0, max_value=220_000))
def test_random_stops_keep_exactly_last_completed_realm(ms: int) -> None:
    """There is exactly one location, including during paid partial steps."""
    state, _ = advance(traveller(), journey(), ms)
    completed = min(3, ms // 60_000)
    expected = DESTINATION if completed % 2 else ORIGIN
    assert state.current_realm_id == expected
    assert state.estate_realm_id == expected
    assert state.skills_xp["travel"] == completed * 60
    assert state.inventory["item.fake_sprig"] == 20 - min(3, completed + 1) * 2


@pytest.mark.parametrize("mode", ["visit", "relocate"])
def test_estate_moves_only_when_relocating(mode: str) -> None:
    """Estate residence follows each completed relocation edge, never a visit."""
    state, active = advance(traveller(), journey(mode), 60_000)
    assert state.current_realm_id == DESTINATION
    assert state.estate_realm_id == (DESTINATION if mode == "relocate" else ORIGIN)
    assert active is not None
    state, _ = advance(state, active, 120_000)
    assert state.current_realm_id == ORIGIN and state.estate_realm_id == ORIGIN


def test_base_time_xp_ceil_supplies_and_multiplicative_groups() -> None:
    """Speed never reduces edge XP; groups multiply and supply fractions round up."""
    speed = Modifier(type=ModifierType.JOURNEY_SPEED_PCT, value=100)
    reduction = Modifier(type=ModifierType.SUPPLY_REDUCTION_PCT, value=50)
    form = CONTENT.estate_forms[0].model_copy(update={"modifiers": (speed,)})
    content = replace(
        CONTENT,
        _forms_by_id=MappingProxyType(
            {
                **CONTENT._forms_by_id,
                form.id: form,
            }
        ),
    )
    state = replace(
        traveller(),
        gear_modifiers=(
            speed,
            reduction,
            Modifier(type=ModifierType.XP_PCT, value=1000),
        ),
    )
    duration, supplies = step_cost(
        content.map.edges[0], state, content.progression.visit_profile, content
    )
    assert duration == 15_000
    assert supplies[0].quantity == 2  # ceil(2 / 1.5)
    state, active = advance(state, journey(count=1), duration, content)
    assert active is None and state.skills_xp["travel"] == 60
    assert state.inventory["item.fake_sprig"] == 18


def test_travel_tier_benefit_is_group_p() -> None:
    """Travel tiers use their benefit row rather than tier-distance proficiency."""
    state = replace(
        traveller(), skill_levels={"travel": CONTENT.progression.tier_thresholds[1]}
    )
    definition = CONTENT.map.edges[0]
    definition = definition.model_copy(
        update={
            "supplies": (definition.supplies[0].model_copy(update={"quantity": 11}),)
        }
    )
    duration, supplies = step_cost(
        definition, state, CONTENT.progression.visit_profile, CONTENT
    )
    assert duration == 54_546  # ceil(60000 / 1.1)
    assert supplies[0].quantity == 10


@given(st.lists(st.integers(min_value=0, max_value=180_000), max_size=20))
def test_offline_equals_online_polling(polls: list[int]) -> None:
    """Polling changes neither location, supplies, XP nor remaining step time."""
    expected, expected_active = advance(traveller(), journey(), 175_000)
    state = traveller()
    active: ActiveAction | None = journey()
    for ms in sorted(set([0, *[p for p in polls if p <= 175_000], 175_000])):
        assert active is not None
        state, active = advance(state, active, ms)
    assert state == expected
    assert active == expected_active


def test_offline_cap_discards_partial_step() -> None:
    """A step longer than the offline budget cannot bypass the cap on later polls."""
    content = replace(
        CONTENT, caps=CONTENT.caps.model_copy(update={"offline_hours": 0.01})
    )
    state, active, result = resolve(
        traveller(), journey(), content, START + timedelta(hours=1), random.Random(1)
    )
    assert active is None and result.stop_reason == StopReason.OFFLINE_CAP
    assert state.current_realm_id == ORIGIN
    assert state.skills_xp["travel"] == 0
    assert result.items_consumed == {"item.fake_sprig": 2}


@pytest.mark.anyio
async def test_travel_preview_start_stop_and_removed_routes(
    estate_client: ApiFixture,
) -> None:
    """Preview is free; stopping loses paid supplies; old endpoints return 404."""
    client, factory, headers, clock = estate_client
    character_id = _give(factory, "item.fake_sprig", 10)
    params = {"destination_realm_id": DESTINATION, "mode": "relocate"}
    preview = await client.get("/travel/preview", headers=headers, params=params)
    assert preview.status_code == 200
    assert preview.json()["route"][0]["time_ms"] == 60_000
    with factory() as session:
        stack = session.get(Inventory, (character_id, "item.fake_sprig"))
        assert stack is not None and stack.quantity == 10
        assert session.scalar(select(ActiveActionRecord)) is None
    started = await client.post("/travel/start", headers=headers, json=params)
    assert started.status_code == 200
    assert started.json()["since_last"]["items_consumed"] == {"item.fake_sprig": 2}
    clock["now"] += timedelta(seconds=30)
    poll = await client.get("/actions/poll", headers=headers)
    meta = poll.json()["active"]["meta"]
    assert meta["step_index"] == 0
    assert meta["remaining_ms"] == 30_000
    assert meta["duration_ms"] == 60_000
    assert meta["route"][0]["destination_realm_id"] == DESTINATION
    blocked = await client.post(
        "/estates/me/transform", headers=headers, json={"form_id": "form.homestead"}
    )
    assert blocked.json()["error"]["code"] == "ESTATE_BUSY"
    stopped = await client.post("/actions/stop", headers=headers)
    assert stopped.status_code == 200 and stopped.json()["active"] is None
    with factory() as session:
        character = session.get(Character, character_id)
        assert character is not None and character.current_realm_id == ORIGIN
        stack = session.get(Inventory, (character_id, "item.fake_sprig"))
        assert stack is not None and stack.quantity == 8
    for method, path in [
        ("GET", "/characters/me/relocate"),
        ("POST", "/characters/me/relocate"),
        ("GET", "/characters/me/relocate/preview"),
    ]:
        assert (await client.request(method, path, headers=headers)).status_code == 404


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["visit", "relocate"])
async def test_travel_arrival_persists_and_rewards_claim_once(
    estate_client: ApiFixture, mode: str
) -> None:
    """Arrival atomically persists presence, estate location, XP and summary."""
    client, factory, headers, clock = estate_client
    character_id = _give(factory, "item.fake_sprig", 2)
    response = await client.post(
        "/travel/start",
        headers=headers,
        json={"destination_realm_id": DESTINATION, "mode": mode},
    )
    assert response.status_code == 200
    clock["now"] += timedelta(seconds=60)
    polled = (await client.get("/actions/poll", headers=headers)).json()
    assert polled["active"] is None
    assert polled["since_last"]["xp_gained"] == {"travel": 60}
    assert (
        polled["since_last"]["details"]["resolutions"][0]["current_realm_id"]
        == DESTINATION
    )
    assert (await client.get("/actions/poll", headers=headers)).json()["since_last"][
        "xp_gained"
    ] == {}
    with factory() as session:
        character = session.get(Character, character_id)
        estate = session.scalar(select(Estate))
        skill = session.get(CharacterSkill, (character_id, "travel"))
        assert character is not None and character.current_realm_id == DESTINATION
        assert estate is not None and estate.realm_id == (
            DESTINATION if mode == "relocate" else ORIGIN
        )
        assert skill is not None and skill.xp == 60


@pytest.mark.anyio
async def test_starting_another_action_ends_journey(estate_client: ApiFixture) -> None:
    """Switching work drops the paid partial step without moving presence."""
    client, factory, headers, clock = estate_client
    _give(factory, "item.fake_sprig", 2)
    await client.post(
        "/travel/start",
        headers=headers,
        json={"destination_realm_id": DESTINATION, "mode": "relocate"},
    )
    clock["now"] += timedelta(seconds=30)
    response = await client.post(
        "/actions/start", headers=headers, json={"action_id": "gathering.fake_sprigs"}
    )
    assert response.status_code == 200
    with factory() as session:
        character = session.scalar(select(Character))
        active = session.scalar(select(ActiveActionRecord))
        assert character is not None and character.current_realm_id == ORIGIN
        assert active is not None and active.action_id == "gathering.fake_sprigs"


@pytest.mark.anyio
async def test_travel_validation_codes(estate_client: ApiFixture) -> None:
    """Profiles and estate location gate relocation; fixed owners may visit."""
    client, factory, headers, _ = estate_client
    params = {"destination_realm_id": DESTINATION, "mode": "relocate"}
    same = await client.get(
        "/travel/preview",
        headers=headers,
        params={**params, "destination_realm_id": ORIGIN},
    )
    assert same.json()["error"]["code"] == "ALREADY_THERE"
    form = app.state.content.estate_forms[0]
    water = form.model_copy(
        update={
            "travel_profile": TravelProfile(
                time_mult=1, supply_mult=1, terrains=("water",)
            )
        }
    )
    original = app.state.content
    app.state.content = replace(
        original,
        _forms_by_id=MappingProxyType({**original._forms_by_id, form.id: water}),
    )
    blocked = await client.get("/travel/preview", headers=headers, params=params)
    assert blocked.json()["error"]["code"] == "NO_ROUTE"
    fixed = form.model_copy(update={"mobility": "fixed", "travel_profile": None})
    app.state.content = replace(
        original,
        _forms_by_id=MappingProxyType({**original._forms_by_id, form.id: fixed}),
    )
    blocked = await client.get("/travel/preview", headers=headers, params=params)
    assert blocked.json()["error"]["code"] == "ESTATE_FIXED"
    assert (
        await client.get(
            "/travel/preview", headers=headers, params={**params, "mode": "visit"}
        )
    ).status_code == 200
    app.state.content = original
    with factory() as session:
        estate = session.scalar(select(Estate))
        assert estate is not None
        estate.realm_id = DESTINATION
        session.commit()
    blocked = await client.get("/travel/preview", headers=headers, params=params)
    assert blocked.json()["error"]["code"] == "ESTATE_NOT_HERE"


@pytest.mark.anyio
async def test_postgres_travel_holds_character_realms_and_estate(
    estate_client: ApiFixture,
) -> None:
    """A journey resolve holds its complete write set until the request commits."""
    _, factory, _, clock = estate_client
    with factory() as first:
        if first.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL row lock assertion")
    character_id = _give(factory, "item.fake_sprig", 10)
    with factory() as setup:
        for realm in CONTENT.realms:
            if setup.get(RealmState, realm.id) is None:
                setup.add(
                    RealmState(
                        id=realm.id,
                        template_id=realm.id,
                        last_tick_at=datetime(2026, 1, 1, tzinfo=UTC),
                        current_node_id=realm.starting_node_id,
                    )
                )
        setup.add(
            ActiveActionRecord(
                character_id=character_id,
                action_id=JOURNEY,
                started_at=clock["now"],
                last_resolved_at=clock["now"],
                meta=dict(journey().meta),
            )
        )
        setup.commit()
    with factory() as first:
        resolve_character(first, character_id, clock["now"] + timedelta(seconds=60))
        for model in (Character, RealmState, Estate):
            with factory() as second:
                with pytest.raises(DBAPIError) as error:
                    second.execute(select(model).with_for_update(nowait=True))
                assert getattr(error.value.orig, "sqlstate", None) == "55P03"
                second.rollback()
        first.rollback()


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_time_s", 0),
        ("base_time_s", -1),
        ("min_travel_level", 0),
        ("min_travel_level", 101),
        ("base_loss_pct", -1),
        ("base_loss_pct", 101),
        ("terrain", "sky"),
        ("one_way", 1),
    ],
)
def test_travel_edge_ranges_are_strict(field: str, value: object) -> None:
    """Edges reject invalid terrain, gates, loss, durations and boolean coercion."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        payload = CONTENT.map.edges[0].model_dump()
        payload[field] = value
        MapEdge.model_validate(payload)


@pytest.mark.parametrize(
    "mobility,profile",
    [
        ("fixed", CONTENT.progression.visit_profile),
        ("mobile", None),
    ],
)
def test_form_profile_matches_mobility(
    mobility: str, profile: TravelProfile | None
) -> None:
    """Fixed estates forbid travel profiles; mobile estates require them."""
    from pydantic import ValidationError

    from app.content.schemas import EstateForm

    form = CONTENT.estate_forms[0].model_dump()
    form.update(mobility=mobility, travel_profile=profile)
    with pytest.raises(ValidationError, match="mobile forms require a profile"):
        EstateForm.model_validate(form)


def test_overlapping_travel_supplies_are_atomic() -> None:
    """A failed later selector does not consume an earlier supply line."""
    definition = CONTENT.map.edges[0]
    content = replace(
        CONTENT,
        map=MapPack(
            edges=(
                definition.model_copy(
                    update={
                        "supplies": definition.supplies * 2,
                    }
                ),
            )
        ),
    )
    state, active, result = resolve(
        traveller(3), journey(), content, START, random.Random(1)
    )
    assert active is None and result.stop_reason == StopReason.OUT_OF_SUPPLIES
    assert state.inventory == {"item.fake_sprig": 3}
    assert result.items_consumed == {}
    assert state.current_realm_id == ORIGIN


def test_profiles_multiply_time_and_supply_cost() -> None:
    """Estate profile multipliers feed the resolver rather than only preview."""
    form = CONTENT.estate_forms[0]
    assert form.travel_profile is not None
    slower = form.model_copy(
        update={
            "travel_profile": form.travel_profile.model_copy(
                update={
                    "time_mult": 2,
                    "supply_mult": 1.25,
                }
            )
        }
    )
    content = replace(
        CONTENT,
        _forms_by_id=MappingProxyType({**CONTENT._forms_by_id, form.id: slower}),
    )
    state, active = advance(traveller(), journey(count=1), 60_000, content)
    assert active is not None and state.current_realm_id == ORIGIN
    assert state.inventory["item.fake_sprig"] == 17
    state, active = advance(state, active, 120_000, content)
    assert active is None and state.current_realm_id == DESTINATION
    assert state.skills_xp["travel"] == 60


def test_next_step_uses_arrival_realm_bonus() -> None:
    """Realm group R switches on arrival before the next step is priced."""
    from app.content.schemas import DecayStage

    destination_node = CONTENT.realm(DESTINATION).starting_node_id
    node = CONTENT.development_node(destination_node)
    boosted = node.model_copy(
        update={
            "modifiers": (Modifier(type=ModifierType.JOURNEY_SPEED_PCT, value=100),)
        }
    )
    content = replace(
        CONTENT,
        _nodes_by_id=MappingProxyType({**CONTENT._nodes_by_id, node.id: boosted}),
    )
    initial = replace(
        traveller(), realm_states={DESTINATION: (node.id, DecayStage.FED, ())}
    )
    state, active = advance(initial, journey(), 60_000, content)
    assert active is not None and active.meta["duration_ms"] == 30_000
    state, active = advance(state, active, 90_000, content)
    assert state.current_realm_id == ORIGIN
    assert state.skills_xp["travel"] == 120
    assert active is not None and active.meta["duration_ms"] == 60_000


def test_decimal_ties_and_rounding_are_exact() -> None:
    """Binary float artifacts cannot break ties or add a supply/remove XP."""
    graph = replace(
        CONTENT,
        map=MapPack(
            edges=(
                edge("a", "a", "b", 0.1),
                edge("b", "b", "d", 0.2),
                edge("z", "a", "c", 0.15),
                edge("y", "c", "d", 0.15),
            )
        ),
    )
    assert [
        s["edge_id"]
        for s in route("a", "d", CONTENT.progression.visit_profile, 1, graph)
    ] == ["a", "b"]
    definition = CONTENT.map.edges[0]
    definition = definition.model_copy(
        update={
            "base_time_s": 0.29,
            "supplies": (definition.supplies[0].model_copy(update={"quantity": 25}),),
        }
    )
    form = CONTENT.estate_forms[0]
    assert form.travel_profile is not None
    form = form.model_copy(
        update={
            "travel_profile": form.travel_profile.model_copy(
                update={"supply_mult": 1.1}
            )
        }
    )
    content = replace(
        CONTENT,
        map=MapPack(edges=(definition,)),
        _forms_by_id=MappingProxyType({**CONTENT._forms_by_id, form.id: form}),
        progression=CONTENT.progression.model_copy(
            update={"travel_xp_per_second": 100}
        ),
    )
    state = replace(
        traveller(50),
        gear_modifiers=(Modifier(type=ModifierType.SUPPLY_REDUCTION_PCT, value=10),),
    )
    state, active = advance(state, journey(count=1), 290, content)
    assert active is None
    assert state.skills_xp["travel"] == 29
    assert state.inventory["item.fake_sprig"] == 25


def test_arrival_uses_destination_project_stack() -> None:
    """Journey snapshots carry project tags into the next step's realm sources."""
    from app.content.schemas import DecayStage
    from app.engine.travel import arrival_state

    node_id = CONTENT.realm(DESTINATION).starting_node_id
    initial = replace(
        traveller(),
        realm_stack_tags=("access.fake",),
        realm_states={DESTINATION: (node_id, DecayStage.FALTERING, ("bonus.fake",))},
    )
    arrived = arrival_state(initial, DESTINATION, "visit", CONTENT)
    assert arrived.realm_stack_tags == ("bonus.fake",)
    assert arrived.realm_stage == DecayStage.FALTERING
    assert arrived.current_realm_id == DESTINATION
