"""Pure exploration rolls and private key action projections."""

import uuid
from dataclasses import replace
from datetime import datetime, timedelta

from app.content.loader import ContentIndex
from app.content.schemas import (
    Action,
    DiscoveryTemplate,
    ExplorationAction,
    ExplorationTierBenefit,
    Modifier,
    Requirements,
)
from app.engine.core import (
    BeltStack,
    CharacterState,
    InstanceState,
    RandomSource,
    realm_active_tags,
)
from app.engine.levels import tier_for_level


def tier_benefit(
    state: CharacterState, content: ContentIndex
) -> ExplorationTierBenefit:
    """Read the absolute Exploration tier row, also used for group P speed."""
    tier = tier_for_level(
        state.skill_levels.get("exploration", 1), content.progression.tier_thresholds
    )
    benefit = content.progression.tier_benefits["exploration"][tier - 1]
    assert isinstance(benefit, ExplorationTierBenefit)
    return benefit


def use_exploration_belt(
    state: CharacterState, at: datetime, content: ContentIndex
) -> tuple[dict[int, BeltStack], dict[str, datetime], dict[str, int]]:
    """Activate at most one missing timed buff in belt position order."""
    belt, buffs = dict(state.belt), dict(state.buff_expiries)
    for position, stack in sorted(belt.items()):
        consumable = content.item(stack.item_id).consumable
        if (
            consumable is None
            or consumable.buff is None
            or stack.trigger != {"buff_missing": True}
        ):
            continue
        if buffs.get(stack.item_id, at) > at:
            continue
        buffs[stack.item_id] = at + timedelta(milliseconds=consumable.buff.duration_ms)
        if stack.quantity == 1:
            del belt[position]
        else:
            belt[position] = replace(stack, quantity=stack.quantity - 1)
        return belt, buffs, {stack.item_id: 1}
    return belt, buffs, {}


def template_action(
    template: DiscoveryTemplate, content: ContentIndex, rng: RandomSource
) -> Action:
    """Roll ranged values independently once for this key's private action."""
    if template.gather is not None:
        gather = template.gather
        outputs = []
        for output in gather.outputs:
            quantity = rng.randint(output.quantity_min, output.quantity_max)
            outputs.append(
                output.model_copy(
                    update={"quantity_min": quantity, "quantity_max": quantity}
                )
            )
        return Action(
            id=template.id,
            name=template.name,
            skill_id=gather.skill_id,
            tier=gather.tier,
            unlock_level=gather.unlock_level,
            base_cycle_ms=gather.base_cycle_ms,
            outputs=tuple(outputs),
            xp=gather.xp,
            requires=Requirements(tool_class=gather.tool_class),
            resolver="uniform",
        )
    assert template.combat is not None
    opponent = content.combatant(template.combat.combatant_id)
    return Action(
        id=template.id,
        name=template.name,
        skill_id="melee",
        tier=opponent.tier,
        unlock_level=1,
        base_cycle_ms=opponent.attack_interval_ms,
        xp=1,
        resolver="combat",
        combatant_id=opponent.id,
        location=template.name,
    )


def _gating_shift(
    template: DiscoveryTemplate,
    action: Action,
    state: CharacterState,
    content: ContentIndex,
) -> float:
    skills = set(action.requires.skill_levels)
    if template.gather is not None:
        skills.add(template.gather.skill_id)
    shift = 0.0
    for skill in sorted(skills):
        tier = tier_for_level(
            state.skill_levels.get(skill, 1), content.progression.tier_thresholds
        )
        benefit = content.progression.tier_benefits["exploration"][tier - 1]
        assert isinstance(benefit, ExplorationTierBenefit)
        shift += benefit.rarity_weight_shift
    return shift


def discover(
    state: CharacterState,
    action: Action,
    content: ContentIndex,
    at: datetime,
    rng: RandomSource,
    inventory_limit: int,
) -> tuple[list[InstanceState], int, int]:
    """Roll a discovery, counting overflow separately from retained instances."""
    if not isinstance(action, ExplorationAction):
        return [], 0, 0
    chance = action.discovery_chance
    shift = tier_benefit(state, content).rarity_weight_shift
    for effect in action.consumable_effects:
        if state.buff_expiries.get(effect.item_id, at) <= at:
            continue
        chance *= 1 + (effect.chance_pct or 0) / 100
        shift += effect.weight_shift or 0
    if rng.random() >= min(1, chance):
        return [], 0, 0
    tags = {tag.id for tag, _ in realm_active_tags(state, content)}
    templates = {template.id: template for template in content.exploration.templates}
    candidates = []
    for entry in action.table:
        template = templates[entry.template_id]
        if set(template.requires_realm_tags) <= tags:
            weight = entry.weight * (
                1 + shift + _gating_shift(template, action, state, content)
            ) ** (template.rarity - 1)
            candidates.append((template, weight))
    if not candidates:
        return [], 0, 0
    roll = rng.random() * sum(weight for _, weight in candidates)
    template = candidates[-1][0]
    for candidate, weight in candidates:
        roll -= weight
        if roll < 0:
            template = candidate
            break
    count = (
        rng.randint(template.keys.min, template.keys.max)
        + tier_benefit(state, content).keys_per_discovery_bonus
    )
    found: list[InstanceState] = []
    lost = 0
    for _ in range(count):
        uses = rng.randint(template.uses.min, template.uses.max)
        inline = template_action(template, content, rng)
        if len(state.inventory) + len(state.instances) + len(found) >= inventory_limit:
            lost += 1
            continue
        found.append(
            InstanceState(
                id=str(uuid.UUID(int=rng.randint(0, 2**128 - 1), version=4)),
                template_id=template.id,
                realm_id=state.current_realm_id,
                payload={
                    "action": inline.model_dump(mode="json"),
                    "name": template.name,
                    "flavour": template.flavour,
                    "rarity": template.rarity,
                    "kind": template.kind,
                },
                uses_total=uses,
                uses_remaining=uses,
                state="active",
                created_at=at,
            )
        )
    return found, lost, 1


def exploration_buffs(
    buffs: dict[str, datetime], content: ContentIndex
) -> tuple[tuple[datetime, tuple[Modifier, ...]], ...]:
    """Project identified active and historical timed effects for uniform segments."""
    values = []
    for identifier, expiry in buffs.items():
        consumable = content.item(identifier).consumable
        assert consumable is not None and consumable.buff is not None
        values.append((expiry, consumable.buff.modifiers))
    return tuple(values)
