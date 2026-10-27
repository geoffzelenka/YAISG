"""Project lifecycle mutations inside character → realm → estate locks."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import ContentIndex
from app.content.schemas import Selector
from app.engine.selectors import Shortfall, pay_selector
from app.errors import api_error
from app.models import (
    Character,
    Currency,
    Estate,
    Inventory,
    RealmContribution,
    RealmProjectRun,
    RealmState,
)
from app.services.realms import as_utc, stack_tags


def active_run(session: Session, realm_id: str) -> RealmProjectRun | None:
    """Find the realm's single funding or building attempt under its lock."""
    return session.scalar(
        select(RealmProjectRun).where(
            RealmProjectRun.realm_id == realm_id,
            RealmProjectRun.status.in_(("funding", "building")),
        )
    )


def has_open_vote(session: Session, realm: RealmState) -> bool:
    """Check the reciprocal vote/project exclusion under the realm lock."""
    from app.services.votes import open_vote

    return open_vote(session, realm.id) is not None


def begin_build(run: RealmProjectRun, now: datetime, content: ContentIndex) -> None:
    """Start construction immediately once all snapshot cost lines are funded."""
    if all(
        held >= line["quantity"] * 1000
        for held, line in zip(run.contributed, run.required, strict=True)
    ):
        run.status = "building"
        run.build_completes_at = now + timedelta(
            seconds=content.project(run.project_id).build_seconds
        )


def _pay_kickoff(
    session: Session,
    character: Character,
    realm: RealmState,
    project_id: str,
    content: ContentIndex,
) -> None:
    project = content.project(project_id)
    currency = session.get(Currency, character.id)
    stacks = {
        s.item_id: s
        for s in session.scalars(
            select(Inventory).where(Inventory.character_id == character.id)
        )
    }
    remaining = {item: stack.quantity for item, stack in stacks.items()}
    if currency is None or currency.gold < project.kickoff.gold:
        raise api_error(409, "MISSING_INPUTS", "Kickoff payment is unavailable")
    for line in project.kickoff.goods:
        payment = pay_selector(remaining, line.selector, line.quantity, content)
        if isinstance(payment, Shortfall):
            raise api_error(409, "MISSING_INPUTS", "Kickoff payment is unavailable")
        for item, quantity in payment.items():
            remaining[item] -= quantity
    currency.gold -= project.kickoff.gold
    realm.treasury += project.kickoff.gold
    for item, stack in stacks.items():
        if remaining[item]:
            stack.quantity = remaining[item]
        else:
            session.delete(stack)


def kickoff(
    session: Session,
    character: Character,
    realm: RealmState,
    project_id: str,
    now: datetime,
    content: ContentIndex,
) -> RealmProjectRun:
    """Check conditions in specification order, then consume payment."""
    if character.current_realm_id != realm.id:
        raise api_error(409, "NOT_PRESENT", "You must be in the realm")
    try:
        project = content.project(project_id)
    except KeyError:
        raise api_error(
            409, "PROJECT_NOT_OFFERED", "The project is not offered"
        ) from None
    estate = session.get(Estate, character.home_estate_id)
    if project.kickoff.who == "residents" and (
        estate is None or estate.realm_id != realm.id
    ):
        raise api_error(
            409, "RESIDENTS_ONLY", "Only residents may kick off this project"
        )
    tags = set(stack_tags(session, realm.id)) | set(
        content.development_node(realm.current_node_id).inherent_tags
    )
    if (
        project_id not in content.development_node(realm.current_node_id).projects
        or not set(project.requires_tags) <= tags
        or project.grants_tag in tags
    ):
        raise api_error(409, "PROJECT_NOT_OFFERED", "The project is not offered")
    if active_run(session, realm.id) is not None:
        raise api_error(
            409, "PROJECT_ACTIVE", "The realm already has an active project"
        )
    if has_open_vote(session, realm):
        raise api_error(409, "REALM_VOTING", "The realm has an open vote")
    if realm.pending_transition is not None:
        raise api_error(409, "REALM_TRANSITIONING", "The realm is transitioning")
    failed_at = session.scalar(
        select(RealmProjectRun.failed_at)
        .where(
            RealmProjectRun.realm_id == realm.id,
            RealmProjectRun.project_id == project_id,
            RealmProjectRun.status == "failed",
        )
        .order_by(RealmProjectRun.failed_at.desc())
        .limit(1)
    )
    if failed_at is not None and now < as_utc(failed_at) + timedelta(
        hours=content.economy.project.fail_cooldown_hours
    ):
        raise api_error(409, "PROJECT_COOLDOWN", "The project is cooling down")
    if character.last_kickoff_at is not None and now < as_utc(
        character.last_kickoff_at
    ) + timedelta(days=1):
        raise api_error(
            409,
            "KICKOFF_LIMIT",
            "You already kicked off a project in the last 24 hours",
        )
    from app.services.stores import require_project_stock

    require_project_stock(session, realm, content)
    _pay_kickoff(session, character, realm, project_id, content)
    run = RealmProjectRun(
        realm_id=realm.id,
        project_id=project_id,
        status="funding",
        kicked_off_by=character.id,
        kicked_off_at=now,
        required=[line.model_dump(mode="json", by_alias=True) for line in project.cost],
        contributed=[0 for _ in project.cost],
        last_contribution_at=now,
    )
    begin_build(run, now, content)
    session.add(run)
    character.last_kickoff_at = now
    session.flush()
    return run


def contribute(
    session: Session,
    realm: RealmState,
    run: RealmProjectRun,
    item_id: str,
    quantity_milli: int,
    character_id: uuid.UUID | None,
    now: datetime,
    content: ContentIndex,
) -> int:
    """Credit one consumed payment; the caller withdraws the returned milli-units.

    Realm stores may supply fractional units. Player payments remain whole units.
    Overlapping selectors use specificity, then authored line order (§14.2).
    """
    if run.status != "funding":
        raise api_error(409, "PROJECT_NOT_FUNDING", "There is no funding project")
    try:
        item = content.item(item_id)
    except KeyError:
        raise api_error(
            409, "PROJECT_ITEM_NOT_NEEDED", "The project does not need this item"
        ) from None
    matches = []
    for index, line in enumerate(run.required):
        selector = Selector.model_validate(line["selector"])
        if selector.matches(item):
            specificity = (
                0
                if selector.item is not None
                else 1
                if selector.tier is not None
                else 2
            )
            matches.append((specificity, index))
    if not matches:
        raise api_error(
            409, "PROJECT_ITEM_NOT_NEEDED", "The project does not need this item"
        )
    _, index = min(matches)
    remaining = int(run.required[index]["quantity"]) * 1000 - run.contributed[index]
    # A player cannot pay a fraction; excess on the last unit is consumed.
    payable = (
        ((remaining + 999) // 1000) * 1000 if character_id is not None else remaining
    )
    paid = min(quantity_milli, payable)
    if paid <= 0:
        raise api_error(
            409, "PROJECT_ITEM_NOT_NEEDED", "This cost line is already funded"
        )
    session.add(
        apply_project_payment(run, index, item_id, paid, character_id, now, content)
    )
    return paid


def apply_project_payment(
    run: RealmProjectRun,
    index: int,
    item_id: str,
    paid: int,
    character_id: uuid.UUID | None,
    now: datetime,
    content: ContentIndex,
) -> RealmContribution:
    """Apply an accepted payment and return its immutable consumption record.

    Request payments and batched realm ticks share progress, idle and build
    semantics; the caller owns withdrawing goods and persisting the record.
    """
    remaining = int(run.required[index]["quantity"]) * 1000 - run.contributed[index]
    progress = list(run.contributed)
    progress[index] += min(paid, remaining)
    run.contributed = progress
    run.last_contribution_at = now
    begin_build(run, now, content)
    return RealmContribution(
        run_id=run.id,
        character_id=character_id,
        item_id=item_id,
        quantity_milli=paid,
        contributed_at=now,
    )


def contribute_character(
    session: Session,
    character: Character,
    realm: RealmState,
    item_id: str,
    quantity: int,
    now: datetime,
    content: ContentIndex,
) -> RealmProjectRun:
    """Consume whole inventory units and append their project credit atomically."""
    if character.current_realm_id != realm.id:
        raise api_error(409, "NOT_PRESENT", "You must be in the realm")
    run = active_run(session, realm.id)
    if run is None or run.status != "funding":
        raise api_error(409, "PROJECT_NOT_FUNDING", "There is no funding project")
    stack = session.get(Inventory, (character.id, item_id))
    if stack is None:
        raise api_error(409, "MISSING_INPUTS", "You do not hold the contribution")
    paid = contribute(
        session,
        realm,
        run,
        item_id,
        min(quantity, stack.quantity) * 1000,
        character.id,
        now,
        content,
    )
    stack.quantity -= paid // 1000
    if stack.quantity == 0:
        session.delete(stack)
    return run
