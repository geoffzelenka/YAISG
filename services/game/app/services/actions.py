"""Transactional persistence adapter for lazy action resolution."""

import random
import secrets
import uuid
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.content import ContentIndex
from app.content.runtime import CONTENT
from app.content.schemas import CapType, DecayStage
from app.engine import ActiveAction, CharacterState, ResolveResult, resolve
from app.engine.core import BeltStack, InstanceState, action_definition
from app.engine.health import maximum_hp, regenerate_hp
from app.errors import api_error
from app.models import (
    ActiveActionRecord,
    Character,
    CharacterBelt,
    CharacterBuff,
    CharacterEquipment,
    CharacterSkill,
    Currency,
    Estate,
    EstateUpgrade,
    Inventory,
    ItemInstance,
    RealmState,
    RewardLog,
)
from app.services.realms import finalize_realms, prepare_sqlite_write, stack_tags
from app.services.tutorial import seed_arrival


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


def lock_character_and_load_action(
    session: Session, character_id: uuid.UUID
) -> ActiveActionRecord | None:
    """Acquire the per-character serialization lock before loading state."""
    prepare_sqlite_write(session)
    # The parent exists even before the first action. Always lock it first so
    # starts, polls, stops and realm/estate operations serialize consistently.
    session.scalar(
        select(Character)
        .where(Character.id == character_id)
        # Serialize character changes without blocking foreign-key KEY SHARE locks
        # when a realm tick creates a replacement estate for this owner.
        .with_for_update(key_share=True)
        .execution_options(populate_existing=True)
    )
    return session.scalar(
        select(ActiveActionRecord).where(
            ActiveActionRecord.character_id == character_id
        )
    )


def _load_state(
    session: Session,
    character_id: uuid.UUID,
    content: ContentIndex = CONTENT,
    now: datetime | None = None,
) -> CharacterState:
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
    realm_state = session.get(RealmState, character.current_realm_id)
    equipment = list(
        session.scalars(
            select(CharacterEquipment).where(
                CharacterEquipment.character_id == character_id
            )
        )
    )
    gear = [
        (row.slot, content.item(row.item_id).equip)
        for row in equipment
        if row.slot != "utility"
    ]
    buffs = []
    buff_expiries = {}
    for row in session.scalars(
        select(CharacterBuff).where(CharacterBuff.character_id == character_id)
    ):
        consumable = content.item(row.item_id).consumable
        if consumable is None or consumable.buff is None:
            raise RuntimeError(f"buff {row.item_id} has no buff content")
        buffs.append((as_utc(row.expires_at), consumable.buff.modifiers))
        buff_expiries[row.item_id] = as_utc(row.expires_at)
    caps: defaultdict[CapType, float] = defaultdict(float)
    for _, equip in gear:
        if equip is not None:
            for cap, amount in equip.cap_bonuses.items():
                caps[cap] += amount
    return CharacterState(
        instances=tuple(
            InstanceState(
                id=str(row.id),
                template_id=row.template_id,
                realm_id=row.realm_id,
                payload=dict(row.payload),
                uses_total=row.uses_total,
                uses_remaining=row.uses_remaining,
                state=row.state,
                created_at=as_utc(row.created_at),
                bound_at=as_utc(row.bound_at) if row.bound_at else None,
                invalidated_at=as_utc(row.invalidated_at)
                if row.invalidated_at
                else None,
            )
            for row in session.scalars(
                select(ItemInstance).where(
                    ItemInstance.holder_character_id == character_id
                )
            )
        ),
        hp=character.hp,
        stance=character.stance,
        equipment={row.slot: row.item_id for row in equipment},
        utility_quantity=next(
            (row.quantity for row in equipment if row.slot == "utility"), 0
        ),
        belt={
            row.slot: BeltStack(row.item_id, row.quantity, row.trigger)
            for row in session.scalars(
                select(CharacterBelt).where(CharacterBelt.character_id == character_id)
            )
        },
        buff_expiries=buff_expiries,
        skills_xp={skill.skill_id: skill.xp for skill in skills},
        skill_levels={skill.skill_id: skill.level for skill in skills},
        inventory={stack.item_id: stack.quantity for stack in inventory},
        gold=currency.gold,
        estate_form_id=estate.form_id,
        current_realm_id=character.current_realm_id,
        estate_realm_id=estate.realm_id,
        realm_node_id=(
            realm_state.current_node_id
            if realm_state
            else content.realm(character.current_realm_id).starting_node_id
        ),
        realm_stage=DecayStage(realm_state.decay_stage)
        if realm_state
        else DecayStage.FED,
        realm_stack_tags=stack_tags(session, character.current_realm_id),
        estate_stage=DecayStage(estate.decay_stage),
        installed_upgrades=tuple(upgrades),
        timed_buffs=tuple(buffs),
        consumable_modifiers=tuple(
            modifier
            for end, values in buffs
            if now is not None and end > now
            for modifier in values
        ),
        gear_modifiers=tuple(
            m for _, equip in gear if equip is not None for m in equip.modifiers
        ),
        right_hand_tool_class=next(
            (
                equip.tool_class
                for slot, equip in gear
                if slot == "right_hand" and equip is not None
            ),
            None,
        ),
        cap_bonuses=dict(caps),
    )


def load_character_state(
    session: Session,
    character_id: uuid.UUID,
    content: ContentIndex = CONTENT,
    now: datetime | None = None,
) -> CharacterState:
    """Load engine state without acquiring a write lock or mutating it."""
    return _load_state(session, character_id, content, now)


def discovery_lifecycle(
    realm: RealmState | None, created_at: datetime
) -> tuple[str, datetime | None]:
    """Classify historical discoveries against completed and pending windows."""
    if realm is None:
        return "active", None
    completions = sorted(
        as_utc(datetime.fromisoformat(event["completes_at"]))
        for event in (realm.transition_history or ())
    )
    cutoff = next((at for at in completions if created_at < at), None)
    if cutoff is not None:
        return "invalid", cutoff
    pending = realm.pending_transition
    if pending is not None:
        end = as_utc(datetime.fromisoformat(pending["completes_at"]))
        if created_at < end:
            return "deprecated", None
    return "active", None


def _persist_state(
    session: Session, character_id: uuid.UUID, state: CharacterState
) -> None:
    character = session.get(Character, character_id)
    if character is None:
        raise RuntimeError(f"character {character_id} does not exist")
    estate = session.get(Estate, character.home_estate_id)
    if estate is None:
        raise RuntimeError(f"character {character_id} has no estate")
    character.current_realm_id = state.current_realm_id
    estate.realm_id = state.estate_realm_id
    for key in state.instances:
        row = session.get(ItemInstance, uuid.UUID(key.id))
        if row is None:
            realm = session.get(RealmState, key.realm_id)
            lifecycle, invalidated_at = discovery_lifecycle(realm, key.created_at)
            session.add(
                ItemInstance(
                    id=uuid.UUID(key.id),
                    kind="key",
                    template_id=key.template_id,
                    holder_character_id=character_id,
                    discovered_by_character_id=character_id,
                    discovered_by_name=character.name,
                    realm_id=key.realm_id,
                    payload=dict(key.payload),
                    uses_total=key.uses_total,
                    uses_remaining=key.uses_remaining,
                    state=lifecycle,
                    invalidated_at=invalidated_at,
                    bound_at=key.bound_at,
                    created_at=key.created_at,
                )
            )
        else:
            row.uses_remaining = key.uses_remaining
            row.state = key.state
            row.invalidated_at = key.invalidated_at
            row.bound_at = key.bound_at
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


def _persist_consumable_holders(
    session: Session, character_id: uuid.UUID, state: CharacterState
) -> None:
    """Persist consumed holders and activated buffs under the character lock."""
    utility = session.get(CharacterEquipment, (character_id, "utility"))
    if utility is not None:
        if state.utility_quantity:
            utility.quantity = state.utility_quantity
        else:
            session.delete(utility)
    for row in session.scalars(
        select(CharacterBelt).where(CharacterBelt.character_id == character_id)
    ):
        stack = state.belt.get(row.slot)
        if stack is None:
            session.delete(row)
        else:
            row.quantity = stack.quantity
    for item_id, expiry in state.buff_expiries.items():
        buff = session.get(CharacterBuff, (character_id, item_id))
        if buff is None:
            session.add(
                CharacterBuff(
                    character_id=character_id, item_id=item_id, expires_at=expiry
                )
            )
        else:
            buff.expires_at = expiry


def resolve_character(
    session: Session,
    character_id: uuid.UUID,
    now: datetime,
    content: ContentIndex | None = None,
    additional_realm_ids: set[str] | None = None,
) -> Resolution:
    """Resolve and persist one character inside the caller's transaction."""
    record = lock_character_and_load_action(session, character_id)
    return resolve_locked_character(
        session, character_id, now, content, additional_realm_ids, record
    )


def resolve_locked_character(
    session: Session,
    character_id: uuid.UUID,
    now: datetime,
    content: ContentIndex | None = None,
    additional_realm_ids: set[str] | None = None,
    record: ActiveActionRecord | None = None,
) -> Resolution:
    """Resolve while the caller already holds the character serialization lock."""
    if record is None:
        record = session.scalar(
            select(ActiveActionRecord).where(
                ActiveActionRecord.character_id == character_id
            )
        )
    character = session.get(Character, character_id)
    if character is None:
        raise RuntimeError(f"character {character_id} does not exist")
    resolved_content = content or CONTENT
    for realm_id in additional_realm_ids or ():
        realm = session.get(RealmState, realm_id)
        if (
            realm is not None
            and realm.isolated
            and realm.owner_character_id != character_id
        ):
            raise api_error(404, "UNKNOWN_REALM", "The realm does not exist")
    realm_ids = set(additional_realm_ids or ())
    realm_ids.update(
        session.scalars(
            select(ItemInstance.realm_id).where(
                ItemInstance.holder_character_id == character_id
            )
        )
    )
    realm_ids.add(character.current_realm_id)
    # Estate availability follows its own realm even while the owner is visiting.
    estate_realm_id = session.scalar(
        select(Estate.realm_id).where(Estate.id == character.home_estate_id)
    )
    if estate_realm_id is not None:
        realm_ids.add(estate_realm_id)
    if record is not None:
        realm_ids.update(
            step["destination_realm_id"] for step in record.meta.get("route", [])
        )
    realms = finalize_realms(session, realm_ids, now, resolved_content)
    home = session.get(Estate, character.home_estate_id)
    while home is not None and home.status == "destroyed":
        character.home_estate_id = uuid.UUID(home.data["replacement_id"])
        home = session.get(Estate, character.home_estate_id)
    session.scalar(
        select(Estate).where(Estate.id == character.home_estate_id).with_for_update()
    )
    is_combat = (
        record is not None
        and action_definition(record.action_id, record.meta, resolved_content).resolver
        == "combat"
    )
    if not is_combat:
        regenerate_character_hp(session, character, now, resolved_content)
    if record is None:
        return Resolution(None, empty_result())
    state = replace(
        _load_state(session, character_id, resolved_content, now),
        realm_states={
            realm_id: (
                realm.current_node_id,
                DecayStage(realm.decay_stage),
                stack_tags(session, realm_id),
            )
            if realm
            else (resolved_content.realm(realm_id).starting_node_id, DecayStage.FED, ())
            for realm_id, realm in realms.items()
        },
    )
    action = ActiveAction(
        action_id=record.action_id,
        started_at=as_utc(record.started_at),
        last_resolved_at=as_utc(record.last_resolved_at),
        meta=dict(record.meta),
    )
    new_state, new_active, result = resolve(
        state,
        action,
        resolved_content,
        now,
        random.Random(secrets.randbits(256)),
    )
    _persist_state(session, character_id, new_state)
    seed_arrival(session, character, resolved_content, now)
    session.flush()
    if (
        not is_combat
        and resolved_content.skill(
            action_definition(record.action_id, record.meta, resolved_content).skill_id
        ).category
        == "exploration"
    ):
        _persist_consumable_holders(session, character_id, new_state)
    if is_combat:
        assert new_state.hp is not None
        character.hp = new_state.hp
        character.hp_updated_at = action.last_resolved_at + timedelta(
            milliseconds=result.elapsed_ms
        )
        _persist_consumable_holders(session, character_id, new_state)
        if new_active is None:
            session.flush()
            regenerate_character_hp(session, character, now, resolved_content)
    else:
        regenerate_character_hp(session, character, now, resolved_content)
    if new_active is None:
        session.delete(record)
        remaining = None
    else:
        record.action_id = new_active.action_id
        record.started_at = new_active.started_at
        record.last_resolved_at = new_active.last_resolved_at
        record.meta = dict(new_active.meta)
        remaining = record
    if (
        result.cycles_completed > 0
        or result.stop_reason is not None
        or result.elapsed_ms > 0
        or bool(result.details.keys() - {"level_ups", "stop_reason"})
    ):
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
                details=dict(result.details),
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
    details: list[dict[str, object]] = []
    for log in logs:
        details.append(dict(log.details))
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
        details={"resolutions": details} if details else {},
    )


def clear_active_action(session: Session, character_id: uuid.UUID) -> None:
    """Remove a character's active action in the current transaction."""
    session.execute(
        delete(ActiveActionRecord).where(
            ActiveActionRecord.character_id == character_id
        )
    )


def character_max_hp(
    session: Session,
    character_id: uuid.UUID,
    content: ContentIndex,
    now: datetime | None = None,
) -> float:
    """Load armour contributions and evaluate the pure maximum-health formula."""
    armour_hp = 0.0
    for row in session.scalars(
        select(CharacterEquipment).where(
            CharacterEquipment.character_id == character_id,
            CharacterEquipment.slot != "utility",
        )
    ):
        equip = content.item(row.item_id).equip
        if equip is not None and equip.armour is not None:
            armour_hp += equip.armour.max_hp
    return maximum_hp(
        _load_state(session, character_id, content, now), armour_hp, content
    )


def regenerate_character_hp(
    session: Session, character: Character, now: datetime, content: ContentIndex
) -> None:
    """Materialize lazy HP under the existing character serialization lock."""
    maximum = character_max_hp(session, character.id, content, now)
    character.hp = min(maximum, max(0.0, character.hp))
    if character.hp_updated_at is None:
        character.hp = maximum
        character.hp_updated_at = now
    elif now >= as_utc(character.hp_updated_at):
        character.hp = regenerate_hp(
            character.hp,
            maximum,
            as_utc(character.hp_updated_at),
            now,
            content.progression.combat.regen_per_min,
        )
        character.hp_updated_at = now
