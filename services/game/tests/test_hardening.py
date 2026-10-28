"""Operational limits, transactional telemetry and cross-process liveness."""

import multiprocessing
from datetime import datetime, timedelta
from multiprocessing.connection import Connection
from typing import Any, cast
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock
from test_actions import action_client as action_client
from test_actions import anyio_backend as anyio_backend
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session
from test_trade import ITEM, REALM, seed

from app import config, rate_limit
from app.content.loader import ContentIndex
from app.models import MetricDelta, Player, RealmState
from app.services.realms import finalize_realm, resolve_realm
from app.services.scheduler import run_realm_ticks
from app.services.trade import trade


def totals(session: Session) -> dict[str, int]:
    """Read committed or pending event totals through the database."""
    session.flush()
    return {
        name: int(amount)
        for name, amount in session.execute(
            select(MetricDelta.name, func.sum(MetricDelta.amount)).group_by(
                MetricDelta.name
            )
        )
    }


@pytest.mark.anyio
async def test_rate_limit_shared_across_mutations_reads_free_and_window_resets(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failed intents consume a shared allowance; polling and the next window work."""
    client, _, clock, headers = action_client
    monkeypatch.setattr(rate_limit, "MUTATION_LIMIT", 2)
    clock.advance(timedelta(minutes=1))
    for _ in range(2):
        result = await client.post("/actions/start", headers=headers, json={})
        assert result.status_code == 422
    result = await client.delete(
        "/keys/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert result.status_code == 429
    assert result.json()["error"]["code"] == "RATE_LIMITED"
    assert int(result.headers["Retry-After"]) > 0
    assert (await client.get("/characters/me", headers=headers)).status_code == 200
    clock.advance(timedelta(minutes=1))
    assert (
        await client.post("/actions/start", headers=headers, json={})
    ).status_code == 422
    assert (await client.get("/map")).status_code == 200
    assert (await client.post("/actions/start", json={})).status_code == 401


@pytest.mark.anyio
async def test_metrics_operator_only_and_tick_counters(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Private gauges require an operator and report committed lazy ticks only."""
    client, factory, clock, headers = action_client
    assert (await client.get("/admin/metrics", headers=headers)).status_code == 403
    with factory() as session:
        user = session.scalar(select(Player.auth_user_id))
        realm = session.get(RealmState, REALM)
        assert realm is not None
        resolve_realm(session, realm, clock.now + timedelta(hours=2), CONTENT)
        session.commit()
    monkeypatch.setattr(config, "OPERATOR_AUTH_USER_IDS", frozenset({user}))
    result = await client.get("/admin/metrics", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["counters"]["ticks_run"] == 2
    assert body["counters"]["tick_duration_ns"] > 0
    assert body["counters"]["gold_minted"] == 0
    assert set(body["gold_by_holder"]) == {
        "wallets",
        "treasuries",
        "order_escrow",
        "order_slots",
    }
    from test_gold import BULLION, mint_content

    from app.models import RealmStore

    with factory() as session:
        realm = session.get(RealmState, REALM)
        assert realm is not None
        session.add(RealmStore(realm_id=REALM, item_id=BULLION, quantity_milli=10000))
        resolve_realm(session, realm, clock.now + timedelta(hours=3), mint_content())
        session.commit()
    body = (await client.get("/admin/metrics", headers=headers)).json()
    assert body["counters"]["gold_minted"] == 6
    assert body["counters"]["ticks_run"] == 3
    assert body["gold_by_holder"]["treasuries"] == 6


def test_tick_and_trade_metrics_idempotent_and_rollback(realm_session: Session) -> None:
    """Events count once and aborted changes leave no telemetry behind."""
    character, realm = seed(realm_session)
    realm_session.commit()
    trade(realm_session, character, realm, CONTENT, ITEM, "sell", 1, 0)
    assert totals(realm_session)["realm_trades"] == 1
    realm_session.rollback()
    assert "realm_trades" not in totals(realm_session)
    resolve_realm(realm_session, realm, NOW + timedelta(hours=2), CONTENT)
    before = totals(realm_session)
    resolve_realm(realm_session, realm, NOW + timedelta(hours=2), CONTENT)
    assert totals(realm_session) == before
    assert before["ticks_run"] == 2
    realm_session.rollback()
    assert totals(realm_session) == {}


def _scheduler_process(url: str, now: datetime, pipe: Connection, hold: bool) -> None:
    """Run with a fresh engine; the pipe coordinates actual advisory-lock overlap."""
    engine = create_engine(url)
    factory = sessionmaker(bind=engine)

    def blocked(
        session: Session, realm_id: str, at: datetime, content: ContentIndex
    ) -> RealmState | None:
        pipe.send("locked")
        assert pipe.poll(20)
        assert pipe.recv() == "release"
        return finalize_realm(session, realm_id, at, content)

    try:
        if hold:
            with patch("app.services.scheduler.finalize_realm", side_effect=blocked):
                pipe.send(run_realm_ticks(factory, CONTENT, now))
        else:
            pipe.send(run_realm_ticks(factory, CONTENT, now))
    finally:
        engine.dispose()
        pipe.close()


def test_postgres_scheduler_advisory_lock_two_processes(realm_session: Session) -> None:
    """Independent OS processes exclude overlapping ticks and release for replay."""
    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("PostgreSQL session advisory lock")
    realm_session.commit()
    bind: Any = realm_session.get_bind()
    url = bind.url.render_as_string(hide_password=False)
    ctx = multiprocessing.get_context("spawn")
    first_parent, first_child = ctx.Pipe()
    second_parent, second_child = ctx.Pipe()
    now = NOW + timedelta(hours=1)
    first = ctx.Process(target=_scheduler_process, args=(url, now, first_child, True))
    second = ctx.Process(
        target=_scheduler_process, args=(url, now, second_child, False)
    )
    first.start()
    try:
        assert first_parent.poll(20) and first_parent.recv() == "locked"
        second.start()
        assert second_parent.poll(20) and second_parent.recv() is False
        # Release each realm independently; the advisory lock stays held between them.
        first_parent.send("release")
        while first_parent.poll(20):
            message = first_parent.recv()
            if message is True:
                break
            assert message == "locked"
            first_parent.send("release")
        else:
            pytest.fail("First scheduler did not finish")
        first.join(20)
        second.join(20)
        assert first.exitcode == second.exitcode == 0
        assert run_realm_ticks(sessionmaker(bind=bind), CONTENT, now)
        realm_session.expire_all()
        count = totals(realm_session)["ticks_run"]
        assert count == realm_session.scalar(
            select(func.count())
            .select_from(RealmState)
            .where(RealmState.isolated.is_(False))
        )
    finally:
        for process in (first, second):
            if process.is_alive():
                process.terminate()
                process.join(5)
        first_parent.close()
        second_parent.close()
        first_child.close()
        second_child.close()


def test_rate_limit_concurrent_sessions_and_character_isolation(
    realm_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Independent sessions share one allowance while another identity stays free."""
    import uuid
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi import HTTPException
    from starlette.requests import Request

    from app.auth import VerifiedIdentity

    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    subject = uuid.uuid4()
    gate = Barrier(2)
    monkeypatch.setattr(rate_limit, "MUTATION_LIMIT", 1)

    def attempt(identity: uuid.UUID) -> int:
        request = Request({"type": "http", "method": "POST", "path": "/actions/start"})
        request.state.identity = VerifiedIdentity(identity)
        with factory() as session:
            if identity == subject:
                gate.wait(timeout=5)
            try:
                rate_limit.limit_mutation(request, session, NOW)
            except HTTPException as error:
                assert isinstance(error.detail, dict)
                assert error.detail["error"]["code"] == "RATE_LIMITED"
                return error.status_code
        return 200

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [subject, subject]))
    assert sorted(results) == [200, 429]
    assert attempt(uuid.uuid4()) == 200


def test_market_matches_and_tax_counters(realm_session: Session) -> None:
    """Both commodity matches and fixed-price key sales add durable totals."""
    from test_key_market import make_key
    from test_order_book import market_content, place

    from app.models import MarketMatch
    from app.services.key_market import list_key, transfer_listing

    seller, _ = seed(realm_session)
    buyer, _ = seed(realm_session)
    realm_session.commit()
    place(realm_session, seller, "sell", 1, 100)
    _, matches = place(realm_session, buyer, "buy", 1, 100)
    assert len(matches) == 1
    assert totals(realm_session)["matches"] == 1
    assert totals(realm_session)["tax_gold"] == matches[0].tax_gold
    key = make_key(realm_session, seller, market_content())
    realm_session.commit()
    listing = list_key(realm_session, seller, key.id, 100, NOW, market_content())
    realm_session.commit()
    transfer_listing(realm_session, buyer, listing.id, "buy", NOW, market_content())
    realm_session.commit()
    assert totals(realm_session)["matches"] == 2
    assert totals(realm_session)["tax_gold"] == 2 * matches[0].tax_gold
    # Counter history remains even when a lifecycle job prunes match rows.
    for match in realm_session.scalars(select(MarketMatch)):
        realm_session.delete(match)
    realm_session.commit()
    assert totals(realm_session)["matches"] == 2


def test_caravan_shipment_and_loss_counters(realm_session: Session) -> None:
    """Dispatch counts expected whole-item road loss once, with cursor replay inert."""
    from test_caravans import seed as seed_caravans

    from app.models import RealmShipment
    from app.services.caravans import run_caravan_pass

    content = seed_caravans(realm_session)
    now = NOW + timedelta(days=1)
    assert run_caravan_pass(realm_session, content, now)
    shipments = list(realm_session.scalars(select(RealmShipment)))
    assert shipments
    values = totals(realm_session)
    assert values["caravan_shipments"] == len(shipments)
    assert values.get("caravan_losses", 0) == sum(
        row.quantity_sent - row.quantity_arriving for row in shipments
    )
    assert not run_caravan_pass(realm_session, content, now)
    assert totals(realm_session) == values


def test_decay_shed_and_regression_counters(realm_session: Session) -> None:
    """Catch-up records actual stack loss and one regression start."""
    from test_realm_ticks import tick_content

    from app.services.realms import push_realm_tag, start_transition

    realm = realm_session.get(RealmState, REALM)
    assert realm is not None
    start_transition(realm, "node.verdant_t2", "upgrade", NOW, CONTENT)
    resolve_realm(realm_session, realm, NOW + timedelta(days=7), CONTENT)
    realm.last_tick_at = NOW + timedelta(days=7)
    resolve_realm(realm_session, realm, NOW + timedelta(days=7), CONTENT)
    push_realm_tag(realm_session, realm, "access.fake", NOW + timedelta(days=7))
    realm_session.flush()
    # A fed tick recovers one day, leaving this tier above its failing threshold.
    realm.gauge = 6
    realm.shed_progress = 1
    content = tick_content()
    resolve_realm(realm_session, realm, NOW + timedelta(days=8), content)
    assert totals(realm_session)["tags_shed"] == 1
    assert totals(realm_session)["regressions"] == 1
    resolve_realm(realm_session, realm, NOW + timedelta(days=8), content)
    assert totals(realm_session)["regressions"] == 1


@pytest.mark.anyio
async def test_discovery_counter_survives_key_destruction(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting a discovered key never subtracts its committed discovery event."""
    from test_keys import discover_api

    key = await discover_api(action_client, monkeypatch)
    client, factory, _, headers = action_client
    with factory() as session:
        assert totals(session)["keys_discovered"] == 1
    assert (await client.delete(f"/keys/{key}", headers=headers)).status_code == 204
    with factory() as session:
        assert totals(session)["keys_discovered"] == 1


def test_key_invalidation_first_cutoff_wins(realm_session: Session) -> None:
    """A later realm transition cannot extend access to already-invalid resources."""
    from test_key_market import make_key

    from app.services.keys import deprecate_keys, invalidate_keys

    owner, _ = seed(realm_session)
    key = make_key(realm_session, owner, CONTENT)
    invalidate_keys([key], NOW)
    deprecate_keys([key])
    invalidate_keys([key], NOW + timedelta(days=7))
    assert key.state == "invalid"
    assert key.invalidated_at == NOW


@pytest.mark.anyio
async def test_character_resolution_runs_off_event_loop(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CPU/database resolution must execute outside the request's asyncio thread."""
    from threading import get_ident

    from app.api import characters
    from app.services.actions import resolve_character

    observed: list[int] = []
    original = resolve_character

    def observe(*args: Any, **kwargs: Any) -> Any:
        observed.append(get_ident())
        return original(*args, **kwargs)

    monkeypatch.setattr(characters, "resolve_character", observe)
    client, _, _, headers = action_client
    main_thread = get_ident()
    assert (await client.get("/characters/me", headers=headers)).status_code == 200
    assert observed and all(thread != main_thread for thread in observed)


def test_seed_check_is_a_fatal_ci_step() -> None:
    """Both local CI and each game workflow matrix entry execute the seed checker."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    makefile = (root / "Makefile").read_text()
    ci_target = next(line for line in makefile.splitlines() if line.startswith("ci:"))
    assert "seed-check" in ci_target.split()
    assert (
        "\nseed-check:\n\tcd services/game && python -m app.services.seed_check"
        in makefile
    )
    workflow = (root / ".github/workflows/ci.yml").read_text()
    step = workflow.split("- name: Script checks and thirty-day seed check\n")[1].split(
        "- name:"
    )[0]
    assert "if: matrix.service == 'game'" in step
    assert "run: make scripts-ci seed-check" in step
    assert "continue-on-error" not in step


def test_sqlite_scheduler_two_process_replay(realm_session: Session) -> None:
    """SQLite cannot exclude drivers, but different processes must not replay ticks."""
    if realm_session.get_bind().dialect.name != "sqlite":
        pytest.skip("SQLite cross-process idempotence counterpart")
    realm_session.commit()
    bind: Any = realm_session.get_bind()
    url = bind.url.render_as_string(hide_password=False)
    ctx = multiprocessing.get_context("spawn")
    before = 0
    for index in range(2):
        parent, child = ctx.Pipe()
        process = ctx.Process(
            target=_scheduler_process,
            args=(url, NOW + timedelta(hours=1), child, False),
        )
        process.start()
        try:
            assert parent.poll(20) and parent.recv() is True
            process.join(20)
            assert process.exitcode == 0
            realm_session.expire_all()
            current = totals(realm_session)["ticks_run"]
            if index == 0:
                before = current
                assert before > 0
            else:
                assert current == before
            realm_session.commit()
        finally:
            if process.is_alive():
                process.terminate()
                process.join(5)
            parent.close()
            child.close()


def test_scheduler_failed_unlock_invalidates_connection_and_preserves_error() -> None:
    """A failed session unlock cannot leak a lock or replace the job's exception."""
    from unittest.mock import MagicMock

    factory = MagicMock()
    connection = factory.return_value.__enter__.return_value.connection.return_value
    connection.dialect.name = "postgresql"
    connection.scalar.return_value = True
    connection.scalars.side_effect = ValueError("enumeration failed")
    connection.execute.side_effect = RuntimeError("unlock failed")
    with pytest.raises(ValueError, match="enumeration failed"):
        run_realm_ticks(factory, CONTENT, NOW)
    connection.invalidate.assert_called_once()


def test_operator_configuration_parses_uuid_and_rejects_invalid_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Uppercase UUIDs identify operators; malformed identities fail boot."""
    import runpy
    import uuid

    identifier = uuid.uuid4()
    monkeypatch.setenv("GAME_OPERATOR_AUTH_USER_IDS", str(identifier).upper())
    values = runpy.run_path(config.__file__)
    assert values["OPERATOR_AUTH_USER_IDS"] == frozenset({identifier})
    monkeypatch.setenv("GAME_OPERATOR_AUTH_USER_IDS", "bad-identity")
    with pytest.raises(ValueError):
        runpy.run_path(config.__file__)


def test_scheduler_realm_lock_order_matches_python_sorting(
    realm_session: Session,
) -> None:
    """Mixed case and Unicode ids share Python's canonical realm order."""
    identifiers = [REALM, "realm.Z", "realm.a", "realm.é"]
    for identifier in identifiers[1:]:
        realm_session.add(
            RealmState(
                id=identifier,
                template_id=REALM,
                current_node_id="node.verdant_t1",
                last_tick_at=NOW,
            )
        )
    realm_session.commit()
    observed: list[str] = []

    def observe(
        session: Session, identifier: str, at: datetime, content: ContentIndex
    ) -> None:
        observed.append(identifier)

    with (
        patch("app.services.scheduler.finalize_realm", side_effect=observe),
        patch("app.services.scheduler.run_caravan_pass", return_value=False),
    ):
        assert run_realm_ticks(
            sessionmaker(bind=realm_session.get_bind()), CONTENT, NOW
        )
    assert observed == sorted(identifiers)


@pytest.mark.parametrize("accounts", [2, 4])
def test_postgres_stale_rate_windows_do_not_deadlock(
    realm_session: Session, accounts: int
) -> None:
    """Stale accounts retain independent row locks through allowance commit."""
    import uuid
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy import event, text
    from sqlalchemy.engine import Engine
    from starlette.requests import Request

    from app.auth import VerifiedIdentity
    from app.models import MutationWindow

    engine = realm_session.get_bind()
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL cross-account row-lock regression")
    assert isinstance(engine, Engine)
    subjects = [uuid.uuid4() for _ in range(accounts)]
    realm_session.add_all(
        MutationWindow(auth_user_id=subject, window=0, attempts=1)
        for subject in subjects
    )
    realm_session.commit()
    factory = sessionmaker(bind=engine)
    locked = Barrier(accounts)

    def synchronize_upserts(
        connection: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        if statement.startswith("INSERT INTO mutation_windows"):
            # Each request now owns its row while every other row still appears
            # stale to its snapshot. A cross-account DELETE here deadlocks.
            locked.wait(timeout=10)

    def mutate(subject: uuid.UUID) -> None:
        request = Request({"type": "http", "method": "POST", "path": "/actions/start"})
        request.state.identity = VerifiedIdentity(subject)
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '15s'"))
            rate_limit.limit_mutation(request, session, NOW)

    event.listen(engine, "after_cursor_execute", synchronize_upserts)
    try:
        with ThreadPoolExecutor(max_workers=accounts) as pool:
            list(pool.map(mutate, subjects))
    finally:
        event.remove(engine, "after_cursor_execute", synchronize_upserts)
    realm_session.expire_all()
    rows = list(realm_session.scalars(select(MutationWindow)))
    assert len(rows) == accounts
    assert all(row.attempts == 1 for row in rows)
    assert all(
        row.window == int(NOW.timestamp()) // rate_limit.MUTATION_WINDOW_SECONDS
        for row in rows
    )


def test_all_mutation_routes_include_limiter_and_reads_use_method_gate() -> None:
    """Every mutation alias carries the limiter; GET dependencies exit before DB use."""
    from unittest.mock import Mock

    from fastapi import routing
    from fastapi.dependencies.models import Dependant
    from fastapi.routing import APIRoute
    from starlette.requests import Request

    from app.main import app

    def includes_limiter(dependant: Dependant) -> bool:
        return dependant.call is rate_limit.limit_mutation or any(
            includes_limiter(child) for child in dependant.dependencies
        )

    mutations = 0
    # Recent FastAPI keeps included routers lazy. Effective contexts include
    # inherited dependencies; older versions already expose flattened routes.
    walk_routes = getattr(routing, "iter_route_contexts", iter)
    for candidate in walk_routes(app.routes):
        if not isinstance(getattr(candidate, "original_route", candidate), APIRoute):
            continue
        # Effective contexts proxy the original APIRoute's dependency interface.
        route = cast(APIRoute, candidate)
        limited = includes_limiter(route.dependant)
        methods = route.methods
        assert methods is not None
        if methods & {"POST", "PUT", "PATCH", "DELETE"}:
            mutations += 1
            assert limited, f"Mutation route lacks limiter: {route.path}"
        if "GET" in methods and limited:
            session = Mock(spec=Session)
            request = Request({"type": "http", "method": "GET", "path": route.path})
            rate_limit.limit_mutation(request, session, NOW)
            assert session.mock_calls == [], f"GET consumed allowance: {route.path}"
    assert mutations > 0


def test_metric_cache_preserves_flush_and_rollback_boundaries(
    realm_session: Session,
) -> None:
    """Cached rows combine only pending deltas, including after savepoint rollback."""
    from app.services.metrics import record

    record(realm_session, realm_trades=2)
    record(realm_session, realm_trades=3)
    realm_session.flush()
    record(realm_session, realm_trades=7)
    realm_session.flush()
    assert sorted(realm_session.scalars(select(MetricDelta.amount))) == [5, 7]
    realm_session.rollback()
    record(realm_session, realm_trades=11)
    realm_session.commit()
    with (
        pytest.raises(ValueError, match="Abort nested event"),
        realm_session.begin_nested(),
    ):
        record(realm_session, realm_trades=13)
        realm_session.flush()
        raise ValueError("Abort nested event")
    record(realm_session, realm_trades=17)
    realm_session.commit()
    assert sorted(realm_session.scalars(select(MetricDelta.amount))) == [11, 17]
