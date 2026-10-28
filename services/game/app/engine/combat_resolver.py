"""Pure cycle-by-cycle combat with exact health and XP carries."""

import random
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from fractions import Fraction

from app.content.schemas import Action
from app.engine.combat import CombatStats, attack, opponent_stats, player_stats
from app.engine.core import (
    CharacterState,
    RandomSource,
    ResolveContext,
    ResolveResult,
    StopReason,
)
from app.engine.levels import level_for_xp, tier_for_level


def _fraction(value: float | int) -> Fraction:
    return Fraction(str(value))


def _pack(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _unpack(value: list[int]) -> Fraction:
    return Fraction(*value)


@dataclass(frozen=True)
class CycleParameters:
    """Combat values valid until a level change or the next buff expiry."""

    player: CombatStats
    maximum_hp: Fraction
    regen_per_ms: Fraction
    cycle_regen: Fraction
    taper: Fraction
    style_xp_factor: Fraction
    accuracy_xp_factor: Fraction
    expires_at: datetime | None


class CombatSimulation:
    """Mutable local working set, never shared between resolution calls."""

    def __init__(
        self,
        state: CharacterState,
        action: Action,
        ctx: ResolveContext,
        rng: RandomSource,
    ) -> None:
        self.state = state
        self.action = action
        self.ctx = ctx
        self.content = ctx.content
        assert action.combatant_id is not None
        self.opponent = self.content.combatant(action.combatant_id)
        self.enemy = opponent_stats(self.opponent, self.content)
        self.meta = dict(ctx.active.meta)
        self.at = ctx.active.last_resolved_at
        self.elapsed = 0
        self.cycles = 0
        self.reason: StopReason | None = None
        self.xp = dict(state.skills_xp)
        self.levels = dict(state.skill_levels)
        self.inventory = dict(state.inventory)
        self.instances = list(state.instances)
        self.key = next(
            (key for key in self.instances if key.id == self.meta.get("key_id")), None
        )
        self.belt = dict(state.belt)
        # CharacterBuff rows, loaded into state, are runtime truth.
        # meta["buffs"] is summary-only and must not restore stale expiries.
        self.buffs = dict(state.buff_expiries)
        self.utility = state.utility_quantity
        self._parameters: CycleParameters | None = None
        self._offense_pool = _fraction(self.opponent.xp_pool_offense)
        self._defense_pool = _fraction(self.opponent.xp_pool_defense)
        self._offense_per_dealt = self._offense_pool / self.opponent.max_hp
        self._defense_rate = _fraction(self.opponent.defense_xp_per_damage)
        self._regen_fraction_per_ms = (
            _fraction(self.content.progression.combat.regen_per_min) / 60000
        )
        self._vigor_share = (
            1 - _fraction(self.content.progression.combat.taken_to_defense_pct) / 100
        )
        stance = self.content.progression.stances[
            state.stance or self.content.progression.default_stance
        ]
        self._style_share = _fraction(stance.style)
        self._accuracy_share = _fraction(stance.accuracy)
        self.consumed: defaultdict[str, int] = defaultdict(int)
        self.gained: defaultdict[str, int] = defaultdict(int)
        self.overflow: defaultdict[str, int] = defaultdict(int)
        self.level_ups: defaultdict[str, list[int]] = defaultdict(list)
        self.summary: dict[str, int] = dict.fromkeys(
            ("kills", "defeats", "damage_dealt", "damage_taken"), 0
        )
        self.damage_taken_carry = _unpack(self.meta.get("damage_taken_carry", [0, 1]))
        self.carries = {
            skill: _unpack(value)
            for skill, value in self.meta.get("xp_carries", {}).items()
        }
        self.hp = (
            _unpack(self.meta["hp_exact"])
            if "hp_exact" in self.meta
            else _fraction(
                state.hp if state.hp is not None else self.parameters().player.max_hp
            )
        )
        self.rng = random.Random(0)
        if "rng_state" in self.meta:
            version, values, gaussian = self.meta["rng_state"]
            self.rng.setstate((version, tuple(values), gaussian))
        else:
            self.rng.seed(rng.randint(0, 2**256 - 1))
        if "opponent_hp" not in self.meta:
            self.spawn()
        self.offense = _unpack(self.meta["offense"])
        self.defense = _unpack(self.meta["defense"])

    def spawn(self) -> None:
        """Refill pools only when a new encounter begins."""
        if self.key is not None:
            if self.key.uses_remaining == 0:
                self.reason = StopReason.KEY_DEPLETED
                return
            updated = replace(
                self.key,
                uses_remaining=self.key.uses_remaining - 1,
                bound_at=self.key.bound_at or self.at,
            )
            if not updated.uses_remaining:
                updated = replace(
                    updated, state="invalid" if updated.invalidated_at else "depleted"
                )
            self.instances[self.instances.index(self.key)] = updated
            self.key = updated
        self.meta.update(
            opponent_hp=self.opponent.max_hp,
            offense=_pack(self._offense_pool),
            defense=_pack(self._defense_pool),
            attack_carry_ms=0,
            respawn_remaining_ms=0,
        )

    def current_state(self) -> CharacterState:
        """Materialize the stats input at this historical cycle boundary."""
        modifiers = tuple(
            modifier
            for expiry, values in self.state.timed_buffs
            if expiry > self.at
            for modifier in values
        )
        # Database buffs are identified so belt activation can replace an expiry.
        if self.buffs:
            modifiers = tuple(
                modifier
                for item, expiry in self.buffs.items()
                if expiry > self.at
                for modifier in self.content.item(item).consumable.buff.modifiers  # type: ignore[union-attr]
            )
        return replace(
            self.state,
            skills_xp=self.xp,
            skill_levels=self.levels,
            consumable_modifiers=modifiers,
        )

    def parameters(self) -> CycleParameters:
        """Reuse stats and rational rates until a relevant input changes."""
        cached = self._parameters
        if cached is not None and (
            cached.expires_at is None or self.at < cached.expires_at
        ):
            return cached
        player = player_stats(
            self.current_state(), self.state.equipment, self.opponent, self.content
        )
        maximum = _fraction(player.max_hp)
        regen_per_ms = maximum * self._regen_fraction_per_ms
        tier = tier_for_level(
            self.levels.get(player.style, 1), self.content.progression.tier_thresholds
        )
        taper = _fraction(
            self.content.progression.taper["combat"][max(0, tier - self.opponent.tier)]
        )
        expiries = (
            self.buffs.values()
            if self.buffs
            else (expiry for expiry, _ in self.state.timed_buffs)
        )
        self._parameters = CycleParameters(
            player=player,
            maximum_hp=maximum,
            regen_per_ms=regen_per_ms,
            cycle_regen=regen_per_ms * player.cycle_ms,
            taper=taper,
            style_xp_factor=taper * self._style_share,
            accuracy_xp_factor=taper * self._accuracy_share,
            expires_at=min((end for end in expiries if end > self.at), default=None),
        )
        return self._parameters

    def advance(self, duration: int) -> None:
        """Spend simulation time without reading a clock."""
        self.at += timedelta(milliseconds=duration)
        self.elapsed += duration

    def regenerate(self, duration: int, values: CycleParameters) -> None:
        """Apply cached healing, carrying every fractional HP unit explicitly."""
        healing = (
            values.cycle_regen
            if duration == values.player.cycle_ms
            else values.regen_per_ms * duration
        )
        self.hp = min(values.maximum_hp, self.hp + healing)

    def award(self, skill: str, amount: Fraction) -> None:
        """Persist fractional XP across cycles and encounters, crediting integers."""
        if not amount:
            return
        amount += self.carries.get(skill, 0)
        whole = amount.numerator // amount.denominator
        self.carries[skill] = amount - whole
        if not whole:
            return
        previous = self.levels.get(skill, 1)
        self.xp[skill] = self.xp.get(skill, 0) + whole
        level = level_for_xp(self.xp[skill], self.content.xp_curve.levels)
        self.levels[skill] = level
        if level != previous:
            self._parameters = None
        self.level_ups[skill].extend(range(previous + 1, level + 1))

    def use_utility(self, style: str) -> bool:
        """Consume matching utility before any attack; ranged requires it."""
        item = self.state.equipment.get("utility")
        consumable = self.content.item(item).consumable if item else None
        if self.utility and consumable and consumable.utility_for == style:
            assert item is not None
            self.utility -= 1
            self.consumed[item] += 1
            return True
        if style == "ranged":
            self.reason = StopReason.OUT_OF_AMMO
            return False
        return True

    def use_belt(self, maximum: float) -> None:
        """Evaluate slots after regeneration, consuming at most one."""
        for slot, stack in sorted(self.belt.items()):
            consumable = self.content.item(stack.item_id).consumable
            assert consumable is not None
            if consumable.heal is not None:
                threshold = _fraction(stack.trigger["hp_below_pct"])
                triggered = self.hp * 100 < _fraction(maximum) * threshold
            else:
                triggered = self.buffs.get(stack.item_id, self.at) <= self.at
            if not triggered:
                continue
            self.consumed[stack.item_id] += 1
            if stack.quantity == 1:
                del self.belt[slot]
            else:
                self.belt[slot] = replace(stack, quantity=stack.quantity - 1)
            if consumable.heal is not None:
                self.hp = min(_fraction(maximum), self.hp + _fraction(consumable.heal))
            else:
                assert consumable.buff is not None
                self.buffs[stack.item_id] = self.at + timedelta(
                    milliseconds=consumable.buff.duration_ms
                )
                self._parameters = None
            break

    def loot(self) -> None:
        """Roll full drops and apply the standard distinct-stack overflow rule."""
        for drop in self.opponent.drops:
            if self.rng.random() >= drop.chance:
                continue
            quantity = self.rng.randint(drop.quantity_min, drop.quantity_max)
            current = self.inventory.get(drop.item_id, 0)
            has_slot = (
                current > 0
                or len(self.inventory) + len(self.instances)
                < self.ctx.caps.inventory_slots
            )
            granted = (
                min(
                    quantity,
                    max(0, self.content.item(drop.item_id).stack_limit - current),
                )
                if has_slot
                else 0
            )
            if granted:
                self.inventory[drop.item_id] = current + granted
                self.gained[drop.item_id] += granted
            if granted < quantity:
                self.overflow[drop.item_id] += quantity - granted
                self.reason = StopReason.INVENTORY_FULL

    def award_offense(self, dealt: int, values: CycleParameters) -> None:
        """Drain raw offense before tapering and splitting the credited XP."""
        if not self.offense:
            return
        raw = min(self.offense, dealt * self._offense_per_dealt)
        self.offense -= raw
        self.award(values.player.style, raw * values.style_xp_factor)
        self.award("accuracy", raw * values.accuracy_xp_factor)

    def award_defense(self, taken: Fraction, mitigated: int) -> None:
        """Split the clipped stream in proportion to taken and mitigated damage."""
        if not self.defense:
            return
        damage = taken + mitigated
        paid = min(self.defense, damage * self._defense_rate)
        self.defense -= paid
        vigor = paid * taken / damage * self._vigor_share if damage else Fraction()
        self.award("vigor", vigor)
        self.award("defense", paid - vigor)

    def cycle(self, values: CycleParameters) -> None:
        """Apply §10.5 steps 1–8 literally, including retaliation on a kill."""
        player = values.player
        duration = player.cycle_ms
        if not self.use_utility(player.style):
            return
        # Utility content currently names purpose only; no bonus is invented.
        hit = attack(player, self.enemy, self.rng)
        dealt = min(hit.dealt, self.meta["opponent_hp"])
        self.meta["opponent_hp"] -= dealt
        self.meta["attack_carry_ms"] += duration
        taken = Fraction()
        mitigated = 0
        while self.meta["attack_carry_ms"] >= self.opponent.attack_interval_ms:
            self.meta["attack_carry_ms"] -= self.opponent.attack_interval_ms
            retaliation = attack(self.enemy, player, self.rng)
            damage = min(self.hp, Fraction(retaliation.dealt))
            self.hp -= damage
            taken += damage
            mitigated += retaliation.mitigated
        self.award_offense(dealt, values)
        self.award_defense(taken, mitigated)
        self.regenerate(duration, values)
        self.advance(duration)
        self.use_belt(player.max_hp)
        self.cycles += 1
        self.summary["damage_dealt"] += dealt
        # Keep clipped fractional HP in the summary carry as well as in XP.
        reported = taken + self.damage_taken_carry
        whole = reported.numerator // reported.denominator
        self.summary["damage_taken"] += whole
        self.damage_taken_carry = reported - whole
        if self.meta["opponent_hp"] == 0:
            self.summary["kills"] += 1
            self.loot()
            self.offense = self.defense = Fraction()
            self.meta["respawn_remaining_ms"] = self.opponent.respawn_ms
            if self.key is not None and self.key.uses_remaining == 0:
                self.reason = self.reason or StopReason.KEY_DEPLETED
        if self.hp == 0:
            self.summary["defeats"] += 1
            self.reason = StopReason.DEFEATED

    def run(self, budget: int) -> ResolveResult:
        """Spend waits and whole cycles, stopping at the authored hard ceiling."""
        while self.elapsed < budget and self.reason is None:
            wait = self.meta["respawn_remaining_ms"]
            if wait:
                duration = min(wait, budget - self.elapsed)
                # Split waits at expiry so online polling cannot change healing.
                values = self.parameters()
                if values.expires_at is not None:
                    delta = values.expires_at - self.at
                    duration = min(
                        duration,
                        (delta + timedelta(microseconds=999))
                        // timedelta(milliseconds=1),
                    )
                self.regenerate(duration, values)
                self.advance(duration)
                self.meta["respawn_remaining_ms"] -= duration
                if self.meta["respawn_remaining_ms"]:
                    continue
            if self.meta["opponent_hp"] == 0:
                self.spawn()
                if self.reason is not None:
                    break
                self.offense = _unpack(self.meta["offense"])
                self.defense = _unpack(self.meta["defense"])
            values = self.parameters()
            if self.elapsed + values.player.cycle_ms > budget:
                break
            self.cycle(values)
            if self.cycles >= self.content.progression.combat.max_cycles_per_resolve:
                self.reason = self.reason or StopReason.COMBAT_OFFLINE_CAP
        return self.result()

    def result(self) -> ResolveResult:
        """Return JSON-safe encounter state and reward deltas."""
        xp_delta = {
            skill: amount - self.state.skills_xp.get(skill, 0)
            for skill, amount in self.xp.items()
            if amount != self.state.skills_xp.get(skill, 0)
        }
        details = {
            **self.summary,
            "xp_by_skill": xp_delta,
            "consumables_used": dict(self.consumed),
            "loot": dict(self.gained),
        }
        totals = dict(self.meta.get("totals", {}))
        for key, value in self.summary.items():
            totals[key] = totals.get(key, 0) + value
        for key, values in (
            ("xp_by_skill", xp_delta),
            ("consumables_used", self.consumed),
            ("loot", self.gained),
        ):
            previous = dict(totals.get(key, {}))
            for identifier, value in values.items():
                previous[identifier] = previous.get(identifier, 0) + value
            totals[key] = previous
        self.meta.update(
            hp_exact=_pack(self.hp),
            damage_taken_carry=_pack(self.damage_taken_carry),
            offense=_pack(self.offense),
            defense=_pack(self.defense),
            xp_carries={skill: _pack(value) for skill, value in self.carries.items()},
            buffs={item: expiry.isoformat() for item, expiry in self.buffs.items()},
            rng_state=[
                self.rng.getstate()[0],
                list(self.rng.getstate()[1]),
                self.rng.getstate()[2],
            ],
            totals=totals,
            cycle_ms=self.parameters().player.cycle_ms,
        )
        state = replace(
            self.state,
            hp=float(self.hp),
            skills_xp=self.xp,
            skill_levels=self.levels,
            inventory=self.inventory,
            instances=tuple(self.instances),
            belt=self.belt,
            utility_quantity=self.utility,
            buff_expiries=self.buffs,
            timed_buffs=tuple(
                (expiry, self.content.item(item).consumable.buff.modifiers)  # type: ignore[union-attr]
                for item, expiry in self.buffs.items()
            )
            if self.buffs
            else self.state.timed_buffs,
        )
        active = (
            None
            if self.reason
            else replace(self.ctx.active, last_resolved_at=self.at, meta=self.meta)
        )
        return ResolveResult(
            self.cycles,
            xp_delta,
            dict(self.consumed),
            dict(self.gained),
            dict(self.overflow),
            {
                skill: tuple(values)
                for skill, values in self.level_ups.items()
                if values
            },
            self.reason,
            state,
            active,
            self.elapsed,
            details,
        )


class CombatResolver:
    """The registered pure combat action resolver."""

    def resolve(
        self,
        state: CharacterState,
        action: Action,
        ctx: ResolveContext,
        budget_ms: int,
        rng: RandomSource,
    ) -> ResolveResult:
        """Simulate combat within the shared offline budget."""
        return CombatSimulation(state, action, ctx, rng).run(budget_ms)
