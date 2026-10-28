"""Encounter pools, exact cycle order, polling and transactional combat tests."""

import asyncio
import json
import random
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta
from time import perf_counter

import pytest
from httpx import AsyncClient
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock, action_client, anyio_backend
from test_consumables_hp import NOW, state
from test_estates import _wait_for_postgres_blocker

from app.content.loader import ContentIndex
from app.content.runtime import CONTENT
from app.content.schemas import (
    Consumable,
    Drop,
    Equipment,
    Modifier,
    ModifierType,
    TimedBuff,
    Weapon,
)
from app.engine import combat_resolver
from app.engine.combat import AttackResult, CombatStats
from app.engine.core import ActiveAction, BeltStack, CharacterState, resolve
from app.main import app
from app.models import (
    ActiveActionRecord,
    Character,
    CharacterBelt,
    CharacterBuff,
    CharacterEquipment,
    RewardLog,
)
from app.services import actions as action_service

__all__ = ["action_client", "anyio_backend"]
ApiFixture = tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]]
ACTION = CONTENT.skill("melee").actions[0].id


def content(**opponent_changes: object) -> ContentIndex:
    """Disable passive regen to make terminal and pool expectations exact."""
    return replace(
        CONTENT,
        combatants=(CONTENT.combatants[0].model_copy(update=opponent_changes),),
        progression=CONTENT.progression.model_copy(
            update={
                "combat": CONTENT.progression.combat.model_copy(
                    update={"regen_per_min": 0}
                )
            }
        ),
    )


def active() -> ActiveAction:
    """Begin a new encounter at the injected clock origin."""
    return ActiveAction(ACTION, NOW, NOW)


def fixed_attacks(
    monkeypatch: pytest.MonkeyPatch, dealt: int = 1, taken: int = 1, mitigated: int = 0
) -> None:
    """Make player/opponent attacks distinguishable by their authored interval."""

    def hit(attacker: CombatStats, defender: CombatStats, rng: object) -> AttackResult:
        return (
            AttackResult(dealt, 0)
            if attacker.cycle_ms == 2000
            else AttackResult(taken, mitigated)
        )

    monkeypatch.setattr(combat_resolver, "attack", hit)


def test_pools_drain_once_refill_only_on_respawn_and_remainder_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_attacks(monkeypatch)
    pack = content(
        max_hp=3,
        xp_pool_offense=9,
        xp_pool_defense=20,
        attack_interval_ms=1000,
        respawn_ms=4000,
    )
    character = replace(state(), hp=100)
    first = resolve(
        character, active(), pack, NOW + timedelta(seconds=2), random.Random(1)
    )
    assert first[1] is not None
    assert first[1].meta["offense"] == [6, 1]
    assert first[1].meta["defense"] == [18, 1]
    killed = resolve(
        first[0], first[1], pack, NOW + timedelta(seconds=6), random.Random(1)
    )
    assert killed[1] is not None
    assert killed[1].meta["offense"] == killed[1].meta["defense"] == [0, 1]
    assert killed[1].meta["respawn_remaining_ms"] == 4000
    waiting = resolve(
        killed[0], killed[1], pack, NOW + timedelta(seconds=9), random.Random(1)
    )
    assert waiting[1] is not None
    assert waiting[2].cycles_completed == 0
    assert waiting[1].meta["defense"] == [0, 1]
    respawn = resolve(
        waiting[0], waiting[1], pack, NOW + timedelta(seconds=10), random.Random(1)
    )
    assert respawn[1] is not None
    assert respawn[1].meta["offense"] == [9, 1]
    assert respawn[1].meta["defense"] == [20, 1]
    # An opponent which is never killed pays its defensive pool only once.
    pack = content(max_hp=10**6, xp_pool_defense=3, attack_interval_ms=1000)
    result = resolve(
        character, active(), pack, NOW + timedelta(seconds=20), random.Random(1)
    )
    assert result[1] is not None and result[1].meta["defense"] == [0, 1]
    assert (
        result[2].xp_gained.get("vigor", 0) + result[2].xp_gained.get("defense", 0) <= 3
    )


def ranged_state() -> tuple[CharacterState, ContentIndex]:
    """Author a synthetic ranged weapon without adding production content."""
    item = CONTENT.item("item.fake_sword").model_copy(
        update={
            "equip": Equipment(
                slot="right_hand",
                weapon=Weapon(
                    style="ranged",
                    attack_interval_ms=2000,
                    power=0,
                    accuracy=0,
                    damage_type="piercing",
                ),
            )
        }
    )
    return replace(
        state(), hp=100, equipment={"right_hand": item.id}
    ), content().with_overrides(items=(item,))


def test_ranged_requires_ammunition_melee_and_magic_continue() -> None:
    character, pack = ranged_state()
    stopped = resolve(
        character, active(), pack, NOW + timedelta(seconds=2), random.Random(1)
    )
    assert stopped[1] is None and stopped[2].stop_reason == "OUT_OF_AMMO"
    assert stopped[2].cycles_completed == 0
    character = replace(
        character,
        equipment={**character.equipment, "utility": "item.fake_ammo"},
        utility_quantity=1,
    )
    stopped = resolve(
        character, active(), pack, NOW + timedelta(seconds=4), random.Random(1)
    )
    assert stopped[2].cycles_completed == 1
    assert stopped[2].items_consumed == {"item.fake_ammo": 1}
    assert stopped[2].stop_reason == "OUT_OF_AMMO"
    for style in ("melee", "magic"):
        weapon = pack.item("item.fake_sword").model_copy(
            update={
                "equip": Equipment(
                    slot="right_hand",
                    weapon=Weapon(
                        style=style,
                        attack_interval_ms=2000,
                        power=0,
                        accuracy=0,
                        damage_type=style,
                    ),
                )
            }
        )
        result = resolve(
            replace(character, equipment={"right_hand": weapon.id}, utility_quantity=0),
            active(),
            pack.with_overrides(items=(weapon,)),
            NOW + timedelta(seconds=2),
            random.Random(1),
        )
        assert result[2].cycles_completed == 1 and result[2].stop_reason is None


@pytest.mark.parametrize("opponent_hp,kills", [(1, 1), (10, 0)])
def test_defeat_ends_action_and_simultaneous_kill_counts_first(
    monkeypatch: pytest.MonkeyPatch, opponent_hp: int, kills: int
) -> None:
    fixed_attacks(monkeypatch, taken=1000)
    drop = Drop(item_id="item.fake_sprig", quantity_min=1, quantity_max=1, chance=1)
    pack = content(max_hp=opponent_hp, attack_interval_ms=1000, drops=(drop,))
    result = resolve(
        replace(state(), hp=1),
        active(),
        pack,
        NOW + timedelta(seconds=2),
        random.Random(2),
    )
    assert result[1] is None
    assert result[2].stop_reason == "DEFEATED"
    assert result[2].details["kills"] == kills
    assert result[2].details["defeats"] == 1
    assert result[2].items_gained == ({"item.fake_sprig": 1} if kills else {})
    assert result[0].hp == 0


def test_offensive_taper_drains_pool_defense_and_drops_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_attacks(monkeypatch, dealt=1)
    pack = content(
        max_hp=2,
        xp_pool_offense=100,
        xp_pool_defense=100,
        attack_interval_ms=1000,
        drops=(
            Drop(item_id="item.fake_sprig", quantity_min=2, quantity_max=2, chance=1),
        ),
    )
    base = replace(state(), hp=100)
    results = [
        resolve(
            replace(
                base,
                skill_levels={"melee": level},
                skills_xp={"melee": pack.xp_curve.levels[level - 1].xp},
            ),
            active(),
            pack,
            NOW + timedelta(seconds=4),
            random.Random(3),
        )
        for level in (1, 95)
    ]
    assert results[0][2].xp_gained["melee"] > results[1][2].xp_gained.get("melee", 0)
    for result in results:
        assert result[1] is not None and result[1].meta["offense"] == [0, 1]
        assert result[2].items_gained == {"item.fake_sprig": 2}
    assert results[0][2].xp_gained.get("defense", 0) == results[1][2].xp_gained.get(
        "defense", 0
    )
    assert results[0][2].xp_gained.get("vigor", 0) == results[1][2].xp_gained.get(
        "vigor", 0
    )


@settings(deadline=None, max_examples=20)
@given(seed=st.integers(0, 10000), step_ms=st.integers(137, 7000))
def test_offline_equals_online_polling(seed: int, step_ms: int) -> None:
    """Serialization, partial cycles, respawn and fractional XP survive polling."""
    buff = CONTENT.item("item.fake_buff").model_copy(
        update={
            "consumable": Consumable(
                buff=TimedBuff(
                    modifiers=(
                        Modifier(
                            type=ModifierType.COMBAT_DEFENSE_PCT,
                            value=50,
                            category="combat",
                        ),
                    ),
                    duration_ms=3000,
                )
            )
        }
    )
    pack = replace(
        content(max_hp=4, xp_pool_offense=7, attack_interval_ms=1000, power=1),
        progression=CONTENT.progression,
    ).with_overrides(items=(buff,))
    character = replace(
        state(),
        hp=40,
        belt={
            0: BeltStack(buff.id, 20, {"buff_missing": True}),
            1: BeltStack("item.fake_food", 4, {"hp_below_pct": 50}),
        },
    )
    end_ms = 30000
    offline = resolve(
        character,
        active(),
        pack,
        NOW + timedelta(milliseconds=end_ms),
        random.Random(seed),
    )
    current, running = character, active()
    for milliseconds in [*range(step_ms, end_ms, step_ms), end_ms]:
        current, next_action, _ = resolve(
            current,
            running,
            pack,
            NOW + timedelta(milliseconds=milliseconds),
            random.Random(seed),
        )
        assert next_action is not None
        # Exercise the same JSON boundary as both database dialects.
        running = replace(next_action, meta=json.loads(json.dumps(next_action.meta)))
    assert current == offline[0]
    assert running == offline[1]


def test_regeneration_then_one_belt_item_in_slot_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_attacks(monkeypatch, taken=10)
    pack = content(attack_interval_ms=1000)
    character = replace(
        state(),
        hp=30,
        belt={
            1: BeltStack("item.fake_food", 2, {"hp_below_pct": 100}),
            0: BeltStack("item.fake_buff", 2, {"buff_missing": True}),
        },
    )
    first = resolve(
        character, active(), pack, NOW + timedelta(seconds=2), random.Random(1)
    )
    assert first[2].items_consumed == {"item.fake_buff": 1}
    assert first[0].belt[1].quantity == 2
    assert first[0].buff_expiries["item.fake_buff"] > NOW
    assert first[1] is not None
    second = resolve(
        first[0], first[1], pack, NOW + timedelta(seconds=4), random.Random(1)
    )
    assert second[2].items_consumed == {"item.fake_food": 1}


def test_regeneration_rescues_zero_hp_before_terminal_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Isolate the literal zero-HP ruling so ratification changes one test."""
    fixed_attacks(monkeypatch, taken=10)
    pack = replace(content(attack_interval_ms=1000), progression=CONTENT.progression)
    result = resolve(
        replace(state(), hp=1),
        active(),
        pack,
        NOW + timedelta(seconds=2),
        random.Random(1),
    )
    assert result[0].hp is not None and result[0].hp > 0
    assert result[2].stop_reason is None


def test_cycle_ceiling_stops_with_uppercase_offline_cap() -> None:
    pack = content(attack_interval_ms=1000000, max_hp=10**9)
    pack = replace(
        pack,
        progression=pack.progression.model_copy(
            update={
                "combat": pack.progression.combat.model_copy(
                    update={"max_cycles_per_resolve": 3}
                )
            }
        ),
    )
    result = resolve(
        state(), active(), pack, NOW + timedelta(seconds=20), random.Random(1)
    )
    assert result[2].cycles_completed == 3
    assert result[1] is None and result[2].stop_reason == "OFFLINE_CAP"


def test_twelve_hours_two_second_cycles_time_bound() -> None:
    """Normal CI exercises the pure loop independently of database latency."""
    pack = replace(
        content(
            max_hp=10**9, attack_interval_ms=2000, xp_pool_offense=0, xp_pool_defense=0
        ),
        progression=CONTENT.progression,
    )
    started = perf_counter()
    character = replace(
        state(),
        skill_levels={"vigor": 100, "defense": 100},
        skills_xp={
            skill: pack.xp_curve.levels[99].xp for skill in ("vigor", "defense")
        },
    )
    result = resolve(
        character, active(), pack, NOW + timedelta(hours=12), random.Random(1)
    )
    elapsed = perf_counter() - started
    assert result[2].cycles_completed == 21600
    # This workload survives without zero-HP revival, independent of ratification.
    assert result[0].hp is not None and result[0].hp > 1000
    # Cached runtime is about 0.31s; use the requested 2s floor over 3× that.
    assert elapsed < 2, f"12-hour pure combat simulation took {elapsed:.3f}s"


@pytest.mark.anyio
async def test_engagement_gate_and_consumable_setup_combat_guards(
    action_client: ApiFixture,
) -> None:
    client, factory, clock, headers = action_client
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 1
        character.hp_updated_at = clock.now
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"action_id": ACTION}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_HP"
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 27.5  # Exactly 25% of the unarmoured maximum.
        session.commit()
    assert (
        await client.post("/actions/start", headers=headers, json={"action_id": ACTION})
    ).status_code == 200
    for path in ("/equipment/utility", "/equipment/belt/0"):
        response = await client.put(
            path, headers=headers, json={"item_id": None, "quantity": 0}
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EQUIPMENT_IN_COMBAT"
    assert (
        await client.put(
            "/characters/me/stance", headers=headers, json={"stance": "precise"}
        )
    ).status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize("existing_buff", [False, True])
async def test_combat_persists_hp_consumption_buffs_and_claims_once(
    action_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
    existing_buff: bool,
) -> None:
    client, factory, clock, headers = action_client
    fixed_attacks(monkeypatch)
    pack = content(attack_interval_ms=1000)
    monkeypatch.setattr(app.state, "content", pack)
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 80
        character.hp_updated_at = clock.now
        session.add(
            CharacterEquipment(
                character_id=character.id,
                slot="utility",
                item_id="item.fake_ammo",
                quantity=2,
            )
        )
        session.add(
            CharacterBelt(
                character_id=character.id,
                slot=0,
                item_id="item.fake_buff",
                quantity=1,
                trigger={"buff_missing": True},
            )
        )
        if existing_buff:
            session.add(
                CharacterBuff(
                    character_id=character.id,
                    item_id="item.fake_buff",
                    expires_at=clock.now - timedelta(seconds=1),
                )
            )
        session.commit()
    await client.post("/actions/start", headers=headers, json={"action_id": ACTION})
    clock.advance(timedelta(seconds=2))
    response = await client.get("/actions/poll", headers=headers)
    assert response.status_code == 200
    assert response.json()["since_last"]["items_consumed"] == {"item.fake_buff": 1}
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None and character.hp == 78
        buff = session.get(CharacterBuff, (character.id, "item.fake_buff"))
        assert buff is not None
        definition = pack.item("item.fake_buff").consumable
        assert definition is not None and definition.buff is not None
        assert action_service.as_utc(buff.expires_at) == (
            clock.now + timedelta(milliseconds=definition.buff.duration_ms)
        )
        assert session.get(CharacterBelt, (character.id, 0)) is None
        utility = session.get(CharacterEquipment, (character.id, "utility"))
        assert utility is not None and utility.quantity == 2
    response = await client.get("/actions/poll", headers=headers)
    assert response.json()["since_last"]["xp_gained"] == {}


@pytest.mark.anyio
async def test_postgres_combat_poll_waits_and_never_double_rewards(
    action_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two overlapping combat polls serialize on the character parent row."""
    client, factory, clock, headers = action_client
    with factory() as session:
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("requires PostgreSQL row locks")
    fixed_attacks(monkeypatch)
    pack = content(attack_interval_ms=1000)
    monkeypatch.setattr(app.state, "content", pack)
    assert (
        await client.post("/actions/start", headers=headers, json={"action_id": ACTION})
    ).status_code == 200
    clock.advance(timedelta(seconds=2))
    entering_lock = threading.Event()
    worker_pids: list[int] = []
    original_lock = action_service.lock_character_and_load_action

    def observed_lock(
        session: Session, identifier: uuid.UUID
    ) -> ActiveActionRecord | None:
        worker_pids.append(session.scalar(text("SELECT pg_backend_pid()")))
        entering_lock.set()
        return original_lock(session, identifier)

    monkeypatch.setattr(action_service, "lock_character_and_load_action", observed_lock)
    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        character = first.scalar(select(Character))
        assert character is not None
        first_result = action_service.resolve_character(
            first, character.id, clock.now, pack
        )
        assert first_result.result.cycles_completed == 1
        blocker_pid = first.scalar(text("SELECT pg_backend_pid()"))
        entering_lock.clear()
        worker_pids.clear()
        future = pool.submit(asyncio.run, client.get("/actions/poll", headers=headers))
        try:
            assert entering_lock.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pids[-1], blocker_pid)
            assert not future.done()
        finally:
            first.commit()
        response = future.result(timeout=10)
    assert response.status_code == 200
    assert response.json()["since_last"]["cycles_completed"] == 1
    with factory() as session:
        assert session.scalar(select(func.sum(RewardLog.cycles))) == 1
        character = session.scalar(select(Character))
        assert character is not None and character.hp == 108
    response = await client.get("/actions/poll", headers=headers)
    assert response.json()["since_last"]["cycles_completed"] == 0


@pytest.mark.anyio
async def test_combat_regeneration_is_not_applied_before_fighting_or_twice(
    action_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The adapter delegates elapsed combat healing to each simulated cycle."""
    client, factory, clock, headers = action_client
    fixed_attacks(monkeypatch, taken=5)
    pack = replace(content(attack_interval_ms=1000), progression=CONTENT.progression)
    monkeypatch.setattr(app.state, "content", pack)
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character.hp = 80
        character.hp_updated_at = clock.now
        session.commit()
    await client.post("/actions/start", headers=headers, json={"action_id": ACTION})
    clock.advance(timedelta(seconds=2))
    for _ in range(2):
        profile = await client.get("/characters/me", headers=headers)
        assert profile.json()["hp"] == pytest.approx(70 + 110 * 0.01 / 30)
    completed_at = clock.now
    clock.advance(timedelta(milliseconds=750))
    stopped = await client.post("/actions/stop", headers=headers)
    assert stopped.status_code == 200 and stopped.json()["active"] is None
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None and character.hp_updated_at is not None
        # Stopping discards the partial attack; its healing stays lazily pending.
        assert action_service.as_utc(character.hp_updated_at) == completed_at
    profile = await client.get("/characters/me", headers=headers)
    assert (
        action_service.as_utc(datetime.fromisoformat(profile.json()["hp_updated_at"]))
        == clock.now
    )
    assert profile.json()["hp"] == pytest.approx(70 + 110 * 0.01 * 2.75 / 60)
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None and character.hp_updated_at is not None
        assert action_service.as_utc(character.hp_updated_at) == clock.now


def test_loot_overflow_discards_excess_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_attacks(monkeypatch)
    pack = content(
        max_hp=1,
        attack_interval_ms=1000,
        drops=(
            Drop(item_id="item.fake_sprig", quantity_min=3, quantity_max=3, chance=1),
        ),
    )
    limit = pack.item("item.fake_sprig").stack_limit
    result = resolve(
        replace(state(), hp=100, inventory={"item.fake_sprig": limit - 1}),
        active(),
        pack,
        NOW + timedelta(seconds=2),
        random.Random(1),
    )
    assert result[1] is None and result[2].stop_reason == "inventory_full"
    assert result[0].inventory["item.fake_sprig"] == limit
    assert result[2].items_gained == {"item.fake_sprig": 1}
    assert result[2].overflowed_items == {"item.fake_sprig": 2}


def test_respawn_wait_buff_expiry_and_regeneration_match_polling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_attacks(monkeypatch, taken=10)
    modifier = Modifier(type=ModifierType.COMBAT_HP_PCT, value=100, category="combat")
    buff_item = CONTENT.item("item.fake_buff").model_copy(
        update={
            "consumable": Consumable(
                buff=TimedBuff(modifiers=(modifier,), duration_ms=3000)
            )
        }
    )
    pack = replace(
        content(max_hp=1, attack_interval_ms=1000, respawn_ms=6000),
        progression=CONTENT.progression,
    ).with_overrides(items=(buff_item,))
    character = replace(
        state(), hp=80, belt={0: BeltStack(buff_item.id, 10, {"buff_missing": True})}
    )
    offline = resolve(
        character, active(), pack, NOW + timedelta(seconds=12), random.Random(1)
    )
    current, running = character, active()
    for seconds in range(1, 13):
        current, following, _ = resolve(
            current, running, pack, NOW + timedelta(seconds=seconds), random.Random(1)
        )
        assert following is not None
        running = following
    assert current == offline[0]
    assert running == offline[1]


def test_offline_budget_clips_respawn_wait() -> None:
    pack = content(max_hp=1, respawn_ms=24 * 3600000, attack_interval_ms=1000000)
    running = replace(
        active(),
        meta={
            "opponent_hp": 0,
            "offense": [0, 1],
            "defense": [0, 1],
            "attack_carry_ms": 0,
            "respawn_remaining_ms": 24 * 3600000,
        },
    )
    result = resolve(
        state(), running, pack, NOW + timedelta(hours=13), random.Random(1)
    )
    assert result[2].cycles_completed == 0
    assert result[2].elapsed_ms == 12 * 3600000
    assert result[1] is None and result[2].stop_reason == "OFFLINE_CAP"


def test_offensive_taper_drains_untapered_pool_before_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pool accounting must be observable before a kill discards its remainder."""
    fixed_attacks(monkeypatch, dealt=10)
    pack = content(max_hp=1000, xp_pool_offense=1000, attack_interval_ms=1000)
    results = [
        resolve(
            replace(
                state(),
                hp=100,
                skill_levels={"melee": level},
                skills_xp={"melee": pack.xp_curve.levels[level - 1].xp},
            ),
            active(),
            pack,
            NOW + timedelta(seconds=4),
            random.Random(3),
        )
        for level in (1, 95)
    ]
    for result in results:
        assert result[1] is not None
        assert result[2].details["kills"] == 0
        assert result[1].meta["opponent_hp"] == 980
        assert result[1].meta["offense"] == [980, 1]
    assert results[0][1] is not None and results[1][1] is not None
    assert results[0][1].meta["offense"] == results[1][1].meta["offense"]
    assert results[0][2].xp_gained["melee"] == 10
    assert results[1][2].xp_gained.get("melee", 0) == 0


@pytest.mark.parametrize("defensive_pool,defensive_share", [(100, 16), (16, 8)])
def test_exact_offensive_stance_and_defensive_taken_mitigated_split(
    monkeypatch: pytest.MonkeyPatch,
    defensive_pool: int,
    defensive_share: int,
) -> None:
    """Split two enemy attacks, including taken→Defense and pool clipping."""
    fixed_attacks(monkeypatch, dealt=10, taken=5, mitigated=3)
    pack = content(
        max_hp=100,
        xp_pool_offense=200,
        xp_pool_defense=defensive_pool,
        defense_xp_per_damage=2,
        attack_interval_ms=1000,
    )
    result = resolve(
        replace(state(), hp=100, stance="precise"),
        active(),
        pack,
        NOW + timedelta(seconds=2),
        random.Random(1),
    )
    # Offense: 10 * 200 / 100 = 20; precise splits 25% / 75%.
    # Defense: taken=10, mitigated=6, rate=2. Vigor gets 10*2*80%=16;
    # Defense gets 6*2 + 10*2*20%=16. A 16-point pool halves both.
    assert result[2].xp_gained == {
        "melee": 5,
        "accuracy": 15,
        "vigor": defensive_share,
        "defense": defensive_share,
    }
    assert result[1] is not None
    assert result[1].meta["offense"] == [180, 1]
    assert result[1].meta["defense"] == [max(0, defensive_pool - 32), 1]


@pytest.mark.anyio
async def test_ranged_ammunition_quantity_persists_and_empty_row_is_deleted(
    action_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Matching utility is consumed once per cycle, including across DB reloads."""
    client, factory, clock, headers = action_client
    _, pack = ranged_state()
    monkeypatch.setattr(app.state, "content", pack)
    fixed_attacks(monkeypatch, taken=0)
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        character_id = character.id
        session.add_all(
            [
                CharacterEquipment(
                    character_id=character_id,
                    slot="right_hand",
                    item_id="item.fake_sword",
                    quantity=1,
                ),
                CharacterEquipment(
                    character_id=character_id,
                    slot="utility",
                    item_id="item.fake_ammo",
                    quantity=2,
                ),
            ]
        )
        session.commit()
    response = await client.post(
        "/actions/start", headers=headers, json={"action_id": ACTION}
    )
    assert response.status_code == 200
    for remaining in (1, 0):
        clock.advance(timedelta(seconds=2))
        response = await client.get("/actions/poll", headers=headers)
        assert response.status_code == 200
        assert response.json()["since_last"]["items_consumed"] == {"item.fake_ammo": 1}
        assert response.json()["stop_reason"] is None
        with factory() as session:
            utility = session.get(CharacterEquipment, (character_id, "utility"))
            if remaining:
                assert utility is not None and utility.quantity == remaining
            else:
                assert utility is None
    clock.advance(timedelta(seconds=2))
    response = await client.get("/actions/poll", headers=headers)
    assert response.status_code == 200
    assert response.json()["active"] is None
    assert response.json()["stop_reason"] == "OUT_OF_AMMO"
    assert response.json()["since_last"]["cycles_completed"] == 0
    with factory() as session:
        assert session.get(CharacterEquipment, (character_id, "utility")) is None


@pytest.mark.parametrize("starting_xp", [0, CONTENT.xp_curve.levels[1].xp - 1])
@pytest.mark.parametrize("with_buff", [False, True])
def test_level_up_and_buff_boundaries_refresh_combat_parameters(
    monkeypatch: pytest.MonkeyPatch,
    starting_xp: int,
    with_buff: bool,
) -> None:
    """Following attacks use a gained level, an activated buff, then its expiry."""
    buff = CONTENT.item("item.fake_buff").model_copy(
        update={
            "consumable": Consumable(
                buff=TimedBuff(
                    modifiers=(
                        Modifier(
                            type=ModifierType.COMBAT_POWER_PCT,
                            value=100,
                            category="combat",
                        ),
                    ),
                    duration_ms=2000,
                )
            )
        }
    )
    pack = content(
        max_hp=100,
        xp_pool_offense=100,
        attack_interval_ms=1000,
    ).with_overrides(items=(buff,))
    hits: list[int] = []

    def hit(
        attacker: CombatStats,
        defender: CombatStats,
        rng: object,
    ) -> AttackResult:
        if attacker.damage_type == "blunt":
            hits.append(attacker.max_hit)
            return AttackResult(attacker.max_hit, 0)
        return AttackResult(0, 0)

    monkeypatch.setattr(combat_resolver, "attack", hit)
    character = replace(
        state(),
        hp=100,
        stance="balanced",
        skills_xp={"melee": starting_xp},
        belt={0: BeltStack(buff.id, 1, {"buff_missing": True})} if with_buff else {},
    )
    result = resolve(
        character,
        active(),
        pack,
        NOW + timedelta(seconds=6),
        random.Random(1),
    )
    next_hit = 3 if starting_xp else 2
    expected = [2, next_hit * (2 if with_buff else 1), next_hit]
    assert hits == expected
    assert result[0].skill_levels["melee"] == (2 if starting_xp else 1)
    assert result[2].details["damage_dealt"] == sum(expected)
    assert result[1] is not None
    assert result[1].meta["offense"] == [100 - sum(expected), 1]
