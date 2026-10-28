"""Transactional ownership and lifecycle of private Tutorial Island realms."""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.engine.levels import level_for_xp
from app.errors import api_error
from app.models import (
    ActiveActionRecord,
    Character,
    CharacterEquipment,
    CharacterSkill,
    Currency,
    Estate,
    GoldLedger,
    Inventory,
    ItemInstance,
    KeyListing,
    MarketOrder,
    RealmProjectRun,
    RealmState,
    RealmTag,
)
from app.services.guest_purge import (
    PurgeAudit,
    _dispose_estates,
    _dispose_orders,
    _dispose_realms,
    _validate_isolation,
)


def instance_id(template_id: str, character_id: uuid.UUID) -> str:
    """Return the stable private address for one template and owner."""
    return f"{template_id}:{character_id}"


def create_island(
    session: Session, character: Character, content: ContentIndex, now: datetime
) -> None:
    """Create both zero-treasury instances inside character creation's transaction."""
    character.tutorial_step = content.tutorial.steps[0].id
    for template_id in (content.tutorial.realm_1, content.tutorial.realm_2):
        session.add(
            RealmState(
                id=instance_id(template_id, character.id),
                template_id=template_id,
                isolated=True,
                owner_character_id=character.id,
                current_node_id=content.realm(template_id).starting_node_id,
                treasury=0,
                last_tick_at=now,
            )
        )


def seed_arrival(
    session: Session, character: Character, content: ContentIndex, now: datetime
) -> None:
    """Grant the kickoff cost exactly once, atomically with first arrival."""
    if character.tutorial_step is None or character.tutorial_seeded:
        return
    if character.current_realm_id != instance_id(
        content.tutorial.realm_2, character.id
    ):
        return
    wallet = session.get(Currency, character.id)
    assert wallet is not None
    amount = content.project(content.tutorial.raft_site_project).kickoff.gold
    wallet.gold += amount
    character.tutorial_seeded = True
    session.add(
        GoldLedger(
            cause="tutorial_seed",
            amount=amount,
            realm_id=character.current_realm_id,
            character_id=character.id,
            at=now,
        )
    )


def _condition_met(
    session: Session,
    character: Character,
    content: ContentIndex,
    kind: str,
    identifier: str,
    quantity: int,
) -> bool:
    if kind == "has_item":
        stack = session.get(Inventory, (character.id, identifier))
        return stack is not None and stack.quantity >= quantity
    if kind == "skill_level":
        skill = session.get(CharacterSkill, (character.id, identifier))
        return (
            skill is not None
            and level_for_xp(skill.xp, content.xp_curve.levels) >= quantity
        )
    if kind == "equipped":
        return (
            session.scalar(
                select(CharacterEquipment).where(
                    CharacterEquipment.character_id == character.id,
                    CharacterEquipment.item_id == identifier,
                    CharacterEquipment.quantity >= quantity,
                )
            )
            is not None
        )
    if kind == "in_realm":
        return character.current_realm_id in {
            identifier,
            instance_id(identifier, character.id),
        }
    if kind == "tag_present":
        realm = session.get(RealmState, character.current_realm_id)
        return (
            realm is not None
            and identifier
            in content.development_node(realm.current_node_id).inherent_tags
        ) or session.get(RealmTag, (character.current_realm_id, identifier)) is not None
    if kind == "estate_form":
        estate = session.get(Estate, character.home_estate_id)
        return estate is not None and estate.form_id == identifier
    if kind == "project_kicked_off":
        return (
            session.scalar(
                select(RealmProjectRun.id).where(
                    RealmProjectRun.realm_id.in_(
                        [
                            instance_id(content.tutorial.realm_1, character.id),
                            instance_id(content.tutorial.realm_2, character.id),
                        ]
                    ),
                    RealmProjectRun.project_id == identifier,
                )
            )
            is not None
        )
    raise ValueError(f"Unknown tutorial condition {kind!r}")


def advance_steps(
    session: Session, character: Character, content: ContentIndex
) -> None:
    """Advance all satisfied hints; retain the final departure hint until departure."""
    steps = content.tutorial.steps
    while character.tutorial_step is not None:
        index = next(
            i for i, step in enumerate(steps) if step.id == character.tutorial_step
        )
        condition = steps[index].done_when
        if index == len(steps) - 1 or not _condition_met(
            session,
            character,
            content,
            condition.kind,
            condition.id,
            condition.quantity,
        ):
            return
        character.tutorial_step = steps[index + 1].id


def depart(
    session: Session,
    character: Character,
    account_kind: str,
    destination: str,
    content: ContentIndex,
    now: datetime,
) -> None:
    """Move the raft, audit all island sinks and remove both locked instances."""
    if character.tutorial_step is None:
        raise api_error(409, "NOT_IN_TUTORIAL", "You have already left the island")
    estate = session.get(Estate, character.home_estate_id)
    if estate is None or estate.form_id != content.tutorial.raft_form:
        raise api_error(409, "RAFT_REQUIRED", "Build the raft before departing")
    if account_kind != "full":
        raise api_error(403, "ACCOUNT_REQUIRED", "Register before leaving the island")
    if destination not in content.tutorial.arrival_realms:
        raise api_error(422, "INVALID_ARRIVAL_REALM", "Choose an arrival realm")
    isolated = {
        instance_id(t, character.id)
        for t in (content.tutorial.realm_1, content.tutorial.realm_2)
    }
    realms = list(
        session.scalars(select(RealmState).where(RealmState.id.in_(isolated)))
    )
    if len(realms) != 2 or any(
        not r.isolated or r.owner_character_id != character.id for r in realms
    ):
        raise RuntimeError("Tutorial realm ownership is incomplete")
    _validate_isolation(session, character.id, isolated)
    audit = PurgeAudit(session, character.id, now, cause="tutorial_destroy")
    other_estates = list(
        session.scalars(
            select(Estate)
            .where(
                Estate.realm_id.in_(isolated),
                Estate.id != estate.id,
            )
            .order_by(Estate.id)
            .with_for_update()
        )
    )
    if any(e.owner_character_id not in {None, character.id} for e in other_estates):
        raise RuntimeError("Tutorial estate has foreign ownership")
    orders = list(
        session.scalars(
            select(MarketOrder)
            .where(MarketOrder.realm_id.in_(isolated))
            .order_by(MarketOrder.unit_price, MarketOrder.created_at, MarketOrder.id)
            .with_for_update()
        )
    )
    _dispose_orders(session, orders, audit)
    # Stop every island action before deleting any key or realm it can reference.
    session.execute(
        delete(ActiveActionRecord).where(
            ActiveActionRecord.character_id == character.id
        )
    )
    _dispose_island_keys(session, character, isolated, audit)
    _dispose_estates(session, other_estates, isolated, content, audit)
    wallet = session.get(Currency, character.id)
    assert wallet is not None
    audit.gold(wallet.gold)
    wallet.gold = 0
    character.current_realm_id = destination
    character.tutorial_step = None
    estate.realm_id = destination
    session.flush()
    _dispose_realms(session, isolated, audit)


def _dispose_island_keys(
    session: Session, character: Character, isolated: set[str], audit: PurgeAudit
) -> None:
    """Destroy local discoveries and settle listing custody before realm deletion."""
    instances = list(
        session.scalars(select(ItemInstance).where(ItemInstance.realm_id.in_(isolated)))
    )
    ids = {instance.id for instance in instances}
    foreign_action = session.scalar(
        select(ActiveActionRecord.character_id)
        .where(
            ActiveActionRecord.key_instance_id.in_(ids),
            ActiveActionRecord.character_id != character.id,
        )
        .limit(1)
    )
    if foreign_action is not None:
        raise RuntimeError("Tutorial key has a foreign action reference")
    listings = list(
        session.scalars(
            select(KeyListing)
            .where(
                (KeyListing.realm_id.in_(isolated)) | (KeyListing.instance_id.in_(ids))
            )
            .order_by(KeyListing.created_at, KeyListing.id)
            .with_for_update()
        )
    )
    for listing in listings:
        if listing.seller_character_id != character.id:
            raise RuntimeError("Tutorial key has foreign listing custody")
        if listing.status == "open" and listing.instance_id not in ids:
            instance = session.get(ItemInstance, listing.instance_id)
            assert instance is not None
            instance.holder_character_id = character.id
        session.delete(listing)
    session.flush()
    for instance in instances:
        if instance.holder_character_id not in {None, character.id}:
            raise RuntimeError("Tutorial key has foreign custody")
        audit.goods(f"instance:{instance.template_id}", 1000, f"instance:{instance.id}")
        session.delete(instance)
    session.flush()
