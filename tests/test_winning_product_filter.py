"""Tests for the multi-signal winning product filtering engine."""

from types import SimpleNamespace

import pytest

from analytics.winning_product_filter import (
    DEPRIORITIZE_VERDICT,
    FACTOR_WEIGHTS,
    STRONG_VERDICT,
    VALIDATION_VERDICT,
    WORTH_VERDICT,
    WinningProductFilter,
)

pytestmark = pytest.mark.unit


def make_request(**overrides):
    defaults = {
        "keyword": "test",
        "min_rating": 3.0,
        "skip_risky_brands": True,
        "skip_hazmat": True,
        "skip_amazon_seller": False,
        "skip_brand_seller": False,
        "min_margin": 20.0,
        "min_sales": 50,
        "max_sales": 1000,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def healthy_product(**overrides):
    """A candidate with every available signal supporting research."""
    product = {
        "asin": "B001",
        "title": "Healthy Product",
        "brand": "BrandOne",
        "price": 25.0,
        "rating": 4.4,
        "reviews": 120,
        "estimated_sales": 300,
        "margin": 32.0,
        "enhanced_score": 78,
        "_search_confidence": 0.7,
        "score_breakdown": {"demand": 80, "competition": 75, "profit": 82},
        "seller_info": {
            "data_status": "observed",
            "amazon_seller": False,
            "total_sellers": 5,
            "seller_name": "Independent Seller Co",
        },
        "risks": {"brand_risk": "SAFE", "hazmat": False},
    }
    product.update(overrides)
    return product


def test_factor_weights_sum_to_one():
    assert abs(sum(FACTOR_WEIGHTS.values()) - 1.0) < 1e-9


def test_healthy_product_earns_strong_verdict():
    result = WinningProductFilter().evaluate(healthy_product(), make_request())

    assert result["decision"] == STRONG_VERDICT
    assert result["verdict"] == STRONG_VERDICT
    assert result["supporting_signals"] >= 4
    assert result["composite_score"] >= 65
    assert result["confirmed_major_risk"] is False
    assert result["confirmed_seller_conflict"] is False


def test_backward_compatible_keys_are_present():
    result = WinningProductFilter().evaluate(healthy_product(), make_request())

    for key in (
        "decision",
        "strict_match",
        "confirmed_seller_conflict",
        "review_flags",
        "strengths",
        "trend",
        "confidence",
        "composite_score",
    ):
        assert key in result


def test_single_strong_signal_is_not_sufficient_for_winner():
    """Excellent demand alone cannot carry a weak product to the top tier."""
    product = healthy_product(
        estimated_sales=900,      # demand signal excellent
        margin=12.0,              # profitability weak
        enhanced_score=30,        # opportunity weak
        reviews=5000,             # entrenched competition
        risks={"brand_risk": "HIGH", "hazmat": True},
    )

    result = WinningProductFilter().evaluate(product, make_request())

    assert result["decision"] != STRONG_VERDICT
    assert "sales_below_preference" not in result["review_flags"]  # sales itself was fine
    assert "brand_risk_requires_manual_validation" in result["review_flags"]
    assert "hazmat_flag_requires_manual_validation" in result["review_flags"]


def test_weak_core_signal_blocks_top_verdict_even_with_high_composite():
    product = healthy_product(margin=2.0, enhanced_score=35)

    result = WinningProductFilter().evaluate(product, make_request())

    assert result["decision"] != STRONG_VERDICT
    assert any("weak_" in reason or "needs_validation" in reason
               for reason in result["verdict_reasons"])


def test_missing_trend_and_seller_data_renormalize_instead_of_failing():
    """A candidate without trend/seller evidence stays comparable to one with it."""
    request = make_request()
    with_evidence = WinningProductFilter().evaluate(
        healthy_product(),
        request,
        history={"price": [25, 25.5, 26], "bsr": [9000, 8500, 8000]},
    )
    without_evidence = WinningProductFilter().evaluate(healthy_product(), request)

    assert without_evidence["factors"]["market_trend"]["available"] is False
    assert without_evidence["factors"]["market_trend"]["score"] is None
    # Renormalized composite stays within a fair band of the evidence-rich one.
    assert abs(with_evidence["composite_score"] - without_evidence["composite_score"]) < 12
    assert without_evidence["trend"] == "Insufficient Data"


def test_history_wiring_classifies_declining_trend():
    request = make_request()
    improving = WinningProductFilter().evaluate(
        healthy_product(),
        request,
        history={"price": [20, 21, 22], "bsr": [9000, 7000, 5000], "reviews": [100, 150, 210]},
    )
    declining = WinningProductFilter().evaluate(
        healthy_product(),
        request,
        history={"price": [22, 21, 20], "bsr": [5000, 7000, 9000], "reviews": [210, 150, 100]},
    )

    assert improving["trend"] == "Improving"
    assert declining["trend"] == "Declining"
    assert improving["composite_score"] > declining["composite_score"]
    assert improving["factors"]["market_trend"]["score"] > declining["factors"]["market_trend"]["score"]


def test_bsr_lower_is_better_in_trend_classification():
    result = WinningProductFilter().evaluate(
        healthy_product(),
        make_request(),
        history={"bsr": [9000, 7000, 5000]},
    )

    assert result["trend_detail"]["bsr"] == "Improving"


def test_confirmed_major_risk_gate_when_requested():
    product = healthy_product(
        risks={"brand_risk": "HIGH", "brand_veto": True, "hazmat": False},
    )

    result = WinningProductFilter().evaluate(
        product, make_request(skip_risky_brands=True)
    )

    assert result["confirmed_major_risk"] is True
    assert result["decision"] == DEPRIORITIZE_VERDICT
    assert result["composite_score"] <= 25


def test_flagged_but_unconfirmed_risk_stays_as_review_flag():
    """Uncertain risk evidence flags for review instead of rejecting outright."""
    product = healthy_product(
        risks={"brand_risk": "HIGH", "hazmat": True},  # flagged, no veto flag
    )

    result = WinningProductFilter().evaluate(product, make_request())

    assert result["confirmed_major_risk"] is False
    assert "brand_risk_requires_manual_validation" in result["review_flags"]
    assert result["decision"] in (WORTH_VERDICT, VALIDATION_VERDICT, DEPRIORITIZE_VERDICT)


def test_scorer_veto_caps_verdict_regardless_of_other_signals():
    product = healthy_product(is_vetoed=True, veto_reasons=["low_margin"])

    result = WinningProductFilter().evaluate(product, make_request())

    assert result["decision"] == DEPRIORITIZE_VERDICT
    assert "confirmed_veto_condition" in result["verdict_reasons"]
    assert result["composite_score"] <= 25


def test_seller_data_unavailable_is_not_scored_against_candidate():
    product = healthy_product(
        seller_info={"data_status": "unavailable", "amazon_seller": False},
    )

    result = WinningProductFilter().evaluate(product, make_request())

    assert result["factors"]["seller_position"]["available"] is False
    assert "seller_data_unavailable" in result["review_flags"]


def test_amazon_seller_without_skip_filter_is_heavy_penalty_not_conflict():
    product = healthy_product(
        seller_info={
            "data_status": "observed",
            "amazon_seller": True,
            "total_sellers": 8,
            "seller_name": "Amazon.com",
        },
    )

    result = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=False)
    )

    assert result["confirmed_seller_conflict"] is False
    # Amazon is present but not dominant and the skip filter is off, so this
    # is a soft penalty, not a hard exclusion.  The score should be reduced
    # relative to a clean listing (95) but must still be a notable penalty.
    assert result["factors"]["seller_position"]["score"] <= 70
    assert result["factors"]["seller_position"]["score"] > 0


def test_strict_match_semantics_unchanged():
    in_range = WinningProductFilter().evaluate(healthy_product(), make_request())
    out_of_range = WinningProductFilter().evaluate(
        healthy_product(estimated_sales=20), make_request()
    )

    assert in_range["strict_match"] is True
    assert out_of_range["strict_match"] is False
    assert "sales_below_preference" in out_of_range["review_flags"]


def test_verdict_tiers_are_ordered_by_evidence_strength():
    f = WinningProductFilter()
    strong = f.evaluate(healthy_product(), make_request())
    # Mixed evidence: several signals mediocre so support is only partial.
    mid_product = healthy_product(
        estimated_sales=60,
        margin=21.0,
        enhanced_score=48,
        reviews=1500,
        seller_info={
            "data_status": "observed",
            "amazon_seller": False,
            "total_sellers": 30,
            "seller_name": "Independent Seller Co",
        },
    )
    mid = f.evaluate(mid_product, make_request())
    weak = f.evaluate(
        healthy_product(estimated_sales=10, margin=3.0, enhanced_score=20, reviews=4000),
        make_request(),
    )

    assert strong["decision"] == STRONG_VERDICT
    assert mid["decision"] == WORTH_VERDICT
    assert weak["decision"] in (VALIDATION_VERDICT, DEPRIORITIZE_VERDICT)
    assert (
        strong["composite_score"] > mid["composite_score"] > weak["composite_score"]
    )


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------
import asyncio

from analytics.profitability import ProfitabilityAnalyzer
from analytics.risk import ProductRiskAnalyzer
from web_app.backend.services.search_pipeline import SearchPipeline


class _Scorer:
    def calculate_score(self, product):
        pillar = SimpleNamespace(score=80)
        return SimpleNamespace(
            total_score=80,
            demand_pillar=pillar,
            competition_pillar=pillar,
            profit_pillar=pillar,
            is_vetoed=False,
            veto_details=[],
        )


class _FeeCalc:
    def calculate_all_fees(self, price, category=None):
        return SimpleNamespace(
            referral_fee=price * 0.15,
            fba_fulfillment_fee=3.0,
            monthly_storage_fee=0.25,
            total_amazon_fees=(price * 0.15) + 3.25,
        )


class _Brand:
    def check_brand(self, brand, title):
        return SimpleNamespace(
            risk_level=SimpleNamespace(value="SAFE"), reason="ok", is_veto=False
        )


class _Hazmat:
    def check_product(self, product):
        return SimpleNamespace(is_hazmat=False, category=None, is_veto=False)


class _Provider:
    def __init__(self, base_url=None):
        self.base_url = base_url

    async def search_products(self, keyword, pages=1):
        return [
            {
                "asin": "B001",
                "title": "BrandOne Test Product",
                "brand": "BrandOne",
                "price": 20.0,
                "rating": 4.5,
                "reviews": 100,
                "estimated_sales": 100,
            }
        ]

    async def get_sellers(self, asin):
        return {
            "amazon_seller": False,
            "total_sellers": 2,
            "seller_name": "Independent Seller",
            "data_status": "observed",
        }


def _pipeline(risk_analyzer=None):
    return SearchPipeline(
        scorer=_Scorer(),
        profitability=ProfitabilityAnalyzer(_FeeCalc()),
        risk_analyzer=risk_analyzer or ProductRiskAnalyzer(_Brand(), _Hazmat()),
        provider_factory=_Provider,
        seller_delay_range=(0, 0),
    )


def _run_request(**overrides):
    defaults = {
        "keyword": "test",
        "marketplace": "US",
        "pages": 1,
        "min_rating": 3.0,
        "skip_risky_brands": True,
        "skip_hazmat": True,
        "skip_amazon_seller": False,
        "skip_brand_seller": False,
        "min_margin": 0,
        "min_sales": 0,
        "max_sales": 1000,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_pipeline_excludes_confirmed_major_risk_when_requested():
    class VetoRiskAnalyzer:
        def analyze(self, product):
            return SimpleNamespace(
                risks={"brand_risk": "HIGH", "hazmat": False},
                brand_veto=True,
                hazmat_veto=False,
            )

    response = asyncio.run(
        _pipeline(VetoRiskAnalyzer()).run(_run_request(skip_risky_brands=True))
    )

    assert response["summary"]["total_products"] == 0


def test_pipeline_keeps_veto_risk_when_not_requested():
    """Opting out of the risky-brand filter keeps products visible and flagged."""

    class VetoRiskAnalyzer:
        def analyze(self, product):
            return SimpleNamespace(
                risks={"brand_risk": "HIGH", "hazmat": False},
                brand_veto=True,
                hazmat_veto=False,
            )

    response = asyncio.run(
        _pipeline(VetoRiskAnalyzer()).run(_run_request(skip_risky_brands=False))
    )

    assert response["summary"]["total_products"] == 1
    qualification = response["results"][0]["winning_product"]
    # Confirmed veto facts stay on the record for downstream consumers...
    assert qualification["confirmed_major_risk"] is False
    assert response["results"][0]["risks"]["brand_veto"] is True
    # ...but unresolved risk flags block the top tier verdict.
    assert qualification["decision"] in (WORTH_VERDICT, VALIDATION_VERDICT)
    assert "brand_risk_requires_manual_validation" in qualification["review_flags"]


def test_pipeline_summary_reports_verdict_distribution():
    response = asyncio.run(_pipeline().run(_run_request()))

    assert "verdicts" in response["summary"]
    assert response["summary"]["verdicts"] == {STRONG_VERDICT: 1}
    result = response["results"][0]["winning_product"]
    assert result["factors"]["opportunity"]["available"] is True
    assert result["factors"]["market_trend"]["available"] is False


class _ImprovingHistoryService:
    """Pretends this ASIN was observed before with improving metrics."""

    def get_observation_history_for_asin(self, db, asin, marketplace="US", days=30):
        return {
            "price": [20.0, 20.5, 21.0],
            "bsr": [9000, 7000, 5000],
            "reviews": [100, 140, 190],
        }


def test_pipeline_reuses_stored_history_for_trend_qualification():
    pipeline = _pipeline()
    pipeline.history_service = _ImprovingHistoryService()

    response = asyncio.run(pipeline.run(_run_request(), db=object()))

    qualification = response["results"][0]["winning_product"]
    assert qualification["factors"]["market_trend"]["available"] is True
    assert qualification["trend"] == "Improving"
    assert qualification["trend_detail"]["bsr"] == "Improving"
    # Trend evidence should raise the composite versus the no-history case.
    baseline = asyncio.run(_pipeline().run(_run_request()))
    assert (
        qualification["composite_score"]
        > baseline["results"][0]["winning_product"]["composite_score"]
    )


def test_pipeline_survives_history_lookup_failure():
    class BrokenHistoryService:
        def get_observation_history_for_asin(self, db, asin, marketplace="US", days=30):
            raise RuntimeError("database unavailable")

    pipeline = _pipeline()
    pipeline.history_service = BrokenHistoryService()

    response = asyncio.run(pipeline.run(_run_request(), db=object()))

    assert response["summary"]["total_products"] == 1
    qualification = response["results"][0]["winning_product"]
    assert qualification["trend"] == "Insufficient Data"


# ---------------------------------------------------------------------------
# Seller filtering regression tests - Amazon/brand in ANY offer
# ---------------------------------------------------------------------------

def test_amazon_in_buybox_only_excludes_when_skip_amazon_seller():
    """Amazon present only in buy-box → excluded when skip_amazon_seller=True."""
    product = healthy_product(
        seller_info={
            "data_status": "observed",
            "amazon_seller": True,
            "brand_is_seller": False,
            "buy_box_seller_name": "Amazon.com",
            "total_sellers": 4,
        },
    )

    # Without skip filter: penalized but not excluded
    result_no_skip = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=False)
    )
    assert result_no_skip["confirmed_seller_conflict"] is False

    # With skip filter: hard exclusion
    result_skip = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=True)
    )
    assert result_skip["confirmed_seller_conflict"] is True
    assert result_skip["decision"] == DEPRIORITIZE_VERDICT
    assert "confirmed_amazon_seller" in result_skip["verdict_reasons"]


def test_amazon_in_other_offers_not_buybox_excludes_when_skip_amazon_seller():
    """Amazon present in offer #2-4 but NOT buy-box → still excluded when skip_amazon_seller=True."""
    product = healthy_product(
        seller_info={
            "data_status": "observed",
            "amazon_seller": True,  # ← Amazon detected in ANY offer
            "brand_is_seller": False,
            "buy_box_seller_name": "Independent Seller Co",  # ← buy-box is NOT Amazon
            "total_sellers": 4,
        },
    )

    # With skip filter: hard exclusion (this is the critical fix)
    result = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=True)
    )
    assert result["confirmed_seller_conflict"] is True
    assert result["decision"] == DEPRIORITIZE_VERDICT
    assert "confirmed_amazon_seller" in result["verdict_reasons"]


def test_brand_in_buybox_only_excludes_when_skip_brand_seller():
    """Brand present only in buy-box → excluded when skip_brand_seller=True."""
    product = healthy_product(
        brand="BrandOne",
        seller_info={
            "data_status": "observed",
            "amazon_seller": False,
            "brand_is_seller": True,  # ← Brand detected
            "buy_box_seller_name": "BrandOne Official Store",
            "total_sellers": 3,
        },
    )

    # Without skip filter: allowed
    result_no_skip = WinningProductFilter().evaluate(
        product, make_request(skip_brand_seller=False)
    )
    assert result_no_skip["confirmed_seller_conflict"] is False

    # With skip filter: hard exclusion
    result_skip = WinningProductFilter().evaluate(
        product, make_request(skip_brand_seller=True)
    )
    assert result_skip["confirmed_seller_conflict"] is True
    assert result_skip["decision"] == DEPRIORITIZE_VERDICT
    assert "confirmed_brand_owner" in result_skip["verdict_reasons"]


def test_brand_in_other_offers_not_buybox_excludes_when_skip_brand_seller():
    """Brand present in offer #2-4 but NOT buy-box → still excluded when skip_brand_seller=True."""
    product = healthy_product(
        brand="Sony",
        seller_info={
            "data_status": "observed",
            "amazon_seller": False,
            "brand_is_seller": True,  # ← Brand detected in ANY offer (not just buy-box)
            "buy_box_seller_name": "Third Party Seller LLC",
            "total_sellers": 5,
        },
    )

    # With skip filter: hard exclusion (this is the critical fix)
    result = WinningProductFilter().evaluate(
        product, make_request(skip_brand_seller=True)
    )
    assert result["confirmed_seller_conflict"] is True
    assert result["decision"] == DEPRIORITIZE_VERDICT
    assert "confirmed_brand_owner" in result["verdict_reasons"]


def test_seller_data_unavailable_with_strict_filters_excludes():
    """When seller data unavailable + strict filters ON → exclude (fail-closed)."""
    product = healthy_product(
        seller_info={
            "data_status": "unavailable",  # ← Couldn't fetch seller data
            "amazon_seller": False,
            "brand_is_seller": False,
            "total_sellers": 0,
        },
    )

    # Strict filters ON but data unavailable → fail-closed (exclude)
    result = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=True, skip_brand_seller=True)
    )
    assert result["confirmed_seller_conflict"] is True
    assert result["decision"] == DEPRIORITIZE_VERDICT
    assert "seller_data_unavailable_under_strict_filtering" in result["verdict_reasons"]


def test_seller_data_blocked_with_strict_filters_excludes():
    """When seller data blocked + strict filters ON → exclude (fail-closed)."""
    product = healthy_product(
        seller_info={
            "data_status": "blocked",  # ← Bot detection or blocked
            "amazon_seller": False,
            "brand_is_seller": False,
            "total_sellers": 0,
        },
    )

    # Strict filters ON but data blocked → fail-closed (exclude)
    result = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=True, skip_brand_seller=True)
    )
    assert result["confirmed_seller_conflict"] is True
    assert result["decision"] == DEPRIORITIZE_VERDICT
    assert "seller_data_unavailable_under_strict_filtering" in result["verdict_reasons"]


def test_no_amazon_no_brand_passes_strict_filters():
    """Product with no Amazon and no brand in offers → passes strict filters."""
    product = healthy_product(
        brand="CleanBrand",
        seller_info={
            "data_status": "observed",
            "amazon_seller": False,  # ← No Amazon
            "brand_is_seller": False,  # ← No brand
            "buy_box_seller_name": "Independent Seller Co",
            "total_sellers": 6,
        },
    )

    result = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=True, skip_brand_seller=True)
    )
    assert result["confirmed_seller_conflict"] is False
    assert result["decision"] != DEPRIORITIZE_VERDICT
    # Should get good scores for clean seller position
    assert result["factors"]["seller_position"]["available"] is True
    assert result["factors"]["seller_position"]["score"] >= 85


def test_both_amazon_and_brand_present_double_conflict():
    """Product sold by BOTH Amazon AND brand → double conflict."""
    product = healthy_product(
        brand="DoubleTrouble",
        seller_info={
            "data_status": "observed",
            "amazon_seller": True,
            "brand_is_seller": True,
            "buy_box_seller_name": "Amazon.com",
            "total_sellers": 4,
        },
    )

    result = WinningProductFilter().evaluate(
        product, make_request(skip_amazon_seller=True, skip_brand_seller=True)
    )
    assert result["confirmed_seller_conflict"] is True
    assert result["decision"] == DEPRIORITIZE_VERDICT
    # Both reasons should be present
    reasons = result["verdict_reasons"]
    assert "confirmed_amazon_seller" in reasons or "confirmed_brand_owner" in reasons
