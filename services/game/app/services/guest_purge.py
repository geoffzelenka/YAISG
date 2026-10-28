"""Atomic guest cleanup with explicit custody disposal and durable sink audits."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.content.loader import ContentIndex
from app.guest_settings import GuestSettings
from app.models import (
    ActiveActionRecord,
    Character,
    CharacterBelt,
    CharacterBuff,
    CharacterEquipment,
    CharacterSkill,
    Currency,
    Estate,
    EstateLarder,
    EstateOwnershipHistory,
    EstateUpgrade,
    GoldLedger,
    GoodsLedger,
    Inventory,
    ItemInstance,
    KeyListing,
    MarketOrder,
    Player,
    RealmContribution,
    RealmLine,
    RealmProjectRun,
    RealmShipment,
    RealmState,
    RealmStore,
    RealmTag,
    RealmVote,
    RealmVoteEligibility,
    RewardLog,
)
from app.services.realms import as_utc, prepare_sqlite_write

GUEST_PURGE_LOCK = 1497453385


class PurgeAudit:
    """Write sinks in the same transaction that removes their physical holders."""

    def __init__(
        self, session: Session, character_id: uuid.UUID, now: datetime
    ) -> None:
        self.session = session
        self.character_id = character_id
        self.now = now

    def goods(self, item: str, amount: int, holder: str) -> None:
        """Record a physical sink in milli-items, including individual keys."""
        if amount:
            self.session.add(
                GoodsLedger(
                    cause="guest_purge",
                    item_id=item,
                    amount_milli=-amount,
                    holder=holder,
                    character_id=self.character_id,
                    at=self.now,
                )
            )

    def gold(self, amount: int, realm_id: str | None = None) -> None:
        """Record destruction of wallet, escrow, slot or isolated treasury gold."""
        if amount:
            self.session.add(
                GoldLedger(
                    cause="guest_purge",
                    amount=-amount,
                    realm_id=realm_id,
                    character_id=self.character_id,
                    at=self.now,
                )
            )


def dispose_character(
    session: Session, character: Character, content: ContentIndex, now: datetime
) -> None:
    """Dispose a locked character after locking realms, estates and orders.

    Shared fixed estates become realm-owned, retaining their upgrades/larder.
    Mobile estates and estates inside the owner's isolated instances disappear.
    Provenance on shared projects, votes and keys survives without the identity.
    """
    realms = list(
        session.scalars(select(RealmState).order_by(RealmState.id).with_for_update())
    )
    isolated = {
        r.id for r in realms if r.isolated and r.owner_character_id == character.id
    }
    estates = list(
        session.scalars(
            select(Estate)
            .where(
                or_(
                    Estate.owner_character_id == character.id,
                    Estate.realm_id.in_(isolated),
                )
            )
            .order_by(Estate.id)
            .with_for_update()
        )
    )
    orders = list(
        session.scalars(
            select(MarketOrder)
            .where(
                MarketOrder.character_id == character.id,
            )
            .order_by(MarketOrder.unit_price, MarketOrder.created_at, MarketOrder.id)
            .with_for_update()
        )
    )
    if any(estate.owner_character_id not in {None, character.id} for estate in estates):
        raise ValueError("Isolated realm estate has foreign ownership")
    _validate_isolation(session, character.id, isolated)
    audit = PurgeAudit(session, character.id, now)
    _dispose_orders(session, orders, audit)
    _dispose_keys(session, character.id, isolated, audit)
    _dispose_personal(session, character.id, audit)
    _dispose_estates(session, estates, isolated, content, audit)
    _detach_provenance(session, character.id)
    _dispose_realms(session, isolated, audit)
    session.flush()
    session.delete(character)
    session.flush()


def _validate_isolation(
    session: Session, character_id: uuid.UUID, isolated: set[str]
) -> None:
    """Fail atomically on foreign custody even when SQLite FK checks are disabled."""
    foreign_orders = session.scalar(
        select(MarketOrder.id)
        .where(
            MarketOrder.realm_id.in_(isolated),
            MarketOrder.character_id != character_id,
        )
        .limit(1)
    )
    foreign_listings = session.scalar(
        select(KeyListing.id)
        .where(
            KeyListing.realm_id.in_(isolated),
            KeyListing.seller_character_id != character_id,
        )
        .limit(1)
    )
    foreign_presence = session.scalar(
        select(Character.id)
        .where(
            Character.current_realm_id.in_(isolated),
            Character.id != character_id,
        )
        .limit(1)
    )
    if foreign_orders or foreign_listings or foreign_presence:
        raise ValueError(
            "Isolated guest realm has foreign character or market references"
        )


def _dispose_orders(
    session: Session, orders: list[MarketOrder], audit: PurgeAudit
) -> None:
    for order in orders:
        audit.gold(order.fill_gold + order.escrow_gold_remaining, order.realm_id)
        amount = order.fill_items + (
            order.quantity_remaining if order.side == "sell" else 0
        )
        audit.goods(order.item_id, amount * 1000, f"order:{order.id}")
        session.delete(order)
    session.flush()


def _dispose_keys(
    session: Session, character_id: uuid.UUID, isolated: set[str], audit: PurgeAudit
) -> None:
    listings = list(
        session.scalars(
            select(KeyListing)
            .where(
                or_(
                    KeyListing.seller_character_id == character_id,
                    KeyListing.buyer_character_id == character_id,
                )
            )
            .order_by(KeyListing.created_at, KeyListing.id)
            .with_for_update()
        )
    )
    listed = {row.instance_id for row in listings if row.status == "open"}
    instances = list(
        session.scalars(
            select(ItemInstance).where(
                or_(
                    ItemInstance.holder_character_id == character_id,
                    ItemInstance.id.in_(listed),
                    ItemInstance.realm_id.in_(isolated),
                )
            )
        )
    )
    for instance in instances:
        if instance.holder_character_id not in {None, character_id}:
            raise ValueError("Isolated realm key has foreign custody")
    session.execute(
        delete(ActiveActionRecord).where(
            ActiveActionRecord.character_id == character_id
        )
    )
    for listing in listings:
        session.delete(listing)
    session.flush()
    for instance in instances:
        # A closed listing may reference a key discovered in an isolated realm.
        session.execute(delete(KeyListing).where(KeyListing.instance_id == instance.id))
        audit.goods(f"instance:{instance.template_id}", 1000, f"instance:{instance.id}")
        session.delete(instance)
    session.execute(
        update(ItemInstance)
        .where(
            ItemInstance.discovered_by_character_id == character_id,
        )
        .values(discovered_by_character_id=None)
    )
    session.flush()


def _dispose_personal(
    session: Session, character_id: uuid.UUID, audit: PurgeAudit
) -> None:
    for model in (Inventory, CharacterEquipment, CharacterBelt):
        for item_id, quantity in session.execute(
            select(model.item_id, model.quantity).where(
                model.character_id == character_id
            )
        ):
            audit.goods(
                item_id, quantity * 1000, f"{model.__tablename__}:{character_id}"
            )
        session.execute(delete(model).where(model.character_id == character_id))
    wallet = session.get(Currency, character_id)
    if wallet is not None:
        audit.gold(wallet.gold)
    for personal_model in (Currency, CharacterSkill, CharacterBuff, RewardLog):
        session.execute(
            delete(personal_model).where(personal_model.character_id == character_id)
        )


def _dispose_estates(
    session: Session,
    estates: list[Estate],
    isolated: set[str],
    content: ContentIndex,
    audit: PurgeAudit,
) -> None:
    for estate in estates:
        if (
            estate.realm_id not in isolated
            and content.estate_form(estate.form_id).mobility == "fixed"
        ):
            estate.owner_character_id = None
            continue
        for row in session.scalars(
            select(EstateLarder).where(EstateLarder.estate_id == estate.id)
        ):
            audit.goods(row.item_id, row.quantity_milli, f"estate:{estate.id}")
        for model in (EstateLarder, EstateUpgrade, EstateOwnershipHistory):
            session.execute(delete(model).where(model.estate_id == estate.id))
        session.delete(estate)
    session.flush()


def _detach_provenance(session: Session, character_id: uuid.UUID) -> None:
    session.execute(
        delete(EstateOwnershipHistory).where(
            EstateOwnershipHistory.character_id == character_id
        )
    )
    session.execute(
        delete(RealmVoteEligibility).where(
            RealmVoteEligibility.character_id == character_id
        )
    )
    session.execute(
        update(RealmContribution)
        .where(RealmContribution.character_id == character_id)
        .values(character_id=None)
    )
    session.execute(
        update(RealmProjectRun)
        .where(RealmProjectRun.kicked_off_by == character_id)
        .values(kicked_off_by=None)
    )
    session.execute(
        update(RealmVote)
        .where(RealmVote.called_by == character_id)
        .values(called_by=None)
    )


def _dispose_realms(session: Session, isolated: set[str], audit: PurgeAudit) -> None:
    for shipment in session.scalars(
        select(RealmShipment).where(
            or_(
                RealmShipment.from_realm_id.in_(isolated),
                RealmShipment.to_realm_id.in_(isolated),
            )
        )
    ):
        if shipment.status == "in_transit":
            audit.goods(
                shipment.item_id,
                shipment.quantity_arriving * 1000,
                f"shipment:{shipment.id}",
            )
        session.delete(shipment)
    runs = select(RealmProjectRun.id).where(RealmProjectRun.realm_id.in_(isolated))
    votes = select(RealmVote.id).where(RealmVote.realm_id.in_(isolated))
    session.execute(
        delete(RealmVoteEligibility).where(RealmVoteEligibility.vote_id.in_(votes))
    )
    session.execute(delete(RealmContribution).where(RealmContribution.run_id.in_(runs)))
    for model in (RealmTag, RealmLine, RealmVote, RealmProjectRun):
        session.execute(delete(model).where(model.realm_id.in_(isolated)))
    for realm_id in sorted(isolated):
        realm = session.get(RealmState, realm_id)
        assert realm is not None
        audit.gold(realm.treasury, realm_id)
        for store in session.scalars(
            select(RealmStore).where(RealmStore.realm_id == realm_id)
        ):
            audit.goods(store.item_id, store.quantity_milli, f"realm:{realm_id}")
        session.execute(delete(RealmStore).where(RealmStore.realm_id == realm_id))
        session.delete(realm)
    session.flush()


def purge_guests(
    session: Session, content: ContentIndex, settings: GuestSettings, now: datetime
) -> int:
    """Recheck inactivity under locks and isolate each guest deletion in a savepoint."""
    prepare_sqlite_write(session)
    cutoff = now - timedelta(days=settings.guest_ttl_days)
    identifiers = list(
        session.scalars(
            select(Player.id)
            .where(
                Player.kind == "guest",
                func.coalesce(Player.last_activity_at, Player.created_at) < cutoff,
            )
            .order_by(Player.id)
        )
    )
    # Lock the entire candidate character set before taking any realm lock.
    # Otherwise a later candidate could hold a character while waiting on a
    # realm already locked by this transaction, creating an AB-BA deadlock.
    characters = {
        character.player_id: character
        for character in session.scalars(
            select(Character)
            .where(Character.player_id.in_(identifiers))
            .order_by(Character.id)
            .with_for_update()
        )
    }
    players = list(
        session.scalars(
            select(Player)
            .where(Player.id.in_(identifiers))
            .order_by(Player.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    )
    count = 0
    for player in players:
        character = characters.get(player.id)
        if (
            player.kind != "guest"
            or as_utc(player.last_activity_at or player.created_at) >= cutoff
        ):
            continue
        try:
            with session.begin_nested():
                if character is not None:
                    dispose_character(session, character, content, now)
                session.delete(player)
                session.flush()
            count += 1
        except Exception:
            logging.getLogger(__name__).exception(
                "Game guest purge failed: player_id=%s", player.id
            )
    return count


def run_guest_purge(
    factory: sessionmaker[Session],
    content: ContentIndex,
    settings: GuestSettings,
    now: datetime,
) -> None:
    """Use one transactional PostgreSQL advisory lock and roll back on failure."""
    try:
        with factory() as session:
            if session.get_bind().dialect.name == "postgresql" and not session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"),
                {"key": GUEST_PURGE_LOCK},
            ):
                return
            purge_guests(session, content, settings, now)
            session.commit()
    except Exception:
        logging.getLogger(__name__).exception("Game guest purge failed")
