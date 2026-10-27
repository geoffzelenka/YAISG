"""Exact rate integration, warning suppression and command behavior."""

import json
import shutil
import subprocess
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import CONTENT_DIR
from app.content.lint import (
    lint_content,
    stack_bound,
    target_xp_per_hour,
    training_hours,
)
from app.content.loader import load_content
from app.content.schemas import (
    Action,
    EstateUpgrade,
    LintConfig,
    Modifier,
    ModifierType,
    Skill,
)


@pytest.mark.parametrize(("level", "expected"), [(1, 3472), (50, 7547), (95, 15395)])
def test_target_matches_design_table(level: int, expected: int) -> None:
    """The rounded design table allows its displayed approximate precision."""
    assert float(target_xp_per_hour(level, 1.015969)) == pytest.approx(expected, abs=2)


def _ladder(step: int, g: float) -> Skill:
    actions = []
    for level in range(1, 100, step):
        rate = target_xp_per_hour(level, g)
        # Represent each rational target exactly with integer XP and duration.
        actions.append(
            Action(
                id=f"fake.{level}",
                name="Fake",
                skill_id="fake",
                tier=1,
                unlock_level=level,
                xp=rate.numerator,
                base_cycle_ms=rate.denominator * 3_600_000,
            )
        )
    return Skill(id="fake", name="Fake", category="gathering", actions=tuple(actions))


@pytest.mark.parametrize(
    ("step", "g", "expected"),
    [(1, 1.015969, 720), (10, 1.015969, 778), (10, 1.016938, 720)],
)
def test_exact_training_ladders(step: int, g: float, expected: int) -> None:
    content = load_content(CONTENT_DIR)
    hours = training_hours(_ladder(step, g), content.xp_curve.root)
    assert hours is not None
    assert float(hours) == pytest.approx(expected, abs=1)


def test_level_one_alone_is_exactly_2880_hours() -> None:
    content = load_content(CONTENT_DIR)
    assert training_hours(_ladder(100, 1.015969), content.xp_curve.root) == 2880
    report = lint_content(replace(content, skills=(_ladder(1, 1.015969),)))[0]
    assert report.level_one_hours == pytest.approx(2880)


def test_training_uses_best_unlocked_rate_and_exact_costs() -> None:
    skill = _ladder(100, 1.015969)
    first = skill.actions[0]
    later = first.model_copy(
        update={"id": "later", "unlock_level": 2, "xp": first.xp * 2}
    )
    slower = first.model_copy(update={"id": "slower", "unlock_level": 3, "xp": 1})
    skill = skill.model_copy(update={"actions": (first, later, slower)})
    rate = target_xp_per_hour(1, 1.015969)
    assert (
        training_hours(skill, (1, 2, 3))
        == Fraction(1, 1) / rate + Fraction(5, 2) / rate
    )
    assert (
        training_hours(skill.model_copy(update={"actions": (later,)}), (1, 2)) is None
    )


def test_off_curve_suppresses_only_action_warning() -> None:
    content = load_content(CONTENT_DIR)
    skill = _ladder(100, 1.015969)
    action = skill.actions[0].model_copy(update={"xp": 1})
    skill = skill.model_copy(update={"actions": (action,)})
    report = lint_content(replace(content, skills=(skill,)))[0]
    assert report.actions[0].warning
    exempt = action.model_copy(update={"off_curve": "Deliberately slow fake action"})
    report = lint_content(
        replace(content, skills=(skill.model_copy(update={"actions": (exempt,)}),))
    )[0]
    assert not report.actions[0].warning
    assert report.optimal_hours is not None and report.optimal_hours > 2880


def test_stack_warning_excludes_proficiency_and_xp_cap() -> None:
    content = load_content(CONTENT_DIR)
    skill = _ladder(100, 1.015969)
    node = content.development_nodes[0].model_copy(
        update={
            "inherent_tags": (),
            "modifiers": (
                Modifier(type=ModifierType.XP_PCT, value=100, skill_id=skill.id),
            ),
        }
    )
    content = replace(content, skills=(skill,), development_nodes=(node,), upgrades=())
    report = lint_content(content)[0]
    assert report.stack_bound == pytest.approx(2.1)  # form +5%, realm +100%
    assert report.stack_warning
    progression = content.progression.model_copy(
        update={
            "xp_bonus_cap_pct": 0,
            "proficiency": {"gathering": (100, 100, 100, 100, 100)},
        }
    )
    assert (
        lint_content(replace(content, progression=progression))[0].stack_bound
        == report.stack_bound
    )


def test_stack_respects_slots_scope_and_inert_upgrades() -> None:
    content = load_content(CONTENT_DIR)
    skill = _ladder(100, 1.015969)
    node = content.development_nodes[0].model_copy(
        update={"modifiers": (), "cap_bonuses": (), "inherent_tags": ()}
    )
    form = content.estate_forms[0].model_copy(
        update={"modifiers": (), "cap_bonuses": (), "upgrade_slots": 1}
    )
    upgrade = EstateUpgrade(
        id="fake",
        name="Fake",
        cost=(),
        modifiers=(
            Modifier(type=ModifierType.XP_PCT, value=50, category="gathering"),
            Modifier(type=ModifierType.CYCLE_SPEED_PCT, value=20, skill_id="fake"),
            Modifier(type=ModifierType.XP_PCT, value=1000, skill_id="other"),
        ),
    )
    inert = upgrade.model_copy(
        update={"id": "inert", "requires_realm_tags": ("missing",)}
    )
    upgrades = (upgrade, upgrade.model_copy(update={"id": "second"}), inert)
    content = replace(
        content,
        skills=(skill,),
        development_nodes=(node,),
        estate_forms=(form,),
        upgrades=upgrades,
        caps=content.caps.model_copy(update={"estate_upgrade_slots": 1}),
    )
    assert stack_bound(skill, content) == pytest.approx(1.5 * 1.2)
    form = form.model_copy(update={"upgrade_slots": 2})
    assert stack_bound(skill, replace(content, estate_forms=(form,))) == pytest.approx(
        2 * 1.4
    )


def test_empty_skills_report_blocked_and_combat_is_skipped() -> None:
    content = load_content(CONTENT_DIR)
    reports = lint_content(content)
    assert {r.skill_id for r in reports} == {
        s.id for s in content.skills if s.category != "combat"
    }
    empty = next(s for s in content.skills if s.category != "combat" and not s.actions)
    report = next(r for r in reports if r.skill_id == empty.id)
    assert report.optimal_hours is None
    assert report.level_one_hours is None


def test_content_lint_command_exits_zero_with_warnings(tmp_path: Path) -> None:
    content_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, content_dir)
    skill = _ladder(100, 1.015969)
    action = skill.actions[0].model_copy(update={"xp": 1, "base_cycle_ms": 3_600_000})
    skill = skill.model_copy(update={"actions": (action,)})
    skills_path = content_dir / "skills.json"
    skills = json.loads(skills_path.read_text())
    skills["skills"].append(skill.model_dump(mode="json"))
    skills_path.write_text(json.dumps(skills))
    progression_path = content_dir / "progression.json"
    progression = json.loads(progression_path.read_text())
    progression["lint"] = {"g": 1.015969, "tolerance_pct": 15}
    progression_path.write_text(json.dumps(progression))
    result = subprocess.run(
        [sys.executable, "-m", "app.content.lint", "--content-dir", str(content_dir)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stdout
    assert "XP-rate content lint" in result.stdout
    reports = json.loads(result.stdout[result.stdout.index("[\n") :])
    crafted_report = next(
        report for report in reports if report["skill_id"] == skill.id
    )
    assert crafted_report["actions"][0]["warning"]


@pytest.mark.parametrize(
    "value",
    [
        {"g": 1.0, "tolerance_pct": 15},
        {"g": 1.01, "tolerance_pct": -1},
        {"g": 1.01, "tolerance_pct": 15, "unknown": True},
    ],
)
def test_lint_settings_reject_invalid_values(value: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        LintConfig.model_validate(value)


@pytest.mark.parametrize(
    ("percentage", "warning"), [(85, False), (115, False), (84, True), (116, True)]
)
def test_rate_tolerance_is_inclusive(percentage: int, warning: bool) -> None:
    content = load_content(CONTENT_DIR)
    skill = _ladder(100, 1.015969)
    rate = target_xp_per_hour(1, 1.015969) * Fraction(percentage, 100)
    action = skill.actions[0].model_copy(
        update={
            "xp": rate.numerator,
            "base_cycle_ms": rate.denominator * 3_600_000,
        }
    )
    skill = skill.model_copy(update={"actions": (action,)})
    assert (
        lint_content(replace(content, skills=(skill,)))[0].actions[0].warning is warning
    )


def test_stack_maximizes_joint_factors_and_keeps_groups_separate() -> None:
    content = load_content(CONTENT_DIR)
    skill = _ladder(100, 1.015969)
    node = content.development_nodes[0].model_copy(
        update={
            "inherent_tags": (),
            "modifiers": (Modifier(type=ModifierType.XP_PCT, value=20),),
            "cap_bonuses": (),
        }
    )
    form = content.estate_forms[0].model_copy(
        update={"modifiers": (), "cap_bonuses": (), "upgrade_slots": 1}
    )
    xp = EstateUpgrade(
        id="xp",
        name="Fake XP",
        cost=(),
        modifiers=(
            Modifier(type=ModifierType.XP_PCT, value=100),
            Modifier(type=ModifierType.CYCLE_SPEED_PCT, value=-50),
        ),
    )
    speed = EstateUpgrade(
        id="speed",
        name="Fake speed",
        cost=(),
        modifiers=(Modifier(type=ModifierType.CYCLE_SPEED_PCT, value=50),),
    )
    content = replace(
        content,
        development_nodes=(node,),
        estate_forms=(form,),
        upgrades=(xp, speed),
        caps=content.caps.model_copy(update={"estate_upgrade_slots": 1}),
    )
    # XP upgrade yields 2 * 0.5 = 1; speed yields 1 * 1.5 = 1.5.
    assert stack_bound(skill, content) == pytest.approx(1.2 * 1.5)


def test_stack_bound_includes_project_and_carried_tags() -> None:
    """Potential realm stacks contribute to the author's uncapped bonus bound."""
    content = load_content(CONTENT_DIR)
    # Remove existing emitted bonuses so a project is the only source of this effect.
    nodes = tuple(
        n.model_copy(
            update={
                "modifiers": (),
                "inherent_tags": (),
                "carried_tags": (),
                "projects": (),
            }
        )
        for n in content.development_nodes
    )
    content = replace(
        content,
        development_nodes=nodes,
        upgrades=(),
        estate_forms=tuple(
            f.model_copy(update={"modifiers": (), "tags": ()})
            for f in content.estate_forms
        ),
    )
    skill = content.skill("gathering")
    baseline = stack_bound(skill, content)
    project_node = nodes[0].model_copy(
        update={"projects": ("project.verdant_cardboard",)}
    )
    project_content = replace(content, development_nodes=(project_node, *nodes[1:]))
    carried_node = nodes[0].model_copy(update={"carried_tags": ("bonus.fake",)})
    carried_content = replace(content, development_nodes=(carried_node, *nodes[1:]))
    assert stack_bound(skill, project_content) == pytest.approx(baseline * 1.02)
    assert stack_bound(skill, carried_content) == pytest.approx(baseline * 1.02)
