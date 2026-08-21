"""Product risk analytics."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ProductRiskResult:
    risks: Dict[str, Any]
    brand_veto: bool
    hazmat_veto: bool

    def should_skip(self, skip_risky_brands: bool, skip_hazmat: bool) -> bool:
        return (skip_risky_brands and self.brand_veto) or (
            skip_hazmat and self.hazmat_veto
        )


class ProductRiskAnalyzer:
    """Evaluate brand and hazmat risk for product candidates."""

    def __init__(self, brand_checker, hazmat_detector):
        self.brand_checker = brand_checker
        self.hazmat_detector = hazmat_detector

    def analyze(self, product: Dict[str, Any]) -> ProductRiskResult:
        brand_risk = self.brand_checker.check_brand(
            product.get("brand", ""),
            product.get("title", ""),
        )
        hazmat = self.hazmat_detector.check_product(product)

        return ProductRiskResult(
            risks={
                "brand_risk": brand_risk.risk_level.value,
                "brand_reason": brand_risk.reason,
                "hazmat": hazmat.is_hazmat,
                "hazmat_category": self._hazmat_category(hazmat),
            },
            brand_veto=bool(brand_risk.is_veto),
            hazmat_veto=bool(hazmat.is_veto),
        )

    @staticmethod
    def _hazmat_category(hazmat) -> Optional[str]:
        category = getattr(hazmat, "category", None)
        return category.value if category else None
