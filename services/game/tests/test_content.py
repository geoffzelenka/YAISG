"""Content loading, integrity, hashing, and HTTP caching tests."""

import asyncio
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import CONTENT_DIR
from app.content import ContentError, load_content
from app.main import app


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _change_unknown_item(content_dir: Path) -> None:
    path = content_dir / "skills.json"
    value = json.loads(path.read_text())
    value["skills"][0]["actions"][0]["outputs"][0]["item_id"] = "item.missing"
    _write_json(path, value)


def _add_duplicate_id(content_dir: Path) -> None:
    path = content_dir / "items.json"
    value = json.loads(path.read_text())
    value["items"].append(value["items"][0])
    _write_json(path, value)


def _set_bad_modifier(content_dir: Path) -> None:
    path = content_dir / "development.json"
    value = json.loads(path.read_text())
    value["nodes"][1]["modifiers"][0]["type"] = "made_up_pct"
    _write_json(path, value)


def _remove_cap(content_dir: Path) -> None:
    path = content_dir / "caps.json"
    value = json.loads(path.read_text())
    del value["inventory_slots"]
    _write_json(path, value)


def _duplicate_map_edge(content_dir: Path) -> None:
    path = content_dir / "map.json"
    value = json.loads(path.read_text())
    duplicate = value["edges"][0].copy()
    duplicate["a"], duplicate["b"] = duplicate["b"], duplicate["a"]
    value["edges"].append(duplicate)
    _write_json(path, value)


def _unknown_map_realm(content_dir: Path) -> None:
    path = content_dir / "map.json"
    value = json.loads(path.read_text())
    value["edges"][0]["b"] = "realm.missing"
    _write_json(path, value)


def _unknown_transformation_form(content_dir: Path) -> None:
    path = content_dir / "estate_forms.json"
    value = json.loads(path.read_text())
    value["forms"][0]["transforms_to"] = ["form.missing"]
    _write_json(path, value)


def _unknown_starting_node(content_dir: Path) -> None:
    path = content_dir / "realms.json"
    value = json.loads(path.read_text())
    value["realms"][0]["starting_node_id"] = "node.missing"
    _write_json(path, value)


def test_placeholder_content_loads() -> None:
    """The checked-in pack exercises required lookups and dependency content."""
    content = load_content(CONTENT_DIR)

    assert len(content.skills) == 11
    assert len(content.actions_for_skill("gathering")) == 3
    assert content.action("manufacturing.demo_crate").inputs[0].selector.item == (
        "item.fake_plank"
    )
    assert content.item("item.prototype_widget").name == "Prototype Widget"
    assert content.realm("realm.verdant_vale").starting_node_id == "node.verdant_t1"
    assert content.development_node("node.verdant_t1").inherent_tags == (
        "verdant",
        "facility.fake_node",
    )
    assert content.upgrade("upgrade.alarm_clock").cap_bonuses[0].value == 2
    assert len(content.xp_curve.levels) == 100


@pytest.mark.parametrize(
    "break_content",
    [
        _change_unknown_item,
        _add_duplicate_id,
        _set_bad_modifier,
        _remove_cap,
        _duplicate_map_edge,
        _unknown_map_realm,
        _unknown_transformation_form,
        _unknown_starting_node,
    ],
    ids=[
        "unknown-item",
        "duplicate-id",
        "bad-modifier",
        "missing-cap",
        "duplicate-map-edge",
        "unknown-map-realm",
        "unknown-form",
        "unknown-starting-node",
    ],
)
def test_broken_content_is_rejected(
    tmp_path: Path, break_content: Callable[[Path], None]
) -> None:
    """Invalid schemas and cross-pack references fail the complete load."""
    fixture_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, fixture_dir)
    break_content(fixture_dir)

    with pytest.raises(ContentError):
        load_content(fixture_dir)


def test_manifest_version_changes_with_content(tmp_path: Path) -> None:
    """Any content change, including engine-only XP, changes the version."""
    fixture_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, fixture_dir)
    original = load_content(fixture_dir)
    xp_path = fixture_dir / "xp_curve.json"
    value = json.loads(xp_path.read_text())
    value[0] += 1
    value[-1] -= 1
    _write_json(xp_path, value)

    changed = load_content(fixture_dir)

    assert changed.manifest.version != original.manifest.version
    assert changed.manifest.packs == original.manifest.packs


def test_public_pack_hash_changes_with_pack_content(tmp_path: Path) -> None:
    """A public pack's hash and overall version track its canonical payload."""
    fixture_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, fixture_dir)
    original = load_content(fixture_dir)
    skills_path = fixture_dir / "skills.json"
    value = json.loads(skills_path.read_text())
    value["skills"][0]["name"] = "Renamed Placeholder Gathering"
    _write_json(skills_path, value)

    changed = load_content(fixture_dir)

    assert changed.manifest.version != original.manifest.version
    assert changed.manifest.packs["skills"] != original.manifest.packs["skills"]
    assert changed.manifest.packs["items"] == original.manifest.packs["items"]


def test_xp_curve_must_increase_from_level_one(tmp_path: Path) -> None:
    """The first XP transition is covered by monotonicity validation."""
    fixture_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, fixture_dir)
    xp_path = fixture_dir / "xp_curve.json"
    value = json.loads(xp_path.read_text())
    value[1] = value[0]
    _write_json(xp_path, value)

    with pytest.raises(ContentError, match="must increase after level 1"):
        load_content(fixture_dir)


def test_pack_etag_and_not_modified_response() -> None:
    """Public packs return strong ETags and honor exact If-None-Match values."""

    async def request_validators() -> tuple[Any, Any, Any, Any]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.get("/content/skills")
            exact = await client.get(
                "/content/skills",
                headers={"If-None-Match": first.headers["etag"]},
            )
            listed = await client.get(
                "/content/skills",
                headers={"If-None-Match": f'"not-current", {first.headers["etag"]}'},
            )
            wildcard = await client.get(
                "/content/skills", headers={"If-None-Match": "*"}
            )
        return first, exact, listed, wildcard

    first, exact, listed, wildcard = asyncio.run(request_validators())

    assert first.status_code == 200
    assert first.json()["skills"]
    assert first.headers["etag"].startswith('"')
    assert first.headers["cache-control"] == "public, no-cache"
    for response in (exact, listed, wildcard):
        assert response.status_code == 304
        assert response.content == b""
        assert response.headers["etag"] == first.headers["etag"]


def test_only_known_content_routes_are_public() -> None:
    """The manifest is public without broadly bypassing auth under /content."""

    async def request_packs() -> tuple[Any, Any]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            manifest = await client.get("/content/manifest")
            missing = await client.get("/content/xp_curve")
        return manifest, missing

    manifest, missing = asyncio.run(request_packs())

    assert manifest.status_code == 200
    assert set(manifest.json()["packs"]) == {
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
    }
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("defect", ["short", "unordered", "total"])
def test_boot_rejects_invalid_xp_table(tmp_path: Path, defect: str) -> None:
    """Each required XP table invariant is checked at load time."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "xp_curve.json"
    costs = json.loads(path.read_text())
    if defect == "short":
        removed = costs.pop()
        costs[-1] += removed
    elif defect == "unordered":
        costs[-1] += costs[1] - costs[0]
        costs[1] = costs[0]
    else:
        costs[-1] -= 1
    _write_json(path, costs)
    messages = {
        "short": "must contain 99 entries",
        "unordered": "must increase after level 1",
        "total": "must sum to 10000000",
    }
    with pytest.raises(ContentError, match=messages[defect]):
        load_content(directory)


@pytest.mark.parametrize("thresholds", [[2, 50], [1, 50, 50], [1, 101], []])
def test_boot_rejects_invalid_tier_thresholds(
    tmp_path: Path, thresholds: list[int]
) -> None:
    """Tier thresholds are validated independently of skill mechanics."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    _write_json(
        directory / "progression.json",
        {
            **json.loads((CONTENT_DIR / "progression.json").read_text()),
            "tier_thresholds": thresholds,
            "tier_titles": ["Placeholder"] * len(thresholds),
        },
    )
    message = (
        "must strictly increase"
        if thresholds == [1, 50, 50]
        else "must start at 1 and end at or below 100"
    )
    with pytest.raises(ContentError, match=message):
        load_content(directory)


def test_xp_thresholds_are_cached_and_curve_is_frozen() -> None:
    """Reading thresholds reuses the loaded tuple and the source table is frozen."""
    from pydantic import ValidationError

    curve = load_content(CONTENT_DIR).xp_curve
    assert curve.levels is curve.levels
    with pytest.raises(ValidationError, match="frozen"):
        curve.root = curve.root


@pytest.mark.parametrize(
    ("defect", "message"),
    [
        ("tier", "tier differs from unlock level"),
        ("output", "output tier differs"),
        ("input", "higher-tier input"),
        ("empty", "selector matches no item"),
        ("category", "Input should be"),
        ("facility", "unknown requirement tag"),
        ("skill", "unknown required skill"),
        ("tool", "unknown tool class"),
        ("coercion", "valid integer"),
    ],
)
def test_content_model_validation(tmp_path: Path, defect: str, message: str) -> None:
    """Reject invalid tiers, references, categories, and coerced scalar types."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "skills.json"
    skills = json.loads(path.read_text())
    action = skills["skills"][1]["actions"][0]
    if defect == "tier":
        action["tier"] = 2
    elif defect in {"input", "output"}:
        items_path = directory / "items.json"
        items = json.loads(items_path.read_text())
        if defect == "input":
            action["inputs"][0]["selector"] = {"class": "fake_plant"}
            skills["skills"][0]["actions"][0]["outputs"][0]["off_tier"] = True
        index = 0 if defect == "input" else 3
        items["items"][index]["tier"] = 2
        _write_json(items_path, items)
    elif defect == "empty":
        action["inputs"][0]["selector"] = {"class": "missing"}
    elif defect == "category":
        skills["skills"][0]["category"] = "missing"
    elif defect == "coercion":
        action["tier"] = "1"
    else:
        field = {"facility": "facility", "skill": "skill_levels", "tool": "tool_class"}[
            defect
        ]
        action["requires"][field] = {"missing": 1} if defect == "skill" else "missing"
    _write_json(path, skills)
    with pytest.raises(ContentError, match=message):
        load_content(directory)


def test_off_tier_output_and_resolver_defaults(tmp_path: Path) -> None:
    """Explicit by-products permit other tiers and category sets default resolver."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "skills.json"
    skills = json.loads(path.read_text())
    action = skills["skills"][0]["actions"][0]
    action["outputs"][0]["off_tier"] = True
    _write_json(path, skills)
    path = directory / "items.json"
    items = json.loads(path.read_text())
    items["items"][0]["tier"] = 2
    # Keep class selectors from matching this deliberately higher-tier by-product.
    items["items"][0]["classes"] = ["byproduct"]
    _write_json(path, items)
    content = load_content(directory)
    assert content.action(action["id"]).resolver == "uniform"


@pytest.mark.parametrize(
    "value", [{}, {"item": "x", "class": "x"}, {"item": "x", "tier": 1}]
)
def test_selector_rejects_invalid_shapes(value: dict[str, object]) -> None:
    """Selectors cannot be empty, mixed, or attach tiers to exact items."""
    from pydantic import ValidationError

    from app.content.schemas import Selector

    with pytest.raises(ValidationError):
        Selector.model_validate(value)


@pytest.mark.parametrize(
    ("category", "resolver"),
    [("gathering", "uniform"), ("combat", "combat"), ("travel", "travel")],
)
def test_category_defaults_resolver(category: str, resolver: str) -> None:
    """Resolver defaults are part of the published action definition."""
    from app.content.schemas import Skill

    skill = Skill.model_validate_json(
        json.dumps(
            {
                "id": "test",
                "name": "Test",
                "category": category,
                "actions": [
                    {
                        "id": "test.action",
                        "name": "Test",
                        "skill_id": "test",
                        "tier": 1,
                        "unlock_level": 1,
                        "base_cycle_ms": 1,
                        "xp": 1,
                    }
                ],
            }
        )
    )
    assert skill.actions[0].resolver == resolver


@pytest.mark.parametrize("retired", ["cycle_time_pct", "market_tax_pct"])
def test_retired_modifier_types_are_rejected(retired: str) -> None:
    """Retired mechanics cannot sneak back into strict content packs."""
    from pydantic import ValidationError

    from app.content.schemas import Modifier

    with pytest.raises(ValidationError):
        Modifier.model_validate_json(json.dumps({"type": retired, "value": 5}))


@pytest.mark.parametrize(
    ("scope", "message"),
    [
        (
            {"skill_id": "gathering", "category": "gathering"},
            "cannot specify both skill_id and category",
        ),
        ({}, "requires a skill or category scope"),
    ],
)
def test_modifier_rejects_invalid_scope(scope: dict[str, str], message: str) -> None:
    """Drop bonuses require a single skill or category scope."""
    from pydantic import ValidationError

    from app.content.schemas import Modifier

    with pytest.raises(ValidationError, match=message):
        Modifier.model_validate_json(
            json.dumps(
                {
                    "type": "extra_drop_chance_pct",
                    "value": 5,
                    **scope,
                }
            )
        )


@pytest.mark.parametrize("field", ["requires", "modifiers"])
def test_loader_rejects_unknown_equipment_skill(tmp_path: Path, field: str) -> None:
    """Both equipment skill gates and modifier scopes reference real skills."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "items.json"
    items = json.loads(path.read_text())
    equip = next(item["equip"] for item in items["items"] if item.get("equip"))
    equip[field] = (
        {"missing": 1}
        if field == "requires"
        else [{"type": "cycle_speed_pct", "value": 1, "skill_id": "missing"}]
    )
    _write_json(path, items)
    with pytest.raises(ContentError, match="unknown equipment.*skill"):
        load_content(directory)


def test_loader_requires_equipped_tool_class(tmp_path: Path) -> None:
    """An inventory goods class cannot satisfy a tool reference without equip."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "skills.json"
    skills = json.loads(path.read_text())
    action = skills["skills"][0]["actions"][0]
    action["requires"]["tool_class"] = "fake_pickaxe"
    _write_json(path, skills)
    load_content(directory)
    items_path = directory / "items.json"
    items = json.loads(items_path.read_text())
    tool = next(
        item
        for item in items["items"]
        if item.get("equip", {}).get("tool_class") == "fake_pickaxe"
    )
    tool["equip"]["tool_class"] = "another_tool"
    tool["classes"].append("fake_pickaxe")
    _write_json(items_path, items)
    with pytest.raises(ContentError, match="unknown tool class"):
        load_content(directory)
