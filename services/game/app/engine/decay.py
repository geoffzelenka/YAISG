"""Pure hunger and asset-loss arithmetic shared by realms and estates."""

from math import isclose

from app.content.schemas import DecayStage, GaugeConfig, ShedConfig


def gauge_stage(gauge: float, config: GaugeConfig) -> DecayStage:
    """Classify days using strictly greater-than authored thresholds."""
    if gauge > config.failing_threshold:
        return DecayStage.FAILING
    if gauge > config.faltering_threshold:
        return DecayStage.FALTERING
    if gauge > config.strained_threshold:
        return DecayStage.STRAINED
    return DecayStage.FED


def advance_gauge(
    gauge: float, due_value: int, unmet_value: int, ticks: int, config: GaugeConfig
) -> float:
    """Weight missing upkeep by reference value; a fully fed tick recovers."""
    if not 0 <= unmet_value <= due_value or ticks <= 0:
        raise ValueError("upkeep requires 0 <= unmet <= due and positive ticks/day")
    if unmet_value:
        value = min(config.max, gauge + unmet_value / due_value / ticks)
    else:
        value = max(0.0, gauge - config.recovery_per_day / ticks)
    # Repeated fractional ticks must not cross a strict stage boundary solely
    # because binary floating-point addition accumulated a few rounding bits.
    for boundary in (
        0.0,
        config.strained_threshold,
        config.faltering_threshold,
        config.failing_threshold,
        config.max,
    ):
        if isclose(value, boundary, rel_tol=0, abs_tol=1e-12):
            return boundary
    return value


def advance_shed(
    progress: float, gauge: float, ticks: int, threshold: float, config: ShedConfig
) -> float:
    """Accumulate failing loss or drain rescued progress without restoring assets."""
    if ticks <= 0:
        raise ValueError("ticks/day must be positive")
    if gauge > threshold:
        value = (
            progress
            + (config.base_per_day + config.per_gauge_day * (gauge - threshold)) / ticks
        )
    else:
        value = max(0.0, progress - config.recovery_per_day / ticks)
    nearest = round(value)
    return (
        float(nearest) if isclose(value, nearest, rel_tol=0, abs_tol=1e-12) else value
    )
