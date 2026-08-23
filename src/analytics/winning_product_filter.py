"""Evidence-aware product qualification for sourcing research.

The filter answers one question per candidate:

    "Is this product worth further sourcing and market research?"

Evaluation is intentionally multi-signal. Eight weighted factors
(opportunity, demand, profitability, competition, risk, seller position,
data confidence, and market trend) are combined into a composite score with
weight renormalization over the signals that actually have data. No single
signal is sufficient to declare a product a winner, and uncertain signals
are treated as unknown rather than as negative evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from analytics.trends import TrendDirection, classify_trend
except ImportError:  # pragma: no cover - direct script-style imports
    from src.analytics.trends import TrendDirection, classify_trend


STRONG_VERDICT = "Strong research candidate"
WORTH_VERDICT = "Worth researching"
VALIDATION_VERDICT = "Needs validation"
DEPRIORITIZE_VERDICT = "Deprioritize"

# Factor weights must sum to 1.0. Factors without data are excluded and the
# remaining weights are renormalized instead of punishing the candidate.
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


class WinningProductFilter:
    """Classify candidates without treating uncertain signals as confirmed facts."""

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
        score = self._number(product.get("enhanced_score"))
        sales = self._number(product.get("estimated_sales"))
        margin = self._number(product.get("margin"))
        raw_confidence = product.get("_search_confidence")
        confidence = float(raw_confidence) if raw_confidence is not None else 0.5
        seller = product.get("seller_info") or {}
        risks = product.get("risks") or {}

        review_flags: List[str] = []
        strengths: List[str] = []

        # ------------------------------------------------------------------
        # Preference flags (kept for backward-compatible API consumers).
        # ------------------------------------------------------------------
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
        if seller.get("data_status") != "observed":
            review_flags.append("seller_data_unavailable")
        elif (seller.get("total_sellers") or 0) > 20:
            review_flags.append("high_seller_count")

        # ------------------------------------------------------------------
        # Confirmed facts (hard gates). Uncertain signals stay as flags;
        # vetoes are acted on only when they are confirmed.
        # ------------------------------------------------------------------
        confirmed_amazon = bool(seller.get("amazon_seller"))
        seller_name = (seller.get("seller_name") or "").strip().lower()
        brand = (product.get("brand") or "").strip().lower()
        confirmed_brand_owner = bool(
            brand and seller_name and (brand in seller_name or seller_name in brand)
        )
        strict_match = (
            sales >= request.min_sales
            and sales <= request.max_sales
            and margin >= request.min_margin
        )
        confirmed_conflict = (
            (request.skip_amazon_seller and confirmed_amazon)
            or (request.skip_brand_seller and confirmed_brand_owner)
        )
        confirmed_major_risk = (
            (request.skip_risky_brands and self._is_veto_level_brand(risks))
            or (request.skip_hazmat and bool(risks.get("hazmat_veto")))
        )

        # ------------------------------------------------------------------
        # Multi-signal factor scores (0-100 each). Missing evidence is
        # marked unavailable instead of being scored as a failure.
        # ------------------------------------------------------------------
        factors: Dict[str, Optional[float]] = {
            "opportunity": self._clamp(score),
            "demand": self._demand_score(sales, request),
            "profitability": self._profitability_score(margin, request),
            "competition": self._competition_score(product, seller),
            "risk": self._risk_score(risks),
            "seller_position": self._seller_position_score(
                seller,
                confirmed_amazon,
                confirmed_brand_owner,
                request.skip_amazon_seller,
                request.skip_brand_seller,
            ),
            "data_confidence": self._clamp(confidence * 100.0),
            "market_trend": self._trend_score(history),
        }
        composite = self._weighted_composite(factors)

        # A confirmed scorer veto (IP risk, hazmat, or unsustainable margin)
        # caps the composite regardless of the remaining evidence.
        scorer_vetoed = bool(product.get("is_vetoed")) or confirmed_major_risk
        if scorer_vetoed:
            composite = min(composite, 25.0)

        # ------------------------------------------------------------------
        # Graded verdict. Broad support is required for the top tier so no
        # single signal can carry a product to "winner".
        # ------------------------------------------------------------------
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

        if scorer_vetoed:
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
        )
        if verdict == STRONG_VERDICT and strengths:
            verdict_reasons = strengths + verdict_reasons

        trend_label, trend_detail = self._trend_labels(history)

        return {
            "decision": verdict,
            "verdict": verdict,
            "strict_match": strict_match,
            "confirmed_seller_conflict": confirmed_conflict,
            "confirmed_major_risk": confirmed_major_risk,
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

    # ----------------------------------------------------------------------
    # Factor scorers
    # ----------------------------------------------------------------------
    def _demand_score(self, sales: float, request) -> float:
        """Score monthly sales against the requested preference band."""
        if sales <= 0:
            return 0.0
        min_sales = float(request.min_sales)
        max_sales = float(request.max_sales)
        if sales > max_sales:
            # Demand is stronger than requested: healthy signal, mild note.
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
        """Prefer the scorer competition pillar; fall back to review moat."""
        breakdown = product.get("score_breakdown") or {}
        pillar = breakdown.get("competition")
        if pillar is not None:
            base = self._clamp(float(pillar))
        else:
            base = self._review_competition(product)
        count = seller.get("total_sellers")
        if isinstance(count, (int, float)):
            if count > 25:
                base -= 15.0
            elif count > 15:
                base -= 7.0
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

    def _risk_score(self, risks: Dict[str, Any]) -> float:
        brand_risk = risks.get("brand_risk")
        hazmat = bool(risks.get("hazmat"))
        if hazmat:
            return 25.0
        if brand_risk in _CLEAN_BRAND_RISK:
            return 100.0
        if brand_risk in _MEDIUM_BRAND_RISK:
            return 60.0
        return 25.0

    def _seller_position_score(
        self,
        seller: Dict[str, Any],
        confirmed_amazon: bool,
        confirmed_brand_owner: bool,
        skip_amazon: bool,
        skip_brand: bool,
    ) -> Optional[float]:
        """Score the competitive seller landscape; None when not observed."""
        if seller.get("data_status") != "observed":
            return None

        count = seller.get("total_sellers")
        if isinstance(count, (int, float)) and count > 0:
            if count <= 15:
                base = 95.0
            elif count <= 25:
                base = 78.0
            else:
                base = 60.0
        else:
            base = 70.0

        if confirmed_amazon or confirmed_brand_owner:
            # Dominant Amazon / brand-owner presence. When the matching skip
            # filter is active the pipeline removes the candidate as a
            # confirmed conflict; otherwise it remains a heavy penalty.
            conflict_requested = (confirmed_amazon and skip_amazon) or (
                confirmed_brand_owner and skip_brand
            )
            base *= 0.2 if conflict_requested else 0.35
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
            # A lower best-seller rank means improving demand.
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

    @staticmethod
    def _weighted_composite(factors: Dict[str, Optional[float]]) -> float:
        """Renormalize weights over available signals instead of penalizing gaps."""
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
    ) -> List[str]:
        reasons: List[str] = []
        if scorer_vetoed:
            reasons.append("confirmed_veto_condition")
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
        """Only an explicit veto-level brand result counts as a confirmed fact."""
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
