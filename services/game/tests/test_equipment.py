"""Permanent equipment, content rules and mid-action integration."""

import json
from collections import Counter
from dataclasses import replace
from datetime import timedelta

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock, action_client, anyio_backend

from app.content.lint import gear_bound
from app.content.runtime import CONTENT
from app.content.schemas import Equipment, EquipmentSlot, Item, Requirements
from app.engine.core import CharacterState, effective_cycle_time, unmet_requirements
from app.engine.equipment import EquipmentError, change_equipment
from app.models import Character, CharacterEquipment, Inventory
from app.services.actions import load_character_state

__all__ = ["action_client", "anyio_backend"]


def state() -> CharacterState:
    """Return ample inventory and a valid placeholder estate/realm."""
    return CharacterState({}, {}, {}, 0, "form.camp", "node.verdant_t1")


def test_validator_rejects_xp_outside_cape() -> None:
    for slot in ("head", "ring", "right_hand"):
        with pytest.raises(ValidationError, match="cape"):
            Equipment.model_validate_json(
                json.dumps(
                    {"slot": slot, "modifiers": [{"type": "xp_pct", "value": 1}]}
                )
            )
    assert Equipment.model_validate_json(
        '{"slot":"cape","modifiers":[{"type":"xp_pct","value":1}]}'
    )


def test_slots_two_handed_requirements_and_conservation() -> None:
    left = CONTENT.item("item.fake_cape").model_copy(
        update={"id": "test.left", "equip": Equipment(slot="left_hand")}
    )
    ring = left.model_copy(
        update={
            "id": "test.ring",
            "equip": Equipment(slot="ring", requires={"melee": 2}),
        }
    )
    content = CONTENT.with_overrides(items=[left, ring])
    inventory = {"item.fake_two_hander": 1, "test.ring": 2}
    equipped = {"left_hand": "test.left"}
    original = Counter(inventory) + Counter(equipped.values())
    current = replace(state(), inventory=inventory)
    inventory, equipped = change_equipment(
        current, equipped, "right_hand", "item.fake_two_hander", content
    )
    assert "left_hand" not in equipped
    assert inventory["test.left"] == 1
    assert Counter(inventory) + Counter(equipped.values()) == original
    current = replace(current, inventory=inventory)
    with pytest.raises(EquipmentError, match="blocks"):
        change_equipment(current, equipped, "left_hand", "test.left", content)
    with pytest.raises(EquipmentError, match="requirements"):
        change_equipment(current, equipped, "left_ring", "test.ring", content)
    current = replace(current, skill_levels={"melee": 2})
    for slot in ("left_ring", "right_ring"):
        inventory, equipped = change_equipment(
            replace(current, inventory=inventory), equipped, slot, "test.ring", content
        )
    assert equipped["left_ring"] == equipped["right_ring"]
    with pytest.raises(EquipmentError, match="fit"):
        change_equipment(current, equipped, "head", "test.ring", content)
    assert Counter(inventory) + Counter(equipped.values()) == original


def test_unequip_needs_capacity_and_stack_space() -> None:
    content = replace(
        CONTENT, caps=CONTENT.caps.model_copy(update={"inventory_slots": 1})
    )
    current = replace(state(), inventory={"item.fake_sprig": 1})
    with pytest.raises(EquipmentError, match="Inventory"):
        change_equipment(current, {"cape": "item.fake_cape"}, "cape", None, content)

    cape = content.item("item.fake_cape").model_copy(update={"stack_limit": 1})
    content = content.with_overrides(items=[cape])
    current = replace(current, inventory={cape.id: 1})
    with pytest.raises(EquipmentError, match="Inventory"):
        change_equipment(current, {"cape": cape.id}, "cape", None, content)


def test_gear_lint_respects_hands_and_ring_sides() -> None:
    def item(identifier: str, slot: str, bonus: float, two: bool = False) -> Item:
        return CONTENT.item("item.fake_cape").model_copy(
            update={
                "id": identifier,
                "equip": Equipment.model_validate_json(
                    json.dumps(
                        {
                            "slot": slot,
                            "two_handed": two,
                            "modifiers": [{"type": "cycle_speed_pct", "value": bonus}],
                        }
                    )
                ),
            }
        )

    content = CONTENT.with_overrides(
        items=[
            item("test.two", "right_hand", 100, True),
            item("test.left", "left_hand", 90),
            item("test.ring", "ring", 10),
        ]
    )
    skill = content.skills[0]
    # Cape's XP and two copies of the ring combine with the best legal hands.
    assert gear_bound(skill, content) == pytest.approx(2.2 * 1.05)


@pytest.mark.anyio
async def test_tool_group_g_and_mid_action_change(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    client, factory, clock, headers = action_client
    action = next(
        a
        for skill in CONTENT.skills
        if skill.category == "gathering"
        for a in skill.actions
    )
    tool_action = action.model_copy(
        update={"requires": Requirements(tool_class="fake_pickaxe")}
    )
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        identifier = character.id
        session.add(
            Inventory(character_id=identifier, item_id="item.fake_pickaxe", quantity=1)
        )
        session.commit()
        before = load_character_state(session, identifier)
        assert any(
            code.value == "MISSING_TOOL"
            for code in unmet_requirements(tool_action, before, CONTENT)
        )
        old_cycle = effective_cycle_time(action, before, CONTENT)
    started = await client.post(
        "/actions/start", headers=headers, json={"action_id": action.id}
    )
    assert started.status_code == 200, started.text
    clock.advance(timedelta(milliseconds=old_cycle / 2))
    response = await client.post(
        "/equipment/equip",
        headers=headers,
        json={"item_id": "item.fake_pickaxe", "slot": "right_hand"},
    )
    assert response.status_code == 200, response.text
    with factory() as session:
        after = load_character_state(session, identifier)
        assert not any(
            code.value == "MISSING_TOOL"
            for code in unmet_requirements(tool_action, after, CONTENT)
        )
        assert after.gear_modifiers == CONTENT.item("item.fake_pickaxe").equip.modifiers  # type: ignore[union-attr]
        new_cycle = effective_cycle_time(action, after, CONTENT)
        assert new_cycle == int(old_cycle / 1.1)
        assert session.get(Inventory, (identifier, "item.fake_pickaxe")) is None
    clock.advance(timedelta(milliseconds=new_cycle / 2 - 1))
    poll = await client.get("/actions/poll", headers=headers)
    assert poll.json()["since_last"]["cycles_completed"] == 0
    clock.advance(timedelta(milliseconds=2))
    poll = await client.get("/actions/poll", headers=headers)
    assert poll.json()["since_last"]["cycles_completed"] == 1
    response = await client.post(
        "/equipment/unequip", headers=headers, json={"slot": "right_hand"}
    )
    assert response.status_code == 200, response.text
    with factory() as session:
        assert session.get(CharacterEquipment, (identifier, "right_hand")) is None
        returned = session.get(Inventory, (identifier, "item.fake_pickaxe"))
        assert returned is not None and returned.quantity == 1


@pytest.mark.anyio
async def test_equipment_caps_xp_and_failed_changes_are_atomic(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cape bonuses reach profiles; rejected intents leave every holder intact."""
    from app.content.schemas import CapType
    from app.engine.core import resolve_caps
    from app.main import app

    client, factory, _, headers = action_client
    cape = CONTENT.item("item.fake_cape")
    assert cape.equip is not None
    cape = cape.model_copy(
        update={
            "equip": cape.equip.model_copy(
                update={"cap_bonuses": {CapType.INVENTORY_SLOTS: 3}}
            )
        }
    )
    content = CONTENT.with_overrides(items=[cape])
    monkeypatch.setattr(app.state, "content", content)
    with factory() as session:
        identifier = session.scalar(select(Character.id))
        assert identifier is not None
        session.add(Inventory(character_id=identifier, item_id=cape.id, quantity=1))
        base = resolve_caps(
            load_character_state(session, identifier, content), content
        ).inventory_slots
        session.commit()
    result = await client.post(
        "/equipment/equip", headers=headers, json={"item_id": cape.id, "slot": "cape"}
    )
    assert result.status_code == 200, result.text
    with factory() as session:
        current = load_character_state(session, identifier, content)
        assert resolve_caps(current, content).inventory_slots == base + 3
        assert current.gear_modifiers == cape.equip.modifiers  # type: ignore[union-attr]
    for path, body, code in (
        ("equip", {"item_id": "missing", "slot": "cape"}, "UNKNOWN_ITEM"),
        ("equip", {"item_id": "item.fake_sprig", "slot": "head"}, "NOT_EQUIPPABLE"),
        ("unequip", {"slot": "head"}, "EQUIPMENT_SLOT_EMPTY"),
        ("equip", {"item_id": cape.id, "slot": "cape"}, "MISSING_INPUTS"),
    ):
        result = await client.post(f"/equipment/{path}", headers=headers, json=body)
        assert result.status_code == 409, result.text
        assert result.json()["error"]["code"] == code
        with factory() as session:
            assert dict(
                load_character_state(session, identifier, content).inventory
            ) == dict(current.inventory)
            equipped = session.get(CharacterEquipment, (identifier, "cape"))
            assert equipped is not None and equipped.item_id == cape.id
    profile = (await client.get("/characters/me", headers=headers)).json()
    action = content.skill("gathering").actions[0]
    assert profile["actions"][action.id]["xp_bonus_uncapped"] > 5
    assert profile["caps"]["inventory_slots"]["effective"] == base + 3
    assert profile["equipment"] == {"cape": {"item_id": cape.id, "quantity": 1}}


@pytest.mark.anyio
async def test_concurrent_equips_transfer_single_item_once(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Independent requests serialize one inventory item on either database."""
    import asyncio
    import threading
    from concurrent.futures import ThreadPoolExecutor

    client, factory, _, headers = action_client
    with factory() as session:
        identifier = session.scalar(select(Character.id))
        assert identifier is not None
        session.add(
            Inventory(character_id=identifier, item_id="item.fake_cape", quantity=1)
        )
        session.commit()
    barrier = threading.Barrier(2)

    def submit() -> int:
        barrier.wait(timeout=10)
        return asyncio.run(
            client.post(
                "/equipment/equip",
                headers=headers,
                json={"item_id": "item.fake_cape", "slot": "cape"},
            )
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        assert sorted(f.result(timeout=20) for f in futures) == [200, 409]
    with factory() as session:
        equipped = session.get(CharacterEquipment, (identifier, "cape"))
        assert equipped is not None and equipped.quantity == 1
        assert session.get(Inventory, (identifier, "item.fake_cape")) is None


@pytest.mark.parametrize(
    "slot",
    [
        "head",
        "chest",
        "gloves",
        "legs",
        "feet",
        "neck",
        "left_arm",
        "right_arm",
        "left_ring",
        "right_ring",
        "belt",
        "cape",
        "right_hand",
        "left_hand",
    ],
)
def test_every_permanent_slot_round_trips(slot: EquipmentSlot) -> None:
    item = CONTENT.item("item.fake_cape").model_copy(
        update={"equip": Equipment(slot=slot)}
    )
    content = CONTENT.with_overrides(items=[item])
    current = replace(state(), inventory={item.id: 1})
    inventory, equipped = change_equipment(current, {}, slot, item.id, content)
    assert inventory == {} and equipped == {slot: item.id}
    inventory, equipped = change_equipment(
        replace(current, inventory=inventory), equipped, slot, None, content
    )
    assert inventory == {item.id: 1} and equipped == {}


def test_two_handed_displacement_is_atomic_when_inventory_is_full() -> None:
    left = CONTENT.item("item.fake_cape").model_copy(
        update={"id": "test.left", "equip": Equipment(slot="left_hand")}
    )
    content = CONTENT.with_overrides(items=[left])
    content = replace(
        content, caps=content.caps.model_copy(update={"inventory_slots": 1})
    )
    current = replace(state(), inventory={"item.fake_two_hander": 2})
    equipped = {"left_hand": left.id}
    with pytest.raises(EquipmentError, match="Inventory"):
        change_equipment(
            current, equipped, "right_hand", "item.fake_two_hander", content
        )
    assert current.inventory == {"item.fake_two_hander": 2}
    assert equipped == {"left_hand": left.id}


@pytest.mark.anyio
async def test_equipped_tool_unlocks_action_start(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Availability and action start share the persisted main-hand tool check."""
    from app.main import app

    client, factory, clock, headers = action_client
    action = CONTENT.skill("gathering").actions[0]
    action = action.model_copy(
        update={"requires": Requirements(tool_class="fake_pickaxe")}
    )
    monkeypatch.setattr(app.state, "content", CONTENT.with_overrides(actions=[action]))
    failed = await client.post(
        "/actions/start", headers=headers, json={"action_id": action.id}
    )
    assert failed.status_code == 409
    assert failed.json()["error"]["code"] == "MISSING_TOOL"
    with factory() as session:
        identifier = session.scalar(select(Character.id))
        assert identifier is not None
        session.add(
            Inventory(character_id=identifier, item_id="item.fake_pickaxe", quantity=1)
        )
        session.commit()
    equipped = await client.post(
        "/equipment/equip",
        headers=headers,
        json={"item_id": "item.fake_pickaxe", "slot": "right_hand"},
    )
    assert equipped.status_code == 200
    started = await client.post(
        "/actions/start", headers=headers, json={"action_id": action.id}
    )
    assert started.status_code == 200, started.text
    clock.advance(timedelta(milliseconds=started.json()["cycle_ms"] / 2))
    removed = await client.post(
        "/equipment/unequip", headers=headers, json={"slot": "right_hand"}
    )
    assert removed.status_code == 200, removed.text
    clock.advance(timedelta(hours=1))
    poll = await client.get("/actions/poll", headers=headers)
    assert poll.json()["active"] is None
    assert poll.json()["stop_reason"] == "REQUIREMENT_LOST"
    assert poll.json()["since_last"]["cycles_completed"] == 0


@pytest.mark.anyio
async def test_equipment_changes_rejected_during_combat(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Combat resolution runs before either equipment mutation is rejected."""
    from functools import partial

    from app.engine import UniformResolver, resolve
    from app.engine.core import ACTION_RESOLVERS
    from app.main import app
    from app.services import actions

    client, _, _, headers = action_client
    action = (
        CONTENT.skill("gathering").actions[0].model_copy(update={"resolver": "combat"})
    )
    monkeypatch.setattr(app.state, "content", CONTENT.with_overrides(actions=[action]))
    # Exercise the existing resolver seam without implementing future combat rules.
    monkeypatch.setattr(
        actions,
        "resolve",
        partial(resolve, resolvers={**ACTION_RESOLVERS, "combat": UniformResolver()}),
    )
    started = await client.post(
        "/actions/start", headers=headers, json={"action_id": action.id}
    )
    assert started.status_code == 200
    for path, body in (
        ("equip", {"item_id": "item.fake_cape", "slot": "cape"}),
        ("unequip", {"slot": "cape"}),
    ):
        response = await client.post(f"/equipment/{path}", headers=headers, json=body)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EQUIPMENT_IN_COMBAT"


def test_gear_lint_includes_estate_slot_grants() -> None:
    """A gear cap grant must not hide the estate stack it makes possible."""
    from app.content.lint import stack_bound
    from app.content.schemas import CapType, EstateUpgrade, Modifier, ModifierType

    ring = CONTENT.item("item.fake_cape").model_copy(
        update={
            "id": "test.slots",
            "equip": Equipment(
                slot="ring", cap_bonuses={CapType.ESTATE_UPGRADE_SLOTS: 1}
            ),
        }
    )
    form = CONTENT.estate_forms[0].model_copy(
        update={"upgrade_slots": 0, "cap_bonuses": (), "modifiers": (), "tags": ()}
    )
    node = CONTENT.development_nodes[0].model_copy(
        update={
            "modifiers": (),
            "inherent_tags": (),
            "projects": (),
            "carried_tags": (),
        }
    )
    upgrade = EstateUpgrade(
        id="test.upgrade",
        name="Test upgrade",
        cost=(),
        modifiers=(Modifier(type=ModifierType.CYCLE_SPEED_PCT, value=10),),
    )
    content = replace(
        CONTENT.with_overrides(items=[ring]),
        estate_forms=(form,),
        development_nodes=(node,),
        upgrades=(upgrade, upgrade.model_copy(update={"id": "test.other"})),
    )
    skill = content.skill("gathering")
    assert stack_bound(skill, content) == pytest.approx(
        gear_bound(skill, content) * 1.2
    )
