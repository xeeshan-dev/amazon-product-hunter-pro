"""Tests for the search pipeline orchestration."""

from types import SimpleNamespace

import pytest

from analytics.profitability import ProfitabilityAnalyzer
from analytics.risk import ProductRiskAnalyzer
from web_app.backend.services.search_pipeline import SearchPipeline

pytestmark = pytest.mark.unit


class FakeProvider:
    def __init__(self, base_url=None):
        self.base_url = base_url

    async def search_products(self, keyword, pages=1):
        return [
            {
                "asin": "B001",
                "title": "BrandOne Test Product",
                "brand": "BrandOne",
                "price": 20.0,
                "rating": 4.5,
                "reviews": 100,
                "estimated_sales": 100,
            },
            {
                "asin": "B002",
                "title": "Low Rated Product",
                "brand": "BrandTwo",
                "price": 10.0,
                "rating": 2.0,
                "reviews": 10,
                "estimated_sales": 50,
            },
        ]

    async def get_sellers(self, asin):
        return {
            "amazon_seller": False,
            "total_sellers": 2,
            "seller_name": "Independent Seller",
            "prices": {"fba": [], "fbm": []},
            "fba_count": 1,
            "fbm_count": 1,
        }


class FakeScorer:
    def calculate_score(self, product):
        pillar = SimpleNamespace(score=80)
        return SimpleNamespace(
            total_score=80,
            demand_pillar=pillar,
            competition_pillar=pillar,
            profit_pillar=pillar,
            is_vetoed=False,
            veto_details=[],
        )


class FakeFeeCalculator:
    def calculate_all_fees(self, price, category=None):
        return SimpleNamespace(
            referral_fee=price * 0.15,
            fba_fulfillment_fee=3.0,
            monthly_storage_fee=0.25,
            total_amazon_fees=(price * 0.15) + 3.25,
        )


class FakeBrandRiskChecker:
    def check_brand(self, brand, title):
        return SimpleNamespace(
            risk_level=SimpleNamespace(value="SAFE"),
            reason="No known risk",
            is_veto=False,
        )


class FakeHazmatDetector:
    def check_product(self, product):
        return SimpleNamespace(is_hazmat=False, category=None, is_veto=False)


def make_request(**overrides):
    defaults = {
        "keyword": "test",
        "marketplace": "US",
        "pages": 1,
        "min_rating": 3.0,
        "skip_risky_brands": True,
        "skip_hazmat": True,
        "skip_amazon_seller": False,
        "skip_brand_seller": False,
        "min_margin": 0,
        "min_sales": 0,
        "max_sales": 1000,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_pipeline():
    return SearchPipeline(
        scorer=FakeScorer(),
        profitability=ProfitabilityAnalyzer(FakeFeeCalculator()),
        risk_analyzer=ProductRiskAnalyzer(
            FakeBrandRiskChecker(),
            FakeHazmatDetector(),
        ),
        provider_factory=FakeProvider,
        seller_delay_range=(0, 0),
    )


@pytest.mark.asyncio
async def test_search_pipeline_filters_and_scores_products():
    pipeline = make_pipeline()

    response = await pipeline.run(make_request())

    assert response["summary"]["total_products"] == 1
    assert response["summary"]["total_revenue"] == 2000.0
    assert response["results"][0]["asin"] == "B001"
    assert response["results"][0]["enhanced_score"] == 80
    assert response["results"][0]["seller_info"]["seller_name"] is None


@pytest.mark.asyncio
async def test_search_pipeline_enriches_sellers_when_seller_filters_active():
    pipeline = make_pipeline()

    response = await pipeline.run(make_request(skip_amazon_seller=True))

    assert response["summary"]["total_products"] == 1
    assert response["results"][0]["seller_info"]["seller_name"] == "Independent Seller"
