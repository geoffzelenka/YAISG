"""Content graph validation and pure estate voting weights."""

import json
import shutil
from pathlib import Path

import pytest

from app.config import CONTENT_DIR
from app.content import ContentError, load_content
from app.engine.estates import estate_value, vote_weight


@pytest.mark.parametrize(
    "mobility,tier,weight",
    [
        ("mobile", 1, 1),
        ("mobile", 3, 1),
        ("fixed", 1, 10),
        ("fixed", 2, 11),
        ("fixed", 3, 12),
    ],
)
def test_estate_vote_weights(mobility: str, tier: int, weight: int) -> None:
    """Mobile weight is constant; fixed weight increases with form tier."""
    form = load_content(CONTENT_DIR).estate_forms[0]
    assert (
        vote_weight(
            form.model_copy(
                update={
                    "mobility": mobility,
                    "tier": tier,
                    "travel_profile": form.travel_profile
                    if mobility == "mobile"
                    else None,
                }
            )
        )
        == weight
    )


@pytest.mark.parametrize(
    "case",
    [
        "transform_mobility",
        "regression_mobility",
        "regression_tier",
        "unknown_regression",
        "basic_missing",
        "basic_fixed",
        "basic_upkeep",
        "basic_production",
    ],
)
def test_estate_form_graph_validation(tmp_path: Path, case: str) -> None:
    """Invalid graph edges and unsafe starter forms are rejected at boot."""
    content_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, content_dir)
    path = content_dir / "estate_forms.json"
    pack = json.loads(path.read_text())
    basic, higher = pack["forms"][:2]
    progression_path = content_dir / "progression.json"
    progression = json.loads(progression_path.read_text())
    if case == "transform_mobility":
        higher.update(mobility="fixed", travel_profile=None, regresses_to=None)
    elif case == "regression_mobility":
        basic["transforms_to"] = []
        higher.update(mobility="fixed", travel_profile=None, transforms_to=[])
        pack["forms"][2]["regresses_to"] = None
    elif case == "regression_tier":
        higher["regresses_to"] = higher["id"]
    elif case == "unknown_regression":
        higher["regresses_to"] = "missing"
    elif case == "basic_missing":
        progression["basic_mobile_form"] = "missing"
    elif case == "basic_fixed":
        for form in pack["forms"]:
            form.update(mobility="fixed", travel_profile=None)
    elif case == "basic_upkeep":
        basic["upkeep"] = [{"selector": {"item": "item.fake_sprig"}, "per_day": 1}]
    else:
        basic["production"] = [{"item_id": "item.fake_sprig", "per_day": 1}]
    path.write_text(json.dumps(pack))
    progression_path.write_text(json.dumps(progression))
    with pytest.raises(ContentError):
        load_content(content_dir)


def test_fixed_form_graph_loads(tmp_path: Path) -> None:
    """Fixed estates support transforms and lower-tier regressions independently."""
    content_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, content_dir)
    path = content_dir / "estate_forms.json"
    pack = json.loads(path.read_text())
    for tier in range(1, 4):
        pack["forms"].append(
            {
                **pack["forms"][0],
                "id": f"fixed.{tier}",
                "mobility": "fixed",
                "travel_profile": None,
                "tier": tier,
                "transforms_to": [f"fixed.{tier + 1}"] if tier < 3 else [],
                "regresses_to": f"fixed.{tier - 1}" if tier > 1 else None,
            }
        )
    path.write_text(json.dumps(pack))
    content = load_content(content_dir)
    assert [
        vote_weight(content.estate_form(f"fixed.{tier}")) for tier in range(1, 4)
    ] == [10, 11, 12]


def test_valuation_goods_selector_gold_and_provider() -> None:
    """Rebuild costs use the cheapest selector match and an injectable unit ask."""
    content = load_content(CONTENT_DIR)
    form = content.estate_form("form.fake_workshop")
    expected = 20 + 2 * min(
        item.reference_price
        for item in content.items
        if form.build_cost.goods[0].selector.matches(item)
    )
    value = estate_value(form.id, (), "realm.verdant_vale", content)
    assert value.value == expected
    assert value.path == (form.id,)
    assert (
        estate_value(
            form.id, (), "realm.verdant_vale", content, lambda realm, item: 1
        ).value
        == 22
    )
    upgrade = content.upgrades[0]
    upgraded = estate_value(form.id, (upgrade.id,), "realm.verdant_vale", content)
    assert upgraded.value == expected + sum(
        entry.qty * content.item(entry.item_id).reference_price
        for entry in upgrade.cost
    )


def test_valuation_records_cheapest_tier_one_path() -> None:
    """Alternative rebuild roots and cyclic edges cannot inflate the chosen cost."""
    from dataclasses import replace
    from types import MappingProxyType

    from app.content.schemas import BuildCost

    content = load_content(CONTENT_DIR)
    base = content.estate_form("form.fake_workshop")
    target = base.model_copy(
        update={"id": "fixed.target", "tier": 2, "build_cost": BuildCost(gold=7)}
    )
    expensive = base.model_copy(
        update={
            "id": "fixed.expensive",
            "transforms_to": (target.id,),
            "build_cost": BuildCost(gold=100),
        }
    )
    cheap = base.model_copy(
        update={
            "id": "fixed.cheap",
            "transforms_to": (target.id,),
            "build_cost": BuildCost(gold=10),
        }
    )
    target = target.model_copy(update={"transforms_to": (cheap.id,)})
    forms = (expensive, cheap, target)
    content = replace(
        content,
        estate_forms=forms,
        _forms_by_id=MappingProxyType({form.id: form for form in forms}),
    )
    value = estate_value(target.id, (), "realm.verdant_vale", content)
    assert value.value == 17
    assert value.path == (cheap.id, target.id)
