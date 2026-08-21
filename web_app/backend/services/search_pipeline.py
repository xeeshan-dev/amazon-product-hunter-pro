"""Search pipeline orchestration.

This module keeps the current business behavior intact while separating the
API route from provider collection, enrichment, filtering, analytics, and
response assembly.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Dict, List, Optional

from analytics.profitability import ProfitabilityAnalyzer, ProfitabilityInput
from analytics.risk import ProductRiskAnalyzer
from providers.amazon_html_provider import AmazonHTMLProvider

logger = logging.getLogger(__name__)


MARKETPLACE_URLS = {
    "US": "https://www.amazon.com",
    "UK": "https://www.amazon.co.uk",
    "DE": "https://www.amazon.de",
}


class SearchPipeline:
    """Execute the product search pipeline for the active API contract."""

    def __init__(
        self,
        scorer,
        profitability: ProfitabilityAnalyzer,
        risk_analyzer: ProductRiskAnalyzer,
        provider_factory: Callable[..., Any] = AmazonHTMLProvider,
        seller_delay_range: tuple[float, float] = (0.3, 0.7),
    ):
        self.scorer = scorer
        self.profitability = profitability
        self.risk_analyzer = risk_analyzer
        self.provider_factory = provider_factory
        self.seller_delay_range = seller_delay_range

    async def run(self, request) -> Dict[str, Any]:
        logger.info(
            "Search request: %s (filters: amazon_seller=%s, brand_seller=%s, sales=%s-%s)",
            request.keyword,
            request.skip_amazon_seller,
            request.skip_brand_seller,
            request.min_sales,
            request.max_sales,
        )

        provider = self.provider_factory(
            base_url=MARKETPLACE_URLS.get(request.marketplace)
        )
        raw_products = await provider.search_products(
            request.keyword,
            pages=request.pages,
        )
        logger.info("Found %s products", len(raw_products))

        processed_results = []
        for product in raw_products:
            candidate = dict(product)

            if not self._passes_rating_filter(candidate, request):
                continue

            self._apply_score(candidate)

            if not self._apply_risk(candidate, request):
                continue

            sales = self._apply_financials(candidate)

            if not self._passes_margin_filter(candidate, request):
                continue

            if not self._passes_sales_filter(sales, request):
                continue

            await self._enrich_seller_info(candidate, request, provider)

            if not self._passes_seller_filters(candidate, request):
                continue

            processed_results.append(candidate)

        return self._build_response(processed_results, request)

    def _passes_rating_filter(self, product: Dict[str, Any], request) -> bool:
        rating = float(product.get("rating") or 0)
        return rating >= request.min_rating

    def _apply_score(self, product: Dict[str, Any]) -> None:
        score_result = self.scorer.calculate_score(product)
        product["enhanced_score"] = score_result.total_score
        product["score_breakdown"] = {
            "demand": score_result.demand_pillar.score,
            "competition": score_result.competition_pillar.score,
            "profit": score_result.profit_pillar.score,
        }
        product["is_vetoed"] = score_result.is_vetoed
        product["veto_reasons"] = score_result.veto_details

    def _apply_risk(self, product: Dict[str, Any], request) -> bool:
        result = self.risk_analyzer.analyze(product)
        product["risks"] = result.risks
        return not result.should_skip(
            skip_risky_brands=request.skip_risky_brands,
            skip_hazmat=request.skip_hazmat,
        )

    def _apply_financials(self, product: Dict[str, Any]) -> int:
        price = product.get("price", 0) or 0
        sales = product.get("estimated_sales", 0) or 0
        result = self.profitability.analyze(
            ProfitabilityInput(
                selling_price=price,
                estimated_sales=sales,
                category=product.get("category"),
            )
        )
        product["est_revenue"] = result.revenue
        product["fees_breakdown"] = {
            "referral": result.fees.referral,
            "fba": result.fees.fba,
            "storage": result.fees.storage,
            "total": result.fees.total,
        }
        product["est_profit"] = result.net_profit
        product["margin"] = result.margin
        return sales

    def _passes_margin_filter(self, product: Dict[str, Any], request) -> bool:
        return product["margin"] >= request.min_margin

    def _passes_sales_filter(self, sales: int, request) -> bool:
        return request.min_sales <= sales <= request.max_sales

    async def _enrich_seller_info(
        self,
        product: Dict[str, Any],
        request,
        provider,
    ) -> None:
        if not (request.skip_amazon_seller or request.skip_brand_seller):
            product["seller_info"] = {
                "amazon_seller": False,
                "total_sellers": 0,
                "seller_name": None,
            }
            return

        asin = product.get("asin")
        if not asin:
            product["seller_info"] = {
                "amazon_seller": False,
                "total_sellers": 0,
                "seller_name": None,
            }
            return

        try:
            seller_summary = await provider.get_sellers(asin)
            product["seller_info"] = seller_summary

            brand = product.get("brand", "")
            if not brand:
                title = product.get("title", "")
                brand = title.split(" ")[0] if title else ""
            product["brand"] = brand

            logger.debug(
                "[%s] seller='%s' brand='%s'",
                asin,
                seller_summary.get("seller_name"),
                brand,
            )

            if self.seller_delay_range != (0, 0):
                await asyncio.sleep(random.uniform(*self.seller_delay_range))
        except Exception as exc:
            logger.warning("Failed to fetch seller info for %s: %s", asin, exc)
            product["seller_info"] = {
                "amazon_seller": False,
                "total_sellers": 0,
                "seller_name": None,
            }

    def _passes_seller_filters(self, product: Dict[str, Any], request) -> bool:
        seller_info = product.get("seller_info", {})
        if request.skip_amazon_seller and seller_info.get("amazon_seller", False):
            logger.info("Skipping product %s - Amazon is seller", product.get("asin"))
            return False

        if request.skip_brand_seller:
            seller_name = seller_info.get("seller_name", "") or ""
            brand = product.get("brand", "") or ""

            if seller_name and brand:
                seller_lower = seller_name.lower()
                brand_lower = brand.lower()
                if brand_lower in seller_lower or seller_lower in brand_lower:
                    logger.info(
                        "Skipping product %s - Seller '%s' matches brand '%s'",
                        product.get("asin"),
                        seller_name,
                        brand,
                    )
                    return False

        return True

    def _build_response(
        self,
        processed_results: List[Dict[str, Any]],
        request,
    ) -> Dict[str, Any]:
        total_market_revenue = sum(
            product.get("est_revenue", 0) for product in processed_results
        )
        for product in processed_results:
            if total_market_revenue > 0:
                product["market_share"] = (
                    product["est_revenue"] / total_market_revenue
                ) * 100
            else:
                product["market_share"] = 0

        processed_results.sort(key=lambda item: item.get("est_revenue", 0), reverse=True)

        return {
            "summary": {
                "total_products": len(processed_results),
                "total_revenue": total_market_revenue,
                "avg_revenue": (
                    total_market_revenue / len(processed_results)
                    if processed_results
                    else 0
                ),
                "avg_sales": (
                    sum(product.get("estimated_sales", 0) for product in processed_results)
                    / len(processed_results)
                    if processed_results
                    else 0
                ),
            },
            "results": processed_results[:50],
            "metadata": {
                "keyword": request.keyword,
                "marketplace": request.marketplace,
                "filters_applied": {
                    "min_rating": request.min_rating,
                    "min_margin": request.min_margin,
                    "sales_range": f"{request.min_sales}-{request.max_sales}",
                    "skip_amazon_seller": request.skip_amazon_seller,
                    "skip_brand_seller": request.skip_brand_seller,
                },
            },
        }
