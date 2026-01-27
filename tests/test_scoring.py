"""
Tests for scoring and analysis modules
"""
import pytest
from analysis.enhanced_scoring import EnhancedOpportunityScorer, ScoreStatus
from analysis.fba_calculator import FBAFeeCalculator, ProductDimensions
from risk.brand_risk import BrandRiskChecker, RiskLevel
from risk.hazmat_detector import HazmatDetector


def test_enhanced_scorer_basic(sample_product):
    """Test basic scoring functionality"""
    scorer = EnhancedOpportunityScorer()
    result = scorer.calculate_score(sample_product)
    
    assert result.total_score >= 0
    assert result.total_score <= 100
    assert result.status in [s for s in ScoreStatus]
    assert result.confidence >= 0
    assert result.confidence <= 1.0


def test_enhanced_scorer_veto():
    """Test veto logic"""
    scorer = EnhancedOpportunityScorer()
    
    # Product with critical brand risk
    risky_product = {
        'title': 'Nike Air Jordan Shoes',
        'brand': 'Nike',
        'price': 100,
        'rating': 4.5,
        'reviews': 1000,
        'bsr': 500
    }
    
    result = scorer.calculate_score(risky_product)
    assert result.is_vetoed == True
    assert result.veto_reason.value != 'none'


def test_fba_fee_calculator():
    """Test FBA fee calculations"""
    calc = FBAFeeCalculator()
    
    # Test with dimensions
    dims = ProductDimensions(length=10, width=8, height=4, weight=1.5)
    fees = calc.calculate_all_fees(price=29.99, dims=dims)
    
    assert fees.referral_fee > 0
    assert fees.fba_fulfillment_fee > 0
    assert fees.total_amazon_fees > 0
    assert fees.size_tier is not None


def test_fba_fee_without_dimensions():
    """Test FBA fee estimation without dimensions"""
    calc = FBAFeeCalculator()
    fees = calc.calculate_all_fees(price=29.99)
    
    assert fees.referral_fee > 0
    assert fees.fba_fulfillment_fee > 0
    assert len(fees.notes) > 0  # Should have warning about estimated dimensions


def test_brand_risk_checker_safe():
    """Test brand risk checker with safe brand"""
    checker = BrandRiskChecker()
    result = checker.check_brand("GenericBrand", "Generic Product Title")
    
    assert result.risk_level == RiskLevel.SAFE
    assert result.is_veto == False


def test_brand_risk_checker_critical():
    """Test brand risk checker with critical brand"""
    checker = BrandRiskChecker()
    result = checker.check_brand("Nike", "Nike Air Jordan Shoes")
    
    assert result.risk_level == RiskLevel.CRITICAL
    assert result.is_veto == True


def test_hazmat_detector_safe():
    """Test hazmat detector with safe product"""
    detector = HazmatDetector()
    product = {
        'title': 'Yoga Mat Exercise Fitness',
        'description': 'Non-slip yoga mat for home workouts'
    }
    
    result = detector.check_product(product)
    assert result.is_hazmat == False


def test_hazmat_detector_battery():
    """Test hazmat detector with battery product"""
    detector = HazmatDetector()
    product = {
        'title': 'Rechargeable Lithium Battery Pack',
        'description': 'High capacity lithium-ion battery'
    }
    
    result = detector.check_product(product)
    assert result.is_hazmat == True
    assert 'lithium' in [k.lower() for k in result.matched_keywords]


def test_profit_calculation():
    """Test profit margin calculations"""
    calc = FBAFeeCalculator()
    
    profit_data = calc.calculate_profit(
        price=50.00,
        cogs=15.00,
        dims=ProductDimensions(12, 8, 4, 2.0)
    )
    
    assert 'net_profit' in profit_data
    assert 'profit_margin' in profit_data
    assert 'roi' in profit_data
    assert profit_data['net_profit'] > 0  # Should be profitable
