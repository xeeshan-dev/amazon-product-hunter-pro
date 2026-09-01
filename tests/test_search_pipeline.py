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

    async def get_sellers(self, asin, brand=""):
        return {
            "amazon_seller": False,
            "brand_is_seller": False,
            "total_sellers": 2,
            "seller_name": "Independent Seller",
            "prices": {"fba": [], "fbm": []},
            "fba_count": 1,
            "fbm_count": 1,
            "data_status": "observed",
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
    # seller data is always fetched (needed for brand-owner / Amazon dominance detection)
    assert response["results"][0]["seller_info"]["data_status"] == "observed"
    assert response["summary"]["filter_mode"] == "strict"


@pytest.mark.asyncio
async def test_search_pipeline_enriches_sellers_when_seller_filters_active():
    pipeline = make_pipeline()

    response = await pipeline.run(make_request(skip_amazon_seller=True))

    assert response["summary"]["total_products"] == 1
    assert response["results"][0]["seller_info"]["seller_name"] == "Independent Seller"
    assert response["results"][0]["seller_info"]["data_status"] == "observed"


@pytest.mark.asyncio
async def test_search_pipeline_returns_review_candidates_when_strict_filters_match_none():
    pipeline = make_pipeline()

    response = await pipeline.run(make_request(min_sales=500, min_margin=50))

    assert response["summary"]["filter_mode"] == "review_fallback"
    assert response["summary"]["review_candidates_returned"] is True
    candidate = response["results"][0]
    assert "sales_below_preference" in candidate["winning_product"]["review_flags"]
    assert "margin_below_preference" in candidate["winning_product"]["review_flags"]


@pytest.mark.asyncio
async def test_search_pipeline_keeps_keyword_risk_flags_for_manual_validation():
    class FlaggedRiskAnalyzer:
        def analyze(self, product):
            return SimpleNamespace(risks={"brand_risk": "HIGH", "hazmat": True})

    pipeline = make_pipeline()
    pipeline.risk_analyzer = FlaggedRiskAnalyzer()
    response = await pipeline.run(make_request())

    assert response["summary"]["total_products"] == 1
    flags = response["results"][0]["winning_product"]["review_flags"]
    assert "brand_risk_requires_manual_validation" in flags
    assert "hazmat_flag_requires_manual_validation" in flags


@pytest.mark.asyncio
async def test_search_pipeline_excludes_confirmed_amazon_seller_when_requested():
    class AmazonSellerProvider(FakeProvider):
        async def get_sellers(self, asin, brand=""):
            return {
                "amazon_seller": True,
                "brand_is_seller": False,
                "total_sellers": 2,
                "seller_name": "Amazon.com",
                "data_status": "observed",
            }

    pipeline = make_pipeline()
    pipeline.provider_factory = AmazonSellerProvider

    response = await pipeline.run(make_request(skip_amazon_seller=True))

    assert response["summary"]["total_products"] == 0


@pytest.mark.asyncio
async def test_search_pipeline_excludes_confirmed_brand_seller_when_requested():
    class BrandSellerProvider(FakeProvider):
        async def get_sellers(self, asin, brand=""):
            return {
                "amazon_seller": False,
                "brand_is_seller": True,
                "total_sellers": 4,
                "seller_name": "Independent Seller",
                "data_status": "observed",
            }

    pipeline = make_pipeline()
    pipeline.provider_factory = BrandSellerProvider

    response = await pipeline.run(make_request(skip_brand_seller=True))

    assert response["summary"]["total_products"] == 0


@pytest.mark.asyncio
async def test_search_pipeline_excludes_unverified_seller_data_in_strict_mode():
    class UnavailableSellerProvider(FakeProvider):
        async def get_sellers(self, asin, brand=""):
            return {
                "amazon_seller": False,
                "brand_is_seller": False,
                "total_sellers": 0,
                "seller_name": None,
                "data_status": "blocked",
            }

    pipeline = make_pipeline()
    pipeline.provider_factory = UnavailableSellerProvider

    response = await pipeline.run(
        make_request(skip_amazon_seller=True, skip_brand_seller=True)
    )

    assert response["summary"]["total_products"] == 0


@pytest.mark.asyncio
async def test_search_pipeline_skips_products_missing_required_validation_data():
    class InvalidProductProvider(FakeProvider):
        async def search_products(self, keyword, pages=1):
            return [{"asin": "B001", "title": "Incomplete", "price": 0, "rating": 5}]

    pipeline = make_pipeline()
    pipeline.provider_factory = InvalidProductProvider

    response = await pipeline.run(make_request())

    assert response["summary"]["total_products"] == 0
