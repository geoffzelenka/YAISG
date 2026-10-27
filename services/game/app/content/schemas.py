"""Validated, immutable schemas for static game content."""

from enum import StrEnum
from itertools import accumulate
from typing import Literal, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    RootModel,
    StrictInt,
    model_serializer,
    model_validator,
)

SkillCategory = Literal[
    "gathering", "refining", "manufacturing", "combat", "travel", "exploration"
]


class ContentModel(BaseModel):
    """Base class that rejects unknown content fields and prevents mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ModifierType(StrEnum):
    """Modifier mechanics understood by the game engine."""

    CYCLE_SPEED_PCT = "cycle_speed_pct"
    XP_PCT = "xp_pct"
    EXTRA_DROP_CHANCE_PCT = "extra_drop_chance_pct"


class CapType(StrEnum):
    """Upgradeable limit mechanics understood by the game engine."""

    OFFLINE_HOURS = "offline_hours"
    INVENTORY_SLOTS = "inventory_slots"
    ORDER_SLOTS = "order_slots"
    KEY_LISTINGS = "key_listings"
    BELT_SLOTS = "belt_slots"
    ESTATE_UPGRADE_SLOTS = "estate_upgrade_slots"


class ItemQuantity(ContentModel):
    """A positive quantity of an item."""

    item_id: str = Field(min_length=1)
    qty: int = Field(gt=0)


class Selector(ContentModel):
    """Exactly one item or class, optionally restricted to a tier."""

    item: str | None = Field(default=None, min_length=1)
    class_: str | None = Field(default=None, alias="class", min_length=1)
    tier: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def validate_shape(self) -> "Selector":
        """Reject mixed and empty selectors."""
        if (self.item is None) == (self.class_ is None):
            raise ValueError("selector requires exactly one item or class")
        if self.item is not None and self.tier is not None:
            raise ValueError("item selector forbids tier")
        return self

    @model_serializer
    def serialize_selector(self) -> dict[str, str | int]:
        """Publish only the keys belonging to the selected shape."""
        if self.item is not None:
            return {"item": self.item}
        result: dict[str, str | int] = {"class": self.class_ or ""}
        if self.tier is not None:
            result["tier"] = self.tier
        return result

    def matches(self, item: "Item") -> bool:
        """Return whether an item belongs to this selector."""
        if self.item is not None:
            return self.item == item.id
        return self.class_ in item.classes and (
            self.tier is None or self.tier == item.tier
        )


class ActionInput(ContentModel):
    """A selector quantity consumed each cycle."""

    selector: Selector
    quantity: int = Field(gt=0)


class Drop(ContentModel):
    """A possible output from an action."""

    item_id: str = Field(min_length=1)
    quantity_min: int = Field(gt=0)
    quantity_max: int = Field(gt=0)
    chance: float = Field(ge=0, le=1)
    off_tier: bool = False

    @model_validator(mode="after")
    def validate_quantity_range(self) -> "Drop":
        """Require an ascending inclusive quantity range."""
        if self.quantity_max < self.quantity_min:
            raise ValueError("output quantity range must ascend")
        return self


class Requirements(ContentModel):
    """References established here and enforced by the tags phase."""

    facility: str | None = None
    realm_tags: tuple[str, ...] = ()
    skill_levels: dict[str, int] = Field(default_factory=dict)
    tool_class: str | None = None

    @model_validator(mode="after")
    def validate_levels(self) -> "Requirements":
        """Reject invalid cross-skill levels."""
        if any(level < 1 or level > 100 for level in self.skill_levels.values()):
            raise ValueError("required skill levels must be between 1 and 100")
        return self


class Action(ContentModel):
    """A timed action belonging to a skill."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    tier: int = Field(ge=1, le=5)
    unlock_level: int = Field(ge=1, le=100)
    base_cycle_ms: int = Field(gt=0)
    inputs: tuple[ActionInput, ...] = ()
    outputs: tuple[Drop, ...] = ()
    xp: int = Field(gt=0)
    requires: Requirements = Requirements()
    resolver: Literal["uniform", "combat", "travel"] | None = None
    off_curve: str | None = None


class Skill(ContentModel):
    """A skill and its available actions."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: SkillCategory
    actions: tuple[Action, ...] = ()

    @model_validator(mode="after")
    def default_resolvers(self) -> "Skill":
        """Materialize the category's resolver when omitted."""
        resolver = self.category if self.category in {"combat", "travel"} else "uniform"
        object.__setattr__(
            self,
            "actions",
            tuple(
                a.model_copy(update={"resolver": resolver}) if a.resolver is None else a
                for a in self.actions
            ),
        )
        return self


class SkillsPack(ContentModel):
    """Top-level skills content pack."""

    skills: tuple[Skill, ...]


class Item(ContentModel):
    """A stackable inventory item."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    tier: int = Field(ge=1, le=5)
    classes: tuple[str, ...]
    reference_price: int = Field(gt=0)
    bullion: bool = False
    spoilage_pct_per_day: float = Field(default=0, ge=0, le=100)
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
    category: SkillCategory | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "Modifier":
        """Require one supported scope for this modifier type."""
        if self.skill_id is not None and self.category is not None:
            raise ValueError("modifier cannot specify both skill_id and category")
        if (
            self.type == ModifierType.EXTRA_DROP_CHANCE_PCT
            and self.skill_id is None
            and self.category is None
        ):
            raise ValueError("extra_drop_chance_pct requires a skill or category scope")
        return self


class MarketOffer(ContentModel):
    """A realm vendor's fixed offer for an item."""

    item_id: str = Field(min_length=1)
    buy_price: int = Field(ge=0)
    sell_price: int = Field(ge=0)


class CapBonus(ContentModel):
    """An additive increase to an engine cap."""

    cap: CapType
    value: float = Field(gt=0)


class Realm(ContentModel):
    """A realm identity whose mechanics live on a development node."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    starting_node_id: str = Field(min_length=1)
    market_offers: tuple[MarketOffer, ...] = ()


class RealmsPack(ContentModel):
    """Top-level realms content pack."""

    realms: tuple[Realm, ...]


class MapCost(ContentModel):
    """Typed cost of traversing one map edge."""

    gold: int = Field(ge=0)
    items: tuple[ItemQuantity, ...] = ()
    time_ms: int = Field(ge=0)


class MapEdge(ContentModel):
    """An undirected connection between two realms."""

    realms: tuple[str, str]
    cost: MapCost


class MapPosition(ContentModel):
    """Optional presentation coordinates for a realm."""

    x: float
    y: float


class MapPack(ContentModel):
    """Realm topology and optional presentation positions."""

    edges: tuple[MapEdge, ...]
    positions: dict[str, MapPosition] = {}


class ProfileItem(ContentModel):
    """A dormant upkeep quantity."""

    item_id: str = Field(min_length=1)
    qty: int = Field(gt=0)


class ProductionItem(ContentModel):
    """A dormant daily production quantity."""

    item_id: str = Field(min_length=1)
    per_day: int = Field(gt=0)


class EstateForm(ContentModel):
    """A content-defined estate form."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    specialty_tags: tuple[str, ...] = ()
    relocation_class: str = Field(min_length=1)
    base_caps: dict[CapType, float] = {}
    modifiers: tuple[Modifier, ...] = ()
    upkeep_profile: tuple[ProfileItem, ...] = ()
    production_profile: tuple[ProductionItem, ...] = ()


class FormTransformation(ContentModel):
    """A directed estate-form transformation and its item cost."""

    from_form: str = Field(alias="from", min_length=1)
    to_form: str = Field(alias="to", min_length=1)
    cost: tuple[ItemQuantity, ...]


class RelocationClass(ContentModel):
    """Multipliers applied when relocating an estate."""

    cost_multiplier: float = Field(ge=0)
    time_multiplier: float = Field(ge=0)


class EstateFormsPack(ContentModel):
    """Estate forms, transformations, and relocation classes."""

    forms: tuple[EstateForm, ...]
    transformations: tuple[FormTransformation, ...]
    relocation_classes: dict[str, RelocationClass]


class DevelopmentNode(ContentModel):
    """A complete realm mechanical identity."""

    id: str = Field(min_length=1)
    archetype: str = Field(min_length=1)
    name: str = Field(min_length=1)
    tags: tuple[str, ...] = ()
    modifiers: tuple[Modifier, ...] = ()
    cap_bonuses: tuple[CapBonus, ...] = ()
    upkeep_profile: tuple[ProfileItem, ...] = ()
    projects: tuple[str, ...] = ()


class DevelopmentEdge(ContentModel):
    """A directed development or regression gauge."""

    id: str = Field(min_length=1)
    from_node: str = Field(alias="from", min_length=1)
    to_node: str = Field(alias="to", min_length=1)
    progress_target: int = Field(gt=0)
    kind: str
    transition_ms: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_transition(self) -> "DevelopmentEdge":
        """Require transition time only for development edges."""
        if self.kind not in {"development", "regression"}:
            raise ValueError("edge kind must be development or regression")
        if self.kind == "development" and self.transition_ms is None:
            raise ValueError("development edge requires transition_ms")
        if self.kind == "regression" and self.transition_ms is not None:
            raise ValueError("regression edge forbids transition_ms")
        return self


class DevelopmentPack(ContentModel):
    """Realm development nodes and directed edges."""

    nodes: tuple[DevelopmentNode, ...]
    edges: tuple[DevelopmentEdge, ...]


class ProjectAward(ContentModel):
    """Progress granted to a development edge."""

    edge_id: str = Field(min_length=1)
    progress: int = Field(gt=0)


class Project(ContentModel):
    """A communal project definition."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    targets: tuple[ItemQuantity, ...]
    awards: tuple[ProjectAward, ...]


class ProjectsPack(ContentModel):
    """Top-level realm projects content pack."""

    projects: tuple[Project, ...]


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
    order_slots: int = Field(gt=0)
    key_listings: int = Field(gt=0)
    belt_slots: int = Field(gt=0)
    estate_upgrade_slots: int = Field(gt=0)


class XpLevel(ContentModel):
    """Cumulative XP required to reach a level."""

    level: int = Field(ge=1, le=100)
    xp: int = Field(ge=0)


class XpCurve(RootModel[tuple[StrictInt, ...]]):
    """Checked-in per-level XP costs."""

    model_config = ConfigDict(frozen=True)
    _levels: tuple[XpLevel, ...] = PrivateAttr(default=())

    @model_validator(mode="after")
    def validate_costs(self) -> "XpCurve":
        """Validate the complete static table."""
        if len(self.root) != 99:
            raise ValueError("XP curve must contain 99 entries")
        if self.root[0] <= 0 or any(
            b <= a for a, b in zip(self.root, self.root[1:], strict=False)
        ):
            raise ValueError("XP costs must increase after level 1")
        if sum(self.root) != 10_000_000:
            raise ValueError("XP costs must sum to 10000000")
        self._levels = tuple(
            XpLevel(level=i, xp=xp)
            for i, xp in enumerate(accumulate(self.root, initial=0), start=1)
        )
        return self

    @property
    def levels(self) -> tuple[XpLevel, ...]:
        """Return immutable cumulative thresholds computed during validation."""
        return self._levels


class ProgressionPack(ContentModel):
    """Content-defined tier thresholds and titles."""

    tier_thresholds: tuple[StrictInt, ...]
    tier_titles: tuple[str, ...]
    min_factor: float = Field(gt=0, le=1)
    min_cycle_ms: int = Field(gt=0)
    xp_bonus_cap_pct: float = Field(ge=0)
    proficiency: dict[SkillCategory, tuple[float, float, float, float, float]]
    taper: dict[SkillCategory, tuple[float, float, float, float, float]]

    @model_validator(mode="after")
    def validate_tiers(self) -> "ProgressionPack":
        """Require increasing thresholds and matching titles."""
        for table in (self.proficiency, self.taper):
            if set(table) != set(get_args(SkillCategory)):
                raise ValueError("bonus tables require every skill category")
        if any(value < 0 or value > 1 for row in self.taper.values() for value in row):
            raise ValueError("taper factors must be between zero and one")
        t = self.tier_thresholds
        if not t or t[0] != 1 or t[-1] > 100:
            raise ValueError("thresholds must start at 1 and end at or below 100")
        if any(b <= a for a, b in zip(t, t[1:], strict=False)):
            raise ValueError("thresholds must strictly increase")
        if len(t) != len(self.tier_titles) or not all(self.tier_titles):
            raise ValueError("each tier requires a title")
        return self
