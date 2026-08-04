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

    assert xp_progress(40, curve) == (40, 60)
    assert xp_progress(100, curve) == (0, 112)
