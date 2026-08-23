"""Estimate-confidence and data-quality contract tests."""

from datetime import datetime, timezone
from types import SimpleNamespace

from web_app.backend.services.confidence_service import ConfidenceService


def test_estimate_includes_coarse_range_and_observation_metadata():
    snapshot = SimpleNamespace(confidence=0.8, source="amazon_html", recorded_at=datetime(2026, 1, 1, tzinfo=timezone.utc), price=1, bsr=1, reviews=1, estimated_sales=1, margin=1, opportunity_score=1)
    estimate = ConfidenceService().estimate(100.0, snapshot, "BSR + category model")

    assert estimate == {
        "value": 100.0, "lower_bound": 85.0, "upper_bound": 115.0,
        "confidence": 0.8, "source": "amazon_html", "observed_at": "2026-01-01T00:00:00+00:00", "method": "BSR + category model",
    }


def test_data_quality_does_not_claim_good_quality_for_stale_data():
    snapshot = SimpleNamespace(confidence=0.9, price=1, bsr=1, reviews=1, estimated_sales=1, margin=1, opportunity_score=1)
    quality = ConfidenceService().data_quality({"status": "Stale", "last_observed_at": "x", "source": "amazon_html", "age_seconds": 999, "confidence": 0.9}, snapshot)
    assert quality["quality"] == "Stale"
    assert quality["confidence"] == 0.9
