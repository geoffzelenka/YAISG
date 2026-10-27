"""Integrated pricing, funding and public visibility contracts."""

from dataclasses import replace
from decimal import Decimal as D

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.orm import Session
from test_estates import anyio_backend as anyio_backend
from test_estates import estate_client as estate_client
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from test_travel import ApiFixture

from app.content.schemas import MarketConfig, Selector
from app.engine.market import (
    QuoteContext,
    allocate_budgets,
    integral,
    multiplier,
    quote,
    total,
    treasury_band,
)
from app.engine.stores import Line
from app.models import RealmState
from app.services.realm_ticks import load_context, step_10_lines


def context(stock: int = 100) -> QuoteContext:
    """Use the specification's example with ample funding."""
    return QuoteContext(
        10, 1, D(stock), D(1000), D(0), MarketConfig(), D(25), 100000, 100000, stock
    )


@pytest.mark.parametrize(
    ("stock", "expected"), [(0, 2.10), (250, 1.08), (500, 0.55), (1000, 0.33)]
)
def test_curve_values(stock: int, expected: float) -> None:
    assert float(multiplier(D(stock), D(1000), MarketConfig())) == pytest.approx(
        expected, abs=0.01
    )


def test_integrated_example() -> None:
    assert quote(context(), "example", "sell", 500).gold == 4439


@given(st.integers(1, 900))
def test_margin_round_trip_and_unit_integral(quantity: int) -> None:
    ctx = context(1000)
    buy = total(ctx, "buy", quantity)
    after = replace(ctx, stock=ctx.stock - quantity)
    sell = total(after, "sell", quantity)
    raw = D(10) * integral(after.stock, ctx.stock, ctx.cap, ctx.settings)
    ask = raw * D("1.25")
    assert buy >= ask >= raw >= sell
    assert D(buy) - ask < 1
    assert raw - sell < 1
    assert buy > sell
    pieces = sum(
        (
            integral(after.stock + n, after.stock + n + 1, ctx.cap, ctx.settings)
            for n in range(quantity)
        ),
        D(0),
    )
    assert abs(pieces - integral(after.stock, ctx.stock, ctx.cap, ctx.settings)) < D(
        "1e-23"
    )


@given(st.integers(0, 100000))
def test_budget_conservation_and_bisection(treasury: int) -> None:
    item = CONTENT.items[0]
    lines = tuple(
        Line(str(n), Selector(item=item.id), 1000, 3000, 100000, n * 1000, False)
        for n in range(3)
    )
    funded = allocate_budgets(lines, treasury, CONTENT)
    assert sum(line.budget_gold for line in funded) <= treasury
    ctx = replace(context(), budget=treasury, treasury=treasury)
    maximum = quote(ctx, item.id, "sell", 1).max_quantity
    assert total(ctx, "sell", maximum) <= treasury
    if treasury == 0:
        assert maximum == 0
    elif maximum < 900:
        assert total(ctx, "sell", maximum + 1) > treasury


def test_band_hysteresis() -> None:
    settings = MarketConfig()
    assert treasury_band(D("1.01"), "0", settings) == "0"
    assert treasury_band(D("1.11"), "0", settings) == "1"
    assert treasury_band(D(".99"), "1", settings) == "1"
    assert treasury_band(D(".89"), "1", settings) == "0"


def test_step_ten_allocates_budgets_and_band(realm_session: Session) -> None:
    realm = realm_session.get(RealmState, "realm.verdant_vale")
    assert realm is not None
    realm.treasury = 12345
    ctx = load_context(realm_session, realm, None, CONTENT)
    step_10_lines(ctx, realm, NOW, CONTENT)
    assert sum(line.budget_gold for line in ctx.lines) <= realm.treasury
    assert realm.treasury_band is not None


@pytest.mark.anyio
async def test_market_visibility_quotes_and_private_treasury(
    estate_client: ApiFixture,
) -> None:
    client, factory, headers, _ = estate_client
    from app.models import Estate

    with factory() as session:
        session.add(Estate(realm_id="realm.verdant_vale", form_id="form.fake_workshop"))
        session.commit()
    realm = "realm.verdant_vale"
    for path in [
        "/map",
        "/realms",
        f"/realms/{realm}",
        f"/realms/{realm}/estates",
        f"/realms/{realm}/market",
    ]:
        response = await client.get(path, headers=headers)
        assert response.status_code == 200, response.text

        def check(value: object) -> None:
            if isinstance(value, dict):
                assert "treasury" not in value
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        check(response.json())
    market = (await client.get(f"/realms/{realm}/market", headers=headers)).json()
    assert market["lines"]
    item = market["lines"][0]["members"][0]["item_id"]
    response = await client.get(
        f"/realms/{realm}/market/quote",
        headers=headers,
        params={"item_id": item, "side": "sell", "quantity": 1},
    )
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"gold", "max_quantity"}


def test_postgres_market_resolve_retains_realm_lock(realm_session: Session) -> None:
    """Quotes read state under the same transaction's PostgreSQL realm lock."""
    from sqlalchemy import select
    from sqlalchemy.exc import DBAPIError

    from app.services.market import market_view
    from app.services.realms import finalize_realm

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    realm = finalize_realm(realm_session, "realm.verdant_vale", NOW, CONTENT)
    assert realm is not None
    market_view(realm_session, realm, CONTENT)
    with Session(realm_session.get_bind()) as competing:
        with pytest.raises(DBAPIError):
            competing.scalar(
                select(RealmState)
                .where(RealmState.id == realm.id)
                .with_for_update(nowait=True)
            )
        competing.rollback()


def test_weighted_quotes_and_physical_limits() -> None:
    ctx = replace(context(), reference_price=10, w=10)
    result = quote(ctx, "weighted", "sell", 500)
    assert result.max_quantity == 90
    assert result.gold == total(ctx, "sell", 90)
    ctx = replace(context(500), reserve=D(450), available=10)
    assert quote(ctx, "limited", "buy", 100).max_quantity == 10
    assert (
        quote(replace(ctx, treasury=0, budget=0), "empty", "sell", 1).max_quantity == 0
    )


def test_reads_preserve_spent_budgets_and_estate_ask(realm_session: Session) -> None:
    """Reads do not make newly arrived gold spendable before the next tick."""
    from app.engine.estates import estate_value
    from app.models import Estate, RealmLine, RealmStore
    from app.services.estates import persisted_estate_value
    from app.services.market import market_contexts, spot_ask
    from app.services.stores import recompute_lines

    content = CONTENT.with_overrides(
        items=[
            CONTENT.item("item.fake_sprig").model_copy(update={"reference_price": 10})
        ]
    )
    realm = realm_session.get(RealmState, "realm.verdant_vale")
    assert realm is not None
    realm.treasury = 10000
    estate = Estate(realm_id=realm.id, form_id="form.fake_workshop")
    realm_session.add(estate)
    realm_session.add(
        RealmStore(realm_id=realm.id, item_id="item.fake_sprig", quantity_milli=10000)
    )
    realm_session.flush()
    recompute_lines(realm_session, realm, content)
    realm_session.flush()
    rows = list(realm_session.query(RealmLine).filter_by(realm_id=realm.id))
    assert rows
    for row in rows:
        row.budget_gold = 0
    realm_session.flush()
    realm.treasury += 50000
    refreshed = recompute_lines(realm_session, realm, content)
    assert all(row.budget_gold == 0 for row in refreshed)
    realm_session.flush()
    contexts = market_contexts(realm_session, realm, content)
    assert spot_ask(contexts["item.fake_sprig"][1]) is not None
    expected = estate_value(
        estate.form_id,
        [],
        realm.id,
        content,
        lambda realm_id, item_id: spot_ask(contexts[item_id][1]),
    )
    assert persisted_estate_value(realm_session, estate, content) == expected
    assert expected.value < estate_value(estate.form_id, [], realm.id, content).value


def test_all_realm_and_map_response_schemas_hide_treasury() -> None:
    """Follow schema references for every realm/map endpoint response."""
    from app.main import app

    schema = app.openapi()
    seen: set[str] = set()

    def check(value: object) -> None:
        if isinstance(value, dict):
            properties = value.get("properties", {})
            assert "treasury" not in properties
            reference = value.get("$ref")
            if isinstance(reference, str) and reference not in seen:
                seen.add(reference)
                check(schema["components"]["schemas"][reference.rsplit("/", 1)[1]])
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    for path, methods in schema["paths"].items():
        if path == "/map" or path.startswith("/realms"):
            for operation in methods.values():
                check(operation.get("responses", {}))


def test_quote_precision_is_independent_of_decimal_context() -> None:
    """Ambient rounding cannot change either total gold or tradable quantity."""
    from decimal import localcontext

    ctx = context(101)
    expected = quote(ctx, "example", "sell", 500)
    with localcontext() as precision:
        precision.prec = 2
        assert quote(ctx, "example", "sell", 500) == expected
