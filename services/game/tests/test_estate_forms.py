"""Content graph validation and pure estate voting weights."""

import json
import shutil
from pathlib import Path

import pytest

from app.config import CONTENT_DIR
from app.content import ContentError, load_content
from app.engine.estates import vote_weight


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
    basic, higher, _ = pack["forms"]
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
