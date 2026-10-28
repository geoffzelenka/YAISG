"""Pure combat stat construction and D12 attack arithmetic."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from app.content.loader import ContentIndex
from app.content.schemas import Combatant, CombatProgression, ModifierType, Weapon
from app.engine.core import CharacterState, scoped_bonus_total
from app.engine.health import maximum_hp
from app.engine.levels import tier_for_level

COMBAT_SKILL_IDS = ("melee", "ranged", "magic", "accuracy", "defense", "vigor")


class AttackRng(Protocol):
    """The random operations needed by one attack."""

    def random(self) -> float:
        """Return a uniform probability."""
        ...

    def randint(self, a: int, b: int) -> int:
        """Return an inclusive uniform integer."""
        ...


@dataclass(frozen=True)
class CombatStats:
    """Resolved values for either side of an encounter."""

    style: str
    damage_type: str
    accuracy: float
    max_hit: int
    defense: float
    armour: float
    max_hp: float
    cycle_ms: int
    settings: CombatProgression
    weak_to: tuple[str, ...] = ()
    resistant_to: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttackResult:
    """Damage partition, including damage avoided by a miss."""

    dealt: int
    mitigated: int


def eff(skill_id: str, level: int, content: ContentIndex) -> float:
    """Apply the uniform tier multiplier to the five non-Vigor combat skills."""
    if skill_id == "vigor":
        return float(level)
    if skill_id not in COMBAT_SKILL_IDS:
        raise ValueError(f"not a combat skill: {skill_id}")
    tier = tier_for_level(level, content.progression.tier_thresholds)
    return level * (1 + content.progression.combat.tier_multiplier * (tier - 1))


def player_stats(
    state: CharacterState,
    equipment: Mapping[str, str],
    combatant: Combatant,
    content: ContentIndex,
) -> CombatStats:
    """Resolve equipped weapon style, armour and all five bonus source groups."""
    settings = content.progression.combat
    weapon = equipped_weapon(equipment, content)
    equipped = [
        content.item(item_id).equip
        for slot, item_id in equipment.items()
        if slot != "utility"
    ]
    tier = tier_for_level(
        state.skill_levels.get(weapon.style, 1), content.progression.tier_thresholds
    )
    distance = max(0, tier - combatant.tier)

    def factor(kind: ModifierType) -> float:
        percent = (
            content.progression.combat_effectiveness[distance]
            if kind
            in {
                ModifierType.COMBAT_ACCURACY_PCT,
                ModifierType.COMBAT_POWER_PCT,
                ModifierType.COMBAT_DEFENSE_PCT,
            }
            else 0
        )
        return scoped_bonus_total(kind, weapon.style, "combat", state, content, percent)

    armour = sum(
        e.armour.armour for e in equipped if e is not None and e.armour is not None
    )
    hp = sum(
        e.armour.max_hp for e in equipped if e is not None and e.armour is not None
    )
    accuracy = eff("accuracy", state.skill_levels.get("accuracy", 1), content)
    power = eff(weapon.style, state.skill_levels.get(weapon.style, 1), content)
    defense = eff("defense", state.skill_levels.get("defense", 1), content)
    return CombatStats(
        weapon.style,
        weapon.damage_type,
        (accuracy + weapon.accuracy) * factor(ModifierType.COMBAT_ACCURACY_PCT),
        max(
            1,
            math.floor(
                (settings.base_hit + power * settings.hit_per_level + weapon.power)
                * factor(ModifierType.COMBAT_POWER_PCT)
            ),
        ),
        defense * factor(ModifierType.COMBAT_DEFENSE_PCT),
        armour * factor(ModifierType.COMBAT_ARMOUR_PCT),
        maximum_hp(state, hp, content),
        max(
            content.progression.min_cycle_ms,
            math.floor(
                weapon.attack_interval_ms / factor(ModifierType.CYCLE_SPEED_PCT)
            ),
        ),
        settings,
    )


def equipped_weapon(equipment: Mapping[str, str], content: ContentIndex) -> Weapon:
    """Use the right-hand weapon or the authored unarmed fallback."""
    right = (
        content.item(equipment["right_hand"]).equip
        if "right_hand" in equipment
        else None
    )
    if right is not None and right.weapon is not None:
        return right.weapon
    return content.progression.combat.unarmed


def opponent_stats(opponent: Combatant, content: ContentIndex) -> CombatStats:
    """Adapt authored opponent values to the shared attack interface."""
    return CombatStats(
        opponent.style,
        opponent.style,
        opponent.accuracy,
        opponent.power,
        opponent.defense,
        opponent.armour,
        opponent.max_hp,
        opponent.attack_interval_ms,
        content.progression.combat,
        opponent.weak_to,
        opponent.resistant_to,
    )


def hit_chance(attacker: CombatStats, defender: CombatStats) -> float:
    """Clamp the accuracy contest, including the zero/zero case."""
    total = attacker.accuracy + defender.defense
    ratio = attacker.accuracy / total if total else 0.5
    return min(
        attacker.settings.max_hit_chance, max(attacker.settings.min_hit_chance, ratio)
    )


def attack(
    attacker: CombatStats, defender: CombatStats, rng: AttackRng
) -> AttackResult:
    """Roll damage even on a miss; partition it into dealt and mitigated."""
    lands = rng.random() < hit_chance(attacker, defender)
    rolled = rng.randint(1, attacker.max_hit)
    damage = damage_on_hit(attacker, defender, rolled)
    if not lands:
        return AttackResult(0, damage.dealt + damage.mitigated)
    return damage


def damage_on_hit(
    attacker: CombatStats, defender: CombatStats, roll: int
) -> AttackResult:
    """Apply weakness/resistance and armour floors to an inclusive damage roll."""
    multiplier = 1.0
    if attacker.damage_type in defender.weak_to:
        multiplier *= attacker.settings.weakness_multiplier
    if attacker.damage_type in defender.resistant_to:
        multiplier *= attacker.settings.resistance_multiplier
    rolled = math.floor(roll * multiplier)
    blocked = math.floor(
        rolled * defender.armour / (defender.armour + attacker.settings.armour_k)
    )
    return AttackResult(rolled - blocked, blocked)
