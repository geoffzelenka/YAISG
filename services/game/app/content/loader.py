"""Load, validate, cross-check, and hash static content packs."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel, ValidationError

from app.content.schemas import (
    Action,
    CapsConfig,
    DevelopmentEdge,
    DevelopmentNode,
    DevelopmentPack,
    EstateForm,
    EstateFormsPack,
    EstateUpgrade,
    Item,
    ItemsPack,
    MapPack,
    Project,
    ProjectsPack,
    Realm,
    RealmsPack,
    Skill,
    SkillsPack,
    UpgradesPack,
    XpCurve,
)

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
)
_KNOWN_PACKS = {*PUBLIC_PACKS, "xp_curve"}


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

    manifest: ContentManifest
    skills: tuple[Skill, ...]
    items: tuple[Item, ...]
    realms: tuple[Realm, ...]
    upgrades: tuple[EstateUpgrade, ...]
    map: MapPack
    estate_forms: tuple[EstateForm, ...]
    development_nodes: tuple[DevelopmentNode, ...]
    development_edges: tuple[DevelopmentEdge, ...]
    projects: tuple[Project, ...]
    caps: CapsConfig
    xp_curve: XpCurve
    relocation_classes: MappingProxyType[str, Any]
    pack_payloads: MappingProxyType[str, bytes]
    _skills_by_id: MappingProxyType[str, Skill]
    _actions_by_id: MappingProxyType[str, Action]
    _actions_by_skill: MappingProxyType[str, tuple[Action, ...]]
    _items_by_id: MappingProxyType[str, Item]
    _realms_by_id: MappingProxyType[str, Realm]
    _upgrades_by_id: MappingProxyType[str, EstateUpgrade]
    _forms_by_id: MappingProxyType[str, EstateForm]
    _nodes_by_id: MappingProxyType[str, DevelopmentNode]

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
        return model.model_validate(json.loads(path.read_text(encoding="utf-8")))
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


def _validate(
    skills: dict[str, Skill],
    actions: dict[str, Action],
    items: dict[str, Item],
    realms: dict[str, Realm],
    upgrades: dict[str, EstateUpgrade],
    map_pack: MapPack,
    forms_pack: EstateFormsPack,
    nodes: dict[str, DevelopmentNode],
    edges: dict[str, DevelopmentEdge],
    projects: dict[str, Project],
    xp_curve: XpCurve,
) -> None:
    item_ids = set(items)
    tags = {tag for node in nodes.values() for tag in node.tags}
    for action in actions.values():
        if action.skill_id not in skills:
            raise ContentError(
                f"unknown skill_id {action.skill_id!r} in action {action.id}"
            )
        _require_items(
            (v.item_id for v in action.inputs),
            item_ids,
            f"action {action.id} inputs",
        )
        _require_items(
            (v.item_id for v in action.drops),
            item_ids,
            f"action {action.id} drops",
        )
        if set(action.realm_tags) - tags - {"*"}:
            raise ContentError(f"unknown realm tags in action {action.id}")
    for realm in realms.values():
        if realm.starting_node_id not in nodes:
            raise ContentError(
                "unknown starting_node_id "
                f"{realm.starting_node_id!r} in realm {realm.id}"
            )
        _require_items(
            (v.item_id for v in realm.market_offers),
            item_ids,
            f"realm {realm.id} market",
        )
    pairs: set[frozenset[str]] = set()
    for map_edge in map_pack.edges:
        left, right = map_edge.realms
        if left not in realms or right not in realms:
            raise ContentError(f"unknown realm in map edge {map_edge.realms}")
        pair = frozenset(map_edge.realms)
        if left == right or len(pair) != 2:
            raise ContentError("map edges cannot be self-edges")
        if pair in pairs:
            raise ContentError(f"duplicate map edge {map_edge.realms}")
        pairs.add(pair)
        _require_items((v.item_id for v in map_edge.cost.items), item_ids, "map edge")
    if set(map_pack.positions) - set(realms):
        raise ContentError("map position references an unknown realm")
    forms = _unique(forms_pack.forms, "estate form")
    for form in forms.values():
        if form.relocation_class not in forms_pack.relocation_classes:
            raise ContentError(f"unknown relocation class {form.relocation_class!r}")
        _require_items(
            (v.item_id for v in form.upkeep_profile),
            item_ids,
            f"form {form.id} upkeep",
        )
        _require_items(
            (v.item_id for v in form.production_profile),
            item_ids,
            f"form {form.id} production",
        )
    for transformation in forms_pack.transformations:
        if transformation.from_form not in forms or transformation.to_form not in forms:
            raise ContentError("transformation references an unknown form")
        _require_items(
            (v.item_id for v in transformation.cost), item_ids, "transformation"
        )
    for edge in edges.values():
        if edge.from_node not in nodes or edge.to_node not in nodes:
            raise ContentError(f"development edge {edge.id} references an unknown node")
        if edge.from_node == edge.to_node:
            raise ContentError(f"development edge {edge.id} is a self-loop")
    for node in nodes.values():
        if set(node.projects) - set(projects):
            raise ContentError(f"node {node.id} references an unknown project")
        _require_items(
            (v.item_id for v in node.upkeep_profile), item_ids, f"node {node.id}"
        )
    for project in projects.values():
        _require_items(
            (v.item_id for v in project.targets), item_ids, f"project {project.id}"
        )
        for award in project.awards:
            if award.edge_id not in edges:
                raise ContentError(f"project {project.id} references an unknown edge")
            if edges[award.edge_id].kind != "development":
                raise ContentError(f"project {project.id} awards a regression edge")
    for upgrade in upgrades.values():
        _require_items(
            (v.item_id for v in upgrade.cost), item_ids, f"upgrade {upgrade.id}"
        )
        if set(upgrade.realm_tags) - tags - {"*"}:
            raise ContentError(f"unknown realm tags in upgrade {upgrade.id}")
    if [v.level for v in xp_curve.levels] != list(range(1, 100)):
        raise ContentError("XP curve must contain ordered levels 1 through 99")
    if any(
        b.xp <= a.xp for a, b in zip(xp_curve.levels, xp_curve.levels[1:], strict=False)
    ):
        raise ContentError("XP requirements must increase after level 1")


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
    packs: dict[str, BaseModel] = {
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
    }
    skills = _unique(skills_pack.skills, "skill")
    actions = _unique((a for s in skills.values() for a in s.actions), "action")
    items = _unique(items_pack.items, "item")
    realms = _unique(realms_pack.realms, "realm")
    upgrades = _unique(upgrades_pack.upgrades, "upgrade")
    nodes = _unique(development.nodes, "development node")
    edges = _unique(development.edges, "development edge")
    projects = _unique(projects_pack.projects, "project")
    _validate(
        skills,
        actions,
        items,
        realms,
        upgrades,
        map_pack,
        forms_pack,
        nodes,
        edges,
        projects,
        xp_curve,
    )
    canonical = {
        name: model.model_dump(mode="json", by_alias=True)
        for name, model in packs.items()
    }
    payloads = {name: _canonical_bytes(canonical[name]) for name in PUBLIC_PACKS}
    hashes = {
        name: hashlib.sha256(value).hexdigest() for name, value in payloads.items()
    }
    forms = _unique(forms_pack.forms, "estate form")
    return ContentIndex(
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
        tuple(edges.values()),
        tuple(projects.values()),
        caps,
        xp_curve,
        MappingProxyType(forms_pack.relocation_classes),
        MappingProxyType(payloads),
        MappingProxyType(skills),
        MappingProxyType(actions),
        MappingProxyType({k: v.actions for k, v in skills.items()}),
        MappingProxyType(items),
        MappingProxyType(realms),
        MappingProxyType(upgrades),
        MappingProxyType(forms),
        MappingProxyType(nodes),
    )
