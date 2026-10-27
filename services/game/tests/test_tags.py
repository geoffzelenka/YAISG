"""Tag activation and complete action requirement behavior."""

import random
from dataclasses import replace
from datetime import timedelta
from types import MappingProxyType
from typing import Any, Literal

import pytest
from pydantic import ValidationError
from test_engine import START, content, make_active, make_state

from app.content.loader import ContentIndex
from app.content.schemas import (
    CapType,
    DecayStage,
    Modifier,
    ModifierType,
    Requirements,
    Tag,
    TagEffects,
)
from app.engine import ErrorCode, StopReason, can_start, resolve, resolve_caps
from app.engine.core import estate_active_tags, modifier_groups, unmet_requirements
from app.engine.tags import TagHolder, active_tags

__all__ = ["content"]


def test_node_listed_gathering_and_unlisted(content: ContentIndex) -> None:
    """Node offerings gate gathering independently of tag requirements."""
    state = make_state()
    action = content.action("gathering.fake_sprigs")
    assert not unmet_requirements(action, state, content)
    content = replace(
        content,
        _nodes_by_id=MappingProxyType(
            {
                **content._nodes_by_id,
                state.realm_node_id: content.development_node(
                    state.realm_node_id
                ).model_copy(update={"actions": ()}),
            }
        ),
    )
    assert unmet_requirements(action, state, content) == (ErrorCode.NOT_OFFERED_HERE,)


@pytest.mark.parametrize("stage", list(DecayStage))
def test_stage_effects_preserve_access(stage: DecayStage) -> None:
    """D11 applies identically to all stages at or beyond Faltering."""
    kinds: tuple[Literal["facility", "bonus", "malus", "access"], ...] = (
        "facility",
        "bonus",
        "malus",
        "access",
    )
    tags = tuple(Tag(id=kind, name=kind, kind=kind) for kind in kinds)
    values = {
        tag.id: factor for tag, factor in active_tags(TagHolder(tags, 0.5), stage)
    }
    if stage in (DecayStage.FED, DecayStage.STRAINED):
        assert values == {kind: 1 for kind in ("facility", "bonus", "malus", "access")}
    else:
        assert values == {"bonus": 0.5, "malus": 0.5, "access": 1}


def test_facility_realm_owner_and_elsewhere(content: ContentIndex) -> None:
    """Realm facilities serve all; estate facilities serve their present owner."""
    action = content.action("refining.fake_plank").model_copy(
        update={"requires": Requirements(facility="facility.fake_node")}
    )
    state = make_state(inventory={"item.fake_sprig": 2})
    assert not unmet_requirements(action, state, content)
    assert ErrorCode.MISSING_FACILITY in unmet_requirements(
        action, replace(state, realm_stage=DecayStage.FALTERING), content
    )
    action = action.model_copy(
        update={"requires": Requirements(facility="facility.fake_upgrade")}
    )
    state = replace(state, installed_upgrades=("upgrade.painted_sign",))
    assert not unmet_requirements(action, state, content)
    assert ErrorCode.MISSING_FACILITY in unmet_requirements(
        action, replace(state, estate_realm_id="elsewhere"), content
    )


def test_inert_upgrade_contributes_nothing(content: ContentIndex) -> None:
    """Missing any required realm tag disables every upgrade contribution."""
    upgrade = content.upgrade("upgrade.painted_sign").model_copy(
        update={"requires_realm_tags": ("verdant", "ashen")}
    )
    content = content.with_overrides(upgrades=(upgrade,))
    state = make_state(upgrades=(upgrade.id,))
    assert estate_active_tags(state, content) == ()
    assert modifier_groups(state, content)[1] == ()


def test_each_requirement_code_and_shared_start(content: ContentIndex) -> None:
    """Each gate is independently reported and cleared by satisfying its condition."""
    action = content.action("gathering.fake_sprigs")
    state = make_state()
    cases: list[tuple[dict[str, Any], ErrorCode]] = [
        ({"unlock_level": 2}, ErrorCode.INSUFFICIENT_LEVEL),
        ({"requires": Requirements(facility="absent")}, ErrorCode.MISSING_FACILITY),
        (
            {"requires": Requirements(realm_tags=("verdant", "ashen"))},
            ErrorCode.MISSING_REALM_TAG,
        ),
        (
            {"requires": Requirements(skill_levels={"refining": 2})},
            ErrorCode.MISSING_SKILL_LEVEL,
        ),
        ({"requires": Requirements(tool_class="fake_plant")}, ErrorCode.MISSING_TOOL),
        (
            {"inputs": content.action("refining.fake_plank").inputs},
            ErrorCode.MISSING_INPUTS,
        ),
    ]
    for fields, code in cases:
        changed = action.model_copy(update=fields)
        altered = content.with_overrides(actions=(changed,))
        assert unmet_requirements(changed, state, altered) == (code,)
        assert can_start(action.id, state, altered) == code
    assert not unmet_requirements(action, state, content)


def test_requirement_lost_grants_cycles_through_detecting_resolve(
    content: ContentIndex,
) -> None:
    """Losing a realm tag ends the action after granting the accrued cycles."""
    state = make_state()
    action = content.action("gathering.fake_sprigs").model_copy(
        update={"requires": Requirements(realm_tags=("access.fake",))}
    )
    content = content.with_overrides(actions=(action,))
    state = replace(state, realm_stack_tags=("access.fake",))
    state, active, first = resolve(
        state, make_active(), content, START + timedelta(seconds=3), random.Random(1)
    )
    assert first.cycles_completed == 1 and active is not None
    _, remaining, result = resolve(
        replace(state, realm_stack_tags=()),
        active,
        content,
        START + timedelta(seconds=6),
        random.Random(2),
    )
    assert result.cycles_completed == 1
    assert result.stop_reason == StopReason.REQUIREMENT_LOST
    assert remaining is None


@pytest.mark.parametrize("offset_ms", [0, -1])
def test_zero_cycle_requirement_loss(content: ContentIndex, offset_ms: int) -> None:
    """Loss is detected even before another complete cycle is available."""
    state = replace(make_state(), realm_node_id="node.ashen_t1")
    _, active, result = resolve(
        state,
        make_active(),
        content,
        START + timedelta(milliseconds=offset_ms),
        random.Random(1),
    )
    assert result.cycles_completed == 0
    assert active is None
    assert result.stop_reason == StopReason.REQUIREMENT_LOST


def test_tag_bonus_group_and_cap(content: ContentIndex) -> None:
    """Realm and estate tag modifiers stay in R/E; caps are additive amounts."""
    bonus = Tag(
        id="bonus.fake",
        name="Fake",
        kind="bonus",
        modifiers=(Modifier(type=ModifierType.XP_PCT, value=20),),
        cap_bonuses={CapType.INVENTORY_SLOTS: 7},
    )
    content = replace(
        content, tags=tuple(bonus if t.id == bonus.id else t for t in content.tags)
    )
    state = replace(make_state(), realm_stack_tags=(bonus.id,))
    assert modifier_groups(state, content)[2][-1].value == 20
    assert (
        modifier_groups(replace(state, realm_stage=DecayStage.FALTERING), content)[2][
            -1
        ].value
        == 10
    )
    assert (
        resolve_caps(state, content).inventory_slots == content.caps.inventory_slots + 7
    )


@pytest.mark.parametrize(
    "effects",
    [
        {"unknown": True},
        {"market_access": 1},
        {"caravan_access": "yes"},
        {"mint": {"value_per_day": -1}},
        {"edge_loss_reduction_pct": 101},
        {"reserve_days_delta": "bad"},
    ],
)
def test_tag_effect_fields_are_strict(effects: dict[str, object]) -> None:
    """Malformed future effect data fails now, before consumers are introduced."""
    with pytest.raises(ValidationError):
        TagEffects.model_validate(effects)


def test_form_tags_are_inert_scaled_and_presence_scoped(content: ContentIndex) -> None:
    """Form emissions feed E and caps only when the form is active and present."""
    bonus = Tag(
        id="bonus.fake",
        name="Fake",
        kind="bonus",
        modifiers=(Modifier(type=ModifierType.XP_PCT, value=20),),
        cap_bonuses={CapType.INVENTORY_SLOTS: 7},
    )
    form = content.estate_form("form.camp").model_copy(
        update={"tags": (bonus.id,), "requires_realm_tags": ("verdant",)}
    )
    content = replace(
        content,
        tags=tuple(bonus if t.id == bonus.id else t for t in content.tags),
        _forms_by_id=MappingProxyType({**content._forms_by_id, form.id: form}),
    )
    state = make_state()
    assert modifier_groups(state, content)[1][-1].value == 20
    assert (
        resolve_caps(state, content).inventory_slots == content.caps.inventory_slots + 7
    )
    assert (
        modifier_groups(replace(state, estate_stage=DecayStage.FALTERING), content)[1][
            -1
        ].value
        == 10
    )
    for absent in (
        replace(state, estate_realm_id="away"),
        replace(state, realm_node_id="node.ashen_t1"),
    ):
        assert estate_active_tags(absent, content) == ()
        assert modifier_groups(absent, content)[1] == ()
        assert (
            resolve_caps(absent, content).inventory_slots
            == content.caps.inventory_slots
        )


def test_lint_includes_emitted_tag_modifiers(content: ContentIndex) -> None:
    """Authoring bounds include tag bonuses using runtime group semantics."""
    from app.content.lint import stack_bound

    bonus = Tag(
        id="bonus.fake",
        name="Fake",
        kind="bonus",
        modifiers=(Modifier(type=ModifierType.XP_PCT, value=100),),
    )
    nodes = tuple(
        n.model_copy(update={"inherent_tags": (bonus.id,)})
        for n in content.development_nodes
    )
    changed = replace(
        content,
        tags=tuple(bonus if t.id == bonus.id else t for t in content.tags),
        development_nodes=nodes,
    )
    skill = content.skill("gathering")
    assert stack_bound(skill, changed) > stack_bound(skill, content) * 1.9


def test_lint_accounts_for_weakened_malus(content: ContentIndex) -> None:
    """Weakening a malus can make a stronger stack than the Fed snapshot."""
    from app.content.lint import stack_bound

    tag = Tag(
        id="bonus.fake",
        name="Fake malus",
        kind="malus",
        modifiers=(Modifier(type=ModifierType.XP_PCT, value=-100),),
    )
    node = content.development_nodes[0].model_copy(
        update={
            "inherent_tags": (tag.id,),
            "modifiers": (Modifier(type=ModifierType.XP_PCT, value=100),),
        }
    )
    form = content.estate_forms[0].model_copy(update={"tags": (), "modifiers": ()})
    content = replace(
        content,
        tags=tuple(tag if t.id == tag.id else t for t in content.tags),
        development_nodes=(node,),
        estate_forms=(form,),
        upgrades=(),
    )
    assert stack_bound(content.skill("gathering"), content) == 1.5
