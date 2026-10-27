"""Demand-line arithmetic, validation, and one-time world creation."""

import json
import os
import shutil
from dataclasses import replace
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session
from test_realms import realm_session as realm_session

from app.config import CONTENT_DIR
from app.content import ContentError, load_content
from app.content.lint import upkeep_overlaps
from app.content.schemas import Selector, TagUpkeep
from app.db import Base, configure_sqlite_engine
from app.engine.stores import Demand, derive_lines, due, membership, warehouse_cap
from app.models import Estate, RealmLine, RealmState, RealmStore, WorldState
from app.services.stores import recompute_lines
from app.services.world import WorldStateError, create_world

CONTENT = load_content(CONTENT_DIR)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@settings(derandomize=True)
@given(d=st.integers(0, 10**15), T=st.integers(1, 1000), day=st.integers(0, 1000))
def test_due_sums_to_daily_rate(d: int, T: int, day: int) -> None:
    """Every complete day pays exactly the daily rate, even with tiny rates."""
    assert sum(due(d, n, T) for n in range(day * T, (day + 1) * T)) == d


@pytest.mark.parametrize("args", [(-1, 0, 24), (1, -1, 24), (1, 0, 0)])
def test_due_rejects_invalid_inputs(args: tuple[int, int, int]) -> None:
    """Invalid pure inputs fail explicitly."""
    with pytest.raises(ValueError):
        due(*args)


def test_line_grouping_specificity_and_value_units() -> None:
    """Grouping sums rates; stock belongs once, with item then tier precedence."""
    item = CONTENT.items[0]
    broad = Selector.model_validate({"class": item.classes[0]})
    tier = Selector.model_validate({"class": item.classes[0], "tier": item.tier})
    exact = Selector(item=item.id)
    node = CONTENT.development_nodes[0]
    lines = derive_lines(
        node,
        (),
        (),
        (
            Demand(broad, Fraction(1000)),
            Demand(tier, Fraction(2000)),
            Demand(exact, Fraction(3000), True),
            Demand(exact, Fraction(500), True),
        ),
        {item.id: 1234},
        CONTENT,
    )
    chosen = membership(item, lines)
    assert chosen is not None and chosen.selector == exact
    assert chosen.draw_per_day == 3500
    assert chosen.stock == 1234 * item.reference_price
    assert sum(line.stock for line in lines) == chosen.stock
    tier_match = membership(item, tuple(line for line in lines if line != chosen))
    assert tier_match is not None and tier_match.selector == tier
    # A non-unit reference price proves value measurement differs from quantity.
    valuable = CONTENT.items[1]
    value = derive_lines(
        node,
        (),
        (),
        (Demand(Selector(item=valuable.id), Fraction(1000), True),),
        {valuable.id: 2500},
        CONTENT,
    )[0]
    assert value.stock == 2500 * valuable.reference_price > 2500


def test_reserve_delta_transition_node_override_and_no_line_cap() -> None:
    """Reserve includes active tag deltas and the full pending transition window."""
    selector = Selector(item=CONTENT.items[0].id)
    node = CONTENT.development_nodes[0].model_copy(
        update={
            "upkeep": (TagUpkeep(selector=selector, per_day=2),),
            "reserve_days": 4.0,
            "cap_days": 20.0,
        }
    )
    tag = CONTENT.tags[0].model_copy(
        update={
            "effects": CONTENT.tags[0].effects.model_copy(
                update={"reserve_days_delta": 1.0}
            ),
            "upkeep": (TagUpkeep(selector=selector, per_day=1),),
        }
    )
    form = CONTENT.estate_forms[0].model_copy(
        update={
            "upkeep": (TagUpkeep(selector=selector, per_day=3),),
        }
    )
    line = derive_lines(node, (tag,), (form,), (), {}, CONTENT, Fraction(7))[0]
    assert (line.draw_per_day, line.reserve, line.cap) == (6000, 72000, 120000)
    normal = derive_lines(node, (tag,), (form,), (), {}, CONTENT)[0]
    assert normal.reserve == 30000
    item = CONTENT.items[1]
    assert membership(item, (line,)) is None
    assert (
        warehouse_cap(item, CONTENT)
        == CONTENT.economy.warehouse_value_cap * 1000 // item.reference_price
    )
    assert warehouse_cap(item.model_copy(update={"warehouse_cap": 7}), CONTENT) == 7000


def test_validator_rejects_mixed_price_upkeep_class(tmp_path: Path) -> None:
    """Ordinary upkeep requires interchangeable reference values."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "estate_forms.json"
    data = json.loads(path.read_text())
    data["forms"][-1]["upkeep"][0]["selector"] = {"class": "fake_plant"}
    path.write_text(json.dumps(data))
    with pytest.raises(ContentError, match="mixed reference prices"):
        load_content(directory)


def test_upkeep_overlap_warning() -> None:
    """Lint warns about intersecting selectors rather than rejecting overlap."""
    form = CONTENT.estate_forms[-1]
    extra = TagUpkeep(
        selector=Selector.model_validate({"class": "fake_plant"}), per_day=1
    )
    content = replace(
        CONTENT,
        estate_forms=(form.model_copy(update={"upkeep": (*form.upkeep, extra)}),),
    )
    warnings = upkeep_overlaps(content)
    assert len(warnings) == 1 and "upkeep overlap" in warnings[0]


def test_world_creation_twice_creates_once(tmp_path: Path) -> None:
    """Marker, gold, stores, estates, and derived lines survive retries unchanged."""
    engine = create_engine(
        os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'world.db'}")
    )
    if engine.dialect.name == "sqlite":
        configure_sqlite_engine(engine)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            assert create_world(session, CONTENT, NOW)
            session.commit()
            quantities = list(
                session.execute(
                    select(RealmStore.item_id, RealmStore.quantity_milli).order_by(
                        RealmStore.realm_id
                    )
                )
            )
            estates = list(session.scalars(select(Estate.id).order_by(Estate.id)))
            assert len(estates) == sum(
                len(seed.estates) for seed in CONTENT.world_seed.realms
            )
            assert all(
                owner is None
                for owner in session.scalars(select(Estate.owner_character_id))
            )
            marker = session.get(WorldState, 1)
            assert marker is not None
            assert marker.content_version == CONTENT.world_seed_version
            assert session.scalar(select(func.count()).select_from(WorldState)) == 1
            assert not create_world(session, CONTENT, NOW)
            session.commit()
            assert estates == list(
                session.scalars(select(Estate.id).order_by(Estate.id))
            )
            assert quantities == list(
                session.execute(
                    select(RealmStore.item_id, RealmStore.quantity_milli).order_by(
                        RealmStore.realm_id
                    )
                )
            )
            for seed in CONTENT.world_seed.realms:
                realm = session.get(RealmState, seed.realm_id)
                assert realm is not None and realm.treasury == seed.treasury
                first = [
                    (r.line_key, r.draw_per_day, r.stock)
                    for r in recompute_lines(session, realm, CONTENT)
                ]
                session.flush()
                second = [
                    (r.line_key, r.draw_per_day, r.stock)
                    for r in recompute_lines(session, realm, CONTENT)
                ]
                assert first == second
            assert session.scalar(select(func.count()).select_from(RealmLine))
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_funding_overlay_uses_run_snapshot_and_full_estate_upkeep(
    realm_session: Session,
) -> None:
    """Only unfunded snapshot requirements add draw; larder never discounts it."""
    from test_projects import _run

    from app.models import EstateLarder

    realm = realm_session.get(RealmState, "realm.verdant_vale")
    assert realm is not None
    run = _run(realm_session, realm)
    item_id = CONTENT.items[0].id
    run.required = [{"selector": {"item": item_id}, "quantity": 10}]
    run.contributed = [2500]
    estate = Estate(form_id=CONTENT.estate_forms[-1].id, realm_id=realm.id)
    realm_session.add(estate)
    realm_session.flush()
    realm_session.add(
        EstateLarder(estate_id=estate.id, item_id=item_id, quantity_milli=999000)
    )
    realm_session.flush()
    days = Fraction(str(CONTENT.project(run.project_id).realm_completion_days))
    lines = recompute_lines(realm_session, realm, CONTENT)
    target = next(line for line in lines if line.selector == {"item": item_id})
    assert target.draw_per_day == int(1000 + Fraction(7500) / days)
    realm_session.flush()
    run.contributed = [10000]
    lines = recompute_lines(realm_session, realm, CONTENT)
    assert (
        next(line for line in lines if line.selector == {"item": item_id}).draw_per_day
        == 1000
    )
    realm_session.flush()
    run.status = "building"
    run.contributed = [0]
    lines = recompute_lines(realm_session, realm, CONTENT)
    assert (
        next(line for line in lines if line.selector == {"item": item_id}).draw_per_day
        == 1000
    )


def test_postgres_concurrent_world_creation_once(realm_session: Session) -> None:
    """A concurrent creator waits for the seed transaction, then creates nothing."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from test_estates import _wait_for_postgres_blocker

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL conflict locking")
    realm_session.execute(delete(RealmState))
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    ready = threading.Event()
    worker_pid: list[int] = []

    def second_creator() -> bool:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            worker_pid.append(session.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            created = create_world(session, CONTENT, NOW)
            session.commit()
            return created

    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        blocker_pid = first.scalar(text("SELECT pg_backend_pid()"))
        assert isinstance(blocker_pid, int)
        assert create_world(first, CONTENT, NOW)
        future = pool.submit(second_creator)
        try:
            assert ready.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pid[0], blocker_pid)
        finally:
            first.commit()
        assert future.result(timeout=10) is False
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(WorldState)) == 1
        assert session.scalar(select(func.count()).select_from(Estate)) == sum(
            len(seed.estates) for seed in CONTENT.world_seed.realms
        )
        assert session.scalar(select(func.sum(RealmState.treasury))) == sum(
            seed.treasury for seed in CONTENT.world_seed.realms
        )

        from app.models import GoldLedger

        assert session.scalar(select(func.sum(GoldLedger.amount))) == sum(
            seed.treasury for seed in CONTENT.world_seed.realms
        )
        assert session.scalar(select(func.count()).select_from(GoldLedger)) == len(
            CONTENT.world_seed.realms
        )


@pytest.mark.parametrize(
    "case",
    [
        "missing_realm",
        "unknown_item",
        "unknown_form",
        "mobile_form",
        "duplicate_item",
        "isolated_realm",
    ],
)
def test_world_seed_validation(tmp_path: Path, case: str) -> None:
    """Seed references are complete and safe before world creation can begin."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "world_seed.json"
    data = json.loads(path.read_text())
    if case == "missing_realm":
        data["realms"].pop()
    elif case == "unknown_item":
        data["realms"][0]["stores"][0]["item_id"] = "missing"
    elif case == "unknown_form":
        data["realms"][0]["estates"] = ["missing"]
    elif case == "mobile_form":
        data["realms"][0]["estates"] = [CONTENT.progression.basic_mobile_form]
    elif case == "duplicate_item":
        data["realms"][0]["stores"].append(data["realms"][0]["stores"][0])
    else:
        realms_path = directory / "realms.json"
        realms = json.loads(realms_path.read_text())
        realms["realms"][0]["isolated"] = True
        realms_path.write_text(json.dumps(realms))
    path.write_text(json.dumps(data))
    with pytest.raises(ContentError, match="world_seed"):
        load_content(directory)


def test_world_seed_is_private_but_versioned(tmp_path: Path) -> None:
    """Seed treasury changes affect only the private hash, never the manifest."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "world_seed.json"
    data = json.loads(path.read_text())
    data["realms"][0]["treasury"] += 1
    path.write_text(json.dumps(data))
    changed = load_content(directory)
    assert changed.manifest.as_dict() == CONTENT.manifest.as_dict()
    assert changed.world_seed_version != CONTENT.world_seed_version
    assert changed.pack_payloads == CONTENT.pack_payloads
    assert "world_seed" not in changed.manifest.packs


def test_cap_validation_includes_transition_and_tag_delta(tmp_path: Path) -> None:
    """The cap must strictly exceed the maximum attainable reserve."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "economy.json"
    data = json.loads(path.read_text())
    data["cap_days"] = 10
    path.write_text(json.dumps(data))
    with pytest.raises(ContentError, match="cap_days"):
        load_content(directory)
    data["cap_days"] = 11
    path.write_text(json.dumps(data))
    tag_path = directory / "tags.json"
    tags = json.loads(tag_path.read_text())
    tags["tags"][0]["effects"] = {"reserve_days_delta": 2}
    tag_path.write_text(json.dumps(tags))
    with pytest.raises(ContentError, match="cap_days"):
        load_content(directory)


def test_world_creation_rollback_allows_retry(realm_session: Session) -> None:
    """An interrupted seed cannot leave a singleton marker or partial holdings."""
    realm_session.execute(delete(RealmState))
    realm_session.commit()
    assert create_world(realm_session, CONTENT, NOW)
    realm_session.rollback()
    assert realm_session.get(WorldState, 1) is None
    assert realm_session.scalar(select(func.count()).select_from(Estate)) == 0
    assert realm_session.scalar(select(func.count()).select_from(RealmStore)) == 0
    assert create_world(realm_session, CONTENT, NOW)
    realm_session.commit()
    assert not create_world(realm_session, CONTENT, NOW)


def test_pending_reserve_uses_full_recorded_transition(realm_session: Session) -> None:
    """A later content duration change cannot shrink a pending window's reserve."""
    from datetime import timedelta

    from app.services.realms import start_transition

    realm = realm_session.get(RealmState, "realm.verdant_vale")
    assert realm is not None
    realm_session.add(Estate(form_id=CONTENT.estate_forms[-1].id, realm_id=realm.id))
    realm_session.flush()
    start_transition(realm, "node.verdant_t2", "upgrade", NOW, CONTENT)
    assert realm.pending_transition is not None
    realm.pending_transition = {
        **realm.pending_transition,
        "completes_at": (NOW + timedelta(days=5)).isoformat(),
    }
    line = recompute_lines(realm_session, realm, CONTENT)[0]
    assert line.reserve == 8000


@pytest.mark.parametrize("transition_days", [Fraction(0), Fraction(7)])
def test_negative_effective_reserve_days_clamp_to_zero(
    transition_days: Fraction,
) -> None:
    """Large negative tag deltas never create a negative reserve."""
    node = CONTENT.development_nodes[0].model_copy(
        update={
            "upkeep": (
                TagUpkeep(selector=Selector(item=CONTENT.items[0].id), per_day=1),
            )
        }
    )
    tag = CONTENT.tags[0].model_copy(
        update={
            "effects": CONTENT.tags[0].effects.model_copy(
                update={"reserve_days_delta": -20.0}
            )
        }
    )
    line = derive_lines(node, (tag,), (), (), {}, CONTENT, transition_days)[0]
    assert line.reserve == 0
    assert line.draw_per_day == 1000
    assert line.cap == CONTENT.economy.cap_days * 1000


def test_validator_rejects_mixed_price_project_class(tmp_path: Path) -> None:
    """Project cost selectors become ordinary overlay lines and need equal prices."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "projects.json"
    data = json.loads(path.read_text())
    data["projects"][0]["cost"][0]["selector"] = {"class": "fake_plant"}
    path.write_text(json.dumps(data))
    with pytest.raises(ContentError, match="mixed reference prices"):
        load_content(directory)


def test_world_creation_rejects_unmarked_existing_realms(
    realm_session: Session,
) -> None:
    """Partial legacy state cannot receive a treasury or a committed seed marker."""
    realm = realm_session.get(RealmState, "realm.verdant_vale")
    assert realm is not None
    realm.treasury = 77
    realm_session.commit()
    with pytest.raises(WorldStateError, match="run make db-reset"):
        create_world(realm_session, CONTENT, NOW)
    realm_session.commit()
    realm_session.refresh(realm)
    assert realm.treasury == 77
    assert realm_session.get(WorldState, 1) is None
    assert realm_session.scalar(select(func.count()).select_from(Estate)) == 0
    assert realm_session.scalar(select(func.count()).select_from(RealmStore)) == 0


def test_realm_lock_rejects_missing_seeded_realm(realm_session: Session) -> None:
    """A committed world marker never permits silent use of a missing realm."""
    from app.services.realms import finalize_realm

    realm_session.add(
        WorldState(
            id=1,
            seeded_at=NOW,
            last_caravan_pass=NOW,
            content_version=CONTENT.world_seed_version,
        )
    )
    realm_session.commit()
    with pytest.raises(WorldStateError, match="missing realm.*make db-reset"):
        finalize_realm(realm_session, "realm.ashen_reach", NOW, CONTENT)
    assert realm_session.get(RealmState, "realm.ashen_reach") is None


@pytest.mark.parametrize("scope", ["global", "node"])
@pytest.mark.parametrize("cap_days", [2.0, 3.0, 4.0])
def test_cap_days_covers_vote_stock_minimum(
    tmp_path: Path, scope: str, cap_days: float
) -> None:
    """Global defaults and every node override must permit the vote stock gate."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    economy_path = directory / "economy.json"
    economy = json.loads(economy_path.read_text())
    # Isolate the minimum stock rule from the stricter transition-reserve bound.
    economy["reserve_days"] = 0
    economy["transition"]["duration_days"] = 1
    economy["vote"]["min_stock_days"] = 3
    economy["cap_days"] = cap_days if scope == "global" else 11
    economy_path.write_text(json.dumps(economy))
    development_path = directory / "development.json"
    development = json.loads(development_path.read_text())
    if scope == "global":
        # Even when all effective caps override it, the default must be valid.
        for node in development["nodes"]:
            node["cap_days"] = 11
    else:
        development["nodes"][0]["cap_days"] = cap_days
    development_path.write_text(json.dumps(development))
    if cap_days < 3:
        with pytest.raises(
            ContentError, match=r"cap_days must cover vote.min_stock_days"
        ):
            load_content(directory)
    else:
        assert load_content(directory).economy.vote.min_stock_days == 3
