"""Evidence-aware product qualification for FBA sourcing research.

The filter answers one question per candidate:

    "Is this product worth further sourcing and market research?"

Core philosophy (mirrors manual FBA product hunting):
  1. Brand-not-selling:  The product brand should NOT be the active seller.
     If Adidas makes the product, Adidas should not be selling it on Amazon.
  2. Amazon seller policy: when skip_amazon_seller is enabled, any Amazon
     presence in offers is a hard exclude; otherwise Amazon dominance is a
     strong negative signal.
  3. Healthy demand: BSR-derived sales must be high enough to be worth sourcing.
  4. Profitable margin: After FBA fees the margin must support a real business.
  5. Manageable competition: Not price-war territory (>25 FBA sellers).
  6. Low IP / hazmat risk: Confirmed veto-level risks are hard-excluded.

Eight weighted factors (opportunity, demand, profitability, competition, risk,
seller_position, data_confidence, market_trend) are combined into a composite
score.  Weight renormalization is applied over signals that actually have data
so missing data penalises by reducing confidence, not by tanking the score.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    from analytics.trends import TrendDirection, classify_trend
except ImportError:
    from src.analytics.trends import TrendDirection, classify_trend


STRONG_VERDICT = "Strong research candidate"
WORTH_VERDICT = "Worth researching"
VALIDATION_VERDICT = "Needs validation"
DEPRIORITIZE_VERDICT = "Deprioritize"

# Factor weights must sum to 1.0.
FACTOR_WEIGHTS: Dict[str, float] = {
    "opportunity": 0.16,
    "demand": 0.18,
    "profitability": 0.18,
    "competition": 0.12,
    "risk": 0.12,
    "seller_position": 0.09,
    "data_confidence": 0.08,
    "market_trend": 0.07,
}

CORE_FACTORS = ("demand", "profitability", "opportunity")

RISK_FLAG_BRAND = "brand_risk_requires_manual_validation"
RISK_FLAG_HAZMAT = "hazmat_flag_requires_manual_validation"

_CLEAN_BRAND_RISK = {None, "", "SAFE", "safe", "LOW", "low"}
_MEDIUM_BRAND_RISK = {"MEDIUM", "medium", "MODERATE", "moderate"}

# Amazon market dominance threshold.
# If Amazon's estimated revenue share of this search exceeds this value
# AND Amazon is confirmed as a seller, the product is deprioritised.
AMAZON_DOMINANCE_THRESHOLD = 0.40  # 40 % — configurable

# Maximum FBA seller count before we flag price-war territory.
MAX_FBA_SELLERS = 25
# FBA seller sweet spot (3–15 is healthy competition)
MIN_FBA_SELLERS_SWEETSPOT = 3
MAX_FBA_SELLERS_SWEETSPOT = 15

# Minimum reviews on top competitors to consider the niche accessible.
REVIEW_VULNERABILITY_THRESHOLD = 400

# Price sweet-spot for private-label FBA (low enough to impulse-buy,
# high enough to cover fees and leave margin).
PRICE_SWEETSPOT_LOW = 15.0
PRICE_SWEETSPOT_HIGH = 70.0


class WinningProductFilter:
    """Classify FBA product candidates using multi-signal evidence scoring."""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def validate(self, product: Dict[str, Any]) -> List[str]:
        errors = []
        if not product.get("asin"):
            errors.append("missing_asin")
        if not product.get("title"):
            errors.append("missing_title")
        if self._number(product.get("price")) <= 0:
            errors.append("missing_or_invalid_price")
        return errors

    def evaluate(
        self,
        product: Dict[str, Any],
        request,
        history: Optional[Dict[str, List[Optional[float]]]] = None,
    ) -> Dict[str, Any]:
        # ---- Normalise key metrics -----------------------------------------
        score = self._number(product.get("enhanced_score"))
        sales = self._number(product.get("estimated_sales"))
        margin = self._number(product.get("margin"))
        price = self._number(product.get("price"))
        raw_confidence = product.get("_search_confidence")
        confidence = float(raw_confidence) if raw_confidence is not None else 0.5
        seller = product.get("seller_info") or {}
        risks = product.get("risks") or {}
        seller_data_status = (seller.get("data_status") or "unavailable").strip().lower()

        # ---- Brand-owns-listing detection ---------------------------------
        # Primary signal: SellerAnalyzer checked EVERY offer against the brand
        # (bidirectional substring match across the full AOD offer list).
        seller_brand_is_seller = bool(seller.get("brand_is_seller", False))

        # Secondary signal: name-match on buy-box seller vs product brand field
        brand = self._normalize_entity_name(product.get("brand"))
        seller_name = self._normalize_entity_name(seller.get("seller_name"))
        name_match = self._brand_seller_match(brand, seller_name)
        # Title storefront signal ("Visit the Adidas Store", "by Adidas")
        title_lower = (product.get("title") or "").lower()
        brand_storefront_signal = bool(
            brand and (
                f"visit the {brand}" in title_lower
                or f"by {brand}" in title_lower
                or seller_name == brand
            )
        )
        confirmed_brand_owner = seller_brand_is_seller or name_match or brand_storefront_signal

        # ---- Amazon seller detection --------------------------------------
        # "Amazon should not be selling this product."
        # confirmed_amazon_seller = True when Amazon appears in ANY offer
        # (buy-box OR any other offer in the AOD list).
        confirmed_amazon_seller = bool(seller.get("amazon_seller"))

        # amazon_dominant = True when Amazon is confirmed AND has a large share
        # of the search result revenue (used for soft scoring only).
        # For the hard exclude, confirmed_amazon_seller alone is enough
        # when skip_amazon_seller is True.
        product_market_share_pct = self._number(product.get("market_share"))
        amazon_dominant = (
            confirmed_amazon_seller
            and product_market_share_pct >= (AMAZON_DOMINANCE_THRESHOLD * 100)
        )

        # ---- Confirmed conflict (hard exclude) ----------------------------
        # skip_amazon_seller: exclude if Amazon is ANY seller (not just dominant)
        # skip_brand_seller: exclude if brand owns ANY offer
        strict_seller_filter_unverified = bool(
            (request.skip_amazon_seller or request.skip_brand_seller)
            and seller_data_status != "observed"
        )
        confirmed_conflict = (
            (request.skip_amazon_seller and confirmed_amazon_seller)
            or (request.skip_brand_seller and confirmed_brand_owner)
            or strict_seller_filter_unverified
        )

        # ---- Strict match (meets every preference numerically) ------------
        strict_match = (
            sales >= request.min_sales
            and sales <= request.max_sales
            and margin >= request.min_margin
        )

        # ---- Confirmed major risk (IP / hazmat veto) ----------------------
        confirmed_major_risk = (
            (request.skip_risky_brands and self._is_veto_level_brand(risks))
            or (request.skip_hazmat and bool(risks.get("hazmat_veto")))
        )

        # ---- Review flags & strengths (backward-compat flags) -------------
        review_flags: List[str] = []
        strengths: List[str] = []

        if sales >= request.min_sales:
            strengths.append("sales_target_met")
        else:
            review_flags.append("sales_below_preference")
        if sales > request.max_sales:
            review_flags.append("sales_above_preference")
        if margin >= request.min_margin:
            strengths.append("margin_target_met")
        else:
            review_flags.append("margin_below_preference")
        if score >= 60:
            strengths.append("opportunity_score_supports_research")
        else:
            review_flags.append("opportunity_score_requires_validation")
        if confidence >= 0.65:
            strengths.append("reasonable_data_confidence")
        else:
            review_flags.append("limited_data_confidence")
        if risks.get("brand_risk") not in (None, "SAFE", "safe"):
            review_flags.append(RISK_FLAG_BRAND)
        if risks.get("hazmat"):
            review_flags.append(RISK_FLAG_HAZMAT)
        if seller_data_status != "observed":
            review_flags.append("seller_data_unavailable")
            if strict_seller_filter_unverified:
                review_flags.append("seller_data_unverified_for_strict_filters")
        elif (seller.get("total_sellers") or 0) > MAX_FBA_SELLERS:
            review_flags.append("high_seller_count")
        if confirmed_brand_owner:
            review_flags.append("brand_owns_listing")
        if amazon_dominant:
            review_flags.append("amazon_market_dominant")
        if not PRICE_SWEETSPOT_LOW <= price <= PRICE_SWEETSPOT_HIGH:
            review_flags.append("price_outside_sweetspot")

        # ---- Multi-signal factor scores (0-100 each) ----------------------
        factors: Dict[str, Optional[float]] = {
            "opportunity": self._clamp(score),
            "demand": self._demand_score(sales, request),
            "profitability": self._profitability_score(margin, request),
            "competition": self._competition_score(product, seller),
            "risk": self._risk_score(risks, amazon_dominant, confirmed_brand_owner),
            "seller_position": self._seller_position_score(
                seller,
                confirmed_amazon_seller,
                confirmed_brand_owner,
                amazon_dominant,
                request.skip_amazon_seller,
                request.skip_brand_seller,
            ),
            "data_confidence": self._clamp(confidence * 100.0),
            "market_trend": self._trend_score(history),
        }
        composite = self._weighted_composite(factors)

        # ---- Hard veto caps composite ------------------------------------
        scorer_vetoed = bool(product.get("is_vetoed")) or confirmed_major_risk
        # Brand-owns-listing and Amazon-dominance are soft signals in scoring
        # but cap the composite when the matching filter is active.
        soft_conflict = (
            (request.skip_brand_seller and confirmed_brand_owner)
            or (request.skip_amazon_seller and amazon_dominant)
        )
        if scorer_vetoed or soft_conflict:
            composite = min(composite, 25.0)

        # ---- Graded verdict ----------------------------------------------
        available_factors = {k: v for k, v in factors.items() if v is not None}
        supporting = sum(1 for value in available_factors.values() if value >= 70)
        weak_core = any(
            available_factors.get(name) is not None
            and available_factors[name] < 40
            for name in CORE_FACTORS
        )
        open_risk_flags = (
            RISK_FLAG_BRAND in review_flags or RISK_FLAG_HAZMAT in review_flags
        )
        low_confidence = available_factors.get("data_confidence", 50) < 45

        if scorer_vetoed or soft_conflict:
            verdict = DEPRIORITIZE_VERDICT
        elif (
            composite >= 65
            and supporting >= 4
            and not weak_core
            and not open_risk_flags
            and not low_confidence
        ):
            verdict = STRONG_VERDICT
        elif composite >= 50 and supporting >= 3 and not weak_core:
            verdict = WORTH_VERDICT
        elif composite >= 35:
            verdict = VALIDATION_VERDICT
        else:
            verdict = DEPRIORITIZE_VERDICT

        verdict_reasons = self._verdict_reasons(
            verdict=verdict,
            composite=composite,
            supporting=supporting,
            available_count=len(available_factors),
            weak_core=weak_core,
            open_risk_flags=open_risk_flags,
            low_confidence=low_confidence,
            scorer_vetoed=scorer_vetoed,
            amazon_dominant=amazon_dominant,
            confirmed_brand_owner=confirmed_brand_owner,
        )
        if verdict == STRONG_VERDICT and strengths:
            verdict_reasons = strengths + verdict_reasons

        trend_label, trend_detail = self._trend_labels(history)

        return {
            "decision": verdict,
            "verdict": verdict,
            "strict_match": strict_match,
            "confirmed_seller_conflict": confirmed_conflict,
            "strict_seller_filter_unverified": strict_seller_filter_unverified,
            "confirmed_major_risk": confirmed_major_risk,
            "confirmed_brand_owner": confirmed_brand_owner,
            "amazon_dominant": amazon_dominant,
            "review_flags": review_flags,
            "strengths": strengths,
            "factors": {
                name: {
                    "score": None if value is None else round(value, 1),
                    "weight": FACTOR_WEIGHTS[name],
                    "available": value is not None,
                }
                for name, value in factors.items()
            },
            "supporting_signals": supporting,
            "verdict_reasons": verdict_reasons,
            "trend": trend_label,
            "trend_detail": trend_detail,
            "confidence": round(confidence, 2),
            "composite_score": round(composite, 1),
        }

    # ------------------------------------------------------------------
    # Factor scorers
    # ------------------------------------------------------------------

    def _demand_score(self, sales: float, request) -> float:
        """Score monthly sales against the requested preference band."""
        if sales <= 0:
            return 0.0
        min_sales = float(request.min_sales)
        max_sales = float(request.max_sales)
        if sales > max_sales:
            return 82.0
        if sales >= min_sales:
            span = max_sales - min_sales
            position = (sales - min_sales) / span if span > 0 else 1.0
            return 70.0 + 25.0 * self._clamp(position)
        if min_sales <= 0:
            return 70.0
        return max(5.0, 55.0 * (sales / min_sales))

    def _profitability_score(self, margin: float, request) -> float:
        """Score margin against the requested minimum with a 15-point runway."""
        floor = float(request.min_margin)
        gap = floor - margin
        if gap <= -15:
            return 100.0
        if gap <= 0:
            return 65.0 + 35.0 * ((margin - floor) / 15.0)
        if gap <= 10:
            return max(5.0, 65.0 - 35.0 * (gap / 10.0))
        if margin < 10:
            return 10.0
        return max(5.0, 30.0 * (margin / max(floor, 1.0)))

    def _competition_score(
        self, product: Dict[str, Any], seller: Dict[str, Any]
    ) -> float:
        """Prefer the scorer competition pillar; fall back to review moat + seller count."""
        breakdown = product.get("score_breakdown") or {}
        pillar = breakdown.get("competition")
        if pillar is not None:
            base = self._clamp(float(pillar))
        else:
            base = self._review_competition(product)

        # Adjust for total seller count
        count = seller.get("total_sellers")
        if isinstance(count, (int, float)):
            if count > MAX_FBA_SELLERS:
                base -= 20.0  # Price-war territory
            elif count > MAX_FBA_SELLERS_SWEETSPOT:
                base -= 8.0
            elif count < MIN_FBA_SELLERS_SWEETSPOT and count > 0:
                base -= 5.0  # Suspiciously low — may be ungated niche with little demand

        return self._clamp(base)

    @staticmethod
    def _review_competition(product: Dict[str, Any]) -> float:
        reviews = product.get("reviews") or 0
        try:
            reviews = float(reviews)
        except (TypeError, ValueError):
            reviews = 0.0
        if reviews <= 100:
            return 90.0
        if reviews <= 400:
            return 72.0
        if reviews <= 1000:
            return 52.0
        return 32.0

    def _risk_score(
        self,
        risks: Dict[str, Any],
        amazon_dominant: bool,
        confirmed_brand_owner: bool,
    ) -> float:
        """Combine IP/hazmat risk with seller structure risk."""
        brand_risk = risks.get("brand_risk")
        hazmat = bool(risks.get("hazmat"))

        if hazmat:
            return 20.0
        if brand_risk not in _CLEAN_BRAND_RISK:
            base = 25.0 if brand_risk not in _MEDIUM_BRAND_RISK else 55.0
        else:
            base = 100.0

        # Seller structure risk
        if amazon_dominant:
            base -= 30.0
        if confirmed_brand_owner:
            base -= 25.0

        return self._clamp(base)

    def _seller_position_score(
        self,
        seller: Dict[str, Any],
        confirmed_amazon: bool,
        confirmed_brand_owner: bool,
        amazon_dominant: bool,
        skip_amazon: bool,
        skip_brand: bool,
    ) -> Optional[float]:
        """Score the seller landscape. None when not observed."""
        if seller.get("data_status") != "observed":
            return None

        count = seller.get("total_sellers")
        if isinstance(count, (int, float)) and count > 0:
            if MIN_FBA_SELLERS_SWEETSPOT <= count <= MAX_FBA_SELLERS_SWEETSPOT:
                base = 95.0   # Sweet spot
            elif count <= MAX_FBA_SELLERS:
                base = 75.0   # Manageable
            else:
                base = 45.0   # Price-war risk
        else:
            base = 65.0

        # Brand-owns-listing: heavy penalty
        if confirmed_brand_owner:
            base *= 0.2 if skip_brand else 0.4

        # Amazon dominance: heavy penalty (separate from brand-owner)
        if amazon_dominant:
            base *= 0.2 if skip_amazon else 0.35
        elif confirmed_amazon:
            # Amazon present but not dominant — softer penalty
            base *= 0.55 if skip_amazon else 0.70

        return self._clamp(base)

    def _trend_score(
        self, history: Optional[Dict[str, List[Optional[float]]]]
    ) -> Optional[float]:
        """Aggregate historical direction; None when no series qualifies."""
        directions = self._trend_directions(history)
        scored = [
            {"Improving": 90.0, "Stable": 75.0, "Declining": 25.0}.get(direction.value)
            for direction in directions.values()
        ]
        scored = [value for value in scored if value is not None]
        if not scored:
            return None
        return sum(scored) / len(scored)

    def _trend_directions(
        self, history: Optional[Dict[str, List[Optional[float]]]]
    ) -> Dict[str, "TrendDirection"]:
        if not history:
            return {}
        directions: Dict[str, TrendDirection] = {}
        price = history.get("price")
        if price:
            directions["price"] = classify_trend(price)
        bsr = history.get("bsr")
        if bsr:
            directions["bsr"] = classify_trend(bsr, lower_is_better=True)
        reviews = history.get("reviews")
        if reviews:
            directions["reviews"] = classify_trend(reviews)
        return directions

    def _trend_labels(
        self, history: Optional[Dict[str, List[Optional[float]]]]
    ) -> tuple:
        directions = self._trend_directions(history)
        detail = {name: direction.value for name, direction in directions.items()}
        if not detail:
            return "Insufficient Data", detail
        improving = sum(1 for value in detail.values() if value == "Improving")
        declining = sum(1 for value in detail.values() if value == "Declining")
        if declining and declining >= improving:
            label = "Declining"
        elif improving:
            label = "Improving" if improving > len(detail) / 2 else "Stable"
        else:
            label = "Stable"
        return label, detail

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _weighted_composite(factors: Dict[str, Optional[float]]) -> float:
        """Renormalize weights over available signals instead of penalising gaps."""
        total_weight = sum(
            FACTOR_WEIGHTS[name]
            for name, value in factors.items()
            if value is not None
        )
        if total_weight <= 0:
            return 0.0
        weighted = sum(
            FACTOR_WEIGHTS[name] * float(value)
            for name, value in factors.items()
            if value is not None
        )
        return weighted / total_weight

    @staticmethod
    def _verdict_reasons(
        *,
        verdict: str,
        composite: float,
        supporting: int,
        available_count: int,
        weak_core: bool,
        open_risk_flags: bool,
        low_confidence: bool,
        scorer_vetoed: bool,
        amazon_dominant: bool,
        confirmed_brand_owner: bool,
    ) -> List[str]:
        reasons: List[str] = []
        if scorer_vetoed:
            reasons.append("confirmed_veto_condition")
        if amazon_dominant:
            reasons.append("amazon_has_market_dominance")
        if confirmed_brand_owner:
            reasons.append("brand_owns_listing")
        if open_risk_flags:
            reasons.append("unresolved_risk_flags_require_review")
        if low_confidence:
            reasons.append("limited_data_confidence")
        if verdict == STRONG_VERDICT:
            reasons.append(
                f"{supporting}_of_{available_count}_signals_support_research"
            )
        elif verdict == WORTH_VERDICT:
            reasons.append(f"composite_{round(composite)}_with_partial_support")
        elif verdict == VALIDATION_VERDICT:
            reasons.append("mixed_evidence_needs_validation")
        elif weak_core:
            reasons.append("weak_core_signal_requires_review")
        else:
            reasons.append("insufficient_broad_support")
        return reasons

    @staticmethod
    def _is_veto_level_brand(risks: Dict[str, Any]) -> bool:
        return bool(risks.get("brand_veto"))

    @staticmethod
    def _clamp(value, low: float = 0.0, high: float = 100.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return low
        return max(low, min(high, number))

    @staticmethod
    def _number(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize_entity_name(value: Any) -> str:
        text = (str(value or "")).strip().lower()
        text = "".join(ch if (ch.isalnum() or ch.isspace() or ch in {"&", "-", "."}) else " " for ch in text)
        text = re.sub(
            r"\b(official|store|shop|direct|llc|inc|corp|ltd|co|company|usa|us)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        return " ".join(text.split())

    @classmethod
    def _brand_seller_match(cls, brand: str, seller_name: str) -> bool:
        brand = cls._normalize_entity_name(brand)
        seller_name = cls._normalize_entity_name(seller_name)
        if not brand or not seller_name:
            return False
        if len(brand) < 3:
            return False
        if brand == seller_name:
            return True
        if len(brand) <= 4 and len(seller_name) > len(brand):
            return f" {brand} " in f" {seller_name} "
        return brand in seller_name or seller_name in brand
