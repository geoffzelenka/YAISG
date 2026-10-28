"""Mint arithmetic, gold auditability, operator access and bounded catch-up."""

from dataclasses import replace
from datetime import timedelta
from types import MappingProxyType

import pytest
from fastapi import HTTPException
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from test_travel import ApiFixture

from app import config
from app.content.loader import ContentIndex
from app.content.schemas import BuildCost, Item
from app.engine.stores import mint_demands
from app.main import app
from app.models import (
    Character,
    Currency,
    Estate,
    GoldLedger,
    Inventory,
    Player,
    RealmProjectRun,
    RealmState,
    RealmStore,
)
from app.services.realm_ticks import (
    load_context,
    step_4_realm_upkeep,
    step_7_caps,
    step_8_gauges,
    step_10_lines,
)
from app.services.realms import resolve_realm
from app.services.trade import trade
from app.services.world import create_world

REALM = "realm.verdant_vale"
BULLION = "item.fake_bullion"
MINT = "access.fake_mint"


def mint_content() -> ContentIndex:
    """Activate a mint without unrelated upkeep or decay losses."""
    node = CONTENT.development_node("node.verdant_t1").model_copy(
        update={"inherent_tags": (MINT,), "upkeep": ()}
    )
    return replace(
        CONTENT, _nodes_by_id=MappingProxyType({**CONTENT._nodes_by_id, node.id: node})
    )


@pytest.mark.parametrize("flag,classes", [(True, ()), (False, ("bullion",))])
def test_bullion_flag_matches_class(flag: bool, classes: tuple[str, ...]) -> None:
    with pytest.raises(ValidationError, match="bullion flag"):
        Item(
            id="test",
            name="test",
            tier=1,
            reference_price=1,
            bullion=flag,
            classes=classes,
        )


def test_largest_mint_line_caps_gauge_and_faltering(realm_session: Session) -> None:
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    content = mint_content()
    tag = next(t for t in content.tags if t.id == MINT)
    smaller = tag.model_copy(
        update={
            "effects": tag.effects.model_copy(
                update={
                    "mint": tag.effects.mint.model_copy(update={"value_per_day": 24})
                    if tag.effects.mint
                    else None
                }
            )
        }
    )
    assert mint_demands((tag, smaller))[0].daily_milli == 120000
    realm.decay_stage = "faltering"
    realm.treasury = 120
    context = load_context(realm_session, realm, None, content)
    assert realm.treasury_band == "1"
    line = context.lines[0]
    assert line.value_measured and line.draw_per_day == 120000
    assert line.reserve == 360000 and line.cap == 1320000
    context.stores[BULLION] = 300000
    step_7_caps(context, realm, NOW, content)
    assert context.stores[BULLION] == 264000
    context.stores[BULLION] = 0
    step_4_realm_upkeep(context, realm, NOW + timedelta(hours=1), content)
    assert context.realm_due[line.key] == context.realm_unmet[line.key] == 5000
    step_8_gauges(context, realm, NOW, content)
    assert realm.gauge == pytest.approx(1 / 24)


@pytest.mark.parametrize("multiple,expected", [(1.2, 6), (0.99, 4), (0, 0)])
def test_coinage_per_tick_and_day(
    realm_session: Session, multiple: float, expected: int
) -> None:
    content = mint_content()
    content = replace(
        content,
        economy=content.economy.model_copy(update={"coinage_multiple": multiple}),
    )
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    context = load_context(realm_session, realm, None, content)
    context.stores[BULLION] = 24000
    for tick in range(1, 25):
        step_4_realm_upkeep(context, realm, NOW + timedelta(hours=tick), content)
        assert realm.treasury == tick * expected
    assert context.stores[BULLION] == 0
    assert sum(entry.amount for entry in context.ledger) == 24 * expected
    step_4_realm_upkeep(context, realm, NOW + timedelta(hours=25), content)
    assert realm.treasury == 24 * expected


def test_scarce_bullion_drains_treasury_until_mint_stops(
    realm_session: Session,
) -> None:
    from test_trade import seed

    character, realm = seed(realm_session)
    content = mint_content()
    realm.treasury = 40
    realm_session.add(
        Inventory(character_id=character.id, item_id=BULLION, quantity=100)
    )
    realm_session.flush()
    balances = []
    for tick in range(30):
        context = load_context(realm_session, realm, None, content)
        step_10_lines(context, realm, NOW, content)
        from app.services.stores import replace_lines

        replace_lines(realm_session, realm.id, context.lines)
        realm_session.flush()
        try:
            trade(realm_session, character, realm, content, BULLION, "sell", 1, 0)
        except HTTPException as error:
            assert isinstance(error.detail, dict)
            assert error.detail["error"]["code"] == "UNFUNDED_DEMAND"
            break
        context = load_context(realm_session, realm, None, content)
        step_4_realm_upkeep(context, realm, NOW + timedelta(hours=tick + 1), content)
        store = realm_session.get(RealmStore, (REALM, BULLION))
        assert store is not None
        store.quantity_milli = context.stores[BULLION]
        realm_session.flush()
        balances.append(realm.treasury)
    assert balances and all(
        b < a for a, b in zip([40, *balances], balances, strict=False)
    )
    before = realm.treasury
    step_4_realm_upkeep(context, realm, NOW + timedelta(days=2), content)
    assert realm.treasury == before


def test_seed_ledger_once_and_atomic_rollback(realm_session: Session) -> None:
    realm_session.execute(delete(RealmState))
    realm_session.commit()
    assert create_world(realm_session, CONTENT, NOW)
    assert not create_world(realm_session, CONTENT, NOW)
    assert realm_session.scalar(select(func.sum(GoldLedger.amount))) == sum(
        s.treasury for s in CONTENT.world_seed.realms
    )
    realm_session.rollback()
    assert realm_session.scalar(select(func.count()).select_from(GoldLedger)) == 0
    assert create_world(realm_session, CONTENT, NOW)


@pytest.mark.anyio
async def test_admin_economy_operator_only(
    estate_client: ApiFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, headers, _ = estate_client
    result = await client.get("/admin/economy", headers=headers)
    assert (
        result.status_code == 403
        and result.json()["error"]["code"] == "OPERATOR_REQUIRED"
    )
    with factory() as session:
        user_id = session.scalar(select(Player.auth_user_id))
    monkeypatch.setattr(config, "OPERATOR_AUTH_USER_IDS", frozenset({user_id}))
    result = await client.get("/admin/economy", headers=headers)
    assert result.status_code == 200
    assert result.json()["holders"] == {
        "wallets": 100,
        "treasuries": 0,
        "order_escrow": 0,
        "order_slots": 0,
    }
    assert result.json()["ledger"] == {"world_seed": 0}


@pytest.mark.anyio
@settings(
    max_examples=12,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    operations=st.lists(
        st.sampled_from(
            [
                "mint",
                "order_trade",
                "order_cancel",
                "buy",
                "sell",
                "gift",
                "build",
                "transform",
                "surrender",
                "estate_buy",
                "kickoff",
            ]
        ),
        max_size=20,
    )
)
async def test_random_gold_operations_match_ledger(
    estate_client: ApiFixture, operations: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, factory, headers, clock = estate_client
    content = mint_content()
    node = content.development_node("node.verdant_t1")
    content = replace(
        content,
        _nodes_by_id=MappingProxyType(
            {
                **content._nodes_by_id,
                node.id: node.model_copy(
                    update={"inherent_tags": (*node.inherent_tags, "access.fake")}
                ),
            }
        ),
    )
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "market": content.economy.market.model_copy(
                    update={"tax_burn_pct": 100}
                )
            }
        ),
    )
    forms = tuple(
        f.model_copy(
            update={"build_cost": BuildCost(gold=7), "upkeep": (), "production": ()}
        )
        for f in content.estate_forms
    )
    project = content.project("project.verdant_cardboard")
    project = project.model_copy(
        update={"kickoff": project.kickoff.model_copy(update={"gold": 11})}
    )
    content = replace(
        content,
        estate_forms=forms,
        _forms_by_id=MappingProxyType({f.id: f for f in forms}),
        _projects_by_id=MappingProxyType(
            {**content._projects_by_id, project.id: project}
        ),
    )
    original = app.state.content
    app.state.content = content
    try:
        with factory() as session:
            character = session.scalar(select(Character))
            assert character is not None
            home = session.get(Estate, character.home_estate_id)
            assert home is not None
            character.last_kickoff_at = None
            home.form_id = "form.camp"
            target = Estate(realm_id=REALM, form_id="form.fake_workshop")
            session.add(target)
            session.flush()
            target_id = target.id
            wallet = session.get(Currency, character.id)
            realm = session.get(RealmState, REALM)
            assert wallet is not None and realm is not None
            wallet.gold = 100000
            realm.treasury = 100000
            realm.last_tick_at = clock["now"]
            session.execute(delete(RealmProjectRun))
            for item in (BULLION, "item.fake_sprig"):
                row = session.get(Inventory, (character.id, item))
                if row is None:
                    session.add(
                        Inventory(character_id=character.id, item_id=item, quantity=100)
                    )
                else:
                    row.quantity = 100
                store = session.get(RealmStore, (REALM, item))
                if store is None:
                    session.add(
                        RealmStore(realm_id=REALM, item_id=item, quantity_milli=80000)
                    )
                else:
                    store.quantity_milli = 80000
            session.flush()
            context = load_context(session, realm, None, content)
            step_10_lines(context, realm, clock["now"], content)
            from app.services.stores import replace_lines

            replace_lines(session, realm.id, context.lines)
            session.commit()

        with factory() as session:
            user_id = session.scalar(select(Player.auth_user_id))
        monkeypatch.setattr(config, "OPERATOR_AUTH_USER_IDS", frozenset({user_id}))

        async def net() -> int:
            report = await client.get("/admin/economy", headers=headers)
            assert report.status_code == 200
            data = report.json()
            return int(sum(data["holders"].values()) - sum(data["ledger"].values()))

        baseline = await net()
        # Exercise every gold flow before the random interleavings.
        prefix = [
            "transform",
            "build",
            "surrender",
            "estate_buy",
            "surrender",
            "kickoff",
            "sell",
            "buy",
            "gift",
            "mint",
            "order_trade",
            "order_cancel",
        ]
        for index, operation in enumerate([*prefix, *operations]):
            if operation == "mint":
                clock["now"] += timedelta(hours=1)
                with factory.begin() as session:
                    realm = session.get(RealmState, REALM)
                    assert realm is not None
                    resolve_realm(session, realm, clock["now"], content)
            elif operation in ("order_trade", "order_cancel"):
                order_ids = []
                for side in ["sell", "buy"] if operation == "order_trade" else ["buy"]:
                    result = await client.post(
                        "/market/orders",
                        headers=headers,
                        json={
                            "side": side,
                            "item_id": BULLION,
                            "quantity": 1,
                            "unit_price": 3,
                        },
                    )
                    assert result.status_code == 201, result.text
                    order_ids.append(result.json()["order"]["id"])
                    assert await net() == baseline
                for order_id in order_ids:
                    if operation == "order_cancel":
                        result = await client.post(
                            f"/market/orders/{order_id}/cancel", headers=headers
                        )
                        assert result.status_code == 200
                        assert await net() == baseline
                    result = await client.post(
                        f"/market/orders/{order_id}/collect", headers=headers
                    )
                    assert result.status_code == 200
            else:
                routes = {
                    "transform": (
                        "/estates/me/transform",
                        {"form_id": "form.homestead"},
                    ),
                    "build": ("/estates/build", {"form_id": "form.fake_workshop"}),
                    "surrender": ("/estates/me/surrender", {"donate": False}),
                    "estate_buy": (f"/estates/{target_id}/buy", {}),
                    "kickoff": (f"/realms/{REALM}/projects/{project.id}/kickoff", {}),
                    "gift": (f"/realms/{REALM}/treasury/gift", {"gold": 1}),
                    "buy": (
                        f"/realms/{REALM}/market/trade",
                        {
                            "item_id": BULLION,
                            "side": "buy",
                            "quantity": 1,
                            "limit_gold": 100,
                        },
                    ),
                    "sell": (
                        f"/realms/{REALM}/market/trade",
                        {
                            "item_id": BULLION,
                            "side": "sell",
                            "quantity": 1,
                            "limit_gold": 0,
                        },
                    ),
                }
                url, body = routes[operation]
                result = await client.post(url, headers=headers, json=body)
                assert result.status_code in (200, 204, 409), result.text
                if index < len(prefix):
                    assert result.status_code in (200, 204), result.text
            assert await net() == baseline
    finally:
        app.state.content = original


@pytest.mark.parametrize("ticks", [2, 72])
def test_mint_catchup_batches_ledger_and_is_idempotent(
    realm_session: Session, ticks: int
) -> None:
    """Ledger insertion stays one batched write across the full catch-up window."""
    from sqlalchemy import event
    from sqlalchemy.engine import Connection, ExecutionContext

    content = mint_content()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    realm_session.add(
        RealmStore(realm_id=REALM, item_id=BULLION, quantity_milli=100000)
    )
    realm_session.commit()
    statements: list[str] = []

    def record(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: ExecutionContext,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    engine = realm_session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        resolve_realm(realm_session, realm, NOW + timedelta(hours=ticks), content)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert len([s for s in statements if "INSERT INTO gold_ledger" in s]) == 1
    metrics_writes = [s for s in statements if "INSERT INTO metric_deltas" in s]
    assert len(metrics_writes) == 1  # One telemetry batch, regardless of tick count.
    gameplay_statements = [s for s in statements if s not in metrics_writes]
    assert len(gameplay_statements) <= 17  # Original gameplay query budget.
    assert realm.treasury == ticks * 6
    assert realm_session.scalar(select(func.sum(GoldLedger.amount))) == ticks * 6
    before = len(list(realm_session.scalars(select(GoldLedger))))
    resolve_realm(realm_session, realm, NOW + timedelta(hours=ticks), content)
    assert len(list(realm_session.scalars(select(GoldLedger)))) == before
    realm_session.rollback()
    assert realm_session.scalar(select(func.count()).select_from(GoldLedger)) == 0


def test_postgres_concurrent_mint_resolves_once(realm_session: Session) -> None:
    """A resolver waiting for the realm lock cannot coin the same tick twice."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from test_estates import _wait_for_postgres_blocker

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("Concurrent row locking requires PostgreSQL")
    realm_session.add(RealmStore(realm_id=REALM, item_id=BULLION, quantity_milli=1000))
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    attempting = Event()
    worker_pid: list[int] = []

    def resolve_once() -> None:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            worker_pid.append(
                session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            attempting.set()
            realm = session.scalar(
                select(RealmState).where(RealmState.id == REALM).with_for_update()
            )
            resolve_realm(session, realm, NOW + timedelta(hours=1), mint_content())
            session.commit()

    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        blocker_pid = first.execute(text("SELECT pg_backend_pid()")).scalar_one()
        realm = first.scalar(
            select(RealmState).where(RealmState.id == REALM).with_for_update()
        )
        resolve_realm(first, realm, NOW + timedelta(hours=1), mint_content())
        future = pool.submit(resolve_once)
        try:
            assert attempting.wait(5)
            _wait_for_postgres_blocker(factory, worker_pid[0], blocker_pid)
        finally:
            first.commit()
        future.result(timeout=10)
    realm_session.expire_all()
    realm = realm_session.get(RealmState, REALM)
    assert realm is not None and realm.treasury == 6
    assert realm_session.scalar(select(func.sum(GoldLedger.amount))) == 6
    assert realm_session.scalar(select(func.count()).select_from(GoldLedger)) == 1


def test_coinage_fractional_bullion_and_value_remainder() -> None:
    """Mixed reference prices cannot overdraw appetite or round gold upward."""
    from app.content.schemas import Selector
    from app.engine.realm_ticks import coinage, consume_value

    other = CONTENT.item(BULLION).model_copy(
        update={"id": "item.other_bullion", "reference_price": 7}
    )
    content = CONTENT.with_overrides(items=[other])
    stock = {BULLION: 1, other.id: 1000}
    paid = consume_value(
        stock, Selector.model_validate({"class": "bullion"}), 5000, content
    )
    assert paid == 4996
    assert stock == {BULLION: 0, other.id: 287}
    assert coinage(paid, 1.2) == 5


def test_wallet_retains_64_bit_gold(realm_session: Session) -> None:
    """Wallets accept the same 64-bit range as realm treasuries."""
    from test_trade import seed

    character, _ = seed(realm_session)
    wallet = realm_session.get(Currency, character.id)
    assert wallet is not None
    wallet.gold = 2**40
    realm_session.commit()
    realm_session.expire_all()
    assert realm_session.scalar(select(Currency.gold)) == 2**40
