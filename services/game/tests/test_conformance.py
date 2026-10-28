"""Final public-surface and operational retention regressions."""

import re

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock
from test_actions import action_client as action_client
from test_actions import anyio_backend as anyio_backend
from test_hardening import totals
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.db import Base
from app.main import app
from app.models import MetricDelta
from app.services.market_lifecycle import run_market_lifecycle
from app.services.metrics import compact_deltas, record


def test_consolidated_action_routes_replace_aliases() -> None:
    """Only the four specified action operations are advertised."""
    paths = app.openapi()["paths"]
    for path, method in (
        ("/actions/available", "get"),
        ("/actions/start", "post"),
        ("/actions/poll", "get"),
        ("/actions/stop", "post"),
    ):
        assert method in paths[path]
    assert not any("/characters/me/action" in path for path in paths)
    assert not any("/relocate" in path for path in paths)


@pytest.mark.anyio
async def test_removed_action_aliases_return_not_found(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Old clients cannot mutate or read through retired action aliases."""
    client, _, _, headers = action_client
    for method, path in (
        ("GET", "/characters/me/actions/available"),
        ("GET", "/characters/me/action"),
        ("POST", "/characters/me/action"),
        ("DELETE", "/characters/me/action"),
    ):
        assert (await client.request(method, path, headers=headers)).status_code == 404


def test_metric_compaction_preserves_totals_rollback_and_future_events(
    realm_session: Session,
) -> None:
    """Bounded compaction preserves counters and remains atomic with rollback."""
    for _ in range(6):
        record(realm_session, matches=2, tax_gold=3)
        realm_session.flush()
    realm_session.commit()
    before = totals(realm_session)
    count = realm_session.scalar(select(func.count()).select_from(MetricDelta))
    assert count == 12
    assert compact_deltas(realm_session, batch_size=5) == 4
    assert totals(realm_session) == before
    realm_session.rollback()
    assert realm_session.scalar(select(func.count()).select_from(MetricDelta)) == count
    assert totals(realm_session) == before
    assert compact_deltas(realm_session) == 10
    realm_session.commit()
    assert compact_deltas(realm_session) == 0
    record(realm_session, matches=1)
    realm_session.commit()
    assert totals(realm_session) == {"matches": 13, "tax_gold": 18}
    with pytest.raises(ValueError, match="at least two"):
        compact_deltas(realm_session, batch_size=1)


@pytest.mark.anyio
async def test_lifecycle_compacts_committed_metrics(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """The existing periodic lifecycle driver actually performs compaction."""
    _, factory, _, _ = action_client
    with factory() as session:
        for _ in range(3):
            record(session, matches=1)
            session.flush()
        session.commit()
    assert run_market_lifecycle(factory, CONTENT, NOW)
    with factory() as session:
        assert totals(session)["matches"] == 3
        assert (
            session.scalar(
                select(func.count())
                .select_from(MetricDelta)
                .where(MetricDelta.name == "matches")
            )
            == 1
        )


@pytest.mark.anyio
async def test_postgres_metric_compaction_skips_locked_rows_and_keeps_new_events(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Concurrent maintenance skips locked samples; new gameplay inserts survive."""
    _, factory, _, _ = action_client
    with factory() as first, factory() as second:
        if first.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL row locking required")
        for _ in range(4):
            record(first, matches=2)
            first.flush()
        first.commit()
        first.scalar(select(MetricDelta).with_for_update().limit(1))
        assert compact_deltas(second) == 2
        second.commit()
        record(second, matches=3)
        second.commit()
        first.rollback()
        assert compact_deltas(first) == 2
        first.commit()
        assert totals(first)["matches"] == 11


def test_design_tables_and_endpoints_exist_without_retired_schema() -> None:
    """The consolidated design inventory is present, including rarely used routes."""
    expected_tables = {
        "players",
        "characters",
        "character_skills",
        "active_actions",
        "inventories",
        "currency",
        "reward_log",
        "character_equipment",
        "character_belt",
        "character_buffs",
        "item_instances",
        "key_listings",
        "estates",
        "estate_upgrades",
        "estate_ownership_history",
        "estate_larder",
        "realm_state",
        "realm_project_runs",
        "realm_contributions",
        "realm_tags",
        "realm_votes",
        "realm_vote_eligibility",
        "realm_stores",
        "realm_lines",
        "realm_shipments",
        "market_orders",
        "market_matches",
        "gold_ledger",
        "world_state",
    }
    assert expected_tables <= Base.metadata.tables.keys()
    assert (
        not {"realm_edges", "realm_edge_progress", "realm_projects"}
        & Base.metadata.tables.keys()
    )
    assert "realm_id" not in Base.metadata.tables["characters"].c
    assert not {
        "level",
        "upgrade_slots",
        "relocating_to_realm_id",
        "relocation_completes_at",
    } & set(Base.metadata.tables["estates"].c.keys())
    actual = {
        (method.upper(), re.sub(r"\{[^}]+\}", "{}", path))
        for path, methods in app.openapi()["paths"].items()
        for method in methods
    }
    # The key router shares one handler with a Literal operation parameter.
    transfer = app.openapi()["paths"]["/keys/market/{identifier}/{operation}"]["post"]
    operation = next(p for p in transfer["parameters"] if p["name"] == "operation")
    assert set(operation["schema"]["enum"]) == {"buy", "cancel"}
    actual.update(
        ("POST", f"/keys/market/{{}}/{value}") for value in operation["schema"]["enum"]
    )
    expected = {
        ("GET", "/content/manifest"),
        ("GET", "/content/{}"),
        ("GET", "/map"),
        ("POST", "/characters"),
        ("GET", "/characters/me"),
        ("GET", "/characters/me/inventory"),
        ("PUT", "/characters/me/stance"),
        ("POST", "/equipment/equip"),
        ("POST", "/equipment/unequip"),
        ("PUT", "/equipment/utility"),
        ("PUT", "/equipment/belt/{}"),
        ("GET", "/actions/available"),
        ("POST", "/actions/start"),
        ("GET", "/actions/poll"),
        ("POST", "/actions/stop"),
        ("GET", "/travel/preview"),
        ("POST", "/travel/start"),
        ("GET", "/estates/me"),
        ("POST", "/estates/me/upgrades/{}"),
        ("POST", "/estates/me/transform"),
        ("POST", "/estates/build"),
        ("POST", "/estates/{}/buy"),
        ("POST", "/estates/me/surrender"),
        ("POST", "/estates/me/larder"),
        ("GET", "/realms"),
        ("GET", "/realms/{}"),
        ("GET", "/realms/{}/estates"),
        ("GET", "/realms/{}/tags/{}"),
        ("POST", "/realms/{}/projects/{}/kickoff"),
        ("POST", "/realms/{}/project/contribute"),
        ("POST", "/realms/{}/upgrades/{}/call"),
        ("GET", "/realms/{}/vote"),
        ("POST", "/realms/{}/vote"),
        ("GET", "/realms/{}/market"),
        ("GET", "/realms/{}/market/quote"),
        ("POST", "/realms/{}/market/trade"),
        ("POST", "/realms/{}/treasury/gift"),
        ("GET", "/market/book/{}"),
        ("GET", "/market/orders/me"),
        ("GET", "/market/history/me"),
        ("POST", "/market/orders"),
        ("POST", "/market/orders/{}/cancel"),
        ("POST", "/market/orders/{}/collect"),
        ("GET", "/keys/me"),
        ("DELETE", "/keys/{}"),
        ("GET", "/keys/market"),
        ("POST", "/keys/market"),
        ("POST", "/keys/market/{}/buy"),
        ("POST", "/keys/market/{}/cancel"),
        ("POST", "/tutorial/depart"),
        ("GET", "/admin/economy"),
    }
    assert expected <= actual, expected - actual
