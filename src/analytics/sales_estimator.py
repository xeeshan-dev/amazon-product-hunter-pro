"""Sales estimation analytics.

This module owns BSR-to-sales heuristics independently from scraping code. The
numbers are estimates only; callers should treat them as directional signals.
"""

from dataclasses import dataclass
import math
from typing import Optional


@dataclass(frozen=True)
class SalesEstimateInput:
    bsr: Optional[int]
    category: Optional[str] = None


@dataclass(frozen=True)
class SalesEstimateResult:
    monthly_sales: int
    lower_bound: int
    upper_bound: int
    confidence: float
    method: str


class BSRSalesEstimator:
    """Estimate monthly unit sales from BSR and category."""

    CATEGORY_CURVES = {
        "Health & Household": (60000, 0.4),
        "Home & Kitchen": (50000, 0.4),
        "Beauty & Personal Care": (55000, 0.4),
        "Sports & Outdoors": (40000, 0.4),
        "Pet Supplies": (45000, 0.4),
        "Toys & Games": (45000, 0.45),
        "Electronics": (35000, 0.35),
    }
    DEFAULT_CURVE = (40000, 0.4)
    METHOD = "bsr_log_curve"

    def estimate(self, data: SalesEstimateInput) -> SalesEstimateResult:
        bsr = data.bsr or 0
        if bsr <= 0:
            return SalesEstimateResult(
                monthly_sales=0,
                lower_bound=0,
                upper_bound=0,
                confidence=0.0,
                method=self.METHOD,
            )

        category = data.category or ""
        curve = self.CATEGORY_CURVES.get(category, self.DEFAULT_CURVE)
        sales = self._estimate_monthly_sales(bsr, curve)
        lower_bound = max(0, int(round(sales * 0.7)))
        upper_bound = int(round(sales * 1.3))

        return SalesEstimateResult(
            monthly_sales=sales,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            confidence=self._confidence(bsr, category),
            method=self.METHOD,
        )

    def _estimate_monthly_sales(self, bsr: int, curve: tuple[int, float]) -> int:
        if bsr < 100:
            estimated_sales = 3000 + (100 - bsr) * 50
        else:
            c_value, exponent = curve
            estimated_sales = int(c_value * math.pow(bsr, -exponent))

        return max(0, min(int(estimated_sales), 50000))

    def _confidence(self, bsr: int, category: str) -> float:
        confidence = 0.65 if category in self.CATEGORY_CURVES else 0.5

        if bsr <= 5000:
            confidence += 0.1
        elif bsr > 100000:
            confidence -= 0.15

        return round(max(0.0, min(confidence, 0.85)), 2)
