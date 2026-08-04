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
    value["skills"][0]["actions"][0]["drops"][0]["item_id"] = "item.missing"
    _write_json(path, value)


def _add_duplicate_id(content_dir: Path) -> None:
    path = content_dir / "items.json"
    value = json.loads(path.read_text())
    value["items"].append(value["items"][0])
    _write_json(path, value)


def _set_bad_modifier(content_dir: Path) -> None:
    path = content_dir / "realms.json"
    value = json.loads(path.read_text())
    value["realms"][0]["modifiers"][0]["type"] = "made_up_pct"
    _write_json(path, value)


def _remove_cap(content_dir: Path) -> None:
    path = content_dir / "caps.json"
    value = json.loads(path.read_text())
    del value["inventory_slots"]
    _write_json(path, value)


def test_placeholder_content_loads() -> None:
    """The checked-in pack exercises required lookups and dependency content."""
    content = load_content(CONTENT_DIR)

    assert len(content.skills) == 4
    assert len(content.actions_for_skill("gathering")) == 3
    assert content.action("crafting.demo_crate").inputs[0].item_id == (
        "item.fake_plank"
    )
    assert content.item("item.prototype_widget").name == "Prototype Widget"
    assert content.realm("realm.verdant_vale").tags == ("verdant",)
    assert content.upgrade("upgrade.alarm_clock").cap_bonuses[0].value == 2
    assert len(content.xp_curve.levels) == 99


@pytest.mark.parametrize(
    "break_content",
    [_change_unknown_item, _add_duplicate_id, _set_bad_modifier, _remove_cap],
    ids=["unknown-item", "duplicate-id", "bad-modifier", "missing-cap"],
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
    value["formula"] += " (equivalent placeholder note)"
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
    value["levels"][1]["xp"] = value["levels"][0]["xp"]
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
    }
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "UNAUTHORIZED"
