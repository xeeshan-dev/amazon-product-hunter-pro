"""Search pipeline orchestration.

Stages (in order for each candidate):
  1. Provider collection via AmazonHTMLProvider
  2. Validation (asin, title, price present)
  3. Rating pre-filter (cheap, no network cost)
  4. Financials (FBA fees, margin, revenue) — must run before scoring
  5. Opportunity scoring (EnhancedOpportunityScorer)
  6. Risk analysis (brand / hazmat)
  7. Hard major-risk exclude (only when confirmed + filter active)
  8. Seller enrichment (AOD fetch — only when seller filters requested)
  9. Brand-owner & Amazon-dominance detection (inside WinningProductFilter)
 10. Seller-conflict exclude (brand-owns-listing / Amazon confirmed seller)
 11. Qualification via WinningProductFilter (composite score + verdict)
 12. Response assembly, sorting, persistence
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
        seller_enrichment_limit: int = 20,
        seller_enrichment_concurrency: int = 3,
        seller_enrichment_timeout: float = 12.0,
        persistence_service: Optional[Any] = None,
        winning_filter: Optional[WinningProductFilter] = None,
        history_service: Optional[Any] = None,
    ):
        self.scorer = scorer
        self.profitability = profitability
        self.risk_analyzer = risk_analyzer
        self.provider_factory = provider_factory
        self.seller_delay_range = seller_delay_range
        self.seller_enrichment_limit = max(1, seller_enrichment_limit)
        self.seller_enrichment_concurrency = max(1, seller_enrichment_concurrency)
        self.seller_enrichment_timeout = max(1.0, seller_enrichment_timeout)
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
            "Search: '%s' | amazon_seller=%s brand_seller=%s sales=%s-%s margin>=%s",
            request.keyword,
            request.skip_amazon_seller,
            request.skip_brand_seller,
            request.min_sales,
            request.max_sales,
            request.min_margin,
        )

        provider = self.provider_factory(
            base_url=MARKETPLACE_URLS.get(request.marketplace)
        )
        raw_products = await provider.search_products(
            request.keyword,
            pages=request.pages,
        )
        logger.info("Collected %s raw products", len(raw_products))

        candidates: List[Dict[str, Any]] = []

        for product in raw_products:
            candidate = dict(product)

            # Stage 2: validation
            errors = self.winning_filter.validate(candidate)
            if errors:
                logger.debug("Skipping %s (validation: %s)", candidate.get("asin"), errors)
                continue

            # Stage 3: cheap rating pre-filter
            if not self._passes_rating_filter(candidate, request):
                continue

            # Stage 4: financials — MUST run before scoring so profit_margin is set
            self._apply_financials(candidate)

            # Stage 5: opportunity scoring
            self._apply_score(candidate)

            # Stage 6: risk analysis
            risk_result = self._apply_risk(candidate)

            # Stage 7: hard-exclude confirmed major risks
            if self._is_confirmed_major_risk(risk_result, request):
                logger.info("Hard-excluding %s (major risk)", candidate.get("asin"))
                continue

            # Stage 8: seller enrichment (only when needed — network cost)
            candidates.append(candidate)

        # Enrich each candidate with seller info
        for candidate in candidates:
            await self._enrich_seller_info(candidate, request, provider)

        strict_results: List[Dict[str, Any]] = []
        review_results: List[Dict[str, Any]] = []

        for candidate in candidates:

            # Stage 9-10: WinningProductFilter handles brand-owner detection,
            # Amazon dominance, composite scoring, and verdict.
            history = self._observation_history(candidate, request.marketplace, db)
            qualification = self.winning_filter.evaluate(
                candidate,
                request,
                history=history,
            )
            candidate["winning_product"] = qualification

            # Hard-exclude confirmed seller conflicts
            if qualification["confirmed_seller_conflict"]:
                logger.info(
                    "Excluding %s: confirmed seller conflict "
                    "(brand_owner=%s, amazon=%s)",
                    candidate.get("asin"),
                    qualification.get("confirmed_brand_owner"),
                    candidate.get("seller_info", {}).get("amazon_seller"),
                )
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

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    def _passes_rating_filter(self, product: Dict[str, Any], request) -> bool:
        rating = float(product.get("rating") or 0)
        return rating >= request.min_rating

    def _apply_financials(self, product: Dict[str, Any]) -> None:
        """Calculate FBA fees, revenue, profit, and margin.

        Sets both `margin` and `profit_margin` to the same value so that
        EnhancedOpportunityScorer (reads profit_margin) and WinningProductFilter
        (reads margin) always see identical data.
        """
        price = product.get("price") or 0
        sales = product.get("estimated_sales") or 0
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
        # Keep both names in sync so all modules read the same value.
        product["margin"] = result.margin
        product["profit_margin"] = result.margin

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
        if getattr(result, "brand_veto", None) is not None:
            product["risks"]["brand_veto"] = bool(result.brand_veto)
        if getattr(result, "hazmat_veto", None) is not None:
            product["risks"]["hazmat_veto"] = bool(result.hazmat_veto)
        return result

    async def _enrich_seller_info(
        self,
        product: Dict[str, Any],
        request,
        provider,
    ) -> None:
        """Fetch AOD seller data for every product.

        Passes the product brand so SellerAnalyzer can flag brand_is_seller
        at the offer level — catching cases where the brand appears as any
        offer, not just the buy-box.
        """
        asin = product.get("asin")
        if not asin:
            product["seller_info"] = {
                "amazon_seller": False,
                "brand_is_seller": False,
                "total_sellers": None,
                "fba_count": 0,
                "fbm_count": 0,
                "seller_name": None,
                "data_status": "unavailable",
            }
            return

        try:
            brand = (product.get("brand") or "").strip()
            seller_summary = await provider.get_sellers(asin, brand=brand)
            seller_summary["data_status"] = "observed"
            product["seller_info"] = seller_summary

            logger.info(
                "[%s] Sellers: total=%s fba=%s fbm=%s amazon=%s brand_seller=%s buy_box='%s'",
                asin,
                seller_summary.get("total_sellers"),
                seller_summary.get("fba_count", 0),
                seller_summary.get("fbm_count", 0),
                seller_summary.get("amazon_seller", False),
                seller_summary.get("brand_is_seller", False),
                seller_summary.get("seller_name"),
            )

            if self.seller_delay_range != (0, 0):
                await asyncio.sleep(random.uniform(*self.seller_delay_range))
        except Exception as exc:
            logger.warning("Seller fetch failed for %s: %s", asin, exc)
            product["seller_info"] = {
                "amazon_seller": False,
                "brand_is_seller": False,
                "total_sellers": None,
                "seller_name": None,
                "data_status": "unavailable",
            }

    def _observation_history(self, product, marketplace, db):
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
            logger.warning("History lookup failed for %s: %s", asin, exc)
            return None

    @staticmethod
    def _is_confirmed_major_risk(risk_result, request) -> bool:
        if risk_result is None:
            return False
        brand_veto = bool(getattr(risk_result, "brand_veto", False))
        hazmat_veto = bool(getattr(risk_result, "hazmat_veto", False))
        return (request.skip_risky_brands and brand_veto) or (
            request.skip_hazmat and hazmat_veto
        )

    # ------------------------------------------------------------------
    # Response assembly
    # ------------------------------------------------------------------

    def _build_response(
        self,
        processed_results: List[Dict[str, Any]],
        request,
        filter_mode: str = "strict",
    ) -> Dict[str, Any]:
        total_market_revenue = sum(
            p.get("est_revenue", 0) for p in processed_results
        )
        for product in processed_results:
            product["market_share"] = (
                (product.get("est_revenue", 0) / total_market_revenue * 100)
                if total_market_revenue > 0
                else 0
            )

        # Sort: composite score desc, then revenue desc
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
                    if processed_results else 0
                ),
                "avg_sales": (
                    sum(p.get("estimated_sales", 0) for p in processed_results)
                    / len(processed_results)
                    if processed_results else 0
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

    # ------------------------------------------------------------------
    # Analyser helper (used by ProductAnalyzerService)
    # ------------------------------------------------------------------

    async def analyze_product(
        self, product: Dict[str, Any], provider
    ) -> Dict[str, Any]:
        """Apply the deterministic analysis stack to a single product."""
        candidate = dict(product)
        self._apply_financials(candidate)
        self._apply_score(candidate)
        candidate["risks"] = self.risk_analyzer.analyze(candidate).risks
        _dummy_request = type("AnalyzerRequest", (), {
            "skip_amazon_seller": True,
            "skip_brand_seller": True,
        })()
        await self._enrich_seller_info(candidate, _dummy_request, provider)
        return candidate

    @staticmethod
    def _remove_persistence_metadata(products: List[Dict[str, Any]]) -> None:
        for product in products:
            product.pop("_search_recommendation", None)
            product.pop("_search_confidence", None)
