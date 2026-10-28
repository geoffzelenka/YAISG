"""Tutorial lifecycle, isolation, ownership and gold conservation regressions."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from typing import Any, cast

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker
from test_estates import (
    _KEY_ID,
    _PRIVATE_KEY,
    _token,
)
from test_estates import (
    anyio_backend as anyio_backend,
)
from test_estates import (
    estate_client as estate_client,
)

from app.content.runtime import CONTENT
from app.main import app
from app.models import Character, Currency, Estate, GoldLedger, RealmState
from app.services.actions import resolve_character
from app.services.projects import kickoff
from app.services.tutorial import instance_id, seed_arrival

ApiFixture = tuple[
    AsyncClient, sessionmaker[Session], dict[str, str], dict[str, datetime]
]


def headers(kind: str = "guest") -> dict[str, str]:
    """Sign an identity trusted by the shared HTTP fixture."""
    claims = jwt.decode(_token(), options={"verify_signature": False})
    claims["kind"] = kind
    token = jwt.encode(
        claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": _KEY_ID}
    )
    return {"Authorization": f"Bearer {token}"}


async def create(
    client: AsyncClient, auth: dict[str, str], name: str
) -> dict[str, Any]:
    """Create an actual island character without a world-placement fixture."""
    response = await client.post("/characters", headers=auth, json={"name": name})
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json())


@pytest.mark.anyio
async def test_guest_completes_island_upgrades_and_departs_with_zero_gold_and_raft(
    estate_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The complete guest run uses ordinary actions, gear, travel and projects."""
    client, factory, _, clock = estate_client
    monkeypatch.setattr("app.services.actions.secrets.randbits", lambda _: 42)
    auth = headers()
    created = await create(client, auth, "Island Guest")
    character_id = uuid.UUID(created["character"]["id"])
    realm_1 = instance_id(CONTENT.tutorial.realm_1, character_id)
    realm_2 = instance_id(CONTENT.tutorial.realm_2, character_id)
    assert created["character"]["current_realm_id"] == realm_1
    assert created["gold"] == 0
    with factory() as session:
        before_world_gold = sum(
            session.scalars(
                select(RealmState.treasury).where(RealmState.isolated.is_(False))
            )
        )
        assert (
            len(
                list(
                    session.scalars(
                        select(RealmState).where(
                            RealmState.owner_character_id == character_id
                        )
                    )
                )
            )
            == 2
        )

    async def post(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await client.post(path, headers=auth, json=body)
        assert response.status_code == 200, response.text
        return cast(dict[str, Any], response.json())

    async def profile() -> dict[str, Any]:
        response = await client.get("/characters/me", headers=auth)
        assert response.status_code == 200, response.text
        return cast(dict[str, Any], response.json())

    async def work(action: str, seconds: int) -> None:
        await post("/actions/start", {"action_id": action})
        clock["now"] += timedelta(seconds=seconds)
        await post("/actions/stop")

    await work("tutorial.gather", 30)
    assert (await profile())["character"]["tutorial_step"] == "clothes"
    for action, item, slot, next_step in (
        ("tutorial.clothes", "item.tutorial_clothes", "chest", "club"),
        ("tutorial.club", "item.tutorial_club", "right_hand", "fight"),
    ):
        await work(action, 1)
        await post("/equipment/equip", {"item_id": item, "slot": slot})
        assert (await profile())["character"]["tutorial_step"] == next_step
    await work("tutorial.fight", 20)
    assert (await profile())["character"]["tutorial_step"] == "food"
    await work("tutorial.food", 1)
    assert (await profile())["character"]["tutorial_step"] == "travel"
    await post("/travel/start", {"destination_realm_id": realm_2, "mode": "relocate"})
    clock["now"] += timedelta(seconds=3)
    reached = await profile()
    assert (
        reached["gold"]
        == CONTENT.project(CONTENT.tutorial.raft_site_project).kickoff.gold
    )
    assert (await profile())["gold"] == reached["gold"]
    await post(
        f"/realms/{realm_2}/projects/{CONTENT.tutorial.raft_site_project}/kickoff"
    )
    assert (await profile())["character"]["tutorial_step"] == "fund"
    await post(
        f"/realms/{realm_2}/project/contribute",
        {"item_id": "item.fake_sprig", "quantity": 2},
    )
    clock["now"] += timedelta(seconds=3)
    assert (await profile())["character"]["tutorial_step"] == "raft"
    await post("/estates/me/transform", {"form_id": CONTENT.tutorial.raft_form})
    assert (await profile())["character"]["tutorial_step"] == "depart"
    destination = CONTENT.tutorial.arrival_realms[0]
    refused = await client.post(
        "/tutorial/depart", headers=auth, json={"destination_realm_id": destination}
    )
    assert (
        refused.status_code == 403
        and refused.json()["error"]["code"] == "ACCOUNT_REQUIRED"
    )
    # Auth is a separate service (its upgrade identity contract has its own tests).
    # Deliver the upgraded token for this same subject, as /auth/upgrade does.
    claims = jwt.decode(
        auth["Authorization"].split()[1], options={"verify_signature": False}
    )
    claims["kind"] = "full"
    auth["Authorization"] = "Bearer " + jwt.encode(
        claims, _PRIVATE_KEY, algorithm="RS256", headers={"kid": _KEY_ID}
    )
    assert (await client.get("/players/me", headers=auth)).json()["kind"] == "full"
    await post("/tutorial/depart", {"destination_realm_id": destination})
    arrived = await profile()
    assert arrived["gold"] == 0
    assert arrived["character"]["tutorial_step"] is None
    assert arrived["character"]["current_realm_id"] == destination
    with factory() as session:
        estate = session.get(Estate, uuid.UUID(arrived["estate"]["id"]))
        assert estate is not None and estate.form_id == CONTENT.tutorial.raft_form
        assert estate.realm_id == destination
        assert not list(
            session.scalars(
                select(RealmState).where(RealmState.owner_character_id == character_id)
            )
        )
        assert (
            sum(
                session.scalars(
                    select(RealmState.treasury).where(RealmState.isolated.is_(False))
                )
            )
            == before_world_gold
        )
        entries = list(
            session.scalars(
                select(GoldLedger).where(GoldLedger.character_id == character_id)
            )
        )
        assert {row.cause for row in entries} == {"tutorial_seed", "tutorial_destroy"}
        assert sum(row.amount for row in entries) == 0


@pytest.mark.anyio
async def test_island_visibility_and_travel_ownership(
    estate_client: ApiFixture,
) -> None:
    """World discovery excludes islands; templates and foreign instances are closed."""
    client, factory, _, clock = estate_client
    a, b = headers(), headers()
    first = await create(client, a, "First Island")
    second = await create(client, b, "Second Island")
    own = first["character"]["current_realm_id"]
    foreign = second["character"]["current_realm_id"]
    for path in ("/realms", "/map"):
        response = await client.get(path, headers=a)
        assert response.status_code == 200
        assert "tutorial" not in response.text
    assert (await client.get(f"/realms/{own}", headers=a)).status_code == 200
    assert (await client.get(f"/realms/{foreign}", headers=a)).status_code == 404
    for destination in (foreign, CONTENT.tutorial.arrival_realms[0]):
        response = await client.post(
            "/travel/start",
            headers=a,
            json={"destination_realm_id": destination, "mode": "visit"},
        )
        assert (
            response.status_code == 409
            and response.json()["error"]["code"] == "NO_ROUTE"
        )
    denied = await client.post(
        f"/realms/{foreign}/projects/{CONTENT.tutorial.raft_site_project}/kickoff",
        headers=a,
    )
    assert denied.status_code == 404
    with factory() as session:
        realm = session.get(RealmState, own)
        assert realm is not None
        old_tick = realm.last_tick_at
    from app.services.scheduler import run_realm_ticks

    assert run_realm_ticks(factory, app.state.content, clock["now"] + timedelta(days=1))
    with factory() as session:
        from app.services.caravans import run_caravan_pass

        run_caravan_pass(session, app.state.content, clock["now"] + timedelta(days=1))
        session.commit()
        realm = session.get(RealmState, own)
        assert realm is not None and realm.last_tick_at == old_tick


@pytest.mark.anyio
async def test_postgres_two_private_project_kickoffs_succeed(
    estate_client: ApiFixture,
) -> None:
    """Independent sessions contend on no shared one-project-per-realm slot."""
    client, factory, _, clock = estate_client
    if factory.kw["bind"].dialect.name != "postgresql":
        pytest.skip("Concurrent row locking requires PostgreSQL")
    ids = []
    for name in ("Private One", "Private Two"):
        created = await create(client, headers(), name)
        ids.append(uuid.UUID(created["character"]["id"]))

    barrier = Barrier(2)

    def launch(identifier: uuid.UUID) -> str:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            character = session.get(Character, identifier)
            assert character is not None
            realm_id = instance_id(CONTENT.tutorial.realm_2, identifier)
            character.current_realm_id = realm_id
            seed_arrival(session, character, CONTENT, clock["now"])
            session.commit()
            barrier.wait(timeout=5)
            resolve_character(session, identifier, clock["now"], CONTENT)
            realm = session.get(RealmState, realm_id)
            assert realm is not None
            result = kickoff(
                session,
                character,
                realm,
                CONTENT.tutorial.raft_site_project,
                clock["now"],
                CONTENT,
            )
            session.commit()
            return str(result.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(launch, ids))
    assert len(set(results)) == 2


@pytest.mark.anyio
async def test_departure_audits_wallet_orders_stores_keys_and_rolls_back(
    estate_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cleanup is explicit and failure cannot remove holders without their audits."""
    from app.models import (
        GoodsLedger,
        Inventory,
        ItemInstance,
        KeyListing,
        MarketOrder,
        RealmStore,
    )
    from app.services import tutorial

    client, factory, _, clock = estate_client
    auth = headers("full")
    created = await create(client, auth, "Cleanup Island")
    identifier = uuid.UUID(created["character"]["id"])
    realm_id = instance_id(CONTENT.tutorial.realm_2, identifier)
    key_id = uuid.uuid4()
    with factory() as session:
        character = session.get(Character, identifier)
        assert character is not None
        character.current_realm_id = realm_id
        estate = session.get(Estate, character.home_estate_id)
        assert estate is not None
        estate.form_id = CONTENT.tutorial.raft_form
        estate.realm_id = realm_id
        seed_arrival(session, character, CONTENT, clock["now"])
        wallet = session.get(Currency, identifier)
        realm = session.get(RealmState, realm_id)
        assert wallet is not None and realm is not None
        # Partition the seed between all three physical gold holders.
        wallet.gold = 2
        realm.treasury = 5
        session.add(
            MarketOrder(
                character_id=identifier,
                side="buy",
                item_id="item.fake_sprig",
                unit_price=3,
                quantity=1,
                quantity_remaining=1,
                escrow_gold_remaining=3,
                fill_items=0,
                fill_gold=0,
                status="open",
                realm_id=realm_id,
                created_at=clock["now"],
                expires_at=clock["now"] + timedelta(days=1),
            )
        )
        session.add(
            RealmStore(
                realm_id=realm_id, item_id="item.fake_sprig", quantity_milli=2500
            )
        )
        session.add(
            Inventory(character_id=identifier, item_id="item.fake_food", quantity=1)
        )
        session.add(
            ItemInstance(
                id=key_id,
                template_id=CONTENT.exploration.templates[0].id,
                holder_character_id=None,
                discovered_by_character_id=identifier,
                discovered_by_name="Cleanup Island",
                realm_id=realm_id,
                payload={},
                uses_total=1,
                uses_remaining=1,
                state="active",
                created_at=clock["now"],
            )
        )
        session.flush()
        session.add(
            KeyListing(
                instance_id=key_id,
                seller_character_id=identifier,
                price_gold=1,
                realm_id=realm_id,
                status="open",
                created_at=clock["now"],
            )
        )
        session.commit()
    from app.services.guest_purge import _dispose_realms

    original = _dispose_realms

    def fail(*args: object) -> None:
        raise RuntimeError("forced cleanup failure")

    monkeypatch.setattr(tutorial, "_dispose_realms", fail)
    destination = CONTENT.tutorial.arrival_realms[0]
    response = await client.post(
        "/tutorial/depart", headers=auth, json={"destination_realm_id": destination}
    )
    assert response.status_code == 500
    with factory() as session:
        assert session.get(RealmState, realm_id) is not None
        assert session.get(ItemInstance, key_id) is not None
        wallet = session.get(Currency, identifier)
        assert wallet is not None and wallet.gold == 2
        assert not list(
            session.scalars(
                select(GoldLedger).where(
                    GoldLedger.cause == "tutorial_destroy",
                    GoldLedger.character_id == identifier,
                )
            )
        )
        assert not list(
            session.scalars(
                select(GoodsLedger).where(GoodsLedger.character_id == identifier)
            )
        )
    monkeypatch.setattr(tutorial, "_dispose_realms", original)
    response = await client.post(
        "/tutorial/depart", headers=auth, json={"destination_realm_id": destination}
    )
    assert response.status_code == 200, response.text
    with factory() as session:
        assert session.get(ItemInstance, key_id) is None
        assert not list(
            session.scalars(
                select(KeyListing).where(KeyListing.seller_character_id == identifier)
            )
        )
        assert not list(
            session.scalars(
                select(MarketOrder).where(MarketOrder.character_id == identifier)
            )
        )
        assert (
            sum(
                session.scalars(
                    select(GoldLedger.amount).where(
                        GoldLedger.character_id == identifier
                    )
                )
            )
            == 0
        )
        sinks = list(
            session.scalars(
                select(GoodsLedger).where(GoodsLedger.character_id == identifier)
            )
        )
        assert {row.item_id: row.amount_milli for row in sinks} == {
            "item.fake_sprig": -2500,
            f"instance:{CONTENT.exploration.templates[0].id}": -1000,
        }
        assert all(row.cause == "tutorial_destroy" for row in sinks)
        food = session.get(Inventory, (identifier, "item.fake_food"))
        assert food is not None and food.quantity == 1
    repeated = await client.post(
        "/tutorial/depart", headers=auth, json={"destination_realm_id": destination}
    )
    assert (
        repeated.status_code == 409
        and repeated.json()["error"]["code"] == "NOT_IN_TUTORIAL"
    )


def test_seed_check_validates_arrival_bids_at_every_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single unfunded intermediate tick fails even when final bids recover."""
    from app.services import seed_check
    from app.services.market import market_contexts

    original = market_contexts
    calls = 0

    def contexts(session: Session, realm: RealmState, content: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 2:
            return {}
        return original(session, realm, CONTENT)

    monkeypatch.setattr(seed_check, "market_contexts", contexts)
    reports = seed_check.check_seed(CONTENT, days=1)
    assert calls == CONTENT.economy.tick.per_day * len(CONTENT.tutorial.arrival_realms)
    assert (
        next(
            r for r in reports if r.realm_id == CONTENT.tutorial.arrival_realms[0]
        ).arrival_bids_check
        == "failed"
    )
    monkeypatch.setattr(seed_check, "market_contexts", original)
    assert all(
        r.arrival_bids_check == "passed" for r in seed_check.check_seed(CONTENT, days=1)
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "kind",
    [
        "has_item",
        "skill_level",
        "equipped",
        "in_realm",
        "tag_present",
        "estate_form",
        "project_kicked_off",
    ],
)
async def test_each_tutorial_condition_advances_lazily(
    estate_client: ApiFixture,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Every supported content condition advances from authoritative profile state."""
    from dataclasses import replace

    from app.content.schemas import TutorialStep
    from app.models import CharacterEquipment, CharacterSkill, Inventory
    from app.services.realms import push_realm_tag

    client, factory, _, clock = estate_client
    auth = headers()
    created = await create(client, auth, "Condition Hero")
    identifier = uuid.UUID(created["character"]["id"])
    targets = {
        "has_item": "item.fake_food",
        "skill_level": "travel",
        "equipped": "item.tutorial_clothes",
        "in_realm": CONTENT.tutorial.realm_2,
        "tag_present": "facility.tutorial_raft",
        "estate_form": CONTENT.tutorial.raft_form,
        "project_kicked_off": CONTENT.tutorial.raft_site_project,
    }
    condition: dict[str, Any] = {"kind": kind, "id": targets[kind]}
    if kind in {"has_item", "skill_level"}:
        condition["quantity"] = 2
    step = TutorialStep.model_validate(
        {"id": "check", "hint": "Check milestone", "done_when": condition}
    )
    content = replace(
        CONTENT,
        tutorial=CONTENT.tutorial.model_copy(
            update={"steps": (step, CONTENT.tutorial.steps[-1])}
        ),
    )
    monkeypatch.setattr(app.state, "content", content)
    with factory() as session:
        character = session.get(Character, identifier)
        assert character is not None
        character.tutorial_step = "check"
        session.commit()
    pending = await client.get("/characters/me", headers=auth)
    assert pending.status_code == 200, pending.text
    assert pending.json()["character"]["tutorial_step"] == "check"
    with factory() as session:
        character = session.get(Character, identifier)
        assert character is not None
        character.current_realm_id = instance_id(CONTENT.tutorial.realm_2, identifier)
        realm = session.get(RealmState, character.current_realm_id)
        assert realm is not None
        if kind == "has_item":
            session.add(
                Inventory(character_id=identifier, item_id=targets[kind], quantity=2)
            )
        elif kind == "skill_level":
            skill = session.get(CharacterSkill, (identifier, "travel"))
            assert skill is not None
            skill.xp = CONTENT.xp_curve.levels[1].xp
        elif kind == "equipped":
            session.add(
                CharacterEquipment(
                    character_id=identifier,
                    slot="chest",
                    item_id=targets[kind],
                    quantity=1,
                )
            )
        elif kind == "estate_form":
            estate = session.get(Estate, character.home_estate_id)
            assert estate is not None
            estate.form_id = targets[kind]
        elif kind == "tag_present":
            push_realm_tag(session, realm, targets[kind], clock["now"])
        elif kind == "project_kicked_off":
            seed_arrival(session, character, CONTENT, clock["now"])
            kickoff(session, character, realm, targets[kind], clock["now"], CONTENT)
        session.commit()
    response = await client.get("/characters/me", headers=auth)
    assert response.status_code == 200, response.text
    assert response.json()["character"]["tutorial_step"] == "depart"
