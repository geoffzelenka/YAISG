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
