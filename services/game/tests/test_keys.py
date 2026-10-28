"""Exploration discovery, private finite access and transition lifecycle."""

import random
import uuid
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock, action_client, anyio_backend
from test_consumables_hp import NOW, state
from world_helpers import create_world_character

from app.content.loader import ContentIndex
from app.content.runtime import CONTENT
from app.content.schemas import (
    CombatDiscovery,
    ExplorationPack,
    IntegerRange,
    Modifier,
    ModifierType,
)
from app.engine.consumables import transfer_stack
from app.engine.core import (
    ActiveAction,
    BeltStack,
    InstanceState,
    StopReason,
    effective_cycle_time,
    resolve,
    resolve_caps,
)
from app.engine.equipment import EquipmentError, change_equipment
from app.engine.exploration import discover, template_action, tier_benefit
from app.main import app
from app.models import ActiveActionRecord, Character, ItemInstance, RealmState
from app.services.realms import finalize_realm, start_transition

__all__ = ["action_client", "anyio_backend"]
ApiFixture = tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]]
EXPEDITION = CONTENT.exploration.actions[0].id
REALM = "realm.verdant_vale"


def exploration_content(chance: float = 1, count: int = 1) -> ContentIndex:
    """Offer a short deterministic expedition and independently ranged keys."""
    action = CONTENT.exploration.actions[0].model_copy(
        update={"discovery_chance": chance, "base_cycle_ms": 1000}
    )
    template = CONTENT.exploration.templates[0].model_copy(
        update={"keys": IntegerRange(min=count, max=count)}
    )
    content = CONTENT.with_overrides(actions=(action,))
    nodes = {
        node.id: node.model_copy(update={"actions": (*node.actions, EXPEDITION)})
        for node in content.development_nodes
    }
    return replace(
        content,
        exploration=ExplorationPack(actions=(action,), templates=(template,)),
        _nodes_by_id=MappingProxyType(nodes),
    )


def key_state(
    content: ContentIndex, *, combat: bool = False, uses: int = 2
) -> InstanceState:
    """Roll a private test resource without creating a public content action."""
    template = content.exploration.templates[0]
    if combat:
        template = template.model_copy(
            update={
                "kind": "combat",
                "gather": None,
                "combat": CombatDiscovery(combatant_id=content.combatants[0].id),
            }
        )
    action = template_action(template, content, random.Random(1))
    return InstanceState(
        str(uuid.uuid4()),
        template.id,
        REALM,
        {"action": action.model_dump(mode="json")},
        uses,
        uses,
        "active",
        NOW,
    )


def test_keys_never_stack_and_all_gains_count_instance_slots() -> None:
    content = exploration_content(count=3)
    initial = replace(state(), current_realm_id=REALM)
    result, _, summary = resolve(
        initial,
        ActiveAction(EXPEDITION, NOW, NOW),
        content,
        NOW + timedelta(seconds=1),
        random.Random(3),
    )
    assert len(result.instances) == 3
    assert len({key.id for key in result.instances}) == 3
    assert summary.details["keys_created"] == 3
    limit = resolve_caps(initial, content).inventory_slots
    full = replace(
        initial,
        instances=tuple(replace(result.instances[0], id=str(i)) for i in range(limit)),
    )
    result, remaining, summary = resolve(
        full,
        ActiveAction(EXPEDITION, NOW, NOW),
        content,
        NOW + timedelta(seconds=1),
        random.Random(3),
    )
    assert result.instances == full.instances and remaining is None
    assert summary.details["keys_lost"] == 3
    assert summary.stop_reason == StopReason.INVENTORY_FULL
    # Commodity gathering must also count trophy slots.
    gather = content.action("gathering.fake_sprigs").model_copy(
        update={"requires": content.action("refining.fake_plank").requires}
    )
    result, _, summary = resolve(
        full,
        ActiveAction(gather.id, NOW, NOW),
        content.with_overrides(actions=(gather,)),
        NOW + timedelta(seconds=5),
        random.Random(2),
    )
    assert not result.inventory and summary.overflowed_items


def test_rolled_values_independent_across_keys_of_one_discovery() -> None:
    content = exploration_content(count=20)
    initial = replace(state(), current_realm_id=REALM)
    found, lost, count = discover(
        initial, content.action(EXPEDITION), content, NOW, random.Random(7), 100
    )
    assert count == 1 and lost == 0 and len(found) == 20
    assert len({key.uses_total for key in found}) > 1
    quantities = [key.payload["action"]["outputs"][0]["quantity_min"] for key in found]
    assert len(set(quantities)) > 1
    assert all(
        key.payload["action"]["outputs"][0]["quantity_max"] == quantity
        for key, quantity in zip(found, quantities, strict=True)
    )
    assert len({id(key.payload) for key in found}) == 20


def test_discovery_rate_seeded_long_run_within_tolerance() -> None:
    content = exploration_content(chance=0.03)
    initial = replace(state(), current_realm_id=REALM)
    rng = random.Random(9001)
    discoveries = sum(
        discover(initial, content.action(EXPEDITION), content, NOW, rng, 100)[2]
        for _ in range(20000)
    )
    assert abs(discoveries / 20000 - 0.03) < 0.004


def test_binding_uses_clip_batch_and_depletion() -> None:
    content = exploration_content()
    key = key_state(content, uses=2)
    initial = replace(state(), current_realm_id=REALM, instances=(key,))
    active = ActiveAction(
        key.template_id,
        NOW,
        NOW,
        {"key_id": key.id, "key_action": key.payload["action"]},
    )
    result, remaining, summary = resolve(
        initial, active, content, NOW + timedelta(hours=1), random.Random(1)
    )
    assert summary.cycles_completed == 2 and remaining is None
    assert summary.stop_reason == StopReason.KEY_DEPLETED
    assert result.instances[0].state == "depleted"
    assert result.instances[0].bound_at == NOW
    assert result.instances[0].uses_remaining == 0
    assert result.skills_xp["gathering"] == 20


def test_exploration_tier_speed_is_group_p_and_belt_shapes_discovery() -> None:
    content = exploration_content(chance=0.5)
    initial = replace(
        state(),
        current_realm_id=REALM,
        skill_levels={"exploration": 50},
        gear_modifiers=(
            Modifier(
                type=ModifierType.CYCLE_SPEED_PCT, skill_id="exploration", value=20
            ),
        ),
    )
    assert effective_cycle_time(content.action(EXPEDITION), initial, content) == int(
        1000 / (1.2 * 1.05)
    )
    initial = replace(
        initial,
        skill_levels={},
        gear_modifiers=(),
        belt={0: BeltStack("item.fake_buff", 2, {"buff_missing": True})},
    )

    # A fixed roll between .5 and .75 proves the authored +50% chance effect.
    class Rng:
        def random(self) -> float:
            return 0.6

        def randint(self, a: int, b: int) -> int:
            return a

    result, _, summary = resolve(
        initial,
        ActiveAction(EXPEDITION, NOW, NOW),
        content,
        NOW + timedelta(seconds=1),
        Rng(),
    )
    assert summary.items_consumed == {"item.fake_buff": 1}
    assert summary.details["discoveries"] == 1
    assert result.belt[0].quantity == 1 and "item.fake_buff" in result.buff_expiries
    _, _, without = resolve(
        replace(initial, belt={}),
        ActiveAction(EXPEDITION, NOW, NOW),
        content,
        NOW + timedelta(seconds=1),
        Rng(),
    )
    assert without.details["discoveries"] == 0


def test_equipment_and_consumable_returns_share_instance_capacity() -> None:
    content = exploration_content()
    initial = state()
    key = key_state(content)
    limit = resolve_caps(initial, content).inventory_slots
    initial = replace(
        initial, instances=tuple(replace(key, id=str(i)) for i in range(limit))
    )
    with pytest.raises(EquipmentError, match="displaced"):
        change_equipment(initial, {"cape": "item.fake_cape"}, "cape", None, content)
    with pytest.raises(EquipmentError, match="returned"):
        transfer_stack(initial, ("item.fake_food", 1), None, 0, content)
    # A transfer that frees a stack remains legal even when instances exceed cap.
    inventory, equipped = change_equipment(
        replace(initial, inventory={"item.fake_cape": 1}),
        {},
        "cape",
        "item.fake_cape",
        content,
    )
    assert inventory == {} and equipped == {"cape": "item.fake_cape"}


def test_combat_keys_charge_initial_and_each_spawn_and_finish_last_encounter() -> None:
    content = exploration_content()
    opponent = content.combatants[0].model_copy(
        update={"max_hp": 1, "respawn_ms": 1, "power": 1}
    )
    content = replace(content, combatants=(opponent,))
    key = key_state(content, combat=True, uses=2)
    initial = replace(state(), current_realm_id=REALM, instances=(key,))
    active = ActiveAction(
        key.template_id,
        NOW,
        NOW,
        {"key_id": key.id, "key_action": key.payload["action"]},
    )
    initial, pending, summary = resolve(initial, active, content, NOW, random.Random(5))
    assert pending is not None and summary.cycles_completed == 0
    assert (
        initial.instances[0].uses_remaining == 1
        and initial.instances[0].bound_at == NOW
    )
    result, remaining, summary = resolve(
        initial, pending, content, NOW + timedelta(hours=1), random.Random(5)
    )
    assert remaining is None and summary.stop_reason == StopReason.KEY_DEPLETED
    assert summary.details["kills"] == 2 and result.instances[0].uses_remaining == 0
    assert 0 < summary.elapsed_ms < 3600000
    _, _, at_kill = resolve(
        initial,
        pending,
        content,
        NOW + timedelta(milliseconds=summary.elapsed_ms),
        random.Random(5),
    )
    assert at_kill.stop_reason == StopReason.KEY_DEPLETED
    assert at_kill.details["kills"] == 2
    assert at_kill.elapsed_ms == summary.elapsed_ms
    _, before, before_kill = resolve(
        initial,
        pending,
        content,
        NOW + timedelta(milliseconds=summary.elapsed_ms - 1),
        random.Random(5),
    )
    assert before is not None and before_kill.details["kills"] == 1
    assert before.last_resolved_at == NOW + timedelta(
        milliseconds=before_kill.elapsed_ms
    )


async def discover_api(fixture: ApiFixture, monkeypatch: pytest.MonkeyPatch) -> str:
    """Create a key through the real authenticated exploration resolver."""
    client, _, clock, headers = fixture
    monkeypatch.setattr(app.state, "content", exploration_content())
    response = await client.post(
        "/actions/start", headers=headers, json={"action_id": EXPEDITION}
    )
    assert response.status_code == 200, response.text
    clock.advance(timedelta(milliseconds=response.json()["cycle_ms"]))
    response = await client.post("/actions/stop", headers=headers)
    assert response.status_code == 200, response.text
    response = await client.get("/keys/me", headers=headers)
    assert response.status_code == 200, response.text
    key = response.json()["keys"][-1]
    assert key["discovered_by_name"] == "Action Hero" and key["realm_id"] == REALM
    return str(key["id"])


@pytest.mark.anyio
async def test_key_api_private_binding_depletion_disposal_and_commodity_rejection(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, clock, headers = action_client
    identifier = await discover_api(action_client, monkeypatch)
    response = await client.get(
        f"/market/book/{identifier}",
        headers=headers,
    )
    assert (
        response.status_code == 404
        and response.json()["error"]["code"] == "UNKNOWN_ITEM"
    )
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert response.status_code == 200, response.text
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None and key.bound_at is not None
        uses = key.uses_total
    clock.advance(timedelta(hours=1))
    response = await client.get("/actions/poll", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["stop_reason"] == "KEY_DEPLETED"
    assert response.json()["since_last"]["cycles_completed"] == uses
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "KEY_DEPLETED"
    )
    response = await client.delete(f"/keys/{identifier}", headers=headers)
    assert response.status_code == 204
    assert (await client.get("/keys/me", headers=headers)).json()["keys"] == []
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert response.status_code == 404


@pytest.mark.parametrize("tick_path", [False, True])
@pytest.mark.anyio
async def test_transition_deprecation_and_invalidation_stops_running_key(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch, tick_path: bool
) -> None:
    client, factory, clock, headers = action_client
    identifier = await discover_api(action_client, monkeypatch)
    with factory() as session:
        discovered = session.get(ItemInstance, uuid.UUID(identifier))
        assert discovered is not None
        discovered.uses_total = discovered.uses_remaining = 4
        session.commit()
    content = app.state.content
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert response.status_code == 200
    with factory() as session:
        realm = session.get(RealmState, REALM)
        assert realm is not None
        if tick_path:
            from app.services.realm_ticks import (
                complete_tick_transition,
                load_context,
                persist_context,
            )

            context = load_context(session, realm, None, content)
            start_transition(
                realm,
                realm.current_node_id,
                "upgrade",
                clock.now,
                content,
                keys=context.keys,
            )
        else:
            start_transition(
                realm, realm.current_node_id, "upgrade", clock.now, content
            )
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None and key.state == "deprecated"
        due = clock.now + timedelta(days=content.economy.transition.duration_days)
        if tick_path:
            complete_tick_transition(context, realm, due, content)
            persist_context(session, realm, context)
        else:
            finalize_realm(session, REALM, due, content)
        session.commit()
        assert key.state == "invalid"
        character = session.scalar(select(Character))
        assert (
            character is not None
            and session.get(ActiveActionRecord, character.id) is not None
        )
    clock.advance(due - clock.now)
    response = await client.get("/actions/poll", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["stop_reason"] == "KEY_DEPLETED"
    assert response.json()["since_last"]["cycles_completed"] == key.uses_total
    assert (await client.get("/actions/poll", headers=headers)).json()[
        "stop_reason"
    ] is None
    response = await client.delete(f"/keys/{identifier}", headers=headers)
    assert response.status_code == 204


@pytest.mark.anyio
async def test_key_start_gates_and_discoverer_snapshot(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inline access replaces public offering and validates realm, level and tool."""
    client, factory, _, headers = action_client
    identifier = await discover_api(action_client, monkeypatch)
    with factory() as session:
        character = session.scalar(select(Character))
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert character is not None and key is not None
        character.name = "Renamed Hero"
        original = dict(key.payload["action"])
        key.payload = {**key.payload, "action": {**original, "unlock_level": 10}}
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "INSUFFICIENT_LEVEL"
    )
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None and key.bound_at is None
        key.payload = {
            **key.payload,
            "action": {**original, "requires": {"tool_class": "fake_pickaxe"}},
        }
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "MISSING_TOOL"
    )
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        character = session.scalar(select(Character))
        assert key is not None and character is not None
        key.payload = {**key.payload, "action": original}
        character.current_realm_id = "realm.ashen_reach"
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "KEY_WRONG_REALM"
    )
    keys = (await client.get("/keys/me", headers=headers)).json()["keys"]
    assert keys[0]["discovered_by_name"] == "Action Hero"
    with factory() as session:
        character = session.scalar(select(Character))
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert character is not None and key is not None
        character.current_realm_id = REALM
        key.state = "deprecated"
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert response.status_code == 200, response.text
    # An arbitrary client cannot supply its own inline projection.
    response = await client.post(
        "/actions/start",
        headers=headers,
        json={"key_id": identifier, "key_action": original},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_other_character_cannot_see_use_or_delete_a_key(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Private action access and deletion both require the current holder."""
    from test_actions import _token

    client, factory, _, _ = action_client
    identifier = await discover_api(action_client, monkeypatch)
    other = {"Authorization": f"Bearer {_token()}"}
    response = await create_world_character(
        client, factory, headers=other, name="Other Hero", realm_id=REALM
    )
    assert response.status_code == 201
    assert (await client.get("/keys/me", headers=other)).json()["keys"] == []
    response = await client.post(
        "/actions/start", headers=other, json={"key_id": identifier}
    )
    assert (
        response.status_code == 404
        and response.json()["error"]["code"] == "UNKNOWN_KEY"
    )
    response = await client.delete(f"/keys/{identifier}", headers=other)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_combat_key_start_charges_spawn_and_locks_equipment(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The initial spawn is persisted immediately and gear guards use private combat."""
    from app.engine.exploration import template_action

    client, factory, _, headers = action_client
    identifier = await discover_api(action_client, monkeypatch)
    content = app.state.content
    template = content.exploration.templates[0].model_copy(
        update={
            "kind": "combat",
            "gather": None,
            "combat": CombatDiscovery(combatant_id=content.combatants[0].id),
        }
    )
    inline = template_action(template, content, random.Random(1))
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        character = session.scalar(select(Character))
        assert key is not None and character is not None
        key.payload = {"action": inline.model_dump(mode="json")}
        key.uses_total = key.uses_remaining = 1
        character.hp = 0
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "INSUFFICIENT_HP"
    )
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 110
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert response.status_code == 200, response.text
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None and key.uses_remaining == 0 and key.state == "depleted"
        assert key.bound_at is not None
    for path, method, body in (
        ("/equipment/unequip", "post", {"slot": "cape"}),
        ("/equipment/utility", "put", {"item_id": None, "quantity": 0}),
        ("/equipment/belt/0", "put", {"item_id": None, "quantity": 0}),
    ):
        response = await client.request(method, path, headers=headers, json=body)
        assert (
            response.status_code == 409
            and response.json()["error"]["code"] == "EQUIPMENT_IN_COMBAT"
        )
    response = await client.get("/actions/poll", headers=headers)
    assert response.status_code == 200 and response.json()["active"] is not None
    # Deleting a running final encounter does not leave a dangling FK/action.
    response = await client.delete(f"/keys/{identifier}", headers=headers)
    assert response.status_code == 204
    assert (await client.get("/actions/poll", headers=headers)).json()["active"] is None


def test_rarity_weight_shifts_and_template_tag_filtering() -> None:
    """Tier benefits, gating tiers and active consumables favor rarer templates."""
    from app.content.schemas import DiscoveryConsumableEffect, DiscoveryWeight

    content = exploration_content()
    common = content.exploration.templates[0]
    rare = common.model_copy(update={"id": "placeholder.rare", "rarity": 3})
    action = content.exploration.actions[0].model_copy(
        update={
            "table": (
                DiscoveryWeight(template_id=common.id, weight=1),
                DiscoveryWeight(template_id=rare.id, weight=1),
            ),
            "consumable_effects": (
                DiscoveryConsumableEffect(item_id="item.fake_buff", weight_shift=1),
            ),
        }
    )
    content = replace(
        content,
        exploration=ExplorationPack(actions=(action,), templates=(common, rare)),
    )

    class Rng:
        def random(self) -> float:
            return 0.4

        def randint(self, a: int, b: int) -> int:
            return a

    initial = replace(state(), current_realm_id=REALM)
    assert (
        discover(initial, action, content, NOW, Rng(), 100)[0][0].template_id
        == common.id
    )
    for strengthened in (
        replace(initial, skill_levels={"exploration": 95}),
        replace(initial, skill_levels={"gathering": 95}),
        replace(initial, buff_expiries={"item.fake_buff": NOW + timedelta(seconds=1)}),
    ):
        assert (
            discover(strengthened, action, content, NOW, Rng(), 100)[0][0].template_id
            == rare.id
        )
    rare = rare.model_copy(update={"requires_realm_tags": ("ashen",)})
    content = replace(
        content,
        exploration=ExplorationPack(actions=(action,), templates=(common, rare)),
    )
    assert (
        discover(
            replace(initial, skill_levels={"exploration": 95}),
            action,
            content,
            NOW,
            Rng(),
            100,
        )[0][0].template_id
        == common.id
    )


@pytest.mark.anyio
async def test_postgres_key_polls_serialize_uses_and_rewards(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A waiting key poll cannot spend the same gathering use twice."""
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text
    from test_estates import _wait_for_postgres_blocker

    from app.services import actions as action_service

    client, factory, clock, headers = action_client
    with factory() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("requires PostgreSQL row locks")
    identifier = await discover_api(action_client, monkeypatch)
    started = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert started.status_code == 200
    clock.advance(timedelta(milliseconds=started.json()["cycle_ms"]))
    entering = threading.Event()
    worker_pids: list[int] = []
    original = action_service.lock_character_and_load_action

    def observe(session: Session, character_id: uuid.UUID) -> ActiveActionRecord | None:
        session.execute(text("SET LOCAL statement_timeout = '10s'"))
        worker_pids.append(session.scalar(text("SELECT pg_backend_pid()")))
        entering.set()
        return original(session, character_id)

    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        key = first.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None and key.holder_character_id is not None
        before = key.uses_remaining
        resolved = action_service.resolve_character(
            first, key.holder_character_id, clock.now, app.state.content
        )
        assert resolved.result.cycles_completed == 1
        blocker = first.scalar(text("SELECT pg_backend_pid()"))
        monkeypatch.setattr(action_service, "lock_character_and_load_action", observe)
        future = pool.submit(asyncio.run, client.get("/actions/poll", headers=headers))
        try:
            assert entering.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pids[-1], blocker)
            assert not future.done()
        finally:
            first.commit()
        response = future.result(timeout=10)
    assert response.status_code == 200
    assert response.json()["since_last"]["cycles_completed"] == 1
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert key is not None and key.uses_remaining == before - 1
    assert (await client.get("/actions/poll", headers=headers)).json()["since_last"][
        "cycles_completed"
    ] == 0


@pytest.mark.parametrize(
    ("defect", "message"),
    [
        ("range", "range must ascend"),
        ("kind", "payload must match kind"),
        ("chance", "less than or equal to 1"),
        ("extra", "Extra inputs are not permitted"),
        ("template", "unknown discovery template"),
        ("tag", "unknown discovery tag"),
        ("skill", "unknown gathering skill"),
        ("combatant", "unknown discovery combatant"),
        ("consumable", "requires a buff item"),
    ],
)
def test_exploration_pack_validation(tmp_path: Path, defect: str, message: str) -> None:
    """Boot rejects malformed exploration records and dangling references."""
    import json
    import shutil

    from app.config import CONTENT_DIR
    from app.content.loader import ContentError, load_content

    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "exploration.json"
    data = json.loads(path.read_text())
    template, action = data["templates"][0], data["actions"][0]
    if defect == "range":
        template["uses"] = {"min": 2, "max": 1}
    elif defect == "kind":
        template["kind"] = "combat"
    elif defect == "chance":
        action["discovery_chance"] = 2
    elif defect == "extra":
        action["unrecognized"] = 1
    elif defect == "template":
        action["table"][0]["template_id"] = "unknown"
    elif defect == "tag":
        template["requires_realm_tags"] = ["unknown"]
    elif defect == "skill":
        template["gather"]["skill_id"] = "unknown"
    elif defect == "combatant":
        template.update(kind="combat", gather=None, combat={"combatant_id": "unknown"})
    else:
        action["consumable_effects"][0]["item_id"] = "item.fake_food"
    path.write_text(json.dumps(data))
    with pytest.raises(ContentError, match=message):
        load_content(directory)


@pytest.mark.anyio
async def test_postgres_transition_completes_while_key_owner_waits_for_realm(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Realm invalidation never locks the waiting character in reverse order."""
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text
    from test_estates import _wait_for_postgres_blocker

    from app.services import actions as action_service
    from app.services.realms import _finalize_locked_realm

    client, factory, clock, headers = action_client
    with factory() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("requires PostgreSQL row locks")
    identifier = await discover_api(action_client, monkeypatch)
    response = await client.post(
        "/actions/start", headers=headers, json={"key_id": identifier}
    )
    assert response.status_code == 200
    clock.advance(timedelta(milliseconds=response.json()["cycle_ms"]))
    original = action_service.lock_character_and_load_action
    entering = threading.Event()
    pids: list[int] = []

    def observed(
        session: Session, character_id: uuid.UUID
    ) -> ActiveActionRecord | None:
        session.execute(text("SET LOCAL statement_timeout = '10s'"))
        record = original(session, character_id)
        pids.append(session.scalar(text("SELECT pg_backend_pid()")))
        entering.set()
        return record

    monkeypatch.setattr(action_service, "lock_character_and_load_action", observed)
    content = app.state.content
    instant = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "transition": content.economy.transition.model_copy(
                    update={"duration_days": 0}
                )
            }
        ),
    )
    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        realm = first.scalar(
            select(RealmState).where(RealmState.id == REALM).with_for_update()
        )
        assert realm is not None
        blocker = first.scalar(text("SELECT pg_backend_pid()"))
        future = pool.submit(asyncio.run, client.get("/actions/poll", headers=headers))
        try:
            assert entering.wait(timeout=5)
            _wait_for_postgres_blocker(factory, pids[-1], blocker)
            start_transition(
                realm, realm.current_node_id, "upgrade", clock.now, instant
            )
            _finalize_locked_realm(first, realm, clock.now, instant)
        finally:
            first.commit()
        response = future.result(timeout=10)
    assert response.status_code == 200, response.text
    assert response.json()["stop_reason"] == "KEY_INVALIDATED"
    assert response.json()["since_last"]["cycles_completed"] == 1
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        assert (
            key is not None
            and key.state == "invalid"
            and key.uses_remaining == key.uses_total - 1
        )


@pytest.mark.anyio
async def test_discovery_during_pending_transition_is_deprecated(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resources found during the warning window share the realm's lifecycle."""
    client, factory, clock, headers = action_client
    content = exploration_content()
    monkeypatch.setattr(app.state, "content", content)
    with factory() as session:
        realm = session.get(RealmState, REALM)
        assert realm is not None
        start_transition(realm, realm.current_node_id, "upgrade", clock.now, content)
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"action_id": EXPEDITION}
    )
    assert response.status_code == 200
    clock.advance(timedelta(milliseconds=response.json()["cycle_ms"]))
    response = await client.post("/actions/stop", headers=headers)
    assert response.json()["since_last"]["cycles_completed"] == 1
    response = await client.get("/keys/me", headers=headers)
    assert response.status_code == 200
    assert len(response.json()["keys"]) == 1
    assert response.json()["keys"][0]["state"] == "deprecated"


@pytest.mark.anyio
async def test_market_collection_and_realm_purchase_count_instance_slots(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A trophy occupies the last slot for both market receipt paths."""
    from fastapi import HTTPException

    from app.models import Currency, MarketOrder, RealmStore
    from app.services.order_book import collect_order
    from app.services.trade import trade

    _, factory, clock, _ = action_client
    identifier = await discover_api(action_client, monkeypatch)
    content = app.state.content
    # Remove estate/node effects from the cap and give the realm market access.
    content = replace(
        content,
        caps=content.caps.model_copy(update={"inventory_slots": 1}),
        tags=tuple(
            tag.model_copy(
                update={
                    "effects": tag.effects.model_copy(update={"market_access": True})
                }
            )
            for tag in content.tags
        ),
    )
    with factory() as session:
        key = session.get(ItemInstance, uuid.UUID(identifier))
        character = session.scalar(select(Character))
        realm = session.get(RealmState, REALM)
        assert key is not None and character is not None and realm is not None
        key.state = "invalid"
        wallet = session.get(Currency, character.id)
        assert wallet is not None
        wallet.gold = 10000
        session.add(
            RealmStore(realm_id=REALM, item_id="item.fake_plank", quantity_milli=10000)
        )
        order = MarketOrder(
            character_id=character.id,
            side="buy",
            item_id="item.fake_plank",
            unit_price=1,
            quantity=1,
            quantity_remaining=0,
            fill_items=1,
            status="collectable",
            realm_id=REALM,
            created_at=clock.now,
            expires_at=clock.now + timedelta(days=1),
        )
        session.add(order)
        session.flush()
        assert collect_order(session, character, order, clock.now, content) == (0, 0)
        assert order.fill_items == 1 and order.status == "collectable"
        with pytest.raises(HTTPException) as rejected:
            trade(
                session, character, realm, content, "item.fake_plank", "buy", 1, 10000
            )
        assert (
            cast(dict[str, Any], rejected.value.detail)["error"]["code"]
            == "INVENTORY_FULL"
        )
        session.delete(key)
        session.flush()
        assert collect_order(session, character, order, clock.now, content) == (1, 0)


def test_partial_exploration_does_not_activate_belt_or_create_reward_details() -> None:
    """Unfinished expeditions produce no loot, consumptions or empty feed entries."""
    content = exploration_content()
    initial = replace(
        state(),
        current_realm_id=REALM,
        belt={0: BeltStack("item.fake_buff", 1, {"buff_missing": True})},
    )
    result, active, summary = resolve(
        initial,
        ActiveAction(EXPEDITION, NOW, NOW),
        content,
        NOW + timedelta(milliseconds=500),
        random.Random(1),
    )
    assert active is not None and summary.cycles_completed == 0
    assert result == initial and summary.details == {
        "level_ups": {},
        "stop_reason": None,
    }


def test_combat_loot_counts_instance_slots() -> None:
    """A paid encounter cannot put commodity loot into a trophy's occupied slot."""
    from app.content.schemas import Drop

    content = exploration_content()
    opponent = content.combatants[0].model_copy(
        update={
            "max_hp": 1,
            "drops": (
                Drop(
                    item_id="item.fake_sprig", quantity_min=1, quantity_max=1, chance=1
                ),
            ),
        }
    )
    content = replace(content, combatants=(opponent,))
    key = key_state(content, combat=True, uses=1)
    initial = replace(state(), current_realm_id=REALM, instances=(key,))
    # Fill every other slot with invalid trophies, which count equally.
    initial = replace(
        initial,
        instances=(
            key,
            *(
                replace(key, id=str(i), state="invalid")
                for i in range(resolve_caps(initial, content).inventory_slots - 1)
            ),
        ),
    )
    active = ActiveAction(
        key.template_id,
        NOW,
        NOW,
        {"key_id": key.id, "key_action": key.payload["action"]},
    )
    result, remaining, summary = resolve(
        initial, active, content, NOW + timedelta(hours=1), random.Random(5)
    )
    assert remaining is None and summary.stop_reason == StopReason.INVENTORY_FULL
    assert not result.inventory and summary.overflowed_items == {"item.fake_sprig": 1}
    assert result.instances[0].uses_remaining == 0


def test_exploration_tier_bonus_adds_to_rolled_key_count() -> None:
    """Tier two grants the authored bonus in addition to the template count."""
    content = exploration_content(count=3)
    initial = replace(state(), current_realm_id=REALM, skill_levels={"exploration": 50})
    found, lost, discoveries = discover(
        initial, content.action(EXPEDITION), content, NOW, random.Random(2), 100
    )
    assert discoveries == 1 and lost == 0
    assert len(found) == 3 + tier_benefit(initial, content).keys_per_discovery_bonus
    assert all(uuid.UUID(key.id).version == 4 for key in found)


def test_running_key_loses_requirement_when_holder_leaves_realm() -> None:
    """Resolve-time presence checks stop a previously started private action."""
    content = exploration_content()
    key = key_state(content)
    initial = replace(state(), current_realm_id="realm.ashen_reach", instances=(key,))
    active = ActiveAction(
        key.template_id,
        NOW,
        NOW,
        {"key_id": key.id, "key_action": key.payload["action"]},
    )
    result, remaining, summary = resolve(
        initial, active, content, NOW + timedelta(hours=1), random.Random(1)
    )
    assert remaining is None and summary.stop_reason == StopReason.REQUIREMENT_LOST
    assert summary.cycles_completed == 0 and result.instances == initial.instances


@pytest.mark.parametrize("combat", [False, True])
def test_key_invalidation_offline_matches_polling_across_completion(
    combat: bool,
) -> None:
    """Both resolvers credit exactly the same work before a transition cutoff."""
    content = exploration_content()
    key = key_state(content, combat=combat, uses=100)
    cutoff = NOW + timedelta(seconds=11)
    initial = replace(state(), current_realm_id=REALM, instances=(key,))
    active = ActiveAction(
        key.template_id,
        NOW,
        NOW,
        {"key_id": key.id, "key_action": key.payload["action"]},
    )
    invalid = replace(
        initial, instances=(replace(key, state="invalid", invalidated_at=cutoff),)
    )
    offline, _, summary = resolve(
        invalid, active, content, NOW + timedelta(seconds=30), random.Random(1)
    )
    current, running = initial, active
    cycles = 0
    for seconds in (3, 6, 9, 30):
        if seconds == 30:
            current = replace(
                current,
                instances=tuple(
                    replace(key, state="invalid", invalidated_at=cutoff)
                    for key in current.instances
                ),
            )
        current, following, part = resolve(
            current,
            running,
            content,
            NOW + timedelta(seconds=seconds),
            random.Random(1),
        )
        cycles += part.cycles_completed
        if following is not None:
            running = following
    assert following is None
    assert summary.stop_reason == part.stop_reason == StopReason.KEY_INVALIDATED
    assert cycles == summary.cycles_completed
    assert current == offline
    assert summary.elapsed_ms <= 11000


@pytest.mark.anyio
@pytest.mark.parametrize("complete", [False, True])
async def test_historical_discoveries_classified_across_transition_windows(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch, complete: bool
) -> None:
    """Unpolled discoveries retain lifecycle state after pending data is cleared."""
    client, factory, clock, headers = action_client
    content = exploration_content()
    # Start before the transition and let one long batch straddle both boundaries.
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "transition": content.economy.transition.model_copy(
                    update={"duration_days": (2 if complete else 10) / 86400}
                )
            }
        ),
    )
    monkeypatch.setattr(app.state, "content", content)
    response = await client.post(
        "/actions/start", headers=headers, json={"action_id": EXPEDITION}
    )
    assert response.status_code == 200
    began = clock.now
    with factory() as session:
        realm = session.get(RealmState, REALM)
        assert realm is not None
        start_transition(
            realm,
            realm.current_node_id,
            "upgrade",
            began + timedelta(seconds=2 if complete else -1),
            content,
        )
        session.commit()
    clock.advance(timedelta(seconds=5 if complete else 3))
    response = await client.post("/actions/stop", headers=headers)
    assert response.status_code == 200, response.text
    keys = (await client.get("/keys/me", headers=headers)).json()["keys"]
    assert len(keys) == (5 if complete else 3)
    for key in keys:
        from datetime import datetime

        created = datetime.fromisoformat(key["created_at"])
        if complete and created < began + timedelta(seconds=4):
            assert key["state"] == "invalid"
            assert datetime.fromisoformat(key["invalidated_at"]) == began + timedelta(
                seconds=4
            )
        else:
            assert key["state"] == ("active" if complete else "deprecated")


def test_combat_key_depletes_before_invalidation_cutoff() -> None:
    """The last paid encounter finishing first keeps its original stop and timing."""
    content = exploration_content()
    key = key_state(content, combat=True, uses=1)
    cutoff = NOW + timedelta(hours=1)
    initial = replace(
        state(),
        current_realm_id=REALM,
        instances=(replace(key, state="invalid", invalidated_at=cutoff),),
    )
    active = ActiveAction(
        key.template_id,
        NOW,
        NOW,
        {"key_id": key.id, "key_action": key.payload["action"]},
    )
    result, remaining, summary = resolve(
        initial, active, content, NOW + timedelta(hours=2), random.Random(5)
    )
    assert remaining is None and summary.stop_reason == StopReason.KEY_DEPLETED
    assert summary.details["kills"] == 1 and summary.elapsed_ms < 3600000
    assert result.instances[0].uses_remaining == 0
    assert result.instances[0].invalidated_at == cutoff
