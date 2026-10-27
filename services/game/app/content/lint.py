"""Warning-only designer reports; no runtime state or database is needed.

Training integrates the checked-in XP costs at each level's best base rate.
It deliberately omits taper as well as bonuses, to measure the §5.2 anchors.
Stack bounds maximize XP-factor times speed-factor jointly within each group,
then multiply the group maxima. Realm and estate maxima may use different
nodes: this relaxation is conservative. See docs/v08/content-lint.md.
"""

import argparse
import json
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
from types import MappingProxyType

from app.config import CONTENT_DIR
from app.content.loader import ContentIndex, load_content
from app.content.schemas import Action, DecayStage, Modifier, ModifierType, Skill
from app.engine.core import (
    CharacterState,
    modifier_groups,
    realm_active_tags,
    resolve_caps,
)
from app.engine.tags import tags_present


@dataclass(frozen=True)
class ActionReport:
    """One action's authored rate and curve comparison."""

    action_id: str
    xp_per_hour: float
    target_xp_per_hour: float
    deviation_pct: float
    off_curve: str | None
    warning: bool


@dataclass(frozen=True)
class SkillReport:
    """Time anchors and external stack bound for one non-combat skill."""

    skill_id: str
    actions: tuple[ActionReport, ...]
    optimal_hours: float | None
    optimal_anchor_hours: int
    level_one_hours: float | None
    level_one_anchor_hours: int
    stack_bound: float
    stack_warning: bool


def target_xp_per_hour(unlock_level: int, g: float) -> Fraction:
    """Return the rational rate target without intermediate float rounding."""
    if not 1 <= unlock_level <= 100:
        raise ValueError("unlock level must be between 1 and 100")
    return Fraction(10_000_000, 2880) * Fraction(str(g)) ** (unlock_level - 1)


def action_rate(action: Action) -> Fraction:
    """Return exact base XP per hour, excluding all bonuses and constraints."""
    return Fraction(action.xp * 3_600_000, action.base_cycle_ms)


def training_hours(skill: Skill, costs: tuple[int, ...]) -> Fraction | None:
    """Integrate level costs at the best unlocked rate; None means blocked."""
    hours = Fraction(0)
    for level, cost in enumerate(costs, start=1):
        rate = max(
            (action_rate(a) for a in skill.actions if a.unlock_level <= level),
            default=Fraction(0),
        )
        if not rate:
            return None
        hours += cost / rate
    return hours


def _group_bound(
    modifiers: tuple[Modifier, ...], skill: Skill, content: ContentIndex
) -> float:
    factors = []
    for kind in (ModifierType.XP_PCT, ModifierType.CYCLE_SPEED_PCT):
        percent = sum(
            m.value
            for m in modifiers
            if m.type == kind
            and (m.skill_id is None or m.skill_id == skill.id)
            and (m.category is None or m.category == skill.category)
        )
        factors.append(max(content.progression.min_factor, 1 + percent / 100))
    return factors[0] * factors[1]


def stack_bound(skill: Skill, content: ContentIndex) -> float:
    """Bound uncapped external XP × speed, using distinct upgrades within slots."""
    content = replace(
        content,
        _nodes_by_id=MappingProxyType({n.id: n for n in content.development_nodes}),
        _forms_by_id=MappingProxyType({f.id: f for f in content.estate_forms}),
        _upgrades_by_id=MappingProxyType({u.id: u for u in content.upgrades}),
    )
    realm_best = 1.0
    estate_best = 1.0
    stages = (DecayStage.FED, DecayStage.FALTERING)
    candidates = product(
        content.development_nodes, content.estate_forms, stages, stages
    )
    for node, form, realm_stage, estate_stage in candidates:
        state = CharacterState(
            {},
            {},
            {},
            0,
            form.id,
            node.id,
            realm_stage=realm_stage,
            estate_stage=estate_stage,
        )
        realm = {tag.id for tag, _ in realm_active_tags(state, content)}
        upgrades = tuple(
            u for u in content.upgrades if tags_present(u.requires_realm_tags, realm)
        )
        for count in range(len(upgrades) + 1):
            for chosen in combinations(upgrades, count):
                candidate = replace(
                    state, installed_upgrades=tuple(u.id for u in chosen)
                )
                if count > resolve_caps(candidate, content).estate_upgrade_slots:
                    continue
                groups = modifier_groups(candidate, content)
                realm_best = max(realm_best, _group_bound(groups[2], skill, content))
                estate_best = max(estate_best, _group_bound(groups[1], skill, content))
    return realm_best * estate_best


def lint_content(content: ContentIndex) -> tuple[SkillReport, ...]:
    """Report every non-combat skill, including empty skills as blocked."""
    reports = []
    for skill in content.skills:
        if skill.category == "combat":
            continue
        actions = []
        for action in skill.actions:
            rate = action_rate(action)
            target = target_xp_per_hour(action.unlock_level, content.progression.lint.g)
            deviation = (rate / target - 1) * 100
            actions.append(
                ActionReport(
                    action.id,
                    float(rate),
                    float(target),
                    float(deviation),
                    action.off_curve,
                    abs(deviation)
                    > Fraction(str(content.progression.lint.tolerance_pct))
                    and action.off_curve is None,
                )
            )
        hours = training_hours(skill, content.xp_curve.root)
        first_rate = max(
            (action_rate(a) for a in skill.actions if a.unlock_level == 1),
            default=Fraction(0),
        )
        bound = stack_bound(skill, content)
        reports.append(
            SkillReport(
                skill.id,
                tuple(actions),
                None if hours is None else float(hours),
                720,
                float(sum(content.xp_curve.root) / first_rate) if first_rate else None,
                2880,
                bound,
                bound > 1.45,
            )
        )
    return tuple(reports)


def render_text(reports: tuple[SkillReport, ...]) -> str:
    """Render anchor comparisons and all action rates for a designer."""
    lines = ["XP-rate content lint (warning only; combat skipped)"]
    for report in reports:
        lines.append(
            f"{report.skill_id}: optimal={report.optimal_hours} h / 720; "
            f"level-1={report.level_one_hours} h / 2880 "
            "(None = no level-1 action)"
        )
        for action in report.actions:
            status = "WARNING" if action.warning else "OK"
            lines.append(
                f"  {status} {action.action_id}: {action.xp_per_hour:.2f} XP/h; "
                f"target={action.target_xp_per_hour:.2f}; "
                f"deviation={action.deviation_pct:+.2f}%; "
                f"off_curve={action.off_curve!r}"
            )
        status = "WARNING" if report.stack_warning else "OK"
        lines.append(f"  {status} external stack bound={report.stack_bound:.6f} / 1.45")
    return "\n".join(lines)


def main() -> int:
    """Print text and JSON by default; warnings always return success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-dir", type=Path, default=CONTENT_DIR)
    parser.add_argument("--format", choices=("text", "json", "both"), default="both")
    args = parser.parse_args()
    reports = lint_content(load_content(args.content_dir))
    if args.format in {"text", "both"}:
        print(render_text(reports))
    if args.format in {"json", "both"}:
        print(json.dumps([asdict(report) for report in reports], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
