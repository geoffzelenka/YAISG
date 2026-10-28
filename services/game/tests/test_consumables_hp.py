"""Consumable holders, bonus expiry and lazy health behavior."""

import asyncio
import random
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import MappingProxyType

import pytest
from httpx import AsyncClient
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock, action_client, anyio_backend

from app.content.lint import consumable_bound
from app.content.runtime import CONTENT
from app.content.schemas import (
    Armour,
    CapType,
    Consumable,
    Equipment,
    Modifier,
    ModifierType,
    Requirements,
)
from app.engine.consumables import belt_capacity, transfer_stack, validate_consumable
from app.engine.core import ActiveAction, CharacterState, effective_xp, resolve
from app.engine.equipment import EquipmentError
from app.engine.health import maximum_hp, regenerate_hp
from app.main import app
from app.models import (
    Character,
    CharacterBelt,
    CharacterBuff,
    CharacterEquipment,
    Inventory,
)
from app.services.actions import load_character_state

__all__ = ["action_client", "anyio_backend"]
ApiFixture = tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]]
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def state() -> CharacterState:
    """Construct a pure state without estate or realm speed modifiers."""
    return CharacterState(
        {},
        {},
        {},
        0,
        "form.camp",
        "node.verdant_t1",
        current_realm_id="realm.ashen_reach",
        estate_realm_id="realm.verdant_vale",
    )


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        '{"heal":1,"utility_for":"melee"}',
        '{"heal":0}',
        '{"utility_for":"travel"}',
        '{"buff":{"duration_ms":0,"modifiers":[]}}',
    ],
)
def test_consumable_content_validation(payload: str) -> None:
    """Consumables require exactly one supported purpose and valid magnitudes."""
    with pytest.raises(ValidationError):
        Consumable.model_validate_json(payload)


@pytest.mark.parametrize(
    "item,trigger",
    [
        ("item.fake_food", {"hp_below_pct": 0}),
        ("item.fake_food", {"hp_below_pct": 101}),
        ("item.fake_food", {"hp_below_pct": True}),
        ("item.fake_food", {"buff_missing": True}),
        ("item.fake_buff", {"buff_missing": False}),
        ("item.fake_buff", {"buff_missing": 1}),
        ("item.fake_buff", {"buff_missing": True, "hp_below_pct": 10}),
        ("item.fake_ammo", {"hp_below_pct": 50}),
        ("item.fake_food", None),
    ],
)
def test_trigger_validation(item: str, trigger: dict[str, float | bool] | None) -> None:
    """Holder and trigger must match the authored consumable purpose."""
    with pytest.raises(EquipmentError) as error:
        validate_consumable(item, trigger, CONTENT)
    assert error.value.code == "INVALID_CONSUMABLE"


def test_belt_capacity_from_belt_and_cap() -> None:
    current = replace(state(), cap_bonuses={CapType.BELT_SLOTS: 3})
    base = CONTENT.caps.belt_slots
    assert belt_capacity(current, None, CONTENT) == base + 3
    assert belt_capacity(current, "item.fake_belt", CONTENT) == base + 5


def test_stack_return_preserves_over_cap_rule_and_stack_limits() -> None:
    content = replace(
        CONTENT, caps=CONTENT.caps.model_copy(update={"inventory_slots": 1})
    )
    current = replace(state(), inventory={"item.fake_food": 2, "item.fake_buff": 1})
    # Same distinct usage remains legal above a lowered cap.
    result = transfer_stack(
        current, ("item.fake_ammo", 3), "item.fake_buff", 1, content
    )
    assert result == {"item.fake_food": 2, "item.fake_ammo": 3}
    with pytest.raises(EquipmentError, match="Inventory"):
        transfer_stack(current, ("item.fake_ammo", 3), None, 0, content)
    food = content.item("item.fake_food").model_copy(update={"stack_limit": 2})
    with pytest.raises(EquipmentError, match="Inventory"):
        transfer_stack(
            current, (food.id, 1), None, 0, content.with_overrides(items=[food])
        )


def test_buff_group_c_expires_at_segment_boundary() -> None:
    """Expiry splits partial cycles and removes XP and speed exactly at the boundary."""
    action = CONTENT.action("gathering.fake_sprigs").model_copy(
        update={
            "base_cycle_ms": 10000,
            "xp": 10,
            "outputs": (),
            "requires": Requirements(),
        }
    )
    content = CONTENT.with_overrides(actions=[action])
    node = content.development_node("node.verdant_t1").model_copy(
        update={"modifiers": (), "inherent_tags": ()}
    )
    content = replace(
        content, _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node})
    )
    modifiers = (
        Modifier(type=ModifierType.CYCLE_SPEED_PCT, value=100, skill_id="gathering"),
        Modifier(type=ModifierType.XP_PCT, value=20, skill_id="gathering"),
    )
    expiry = NOW + timedelta(seconds=7)
    current = replace(
        state(), timed_buffs=((expiry, modifiers),), consumable_modifiers=modifiers
    )
    active = ActiveAction(action.id, NOW, NOW)
    # First completion at 5s receives C; 40% of the second cycle precedes expiry.
    first_state, first_active, first = resolve(
        current, active, content, NOW + timedelta(seconds=7), random.Random(1)
    )
    assert first.cycles_completed == 1
    assert first.xp_gained == {"gathering": 12}
    assert first_active is not None
    assert first_state.consumable_modifiers == ()
    assert (
        effective_xp(action, replace(current, consumable_modifiers=()), content) == 10
    )
    _, _, early = resolve(
        first_state,
        first_active,
        content,
        NOW + timedelta(milliseconds=12999),
        random.Random(1),
    )
    assert early.cycles_completed == 0
    _, _, second = resolve(
        first_state,
        first_active,
        content,
        NOW + timedelta(seconds=13),
        random.Random(1),
    )
    assert second.cycles_completed == 1 and second.xp_gained == {"gathering": 10}
    _, _, at_expiry = resolve(
        replace(current, timed_buffs=((NOW + timedelta(seconds=5), modifiers),)),
        active,
        content,
        NOW + timedelta(seconds=5),
        random.Random(1),
    )
    assert at_expiry.xp_gained == {"gathering": 10}
    _, _, offline = resolve(
        current, active, content, NOW + timedelta(seconds=13), random.Random(1)
    )
    assert offline.cycles_completed == 2 and offline.xp_gained == {"gathering": 22}


@given(
    hp=st.floats(min_value=0, max_value=500, allow_nan=False),
    seconds=st.integers(min_value=0, max_value=100000),
)
def test_hp_regeneration_math_and_max_clamp(hp: float, seconds: int) -> None:
    maximum = 200.0
    now = NOW + timedelta(seconds=seconds)
    actual = regenerate_hp(hp, maximum, NOW, now, 0.01)
    assert actual == pytest.approx(min(maximum, hp + 2 * seconds / 60))
    assert regenerate_hp(actual, maximum, now, now, 0.01) == actual
    assert regenerate_hp(10, maximum, NOW, NOW - timedelta(seconds=1), 0.01) == 10


def test_maximum_hp_uses_vigor_and_armour() -> None:
    current = replace(state(), skill_levels={"vigor": 7})
    combat = CONTENT.progression.combat
    assert (
        maximum_hp(current, 23, CONTENT)
        == combat.base_hp + 7 * combat.hp_per_level + 23
    )


def test_consumable_lint_combines_simultaneous_buffs() -> None:
    skill = CONTENT.skill("gathering")
    base = consumable_bound(skill, CONTENT)
    extra = CONTENT.item("item.fake_buff").model_copy(
        update={
            "id": "test.second_buff",
            "consumable": Consumable.model_validate_json(
                '{"buff":{"duration_ms":1,"modifiers":[{"type":"cycle_speed_pct","value":20,"category":"gathering"}]}}'
            ),
        }
    )
    assert base == pytest.approx(1.1)
    assert consumable_bound(
        skill, CONTENT.with_overrides(items=[extra])
    ) == pytest.approx(1.3)


@pytest.mark.anyio
async def test_setup_holders_capacity_triggers_and_conservation(
    action_client: ApiFixture,
) -> None:
    client, factory, _, headers = action_client
    with factory() as session:
        identifier = session.scalar(select(Character.id))
        assert identifier is not None
        for item in (
            "item.fake_food",
            "item.fake_ammo",
            "item.fake_buff",
            "item.fake_belt",
        ):
            session.add(Inventory(character_id=identifier, item_id=item, quantity=10))
        session.commit()
    before = Counter(
        {
            item: 10
            for item in (
                "item.fake_food",
                "item.fake_ammo",
                "item.fake_buff",
                "item.fake_belt",
            )
        }
    )
    response = await client.put(
        "/equipment/utility",
        headers=headers,
        json={"item_id": "item.fake_ammo", "quantity": 4},
    )
    assert response.status_code == 200, response.text
    assert response.json()["equipment"]["utility"]["quantity"] == 4
    # Same setup is idempotent and may reuse the existing held stack.
    response = await client.put(
        "/equipment/utility",
        headers=headers,
        json={"item_id": "item.fake_ammo", "quantity": 4},
    )
    assert response.status_code == 200
    body = {"item_id": "item.fake_food", "quantity": 3, "trigger": {"hp_below_pct": 50}}
    capacity = CONTENT.caps.belt_slots
    response = await client.put(
        f"/equipment/belt/{capacity}", headers=headers, json=body
    )
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "INVALID_BELT_SLOT"
    )
    equipped = await client.post(
        "/equipment/equip",
        headers=headers,
        json={"item_id": "item.fake_belt", "slot": "belt"},
    )
    assert equipped.status_code == 200
    assert equipped.json()["equipment"]["utility"]["quantity"] == 4
    response = await client.put(
        f"/equipment/belt/{capacity + 1}", headers=headers, json=body
    )
    assert response.status_code == 200, response.text
    bad = await client.put(
        "/equipment/belt/0",
        headers=headers,
        json={**body, "trigger": {"buff_missing": True}},
    )
    assert (
        bad.status_code == 409 and bad.json()["error"]["code"] == "INVALID_CONSUMABLE"
    )
    buff = await client.put(
        "/equipment/belt/0",
        headers=headers,
        json={
            "item_id": "item.fake_buff",
            "quantity": 2,
            "trigger": {"buff_missing": True},
        },
    )
    assert buff.status_code == 200, buff.text
    profile = (await client.get("/characters/me", headers=headers)).json()
    assert profile["belt"]["0"]["trigger"] == {"buff_missing": True}
    assert profile["belt"][str(capacity + 1)]["quantity"] == 3
    assert profile["equipment"]["utility"]["quantity"] == 4
    with factory() as session:
        actual = Counter(
            {row.item_id: row.quantity for row in session.scalars(select(Inventory))}
        )
        for equipped_row in session.scalars(select(CharacterEquipment)):
            actual[equipped_row.item_id] += equipped_row.quantity
        for belt_row in session.scalars(select(CharacterBelt)):
            actual[belt_row.item_id] += belt_row.quantity
        assert actual == before
    # Lowering capacity preserves holders and lets their owner recover them.
    assert (
        await client.post("/equipment/unequip", headers=headers, json={"slot": "belt"})
    ).status_code == 200
    assert (
        await client.put(
            f"/equipment/belt/{capacity + 1}",
            headers=headers,
            json={"item_id": None, "quantity": 0},
        )
    ).status_code == 200
    assert (
        await client.put(
            "/equipment/utility", headers=headers, json={"item_id": None, "quantity": 0}
        )
    ).status_code == 200
    assert (
        await client.put(
            "/equipment/belt/0", headers=headers, json={"item_id": None, "quantity": 0}
        )
    ).status_code == 200
    with factory() as session:
        assert (
            Counter(
                {
                    row.item_id: row.quantity
                    for row in session.scalars(select(Inventory))
                }
            )
            == before
        )


@pytest.mark.anyio
async def test_profile_lazy_hp_and_buff_adapter(action_client: ApiFixture) -> None:
    client, factory, clock, headers = action_client
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 5
        character.hp_updated_at = clock.now
        session.add(
            CharacterBuff(
                character_id=character.id,
                item_id="item.fake_buff",
                expires_at=clock.now + timedelta(seconds=30),
            )
        )
        session.commit()
    profile = (await client.get("/characters/me", headers=headers)).json()
    assert profile["hp"] == 5
    maximum = profile["max_hp"]
    with factory() as session:
        current = load_character_state(session, character.id, CONTENT, clock.now)
        assert len(current.consumable_modifiers) == 1
        assert not current.gear_modifiers
    clock.advance(timedelta(seconds=30))
    profile = (await client.get("/characters/me", headers=headers)).json()
    assert profile["hp"] == pytest.approx(5 + maximum * 0.005)
    with factory() as session:
        assert (
            load_character_state(
                session, character.id, CONTENT, clock.now
            ).consumable_modifiers
            == ()
        )
    clock.advance(timedelta(days=1))
    profile = (await client.get("/characters/me", headers=headers)).json()
    assert profile["hp"] == profile["max_hp"]
    assert datetime.fromisoformat(profile["hp_updated_at"]) == clock.now


@pytest.mark.anyio
async def test_concurrent_belt_assignments_transfer_stack_once(
    action_client: ApiFixture,
) -> None:
    """Independent requests serialize on the character on SQLite and PostgreSQL."""
    client, factory, _, headers = action_client
    with factory() as session:
        identifier = session.scalar(select(Character.id))
        assert identifier is not None
        session.add(
            Inventory(character_id=identifier, item_id="item.fake_food", quantity=1)
        )
        session.commit()
    barrier = threading.Barrier(2)

    def submit(slot: int) -> int:
        barrier.wait(timeout=10)
        return asyncio.run(
            client.put(
                f"/equipment/belt/{slot}",
                headers=headers,
                json={
                    "item_id": "item.fake_food",
                    "quantity": 1,
                    "trigger": {"hp_below_pct": 50},
                },
            )
        ).status_code

    # Use two different positions: replacing one's own setup is idempotent.
    assert CONTENT.caps.belt_slots >= 2
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit, slot) for slot in (0, 1)]
        assert sorted(f.result(timeout=20) for f in futures) == [200, 409]
    with factory() as session:
        held = list(session.scalars(select(CharacterBelt)))
        assert len(held) == 1 and held[0].quantity == 1
        assert session.get(Inventory, (identifier, "item.fake_food")) is None


@pytest.mark.anyio
async def test_armour_hp_formula_and_removal_clamp(
    action_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Armour changes max HP, preserves damage, and clamps on removal."""
    client, factory, _, headers = action_client
    armour = CONTENT.item("item.fake_cape").model_copy(
        update={
            "id": "test.armour",
            "equip": Equipment(slot="chest", armour=Armour(armour=1, max_hp=25)),
        }
    )
    monkeypatch.setattr(app.state, "content", CONTENT.with_overrides(items=[armour]))
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 7
        session.add(Inventory(character_id=character.id, item_id=armour.id, quantity=1))
        session.commit()
    base = CONTENT.progression.combat.base_hp + CONTENT.progression.combat.hp_per_level
    assert (
        await client.post(
            "/equipment/equip",
            headers=headers,
            json={"item_id": armour.id, "slot": "chest"},
        )
    ).status_code == 200
    profile = (await client.get("/characters/me", headers=headers)).json()
    assert profile["hp"] == 7 and profile["max_hp"] == base + 25
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = base + 25
        session.commit()
    assert (
        await client.post("/equipment/unequip", headers=headers, json={"slot": "chest"})
    ).status_code == 200
    profile = (await client.get("/characters/me", headers=headers)).json()
    assert profile["hp"] == profile["max_hp"] == base


@given(polls=st.lists(st.integers(min_value=0, max_value=40000), max_size=15))
def test_multiple_buff_expiries_match_online_polling(polls: list[int]) -> None:
    """Segmentation, including partial-cycle polls, preserves offline rewards."""
    action = CONTENT.action("gathering.fake_sprigs").model_copy(
        update={
            "xp": 1,
            "outputs": (),
            "requires": Requirements(),
            "base_cycle_ms": 10000,
        }
    )
    content = CONTENT.with_overrides(actions=[action])
    node = content.development_node("node.verdant_t1").model_copy(
        update={"modifiers": (), "inherent_tags": ()}
    )
    content = replace(
        content, _nodes_by_id=MappingProxyType({**content._nodes_by_id, node.id: node})
    )
    first = (Modifier(type=ModifierType.CYCLE_SPEED_PCT, value=100),)
    second = (
        Modifier(type=ModifierType.CYCLE_SPEED_PCT, value=50),
        Modifier(type=ModifierType.XP_PCT, value=100),
    )
    current = replace(
        state(),
        timed_buffs=(
            (NOW + timedelta(seconds=7), first),
            (NOW + timedelta(seconds=11), second),
        ),
    )
    active = ActiveAction(action.id, NOW, NOW)
    offline_state, offline_active, offline = resolve(
        current, active, content, NOW + timedelta(seconds=40), random.Random(1)
    )
    online_cycles = 0
    for ms in sorted({*polls, 40000}):
        assert active is not None
        current, next_active, result = resolve(
            current, active, content, NOW + timedelta(milliseconds=ms), random.Random(1)
        )
        assert next_active is not None
        active = next_active
        online_cycles += result.cycles_completed
    assert current.skills_xp == offline_state.skills_xp
    assert online_cycles == offline.cycles_completed
    assert active == offline_active
