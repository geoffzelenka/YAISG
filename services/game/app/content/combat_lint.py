"""Deterministic expected-rate estimates for authored combat encounters."""

import math
from dataclasses import dataclass, replace
from types import MappingProxyType

from app.content.loader import ContentIndex
from app.content.schemas import Action, Combatant
from app.engine.combat import (
    COMBAT_SKILL_IDS,
    CombatStats,
    damage_on_hit,
    hit_chance,
    opponent_stats,
    player_stats,
)
from app.engine.core import CharacterState


@dataclass(frozen=True)
class CombatReport:
    """One stance's encounter duration and per-skill pool rates."""

    combatant_id: str
    action_id: str | None
    stance: str | None
    time_to_kill_ms: int | None
    encounter_ms: int | None
    xp_per_hour: dict[str, float]
    target_xp_per_hour: float | None
    warnings: tuple[str, ...]


def expected_attack(
    attacker: CombatStats, defender: CombatStats
) -> tuple[float, float]:
    """Average dealt and mitigated over integer rolls and the hit probability."""
    dealt = 0.0
    mitigated = 0.0
    chance = hit_chance(attacker, defender)
    for roll in range(1, attacker.max_hit + 1):
        hit = damage_on_hit(attacker, defender, roll)
        dealt += chance * hit.dealt
        mitigated += hit.mitigated + (1 - chance) * hit.dealt
    return dealt / attacker.max_hit, mitigated / attacker.max_hit


def _standard_player(
    action: Action, opponent: Combatant, content: ContentIndex
) -> CombatStats:
    """Use authored gear at unlock level, with no estate/realm or consumable bonuses."""
    node = content.development_nodes[0]
    form = content.estate_form(content.progression.basic_mobile_form)
    neutral = replace(
        content,
        _nodes_by_id=MappingProxyType(
            {node.id: node.model_copy(update={"modifiers": (), "inherent_tags": ()})}
        ),
        _forms_by_id=MappingProxyType(
            {form.id: form.model_copy(update={"modifiers": (), "tags": ()})}
        ),
    )
    gear: dict[str, str] = {
        slot: item_id
        for slot, item_id in content.progression.combat.standard_gear.items()
    }
    modifiers = tuple(
        modifier
        for item_id in gear.values()
        if (equip := content.item(item_id).equip) is not None
        for modifier in equip.modifiers
    )
    state = CharacterState(
        {},
        {skill: action.unlock_level for skill in COMBAT_SKILL_IDS},
        {},
        0,
        form.id,
        node.id,
        gear_modifiers=modifiers,
    )
    return player_stats(state, gear, opponent, neutral)


def _encounter_rates(
    action: Action, opponent: Combatant, content: ContentIndex
) -> tuple[CombatReport, ...]:
    """Size both streams over an estimated whole-cycle kill and respawn."""
    from app.content.lint import target_xp_per_hour

    player = _standard_player(action, opponent, content)
    enemy = opponent_stats(opponent, content)
    dealt, _ = expected_attack(player, enemy)
    fight_ms = math.ceil(opponent.max_hp / dealt) * player.cycle_ms if dealt else None
    duration = fight_ms + opponent.respawn_ms if fight_ms is not None else None
    incoming = fight_ms // enemy.cycle_ms if fight_ms is not None else 0
    taken, mitigated = expected_attack(enemy, player)
    raw_taken = taken * incoming * opponent.defense_xp_per_damage
    raw_mitigated = mitigated * incoming * opponent.defense_xp_per_damage
    raw = raw_taken + raw_mitigated
    scale = min(1.0, opponent.xp_pool_defense / raw) if raw else 0
    defense_share = content.progression.combat.taken_to_defense_pct / 100
    target = float(target_xp_per_hour(action.unlock_level, content.progression.lint.g))
    reports = []
    for name, stance in content.progression.stances.items():
        xp = {
            player.style: opponent.xp_pool_offense * stance.style,
            "accuracy": opponent.xp_pool_offense * stance.accuracy,
            "defense": (raw_mitigated + raw_taken * defense_share) * scale,
            "vigor": raw_taken * (1 - defense_share) * scale,
        }
        rates = {
            skill: value * 3_600_000 / duration if duration else 0.0
            for skill, value in xp.items()
        }
        warnings = tuple(
            skill
            for skill, rate in rates.items()
            if abs(rate / target - 1) * 100 > content.progression.lint.tolerance_pct
        )
        if duration is None:
            warnings += ("UNDEFEATABLE",)
        reports.append(
            CombatReport(
                opponent.id,
                action.id,
                name,
                fight_ms,
                duration,
                rates,
                target,
                warnings,
            )
        )
    return tuple(reports)


def lint_combat(content: ContentIndex) -> tuple[CombatReport, ...]:
    """Report every combatant, each offered action and each authored stance.

    Kill time is HP divided by mean dealt damage, rounded up to player cycles.
    Incoming XP uses whole opponent attacks during that time, bounded by the
    defensive pool. This estimate excludes survival, buffs and consumable use;
    it does not simulate the encounter resolver. Unreferenced combatants warn
    because their unlock level cannot be determined.
    """
    reports = []
    actions = tuple(
        action
        for skill in content.skills
        for action in skill.actions
        if action.resolver == "combat"
    )
    for opponent in content.combatants:
        offered = tuple(
            action for action in actions if action.combatant_id == opponent.id
        )
        if not offered:
            reports.append(
                CombatReport(
                    opponent.id, None, None, None, None, {}, None, ("NO_COMBAT_ACTION",)
                )
            )
        for action in offered:
            reports.extend(_encounter_rates(action, opponent, content))
    return tuple(reports)
