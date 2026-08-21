import pytest

from scraper.amazon_scraper import AmazonScraper

pytestmark = pytest.mark.unit


class FakeSalesEstimator:
    def __init__(self):
        self.seen = None

    def estimate(self, data):
        self.seen = data

        class Result:
            monthly_sales = 321

        return Result()


def test_scraper_sales_estimation_delegates_to_analytics_service():
    scraper = AmazonScraper.__new__(AmazonScraper)
    scraper.sales_estimator = FakeSalesEstimator()

    sales = scraper._estimate_sales_from_bsr("2500", "Home & Kitchen")

    assert sales == 321
    assert scraper.sales_estimator.seen.bsr == 2500
    assert scraper.sales_estimator.seen.category == "Home & Kitchen"


def test_scraper_sales_estimation_handles_invalid_bsr():
    scraper = AmazonScraper.__new__(AmazonScraper)
    scraper.sales_estimator = FakeSalesEstimator()

    assert scraper._estimate_sales_from_bsr("not-a-number", "Home & Kitchen") == 0
