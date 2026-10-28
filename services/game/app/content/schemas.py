"""Validated, immutable schemas for static game content."""

from enum import StrEnum
from itertools import accumulate
from typing import Annotated, Literal, get_args

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

    JOURNEY_SPEED_PCT = "journey_speed_pct"
    SUPPLY_REDUCTION_PCT = "supply_reduction_pct"
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


EquipmentSlot = Literal[
    "head",
    "chest",
    "gloves",
    "legs",
    "feet",
    "neck",
    "left_arm",
    "right_arm",
    "left_ring",
    "right_ring",
    "belt",
    "cape",
    "right_hand",
    "left_hand",
    "utility",
]


class Weapon(ContentModel):
    """Authored weapon data; combat interprets it in a later phase."""

    style: Literal["melee", "ranged", "magic"]
    attack_interval_ms: int = Field(gt=0)
    power: float = Field(ge=0, allow_inf_nan=False)
    accuracy: float = Field(ge=0, allow_inf_nan=False)
    damage_type: str = Field(min_length=1)


class Armour(ContentModel):
    """Authored defensive data for the combat phase."""

    armour: float = Field(ge=0, allow_inf_nan=False)
    max_hp: float = Field(ge=0, allow_inf_nan=False)


class Equipment(ContentModel):
    """Permanent equipment and its group G contributions."""

    slot: EquipmentSlot | Literal["ring", "arm"]
    two_handed: bool = False
    requires: dict[str, Annotated[int, Field(ge=1, le=100)]] = Field(
        default_factory=dict
    )
    modifiers: tuple["Modifier", ...] = ()
    cap_bonuses: dict[CapType, Annotated[float, Field(ge=0, allow_inf_nan=False)]] = (
        Field(default_factory=dict)
    )
    weapon: Weapon | None = None
    armour: Armour | None = None
    tool_class: str | None = Field(default=None, min_length=1)
    belt_slots: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_equipment(self) -> "Equipment":
        """Reject combinations incompatible with the slot rules."""
        if self.slot != "cape" and any(
            m.type == ModifierType.XP_PCT for m in self.modifiers
        ):
            raise ValueError("xp_pct gear requires the cape slot")
        if (
            self.two_handed or self.tool_class is not None
        ) and self.slot != "right_hand":
            raise ValueError("two-handed items and tools require right_hand")
        if self.belt_slots is not None and self.slot != "belt":
            raise ValueError("belt_slots requires the belt slot")
        return self


class Item(ContentModel):
    """A stackable inventory item."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    tier: int = Field(ge=1, le=5)
    classes: tuple[str, ...]
    reference_price: int = Field(gt=0)
    warehouse_cap: int | None = Field(default=None, gt=0)
    equip: Equipment | None = None
    instanced: bool = False
    bullion: bool = False
    spoilage_pct_per_day: float = Field(default=0, ge=0, le=100)
    stack_limit: int = Field(default=2_147_483_647, gt=0)
    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_bullion(self) -> "Item":
        """Keep the bullion flag and selector class equivalent."""
        if self.bullion != ("bullion" in self.classes):
            raise ValueError("bullion flag must match membership in the bullion class")
        return self


class ItemsPack(ContentModel):
    """Top-level items content pack."""

    items: tuple[Item, ...]


class Modifier(ContentModel):
    """A numeric adjustment to a supported engine mechanic."""

    type: ModifierType
    value: float = Field(allow_inf_nan=False)
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


class CapBonus(ContentModel):
    """An additive increase to an engine cap."""

    cap: CapType
    value: float = Field(gt=0)


class Realm(ContentModel):
    """A realm identity whose mechanics live on a development node."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    starting_node_id: str = Field(min_length=1)
    isolated: bool = False


class RealmsPack(ContentModel):
    """Top-level realms content pack."""

    realms: tuple[Realm, ...]


class TravelProfile(ContentModel):
    """Movement multipliers and traversable terrain."""

    time_mult: float = Field(gt=0, allow_inf_nan=False)
    supply_mult: float = Field(ge=0, allow_inf_nan=False)
    terrains: tuple[Literal["land", "water"], ...] = Field(min_length=1)


class TravelTierBenefit(ContentModel):
    """Travel's group P percentages at a given tier."""

    journey_speed_pct: float = Field(ge=0, allow_inf_nan=False)
    supply_reduction_pct: float = Field(ge=0, allow_inf_nan=False)


class MapEdge(ContentModel):
    """A directed or bidirectional travel connection."""

    id: str = Field(min_length=1)
    a: str = Field(min_length=1)
    b: str = Field(min_length=1)
    terrain: Literal["land", "water"]
    base_time_s: float = Field(gt=0, allow_inf_nan=False)
    supplies: tuple[ActionInput, ...] = ()
    min_travel_level: int = Field(ge=1, le=100)
    base_loss_pct: float = Field(ge=0, le=100, allow_inf_nan=False)
    one_way: bool


class MapPosition(ContentModel):
    """Optional presentation coordinates for a realm."""

    x: float
    y: float


class MapPack(ContentModel):
    """Realm topology and optional presentation positions."""

    edges: tuple[MapEdge, ...]
    positions: dict[str, MapPosition] = {}


class BuildCost(ContentModel):
    """Gold and selector goods paid to acquire a form."""

    gold: int = Field(ge=0)
    goods: tuple[ActionInput, ...] = ()


class TagUpkeep(ContentModel):
    """Daily selector demand added to the holder."""

    selector: Selector
    per_day: float = Field(gt=0, allow_inf_nan=False)


class ProductionItem(ContentModel):
    """Daily production credited to realm stores."""

    item_id: str = Field(min_length=1)
    per_day: float = Field(gt=0, allow_inf_nan=False)


class EstateForm(ContentModel):
    """A content-defined estate form."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    tags: tuple[str, ...] = ()
    requires_realm_tags: tuple[str, ...] = ()
    tier: int = Field(ge=1, le=5)
    build_cost: BuildCost
    upgrade_slots: int = Field(ge=0)
    transforms_to: tuple[str, ...] = ()
    regresses_to: str | None = None
    mobility: Literal["mobile", "fixed"]
    travel_profile: TravelProfile | None

    @model_validator(mode="after")
    def validate_mobility(self) -> "EstateForm":
        """Only mobile forms have a travel profile."""
        if (self.mobility == "mobile") != (self.travel_profile is not None):
            raise ValueError("mobile forms require a profile; fixed forms forbid it")
        return self

    cap_bonuses: tuple[CapBonus, ...] = ()
    modifiers: tuple[Modifier, ...] = ()
    upkeep: tuple[TagUpkeep, ...] = ()
    production: tuple[ProductionItem, ...] = ()


class EstateFormsPack(ContentModel):
    """Estate forms and their upgrade graph."""

    forms: tuple[EstateForm, ...]


class NodeRegression(ContentModel):
    """The lower node reached after a regression."""

    to_node: str = Field(min_length=1)


class NodeUpgrade(ContentModel):
    """A content-authored upgrade or change of realm type."""

    id: str = Field(min_length=1)
    to_node: str = Field(min_length=1)
    kind: Literal["tier_up", "morph"]
    required_tags: tuple[str, ...] = ()
    fee_gold: int = Field(ge=0)


class DevelopmentNode(ContentModel):
    """A realm type at a tier, with its available projects and transitions."""

    id: str = Field(min_length=1)
    tier: int = Field(ge=0, le=5)
    realm_type: str = Field(min_length=1)
    name: str = Field(min_length=1)
    inherent_tags: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    modifiers: tuple[Modifier, ...] = ()
    cap_bonuses: tuple[CapBonus, ...] = ()
    upkeep: tuple[TagUpkeep, ...] = ()
    projects: tuple[str, ...] = ()
    carried_tags: tuple[str, ...] = ()
    upgrades: tuple[NodeUpgrade, ...] = ()
    regression: NodeRegression | None
    reserve_days: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    cap_days: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    margin_pct: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class DevelopmentPack(ContentModel):
    """Realm development graph, with edges owned by their source nodes."""

    nodes: tuple[DevelopmentNode, ...]


class ProjectKickoff(ContentModel):
    """Payment and eligibility for starting a project."""

    gold: int = Field(ge=0)
    goods: tuple[ActionInput, ...] = ()
    who: Literal["residents", "anyone"]


class Project(ContentModel):
    """A non-repeatable project granting a single tag."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    grants_tag: str = Field(min_length=1)
    kickoff: ProjectKickoff
    cost: tuple[ActionInput, ...]
    build_seconds: float = Field(gt=0, allow_inf_nan=False)
    realm_completion_days: float = Field(gt=0, allow_inf_nan=False)
    requires_tags: tuple[str, ...] = ()
    repeatable: Literal[False] = False


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
    requires_realm_tags: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_effect(self) -> "EstateUpgrade":
        """Require every upgrade to have at least one mechanical effect."""
        if not self.modifiers and not self.cap_bonuses and not self.tags:
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


class LintConfig(ContentModel):
    """Designer-selected rate curve and warning tolerance."""

    g: float = Field(gt=1, allow_inf_nan=False)
    tolerance_pct: float = Field(ge=0, le=100, allow_inf_nan=False)


class ProgressionPack(ContentModel):
    """Content-defined tier thresholds and titles."""

    basic_mobile_form: str = Field(min_length=1)
    visit_profile: TravelProfile
    travel_xp_per_second: float = Field(gt=0, allow_inf_nan=False)
    tier_benefits: dict[Literal["travel"], tuple[TravelTierBenefit, ...]]
    lint: LintConfig
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
        if len(self.tier_benefits.get("travel", ())) != len(self.tier_thresholds):
            raise ValueError("Travel benefits require one row per tier")
        return self


class DecayStage(StrEnum):
    """Shared realm and estate health stages."""

    FED = "fed"
    STRAINED = "strained"
    FALTERING = "faltering"
    FAILING = "failing"
    REGRESSED = "regressed"


class MintEffect(ContentModel):
    """Reference value consumed by a mint per day."""

    value_per_day: float = Field(gt=0, allow_inf_nan=False)


class TagEffects(ContentModel):
    """Validated effects consumed by later economy and market phases."""

    market_access: bool = False
    caravan_access: bool = False
    mint: MintEffect | None = None
    edge_loss_reduction_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    reserve_days_delta: float = Field(default=0, allow_inf_nan=False)


class Tag(ContentModel):
    """Facility, numeric bonus, malus or access emitted by a holder."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: Literal["facility", "bonus", "malus", "access"]
    modifiers: tuple[Modifier, ...] = ()
    cap_bonuses: dict[CapType, Annotated[float, Field(gt=0, allow_inf_nan=False)]] = {}
    upkeep: tuple[TagUpkeep, ...] = ()
    effects: TagEffects = TagEffects()


class TagsPack(ContentModel):
    """Definitions of all emitted tags."""

    tags: tuple[Tag, ...]


class DecayConfig(ContentModel):
    """Stage weakening shared by realms and estates."""

    faltering_factor: float = Field(ge=0, le=1)


class GaugeConfig(ContentModel):
    """Hunger measured in equivalent days of missing upkeep."""

    max: float = Field(default=10, gt=0, allow_inf_nan=False)
    recovery_per_day: float = Field(default=1, ge=0, allow_inf_nan=False)
    strained_threshold: float = Field(default=0.5, ge=0, allow_inf_nan=False)
    faltering_threshold: float = Field(default=2, gt=0, allow_inf_nan=False)
    failing_threshold: float = Field(default=4, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_thresholds(self) -> "GaugeConfig":
        """Require stages to be reachable in their advertised order."""
        if not (
            self.strained_threshold
            < self.faltering_threshold
            < self.failing_threshold
            < self.max
        ):
            raise ValueError("gauge thresholds must increase below gauge.max")
        return self


class ShedConfig(ContentModel):
    """Asset loss and recovery rates per day."""

    base_per_day: float = Field(default=0.5, ge=0, allow_inf_nan=False)
    per_gauge_day: float = Field(default=0.5, ge=0, allow_inf_nan=False)
    recovery_per_day: float = Field(default=1, ge=0, allow_inf_nan=False)


class TransitionConfig(ContentModel):
    """Content-owned transition window in days."""

    duration_days: float = Field(default=7, gt=0, allow_inf_nan=False)


class ProjectConfig(ContentModel):
    """Idle erosion and retry settings for project attempts."""

    idle_grace_days: float = Field(default=2, ge=0, allow_inf_nan=False)
    erosion_pct_per_day: float = Field(default=20, gt=0, le=100, allow_inf_nan=False)
    fail_cooldown_hours: float = Field(default=36, ge=0, allow_inf_nan=False)


class TickConfig(ContentModel):
    """Realm tick cadence and bounded lazy catch-up."""

    per_day: int = Field(default=24, gt=0, le=86400)
    max_catchup: int = Field(default=72, gt=0)


class EstateConfig(ContentModel):
    """Estate resale settings."""

    sale_markup_pct: int = Field(default=15, gt=0)


class MarketConfig(ContentModel):
    """Scarcity curve, margin and public treasury health boundaries."""

    tax_pct: float = Field(default=5, ge=0, le=100, allow_inf_nan=False)
    tax_burn_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    order_days: int = Field(default=14, ge=1)
    retention_days: int = Field(default=30, ge=1)
    lifecycle_interval_seconds: int = Field(default=300, ge=1)
    f: float = Field(default=0.33, gt=0, allow_inf_nan=False)
    c: float = Field(default=2.1, gt=0, allow_inf_nan=False)
    k: int = Field(default=3, ge=1)
    m: float = Field(default=0.25, ge=0, allow_inf_nan=False)
    band_days: tuple[float, float, float, float] = (1, 3, 7, 14)
    band_hysteresis_pct: float = Field(default=10, ge=0, lt=100, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid_curve(self) -> "MarketConfig":
        """Reject inverted scarcity and unordered health boundaries."""
        if self.c < self.f:
            raise ValueError("market c must be at least f")
        if not all(0 < n < float("inf") for n in self.band_days) or any(
            a >= b for a, b in zip(self.band_days, self.band_days[1:], strict=False)
        ):
            raise ValueError("market band_days must be positive and increasing")
        return self


class VoteConfig(ContentModel):
    """Authored vote stock requirement, duration and failed-ballot cooldown."""

    min_stock_days: float = Field(default=3, gt=0, allow_inf_nan=False)
    duration_hours: float = Field(default=72, gt=0, allow_inf_nan=False)
    fail_cooldown_hours: float = Field(default=72, ge=0, allow_inf_nan=False)


class CaravanConfig(ContentModel):
    """Authored cadence, friction and shared dispatch capacity."""

    pass_every_ticks: int = Field(default=6, ge=1)
    fee_pct_per_hour: float = Field(default=1, gt=0, allow_inf_nan=False)
    fee_burn_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    time_mult: float = Field(default=2, gt=0, allow_inf_nan=False)
    capacity_value_per_pass: int = Field(default=1000, gt=0)


class EconomyPack(ContentModel):
    """Shared economy settings."""

    caravan: CaravanConfig = CaravanConfig()
    coinage_multiple: float = Field(default=1.2, ge=0, allow_inf_nan=False)
    reserve_days: float = Field(default=3, ge=0, allow_inf_nan=False)
    cap_days: float = Field(default=10, gt=0, allow_inf_nan=False)
    warehouse_value_cap: int = Field(gt=0)
    market: MarketConfig = MarketConfig()
    decay: DecayConfig
    gauge: GaugeConfig = GaugeConfig()
    shed: ShedConfig = ShedConfig()
    estate: EstateConfig = EstateConfig()
    transition: TransitionConfig = TransitionConfig()
    vote: VoteConfig = VoteConfig()
    project: ProjectConfig = ProjectConfig()
    tick: TickConfig = TickConfig()


class SeedRealm(ContentModel):
    """Initial holdings for a world realm; stores use whole units."""

    realm_id: str
    treasury: int = Field(ge=0)
    stores: tuple[ItemQuantity, ...] = ()
    estates: tuple[str, ...] = ()


class WorldSeedPack(ContentModel):
    """Private, versioned world creation data."""

    realms: tuple[SeedRealm, ...]


Equipment.model_rebuild()
