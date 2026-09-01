"""Unit tests for seller offer parsing and seller-data status semantics."""

from types import SimpleNamespace

import pytest

from analysis.seller_analysis import (
    SELLER_DATA_STATUS_BLOCKED,
    SELLER_DATA_STATUS_OBSERVED,
    SELLER_DATA_STATUS_PARSE_FAILED,
    SellerAnalyzer,
)

pytestmark = pytest.mark.unit


class _CookieJar:
    def set(self, *args, **kwargs):
        return None


class _Session:
    def __init__(self):
        self.cookies = _CookieJar()


def _response(status_code: int, text: str):
    return SimpleNamespace(status_code=status_code, text=text, content=text.encode("utf-8"))


def test_seller_analysis_uses_marketplace_host_for_aod_requests():
    analyzer = SellerAnalyzer()
    session = _Session()
    seen_urls = []
    html = "<div class='aod-offer'><div class='aod-offer-soldBy'><a>Amazon.com</a></div></div>" + (" " * 800)

    def fake_fetch(url, headers, referer, timeout):
        seen_urls.append(url)
        return _response(200, html)

    info = analyzer.analyze_sellers(
        soup=None,
        asin="B00TEST123",
        session=session,
        brand="TestBrand",
        base_url="https://www.amazon.co.uk",
        fetch_response=fake_fetch,
    )

    assert seen_urls
    assert all(url.startswith("https://www.amazon.co.uk/") for url in seen_urls)
    assert info.data_status == SELLER_DATA_STATUS_OBSERVED
    assert info.amazon_seller is True


def test_seller_analysis_marks_blocked_when_offer_fetch_is_challenged():
    analyzer = SellerAnalyzer()
    session = _Session()

    def fake_fetch(url, headers, referer, timeout):
        return _response(503, "Robot Check")

    info = analyzer.analyze_sellers(
        soup=None,
        asin="B00TEST123",
        session=session,
        base_url="https://www.amazon.com",
        fetch_response=fake_fetch,
    )

    assert info.data_status == SELLER_DATA_STATUS_BLOCKED
    assert info.total_sellers == 0


def test_seller_analysis_marks_parse_failed_when_aod_payload_is_unusable():
    analyzer = SellerAnalyzer()
    session = _Session()
    malformed_html = "<html><body>aod-offer but no structured offer rows</body></html>" + (" " * 800)

    def fake_fetch(url, headers, referer, timeout):
        return _response(200, malformed_html)

    info = analyzer.analyze_sellers(
        soup=None,
        asin="B00TEST123",
        session=session,
        base_url="https://www.amazon.de",
        fetch_response=fake_fetch,
    )

    assert info.data_status == SELLER_DATA_STATUS_PARSE_FAILED
    assert info.total_sellers == 0
    assert info.amazon_seller is False
