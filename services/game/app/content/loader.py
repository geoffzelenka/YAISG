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
    EstateUpgrade,
    Item,
    ItemsPack,
    Realm,
    RealmsPack,
    Skill,
    SkillsPack,
    UpgradesPack,
    XpCurve,
)

PUBLIC_PACKS = ("skills", "items", "realms", "upgrades", "caps")
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
    caps: CapsConfig
    xp_curve: XpCurve
    pack_payloads: MappingProxyType[str, bytes]
    _skills_by_id: MappingProxyType[str, Skill]
    _actions_by_id: MappingProxyType[str, Action]
    _actions_by_skill: MappingProxyType[str, tuple[Action, ...]]
    _items_by_id: MappingProxyType[str, Item]
    _realms_by_id: MappingProxyType[str, Realm]
    _upgrades_by_id: MappingProxyType[str, EstateUpgrade]

    def skill(self, skill_id: str) -> Skill:
        """Look up a skill, raising KeyError if it does not exist."""
        return self._skills_by_id[skill_id]

    def action(self, action_id: str) -> Action:
        """Look up an action, raising KeyError if it does not exist."""
        return self._actions_by_id[action_id]

    def actions_for_skill(self, skill_id: str) -> tuple[Action, ...]:
        """Return all actions for a skill in content order."""
        return self._actions_by_skill[skill_id]

    def item(self, item_id: str) -> Item:
        """Look up an item, raising KeyError if it does not exist."""
        return self._items_by_id[item_id]

    def realm(self, realm_id: str) -> Realm:
        """Look up a realm, raising KeyError if it does not exist."""
        return self._realms_by_id[realm_id]

    def upgrade(self, upgrade_id: str) -> EstateUpgrade:
        """Look up an estate upgrade, raising KeyError if it does not exist."""
        return self._upgrades_by_id[upgrade_id]

    def with_overrides(
        self,
        *,
        actions: Iterable[Action] = (),
        items: Iterable[Item] = (),
        upgrades: Iterable[EstateUpgrade] = (),
    ) -> "ContentIndex":
        """Return an immutable copy with selected definitions replaced.

        This is intended for engine tests and simulation tooling. It deliberately
        leaves the source pack payloads and manifest unchanged.
        """
        action_overrides = {action.id: action for action in actions}
        item_overrides = {item.id: item for item in items}
        upgrade_overrides = {upgrade.id: upgrade for upgrade in upgrades}
        unknown_actions = set(action_overrides) - set(self._actions_by_id)
        if unknown_actions:
            raise ValueError(
                f"cannot override unknown actions: {sorted(unknown_actions)}"
            )

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
        actions_by_skill = {skill.id: skill.actions for skill in skills}
        actions_by_id = {
            action.id: action for skill in skills for action in skill.actions
        }
        replaced_item_ids = set(item_overrides) & set(self._items_by_id)
        replaced_upgrade_ids = set(upgrade_overrides) & set(self._upgrades_by_id)
        resolved_items = tuple(
            item_overrides.get(item.id, item) for item in self.items
        ) + tuple(
            item
            for item_id, item in item_overrides.items()
            if item_id not in replaced_item_ids
        )
        resolved_upgrades = tuple(
            upgrade_overrides.get(upgrade.id, upgrade) for upgrade in self.upgrades
        ) + tuple(
            upgrade
            for upgrade_id, upgrade in upgrade_overrides.items()
            if upgrade_id not in replaced_upgrade_ids
        )
        return replace(
            self,
            skills=skills,
            items=resolved_items,
            upgrades=resolved_upgrades,
            _actions_by_id=MappingProxyType(actions_by_id),
            _actions_by_skill=MappingProxyType(actions_by_skill),
            _items_by_id=MappingProxyType({item.id: item for item in resolved_items}),
            _upgrades_by_id=MappingProxyType(
                {upgrade.id: upgrade for upgrade in resolved_upgrades}
            ),
        )


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _load_model[ModelT: BaseModel](
    content_dir: Path, pack: str, model: type[ModelT]
) -> ModelT:
    path = content_dir / f"{pack}.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return model.model_validate(raw)
    except FileNotFoundError as error:
        raise ContentError(f"required content pack is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ContentError(f"invalid JSON in {path}: {error}") from error
    except ValidationError as error:
        raise ContentError(f"invalid content in {path}: {error}") from error


def _unique_by_id[ModelT: BaseModel](
    values: Iterable[ModelT], kind: str
) -> dict[str, ModelT]:
    indexed: dict[str, ModelT] = {}
    for value in values:
        identifier = getattr(value, "id", None)
        if not isinstance(identifier, str):
            raise ContentError(f"{kind} has no string id")
        if identifier in indexed:
            raise ContentError(f"duplicate {kind} id: {identifier}")
        indexed[identifier] = value
    return indexed


def _require_items(item_ids: Iterable[str], known: set[str], context: str) -> None:
    for item_id in item_ids:
        if item_id not in known:
            raise ContentError(f"unknown item_id {item_id!r} in {context}")


def _validate_references(
    skills: dict[str, Skill],
    actions: dict[str, Action],
    items: dict[str, Item],
    realms: dict[str, Realm],
    upgrades: dict[str, EstateUpgrade],
    xp_curve: XpCurve,
) -> None:
    item_ids = set(items)
    realm_tags = {tag for realm in realms.values() for tag in realm.tags}
    for action in actions.values():
        if action.skill_id not in skills:
            raise ContentError(
                f"unknown skill_id {action.skill_id!r} in action {action.id}"
            )
        _require_items(
            (entry.item_id for entry in action.inputs),
            item_ids,
            f"action {action.id} inputs",
        )
        _require_items(
            (entry.item_id for entry in action.drops),
            item_ids,
            f"action {action.id} drops",
        )
        unknown_tags = set(action.realm_tags) - realm_tags - {"*"}
        if unknown_tags:
            raise ContentError(
                f"unknown realm tags in action {action.id}: {unknown_tags}"
            )
    for realm in realms.values():
        _require_items(
            (offer.item_id for offer in realm.market_offers),
            item_ids,
            f"realm {realm.id} market",
        )
        _require_items(
            (target.item_id for target in realm.project.contribution_targets),
            item_ids,
            f"realm project {realm.project.id}",
        )
        project_modifiers = (
            modifier for tier in realm.project.tiers for modifier in tier.modifiers
        )
        for modifier in (*realm.modifiers, *project_modifiers):
            if modifier.skill_id is not None and modifier.skill_id not in skills:
                raise ContentError(
                    f"unknown skill_id {modifier.skill_id!r} in realm {realm.id}"
                )
    for upgrade in upgrades.values():
        _require_items(
            (cost.item_id for cost in upgrade.cost),
            item_ids,
            f"upgrade {upgrade.id}",
        )
        unknown_tags = set(upgrade.realm_tags) - realm_tags - {"*"}
        if unknown_tags:
            raise ContentError(
                f"unknown realm tags in upgrade {upgrade.id}: {unknown_tags}"
            )
        for modifier in upgrade.modifiers:
            if modifier.skill_id is not None and modifier.skill_id not in skills:
                raise ContentError(
                    f"unknown skill_id {modifier.skill_id!r} in upgrade {upgrade.id}"
                )
    expected_levels = list(range(1, 100))
    actual_levels = [entry.level for entry in xp_curve.levels]
    if actual_levels != expected_levels:
        raise ContentError("XP curve must contain ordered levels 1 through 99")
    if any(
        current.xp <= previous.xp
        for previous, current in zip(xp_curve.levels, xp_curve.levels[1:], strict=False)
    ):
        raise ContentError("XP requirements must increase after level 1")


def load_content(content_dir: Path) -> ContentIndex:
    """Load all required JSON packs and return an immutable content index."""
    json_files = {path.stem for path in content_dir.rglob("*.json")}
    unknown_files = json_files - _KNOWN_PACKS
    if unknown_files:
        raise ContentError(f"unrecognized content packs: {sorted(unknown_files)}")
    skills_pack = _load_model(content_dir, "skills", SkillsPack)
    items_pack = _load_model(content_dir, "items", ItemsPack)
    realms_pack = _load_model(content_dir, "realms", RealmsPack)
    upgrades_pack = _load_model(content_dir, "upgrades", UpgradesPack)
    caps = _load_model(content_dir, "caps", CapsConfig)
    xp_curve = _load_model(content_dir, "xp_curve", XpCurve)

    skills = _unique_by_id(skills_pack.skills, "skill")
    actions = _unique_by_id(
        (action for skill in skills.values() for action in skill.actions), "action"
    )
    items = _unique_by_id(items_pack.items, "item")
    realms = _unique_by_id(realms_pack.realms, "realm")
    upgrades = _unique_by_id(upgrades_pack.upgrades, "upgrade")
    projects = [realm.project for realm in realms.values()]
    _unique_by_id(projects, "realm project")
    for skill in skills.values():
        for action in skill.actions:
            if action.skill_id != skill.id:
                raise ContentError(
                    f"action {action.id} skill_id does not match "
                    f"parent skill {skill.id}"
                )
    _validate_references(skills, actions, items, realms, upgrades, xp_curve)

    canonical_models = {
        "skills": skills_pack.model_dump(mode="json"),
        "items": items_pack.model_dump(mode="json"),
        "realms": realms_pack.model_dump(mode="json"),
        "upgrades": upgrades_pack.model_dump(mode="json"),
        "caps": caps.model_dump(mode="json"),
        "xp_curve": xp_curve.model_dump(mode="json"),
    }
    pack_payloads = {
        pack: _canonical_bytes(canonical_models[pack]) for pack in PUBLIC_PACKS
    }
    pack_hashes = {
        pack: hashlib.sha256(payload).hexdigest()
        for pack, payload in pack_payloads.items()
    }
    version = hashlib.sha256(_canonical_bytes(canonical_models)).hexdigest()
    actions_by_skill = {
        skill_id: tuple(skill.actions) for skill_id, skill in skills.items()
    }
    return ContentIndex(
        manifest=ContentManifest(version, MappingProxyType(pack_hashes)),
        skills=tuple(skills.values()),
        items=tuple(items.values()),
        realms=tuple(realms.values()),
        upgrades=tuple(upgrades.values()),
        caps=caps,
        xp_curve=xp_curve,
        pack_payloads=MappingProxyType(pack_payloads),
        _skills_by_id=MappingProxyType(skills),
        _actions_by_id=MappingProxyType(actions),
        _actions_by_skill=MappingProxyType(actions_by_skill),
        _items_by_id=MappingProxyType(items),
        _realms_by_id=MappingProxyType(realms),
        _upgrades_by_id=MappingProxyType(upgrades),
    )
