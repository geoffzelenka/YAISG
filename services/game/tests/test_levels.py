"""Properties of the XP level engine."""

from app.config import CONTENT_DIR
from app.content import load_content
from app.engine.levels import level_for_xp, xp_progress


def test_level_for_xp_is_monotonic_and_consistent_with_table() -> None:
    """Every table boundary advances once and arbitrary XP never lowers level."""
    curve = load_content(CONTENT_DIR).xp_curve.levels
    samples = sorted(
        {0, *(entry.xp for entry in curve), *(max(0, entry.xp - 1) for entry in curve)}
    )
    levels = [level_for_xp(xp, curve) for xp in samples]

    assert levels == sorted(levels)
    for entry in curve:
        assert level_for_xp(entry.xp, curve) == entry.level


def test_xp_progress_reports_remaining_xp() -> None:
    """Progress values meet at the next cumulative XP boundary."""
    curve = load_content(CONTENT_DIR).xp_curve.levels

    assert xp_progress(40, curve) == (40, 17)
    assert xp_progress(57, curve) == (0, 63)


def test_design_curve_reference_points_and_halfway() -> None:
    """Exact floored costs and cumulative totals match design section 5.1."""
    curve = load_content(CONTENT_DIR).xp_curve
    for level, step, cumulative in (
        (1, 57, 0),
        (50, 7365, 70189),
        (75, 87564, 840648),
        (90, 386714, 3714612),
        (93, 520478, 4999703),
        (95, 634470, 6094836),
        (99, 942820, 9057180),
    ):
        assert curve.root[level - 1] == step
        assert curve.levels[level - 1].xp == cumulative
    assert curve.levels[92].xp < 5_000_000 <= curve.levels[93].xp


def test_every_boundary_and_uncapped_xp() -> None:
    """Levels advance exactly at thresholds and stop at 100."""
    curve = load_content(CONTENT_DIR).xp_curve.levels
    for entry in curve[1:]:
        assert level_for_xp(entry.xp - 1, curve) == entry.level - 1
        assert level_for_xp(entry.xp, curve) == entry.level
        assert level_for_xp(entry.xp + 1, curve) == entry.level
    assert level_for_xp(10_000_000, curve) == 100
    assert level_for_xp(10**15, curve) == 100
    assert xp_progress(10**15, curve) == (10**15 - 10_000_000, None)


def test_tier_boundaries() -> None:
    """Each tier starts at its content threshold."""
    from app.engine.levels import tier_for_level

    thresholds = load_content(CONTENT_DIR).progression.tier_thresholds
    for level, tier in (
        (1, 1),
        (49, 1),
        (50, 2),
        (74, 2),
        (75, 3),
        (89, 3),
        (90, 4),
        (94, 4),
        (95, 5),
        (100, 5),
    ):
        assert tier_for_level(level, thresholds) == tier


def test_generator_reproduces_checked_in_curve() -> None:
    """Exact amplitude search reproduces the checked-in per-level costs."""
    import json
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from scripts.gen_xp_curve import build_curve; "
            "print(json.dumps(build_curve()))",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == list(load_content(CONTENT_DIR).xp_curve.root)
