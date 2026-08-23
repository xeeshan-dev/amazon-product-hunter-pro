"""Scraper resilience and marketplace-awareness tests."""
from bs4 import BeautifulSoup

import pytest

from scraper.amazon_scraper import AmazonScraper

pytestmark = pytest.mark.unit


def make_price_element(offscreen_text):
    html = f"""
    <span class="a-price" data-a-color="base">
        <span class="a-offscreen">{offscreen_text}</span>
    </span>
    """
    return BeautifulSoup(html, 'html.parser').find('span', class_='a-price')


@pytest.mark.parametrize(
    'text,expected',
    [
        ('$12.99', 12.99),          # US
        ('£12.99', 12.99),          # UK
        ('US$12.99', 12.99),        # UK with forced USD prefs (old bug)
        ('CDN$1,299.00', 1299.0),   # Canada style
        ('12.99 €', 12.99),         # trailing symbol
    ],
)
def test_price_extraction_is_currency_agnostic(text, expected):
    scraper = AmazonScraper()
    assert scraper._extract_price(make_price_element(text)) == expected


def test_marketplace_prefs_follow_base_url():
    uk = AmazonScraper(base_url='https://www.amazon.co.uk')
    us = AmazonScraper()
    assert uk.prefs['currency'] == 'GBP'
    assert 'en-GB' in uk.prefs['language']
    assert us.prefs['currency'] == 'USD'
    assert 'ubid-main' not in uk._get_headers()['Cookie']
    assert 'ubid-main' not in us._get_headers()['Cookie']


def test_block_detection_catches_challenges():
    class FakeResponse:
        def __init__(self, status, body):
            self.status_code = status
            self.text = body
            from io import BytesIO
            self.content = body.encode()

    scraper = AmazonScraper()
    captcha = FakeResponse(200, '<html>Enter the characters you see below</html>')
    interstitial = FakeResponse(202, '<html>continue shopping</html>')
    healthy = FakeResponse(200, '<div>' + 'x' * 40_000 + '</div>')
    assert scraper._is_blocked(captcha) is True
    assert scraper._is_blocked(interstitial) is True
    assert scraper._is_blocked(healthy) is False