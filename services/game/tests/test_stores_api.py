"""Public appetite and private world seed HTTP integration."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock
from test_actions import action_client as action_client
from test_actions import anyio_backend as anyio_backend

from app.models import Estate, RealmStore

pytestmark = pytest.mark.anyio


async def test_realm_lines_below_reserve_and_private_seed(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
) -> None:
    """Detail serves derived shortfalls without exposing the seed or treasury."""
    client, factory, _, headers = action_client
    realm_id = "realm.verdant_vale"
    with factory() as session:
        session.add(Estate(realm_id=realm_id, form_id="form.fake_workshop"))
        session.add(
            RealmStore(
                realm_id=realm_id, item_id="item.fake_sprig", quantity_milli=2000
            )
        )
        session.commit()
    response = await client.get(f"/realms/{realm_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "treasury" not in data
    assert len(data["lines"]) == 1
    line = data["lines"][0]
    assert (line["draw_per_day"], line["reserve"], line["stock"]) == (1000, 3000, 2000)
    assert line["below_reserve"] and line["in_transit"] == 0
    assert "budget_gold" not in line
    with factory() as session:
        store = session.scalar(select(RealmStore))
        assert store is not None
        store.quantity_milli = 3000
        session.commit()
    response = await client.get(f"/realms/{realm_id}", headers=headers)
    assert not response.json()["lines"][0]["below_reserve"]
    manifest = await client.get("/content/manifest")
    assert "world_seed" not in manifest.json()["packs"]
    assert (await client.get("/content/world_seed", headers=headers)).status_code == 404


async def test_boot_seeds_world_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot seeds holdings before requests and preserves them on restart."""
    from sqlalchemy import create_engine, func

    from app import db
    from app import main as game_main
    from app.db import Base
    from app.main import app
    from app.models import WorldState

    engine = create_engine(f"sqlite:///{tmp_path / 'boot.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", factory)
    frozen_datetime = Mock()
    frozen_datetime.now.return_value = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(game_main, "datetime", frozen_datetime)
    try:
        for _ in range(2):
            async with app.router.lifespan_context(app):
                with factory() as session:
                    assert session.get(WorldState, 1) is not None
                    assert session.scalar(
                        select(func.count()).select_from(Estate)
                    ) == sum(
                        len(seed.estates)
                        for seed in app.state.content.world_seed.realms
                    )
    finally:
        engine.dispose()


async def test_boot_missing_tables_logs_migration_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """An unmigrated database fails boot with a concise operator instruction."""
    from sqlalchemy import create_engine
    from sqlalchemy.exc import OperationalError

    from app import db
    from app.main import app

    engine = create_engine(f"sqlite:///{tmp_path / 'unmigrated.db'}")
    monkeypatch.setattr(db, "SessionLocal", sessionmaker(bind=engine))
    try:
        with pytest.raises(OperationalError, match="no such table"):
            async with app.router.lifespan_context(app):
                pytest.fail("boot must fail without migrations")
        messages = [record.getMessage() for record in caplog.records]
        assert (
            messages.count(
                "Database not migrated; run alembic upgrade head / make db-reset"
            )
            == 1
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("case", ["missing_state", "isolated_template"])
async def test_character_creation_rejects_unavailable_realm(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    """Invalid starting realm state cannot create a character or estate."""
    from dataclasses import replace
    from types import MappingProxyType

    from sqlalchemy import delete, func
    from test_actions import _token

    from app.main import app
    from app.models import Character, RealmState

    client, factory, _, _ = action_client
    realm_id = "realm.ashen_reach"
    if case == "missing_state":
        with factory() as session:
            session.execute(delete(RealmState).where(RealmState.id == realm_id))
            session.commit()
        expected_status, expected_code = 503, "WORLD_STATE_INCOMPLETE"
    else:
        content = app.state.content
        realms = dict(content._realms_by_id)
        realms[realm_id] = realms[realm_id].model_copy(update={"isolated": True})
        monkeypatch.setattr(
            app.state,
            "content",
            replace(content, _realms_by_id=MappingProxyType(realms)),
        )
        expected_status, expected_code = 422, "UNKNOWN_REALM"
    response = await client.post(
        "/characters",
        headers={"Authorization": f"Bearer {_token()}"},
        json={"name": "Unavailable Realm", "realm_id": realm_id},
    )
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(Character)) == 1
        assert session.scalar(select(func.count()).select_from(Estate)) == 1
