import pytest

from analytics.recommendations import OpportunityRecommendationEngine


pytestmark = pytest.mark.unit


def test_recommendation_engine_reports_strong_opportunity():
    result = OpportunityRecommendationEngine().generate(
        demand_score=75,
        competition_score=80,
        profit_score=85,
        total_score=78,
    )

    assert result.strengths == [
        "Strong demand indicators",
        "Favorable competitive landscape",
        "Good profit potential",
    ]
    assert result.weaknesses == []
    assert result.recommendations == [
        "\u2705 Product shows strong opportunity - proceed with sourcing research"
    ]


def test_recommendation_engine_reports_low_pillars_and_alternative():
    result = OpportunityRecommendationEngine().generate(
        demand_score=35,
        competition_score=30,
        profit_score=20,
        total_score=25,
    )

    assert result.strengths == []
    assert result.weaknesses == [
        "Weak demand signals",
        "Highly competitive market",
        "Margin concerns",
    ]
    assert result.recommendations == [
        "Verify demand with more research before sourcing",
        "Consider finding a less saturated niche",
        "Try to source at lower cost or find higher-priced alternatives",
        "\u26a0\ufe0f Consider alternative products with better metrics",
    ]
