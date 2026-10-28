"""Load, validate, cross-check, and hash static content packs."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from app.content.schemas import (
    Action,
    CapsConfig,
    DevelopmentNode,
    DevelopmentPack,
    EconomyPack,
    EstateForm,
    EstateFormsPack,
    EstateUpgrade,
    Item,
    ItemsPack,
    MapPack,
    ProgressionPack,
    Project,
    ProjectsPack,
    Realm,
    RealmsPack,
    Skill,
    SkillsPack,
    Tag,
    TagsPack,
    UpgradesPack,
    WorldSeedPack,
    XpCurve,
)

if TYPE_CHECKING:
    from app.engine.caravans import Route

PUBLIC_PACKS = (
    "skills",
    "items",
    "realms",
    "upgrades",
    "caps",
    "map",
    "estate_forms",
    "development",
    "projects",
    "progression",
    "tags",
    "economy",
)
_KNOWN_PACKS = {*PUBLIC_PACKS, "xp_curve", "world_seed"}


class ContentError(RuntimeError):
    """Raised when content cannot safely be loaded by the engine."""


@dataclass(frozen=True)
class ContentManifest:
    """Hashes used to identify the complete content and public packs."""

    version: str
    packs: MappingProxyType[str, str]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable manifest."""
        return {"version": self.version, "packs": dict(self.packs)}


@dataclass(frozen=True)
class ContentIndex:
    """Immutable, typed lookup index for validated content."""

    world_seed: WorldSeedPack
    world_seed_version: str
    tags: tuple[Tag, ...]
    economy: EconomyPack
    manifest: ContentManifest
    skills: tuple[Skill, ...]
    items: tuple[Item, ...]
    realms: tuple[Realm, ...]
    upgrades: tuple[EstateUpgrade, ...]
    map: MapPack
    estate_forms: tuple[EstateForm, ...]
    development_nodes: tuple[DevelopmentNode, ...]
    projects: tuple[Project, ...]
    caps: CapsConfig
    xp_curve: XpCurve
    progression: ProgressionPack
    pack_payloads: MappingProxyType[str, bytes]
    _skills_by_id: MappingProxyType[str, Skill]
    _actions_by_id: MappingProxyType[str, Action]
    _actions_by_skill: MappingProxyType[str, tuple[Action, ...]]
    _items_by_id: MappingProxyType[str, Item]
    _realms_by_id: MappingProxyType[str, Realm]
    _upgrades_by_id: MappingProxyType[str, EstateUpgrade]
    _forms_by_id: MappingProxyType[str, EstateForm]
    _nodes_by_id: MappingProxyType[str, DevelopmentNode]
    _projects_by_id: MappingProxyType[str, Project]

    @cached_property
    def caravan_routes(self) -> dict[tuple[str, str], "Route"]:
        """Cache content-only remoteness once per loaded index."""
        from app.engine.caravans import remoteness

        return remoteness(self.map)

    def skill(self, skill_id: str) -> Skill:
        """Look up a skill."""
        return self._skills_by_id[skill_id]

    def action(self, action_id: str) -> Action:
        """Look up an action."""
        return self._actions_by_id[action_id]

    def actions_for_skill(self, skill_id: str) -> tuple[Action, ...]:
        """Return all actions for a skill in content order."""
        return self._actions_by_skill[skill_id]

    def item(self, item_id: str) -> Item:
        """Look up an item."""
        return self._items_by_id[item_id]

    def realm(self, realm_id: str) -> Realm:
        """Look up a realm."""
        return self._realms_by_id[realm_id]

    def upgrade(self, upgrade_id: str) -> EstateUpgrade:
        """Look up an estate upgrade."""
        return self._upgrades_by_id[upgrade_id]

    def estate_form(self, form_id: str) -> EstateForm:
        """Look up an estate form."""
        return self._forms_by_id[form_id]

    def development_node(self, node_id: str) -> DevelopmentNode:
        """Look up a development node."""
        return self._nodes_by_id[node_id]

    def project(self, project_id: str) -> Project:
        """Look up a realm project."""
        return self._projects_by_id[project_id]

    def with_overrides(
        self,
        *,
        actions: Iterable[Action] = (),
        items: Iterable[Item] = (),
        upgrades: Iterable[EstateUpgrade] = (),
    ) -> "ContentIndex":
        """Return an immutable copy with selected test definitions replaced."""
        action_overrides = {value.id: value for value in actions}
        item_overrides = {value.id: value for value in items}
        upgrade_overrides = {value.id: value for value in upgrades}
        unknown = set(action_overrides) - set(self._actions_by_id)
        if unknown:
            raise ValueError(f"cannot override unknown actions: {sorted(unknown)}")
        skills = tuple(
            skill.model_copy(
                update={
                    "actions": tuple(
                        action_overrides.get(action.id, action)
                        for action in skill.actions
                    )
                }
            )
            for skill in self.skills
        )
        resolved_items = tuple(item_overrides.get(v.id, v) for v in self.items) + tuple(
            v for key, v in item_overrides.items() if key not in self._items_by_id
        )
        resolved_upgrades = tuple(
            upgrade_overrides.get(v.id, v) for v in self.upgrades
        ) + tuple(
            v for key, v in upgrade_overrides.items() if key not in self._upgrades_by_id
        )
        actions_by_skill = {skill.id: skill.actions for skill in skills}
        actions_by_id = {
            action.id: action for skill in skills for action in skill.actions
        }
        return replace(
            self,
            skills=skills,
            items=resolved_items,
            upgrades=resolved_upgrades,
            _actions_by_id=MappingProxyType(actions_by_id),
            _actions_by_skill=MappingProxyType(actions_by_skill),
            _items_by_id=MappingProxyType({v.id: v for v in resolved_items}),
            _upgrades_by_id=MappingProxyType({v.id: v for v in resolved_upgrades}),
        )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _load_model[ModelT: BaseModel](
    directory: Path, pack: str, model: type[ModelT]
) -> ModelT:
    path = directory / f"{pack}.json"
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"), strict=True)
    except FileNotFoundError as error:
        raise ContentError(f"required content pack is missing: {path}") from error
    except (json.JSONDecodeError, ValidationError) as error:
        raise ContentError(f"invalid content in {path}: {error}") from error


def _unique[ModelT: BaseModel](
    values: Iterable[ModelT], kind: str
) -> dict[str, ModelT]:
    result: dict[str, ModelT] = {}
    for value in values:
        identifier = getattr(value, "id", None)
        if not isinstance(identifier, str):
            raise ContentError(f"{kind} has no string id")
        if identifier in result:
            raise ContentError(f"duplicate {kind} id: {identifier}")
        result[identifier] = value
    return result


def _require_items(values: Iterable[str], known: set[str], context: str) -> None:
    for item_id in values:
        if item_id not in known:
            raise ContentError(f"unknown item_id {item_id!r} in {context}")


def _validate_development(
    nodes: dict[str, DevelopmentNode],
    projects: dict[str, Project],
    tags: set[str],
    items: dict[str, Item],
) -> None:
    """Check transition prerequisites, regression connectivity and project inputs."""
    roots = [node.id for node in nodes.values() if node.regression is None]
    if len(roots) != 1:
        raise ContentError("development must have exactly one barren root")
    root = roots[0]
    if nodes[root].tier != 0 or nodes[root].upkeep:
        raise ContentError("barren root must have tier zero and no upkeep")
    for node in nodes.values():
        if set(node.projects) - set(projects):
            raise ContentError(f"node {node.id} references an unknown project")
        if set(node.carried_tags) - tags:
            raise ContentError(f"unknown carried tag in node {node.id}")
        available = {projects[p].grants_tag for p in node.projects} | set(
            node.carried_tags
        )
        _unique(node.upgrades, f"upgrade in node {node.id}")
        for edge in node.upgrades:
            if edge.to_node not in nodes or edge.to_node == node.id:
                raise ContentError(f"invalid upgrade destination in node {node.id}")
            if set(edge.required_tags) - available:
                raise ContentError(f"unsatisfiable required_tags in node {node.id}")
        visited: set[str] = set()
        current = node.id
        while current != root:
            if current in visited or current not in nodes:
                raise ContentError(f"node {node.id} cannot regress to barren root")
            visited.add(current)
            regression = nodes[current].regression
            if regression is None:
                raise ContentError(f"node {node.id} cannot regress to barren root")
            current = regression.to_node
        for upkeep in node.upkeep:
            if not any(upkeep.selector.matches(item) for item in items.values()):
                raise ContentError(f"empty upkeep selector in node {node.id}")
    for project in projects.values():
        if {project.grants_tag, *project.requires_tags} - tags:
            raise ContentError(f"unknown tag in project {project.id}")
        for entry in (*project.kickoff.goods, *project.cost):
            if not any(entry.selector.matches(item) for item in items.values()):
                raise ContentError(f"empty selector in project {project.id}")


def _validate(
    skills: dict[str, Skill],
    actions: dict[str, Action],
    items: dict[str, Item],
    realms: dict[str, Realm],
    upgrades: dict[str, EstateUpgrade],
    map_pack: MapPack,
    forms_pack: EstateFormsPack,
    nodes: dict[str, DevelopmentNode],
    projects: dict[str, Project],
    xp_curve: XpCurve,
    progression: ProgressionPack,
    tag_definitions: tuple[Tag, ...],
) -> None:
    # Keep this local to avoid the loader/engine package import cycle.
    from app.engine.levels import tier_for_level

    item_ids = set(items)
    tags = {tag.id for tag in tag_definitions}
    for item in items.values():
        if item.consumable is not None and item.consumable.buff is not None:
            for modifier in item.consumable.buff.modifiers:
                if modifier.skill_id is not None and modifier.skill_id not in skills:
                    raise ContentError(
                        f"unknown consumable modifier skill in {item.id}"
                    )
        if item.equip is not None:
            if set(item.equip.requires) - set(skills):
                raise ContentError(f"unknown equipment skill in {item.id}")
            for modifier in item.equip.modifiers:
                if modifier.skill_id is not None and modifier.skill_id not in skills:
                    raise ContentError(f"unknown equipment modifier skill in {item.id}")
    for action in actions.values():
        if action.skill_id not in skills:
            raise ContentError(
                f"unknown skill_id {action.skill_id!r} in action {action.id}"
            )
        if action.tier != tier_for_level(
            action.unlock_level, progression.tier_thresholds
        ):
            raise ContentError(f"action {action.id} tier differs from unlock level")
        for entry in action.inputs:
            matches = [item for item in items.values() if entry.selector.matches(item)]
            if not matches:
                raise ContentError(f"selector matches no item in action {action.id}")
            if any(item.tier > action.tier for item in matches):
                raise ContentError(f"higher-tier input in action {action.id}")
        _require_items((v.item_id for v in action.outputs), item_ids, action.id)
        if any(
            items[v.item_id].tier != action.tier and not v.off_tier
            for v in action.outputs
        ):
            raise ContentError(f"output tier differs in action {action.id}")
        required = action.requires
        if set(required.realm_tags) - tags or (
            required.facility is not None and required.facility not in tags
        ):
            raise ContentError(f"unknown requirement tag in action {action.id}")
        if (
            required.facility is not None
            and next(t for t in tag_definitions if t.id == required.facility).kind
            != "facility"
        ):
            raise ContentError(f"non-facility requirement in action {action.id}")
        if set(required.skill_levels) - set(skills):
            raise ContentError(f"unknown required skill in action {action.id}")
        if required.tool_class is not None and not any(
            item.equip is not None and item.equip.tool_class == required.tool_class
            for item in items.values()
        ):
            raise ContentError(f"unknown tool class in action {action.id}")
    for realm in realms.values():
        if realm.starting_node_id not in nodes:
            raise ContentError(
                "unknown starting_node_id "
                f"{realm.starting_node_id!r} in realm {realm.id}"
            )
    _unique(map_pack.edges, "map edge")
    for map_edge in map_pack.edges:
        if map_edge.a not in realms or map_edge.b not in realms:
            raise ContentError(f"unknown realm in map edge {map_edge.id}")
        if map_edge.a == map_edge.b:
            raise ContentError("map edges cannot be self-edges")
        for entry in map_edge.supplies:
            if not any(entry.selector.matches(item) for item in items.values()):
                raise ContentError(f"empty supply selector in edge {map_edge.id}")
    if set(map_pack.positions) - set(realms):
        raise ContentError("map position references an unknown realm")
    forms = _unique(forms_pack.forms, "estate form")
    for form in forms.values():
        for selector in (
            *(line.selector for line in form.build_cost.goods),
            *(line.selector for line in form.upkeep),
        ):
            if not any(selector.matches(item) for item in items.values()):
                raise ContentError(f"empty selector in form {form.id}")
        _require_items((v.item_id for v in form.production), item_ids, form.id)
        for target_id in (
            *form.transforms_to,
            *((form.regresses_to,) if form.regresses_to else ()),
        ):
            if target_id not in forms:
                raise ContentError(f"unknown form {target_id} in form {form.id}")
            if forms[target_id].mobility != form.mobility:
                raise ContentError(f"form edge changes mobility in {form.id}")
        if form.regresses_to and forms[form.regresses_to].tier >= form.tier:
            raise ContentError(f"regression must lower tier in form {form.id}")
    basic = forms.get(progression.basic_mobile_form)
    if basic is None or basic.mobility != "mobile" or basic.upkeep or basic.production:
        raise ContentError(
            "basic_mobile_form must exist, be mobile, and have no upkeep or production"
        )
    _validate_development(nodes, projects, tags, items)
    for upgrade in upgrades.values():
        _require_items(
            (v.item_id for v in upgrade.cost), item_ids, f"upgrade {upgrade.id}"
        )
        if set(upgrade.requires_realm_tags) - tags:
            raise ContentError(f"unknown realm tags in upgrade {upgrade.id}")


def load_content(content_dir: Path) -> ContentIndex:
    """Load all required JSON packs and return an immutable content index."""
    unknown = {path.stem for path in content_dir.rglob("*.json")} - _KNOWN_PACKS
    if unknown:
        raise ContentError(f"unrecognized content packs: {sorted(unknown)}")
    skills_pack = _load_model(content_dir, "skills", SkillsPack)
    items_pack = _load_model(content_dir, "items", ItemsPack)
    realms_pack = _load_model(content_dir, "realms", RealmsPack)
    upgrades_pack = _load_model(content_dir, "upgrades", UpgradesPack)
    caps = _load_model(content_dir, "caps", CapsConfig)
    map_pack = _load_model(content_dir, "map", MapPack)
    forms_pack = _load_model(content_dir, "estate_forms", EstateFormsPack)
    development = _load_model(content_dir, "development", DevelopmentPack)
    projects_pack = _load_model(content_dir, "projects", ProjectsPack)
    xp_curve = _load_model(content_dir, "xp_curve", XpCurve)
    tags_pack = _load_model(content_dir, "tags", TagsPack)
    economy = _load_model(content_dir, "economy", EconomyPack)
    if economy.cap_days < economy.vote.min_stock_days:
        raise ContentError("cap_days must cover vote.min_stock_days in economy")
    progression = _load_model(content_dir, "progression", ProgressionPack)
    world_seed = _load_model(content_dir, "world_seed", WorldSeedPack)
    packs: dict[str, BaseModel] = {
        "world_seed": world_seed,
        "tags": tags_pack,
        "economy": economy,
        "skills": skills_pack,
        "items": items_pack,
        "realms": realms_pack,
        "upgrades": upgrades_pack,
        "caps": caps,
        "map": map_pack,
        "estate_forms": forms_pack,
        "development": development,
        "projects": projects_pack,
        "xp_curve": xp_curve,
        "progression": progression,
    }
    skills = _unique(skills_pack.skills, "skill")
    actions = _unique((a for s in skills.values() for a in s.actions), "action")
    items = _unique(items_pack.items, "item")
    realms = _unique(realms_pack.realms, "realm")
    upgrades = _unique(upgrades_pack.upgrades, "upgrade")
    nodes = _unique(development.nodes, "development node")
    projects = _unique(projects_pack.projects, "project")
    tag_ids = set(_unique(tags_pack.tags, "tag"))
    holders: tuple[DevelopmentNode | EstateForm | EstateUpgrade, ...] = (
        *nodes.values(),
        *forms_pack.forms,
        *upgrades.values(),
    )
    for holder in holders:
        emitted = (
            holder.inherent_tags if isinstance(holder, DevelopmentNode) else holder.tags
        )
        required = getattr(holder, "requires_realm_tags", ())
        if (set(emitted) | set(required)) - tag_ids:
            raise ContentError(f"unknown tag in {holder.id}")
    for node in nodes.values():
        if set(node.actions) - set(actions):
            raise ContentError(f"unknown action in node {node.id}")
    for tag in tags_pack.tags:
        for entry in tag.upkeep:
            if not any(entry.selector.matches(item) for item in items.values()):
                raise ContentError(f"empty upkeep selector in tag {tag.id}")
        for modifier in tag.modifiers:
            if modifier.skill_id is not None and modifier.skill_id not in skills:
                raise ContentError(f"unknown skill in tag {tag.id}")
    _validate(
        skills,
        actions,
        items,
        realms,
        upgrades,
        map_pack,
        forms_pack,
        nodes,
        projects,
        xp_curve,
        progression,
        tags_pack.tags,
    )
    upkeep_holders: tuple[DevelopmentNode | EstateForm | Tag, ...] = (
        *nodes.values(),
        *forms_pack.forms,
        *tags_pack.tags,
    )
    upkeep_selectors = [
        line.selector for holder in upkeep_holders for line in holder.upkeep
    ]
    demand_selectors = upkeep_selectors + [
        line.selector for project in projects.values() for line in project.cost
    ]
    for selector in demand_selectors:
        prices = {i.reference_price for i in items.values() if selector.matches(i)}
        if selector.class_ is not None and len(prices) > 1:
            raise ContentError(
                f"mixed reference prices in ordinary demand selector {selector}"
            )
    for node in nodes.values():
        possible_tags = (
            set(node.inherent_tags)
            | set(node.carried_tags)
            | {projects[p].grants_tag for p in node.projects}
        )
        largest_delta = sum(
            max(0, t.effects.reserve_days_delta)
            for t in tags_pack.tags
            if t.id in possible_tags
        )
        reserve = (
            economy.reserve_days if node.reserve_days is None else node.reserve_days
        )
        cap = economy.cap_days if node.cap_days is None else node.cap_days
        if cap < economy.vote.min_stock_days:
            raise ContentError(
                f"cap_days must cover vote.min_stock_days in node {node.id}"
            )
        if cap <= reserve + largest_delta + economy.transition.duration_days:
            raise ContentError(
                f"cap_days must exceed largest reserve in node {node.id}"
            )
    seeds = {s.realm_id: s for s in world_seed.realms}
    if len(seeds) != len(world_seed.realms) or set(seeds) != {
        r.id for r in realms.values() if not r.isolated
    }:
        raise ContentError("world_seed must name each non-isolated realm exactly once")
    forms_by_id = {f.id: f for f in forms_pack.forms}
    for seed in seeds.values():
        _require_items((s.item_id for s in seed.stores), set(items), "world_seed")
        if len({s.item_id for s in seed.stores}) != len(seed.stores):
            raise ContentError("duplicate world_seed store item")
        if set(seed.estates) - set(forms_by_id):
            raise ContentError("unknown world_seed estate form")
        if any(forms_by_id[form_id].mobility != "fixed" for form_id in seed.estates):
            raise ContentError("world_seed estates must use fixed forms")
    canonical = {
        name: model.model_dump(mode="json", by_alias=True)
        for name, model in packs.items()
    }
    # Publishing a hash of seed treasuries would permit offline guessing.
    seed_version = hashlib.sha256(
        _canonical_bytes(canonical.pop("world_seed"))
    ).hexdigest()
    payloads = {name: _canonical_bytes(canonical[name]) for name in PUBLIC_PACKS}
    hashes = {
        name: hashlib.sha256(value).hexdigest() for name, value in payloads.items()
    }
    forms = _unique(forms_pack.forms, "estate form")
    return ContentIndex(
        world_seed,
        seed_version,
        tags_pack.tags,
        economy,
        ContentManifest(
            hashlib.sha256(_canonical_bytes(canonical)).hexdigest(),
            MappingProxyType(hashes),
        ),
        tuple(skills.values()),
        tuple(items.values()),
        tuple(realms.values()),
        tuple(upgrades.values()),
        map_pack,
        tuple(forms.values()),
        tuple(nodes.values()),
        tuple(projects.values()),
        caps,
        xp_curve,
        progression,
        MappingProxyType(payloads),
        MappingProxyType(skills),
        MappingProxyType(actions),
        MappingProxyType({k: v.actions for k, v in skills.items()}),
        MappingProxyType(items),
        MappingProxyType(realms),
        MappingProxyType(upgrades),
        MappingProxyType(forms),
        MappingProxyType(nodes),
        MappingProxyType(projects),
    )
