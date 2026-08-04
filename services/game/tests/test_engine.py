"""Behavioral and property tests for the pure lazy-resolution engine."""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.content.loader import ContentIndex, load_content
from app.content.schemas import (
    Action,
    CapBonus,
    CapType,
    EstateUpgrade,
    Modifier,
    ModifierType,
)
from app.engine import (
    OK,
    ActiveAction,
    CharacterState,
    CycleRewards,
    ErrorCode,
    RandomSource,
    StopReason,
    can_start,
    effective_cycle_time,
    effective_drops,
    effective_xp,
    resolve,
    resolve_caps,
)

START = datetime(2025, 1, 1, tzinfo=UTC)


class FixedRng:
    """Predictable RNG which takes guaranteed drops only."""

    def random(self) -> float:
        """Miss probabilities below one and hit probability one."""
        return 0.5

    def randint(self, a: int, b: int) -> int:
        """Always choose the minimum drop quantity."""
        return a


@pytest.fixture(scope="module")
def content() -> ContentIndex:
    """Load the checked-in placeholder pack."""
    return load_content(Path(__file__).parents[3] / "content")


def make_state(
    *,
    inventory: dict[str, int] | None = None,
    xp: int = 0,
    level: int = 1,
    upgrades: tuple[str, ...] = (),
    tier: int = 0,
) -> CharacterState:
    """Build a minimal gathering character for engine tests."""
    return CharacterState(
        skills_xp={"gathering": xp, "refining": 0},
        skill_levels={"gathering": level, "refining": 1},
        inventory=inventory or {},
        gold=0,
        realm_id="realm.verdant_vale",
        installed_upgrades=upgrades,
        realm_tier=tier,
    )


def make_active(action_id: str = "gathering.fake_sprigs") -> ActiveAction:
    """Create an action beginning at the shared test timestamp."""
    return ActiveAction(action_id, START, START)


def with_action(content: ContentIndex, action: Action) -> ContentIndex:
    """Replace one indexed action in immutable test content."""
    return content.with_overrides(actions=(action,))


def test_clock_regression_is_a_no_op(content: ContentIndex) -> None:
    """A backwards server-clock correction does not fail or grant rewards."""
    initial_state = make_state()
    active = make_active()

    state, next_active, result = resolve(
        initial_state,
        active,
        content,
        START - timedelta(seconds=1),
        FixedRng(),
    )

    assert state == initial_state
    assert next_active == active
    assert result.cycles_completed == 0


def test_exact_and_partial_cycle_timestamp_math(content: ContentIndex) -> None:
    """Only full cycles advance the authoritative resolution timestamp."""
    state, resolved_active, result = resolve(
        make_state(),
        make_active(),
        content,
        START + timedelta(milliseconds=5_500),
        FixedRng(),
    )
    assert result.cycles_completed == 2  # Verdant's -10% makes this 2,700 ms.
    assert resolved_active is not None
    assert resolved_active.last_resolved_at == START + timedelta(milliseconds=5_400)
    assert state.skills_xp["gathering"] == 20


@given(
    first_ms=st.integers(min_value=0, max_value=40_000),
    extra_ms=st.integers(min_value=0, max_value=40_000),
)
def test_repeated_resolve_equals_one_large_resolve(
    content: ContentIndex, first_ms: int, extra_ms: int
) -> None:
    """Incremental polling preserves remainder and deterministic state math.

    FixedRng intentionally limits this property to timestamps, XP, levels, and
    guaranteed drops. Production resolves are independently seeded, so random
    drop sequences are not expected to be associative across polling boundaries.
    """
    final_now = START + timedelta(milliseconds=first_ms + extra_ms)
    incremental_rng = FixedRng()
    state_a, active_a, _ = resolve(
        make_state(),
        make_active(),
        content,
        START + timedelta(milliseconds=first_ms),
        incremental_rng,
    )
    assert active_a is not None
    state_a, active_a, _ = resolve(
        state_a, active_a, content, final_now, incremental_rng
    )
    state_b, active_b, _ = resolve(
        make_state(), make_active(), content, final_now, FixedRng()
    )
    assert state_a == state_b
    assert active_a == active_b


def test_offline_cap_resolves_only_budgeted_cycles(content: ContentIndex) -> None:
    """Thirteen elapsed hours grants exactly the twelve-hour base cap."""
    state, active, result = resolve(
        make_state(), make_active(), content, START + timedelta(hours=13), FixedRng()
    )
    assert result.cycles_completed == 16_000
    assert result.stop_reason == StopReason.OFFLINE_CAP
    assert active is None
    assert state.skills_xp["gathering"] == 160_000


def test_exact_offline_budget_advances_by_resolved_cycles(
    content: ContentIndex,
) -> None:
    """Exactly twelve hours advances by cycles while keeping the action active."""
    _, active, result = resolve(
        make_state(), make_active(), content, START + timedelta(hours=12), FixedRng()
    )
    assert result.cycles_completed == 16_000
    assert result.stop_reason is None
    assert active is not None
    assert active.last_resolved_at == START + timedelta(hours=12)


def test_offline_cap_does_not_end_action_when_no_cycle_fits(
    content: ContentIndex,
) -> None:
    """A cycle longer than the offline budget remains pending with no progress."""
    action = content.action("gathering.fake_sprigs").model_copy(
        update={"cycle_ms": 14 * 3_600_000}
    )
    _, active, result = resolve(
        make_state(),
        make_active(),
        with_action(content, action),
        START + timedelta(hours=13),
        FixedRng(),
    )
    assert result.cycles_completed == 0
    assert result.xp_gained == {}
    assert result.stop_reason is None
    assert active == make_active()


def test_input_exhaustion_mid_batch(content: ContentIndex) -> None:
    """Resolution consumes two recipes then ends before an unaffordable third."""
    state, active, result = resolve(
        make_state(inventory={"item.fake_sprig": 5}),
        make_active("refining.fake_plank"),
        content,
        START + timedelta(milliseconds=13_500),
        FixedRng(),
    )
    assert result.cycles_completed == 2
    assert result.items_consumed == {"item.fake_sprig": 4}
    assert state.inventory["item.fake_sprig"] == 1
    assert result.stop_reason == StopReason.INPUTS_EXHAUSTED
    assert active is None


def test_inventory_overflow_discards_drop_and_stops(content: ContentIndex) -> None:
    """A new stack beyond capacity is logged, discarded, and ends the action."""
    tiny = replace(content, caps=content.caps.model_copy(update={"inventory_slots": 1}))
    state, active, result = resolve(
        make_state(inventory={"item.mock_ore": 1}),
        make_active(),
        tiny,
        START + timedelta(milliseconds=2_700),
        FixedRng(),
    )
    assert result.cycles_completed == 1
    assert result.items_gained == {}
    assert result.overflowed_items == {"item.fake_sprig": 1}
    assert state.inventory == {"item.mock_ore": 1}
    assert result.stop_reason == StopReason.INVENTORY_FULL
    assert active is None


def test_stack_limit_overflow_is_discarded(content: ContentIndex) -> None:
    """An existing stack accepts only quantities below its content-defined limit."""
    sprig = content.item("item.fake_sprig").model_copy(update={"stack_limit": 1})
    limited = content.with_overrides(items=(sprig,))
    state, active, result = resolve(
        make_state(inventory={sprig.id: 1}),
        make_active(),
        limited,
        START + timedelta(milliseconds=2_700),
        FixedRng(),
    )
    assert state.inventory == {sprig.id: 1}
    assert result.items_gained == {}
    assert result.overflowed_items == {sprig.id: 1}
    assert result.stop_reason == StopReason.INVENTORY_FULL
    assert active is None


def test_consuming_input_frees_a_slot_before_drops(content: ContentIndex) -> None:
    """Input consumption occurs first, allowing output to occupy its freed slot."""
    tiny = replace(content, caps=content.caps.model_copy(update={"inventory_slots": 1}))
    state, _, result = resolve(
        make_state(inventory={"item.fake_sprig": 2}),
        make_active("refining.fake_plank"),
        tiny,
        START + timedelta(milliseconds=9_000),
        FixedRng(),
    )
    assert result.cycles_completed == 1
    assert result.items_consumed == {"item.fake_sprig": 2}
    assert result.items_gained == {"item.fake_plank": 1}
    assert result.overflowed_items == {}
    assert state.inventory == {"item.fake_plank": 1}
    assert result.stop_reason == StopReason.INPUTS_EXHAUSTED


def test_action_ends_when_final_recipe_is_consumed(content: ContentIndex) -> None:
    """Exhaustion is reported even when elapsed time ends at that cycle boundary."""
    _, active, result = resolve(
        make_state(inventory={"item.fake_sprig": 2}),
        make_active("refining.fake_plank"),
        content,
        START + timedelta(milliseconds=4_500),
        FixedRng(),
    )
    assert result.cycles_completed == 1
    assert result.stop_reason == StopReason.INPUTS_EXHAUSTED
    assert active is None


def test_overflow_precedes_input_exhaustion_in_same_cycle(
    content: ContentIndex,
) -> None:
    """Capacity is the reported stop when one cycle also consumes final inputs."""
    plank = content.item("item.fake_plank").model_copy(update={"stack_limit": 1})
    limited = content.with_overrides(items=(plank,))
    _, active, result = resolve(
        make_state(inventory={"item.fake_sprig": 2, plank.id: 1}),
        make_active("refining.fake_plank"),
        limited,
        START + timedelta(milliseconds=4_500),
        FixedRng(),
    )
    assert result.items_consumed == {"item.fake_sprig": 2}
    assert result.overflowed_items == {plank.id: 1}
    assert result.stop_reason == StopReason.INVENTORY_FULL
    assert active is None


class LevelSensitiveRewards:
    """Test strategy demonstrating mid-batch state recomputation."""

    def rewards(
        self,
        action: Action,
        state: CharacterState,
        content: ContentIndex,
        rng: RandomSource,
    ) -> CycleRewards:
        """Give 100 XP at level one and 20 XP after leveling."""
        del action, content, rng
        reward = 100 if state.skill_levels["gathering"] == 1 else 20
        return CycleRewards(reward, ())


def test_level_up_changes_subsequent_cycle_resolution(content: ContentIndex) -> None:
    """Each cycle strategy sees levels produced by the preceding cycle."""
    action = content.action("gathering.fake_sprigs").model_copy(
        update={"cycle_ms": 1_000, "drops": ()}
    )
    custom = with_action(content, action)
    state, _, result = resolve(
        make_state(),
        make_active(),
        custom,
        START + timedelta(milliseconds=2_700),
        FixedRng(),
        reward_strategy=LevelSensitiveRewards(),
    )
    assert result.cycles_completed == 3
    assert result.xp_gained == {"gathering": 140}
    assert result.level_ups == {"gathering": (2,)}
    assert state.skill_levels["gathering"] == 2


def test_modifiers_stack_additively_and_inert_upgrade_is_excluded(
    content: ContentIndex,
) -> None:
    """Realm, tier, and active upgrades sum once; mismatched upgrades do nothing."""
    active_upgrade = EstateUpgrade(
        id="upgrade.active",
        name="Active Test Upgrade",
        cost=(),
        modifiers=(
            Modifier(type=ModifierType.CYCLE_TIME_PCT, value=-5),
            Modifier(type=ModifierType.XP_PCT, value=10),
            Modifier(type=ModifierType.EXTRA_DROP_CHANCE_PCT, value=20),
        ),
        realm_tags=("verdant",),
    )
    inert_upgrade = active_upgrade.model_copy(
        update={"id": "upgrade.inert", "realm_tags": ("ashen",)}
    )
    custom = content.with_overrides(upgrades=(active_upgrade, inert_upgrade))
    state = make_state(upgrades=(active_upgrade.id, inert_upgrade.id), tier=1)
    action = custom.action("gathering.fake_sprigs")
    assert effective_cycle_time(action, state, custom) == 2_550
    assert effective_xp(action, state, custom) == 11  # tier +5%, upgrade +10%
    button = effective_drops(action, state, custom)[1]
    assert button.chance == pytest.approx(0.06)


def test_caps_include_active_upgrades_and_ignore_inert_ones(
    content: ContentIndex,
) -> None:
    """Cap resolution follows the same realm-tag inertness rule as modifiers."""
    active = EstateUpgrade(
        id="upgrade.slots",
        name="Test Slots",
        cost=(),
        cap_bonuses=(CapBonus(cap=CapType.INVENTORY_SLOTS, value=3),),
        realm_tags=("verdant",),
    )
    inert = active.model_copy(
        update={"id": "upgrade.inert_slots", "realm_tags": ("ashen",)}
    )
    custom = content.with_overrides(upgrades=(active, inert))
    caps = resolve_caps(make_state(upgrades=(active.id, inert.id)), custom)
    assert caps.inventory_slots == content.caps.inventory_slots + 3


def test_seeded_drop_frequency_is_close_to_declared_chance(
    content: ContentIndex,
) -> None:
    """Ten thousand cycles statistically track the five-percent button chance."""
    state, _, result = resolve(
        make_state(),
        make_active(),
        content,
        START + timedelta(milliseconds=27_000_000),
        random.Random(2025),
    )
    observed = result.items_gained.get("item.worthless_button", 0) / 10_000
    assert observed == pytest.approx(0.05, abs=0.008)
    assert state.inventory["item.fake_sprig"] >= 10_000


@given(cycles=st.integers(min_value=1, max_value=100))
def test_recipe_input_conservation(content: ContentIndex, cycles: int) -> None:
    """Consumed inputs equal recipe quantity times completed cycles exactly."""
    _, _, result = resolve(
        make_state(inventory={"item.fake_sprig": cycles * 2}),
        make_active("refining.fake_plank"),
        content,
        START + timedelta(milliseconds=(cycles + 1) * 4_500),
        FixedRng(),
    )
    assert result.cycles_completed == cycles
    assert result.items_consumed == {"item.fake_sprig": cycles * 2}


@pytest.mark.parametrize(
    ("state", "action_id", "expected"),
    [
        (make_state(level=1), "gathering.mock_ore", ErrorCode.INSUFFICIENT_LEVEL),
        (make_state(level=10), "gathering.mock_ore", ErrorCode.WRONG_REALM),
        (make_state(), "refining.fake_plank", ErrorCode.MISSING_INPUTS),
        (
            make_state(inventory={"item.fake_sprig": 2}),
            "refining.fake_plank",
            OK,
        ),
    ],
)
def test_can_start_checks_boundaries(
    content: ContentIndex,
    state: CharacterState,
    action_id: str,
    expected: object,
) -> None:
    """Start validation returns stable results in documented priority order."""
    assert can_start(action_id, state, content) == expected
