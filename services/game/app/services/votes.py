"""Ballot mutations under the caller's character and realm locks."""

from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import NodeUpgrade
from app.engine.estates import vote_weight
from app.errors import api_error
from app.models import (
    Character,
    Currency,
    Estate,
    RealmState,
    RealmVote,
    RealmVoteEligibility,
)
from app.services.projects import active_run
from app.services.realms import as_utc, stack_tags, start_transition


def open_vote(session: Session, realm_id: str) -> RealmVote | None:
    """Find the single open ballot under the realm lock."""
    return session.scalar(
        select(RealmVote).where(
            RealmVote.realm_id == realm_id, RealmVote.status == "open"
        )
    )


def _validate_call(
    session: Session,
    character: Character,
    realm: RealmState,
    upgrade_id: str,
    now: datetime,
    content: ContentIndex,
) -> NodeUpgrade:
    estate = session.get(Estate, character.home_estate_id)
    if (
        estate is None
        or estate.status != "active"
        or estate.realm_id != realm.id
        or estate.owner_character_id != character.id
    ):
        raise api_error(
            409, "RESIDENTS_ONLY", "Only residents may call an upgrade vote"
        )
    node = content.development_node(realm.current_node_id)
    upgrade = next((u for u in node.upgrades if u.id == upgrade_id), None)
    if upgrade is None:
        raise api_error(409, "UPGRADE_NOT_OFFERED", "The upgrade is not offered")
    if not set(upgrade.required_tags) <= set(node.inherent_tags) | set(
        stack_tags(session, realm.id)
    ):
        raise api_error(409, "UPGRADE_TAGS_REQUIRED", "The realm lacks required tags")
    if active_run(session, realm.id) is not None:
        raise api_error(
            409, "PROJECT_ACTIVE", "The realm already has an active project"
        )
    if open_vote(session, realm.id) is not None:
        raise api_error(409, "REALM_VOTING", "The realm has an open vote")
    if realm.pending_transition is not None:
        raise api_error(409, "REALM_TRANSITIONING", "The realm is transitioning")
    if realm.vote_cooldown_until is not None and now < as_utc(
        realm.vote_cooldown_until
    ):
        raise api_error(409, "VOTE_COOLDOWN", "Upgrade votes are cooling down")
    return upgrade


def call_vote(
    session: Session,
    character: Character,
    realm: RealmState,
    upgrade_id: str,
    now: datetime,
    content: ContentIndex,
) -> RealmVote:
    """Validate the authored edge, transfer its fee, and snapshot residents."""
    upgrade = _validate_call(session, character, realm, upgrade_id, now, content)
    currency = session.get(Currency, character.id)
    if currency is None or currency.gold < upgrade.fee_gold:
        raise api_error(409, "MISSING_INPUTS", "The vote fee is unavailable")
    residents = list(
        session.execute(
            select(Character.id, Estate.form_id)
            .join(Estate, Estate.owner_character_id == Character.id)
            .where(
                Estate.realm_id == realm.id,
                Estate.status == "active",
                Estate.owner_character_id == Character.id,
            )
        )
    )
    weights = [(cid, vote_weight(content.estate_form(form))) for cid, form in residents]
    currency.gold -= upgrade.fee_gold
    realm.treasury += upgrade.fee_gold
    vote = RealmVote(
        realm_id=realm.id,
        upgrade_id=upgrade_id,
        called_by=character.id,
        called_at=now,
        closes_at=now + timedelta(hours=content.economy.vote.duration_hours),
        eligible_weight=sum(weight for _, weight in weights),
        fee_gold=upgrade.fee_gold,
    )
    session.add(vote)
    session.flush()
    session.add_all(
        [
            RealmVoteEligibility(vote_id=vote.id, character_id=cid, weight=weight)
            for cid, weight in weights
        ]
    )
    session.flush()
    return vote


def close_vote(
    realm: RealmState, vote: RealmVote, now: datetime, content: ContentIndex
) -> None:
    """Decide by strict majority of cast weight, retaining the fee on failure."""
    if vote.status != "open":
        return
    if vote.yes_weight > vote.no_weight:
        upgrade = next(
            u
            for u in content.development_node(realm.current_node_id).upgrades
            if u.id == vote.upgrade_id
        )
        vote.status = "passed"
        start_transition(realm, upgrade.to_node, "upgrade", now, content)
    else:
        vote.status = "failed"
        realm.vote_cooldown_until = now + timedelta(
            hours=content.economy.vote.fail_cooldown_hours
        )


def cast_vote(
    session: Session,
    character: Character,
    realm: RealmState,
    choice: Literal["yes", "no"],
    now: datetime,
    content: ContentIndex,
) -> RealmVote:
    """Persist only aggregate weight and participation; discard the choice."""
    vote = open_vote(session, realm.id)
    if vote is None:
        raise api_error(409, "NO_OPEN_VOTE", "The realm has no open vote")
    eligibility = session.get(RealmVoteEligibility, (vote.id, character.id))
    if eligibility is None:
        raise api_error(
            409, "VOTE_INELIGIBLE", "You were not a resident when this vote was called"
        )
    if eligibility.voted_at is not None:
        raise api_error(409, "ALREADY_VOTED", "You have already voted")
    if choice == "yes":
        vote.yes_weight += eligibility.weight
    else:
        vote.no_weight += eligibility.weight
    eligibility.voted_at = now
    session.flush()
    remaining = session.scalar(
        select(RealmVoteEligibility.character_id)
        .where(
            RealmVoteEligibility.vote_id == vote.id,
            RealmVoteEligibility.voted_at.is_(None),
        )
        .limit(1)
    )
    if remaining is None:
        close_vote(realm, vote, now, content)
    return vote
