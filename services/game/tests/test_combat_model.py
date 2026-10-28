"""Combat model arithmetic, content boundaries, stance and sizing estimates."""

import asyncio
import json
import random
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock, action_client, anyio_backend
from test_consumables_hp import state
from test_estates import _wait_for_postgres_blocker

from app.api import characters
from app.config import CONTENT_DIR
from app.content.combat_lint import lint_combat
from app.content.loader import ContentError, ContentIndex, load_content
from app.content.runtime import CONTENT
from app.content.schemas import Armour, Equipment, Modifier, ModifierType, Weapon
from app.engine.combat import attack, eff, hit_chance, opponent_stats, player_stats
from app.main import app
from app.models import ActiveActionRecord, Character, CharacterEquipment, CharacterSkill
from app.services import actions as action_service
from app.services.actions import Resolution, as_utc, lock_character_and_load_action

__all__ = ["action_client", "anyio_backend"]


@pytest.mark.parametrize("level,tier", [(1, 1), (50, 2), (75, 3), (90, 4), (95, 5)])
@pytest.mark.parametrize(
    "skill", ["melee", "ranged", "magic", "accuracy", "defense", "vigor"]
)
def test_eff_per_tier_and_vigor(skill: str, level: int, tier: int) -> None:
    """Only Vigor omits the uniform per-tier multiplier."""
    multiplier = 1 if skill == "vigor" else 1 + 0.05 * (tier - 1)
    assert eff(skill, level, CONTENT) == pytest.approx(level * multiplier)


def test_hit_bounds_rounding_and_miss_mitigation() -> None:
    """D12 clamps both ends and rolls weak/resisted damage even on a miss."""
    enemy = opponent_stats(CONTENT.combatants[0], CONTENT)
    assert hit_chance(replace(enemy, accuracy=0), enemy) == 0.05
    assert hit_chance(enemy, replace(enemy, defense=0)) == 0.95
    assert hit_chance(replace(enemy, accuracy=0), replace(enemy, defense=0)) == 0.5
    attacker = replace(enemy, max_hit=7)
    for weakness, resistance, expected in [
        (True, False, 8),
        (False, True, 5),
        (True, True, 6),
    ]:
        defender = replace(
            enemy,
            armour=0,
            weak_to=(enemy.damage_type,) if weakness else (),
            resistant_to=(enemy.damage_type,) if resistance else (),
        )
        # Seed zero's first probability is .844, followed by damage seven.
        hit = attack(attacker, replace(defender, defense=0), random.Random(0))
        assert (hit.dealt, hit.mitigated) == (expected, 0)
        miss = attack(replace(attacker, accuracy=0), defender, random.Random(0))
        assert (miss.dealt, miss.mitigated) == (0, expected)
    blocked = attack(attacker, replace(enemy, defense=0, armour=100), random.Random(0))
    assert (blocked.dealt, blocked.mitigated) == (4, 3)


@given(st.integers(min_value=0, max_value=10000))
def test_attack_damage_partition(seed: int) -> None:
    """Every rolled damage unit is either dealt or mitigated, including misses."""
    enemy = replace(opponent_stats(CONTENT.combatants[0], CONTENT), max_hit=17)
    oracle = random.Random(seed)
    oracle.random()
    rolled = oracle.randint(1, 17)
    result = attack(enemy, replace(enemy, armour=50), random.Random(seed))
    assert result.dealt + result.mitigated == rolled
    assert result.dealt >= 0 and result.mitigated >= 0


def test_effectiveness_three_stats_only() -> None:
    """Only accuracy, power and defense receive P, independently of G and C."""
    character = replace(state(), skill_levels={"melee": 95})
    gear = {"chest": "item.fake_armour"}
    opponent = CONTENT.combatants[0]
    base = player_stats(
        character, gear, opponent.model_copy(update={"tier": 5}), CONTENT
    )
    effective = player_stats(character, gear, opponent, CONTENT)
    assert effective.accuracy == pytest.approx(base.accuracy * 1.4)
    assert effective.max_hit == int(base.max_hit * 1.4)
    assert effective.defense == pytest.approx(base.defense * 1.4)
    assert effective.max_hp == base.max_hp
    assert effective.armour == base.armour == 10
    assert effective.cycle_ms == base.cycle_ms
    character = replace(
        character,
        gear_modifiers=(Modifier(type=ModifierType.COMBAT_POWER_PCT, value=50),),
        consumable_modifiers=(Modifier(type=ModifierType.COMBAT_POWER_PCT, value=20),),
    )
    stacked = player_stats(character, gear, opponent, CONTENT)
    assert stacked.max_hit == int(base.max_hit * 1.4 * 1.5 * 1.2)


def test_player_stats_weapon_armour_hp_and_speed() -> None:
    """Authored equipment and modifiers drive each stat, with shared HP arithmetic."""
    opponent = CONTENT.combatants[0]
    unarmed = player_stats(state(), {}, opponent, CONTENT)
    assert (unarmed.style, unarmed.max_hit, unarmed.max_hp, unarmed.cycle_ms) == (
        "melee",
        2,
        110,
        2000,
    )
    weapon_item = next(i for i in CONTENT.items if i.equip and i.equip.weapon)
    assert weapon_item.equip and weapon_item.equip.weapon
    weapon = weapon_item.equip.weapon
    geared = player_stats(state(), {"right_hand": weapon_item.id}, opponent, CONTENT)
    assert geared.style == weapon.style
    assert geared.accuracy == 1 + weapon.accuracy
    assert geared.max_hit == int(2 + weapon.power)
    assert geared.cycle_ms == weapon.attack_interval_ms
    mods = tuple(
        Modifier(type=kind, value=100, category="combat")
        for kind in (ModifierType.COMBAT_HP_PCT, ModifierType.CYCLE_SPEED_PCT)
    )
    buffed = player_stats(
        replace(state(), consumable_modifiers=mods), {}, opponent, CONTENT
    )
    assert buffed.max_hp == 220
    assert buffed.cycle_ms == 1000


def test_combat_lint_flags_oversized_pool() -> None:
    """An oversized offensive pool warns for both receiving skills in every stance."""
    opponent = CONTENT.combatants[0].model_copy(update={"xp_pool_offense": 10**9})
    reports = lint_combat(replace(CONTENT, combatants=(opponent,)))
    assert len(reports) == 3
    for report in reports:
        assert report.encounter_ms == 18000
        assert {"melee", "accuracy"} <= set(report.warnings)
        assert set(report.xp_per_hour) == {"melee", "accuracy", "defense", "vigor"}


@pytest.mark.parametrize("defect", ["gold", "drop", "opponent", "location"])
def test_combat_pack_validation(tmp_path: Path, defect: str) -> None:
    """Unknown drops, currency grants and broken combat action links fail boot."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / (
        "combatants.json" if defect in {"gold", "drop"} else "skills.json"
    )
    payload = json.loads(path.read_text())
    if defect == "gold":
        payload["combatants"][0]["gold"] = 1
    elif defect == "drop":
        payload["combatants"][0]["drops"] = [
            dict(item_id="gold", quantity_min=1, quantity_max=1, chance=1)
        ]
    else:
        action = next(s for s in payload["skills"] if s["id"] == "melee")["actions"][0]
        action["combatant_id" if defect == "opponent" else "location"] = (
            "missing" if defect == "opponent" else ""
        )
    path.write_text(json.dumps(payload))
    with pytest.raises(ContentError):
        load_content(directory)


@pytest.mark.anyio
async def test_stance_change_persists(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """The standing setting persists across requests; invalid input changes nothing."""
    client, _, _, headers = action_client
    response = await client.put(
        "/characters/me/stance", headers=headers, json={"stance": "precise"}
    )
    assert response.status_code == 200
    assert response.json() == {"stance": "precise"}
    profile = await client.get("/characters/me", headers=headers)
    assert profile.json()["character"]["stance"] == "precise"
    rejected = await client.put(
        "/characters/me/stance", headers=headers, json={"stance": "missing"}
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "INVALID_STANCE"
    profile = await client.get("/characters/me", headers=headers)
    assert profile.json()["character"]["stance"] == "precise"


def test_equipped_style_drives_tier_distance_and_armour_totals() -> None:
    """Use the weapon's skill tier, sum defensive gear, and keep HP/speed outside P."""
    sword = CONTENT.item("item.fake_sword").model_copy(
        update={
            "equip": Equipment(
                slot="right_hand",
                weapon=Weapon(
                    style="ranged",
                    attack_interval_ms=3000,
                    accuracy=2,
                    power=3,
                    damage_type="test.pierce",
                ),
            )
        }
    )
    gloves = CONTENT.item("item.fake_armour").model_copy(
        update={
            "id": "test.gloves",
            "equip": Equipment(slot="gloves", armour=Armour(armour=20, max_hp=10)),
        }
    )
    content = CONTENT.with_overrides(items=[sword, gloves])
    gear = {"right_hand": sword.id, "chest": "item.fake_armour", "gloves": gloves.id}
    current = replace(
        state(),
        skill_levels={
            "melee": 1,
            "ranged": 95,
            "accuracy": 50,
            "defense": 75,
            "vigor": 95,
        },
    )
    low = player_stats(current, gear, content.combatants[0], content)
    equal = player_stats(
        current, gear, content.combatants[0].model_copy(update={"tier": 5}), content
    )
    assert low.style == "ranged" and low.damage_type == "test.pierce"
    assert low.accuracy == pytest.approx((52.5 + 2) * 1.4)
    assert low.defense == pytest.approx(82.5 * 1.4)
    assert low.max_hit == int((1 + 114 + 3) * 1.4)
    assert equal.max_hit == 118
    assert low.armour == equal.armour == 30
    assert low.max_hp == equal.max_hp == 1065
    assert low.cycle_ms == equal.cycle_ms == 3000


def test_combat_lint_pool_splits_and_respawn() -> None:
    """The estimate includes respawn and independently splits capped defensive XP."""
    reports = lint_combat(CONTENT)
    balanced = next(report for report in reports if report.stance == "balanced")
    assert balanced.time_to_kill_ms == 16000
    assert balanced.encounter_ms == 18000
    assert balanced.xp_per_hour == pytest.approx(
        {"melee": 2000, "accuracy": 2000, "vigor": 960, "defense": 1440}
    )
    capped = CONTENT.combatants[0].model_copy(update={"xp_pool_defense": 6})
    capped_report = next(
        report
        for report in lint_combat(replace(CONTENT, combatants=(capped,)))
        if report.stance == "balanced"
    )
    assert capped_report.xp_per_hour["defense"] == pytest.approx(720)
    assert capped_report.xp_per_hour["vigor"] == pytest.approx(480)
    orphan = CONTENT.combatants[0].model_copy(update={"id": "test.orphan"})
    report = lint_combat(replace(CONTENT, combatants=(orphan,)))[0]
    assert report.warnings == ("NO_COMBAT_ACTION",)
    assert report.encounter_ms is None


@pytest.mark.parametrize(
    "gear",
    [
        {"left_hand": "item.fake_sword"},
        {"right_hand": "item.fake_two_hander", "left_hand": "item.fake_cape"},
        {"chest": "missing"},
    ],
)
def test_standard_gear_validation(tmp_path: Path, gear: dict[str, str]) -> None:
    """A lint loadout must fit real concrete slots and the authored hand rules."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "progression.json"
    payload = json.loads(path.read_text())
    payload["combat"]["standard_gear"] = gear
    path.write_text(json.dumps(payload))
    with pytest.raises(ContentError):
        load_content(directory)


@pytest.mark.anyio
async def test_combat_actions_use_registered_resolver(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Authored combat is startable through the registered resolver."""
    client, _, _, headers = action_client
    available = await client.get("/actions/available", headers=headers)
    group = next(
        group for group in available.json()["skills"] if group["skill_id"] == "melee"
    )
    action = group["actions"][0]
    assert action["startable"] is True
    assert action["blocked_by"] == []
    start = await client.post(
        "/actions/start", headers=headers, json={"action_id": action["action_id"]}
    )
    assert start.status_code == 200


@pytest.mark.anyio
async def test_stance_change_resolves_elapsed_work_before_changing(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stance mutation credits past work under the old stance up to the change."""
    client, factory, clock, headers = action_client
    start = await client.post(
        "/actions/start", headers=headers, json={"action_id": "gathering.fake_sprigs"}
    )
    assert start.status_code == 200
    clock.advance(timedelta(milliseconds=start.json()["cycle_ms"] * 10))
    original_resolve = action_service.resolve_character
    observed_stances: list[str] = []

    def observe_resolution(
        session: Session, identifier: uuid.UUID, now: datetime, content: ContentIndex
    ) -> Resolution:
        character = session.get(Character, identifier)
        assert character is not None
        observed_stances.append(character.stance)
        return original_resolve(session, identifier, now, content)

    monkeypatch.setattr(characters, "resolve_character", observe_resolution)
    changed = await client.put(
        "/characters/me/stance", headers=headers, json={"stance": "aggressive"}
    )
    assert changed.status_code == 200
    assert observed_stances == [CONTENT.progression.default_stance]
    with factory() as session:
        active = session.scalar(select(ActiveActionRecord))
        assert active is not None
        assert as_utc(active.last_resolved_at) == clock.now
        skill = session.scalar(
            select(CharacterSkill).where(CharacterSkill.skill_id == "gathering")
        )
        assert skill is not None and skill.xp == 100
        character = session.scalar(select(Character))
        assert character is not None and character.stance == "aggressive"


@pytest.mark.anyio
async def test_postgres_stance_waits_for_character_lock(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real stance request waits on a character writer before updating the row."""
    client, factory, _, headers = action_client
    with factory() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("requires PostgreSQL row locks")
    original_lock = lock_character_and_load_action
    entering_lock = threading.Event()
    worker_pids: list[int] = []

    def observed_lock(
        session: Session, identifier: uuid.UUID
    ) -> ActiveActionRecord | None:
        worker_pids.append(session.scalar(text("SELECT pg_backend_pid()")))
        entering_lock.set()
        return original_lock(session, identifier)

    monkeypatch.setattr(action_service, "lock_character_and_load_action", observed_lock)
    with factory() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker.scalar(select(Character).with_for_update())
        blocker_pid = blocker.scalar(text("SELECT pg_backend_pid()"))
        future = pool.submit(
            asyncio.run,
            client.put(
                "/characters/me/stance", headers=headers, json={"stance": "precise"}
            ),
        )
        try:
            assert entering_lock.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pids[0], blocker_pid)
            assert not future.done()
        finally:
            blocker.rollback()
        response = future.result(timeout=10)
    assert response.status_code == 200
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None and character.stance == "precise"


def test_combat_actions_use_category_default_and_allow_bullion(tmp_path: Path) -> None:
    """Combat's default resolver accepts encounter metadata and drops bullion goods."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "skills.json"
    payload = json.loads(path.read_text())
    action = next(skill for skill in payload["skills"] if skill["id"] == "melee")[
        "actions"
    ][0]
    del action["resolver"]
    path.write_text(json.dumps(payload))
    path = directory / "combatants.json"
    payload = json.loads(path.read_text())
    bullion = next(item for item in CONTENT.items if item.bullion)
    payload["combatants"][0]["drops"] = [
        dict(item_id=bullion.id, quantity_min=1, quantity_max=1, chance=1)
    ]
    path.write_text(json.dumps(payload))
    content = load_content(directory)
    assert content.action("placeholder.fight").resolver == "combat"
    assert content.combatants[0].drops[0].item_id == bullion.id
    with pytest.raises(KeyError):
        content.combatant("missing")


@pytest.mark.anyio
async def test_hp_bonus_profile_and_backwards_clock_clamp(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Profiles and combat share HP bonuses, including clamps on backwards reads."""
    client, factory, clock, headers = action_client
    armour = CONTENT.item("item.fake_armour").model_copy(
        update={
            "equip": Equipment(
                slot="chest",
                armour=Armour(armour=10, max_hp=5),
                modifiers=(
                    Modifier(
                        type=ModifierType.COMBAT_HP_PCT, value=100, category="combat"
                    ),
                ),
            )
        }
    )
    content = CONTENT.with_overrides(items=[armour])
    monkeypatch.setattr(app.state, "content", content)
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 400
        character.hp_updated_at = clock.now + timedelta(minutes=1)
        session.add(
            CharacterEquipment(
                character_id=character.id, slot="chest", item_id=armour.id, quantity=1
            )
        )
        session.commit()
    profile = await client.get("/characters/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["max_hp"] == profile.json()["hp"] == 230
    assert as_utc(datetime.fromisoformat(profile.json()["hp_updated_at"])) == (
        clock.now + timedelta(minutes=1)
    )
