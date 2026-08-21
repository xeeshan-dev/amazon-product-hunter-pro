"""Amazon HTML provider adapter around the legacy AmazonScraper."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from providers.base import ProductDataProvider
from scraper.amazon_scraper import AmazonScraper


class AmazonHTMLProvider(ProductDataProvider):
    """Collect and normalize product data from Amazon HTML pages.

    The wrapped scraper still calculates some legacy estimate fields. This
    adapter keeps those fields for API compatibility while establishing the
    boundary where provider-owned collection/parsing ends and analytics can be
    moved out in later refactors.
    """

    DEFAULT_SELLER_SUMMARY = {
        "fba_count": 0,
        "fbm_count": 0,
        "amazon_seller": False,
        "total_sellers": 0,
        "prices": {"fba": [], "fbm": []},
        "seller_name": None,
    }

    def __init__(
        self,
        base_url: Optional[str] = None,
        scraper: Optional[AmazonScraper] = None,
    ):
        self.scraper = scraper or AmazonScraper(base_url=base_url)

    async def search_products(
        self,
        keyword: str,
        pages: int = 1,
        category: Optional[str] = None,
        is_asin: bool = False,
    ) -> List[Dict[str, Any]]:
        products = await asyncio.to_thread(
            self.scraper.search_products,
            keyword,
            pages,
            category,
            is_asin,
        )
        return [self._normalize_product(product) for product in products]

    async def get_product(self, asin: str) -> Optional[Dict[str, Any]]:
        product = await asyncio.to_thread(self.scraper.get_product_details, asin)
        if product is None:
            return None
        return self._normalize_product(product)

    async def get_sellers(self, asin: str) -> Dict[str, Any]:
        summary = await asyncio.to_thread(self.scraper.get_seller_summary, asin)
        return self._normalize_seller_summary(summary)

    async def get_offers(self, asin: str) -> Dict[str, Any]:
        return await self.get_sellers(asin)

    def _normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(product or {})
        normalized["asin"] = self._string_or_none(normalized.get("asin"))
        normalized["title"] = self._string_or_none(normalized.get("title")) or ""
        normalized["brand"] = self._string_or_none(normalized.get("brand")) or ""
        normalized["category"] = self._string_or_none(normalized.get("category")) or ""
        normalized["url"] = self._string_or_none(normalized.get("url")) or ""
        normalized["price"] = self._float_or_none(normalized.get("price"))
        normalized["rating"] = self._float_or_default(normalized.get("rating"), 0.0)
        normalized["reviews"] = self._int_or_default(normalized.get("reviews"), 0)
        normalized["bsr"] = self._int_or_none(normalized.get("bsr"))

        # Compatibility fields produced by the current scraper. These should
        # move to analytics services once the provider boundary is established.
        normalized["estimated_sales"] = self._int_or_default(
            normalized.get("estimated_sales"),
            0,
        )
        normalized["estimated_margin"] = self._float_or_default(
            normalized.get("estimated_margin"),
            0.0,
        )
        normalized["search_volume"] = self._int_or_default(
            normalized.get("search_volume"),
            0,
        )
        normalized["seasonality"] = normalized.get("seasonality") or ["All Year"]
        normalized["market_share"] = self._float_or_default(
            normalized.get("market_share"),
            0.0,
        )
        return normalized

    def _normalize_seller_summary(self, summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        seller = {**self.DEFAULT_SELLER_SUMMARY, **(summary or {})}
        prices = seller.get("prices") or {}
        return {
            "fba_count": self._int_or_default(seller.get("fba_count"), 0),
            "fbm_count": self._int_or_default(seller.get("fbm_count"), 0),
            "amazon_seller": bool(seller.get("amazon_seller", False)),
            "total_sellers": self._int_or_default(seller.get("total_sellers"), 0),
            "prices": {
                "fba": list(prices.get("fba") or []),
                "fbm": list(prices.get("fbm") or []),
            },
            "seller_name": self._string_or_none(seller.get("seller_name")),
        }

    @staticmethod
    def _string_or_none(value: Any) -> Optional[str]:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @staticmethod
    def _float_or_none(value: Any) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _float_or_default(cls, value: Any, default: float) -> float:
        parsed = cls._float_or_none(value)
        return default if parsed is None else parsed

    @staticmethod
    def _int_or_none(value: Any) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _int_or_default(cls, value: Any, default: int) -> int:
        parsed = cls._int_or_none(value)
        return default if parsed is None else parsed
