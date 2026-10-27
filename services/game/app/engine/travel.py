"""Pure routing, step pricing and lazy journey resolution."""

import heapq
import math
from collections import defaultdict
from dataclasses import replace
from datetime import timedelta
from fractions import Fraction
from typing import Any

from app.content.loader import ContentIndex
from app.content.schemas import (
    Action,
    ActionInput,
    DecayStage,
    MapEdge,
    ModifierType,
    TravelProfile,
)
from app.engine.core import (
    CharacterState,
    RandomSource,
    ResolveContext,
    ResolveResult,
    StopReason,
    input_payment,
    modifier_applies,
    modifier_groups,
)
from app.engine.levels import level_for_xp, tier_for_level


def route(
    origin: str,
    destination: str,
    profile: TravelProfile,
    level: int,
    content: ContentIndex,
) -> list[dict[str, str]]:
    """Find the least base-time path, then fewest edges, then edge ids."""
    graph: defaultdict[str, list[tuple[str, MapEdge]]] = defaultdict(list)
    for edge in content.map.edges:
        if edge.terrain not in profile.terrains or edge.min_travel_level > level:
            continue
        graph[edge.a].append((edge.b, edge))
        if not edge.one_way:
            graph[edge.b].append((edge.a, edge))
    queue: list[tuple[Fraction, int, tuple[str, ...], str]] = [
        (Fraction(0), 0, (), origin)
    ]
    paths: dict[tuple[str, ...], list[dict[str, str]]] = {(): []}
    visited: set[str] = set()
    while queue:
        elapsed, count, ids, realm = heapq.heappop(queue)
        if realm in visited:
            continue
        visited.add(realm)
        if realm == destination:
            return paths[ids]
        for target, edge in graph[realm]:
            if target in visited:
                continue
            next_ids = (*ids, edge.id)
            paths[next_ids] = paths[ids] + [
                {"edge_id": edge.id, "destination_realm_id": target}
            ]
            heapq.heappush(
                queue,
                (
                    elapsed + Fraction(str(edge.base_time_s)),
                    count + 1,
                    next_ids,
                    target,
                ),
            )
    raise ValueError(f"No route from {origin!r} to {destination!r}")


def travel_profile(
    state: CharacterState, mode: str, content: ContentIndex
) -> TravelProfile:
    """Return the visitor or mobile estate's movement profile."""
    if mode == "visit":
        return content.progression.visit_profile
    profile = content.estate_form(state.estate_form_id).travel_profile
    if profile is None:
        raise ValueError("A fixed estate has no relocation profile")
    return profile


def travel_total(
    kind: ModifierType, state: CharacterState, content: ContentIndex
) -> Fraction:
    """Combine G/E/R/C and Travel's current tier as group P."""
    factors: list[Fraction] = []
    for group in modifier_groups(state, content):
        percent = sum(
            (
                Fraction(str(modifier.value))
                for modifier in group
                if modifier.type == kind
                and modifier_applies(
                    modifier, "travel", content.skill("travel").category
                )
            ),
            Fraction(0),
        )
        factors.append(
            max(Fraction(str(content.progression.min_factor)), 1 + percent / 100)
        )
    tier = tier_for_level(
        state.skill_levels.get("travel", 1), content.progression.tier_thresholds
    )
    benefit = content.progression.tier_benefits["travel"][tier - 1]
    percent = (
        Fraction(str(benefit.journey_speed_pct))
        if kind == ModifierType.JOURNEY_SPEED_PCT
        else Fraction(str(benefit.supply_reduction_pct))
    )
    return math.prod(factors, start=Fraction(1)) * max(
        Fraction(str(content.progression.min_factor)), 1 + percent / 100
    )


def step_cost(
    edge: MapEdge, state: CharacterState, profile: TravelProfile, content: ContentIndex
) -> tuple[int, tuple[ActionInput, ...]]:
    """Price a step once at start, rounding supplies up and time to milliseconds."""
    duration = max(
        1,
        math.ceil(
            Fraction(str(edge.base_time_s))
            * 1000
            * Fraction(str(profile.time_mult))
            / travel_total(ModifierType.JOURNEY_SPEED_PCT, state, content)
        ),
    )
    reduction = travel_total(ModifierType.SUPPLY_REDUCTION_PCT, state, content)
    supplies = tuple(
        entry.model_copy(update={"quantity": quantity})
        for entry in edge.supplies
        if (
            quantity := math.ceil(
                entry.quantity * Fraction(str(profile.supply_mult)) / reduction
            )
        )
        > 0
    )
    return duration, supplies


def arrival_state(
    state: CharacterState, destination: str, mode: str, content: ContentIndex
) -> CharacterState:
    """Move presence and switch realm sources before pricing the following step."""
    node, stage = state.realm_states.get(
        destination, (content.realm(destination).starting_node_id, DecayStage.FED)
    )
    return replace(
        state,
        current_realm_id=destination,
        estate_realm_id=destination if mode == "relocate" else state.estate_realm_id,
        realm_node_id=node,
        realm_stage=stage,
        realm_stack_tags=(),
    )


def complete_step(
    state: CharacterState,
    edge: MapEdge,
    destination: str,
    mode: str,
    content: ContentIndex,
) -> tuple[CharacterState, tuple[int, ...]]:
    """Move to the next realm and award XP from base time, with no XP bonuses."""
    state = arrival_state(state, destination, mode, content)
    xp = dict(state.skills_xp)
    levels = dict(state.skill_levels)
    xp["travel"] = xp.get("travel", 0) + math.floor(
        Fraction(str(edge.base_time_s))
        * Fraction(str(content.progression.travel_xp_per_second))
    )
    level = level_for_xp(xp["travel"], content.xp_curve.levels)
    gained = tuple(range(levels.get("travel", 1) + 1, level + 1))
    levels["travel"] = level
    return replace(state, skills_xp=xp, skill_levels=levels), gained


class TravelResolver:
    """Resolve a fixed route while retaining paid partial-step progress."""

    def resolve(
        self,
        state: CharacterState,
        action: Action,
        ctx: ResolveContext,
        budget_ms: int,
        rng: RandomSource,
    ) -> ResolveResult:
        """Pay each step at start and grant base-time XP only on arrival."""
        del rng
        content = ctx.content
        meta: dict[str, Any] = dict(ctx.active.meta)
        steps = meta["route"]
        index = int(meta.get("step_index", 0))
        remaining = int(meta.get("remaining_ms", 0))
        consumed: defaultdict[str, int] = defaultdict(int)
        edges_completed: list[str] = []
        levels_gained: list[int] = []
        initial_xp = state.skills_xp.get("travel", 0)
        elapsed = 0
        reason = None
        edges = {edge.id: edge for edge in content.map.edges}
        while index < len(steps):
            edge = edges[steps[index]["edge_id"]]
            if remaining == 0:
                duration, supplies = step_cost(
                    edge, state, travel_profile(state, meta["mode"], content), content
                )
                payment = input_payment(
                    state.inventory,
                    action.model_copy(update={"inputs": supplies}),
                    content,
                )
                if payment is None:
                    reason = StopReason.OUT_OF_SUPPLIES
                    break
                inventory = dict(state.inventory)
                for item_id, quantity in payment.items():
                    inventory[item_id] -= quantity
                    consumed[item_id] += quantity
                state = replace(
                    state, inventory={k: v for k, v in inventory.items() if v}
                )
                remaining = duration
                meta["duration_ms"] = duration
            spent = min(remaining, budget_ms - elapsed)
            remaining -= spent
            elapsed += spent
            if remaining:
                break
            state, gained = complete_step(
                state, edge, steps[index]["destination_realm_id"], meta["mode"], content
            )
            levels_gained.extend(gained)
            edges_completed.append(edge.id)
            index += 1
        meta.update(step_index=index, remaining_ms=remaining)
        active = (
            replace(
                ctx.active,
                meta=meta,
                last_resolved_at=ctx.active.last_resolved_at
                + timedelta(milliseconds=elapsed),
            )
            if reason is None and index < len(steps)
            else None
        )
        xp_delta = state.skills_xp.get("travel", 0) - initial_xp
        return ResolveResult(
            len(edges_completed),
            {"travel": xp_delta} if xp_delta else {},
            dict(consumed),
            {},
            {},
            {"travel": tuple(levels_gained)} if levels_gained else {},
            reason,
            state=state,
            active=active,
            elapsed_ms=elapsed,
            details={
                "edges_completed": edges_completed,
                "supplies_used": dict(consumed),
                "xp": xp_delta,
                "current_realm_id": state.current_realm_id,
            },
        )
