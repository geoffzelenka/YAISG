"""Guest expiry, physical custody and atomic sink accounting."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from world_accounting import goods

from app.guest_settings import GuestSettings
from app.models import (
    Character,
    CharacterBelt,
    CharacterBuff,
    CharacterEquipment,
    Currency,
    Estate,
    EstateLarder,
    EstateOwnershipHistory,
    GoldLedger,
    GoodsLedger,
    Inventory,
    ItemInstance,
    KeyListing,
    MarketOrder,
    Player,
    RealmContribution,
    RealmProjectRun,
    RealmShipment,
    RealmState,
    RealmStore,
    RealmTag,
    RealmVote,
    RealmVoteEligibility,
)
from app.services.guest_purge import purge_guests

SETTINGS = GuestSettings(guest_ttl_days=14, activity_write_interval_minutes=60)


def make_guest(
    session: Session, name: str = "Guest", player_id: uuid.UUID | None = None
) -> tuple[Player, Character]:
    """Create an expired identity and its mobile home with explicit ownership."""
    player = Player(
        id=player_id or uuid.uuid4(),
        auth_user_id=uuid.uuid4(),
        kind="guest",
        created_at=NOW - timedelta(days=15),
        last_activity_at=NOW - timedelta(days=15),
    )
    session.add(player)
    session.flush()
    estate = Estate(realm_id="realm.verdant_vale", form_id="form.camp")
    session.add(estate)
    session.flush()
    character = Character(
        player_id=player.id,
        name=name,
        name_normalized=name.lower(),
        stance=CONTENT.progression.default_stance,
        current_realm_id=estate.realm_id,
        home_estate_id=estate.id,
        created_at=player.created_at,
    )
    session.add(character)
    session.flush()
    estate.owner_character_id = character.id
    session.flush()
    return player, character


def test_game_purge_only_inactive_guests(realm_session: Session) -> None:
    """Full accounts and activity within the TTL survive."""
    session = realm_session
    expired, character = make_guest(session)
    survivors = []
    for name in ("Full", "Recent"):
        player, _ = make_guest(session, name)
        survivors.append(player.id)
        if name == "Full":
            player.kind = "full"
        elif name == "Recent":
            player.last_activity_at = NOW - timedelta(days=14)
    session.commit()
    assert purge_guests(session, CONTENT, SETTINGS, NOW) == 1
    session.commit()
    assert session.get(Player, expired.id) is None
    assert session.get(Character, character.id) is None
    assert all(session.get(Player, identifier) is not None for identifier in survivors)
    assert purge_guests(session, CONTENT, SETTINGS, NOW) == 0


def test_guest_purge_audits_every_holder_and_isolated_realms(
    realm_session: Session,
) -> None:
    """Wallet, slots, escrow, gear, keys, shipments and isolated stores balance."""
    session = realm_session
    player, character = make_guest(session)
    character_id = character.id
    session.add(Currency(character_id=character_id, gold=7))
    session.add(
        Inventory(character_id=character_id, item_id="item.fake_sprig", quantity=3)
    )
    session.add(
        CharacterEquipment(
            character_id=character_id,
            slot="utility",
            item_id="item.fake_ammo",
            quantity=2,
        )
    )
    session.add(
        CharacterBelt(
            character_id=character_id,
            slot=0,
            item_id="item.fake_food",
            quantity=4,
            trigger={},
        )
    )
    session.add(
        CharacterBuff(
            character_id=character_id, item_id="item.fake_food", expires_at=NOW
        )
    )
    isolated = RealmState(
        id="guest-island",
        template_id="realm.verdant_vale",
        isolated=True,
        owner_character_id=character_id,
        current_node_id="node.verdant_t1",
        last_tick_at=NOW,
        treasury=11,
    )
    session.add(isolated)
    session.flush()
    session.add(
        RealmStore(realm_id=isolated.id, item_id="item.fake_sprig", quantity_milli=1250)
    )
    estate = session.get(Estate, character.home_estate_id)
    assert estate is not None
    estate.realm_id = isolated.id
    session.add(
        EstateLarder(estate_id=estate.id, item_id="item.fake_sprig", quantity_milli=750)
    )
    # Shared fixed estates retain physical holdings under realm ownership.
    fixed = Estate(
        realm_id="realm.verdant_vale",
        form_id="form.fake_workshop",
        owner_character_id=character_id,
    )
    session.add(fixed)
    session.flush()
    session.add(
        EstateLarder(estate_id=fixed.id, item_id="item.fake_sprig", quantity_milli=500)
    )
    for side in ("sell", "buy"):
        session.add(
            MarketOrder(
                character_id=character_id,
                side=side,
                item_id="item.fake_sprig",
                unit_price=3,
                quantity=2,
                quantity_remaining=2,
                escrow_gold_remaining=6 if side == "buy" else 0,
                fill_items=1,
                fill_gold=2,
                status="open",
                realm_id="realm.verdant_vale",
                created_at=NOW,
                expires_at=NOW + timedelta(days=1),
            )
        )
    for listed in (False, True):
        key = ItemInstance(
            template_id="fake",
            realm_id=isolated.id,
            holder_character_id=None if listed else character_id,
            discovered_by_character_id=character_id,
            discovered_by_name=character.name,
            payload={},
            uses_total=1,
            uses_remaining=1,
            created_at=NOW,
        )
        session.add(key)
        session.flush()
        if listed:
            session.add(
                KeyListing(
                    instance_id=key.id,
                    seller_character_id=character_id,
                    price_gold=1,
                    realm_id="realm.verdant_vale",
                    status="open",
                    created_at=NOW,
                )
            )
    session.add(
        RealmShipment(
            from_realm_id=isolated.id,
            to_realm_id="realm.verdant_vale",
            item_id="item.fake_sprig",
            quantity_sent=3,
            quantity_arriving=2,
            goods_gold=0,
            fee_gold=0,
            dispatched_at=NOW,
            arrives_at=NOW,
            status="in_transit",
        )
    )
    # Sold keys belong to their buyer, even when the purged guest discovered them.
    buyer, buyer_character = make_guest(session, "Buyer")
    buyer.kind = "full"
    sold = ItemInstance(
        template_id="survives",
        realm_id="realm.verdant_vale",
        holder_character_id=buyer_character.id,
        discovered_by_character_id=character_id,
        discovered_by_name=character.name,
        payload={},
        uses_total=1,
        uses_remaining=1,
        created_at=NOW,
    )
    session.add(sold)
    session.flush()
    session.add(
        KeyListing(
            instance_id=sold.id,
            seller_character_id=character_id,
            buyer_character_id=buyer_character.id,
            price_gold=1,
            realm_id="realm.verdant_vale",
            status="sold",
            created_at=NOW,
            sold_at=NOW,
        )
    )
    run_ids = []
    for realm_id in ("realm.verdant_vale", isolated.id):
        run = RealmProjectRun(
            realm_id=realm_id,
            project_id="project.verdant_cardboard",
            status="funding",
            kicked_off_by=character_id,
            kicked_off_at=NOW,
            required=[],
            contributed=[],
            last_contribution_at=NOW,
        )
        session.add(run)
        session.flush()
        run_ids.append(run.id)
        session.add(
            RealmContribution(
                run_id=run.id,
                character_id=character_id,
                item_id="item.fake_sprig",
                quantity_milli=1000,
                contributed_at=NOW,
            )
        )
        session.add(
            RealmTag(
                realm_id=realm_id,
                tag_id="bonus.fake",
                seq=1,
                node_id="node.verdant_t1",
                acquired_at=NOW,
                project_run_id=run.id,
            )
        )
    vote = RealmVote(
        realm_id="realm.verdant_vale",
        upgrade_id="fake",
        called_by=character_id,
        called_at=NOW,
        closes_at=NOW,
        status="failed",
        yes_weight=0,
        no_weight=0,
        eligible_weight=1,
        fee_gold=0,
    )
    session.add(vote)
    session.flush()
    session.add(
        RealmVoteEligibility(vote_id=vote.id, character_id=character_id, weight=1)
    )
    session.add(
        EstateOwnershipHistory(
            estate_id=fixed.id, character_id=character_id, acquired_at=NOW
        )
    )
    session.commit()
    before = goods(session)
    # This malformed key has physical existence but no valid custodian. Its realm
    # FK must still be cleared by purge, even though the custody oracle rejects it.
    orphan = ItemInstance(
        template_id="orphan",
        realm_id=isolated.id,
        holder_character_id=None,
        discovered_by_character_id=None,
        discovered_by_name="Orphan",
        payload={},
        uses_total=1,
        uses_remaining=1,
        created_at=NOW,
    )
    session.add(orphan)
    before["instance:orphan"] += 1000
    session.commit()
    session.rollback()
    assert purge_guests(session, CONTENT, SETTINGS, NOW) == 1
    session.commit()
    assert session.get(ItemInstance, orphan.id) is None
    after = goods(session)
    sinks: dict[str, int] = {}
    for row in session.scalars(select(GoodsLedger)):
        assert row.cause == "guest_purge" and row.character_id == character_id
        sinks[row.item_id] = sinks.get(row.item_id, 0) + row.amount_milli
    expected = before.copy()
    expected.update(sinks)
    assert after == expected
    assert sum(sinks.values()) == -20000
    assert session.scalar(select(func.sum(GoldLedger.amount))) == -28
    assert session.get(RealmState, isolated.id) is None
    assert session.get(Player, player.id) is None
    assert session.get(Estate, fixed.id) is not None
    session.refresh(fixed)
    assert fixed.owner_character_id is None
    assert session.get(RealmProjectRun, run_ids[0]) is not None
    assert session.get(RealmProjectRun, run_ids[1]) is None
    session.refresh(vote)
    session.refresh(sold)
    assert vote.called_by is None
    assert sold.holder_character_id == buyer_character.id
    assert sold.discovered_by_character_id is None
    assert sold.discovered_by_name == "Guest"
    assert session.scalar(select(func.count()).select_from(ItemInstance)) == 1
    for model in (
        CharacterBuff,
        MarketOrder,
        KeyListing,
        RealmVoteEligibility,
        EstateOwnershipHistory,
    ):
        assert session.scalar(select(func.count()).select_from(model)) == 0


def test_guest_purge_rollback_restores_holders_and_audits(
    realm_session: Session,
) -> None:
    """A failed surrounding transaction cannot leave sinks without holdings."""
    session = realm_session
    player, character = make_guest(session)
    session.add(Currency(character_id=character.id, gold=9))
    session.commit()
    identifier = player.id
    character_id = character.id
    assert purge_guests(session, CONTENT, SETTINGS, NOW) == 1
    session.rollback()
    assert session.get(Player, identifier) is not None
    assert session.get(Currency, character_id) is not None
    assert session.scalar(select(func.count()).select_from(GoldLedger)) == 0


def test_postgres_purge_rechecks_concurrent_activity(realm_session: Session) -> None:
    """Cleanup waits on the character before realms and rechecks committed activity."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from test_estates import _wait_for_postgres_blocker

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    player, character = make_guest(realm_session)
    realm_session.commit()
    player_id, character_id = player.id, character.id
    factory = sessionmaker(bind=realm_session.get_bind())
    started = Event()
    worker_pids: list[int] = []

    def purge() -> int:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            worker_pids.append(
                session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            started.set()
            count = purge_guests(session, CONTENT, SETTINGS, NOW)
            session.commit()
            return count

    with ThreadPoolExecutor(max_workers=1) as pool, factory() as blocker:
        blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        blocker.scalar(
            select(Character).where(Character.id == character_id).with_for_update()
        )
        future = pool.submit(purge)
        try:
            assert started.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pids[0], blocker_pid)
            with factory() as probe:
                assert (
                    probe.scalar(select(RealmState).with_for_update(nowait=True))
                    is not None
                )
            active = blocker.get(Player, player_id)
            assert active is not None
            active.last_activity_at = NOW
            blocker.commit()
        finally:
            blocker.rollback()
        assert future.result(timeout=10) == 0
    realm_session.expire_all()
    assert realm_session.get(Player, player_id) is not None
    assert realm_session.get(Character, character_id) is not None


def test_guest_purge_job_rolls_back_and_logs(
    realm_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A late cleanup failure restores deleted holders and discards sink entries."""
    from sqlalchemy.orm import sessionmaker

    from app.services import guest_purge

    player, character = make_guest(realm_session)
    realm_session.add(Currency(character_id=character.id, gold=9))
    realm_session.commit()
    player_id, character_id = player.id, character.id
    factory = sessionmaker(bind=realm_session.get_bind())

    def fail(*args: object) -> None:
        raise RuntimeError("Injected late purge failure")

    monkeypatch.setattr(guest_purge, "_dispose_realms", fail)
    guest_purge.run_guest_purge(factory, CONTENT, SETTINGS, NOW)
    assert "Game guest purge failed" in caplog.text
    realm_session.expire_all()
    assert realm_session.get(Player, player_id) is not None
    wallet = realm_session.get(Currency, character_id)
    assert wallet is not None and wallet.gold == 9
    assert realm_session.scalar(select(func.count()).select_from(GoldLedger)) == 0


def test_guest_purge_preserves_foreign_isolated_references(
    realm_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Corrupt isolation fails atomically rather than leaving dangling SQLite rows."""
    from sqlalchemy.orm import sessionmaker

    from app.services.guest_purge import run_guest_purge

    guest, character = make_guest(realm_session)
    full, visitor = make_guest(realm_session, "Visitor")
    full.kind = "full"
    island = RealmState(
        id="private-island",
        template_id="realm.verdant_vale",
        isolated=True,
        owner_character_id=character.id,
        current_node_id="node.verdant_t1",
        last_tick_at=NOW,
    )
    realm_session.add(island)
    visitor.current_realm_id = island.id
    realm_session.commit()
    identifiers = guest.id, character.id, visitor.id
    run_guest_purge(sessionmaker(bind=realm_session.get_bind()), CONTENT, SETTINGS, NOW)
    assert "Game guest purge failed" in caplog.text
    realm_session.expire_all()
    assert realm_session.get(Player, identifiers[0]) is not None
    assert realm_session.get(Character, identifiers[1]) is not None
    assert realm_session.get(Character, identifiers[2]) is not None
    assert realm_session.get(RealmState, "private-island") is not None


def test_bad_guest_does_not_block_another_purge(
    realm_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A bad guest rolls back its holders and audits while a later guest is removed."""
    from sqlalchemy.orm import sessionmaker

    from app.services import guest_purge

    session = realm_session
    bad, bad_character = make_guest(session, "Bad", uuid.UUID(int=1))
    good, good_character = make_guest(session, "Good", uuid.UUID(int=2))
    # Process the bad guest first so continuing after its savepoint is exercised.
    session.add_all(
        [
            Currency(character_id=bad_character.id, gold=9),
            Currency(character_id=good_character.id, gold=7),
        ]
    )
    session.commit()
    bad_id, good_id = bad.id, good.id
    bad_character_id, good_character_id = bad_character.id, good_character.id
    original = guest_purge._dispose_realms

    def fail_bad(
        session: Session, isolated: set[str], audit: guest_purge.PurgeAudit
    ) -> None:
        if audit.character_id == bad_character_id:
            raise ValueError("Malformed guest")
        original(session, isolated, audit)

    monkeypatch.setattr(guest_purge, "_dispose_realms", fail_bad)
    guest_purge.run_guest_purge(
        sessionmaker(bind=session.get_bind()), CONTENT, SETTINGS, NOW
    )
    assert "Game guest purge failed" in caplog.text
    session.expire_all()
    assert session.get(Player, bad_id) is not None
    assert session.get(Player, good_id) is None
    assert session.get(Currency, bad_character_id) is not None
    assert session.get(Currency, good_character_id) is None
    assert session.scalar(select(func.sum(GoldLedger.amount))) == -7
    assert (
        session.scalar(
            select(GoldLedger.id).where(GoldLedger.character_id == bad_character_id)
        )
        is None
    )
