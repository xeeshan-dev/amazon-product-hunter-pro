"""Tests for profitability analytics."""

from types import SimpleNamespace

import pytest

from analytics.profitability import ProfitabilityAnalyzer, ProfitabilityInput

pytestmark = pytest.mark.unit


class FakeFeeCalculator:
    def calculate_all_fees(self, price, category=None):
        return SimpleNamespace(
            referral_fee=price * 0.15,
            fba_fulfillment_fee=3.0,
            monthly_storage_fee=0.25,
            total_amazon_fees=(price * 0.15) + 3.25,
        )


def test_profitability_analyzer_preserves_current_search_assumptions():
    analyzer = ProfitabilityAnalyzer(FakeFeeCalculator())

    result = analyzer.analyze(
        ProfitabilityInput(
            selling_price=20.0,
            estimated_sales=100,
            category="Home & Kitchen",
        )
    )

    assert result.revenue == 2000.0
    assert result.fees.referral == 3.0
    assert result.fees.fba == 3.0
    assert result.fees.storage == 0.25
    assert result.fees.total == 6.25
    assert result.cogs == 5.0
    assert result.net_profit == 8.75
    assert result.margin == 43.75


def test_profitability_analyzer_handles_zero_price():
    analyzer = ProfitabilityAnalyzer(FakeFeeCalculator())

    result = analyzer.analyze(ProfitabilityInput(selling_price=0, estimated_sales=100))

    assert result.revenue == 0
    assert result.net_profit == -3.25
    assert result.margin == 0
