"""Validated, immutable schemas for static game content."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContentModel(BaseModel):
    """Base class that rejects unknown content fields and prevents mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ModifierType(StrEnum):
    """Modifier mechanics understood by the game engine."""

    CYCLE_TIME_PCT = "cycle_time_pct"
    XP_PCT = "xp_pct"
    EXTRA_DROP_CHANCE_PCT = "extra_drop_chance_pct"
    MARKET_TAX_PCT = "market_tax_pct"


class CapType(StrEnum):
    """Upgradeable limit mechanics understood by the game engine."""

    OFFLINE_HOURS = "offline_hours"
    INVENTORY_SLOTS = "inventory_slots"
    MARKET_LISTINGS = "market_listings"
    ESTATE_UPGRADE_SLOTS = "estate_upgrade_slots"


class ItemQuantity(ContentModel):
    """A positive quantity of an item."""

    item_id: str = Field(min_length=1)
    qty: int = Field(gt=0)


class Drop(ContentModel):
    """A possible item reward from an action."""

    item_id: str = Field(min_length=1)
    qty: tuple[int, int]
    chance: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_quantity_range(self) -> "Drop":
        """Require a positive, ascending inclusive quantity range."""
        minimum, maximum = self.qty
        if minimum <= 0 or maximum < minimum:
            raise ValueError("drop qty must be a positive [min, max] range")
        return self


class Action(ContentModel):
    """A timed action belonging to a skill."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    level_required: int = Field(ge=1, le=99)
    cycle_ms: int = Field(gt=0)
    inputs: tuple[ItemQuantity, ...] = ()
    xp: int = Field(gt=0)
    drops: tuple[Drop, ...] = ()
    realm_tags: tuple[str, ...] = ()


class Skill(ContentModel):
    """A skill and its available actions."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    actions: tuple[Action, ...] = ()


class SkillsPack(ContentModel):
    """Top-level skills content pack."""

    skills: tuple[Skill, ...]


class Item(ContentModel):
    """A stackable inventory item."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    stack_limit: int = Field(default=2_147_483_647, gt=0)
    tags: tuple[str, ...] = ()


class ItemsPack(ContentModel):
    """Top-level items content pack."""

    items: tuple[Item, ...]


class Modifier(ContentModel):
    """A numeric adjustment to a supported engine mechanic."""

    type: ModifierType
    value: float
    skill_id: str | None = None


class MarketOffer(ContentModel):
    """A realm vendor's fixed offer for an item."""

    item_id: str = Field(min_length=1)
    buy_price: int = Field(ge=0)
    sell_price: int = Field(ge=0)


class CapBonus(ContentModel):
    """An additive increase to an engine cap."""

    cap: CapType
    value: float = Field(gt=0)


class ProjectTier(ContentModel):
    """Modifiers and cap bonuses activated at a realm project tier."""

    tier: int = Field(ge=1)
    modifiers: tuple[Modifier, ...] = ()
    cap_bonuses: tuple[CapBonus, ...] = ()


class RealmProject(ContentModel):
    """A realm's communal contribution project."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    contribution_targets: tuple[ItemQuantity, ...]
    tiers: tuple[ProjectTier, ...]


class Realm(ContentModel):
    """A player realm with availability tags and modifier sources."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    tags: tuple[str, ...]
    modifiers: tuple[Modifier, ...] = ()
    market_offers: tuple[MarketOffer, ...] = ()
    project: RealmProject


class RealmsPack(ContentModel):
    """Top-level realms content pack."""

    realms: tuple[Realm, ...]


class EstateUpgrade(ContentModel):
    """An installable estate upgrade."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    cost: tuple[ItemQuantity, ...]
    modifiers: tuple[Modifier, ...] = ()
    cap_bonuses: tuple[CapBonus, ...] = ()
    realm_tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_effect(self) -> "EstateUpgrade":
        """Require every upgrade to have at least one mechanical effect."""
        if not self.modifiers and not self.cap_bonuses:
            raise ValueError("estate upgrade needs modifiers and/or cap_bonuses")
        return self


class UpgradesPack(ContentModel):
    """Top-level estate upgrades content pack."""

    upgrades: tuple[EstateUpgrade, ...]


class CapsConfig(ContentModel):
    """Required base values for all v1 engine caps."""

    offline_hours: float = Field(gt=0)
    inventory_slots: int = Field(gt=0)
    market_listings: int = Field(gt=0)
    estate_upgrade_slots: int = Field(gt=0)


class XpLevel(ContentModel):
    """Cumulative XP required to reach a level."""

    level: int = Field(ge=1, le=99)
    xp: int = Field(ge=0)


class XpCurve(ContentModel):
    """Checked-in XP table and its documented generation formula."""

    formula: str = Field(min_length=1)
    levels: tuple[XpLevel, ...]
