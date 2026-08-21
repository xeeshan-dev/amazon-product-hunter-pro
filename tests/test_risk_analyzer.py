from types import SimpleNamespace

import pytest

from analytics.risk import ProductRiskAnalyzer

pytestmark = pytest.mark.unit


class FakeBrandRiskChecker:
    def __init__(self, is_veto=False):
        self.is_veto = is_veto

    def check_brand(self, brand, title):
        return SimpleNamespace(
            risk_level=SimpleNamespace(value="critical" if self.is_veto else "safe"),
            reason="Known risky brand" if self.is_veto else "No known risk",
            is_veto=self.is_veto,
        )


class FakeHazmatDetector:
    def __init__(self, is_hazmat=False, is_veto=False, category=None):
        self.is_hazmat = is_hazmat
        self.is_veto = is_veto
        self.category = category

    def check_product(self, product):
        return SimpleNamespace(
            is_hazmat=self.is_hazmat,
            category=self.category,
            is_veto=self.is_veto,
        )


def test_product_risk_analyzer_preserves_response_shape():
    analyzer = ProductRiskAnalyzer(
        FakeBrandRiskChecker(),
        FakeHazmatDetector(
            is_hazmat=True,
            is_veto=False,
            category=SimpleNamespace(value="battery"),
        ),
    )

    result = analyzer.analyze({"brand": "SafeBrand", "title": "Battery Pack"})

    assert result.risks == {
        "brand_risk": "safe",
        "brand_reason": "No known risk",
        "hazmat": True,
        "hazmat_category": "battery",
    }
    assert result.should_skip(skip_risky_brands=True, skip_hazmat=True) is False


def test_product_risk_analyzer_skip_decision_respects_request_flags():
    result = ProductRiskAnalyzer(
        FakeBrandRiskChecker(is_veto=True),
        FakeHazmatDetector(is_hazmat=True, is_veto=True),
    ).analyze({"brand": "RiskyBrand", "title": "Risky Product"})

    assert result.should_skip(skip_risky_brands=True, skip_hazmat=False) is True
    assert result.should_skip(skip_risky_brands=False, skip_hazmat=True) is True
    assert result.should_skip(skip_risky_brands=False, skip_hazmat=False) is False
