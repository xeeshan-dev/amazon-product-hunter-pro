"""
Enhanced Opportunity Scoring System
3-Pillar Model with Veto Logic (Production-Grade)

Pillars:
1. Demand & Trend (40%) - BSR stability, sales velocity, non-seasonal demand
2. Competition (35%) - FBA seller count, review vulnerability, brand dominance
3. Profit & Risk (25% + VETO) - Margins, IP risk, Hazmat status

VETO Logic: Certain conditions auto-reject products regardless of score.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.recommendations import OpportunityRecommendationEngine

logger = logging.getLogger(__name__)


class ScoreStatus(Enum):
    EXCELLENT = "excellent"      # 80-100
    GOOD = "good"                # 60-79
    MARGINAL = "marginal"        # 40-59
    POOR = "poor"                # 20-39
    NOT_VIABLE = "not_viable"    # 0-19 or VETO


class VetoReason(Enum):
    NONE = "none"
    IP_RISK = "ip_risk"
    HAZMAT = "hazmat"
    AMAZON_SELLER = "amazon_as_seller"
    GATED_CATEGORY = "gated_category"
    LOW_MARGIN = "low_margin"
    TOO_COMPETITIVE = "too_competitive"


@dataclass
class PillarScore:
    name: str
    score: float  # 0-100
    weight: float  # Decimal (e.g., 0.40)
    weighted_score: float  # score * weight
    components: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


@dataclass
class OpportunityScore:
    total_score: float  # 0-100
    status: ScoreStatus
    confidence: float  # 0-1.0 (how reliable is this score?)
    
    # Pillar breakdown
    demand_pillar: PillarScore
    competition_pillar: PillarScore
    profit_pillar: PillarScore
    
    # Veto information
    is_vetoed: bool
    veto_reason: VetoReason
    veto_details: str
    
    # Summary
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class EnhancedOpportunityScorer:
    """
    Production-grade opportunity scorer with 3-pillar model.
    
    Features:
    - 3-Pillar weighted scoring (Demand, Competition, Profit)
    - VETO logic for deal-breakers (IP risk, Hazmat, etc.)
    - FBA seller sweet spot detection (3-15 sellers)
    - Review vulnerability analysis
    - Confidence scoring based on data quality
    """
    
    # Pillar weights (must sum to 1.0)
    DEMAND_WEIGHT = 0.40
    COMPETITION_WEIGHT = 0.35
    PROFIT_WEIGHT = 0.25
    
    # FBA seller sweet spot
    MIN_FBA_SELLERS = 3
    MAX_FBA_SELLERS = 15
    
    # Review vulnerability threshold
    VULNERABLE_REVIEW_COUNT = 400
    MIN_VULNERABLE_COMPETITORS = 3
    
    # Margin thresholds
    EXCELLENT_MARGIN = 40
    GOOD_MARGIN = 30
    MIN_MARGIN = 20
    
    # BSR thresholds for scoring
    EXCELLENT_BSR = 5000
    GOOD_BSR = 20000
    OK_BSR = 50000
    MAX_BSR = 100000
    
    def __init__(self):
        self.recommendation_engine = OpportunityRecommendationEngine()

        # Import risk checkers
        try:
            from risk.brand_risk import BrandRiskChecker, RiskLevel
            from risk.hazmat_detector import HazmatDetector
            self.brand_checker = BrandRiskChecker()
            self.hazmat_detector = HazmatDetector()
            self._has_risk_modules = True
        except ImportError:
            logger.warning("Risk modules not available - skipping IP/Hazmat checks")
            self._has_risk_modules = False
        
        logger.info("EnhancedOpportunityScorer initialized")
    
    def calculate_score(self, product: Dict, 
                       historical_data: Dict = None,
                       top_competitors: List[Dict] = None) -> OpportunityScore:
        """
        Calculate comprehensive opportunity score.
        
        Args:
            product: Product data dict
            historical_data: Optional BSR/price history data
            top_competitors: Optional list of top 10 competitor products
            
        Returns:
            OpportunityScore with full breakdown
        """
        # Check for veto conditions first
        is_vetoed, veto_reason, veto_details = self._check_veto_conditions(product)
        
        if is_vetoed:
            # Return zero score with veto information
            return OpportunityScore(
                total_score=0,
                status=ScoreStatus.NOT_VIABLE,
                confidence=1.0,  # We're confident it's bad
                demand_pillar=PillarScore("Demand", 0, self.DEMAND_WEIGHT, 0),
                competition_pillar=PillarScore("Competition", 0, self.COMPETITION_WEIGHT, 0),
                profit_pillar=PillarScore("Profit & Risk", 0, self.PROFIT_WEIGHT, 0),
                is_vetoed=True,
                veto_reason=veto_reason,
                veto_details=veto_details,
                weaknesses=[f"⛔ VETOED: {veto_details}"],
                recommendations=["Do NOT source this product"]
            )
        
        # Calculate each pillar
        demand_pillar = self._calculate_demand_pillar(product, historical_data)
        competition_pillar = self._calculate_competition_pillar(product, top_competitors)
        profit_pillar = self._calculate_profit_pillar(product)
        
        # Calculate total weighted score
        total_score = (
            demand_pillar.weighted_score +
            competition_pillar.weighted_score +
            profit_pillar.weighted_score
        )
        
        # Determine status
        status = self._get_status(total_score)
        
        # Calculate confidence
        confidence = self._calculate_confidence(product, historical_data)
        
        # Generate insights
        strengths, weaknesses, recommendations = self._generate_insights(
            product, demand_pillar, competition_pillar, profit_pillar, total_score
        )
        
        return OpportunityScore(
            total_score=round(total_score, 1),
            status=status,
            confidence=round(confidence, 2),
            demand_pillar=demand_pillar,
            competition_pillar=competition_pillar,
            profit_pillar=profit_pillar,
            is_vetoed=False,
            veto_reason=VetoReason.NONE,
            veto_details="",
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations
        )
    
    def _check_veto_conditions(self, product: Dict) -> Tuple[bool, VetoReason, str]:
        """Check for deal-breaker conditions that auto-reject a product."""
        
        # Check 1: IP Risk (brand blacklist)
        if self._has_risk_modules:
            brand = product.get('brand', '')
            title = product.get('title', '')
            brand_result = self.brand_checker.check_brand(brand, title)
            
            if brand_result.is_veto:
                return (True, VetoReason.IP_RISK, 
                       f"Brand '{brand}' is known for IP claims - high account suspension risk")
        
        # Check 2: Hazmat
        if self._has_risk_modules:
            hazmat_result = self.hazmat_detector.check_product(product)
            if hazmat_result.is_veto:
                return (True, VetoReason.HAZMAT,
                       f"Product contains hazmat indicators: {', '.join(hazmat_result.matched_keywords[:3])}")
        
        # Check 3: Amazon as seller (very hard to compete)
        seller_info = product.get('seller_info', {})
        if seller_info.get('amazon_seller', False):
            # Not an automatic veto, but severe penalty
            # Some sellers still compete with Amazon, so we'll just penalize heavily
            pass  # Handled in competition pillar
        
        # Check 4: Extremely low margin (< 10%)
        # `profit_margin` is set by SearchPipeline._apply_financials which runs
        # before _apply_score, so this value reflects the actual calculated margin.
        # `margin` (alias) is also set — both are always identical.
        margin = product.get('profit_margin') or product.get('margin') or 0
        if margin < 10:
            return (True, VetoReason.LOW_MARGIN,
                   f"Profit margin of {margin:.1f}% is too low for sustainable business")
        
        return (False, VetoReason.NONE, "")
    
    def _calculate_demand_pillar(self, product: Dict, 
                                 historical_data: Dict = None) -> PillarScore:
        """
        Calculate Demand & Trend pillar (40% weight).
        
        Components:
        - BSR Score (40% of pillar)
        - BSR Stability (30% of pillar) - requires historical data
        - Sales Velocity (30% of pillar)
        """
        components = {}
        notes = []
        
        # Component 1: Current BSR Score (40% of pillar)
        bsr = product.get('bsr') or 0
        if bsr > 0:
            if bsr <= self.EXCELLENT_BSR:
                bsr_score = 100
                notes.append(f"✅ Excellent BSR: #{bsr:,}")
            elif bsr <= self.GOOD_BSR:
                bsr_score = 80
                notes.append(f"👍 Good BSR: #{bsr:,}")
            elif bsr <= self.OK_BSR:
                bsr_score = 60
                notes.append(f"⚠️ Average BSR: #{bsr:,}")
            elif bsr <= self.MAX_BSR:
                bsr_score = 40
                notes.append(f"📉 Below average BSR: #{bsr:,}")
            else:
                bsr_score = 20
                notes.append(f"❌ Poor BSR: #{bsr:,}")
        else:
            bsr_score = 0
            notes.append("❌ No BSR data available")
        
        components['bsr_score'] = bsr_score
        
        # Component 2: BSR Stability (30% of pillar)
        if historical_data and 'bsr_variance' in historical_data:
            variance = historical_data['bsr_variance']
            if variance < 0.2:
                stability_score = 100
                notes.append("✅ Very stable BSR (consistent demand)")
            elif variance < 0.4:
                stability_score = 70
                notes.append("👍 Moderately stable BSR")
            elif variance < 0.6:
                stability_score = 40
                notes.append("⚠️ Some BSR volatility (possible seasonality)")
            else:
                stability_score = 20
                notes.append("❌ High BSR volatility (seasonal or declining)")
        else:
            stability_score = 50  # Neutral if no data
            notes.append("📊 No historical data - stability unknown")
        
        components['stability_score'] = stability_score
        
        # Component 3: Sales Velocity (30% of pillar)
        est_sales = product.get('estimated_monthly_sales') or product.get('estimated_sales') or 0
        if est_sales >= 500:
            velocity_score = 100
            notes.append(f"✅ High sales velocity: ~{est_sales}/month")
        elif est_sales >= 300:
            velocity_score = 80
            notes.append(f"👍 Good sales velocity: ~{est_sales}/month")
        elif est_sales >= 100:
            velocity_score = 60
            notes.append(f"⚠️ Moderate sales: ~{est_sales}/month")
        elif est_sales >= 30:
            velocity_score = 40
            notes.append(f"📉 Low sales: ~{est_sales}/month")
        else:
            velocity_score = 20
            notes.append("❌ Very low or unknown sales velocity")
        
        components['velocity_score'] = velocity_score
        
        # Calculate pillar score
        pillar_score = (
            bsr_score * 0.40 +
            stability_score * 0.30 +
            velocity_score * 0.30
        )
        
        return PillarScore(
            name="Demand & Trend",
            score=round(pillar_score, 1),
            weight=self.DEMAND_WEIGHT,
            weighted_score=round(pillar_score * self.DEMAND_WEIGHT, 1),
            components=components,
            notes=notes
        )
    
    def _calculate_competition_pillar(self, product: Dict,
                                      top_competitors: List[Dict] = None) -> PillarScore:
        """
        Calculate Competition pillar (35% weight).
        
        Components:
        - FBA Seller Count (40% of pillar) - Sweet spot: 3-15
        - Review Vulnerability (35% of pillar) - 3+ competitors with <400 reviews
        - Amazon Presence (25% of pillar)
        """
        components = {}
        notes = []
        
        seller_info = product.get('seller_info', {})
        
        # Component 1: FBA Seller Count (40% of pillar)
        fba_count = seller_info.get('fba_count', 0)
        
        if self.MIN_FBA_SELLERS <= fba_count <= self.MAX_FBA_SELLERS:
            # Sweet spot!
            fba_score = 100
            notes.append(f"✅ Ideal FBA seller count: {fba_count} (sweet spot 3-15)")
        elif fba_count < self.MIN_FBA_SELLERS:
            fba_score = 40
            notes.append(f"⚠️ Low FBA sellers ({fba_count}) - may indicate low demand or gating")
        elif fba_count <= 20:
            fba_score = 60
            notes.append(f"⚠️ Slightly high FBA competition: {fba_count} sellers")
        else:
            fba_score = 20
            notes.append(f"❌ Too many FBA sellers: {fba_count} (price war risk)")
        
        components['fba_count_score'] = fba_score
        
        # Component 2: Review Vulnerability (35% of pillar)
        if top_competitors:
            vulnerable_count = sum(
                1 for c in top_competitors[:10] 
                if (c.get('reviews', 0) or 0) < self.VULNERABLE_REVIEW_COUNT
            )
            
            if vulnerable_count >= self.MIN_VULNERABLE_COMPETITORS:
                vulnerability_score = 100
                notes.append(f"✅ {vulnerable_count} weak competitors (<400 reviews) - opportunity!")
            elif vulnerable_count >= 2:
                vulnerability_score = 70
                notes.append(f"👍 {vulnerable_count} competitors with low reviews")
            elif vulnerable_count >= 1:
                vulnerability_score = 50
                notes.append(f"⚠️ Only {vulnerable_count} vulnerable competitor")
            else:
                vulnerability_score = 20
                notes.append("❌ All top competitors have established reviews")
        else:
            # Estimate from product's own reviews
            reviews = product.get('reviews', 0) or 0
            if reviews < 100:
                vulnerability_score = 70
                notes.append("📊 No competitor data - market appears accessible based on reviews")
            elif reviews < 500:
                vulnerability_score = 50
                notes.append("📊 No competitor data - moderate competition estimated")
            else:
                vulnerability_score = 30
                notes.append("📊 No competitor data - appears competitive based on reviews")
        
        components['vulnerability_score'] = vulnerability_score
        
        # Component 3: Amazon Presence (25% of pillar)
        amazon_sells = seller_info.get('amazon_seller', False)
        
        if amazon_sells:
            amazon_score = 0
            notes.append("⚠️ Amazon is a seller - very difficult to compete")
        else:
            amazon_score = 100
            notes.append("✅ Amazon is not a direct seller")
        
        components['amazon_score'] = amazon_score
        
        # Calculate pillar score
        pillar_score = (
            fba_score * 0.40 +
            vulnerability_score * 0.35 +
            amazon_score * 0.25
        )
        
        return PillarScore(
            name="Competition",
            score=round(pillar_score, 1),
            weight=self.COMPETITION_WEIGHT,
            weighted_score=round(pillar_score * self.COMPETITION_WEIGHT, 1),
            components=components,
            notes=notes
        )
    
    def _calculate_profit_pillar(self, product: Dict) -> PillarScore:
        """
        Calculate Profit & Risk pillar (25% weight).
        
        Components:
        - Profit Margin (50% of pillar)
        - Price Point (25% of pillar) - Sweet spot $15-50
        - Risk Factors (25% of pillar)
        """
        components = {}
        notes = []
        
        # Component 1: Profit Margin (50% of pillar)
        margin = product.get('profit_margin', 0) or 0
        
        if margin >= self.EXCELLENT_MARGIN:
            margin_score = 100
            notes.append(f"✅ Excellent margin: {margin}%")
        elif margin >= self.GOOD_MARGIN:
            margin_score = 80
            notes.append(f"👍 Good margin: {margin}%")
        elif margin >= self.MIN_MARGIN:
            margin_score = 60
            notes.append(f"⚠️ Acceptable margin: {margin}%")
        elif margin >= 10:
            margin_score = 30
            notes.append(f"📉 Low margin: {margin}% (barely viable)")
        else:
            margin_score = 0
            notes.append(f"❌ Margin too low: {margin}%")
        
        components['margin_score'] = margin_score
        
        # Component 2: Price Point (25% of pillar)
        price = product.get('price', 0) or 0
        
        if 20 <= price <= 50:
            price_score = 100
            notes.append(f"✅ Ideal price point: ${price}")
        elif 15 <= price < 20 or 50 < price <= 75:
            price_score = 80
            notes.append(f"👍 Good price point: ${price}")
        elif 10 <= price < 15 or 75 < price <= 100:
            price_score = 60
            notes.append(f"⚠️ Moderate price point: ${price}")
        elif price < 10:
            price_score = 30
            notes.append(f"📉 Low price (thin margins after fees): ${price}")
        else:
            price_score = 50
            notes.append(f"⚠️ Higher price point: ${price} (may need more capital)")
        
        components['price_score'] = price_score
        
        # Component 3: Risk Factors (25% of pillar)
        risk_score = 100
        risk_notes = []
        
        # Check IP risk (non-veto level)
        if self._has_risk_modules:
            brand = product.get('brand', '')
            title = product.get('title', '')
            brand_result = self.brand_checker.check_brand(brand, title)
            
            if brand_result.risk_level.value == 'high':
                risk_score -= 40
                risk_notes.append("⚠️ High IP risk brand")
            elif brand_result.risk_level.value == 'medium':
                risk_score -= 20
                risk_notes.append("📋 Moderate IP risk - verify authenticity")
        
        # Check hazmat risk (non-veto level)
        if self._has_risk_modules:
            hazmat_result = self.hazmat_detector.check_product(product)
            if hazmat_result.is_hazmat and not hazmat_result.is_veto:
                risk_score -= 30
                risk_notes.append(f"⚠️ Potential hazmat: {hazmat_result.category.value}")
        
        if risk_notes:
            notes.extend(risk_notes)
        else:
            notes.append("✅ No significant risk factors detected")
        
        components['risk_score'] = max(0, risk_score)
        
        # Calculate pillar score
        pillar_score = (
            margin_score * 0.50 +
            price_score * 0.25 +
            max(0, risk_score) * 0.25
        )
        
        return PillarScore(
            name="Profit & Risk",
            score=round(pillar_score, 1),
            weight=self.PROFIT_WEIGHT,
            weighted_score=round(pillar_score * self.PROFIT_WEIGHT, 1),
            components=components,
            notes=notes
        )
    
    def _get_status(self, score: float) -> ScoreStatus:
        """Convert numeric score to status."""
        if score >= 80:
            return ScoreStatus.EXCELLENT
        elif score >= 60:
            return ScoreStatus.GOOD
        elif score >= 40:
            return ScoreStatus.MARGINAL
        elif score >= 20:
            return ScoreStatus.POOR
        else:
            return ScoreStatus.NOT_VIABLE
    
    def _calculate_confidence(self, product: Dict, 
                             historical_data: Dict = None) -> float:
        """
        Calculate confidence in the score (0-1).
        Based on data quality and availability.
        """
        confidence = 0.5  # Base confidence
        
        # Has BSR data
        if product.get('bsr'):
            confidence += 0.15
        
        # Has price data
        if product.get('price'):
            confidence += 0.10
        
        # Has reviews data
        if product.get('reviews') is not None:
            confidence += 0.10
        
        # Has seller info
        if product.get('seller_info'):
            confidence += 0.10
        
        # Has historical data
        if historical_data:
            confidence += 0.15
        
        # Has profit margin calculated
        if product.get('profit_margin'):
            confidence += 0.10
        
        return min(1.0, confidence)
    
    def _generate_insights(self, product: Dict,
                          demand: PillarScore,
                          competition: PillarScore,
                          profit: PillarScore,
                          total_score: float) -> Tuple[List[str], List[str], List[str]]:
        """Generate actionable insights through the analytics boundary.

        ``product`` remains accepted for compatibility with existing callers.
        """
        result = self.recommendation_engine.generate(
            demand_score=demand.score,
            competition_score=competition.score,
            profit_score=profit.score,
            total_score=total_score,
        )
        return result.strengths, result.weaknesses, result.recommendations

# Convenience function for backward compatibility
def calculate_opportunity_score(product: Dict, 
                                historical_data: Dict = None) -> float:
    """
    Quick opportunity score calculation.
    Returns just the numeric score for backward compatibility.
    """
    scorer = EnhancedOpportunityScorer()
    result = scorer.calculate_score(product, historical_data)
    return result.total_score
