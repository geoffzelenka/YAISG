"""Real operations and preparation for the world conservation property."""

import uuid
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from fractions import Fraction
from types import MappingProxyType
from typing import Literal

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from test_estates import _token
from test_gold import BULLION, REALM, mint_content
from world_accounting import GoodsAccounting, goods
from world_helpers import create_world_character

from app.content.loader import ContentIndex
from app.content.schemas import (
    ActionInput,
    BuildCost,
    IntegerRange,
    ProductionItem,
    Selector,
    TagUpkeep,
)
from app.models import (
    Character,
    Currency,
    Estate,
    Inventory,
    ItemInstance,
    MarketOrder,
    Player,
    RealmProjectRun,
    RealmShipment,
    RealmState,
    RealmStore,
)
from app.services.caravans import run_caravan_pass
from app.services.guest_purge import purge_guests
from app.services.market_lifecycle import run_market_lifecycle
from app.services.realm_ticks import (
    complete_tick_transition,
    load_context,
    persist_context,
)
from app.services.realms import (
    as_utc,
    resolve_realm,
    start_transition,
)

SPRIG = "item.fake_sprig"
PLANK = "item.fake_plank"
OTHER_REALM = "realm.ashen_reach"
# Allow the covering permutation plus four further kickoff attempts in the tail.
EXTRA_PROJECT_NAMES = ("other", "third", "fourth", "fifth", "sixth", "seventh")
PROJECT_IDS = (
    "project.verdant_cardboard",
    *(f"project.{name}" for name in EXTRA_PROJECT_NAMES),
)
OPERATIONS = (
    "tutorial_creation",
    "tutorial_departure",
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
)


def world_content() -> ContentIndex:
    """Exercise authored sources, sinks and access with synthetic test content."""
    content = mint_content()
    expedition = content.exploration.actions[0].model_copy(
        update={"discovery_chance": 1.0, "base_cycle_ms": 1000}
    )
    template = content.exploration.templates[0]
    assert template.gather is not None
    template = template.model_copy(
        update={
            "keys": IntegerRange(min=1, max=1),
            "uses": IntegerRange(min=1, max=1),
            "gather": template.gather.model_copy(
                update={
                    "outputs": tuple(
                        output.model_copy(update={"quantity_min": 1, "quantity_max": 1})
                        for output in template.gather.outputs
                    )
                }
            ),
        }
    )
    content = content.with_overrides(actions=(expedition,))
    content = replace(
        content,
        exploration=content.exploration.model_copy(
            update={"actions": (expedition,), "templates": (template,)}
        ),
    )
    node = content.development_node("node.verdant_t1")
    content = replace(
        content,
        _nodes_by_id=MappingProxyType(
            {
                **content._nodes_by_id,
                node.id: node.model_copy(
                    update={
                        "actions": (*node.actions, expedition.id),
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
                    "effects": tag.effects.model_copy(
                        update={"caravan_access": True, "edge_loss_reduction_pct": 0}
                    )
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
    extra_projects = tuple(
        project.model_copy(
            update={"id": f"project.{name}", "grants_tag": f"bonus.{name}"}
        )
        for name in EXTRA_PROJECT_NAMES
    )
    extra_tags = tuple(
        next(tag for tag in content.tags if tag.id == "bonus.fake").model_copy(
            update={"id": f"bonus.{name}"}
        )
        for name in EXTRA_PROJECT_NAMES
    )
    nodes = {
        key: value.model_copy(
            update={
                "inherent_tags": tuple(
                    dict.fromkeys((*value.inherent_tags, "access.fake"))
                )
            }
        )
        for key, value in content._nodes_by_id.items()
    }
    nodes[node.id] = nodes[node.id].model_copy(
        update={"projects": (*nodes[node.id].projects, *(p.id for p in extra_projects))}
    )
    return replace(
        content,
        tags=(*content.tags, *extra_tags),
        _nodes_by_id=MappingProxyType(nodes),
        _projects_by_id=MappingProxyType(
            {**content._projects_by_id, **{p.id: p for p in extra_projects}}
        ),
    ).with_overrides(
        items=[
            item.model_copy(update={"stack_limit": 1000000}) for item in content.items
        ]
    )


@dataclass
class WorldScenario:
    """Run valid intents and verify every preparatory and generated transfer."""

    client: AsyncClient
    factory: sessionmaker[Session]
    headers: tuple[dict[str, str], dict[str, str]]
    clock: dict[str, datetime]
    content: ContentIndex
    audit: GoodsAccounting
    characters: tuple[uuid.UUID, uuid.UUID]
    baseline_goods: Counter[str] = field(default_factory=Counter)
    baseline_gold: int = 0

    @property
    def now(self) -> datetime:
        """Return the injected simulation clock."""
        return self.clock["now"]

    async def net(self) -> int:
        """Read all gold holders and ledger causes from one server snapshot."""
        response = await self.client.get("/admin/economy", headers=self.headers[0])
        assert response.status_code == 200, response.text
        data = response.json()
        return int(sum(data["holders"].values()) - sum(data["ledger"].values()))

    async def check(self) -> None:
        """Compare holders with sources and independently calculated road loss."""
        actual_gold = await self.net()
        assert actual_gold == self.baseline_gold, (actual_gold, self.baseline_gold)
        with self.factory() as session:
            self.audit.verify_purge_ledger(session)
            expected = self.audit.expected(self.baseline_goods)
            for shipment in session.scalars(select(RealmShipment)):
                route = self.content.caravan_routes[
                    (shipment.from_realm_id, shipment.to_realm_id)
                ]
                # This fixture authors zero road reductions. Compute survival
                # from edge data, independently of dispatch's delivered field.
                retained = Fraction(1)
                for edge in route.edges:
                    retained *= 1 - Fraction(str(edge.base_loss_pct)) / 100
                arriving = int(shipment.quantity_sent * retained)
                assert shipment.quantity_arriving == arriving
                expected[shipment.item_id] -= 1000 * (shipment.quantity_sent - arriving)
            actual_goods = goods(session)
            assert actual_goods == expected, (
                actual_goods,
                expected,
                self.audit.changes,
            )

    async def post(
        self, path: str, body: dict[str, object] | None = None, owner: int = 0
    ) -> Response:
        """Require successful public mutations; rejected intents never count."""
        response = await self.client.post(path, headers=self.headers[owner], json=body)
        assert response.status_code in (200, 201, 204), (path, body, response.text)
        return response

    async def pay_form(self, path: str, form_id: str) -> None:
        """Pay an authored construction cost and count the consumed goods."""
        await self.post(path, {"form_id": form_id})
        cost = self.content.estate_form(form_id).build_cost.goods[0]
        self.audit.add("construction", SPRIG, -cost.quantity * 1000)
        await self.check()

    def home_form(self) -> str:
        """Read the primary character's authoritative current form."""
        with self.factory() as session:
            character = session.get(Character, self.characters[0])
            assert character is not None
            home = session.get(Estate, character.home_estate_id)
            assert home is not None
            return home.form_id

    async def ensure_mobile(self) -> None:
        """Obtain a mobile estate by a real surrender when needed."""
        if self.content.estate_form(self.home_form()).mobility == "fixed":
            await self.post("/estates/me/surrender", {"donate": False})
            await self.check()

    async def ensure_fixed(self) -> None:
        """Obtain a fixed estate by a real build when needed."""
        if self.content.estate_form(self.home_form()).mobility == "mobile":
            await self.pay_form("/estates/build", "form.fake_workshop")

    async def advance_realms(self, duration: timedelta) -> None:
        """Resolve both realms through the ordinary timestamp adapter."""
        self.clock["now"] += duration
        with self.factory() as session:
            for realm in session.scalars(select(RealmState).order_by(RealmState.id)):
                resolve_realm(session, realm, self.now, self.content)
            session.commit()
        await self.check()

    async def match(self) -> tuple[str, str]:
        """Match different owners and verify both recipients' slot holdings."""
        seller = await self.open_order("sell", 3)
        response = await self.post(
            "/market/orders",
            {
                "side": "buy",
                "item_id": BULLION,
                "quantity": 1,
                "unit_price": 3,
            },
        )
        buyer = response.json()["order"]["id"]
        assert len(response.json()["fills"]) == 1
        with self.factory() as session:
            buy = session.get(MarketOrder, uuid.UUID(buyer))
            sell = session.get(MarketOrder, uuid.UUID(seller))
            assert buy is not None and sell is not None
            assert buy.character_id == self.characters[0] != sell.character_id
            assert sell.character_id == self.characters[1]
            assert buy.fill_items == 1 and sell.fill_gold == 2
        await self.check()
        return buyer, seller

    async def open_order(self, side: Literal["buy", "sell"], price: int) -> str:
        """Keep buyer and seller ownership disjoint, including resting orders."""
        response = await self.post(
            "/market/orders",
            {
                "side": side,
                "item_id": BULLION,
                "quantity": 1,
                "unit_price": price,
            },
            owner=0 if side == "buy" else 1,
        )
        await self.check()
        return str(response.json()["order"]["id"])

    async def slot_mutation(self, order_id: str, operation: str) -> None:
        """Act with the slot owner's identity and verify actual collection."""
        with self.factory() as session:
            order = session.get(MarketOrder, uuid.UUID(order_id))
            assert order is not None
            owner = self.characters.index(order.character_id)
        response = await self.post(
            f"/market/orders/{order_id}/{operation}", owner=owner
        )
        if operation == "collect":
            moved = response.json()["collected"]
            assert moved["items"] + moved["gold"] > 0
        await self.check()

    async def cancel(self) -> None:
        """Cancel an actual open escrow, preparing one only if the book is empty."""
        with self.factory() as session:
            identifier = session.scalar(
                select(MarketOrder.id).where(MarketOrder.status == "open")
            )
        order_id = str(identifier) if identifier else await self.open_order("buy", 1)
        await self.slot_mutation(order_id, "cancel")

    async def collect(self) -> None:
        """Collect nonempty proceeds or create a real cross-character fill first."""
        with self.factory() as session:
            identifier = session.scalar(
                select(MarketOrder.id).where(
                    (MarketOrder.fill_items > 0) | (MarketOrder.fill_gold > 0)
                )
            )
        order_id = str(identifier) if identifier else (await self.match())[0]
        await self.slot_mutation(order_id, "collect")

    async def expiry(self) -> None:
        """Expire both occupied escrows at the authored time boundary."""
        identifiers = [
            await self.open_order("buy", 1),
            await self.open_order("sell", 20),
        ]
        with self.factory() as session:
            for identifier in identifiers:
                slot = session.get(MarketOrder, uuid.UUID(identifier))
                assert slot is not None and slot.status == "open"
        due = self.now + timedelta(days=self.content.economy.market.order_days)
        assert run_market_lifecycle(self.factory, self.content, due)
        await self.check()
        with self.factory() as session:
            orders = [session.get(MarketOrder, uuid.UUID(i)) for i in identifiers]
            assert all(
                order is not None and order.status == "collectable" for order in orders
            )
            assert any(order is not None and order.fill_gold > 0 for order in orders)
            assert any(order is not None and order.fill_items > 0 for order in orders)

    async def purge(self) -> None:
        """Purge closed rows alongside old collectable goods and gold."""
        for order_id in await self.match():
            await self.slot_mutation(order_id, "collect")
        await self.expiry()
        with self.factory() as session:
            closed = set(
                session.scalars(
                    select(MarketOrder.id).where(MarketOrder.status == "closed")
                )
            )
            protected = {
                order.id: (order.fill_items, order.fill_gold)
                for order in session.scalars(
                    select(MarketOrder).where(MarketOrder.status == "collectable")
                )
            }
        assert (
            closed
            and any(q for q, _ in protected.values())
            and any(g for _, g in protected.values())
        )
        due = self.now + timedelta(
            days=self.content.economy.market.retention_days
            + self.content.economy.market.order_days,
            seconds=1,
        )
        assert run_market_lifecycle(self.factory, self.content, due)
        await self.check()
        with self.factory() as session:
            assert not closed.intersection(session.scalars(select(MarketOrder.id)))
            for identifier, balances in protected.items():
                order = session.get(MarketOrder, identifier)
                assert (
                    order is not None
                    and (order.fill_items, order.fill_gold) == balances
                )

    async def kickoff(self) -> None:
        """Finish an active attempt, then kick off another offered project."""
        with self.factory() as session:
            active = session.scalar(
                select(RealmProjectRun).where(
                    RealmProjectRun.realm_id == REALM,
                    RealmProjectRun.status.in_(("funding", "building")),
                )
            )
        if active is not None:
            if active.status == "funding":
                await self.contribute(100)
            await self.advance_realms(timedelta(seconds=60))
        with self.factory() as session:
            character = session.get(Character, self.characters[0])
            assert character is not None
            last = character.last_kickoff_at
            completed = set(session.scalars(select(RealmProjectRun.project_id)))
        if last is not None and self.now < as_utc(last) + timedelta(days=1):
            await self.advance_realms(as_utc(last) + timedelta(days=1) - self.now)
        project = next(p for p in PROJECT_IDS if p not in completed)
        await self.post(f"/realms/{REALM}/projects/{project}/kickoff", {})
        await self.check()

    def funding_run(self) -> RealmProjectRun | None:
        """Read the current funding precondition without changing gameplay state."""
        with self.factory() as session:
            return session.scalar(
                select(RealmProjectRun).where(
                    RealmProjectRun.realm_id == REALM,
                    RealmProjectRun.status == "funding",
                )
            )

    async def contribute(self, quantity: int = 1) -> None:
        """Contribute and count the exact clamped payment."""
        run = self.funding_run()
        if run is None:
            await self.kickoff()
            run = self.funding_run()
        assert run is not None
        required = int(run.required[0]["quantity"]) * 1000
        paid = min(quantity, (required - run.contributed[0] + 999) // 1000)
        await self.post(
            f"/realms/{REALM}/project/contribute",
            {
                "item_id": SPRIG,
                "quantity": quantity,
            },
        )
        self.audit.add("projects", SPRIG, -paid * 1000)
        await self.check()

    async def caravan(self) -> None:
        """Fund and restock the seller through real trade, then dispatch a due pass."""
        await self.advance_realms(timedelta(hours=6))
        if self.funding_run() is None:
            await self.kickoff()
        view = await self.client.get(
            f"/realms/{OTHER_REALM}/market", headers=self.headers[1]
        )
        assert view.status_code == 200, view.text
        await self.check()
        members = [
            member for line in view.json()["lines"] for member in line["members"]
        ]
        quantity = min(
            8, next(m["funded_quantity"] for m in members if m["item_id"] == SPRIG)
        )
        if quantity:
            await self.post(
                f"/realms/{OTHER_REALM}/market/trade",
                {
                    "item_id": SPRIG,
                    "side": "sell",
                    "quantity": quantity,
                    "limit_gold": 0,
                },
                owner=1,
            )
            await self.check()
        with self.factory() as session:
            previous = set(session.scalars(select(RealmShipment.id)))
        with self.factory() as session:
            assert run_caravan_pass(session, self.content, self.now)
            session.commit()
        await self.check()
        with self.factory() as session:
            assert set(session.scalars(select(RealmShipment.id))) - previous

    async def arrive(self) -> None:
        """Resolve a shipment that is still in transit."""
        with self.factory() as session:
            pending = set(
                session.scalars(
                    select(RealmShipment.id).where(RealmShipment.status == "in_transit")
                )
            )
        if not pending:
            await self.caravan()
            with self.factory() as session:
                pending = set(
                    session.scalars(
                        select(RealmShipment.id).where(
                            RealmShipment.status == "in_transit"
                        )
                    )
                )
        assert pending
        await self.advance_realms(timedelta(hours=24))
        with self.factory() as session:
            arrived = set(
                session.scalars(
                    select(RealmShipment.id).where(RealmShipment.status == "arrived")
                )
            )
        assert pending <= arrived

    async def buy(self) -> None:
        """Buy a good actually offered above reserve, using the server's market view."""
        view = await self.client.get(f"/realms/{REALM}/market", headers=self.headers[0])
        assert view.status_code == 200, view.text
        await self.check()
        sale = next(row for row in view.json()["for_sale"] if row["item_id"] == PLANK)
        assert sale["quantity"] >= 1
        await self.post(
            f"/realms/{REALM}/market/trade",
            {
                "item_id": PLANK,
                "side": "buy",
                "quantity": 1,
                "limit_gold": 100,
            },
        )
        await self.check()

    async def action(self) -> None:
        """Resolve one deterministic two-sprig to one-plank refining cycle."""
        await self.post("/actions/start", {"action_id": "refining.fake_plank"})
        await self.check()
        self.clock["now"] += timedelta(milliseconds=4500)
        result = await self.post("/actions/stop")
        assert result.json()["since_last"]["cycles_completed"] == 1
        self.audit.add("actions", SPRIG, -2000)
        self.audit.add("actions", PLANK, 1000)
        await self.check()

    async def discovery(self) -> str:
        """Create exactly one resource instance through exploration, then account it."""
        action = self.content.exploration.actions[0]
        response = await self.post("/actions/start", {"action_id": action.id})
        self.clock["now"] += timedelta(milliseconds=response.json()["cycle_ms"])
        response = await self.post("/actions/stop")
        assert response.json()["since_last"]["cycles_completed"] == 1
        self.audit.add(
            "discovery", f"instance:{self.content.exploration.templates[0].id}", 1000
        )
        await self.check()
        with self.factory() as session:
            key = session.scalar(
                select(ItemInstance)
                .where(
                    ItemInstance.holder_character_id == self.characters[0],
                    ItemInstance.state == "active",
                )
                .order_by(ItemInstance.created_at.desc())
            )
            assert key is not None
            return str(key.id)

    async def key_operation(self, operation: str) -> None:
        """Exercise creation, finite use, disposal and invalidation without stacking."""
        identifier = await self.discovery()
        if operation == "exploration":
            return
        if operation == "key_listing_invalidate":
            response = await self.post(
                "/keys/market", {"instance_id": identifier, "price_gold": 3}
            )
        else:
            response = await self.post("/actions/start", {"key_id": identifier})
        await self.check()
        if operation == "key_use":
            self.clock["now"] += timedelta(milliseconds=response.json()["cycle_ms"])
            response = await self.post("/actions/stop")
            assert response.json()["stop_reason"] == "KEY_DEPLETED"
            self.audit.add("key_outputs", SPRIG, 1000)
        elif operation == "key_delete":
            response = await self.client.delete(
                f"/keys/{identifier}", headers=self.headers[0]
            )
            assert response.status_code == 204, response.text
            self.audit.add(
                "instance_delete",
                f"instance:{self.content.exploration.templates[0].id}",
                -1000,
            )
        else:
            # Keep the world fixture's other systems at the same simulation time.
            # The separate transition tests exercise the authored duration.
            instant = replace(
                self.content,
                economy=self.content.economy.model_copy(
                    update={
                        "transition": self.content.economy.transition.model_copy(
                            update={"duration_days": 0}
                        )
                    }
                ),
            )
            with self.factory() as session:
                realm = session.get(RealmState, REALM)
                assert realm is not None
                start_transition(
                    realm, realm.current_node_id, "upgrade", self.now, instant
                )
                context = load_context(session, realm, None, instant)
                complete_tick_transition(context, realm, self.now, instant)
                persist_context(session, realm, context)
                session.commit()
                key = session.get(ItemInstance, uuid.UUID(identifier))
                assert key is not None and key.state == "invalid"
            if operation == "key_listing_invalidate":
                assert key.holder_character_id == self.characters[0]
            else:
                response = await self.post("/actions/stop")
                assert response.json()["stop_reason"] == "KEY_INVALIDATED"
        await self.check()

    async def tutorial_operation(self, operation: str) -> None:
        """Exercise actual creation and audited departure with independent holders."""
        headers = {"Authorization": f"Bearer {_token()}"}
        response = await self.client.post(
            "/characters",
            headers=headers,
            json={"name": f"Island {uuid.uuid4().hex[:10]}"},
        )
        assert response.status_code == 201, response.text
        identifier = uuid.UUID(response.json()["character"]["id"])
        await self.check()
        if operation == "tutorial_creation":
            return
        from app.services.projects import kickoff
        from app.services.tutorial import instance_id, seed_arrival

        with self.factory() as session:
            character = session.get(Character, identifier)
            assert character is not None
            realm_id = instance_id(self.content.tutorial.realm_2, identifier)
            character.current_realm_id = realm_id
            estate = session.get(Estate, character.home_estate_id)
            assert estate is not None
            # Prepare the raft holder; the dedicated end-to-end test builds it.
            estate.realm_id = realm_id
            estate.form_id = self.content.tutorial.raft_form
            seed_arrival(session, character, self.content, self.now)
            realm = session.get(RealmState, realm_id)
            assert realm is not None
            kickoff(
                session,
                character,
                realm,
                self.content.tutorial.raft_site_project,
                self.now,
                self.content,
            )
            donor = session.get(Inventory, (self.characters[0], SPRIG))
            assert donor is not None and donor.quantity > 0
            donor.quantity -= 1
            session.add(
                RealmStore(realm_id=realm_id, item_id=SPRIG, quantity_milli=1000)
            )
            session.commit()
        await self.check()
        response = await self.client.post(
            "/tutorial/depart",
            headers=headers,
            json={"destination_realm_id": self.content.tutorial.arrival_realms[0]},
        )
        assert response.status_code == 200, response.text
        self.audit.add("tutorial_destroy", SPRIG, -1000)
        await self.check()

    async def run(self, operation: str) -> None:
        """Execute one valid generated intent, checking all required preparation."""
        if operation in {"tutorial_creation", "tutorial_departure"}:
            await self.tutorial_operation(operation)
            return
        if operation == "guest_purge":
            headers = {"Authorization": f"Bearer {_token()}"}
            response = await create_world_character(
                self.client,
                self.factory,
                headers=headers,
                name=f"Guest {uuid.uuid4().hex[:10]}",
                realm_id=REALM,
            )
            assert response.status_code == 201, response.text
            with self.factory() as session:
                guest = session.scalar(
                    select(Character).where(
                        Character.id == uuid.UUID(response.json()["character"]["id"])
                    )
                )
                assert guest is not None
                player = session.get(Player, guest.player_id)
                assert player is not None
                player.kind = "guest"
                player.last_activity_at = self.now - timedelta(
                    days=self.content.auth.guest_ttl_days + 1
                )
                donor = session.get(Inventory, (self.characters[0], SPRIG))
                wallet = session.get(Currency, self.characters[0])
                guest_wallet = session.get(Currency, guest.id)
                assert (
                    donor is not None
                    and wallet is not None
                    and guest_wallet is not None
                )
                donor.quantity -= 1
                wallet.gold -= 1
                guest_wallet.gold += 1
                session.add(Inventory(character_id=guest.id, item_id=SPRIG, quantity=1))
                session.commit()
            await self.check()
            with self.factory() as session:
                assert (
                    purge_guests(session, self.content, self.content.auth, self.now)
                    == 1
                )
                session.commit()
            self.audit.add("guest_purge", SPRIG, -1000)
            await self.check()
            return
        if operation in {"key_trade", "key_cancel"}:
            identifier = await self.discovery()
            response = await self.post(
                "/keys/market", {"instance_id": identifier, "price_gold": 3}
            )
            listing_id = response.json()["id"]
            await self.check()
            if operation == "key_trade":
                await self.post(f"/keys/market/{listing_id}/buy", owner=1)
            else:
                await self.post(f"/keys/market/{listing_id}/cancel")
            await self.check()
            return
        if operation in {
            "exploration",
            "key_use",
            "key_delete",
            "key_invalidate",
            "key_listing_invalidate",
        }:
            await self.key_operation(operation)
            return
        if operation in {"utility", "belt"}:
            path = (
                "/equipment/utility" if operation == "utility" else "/equipment/belt/0"
            )
            body = (
                {"item_id": "item.fake_ammo", "quantity": 3}
                if operation == "utility"
                else {
                    "item_id": "item.fake_food",
                    "quantity": 3,
                    "trigger": {"hp_below_pct": 50},
                }
            )
            response = await self.client.put(path, headers=self.headers[0], json=body)
            assert response.status_code == 200, response.text
            await self.check()
            response = await self.client.put(
                path, headers=self.headers[0], json={"item_id": None, "quantity": 0}
            )
            assert response.status_code == 200, response.text
        elif operation in {"equip", "unequip"}:
            await self.post(
                "/equipment/equip", {"item_id": "item.fake_cape", "slot": "cape"}
            )
            await self.check()
            if operation == "unequip":
                await self.post("/equipment/unequip", {"slot": "cape"})
        elif operation == "build":
            await self.ensure_mobile()
            await self.pay_form("/estates/build", "form.fake_workshop")
            return
        elif operation == "estate_buy":
            await self.ensure_mobile()
            with self.factory() as session:
                identifier = session.scalar(
                    select(Estate.id).where(
                        Estate.realm_id == REALM,
                        Estate.owner_character_id.is_(None),
                        Estate.form_id == "form.fake_workshop",
                        Estate.status == "active",
                    )
                )
            assert identifier is not None
            await self.post(f"/estates/{identifier}/buy", {})
        elif operation in ("surrender", "larder"):
            await self.ensure_fixed()
            if operation == "surrender":
                await self.post("/estates/me/surrender", {"donate": False})
            else:
                await self.post("/estates/me/larder", {"item_id": SPRIG, "quantity": 1})
        elif operation == "transform":
            await self.ensure_mobile()
            if self.home_form() != "form.camp":
                await self.ensure_fixed()
                await self.ensure_mobile()
            await self.pay_form("/estates/me/transform", "form.homestead")
            return
        elif operation == "tick":
            await self.advance_realms(timedelta(hours=1))
            return
        elif operation == "order_trade":
            await self.match()
            return
        elif operation == "open_buy":
            await self.open_order("buy", 1)
            return
        elif operation == "open_sell":
            await self.open_order("sell", 20)
            return
        elif operation == "gift":
            await self.post(f"/realms/{REALM}/treasury/gift", {"gold": 1})
        elif operation == "sell":
            await self.advance_realms(timedelta(hours=1))
            await self.post(
                f"/realms/{REALM}/market/trade",
                {
                    "item_id": BULLION,
                    "side": "sell",
                    "quantity": 1,
                    "limit_gold": 0,
                },
            )
        else:
            handlers = {
                "buy": self.buy,
                "kickoff": self.kickoff,
                "contribute": self.contribute,
                "caravan": self.caravan,
                "arrive": self.arrive,
                "collect": self.collect,
                "cancel": self.cancel,
                "expiry": self.expiry,
                "purge": self.purge,
                "action": self.action,
            }
            await handlers[operation]()
            return
        await self.check()
