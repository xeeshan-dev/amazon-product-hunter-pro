"""Small deterministic trend classification helpers."""
from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional


class TrendDirection(str, Enum):
    IMPROVING = "Improving"
    STABLE = "Stable"
    DECLINING = "Declining"
    INSUFFICIENT_DATA = "Insufficient Data"


def classify_trend(
    values: Iterable[Optional[float]],
    *,
    lower_is_better: bool = False,
    min_observations: int = 3,
    stable_threshold_pct: float = 2.0,
) -> TrendDirection:
    """Classify first-to-last movement without claiming significance."""
    observations = [float(value) for value in values if value is not None]
    if len(observations) < min_observations:
        return TrendDirection.INSUFFICIENT_DATA

    first, latest = observations[0], observations[-1]
    if first == 0:
        return TrendDirection.STABLE if latest == 0 else TrendDirection.INSUFFICIENT_DATA

    change_pct = ((latest - first) / abs(first)) * 100
    if abs(change_pct) <= stable_threshold_pct:
        return TrendDirection.STABLE

    improved = change_pct < 0 if lower_is_better else change_pct > 0
    return TrendDirection.IMPROVING if improved else TrendDirection.DECLINING
