"""Provider boundary for product data collection.

Providers collect and normalize external product data. They should not make
opportunity, profitability, risk, recommendation, or user-filter decisions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ProductProviderError(RuntimeError):
    """Raised when a product data provider cannot complete a request."""


class ProductDataProvider(ABC):
    """Interface for product data providers."""

    @abstractmethod
    async def search_products(
        self,
        keyword: str,
        pages: int = 1,
        category: Optional[str] = None,
        is_asin: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search for products and return normalized product dictionaries."""

    @abstractmethod
    async def get_product(self, asin: str) -> Optional[Dict[str, Any]]:
        """Fetch one normalized product by ASIN."""

    @abstractmethod
    async def get_sellers(self, asin: str) -> Dict[str, Any]:
        """Fetch normalized seller summary data for an ASIN."""

    async def get_offers(self, asin: str) -> Dict[str, Any]:
        """Fetch offer data for an ASIN.

        The current Amazon HTML implementation only exposes seller summary data,
        so this method aliases `get_sellers` until offers are modeled separately.
        """
        return await self.get_sellers(asin)
