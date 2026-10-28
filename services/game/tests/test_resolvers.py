"""Golden compatibility, resolver dispatch and presence contracts."""

import json
import random
from dataclasses import asdict, replace
from datetime import timedelta
from pathlib import Path
from types import MappingProxyType

from test_engine import START, make_active, make_state

from app.content.loader import load_content
from app.content.schemas import Action, CapBonus, CapType
from app.engine import (
    CharacterState,
    RandomSource,
    ResolveContext,
    ResolveResult,
    StopReason,
    home_realm,
    is_present,
    is_resident,
    resolve,
    resolve_caps,
)

CONTENT = load_content(Path(__file__).parents[3] / "content")


def test_uniform_matches_pre_refactor_goldens() -> None:
    """Seeded shipped outcomes retain rewards, state, stops and partial time."""
    rows = json.loads(Path(__file__).with_name("resolve_goldens.json").read_text())
    for row in rows:
        state, active, result = resolve(
            make_state(inventory=row["inventory"]),
            make_active(row.get("action_id", "gathering.fake_sprigs")),
            CONTENT,
            START + timedelta(milliseconds=row["ms"]),
            random.Random(row["seed"]),
        )
        # Compare every pre-existing field; the new seam adds explicit state,
        # consumed time and details without changing those recorded outcomes.
        actual = json.loads(json.dumps(asdict(state), default=str))
        actual.pop("realm_states")
        assert actual.pop("right_hand_tool_class") is None
        actual["realm_id"] = actual.pop("current_realm_id")
        assert actual == row["state"]
        actual_active = asdict(active) if active else None
        if actual_active is not None:
            actual_active.pop("meta")
        assert json.loads(json.dumps(actual_active, default=str)) == row["active"]
        actual_result = asdict(result)
        for name in ("state", "active", "elapsed_ms", "details"):
            actual_result.pop(name)
        assert json.loads(json.dumps(actual_result, default=str)) == row["result"]
        if active:
            assert result.elapsed_ms == int(
                (active.last_resolved_at - START).total_seconds() * 1000
            )


class StepResolver:
    """A synthetic step demonstrates the seam without implementing travel."""

    def resolve(
        self,
        state: CharacterState,
        action: Action,
        ctx: ResolveContext,
        budget_ms: int,
        rng: RandomSource,
    ) -> ResolveResult:
        """Record the clipped budget and advance synthetic action metadata."""
        assert action.resolver == "travel"
        assert budget_ms == int(ctx.caps.offline_hours * 3_600_000)
        assert ctx.active.meta == {"step": 1}
        active = replace(
            ctx.active,
            meta={"step": 2},
            last_resolved_at=ctx.active.last_resolved_at + timedelta(milliseconds=10),
        )
        return ResolveResult(
            0,
            {},
            {},
            {},
            {},
            {},
            None,
            state=state,
            active=active,
            elapsed_ms=10,
            details={"step": 2},
        )


def test_registry_dispatch_and_clipped_budget() -> None:
    """Content resolver selection receives meta and a capped elapsed budget."""
    action = CONTENT.action("gathering.fake_sprigs").model_copy(
        update={"resolver": "travel"}
    )
    state = make_state()
    _, active, result = resolve(
        state,
        replace(make_active(), meta={"step": 1}),
        CONTENT.with_overrides(actions=(action,)),
        START + timedelta(days=2),
        random.Random(1),
        resolvers={"travel": StepResolver()},
    )
    assert active is not None and active.meta == {"step": 2}
    assert result.details["step"] == 2
    assert result.elapsed_ms == 10


def test_presence_helpers() -> None:
    """Home and residence follow the estate while presence follows the player."""
    state = replace(make_state(), current_realm_id="away", estate_realm_id="home")
    assert home_realm(state) == "home"
    assert is_resident(state, "home")
    assert not is_present(state, "home")
    assert is_present(state, "away")
    assert not is_resident(state, "away")


def test_cap_below_usage_keeps_items_and_records_overflow() -> None:
    """Leaving estate capacity behind retains holdings and discards new stacks."""
    content = replace(
        CONTENT, caps=CONTENT.caps.model_copy(update={"inventory_slots": 1})
    )
    form = content.estate_form("form.camp").model_copy(
        update={"cap_bonuses": (CapBonus(cap=CapType.INVENTORY_SLOTS, value=2),)}
    )
    content = replace(
        content, _forms_by_id=MappingProxyType({**content._forms_by_id, form.id: form})
    )
    state = replace(
        make_state(inventory={"item.mock_ore": 3, "item.fake_plank": 4}),
        current_realm_id="home",
        estate_realm_id="home",
    )
    assert resolve_caps(state, content).inventory_slots == 3
    away = replace(state, current_realm_id="away")
    assert resolve_caps(away, content).inventory_slots == 1
    new_state, active, result = resolve(
        away, make_active(), content, START + timedelta(seconds=3), random.Random(1)
    )
    assert new_state.inventory == state.inventory
    assert active is None
    assert result.stop_reason == StopReason.INVENTORY_FULL
    assert result.items_gained == {}
    assert result.overflowed_items["item.fake_sprig"] > 0


def test_visitor_loses_only_estate_sources() -> None:
    """Visitors retain G/R/C and normal rewards while losing E and facilities."""
    from app.content.schemas import Modifier, ModifierType
    from app.engine import OK, ErrorCode, can_start
    from app.engine.core import estate_active_tags, modifier_groups

    form = CONTENT.estate_form("form.camp").model_copy(
        update={
            "modifiers": (Modifier(type=ModifierType.XP_PCT, value=20),),
            "tags": ("facility.fake_upgrade",),
            "cap_bonuses": (CapBonus(cap=CapType.INVENTORY_SLOTS, value=2),),
        }
    )
    content = replace(
        CONTENT, _forms_by_id=MappingProxyType({**CONTENT._forms_by_id, form.id: form})
    )
    action = content.action("gathering.fake_sprigs")
    facility_action = action.model_copy(
        update={
            "requires": action.requires.model_copy(
                update={"facility": "facility.fake_upgrade"}
            )
        }
    )
    gated_content = content.with_overrides(actions=(facility_action,))
    home = replace(make_state(), current_realm_id="home", estate_realm_id="home")
    away = replace(home, current_realm_id="away")
    assert can_start(action.id, home, gated_content) == OK
    assert can_start(action.id, away, gated_content) == ErrorCode.MISSING_FACILITY
    assert estate_active_tags(away, content) == ()
    home_groups, away_groups = (
        modifier_groups(home, content),
        modifier_groups(away, content),
    )
    assert home_groups[1] and away_groups[1] == ()
    assert all(home_groups[i] == away_groups[i] for i in (0, 2, 3))
    assert resolve_caps(home, content).inventory_slots == (
        resolve_caps(away, content).inventory_slots + 2
    )
    neutral_form = form.model_copy(
        update={"modifiers": (), "tags": (), "cap_bonuses": ()}
    )
    neutral_content = replace(
        content,
        _forms_by_id=MappingProxyType({**content._forms_by_id, form.id: neutral_form}),
    )
    _, normal_active, normal_result = resolve(
        home,
        make_active(),
        neutral_content,
        START + timedelta(seconds=30),
        random.Random(6),
    )
    _, visitor_active, visitor_result = resolve(
        away, make_active(), content, START + timedelta(seconds=30), random.Random(6)
    )
    assert visitor_active == normal_active
    assert replace(visitor_result, state=None) == replace(normal_result, state=None)
