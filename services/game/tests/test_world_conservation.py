"""Real world transfers and independently counted goods sources and sinks."""

import uuid
from dataclasses import replace
from datetime import datetime, timedelta
from types import MappingProxyType

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_gold import BULLION, REALM, mint_content
from test_travel import ApiFixture
from world_accounting import GoodsAccounting, goods

from app import config
from app.content.loader import ContentIndex
from app.content.schemas import (
    ActionInput,
    BuildCost,
    ProductionItem,
    Selector,
    TagUpkeep,
)
from app.main import app
from app.models import (
    Character,
    Currency,
    Estate,
    EstateLarder,
    GoldLedger,
    Inventory,
    MarketMatch,
    MarketOrder,
    Player,
    RealmContribution,
    RealmProjectRun,
    RealmShipment,
    RealmState,
    RealmStore,
    WorldState,
)
from app.services.caravans import run_caravan_pass
from app.services.market_lifecycle import run_market_lifecycle
from app.services.realm_ticks import (
    load_context,
    step_10_lines,
)
from app.services.realms import resolve_realm
from app.services.stores import replace_lines


def world_content() -> ContentIndex:
    """Exercise authored sources, sinks and access with synthetic test content."""
    content = mint_content()
    node = content.development_node("node.verdant_t1")
    content = replace(
        content,
        _nodes_by_id=MappingProxyType(
            {
                **content._nodes_by_id,
                node.id: node.model_copy(
                    update={
                        "inherent_tags": (*node.inherent_tags, "access.fake"),
                        "upkeep": (
                            TagUpkeep(
                                selector=Selector(item="item.fake_sprig"), per_day=12
                            ),
                        ),
                    }
                ),
            }
        ),
    )
    content = replace(
        content,
        economy=content.economy.model_copy(
            update={
                "caravan": content.economy.caravan.model_copy(
                    update={"fee_burn_pct": 100}
                ),
                "market": content.economy.market.model_copy(
                    update={"tax_burn_pct": 100}
                ),
            }
        ),
    )
    content = replace(content, caps=content.caps.model_copy(update={"order_slots": 64}))
    content = content.with_overrides(
        items=[
            content.item("item.fake_sprig").model_copy(
                update={"spoilage_pct_per_day": 12, "warehouse_cap": 100}
            )
        ]
    )
    content = replace(
        content,
        map=content.map.model_copy(
            update={
                "edges": tuple(
                    edge.model_copy(update={"base_loss_pct": 25})
                    for edge in content.map.edges
                )
            }
        ),
        tags=tuple(
            tag.model_copy(
                update={
                    "effects": tag.effects.model_copy(update={"caravan_access": True})
                }
            )
            for tag in content.tags
        ),
    )
    forms = tuple(
        f.model_copy(
            update={
                "build_cost": BuildCost(
                    gold=7,
                    goods=(
                        ActionInput(
                            selector=Selector(item="item.fake_sprig"), quantity=2
                        ),
                    ),
                ),
                "upkeep": (
                    TagUpkeep(selector=Selector(item="item.fake_sprig"), per_day=1),
                )
                if f.mobility == "fixed"
                else (),
                "production": (ProductionItem(item_id="item.fake_sprig", per_day=2),),
            }
        )
        for f in content.estate_forms
    )
    project = content.project("project.verdant_cardboard")
    project = project.model_copy(
        update={
            "kickoff": project.kickoff.model_copy(update={"gold": 11}),
            "cost": (
                ActionInput(selector=Selector(item="item.fake_sprig"), quantity=100),
            ),
        }
    )
    content = replace(
        content,
        estate_forms=forms,
        _forms_by_id=MappingProxyType({f.id: f for f in forms}),
        _projects_by_id=MappingProxyType(
            {**content._projects_by_id, project.id: project}
        ),
    )
    return content


def seed_world(
    factory: sessionmaker[Session], content: ContentIndex, now: datetime
) -> uuid.UUID:
    """Reset physical holders before each Hypothesis example and take no credit."""
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
        realm.last_tick_at = now
        # Hypothesis reuses the fixture: reset all physical/audit holders.
        session.execute(delete(MarketMatch))
        session.execute(delete(MarketOrder))
        session.execute(delete(RealmContribution))
        session.execute(delete(RealmProjectRun))
        session.execute(delete(RealmShipment))
        session.execute(delete(EstateLarder))
        if session.get(WorldState, 1) is None:
            session.add(
                WorldState(
                    id=1,
                    seeded_at=now,
                    last_caravan_pass=now,
                    content_version="test",
                )
            )
        seller = session.get(RealmState, "realm.ashen_reach")
        assert seller is not None
        seller.last_tick_at = now
        if (
            session.scalar(select(Estate.id).where(Estate.realm_id == seller.id))
            is None
        ):
            session.add(Estate(realm_id=seller.id, form_id="form.fake_workshop"))
        seller_store = session.get(RealmStore, (seller.id, "item.fake_sprig"))
        if seller_store is None:
            session.add(
                RealmStore(
                    realm_id=seller.id,
                    item_id="item.fake_sprig",
                    quantity_milli=100000,
                )
            )
        else:
            seller_store.quantity_milli = 100000
        cap_store = session.get(RealmStore, (REALM, "item.fake_plank"))
        if cap_store is None:
            session.add(
                RealmStore(
                    realm_id=REALM, item_id="item.fake_plank", quantity_milli=10**9
                )
            )
        else:
            cap_store.quantity_milli = 10**9
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
        step_10_lines(context, realm, now, content)
        replace_lines(session, realm.id, context.lines)
        session.commit()

    return target_id


def world_routes(
    target_id: uuid.UUID, project_id: str
) -> dict[str, tuple[str, dict[str, object]]]:
    """Map generated intents to real public mutation endpoints."""
    return {
        "larder": (
            "/estates/me/larder",
            {"item_id": "item.fake_sprig", "quantity": 1},
        ),
        "contribute": (
            f"/realms/{REALM}/project/contribute",
            {"item_id": "item.fake_sprig", "quantity": 1},
        ),
        "transform": (
            "/estates/me/transform",
            {"form_id": "form.homestead"},
        ),
        "build": ("/estates/build", {"form_id": "form.fake_workshop"}),
        "surrender": ("/estates/me/surrender", {"donate": False}),
        "estate_buy": (f"/estates/{target_id}/buy", {}),
        "kickoff": (f"/realms/{REALM}/projects/{project_id}/kickoff", {}),
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


@pytest.mark.anyio
@settings(
    max_examples=20,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@example(operations=[])
@given(
    operations=st.lists(
        st.sampled_from(
            [
                "mint",
                "larder",
                "caravan",
                "contribute",
                "lifecycle",
                "open_buy",
                "open_sell",
                "collect",
                "cancel",
                "action",
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
        max_size=30,
    )
)
async def test_random_world_operations_conserve_goods_and_gold(
    estate_client: ApiFixture, operations: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every accepted transfer preserves the independent world accounting."""
    client, factory, headers, clock = estate_client
    content = world_content()
    audit = GoodsAccounting()
    audit.install(monkeypatch)
    original = app.state.content
    app.state.content = content
    try:
        target_id = seed_world(factory, content, clock["now"])

        with factory() as session:
            user_id = session.scalar(select(Player.auth_user_id))
        monkeypatch.setattr(config, "OPERATOR_AUTH_USER_IDS", frozenset({str(user_id)}))

        async def net() -> int:
            report = await client.get("/admin/economy", headers=headers)
            assert report.status_code == 200
            data = report.json()
            return int(sum(data["holders"].values()) - sum(data["ledger"].values()))

        baseline = await net()
        with factory() as session:
            baseline_goods = goods(session)

        def check_goods() -> None:
            with factory() as session:
                expected = audit.expected(baseline_goods)
                for shipment in session.scalars(select(RealmShipment)):
                    expected[shipment.item_id] -= 1000 * (
                        shipment.quantity_sent - shipment.quantity_arriving
                    )
                assert goods(session) == expected, audit.changes

        # Exercise every gold flow before the random interleavings.
        prefix = [
            "transform",
            "build",
            "larder",
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
            "contribute",
            "caravan",
            "arrive",
            "open_buy",
            "open_sell",
            "cancel",
            "collect",
            "action",
            "lifecycle",
        ]
        for index, operation in enumerate([*prefix, *operations]):
            if operation in ("open_buy", "open_sell"):
                result = await client.post(
                    "/market/orders",
                    headers=headers,
                    json={
                        "side": "buy" if operation == "open_buy" else "sell",
                        "item_id": BULLION,
                        "quantity": 1,
                        "unit_price": 1 if operation == "open_buy" else 20,
                    },
                )
                assert result.status_code in (201, 409), result.text
            elif operation in ("collect", "cancel"):
                with factory() as session:
                    ids = list(
                        session.scalars(
                            select(MarketOrder.id).where(MarketOrder.status != "closed")
                        )
                    )
                for order_id in ids:
                    result = await client.post(
                        f"/market/orders/{order_id}/{operation}", headers=headers
                    )
                    assert result.status_code == 200, result.text
                    assert await net() == baseline
                    check_goods()
            elif operation == "arrive":
                clock["now"] += timedelta(hours=24)
                with factory() as session:
                    for realm in session.scalars(
                        select(RealmState).order_by(RealmState.id)
                    ):
                        resolve_realm(session, realm, clock["now"], content)
                    session.commit()
                with factory() as session:
                    assert (
                        session.scalar(
                            select(RealmShipment.id).where(
                                RealmShipment.status == "arrived"
                            )
                        )
                        is not None
                    )
            elif operation == "lifecycle":
                run_market_lifecycle(factory, content, clock["now"])
            elif operation == "caravan":
                clock["now"] += timedelta(hours=6)
                with factory() as session:
                    run_caravan_pass(session, content, clock["now"])
                    session.commit()
                    if index < len(prefix):
                        assert session.scalar(select(RealmShipment.id)) is not None
            elif operation == "action":
                # Deterministic refining recipe: two sprigs -> one plank.
                result = await client.post(
                    "/actions/start",
                    headers=headers,
                    json={"action_id": "refining.fake_plank"},
                )
                assert result.status_code == 200, result.text
                clock["now"] += timedelta(milliseconds=4500)
                result = await client.post("/actions/stop", headers=headers)
                assert result.status_code == 200, result.text
                cycles = result.json()["since_last"]["cycles_completed"]
                assert cycles == 1
                audit.add("actions", "item.fake_sprig", -2000 * cycles)
                audit.add("actions", "item.fake_plank", 1000 * cycles)
            elif operation == "mint":
                clock["now"] += timedelta(hours=1)
                with factory.begin() as session:
                    mint_realm = session.get(RealmState, REALM)
                    assert mint_realm is not None
                    resolve_realm(session, mint_realm, clock["now"], content)
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
                    check_goods()
                for order_id in order_ids:
                    if operation == "order_cancel":
                        result = await client.post(
                            f"/market/orders/{order_id}/cancel", headers=headers
                        )
                        assert result.status_code == 200
                        assert await net() == baseline
                    check_goods()
                    result = await client.post(
                        f"/market/orders/{order_id}/collect", headers=headers
                    )
                    assert result.status_code == 200
            else:
                url, body = world_routes(target_id, "project.verdant_cardboard")[
                    operation
                ]
                result = await client.post(url, headers=headers, json=body)
                if result.status_code == 200:
                    if operation in ("build", "transform"):
                        audit.add("construction", "item.fake_sprig", -2000)
                    elif operation == "contribute":
                        audit.add("projects", "item.fake_sprig", -1000)
                assert result.status_code in (200, 204, 409), result.text
                if index < len(prefix):
                    assert result.status_code in (200, 204), result.text
            assert await net() == baseline
            check_goods()
            if index == len(prefix) - 1:
                for cause in (
                    "production",
                    "step_2_larder_upkeep",
                    "step_3_estate_upkeep",
                    "step_4_realm_upkeep",
                    "mint_bullion",
                    "spoilage",
                    "cap",
                    "construction",
                    "projects",
                    "actions",
                ):
                    assert any(audit.changes[cause].values()), cause
                with factory() as session:
                    for cause in ("tax_burn", "caravan_fee_burn"):
                        assert (
                            session.scalar(
                                select(GoldLedger.id).where(
                                    GoldLedger.cause == cause, GoldLedger.amount < 0
                                )
                            )
                            is not None
                        )
                    assert any(
                        shipment.quantity_sent > shipment.quantity_arriving
                        for shipment in session.scalars(select(RealmShipment))
                    )
    finally:
        app.state.content = original
        monkeypatch.undo()
