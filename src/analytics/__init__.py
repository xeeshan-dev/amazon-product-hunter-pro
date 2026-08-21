"""Isolated analytics services."""
from analytics.profitability import ProfitabilityAnalyzer, ProfitabilityInput, ProfitabilityResult
from analytics.recommendations import (
    OpportunityRecommendationEngine,
    OpportunityRecommendationResult,
)
from analytics.risk import ProductRiskAnalyzer, ProductRiskResult
from analytics.sales_estimator import BSRSalesEstimator, SalesEstimateInput, SalesEstimateResult

__all__ = [
    "BSRSalesEstimator",
    "ProfitabilityAnalyzer",
    "ProfitabilityInput",
    "ProfitabilityResult",
    "OpportunityRecommendationEngine",
    "OpportunityRecommendationResult",
    "ProductRiskAnalyzer",
    "ProductRiskResult",
    "SalesEstimateInput",
    "SalesEstimateResult",
]
