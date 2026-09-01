"""Tests for product data provider boundaries."""

import pytest

from providers.amazon_html_provider import AmazonHTMLProvider

pytestmark = pytest.mark.unit


class FakeScraper:
    def search_products(self, keyword, pages=1, category=None, is_asin=False):
        return [
            {
                "asin": " B08TEST123 ",
                "title": " Test Product ",
                "price": "19.99",
                "rating": "4.4",
                "reviews": "125",
                "bsr": "2500",
                "estimated_sales": "88",
                "estimated_margin": "42.5",
            }
        ]

    def get_product_details(self, asin):
        return {"asin": asin, "title": "Detail Product", "price": "24.50"}

    def get_seller_summary(self, asin, brand=""):
        return {
            "fba_count": "2",
            "fbm_count": "1",
            "amazon_seller": False,
            "brand_is_seller": False,
            "total_sellers": "3",
            "prices": {"fba": [19.99], "fbm": [18.99]},
            "seller_name": "Example Seller",
            "data_status": "observed",
        }


@pytest.mark.asyncio
async def test_amazon_html_provider_normalizes_search_products():
    provider = AmazonHTMLProvider(scraper=FakeScraper())

    products = await provider.search_products("test", pages=1)

    assert products == [
        {
            "asin": "B08TEST123",
            "title": "Test Product",
            "brand": "",
            "category": "",
            "url": "",
            "price": 19.99,
            "rating": 4.4,
            "reviews": 125,
            "bsr": 2500,
            "estimated_sales": 88,
            "estimated_margin": 42.5,
            "search_volume": 0,
            "seasonality": ["All Year"],
            "market_share": 0.0,
        }
    ]


@pytest.mark.asyncio
async def test_amazon_html_provider_normalizes_seller_summary():
    provider = AmazonHTMLProvider(scraper=FakeScraper())

    seller_summary = await provider.get_sellers("B08TEST123")

    assert seller_summary == {
        "fba_count": 2,
        "fbm_count": 1,
        "amazon_seller": False,
        "brand_is_seller": False,
        "total_sellers": 3,
        "prices": {"fba": [19.99], "fbm": [18.99]},
        "seller_name": "Example Seller",
        "data_status": "observed",
    }
