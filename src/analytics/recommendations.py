"""Opportunity recommendation analytics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class OpportunityRecommendationResult:
    """Actionable summary derived from opportunity score pillars."""

    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class OpportunityRecommendationEngine:
    """Generate stable opportunity insights from scoring outputs."""

    def generate(
        self,
        demand_score: float,
        competition_score: float,
        profit_score: float,
        total_score: float,
    ) -> OpportunityRecommendationResult:
        strengths = []
        weaknesses = []
        recommendations = []

        if demand_score >= 70:
            strengths.append("Strong demand indicators")
        elif demand_score < 40:
            weaknesses.append("Weak demand signals")
            recommendations.append("Verify demand with more research before sourcing")

        if competition_score >= 70:
            strengths.append("Favorable competitive landscape")
        elif competition_score < 40:
            weaknesses.append("Highly competitive market")
            recommendations.append("Consider finding a less saturated niche")

        if profit_score >= 70:
            strengths.append("Good profit potential")
        elif profit_score < 40:
            weaknesses.append("Margin concerns")
            recommendations.append(
                "Try to source at lower cost or find higher-priced alternatives"
            )

        if total_score >= 70:
            recommendations.append(
                "\u2705 Product shows strong opportunity - proceed with sourcing research"
            )
        elif total_score >= 50:
            recommendations.append(
                "\U0001f4ca Moderate opportunity - do additional research before committing"
            )
        else:
            recommendations.append("\u26a0\ufe0f Consider alternative products with better metrics")

        return OpportunityRecommendationResult(
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )
