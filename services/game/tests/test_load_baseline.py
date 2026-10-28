"""Reproducible in-process HTTP baseline on disposable fixture data."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_actions import FakeClock
from test_actions import action_client as action_client
from test_actions import anyio_backend as anyio_backend
from test_order_book import market_content
from test_trade import ITEM, REALM

from app.main import app
from app.models import Character, Inventory


@pytest.mark.anyio
async def test_mixed_load_baseline(
    action_client: tuple[AsyncClient, sessionmaker[Session], FakeClock, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual ASGI routes support concurrent polling, realm reads and order churn."""
    path = Path(__file__).resolve().parents[3] / "scripts" / "load_pipeline.py"
    spec = importlib.util.spec_from_file_location("load_pipeline", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    client, factory, _, headers = action_client
    monkeypatch.setattr(app.state, "content", market_content())
    with factory() as session:
        character = session.scalar(select(Character))
        assert character is not None
        session.add(Inventory(character_id=character.id, item_id=ITEM, quantity=100))
        session.commit()
    result = await module.workload(
        client, [headers["Authorization"].removeprefix("Bearer ")], REALM, ITEM, 4, 5
    )
    print(json.dumps(result, sort_keys=True))
    assert result["requests"] == 100
    assert result["statuses"] == {"200": 80, "201": 20}
    assert result["failures"] == 0
