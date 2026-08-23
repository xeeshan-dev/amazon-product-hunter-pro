"""Standard data-quality and estimate presentation derived from observations."""
from __future__ import annotations

from typing import Any, Dict, Optional


class ConfidenceService:
    """Describe estimate uncertainty without changing deterministic analytics."""

    def estimate(self, value: Optional[float], snapshot, method: str) -> Dict[str, Any]:
        confidence = snapshot.confidence if snapshot and snapshot.confidence is not None else self._default_confidence(snapshot)
        spread = self._spread_for(confidence)
        return {
            "value": value,
            "lower_bound": None if value is None else round(value * (1 - spread), 2),
            "upper_bound": None if value is None else round(value * (1 + spread), 2),
            "confidence": confidence,
            "source": snapshot.source if snapshot else None,
            "observed_at": snapshot.recorded_at.isoformat() if snapshot and snapshot.recorded_at else None,
            "method": method,
        }

    def data_quality(self, freshness: Dict[str, Any], snapshot) -> Dict[str, Any]:
        confidence = snapshot.confidence if snapshot and snapshot.confidence is not None else self._default_confidence(snapshot)
        status = freshness["status"]
        quality = "Unavailable" if status == "Unavailable" else "Good" if status == "Fresh" and confidence >= 0.7 else "Limited" if status != "Stale" else "Stale"
        return {**freshness, "quality": quality, "confidence": confidence}

    @staticmethod
    def _default_confidence(snapshot) -> Optional[float]:
        if snapshot is None:
            return None
        populated = sum(value is not None for value in (
            snapshot.price, snapshot.bsr, snapshot.reviews, snapshot.estimated_sales,
            snapshot.margin, snapshot.opportunity_score,
        ))
        return round(min(0.8, 0.35 + (populated * 0.075)), 2)

    @staticmethod
    def _spread_for(confidence: Optional[float]) -> float:
        if confidence is None:
            return 0.5
        if confidence >= 0.8:
            return 0.15
        if confidence >= 0.6:
            return 0.25
        return 0.4
