"""Random successful interleavings check every physical holder after every step."""

from collections import Counter

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from test_estates import _token
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_gold import BULLION, REALM
from test_realms import NOW
from test_travel import ApiFixture
from world_accounting import GoodsAccounting, goods
from world_helpers import create_empty_world
from world_scenario import (
    OPERATIONS,
    OTHER_REALM,
    PLANK,
    SPRIG,
    WorldScenario,
    world_content,
)

from app import config
from app.db import Base
from app.main import app
from app.models import (
    Character,
    Currency,
    Estate,
    GoldLedger,
    Inventory,
    Player,
    RealmShipment,
    RealmState,
    RealmStore,
)
from app.services.realm_ticks import load_context, step_10_lines
from app.services.stores import replace_lines


async def setup_scenario(
    fixture: ApiFixture, audit: GoodsAccounting, monkeypatch: pytest.MonkeyPatch
) -> WorldScenario:
    """Start a fresh world with two independently authenticated owners."""
    client, factory, headers, clock = fixture
    content = world_content()
    monkeypatch.setattr(app.state, "content", content)
    clock["now"] = NOW
    with factory() as session:
        engine = session.get_bind()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with factory() as session:
        create_empty_world(session, content, NOW)
    partner_headers = {"Authorization": f"Bearer {_token()}"}
    characters = []
    for name, realm_id, auth in (
        ("World Buyer", REALM, headers),
        ("World Seller", OTHER_REALM, partner_headers),
    ):
        response = await client.post(
            "/characters", headers=auth, json={"name": name, "realm_id": realm_id}
        )
        assert response.status_code == 201, response.text
        with factory() as session:
            identifier = session.scalar(
                select(Character.id).where(Character.name == name)
            )
            assert identifier is not None
            characters.append(identifier)
    with factory() as session:
        for identifier in characters:
            wallet = session.get(Currency, identifier)
            assert wallet is not None
            wallet.gold = 1000000
            for item in (
                BULLION,
                SPRIG,
                PLANK,
                "item.fake_cape",
                "item.fake_food",
                "item.fake_ammo",
            ):
                session.add(
                    Inventory(character_id=identifier, item_id=item, quantity=10000)
                )
        for realm in session.scalars(select(RealmState)):
            realm.treasury = 1000000
            session.add(Estate(realm_id=realm.id, form_id="form.fake_workshop"))
        for realm_id, item, amount in (
            (REALM, SPRIG, 80000),
            (REALM, BULLION, 800000),
            (REALM, PLANK, 10**9),
            (OTHER_REALM, SPRIG, 100000),
        ):
            session.add(
                RealmStore(realm_id=realm_id, item_id=item, quantity_milli=amount)
            )
        session.flush()
        for realm in session.scalars(select(RealmState)):
            context = load_context(session, realm, None, content)
            step_10_lines(context, realm, NOW, content)
            replace_lines(session, realm.id, context.lines)
        user_id = session.scalar(
            select(Player.auth_user_id)
            .join(Character)
            .where(Character.id == characters[0])
        )
        session.commit()
    monkeypatch.setattr(config, "OPERATOR_AUTH_USER_IDS", frozenset({str(user_id)}))
    scenario = WorldScenario(
        client,
        factory,
        (headers, partner_headers),
        clock,
        content,
        audit,
        (characters[0], characters[1]),
    )
    with factory() as session:
        scenario.baseline_goods = goods(session)
    scenario.baseline_gold = await scenario.net()
    return scenario


@pytest.mark.anyio
@settings(
    max_examples=8,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    operations=st.tuples(
        st.permutations(OPERATIONS),
        st.lists(st.sampled_from(OPERATIONS), min_size=2, max_size=4),
    ).map(lambda parts: [*parts[0], *parts[1]])
)
async def test_random_world_operations_conserve_goods_and_gold(
    estate_client: ApiFixture,
    operations: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required intents succeed outside the prefix, including repeated operations."""
    success_tally: Counter[str] = Counter()
    # Scope observers to one example so Hypothesis never nests earlier spies.
    with monkeypatch.context() as scoped:
        audit = GoodsAccounting()
        audit.install(scoped)
        scenario = await setup_scenario(estate_client, audit, scoped)
        prefix = (
            "tick",
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
            "tick",
            "order_trade",
            "open_buy",
            "open_sell",
            "cancel",
            "collect",
            "contribute",
            "caravan",
            "arrive",
            "action",
            "expiry",
            "purge",
        )
        for operation in prefix:
            await scenario.run(operation)
        for operation in operations:
            await scenario.run(operation)
            success_tally[operation] += 1
        # Keep the specification independent of the generator: deleting an
        # operation from OPERATIONS must not silently delete its coverage check.
        required = {
            "guest_purge",
            "exploration",
            "key_trade",
            "key_cancel",
            "key_listing_invalidate",
            "key_use",
            "key_delete",
            "key_invalidate",
            "utility",
            "belt",
            "equip",
            "unequip",
            "buy",
            "sell",
            "gift",
            "kickoff",
            "contribute",
            "larder",
            "build",
            "estate_buy",
            "surrender",
            "caravan",
            "arrive",
            "order_trade",
            "open_buy",
            "open_sell",
            "collect",
            "cancel",
            "tick",
            "expiry",
            "purge",
            "action",
            "transform",
        }
        missing = required - {op for op, count in success_tally.items() if count > 0}
        assert not missing, (missing, success_tally)
        for cause in (
            "guest_purge",
            "discovery",
            "instance_delete",
            "key_outputs",
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
        with scenario.factory() as session:
            for cause in ("mint", "tax_burn", "caravan_fee_burn"):
                assert (
                    session.scalar(
                        select(GoldLedger.id).where(
                            GoldLedger.cause == cause, GoldLedger.amount != 0
                        )
                    )
                    is not None
                ), cause
            assert any(
                shipment.quantity_sent > shipment.quantity_arriving
                for shipment in session.scalars(select(RealmShipment))
            )
