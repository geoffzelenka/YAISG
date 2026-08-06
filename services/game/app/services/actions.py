"""Transactional persistence adapter for lazy action resolution."""

import random
import secrets
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.content import ContentIndex
from app.content.runtime import CONTENT
from app.engine import ActiveAction, CharacterState, ResolveResult, resolve
from app.models import (
    ActiveActionRecord,
    Character,
    CharacterSkill,
    Currency,
    Estate,
    EstateUpgrade,
    Inventory,
    RealmState,
    RewardLog,
)


@dataclass(frozen=True)
class Resolution:
    """Persisted outcome and remaining active action for one resolve call."""

    active: ActiveActionRecord | None
    result: ResolveResult


def empty_result() -> ResolveResult:
    """Return the reward-feed shape for a resolve with no active action."""
    return ResolveResult(0, {}, {}, {}, {}, {}, None)


def as_utc(value: datetime) -> datetime:
    """Restore UTC tzinfo omitted by SQLite's datetime adapter."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _lock_active_action(
    session: Session, character_id: uuid.UUID
) -> ActiveActionRecord | None:
    """Acquire the per-character serialization lock before loading state."""
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        # Authentication performs a read first. End that harmless transaction so
        # BEGIN IMMEDIATE can acquire SQLite's writer lock before state is loaded.
        if session.in_transaction():
            session.commit()
        session.connection(execution_options={"sqlite_write_intent": True})
    statement = select(ActiveActionRecord).where(
        ActiveActionRecord.character_id == character_id
    )
    if dialect != "sqlite":
        statement = statement.with_for_update()
    record = session.scalar(statement)
    if record is None and dialect != "sqlite":
        # A first start has no action row to lock, so serialize on its stable
        # parent and re-check for an action created by the prior lock holder.
        session.scalar(
            select(Character.id).where(Character.id == character_id).with_for_update()
        )
        record = session.scalar(statement)
    return record


def _load_state(session: Session, character_id: uuid.UUID) -> CharacterState:
    character = session.get(Character, character_id)
    currency = session.get(Currency, character_id)
    estate = session.get(Estate, character.home_estate_id) if character else None
    if character is None or currency is None or estate is None:
        raise RuntimeError(f"character {character_id} has incomplete action state")
    skills = list(
        session.scalars(
            select(CharacterSkill).where(CharacterSkill.character_id == character_id)
        )
    )
    inventory = list(
        session.scalars(select(Inventory).where(Inventory.character_id == character_id))
    )
    upgrades = session.scalars(
        select(EstateUpgrade.upgrade_id).where(EstateUpgrade.estate_id == estate.id)
    )
    realm_state = session.get(RealmState, character.realm_id)
    return CharacterState(
        skills_xp={skill.skill_id: skill.xp for skill in skills},
        skill_levels={skill.skill_id: skill.level for skill in skills},
        inventory={stack.item_id: stack.quantity for stack in inventory},
        gold=currency.gold,
        estate_form_id=estate.form_id,
        realm_node_id=(
            realm_state.node_id
            if realm_state
            else CONTENT.realm(character.realm_id).starting_node_id
        ),
        installed_upgrades=tuple(upgrades),
        cap_bonuses={},
    )


def load_character_state(session: Session, character_id: uuid.UUID) -> CharacterState:
    """Load engine state without acquiring a write lock or mutating it."""
    return _load_state(session, character_id)


def _persist_state(
    session: Session, character_id: uuid.UUID, state: CharacterState
) -> None:
    # Actions cannot change gold, so only skills and inventory are mutable here.
    for skill_id, xp in state.skills_xp.items():
        skill = session.get(CharacterSkill, (character_id, skill_id))
        if skill is None:
            raise RuntimeError(f"character {character_id} lacks skill {skill_id}")
        skill.xp = xp
        skill.level = state.skill_levels[skill_id]

    existing = {
        stack.item_id: stack
        for stack in session.scalars(
            select(Inventory).where(Inventory.character_id == character_id)
        )
    }
    for item_id, stack in existing.items():
        quantity = state.inventory.get(item_id, 0)
        if quantity:
            stack.quantity = quantity
        else:
            session.delete(stack)
    for item_id, quantity in state.inventory.items():
        if item_id not in existing:
            session.add(
                Inventory(character_id=character_id, item_id=item_id, quantity=quantity)
            )


def resolve_character(
    session: Session,
    character_id: uuid.UUID,
    now: datetime,
    content: ContentIndex | None = None,
    additional_realm_ids: set[str] | None = None,
) -> Resolution:
    """Resolve and persist one character inside the caller's transaction."""
    record = _lock_active_action(session, character_id)
    character = session.get(Character, character_id)
    if character is None:
        raise RuntimeError(f"character {character_id} does not exist")
    # Imported locally to keep the finalizers independent of the action adapter.
    from app.services.realms import finalize_realms, finalize_relocation

    finalize_relocation(session, character, now)
    resolved_content = content or CONTENT
    realm_ids = set(additional_realm_ids or ())
    realm_ids.add(character.realm_id)
    finalize_realms(session, realm_ids, now, resolved_content)
    if record is None:
        return Resolution(None, empty_result())
    state = _load_state(session, character_id)
    action = ActiveAction(
        action_id=record.action_id,
        started_at=as_utc(record.started_at),
        last_resolved_at=as_utc(record.last_resolved_at),
    )
    new_state, new_active, result = resolve(
        state,
        action,
        resolved_content,
        now,
        random.Random(secrets.randbits(256)),
    )
    _persist_state(session, character_id, new_state)
    if new_active is None:
        session.delete(record)
        remaining = None
    else:
        record.last_resolved_at = new_active.last_resolved_at
        remaining = record
    if result.cycles_completed > 0:
        session.add(
            RewardLog(
                character_id=character_id,
                action_id=action.action_id,
                cycles=result.cycles_completed,
                xp=dict(result.xp_gained),
                items={
                    "gained": dict(result.items_gained),
                    "consumed": dict(result.items_consumed),
                    "overflowed": dict(result.overflowed_items),
                },
                details={
                    "level_ups": {
                        skill: list(levels)
                        for skill, levels in result.level_ups.items()
                    },
                    "stop_reason": result.stop_reason,
                },
                resolved_at=now,
            )
        )
    return Resolution(remaining, result)


def claim_rewards(
    session: Session, character_id: uuid.UUID, now: datetime
) -> ResolveResult:
    """Claim and aggregate rewards not yet returned through the action feed."""
    session.flush()
    statement = (
        select(RewardLog)
        .where(
            RewardLog.character_id == character_id,
            RewardLog.claimed_at.is_(None),
        )
        .order_by(RewardLog.resolved_at, RewardLog.id)
    )
    if session.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    logs = list(session.scalars(statement))
    xp: defaultdict[str, int] = defaultdict(int)
    consumed: defaultdict[str, int] = defaultdict(int)
    gained: defaultdict[str, int] = defaultdict(int)
    overflowed: defaultdict[str, int] = defaultdict(int)
    level_ups: defaultdict[str, list[int]] = defaultdict(list)
    stop_reason = None
    for log in logs:
        for skill_id, amount in log.xp.items():
            xp[skill_id] += amount
        for item_id, amount in log.items.get("consumed", {}).items():
            consumed[item_id] += amount
        for item_id, amount in log.items.get("gained", {}).items():
            gained[item_id] += amount
        for item_id, amount in log.items.get("overflowed", {}).items():
            overflowed[item_id] += amount
        for skill_id, levels in log.details.get("level_ups", {}).items():
            level_ups[skill_id].extend(levels)
        logged_reason = log.details.get("stop_reason")
        if logged_reason is not None:
            stop_reason = logged_reason
        log.claimed_at = now
    return ResolveResult(
        cycles_completed=sum(log.cycles for log in logs),
        xp_gained=dict(xp),
        items_consumed=dict(consumed),
        items_gained=dict(gained),
        overflowed_items=dict(overflowed),
        level_ups={skill: tuple(levels) for skill, levels in level_ups.items()},
        stop_reason=stop_reason,
    )


def clear_active_action(session: Session, character_id: uuid.UUID) -> None:
    """Remove a character's active action in the current transaction."""
    session.execute(
        delete(ActiveActionRecord).where(
            ActiveActionRecord.character_id == character_id
        )
    )
