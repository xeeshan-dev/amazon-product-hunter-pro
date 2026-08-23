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
from analytics.winning_product_filter import WinningProductFilter
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
        persistence_service: Optional[Any] = None,
        winning_filter: Optional[WinningProductFilter] = None,
        history_service: Optional[Any] = None,
    ):
        self.scorer = scorer
        self.profitability = profitability
        self.risk_analyzer = risk_analyzer
        self.provider_factory = provider_factory
        self.seller_delay_range = seller_delay_range
        self.persistence_service = persistence_service
        self.winning_filter = winning_filter or WinningProductFilter()
        self.history_service = history_service

    async def run(
        self,
        request,
        db=None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
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

        strict_results = []
        review_results = []
        for product in raw_products:
            candidate = dict(product)

            validation_errors = self.winning_filter.validate(candidate)
            if validation_errors:
                logger.debug("Skipping invalid product %s: %s", candidate.get("asin"), validation_errors)
                continue
            if not self._passes_rating_filter(candidate, request):
                continue

            sales = self._apply_financials(candidate)

            self._apply_score(candidate)

            risk_result = self._apply_risk(candidate)
            if self._is_confirmed_major_risk(risk_result, request):
                logger.info(
                    "Skipping product %s due to a confirmed major risk",
                    candidate.get("asin"),
                )
                continue

            await self._enrich_seller_info(candidate, request, provider)
            history = self._observation_history(candidate, request.marketplace, db)
            qualification = self.winning_filter.evaluate(
                candidate,
                request,
                history=history,
            )
            candidate["winning_product"] = qualification
            if qualification["confirmed_seller_conflict"]:
                logger.info("Skipping product %s due to confirmed seller conflict", candidate.get("asin"))
                continue

            if qualification["strict_match"]:
                strict_results.append(candidate)
            else:
                review_results.append(candidate)

        filter_mode = "strict" if strict_results else "review_fallback"
        processed_results = strict_results or review_results
        response = self._build_response(processed_results, request, filter_mode)
        if self.persistence_service is not None and db is not None:
            self.persistence_service.persist(
                db=db,
                request=request,
                products=response["results"],
                user_id=user_id,
            )

        self._remove_persistence_metadata(response["results"])
        return response

    def _passes_rating_filter(self, product: Dict[str, Any], request) -> bool:
        rating = float(product.get("rating") or 0)
        return rating >= request.min_rating

    async def analyze_product(self, product: Dict[str, Any], provider) -> Dict[str, Any]:
        """Apply the existing deterministic analysis stack to one product."""
        candidate = dict(product)
        self._apply_financials(candidate)
        self._apply_score(candidate)
        candidate["risks"] = self.risk_analyzer.analyze(candidate).risks
        request = type("AnalyzerRequest", (), {
            "skip_amazon_seller": True,
            "skip_brand_seller": True,
        })()
        await self._enrich_seller_info(candidate, request, provider)
        return candidate

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
        recommendations = getattr(score_result, "recommendations", [])
        product["_search_recommendation"] = (
            recommendations[-1] if recommendations else None
        )
        product["_search_confidence"] = getattr(score_result, "confidence", None)

    def _apply_risk(self, product: Dict[str, Any]):
        result = self.risk_analyzer.analyze(product)
        product["risks"] = result.risks
        # Surface confirmed veto facts so downstream qualification can treat
        # them as facts rather than as uncertain review flags.
        if getattr(result, "brand_veto", None) is not None:
            product["risks"]["brand_veto"] = bool(result.brand_veto)
        if getattr(result, "hazmat_veto", None) is not None:
            product["risks"]["hazmat_veto"] = bool(result.hazmat_veto)
        return result

    def _observation_history(self, product, marketplace, db):
        """Reuse stored canonical observations for trend-aware qualification.

        Returns None when no history service is wired, no database session is
        available, or the ASIN has no stored observations yet. Lookup failures
        never fail the search; candidates simply qualify without trend data.
        """
        if self.history_service is None or db is None:
            return None
        asin = product.get("asin")
        if not asin:
            return None
        try:
            return self.history_service.get_observation_history_for_asin(
                db,
                asin,
                marketplace=marketplace,
            )
        except Exception as exc:
            logger.warning("Observation history lookup failed for %s: %s", asin, exc)
            return None

    @staticmethod
    def _is_confirmed_major_risk(risk_result, request) -> bool:
        """Confirmed veto-level risks are excluded only when requested."""
        if risk_result is None:
            return False
        brand_veto = bool(getattr(risk_result, "brand_veto", False))
        hazmat_veto = bool(getattr(risk_result, "hazmat_veto", False))
        return (request.skip_risky_brands and brand_veto) or (
            request.skip_hazmat and hazmat_veto
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
        product["profit_margin"] = result.margin
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
                "data_status": "not_requested",
            }
            return

        asin = product.get("asin")
        if not asin:
            product["seller_info"] = {
                "amazon_seller": False,
                "total_sellers": None,
                "seller_name": None,
                "data_status": "unavailable",
            }
            return

        try:
            seller_summary = await provider.get_sellers(asin)
            seller_summary["data_status"] = "observed"
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
                "total_sellers": None,
                "seller_name": None,
                "data_status": "unavailable",
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
        filter_mode: str = "strict",
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

        processed_results.sort(
            key=lambda item: (
                item.get("winning_product", {}).get("composite_score", 0),
                item.get("est_revenue", 0),
            ),
            reverse=True,
        )

        verdict_counts: Dict[str, int] = {}
        for product in processed_results:
            decision = (product.get("winning_product") or {}).get("decision") or "Unknown"
            verdict_counts[decision] = verdict_counts.get(decision, 0) + 1

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
                "filter_mode": filter_mode,
                "review_candidates_returned": filter_mode == "review_fallback",
                "verdicts": verdict_counts,
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

    @staticmethod
    def _remove_persistence_metadata(products: List[Dict[str, Any]]) -> None:
        """Keep persistence-only analytics metadata out of the public API."""
        for product in products:
            product.pop("_search_recommendation", None)
            product.pop("_search_confidence", None)
