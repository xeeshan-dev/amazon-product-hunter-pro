import math
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MarketMetrics:
    estimated_sales: int = 0
    estimated_revenue: float = 0
    profit_margin: float = 0
    listing_quality: int = 0
    competition_score: float = 0
    seasonality: List[str] = None
    opportunity_score: float = 0
    
    def __post_init__(self):
        if self.seasonality is None:
            self.seasonality = []

class MarketAnalyzer:
    # BSR to Monthly Sales Estimates (rough approximations)
    BSR_SALES_MAP = {
        1000: 1500,    # Top 1000 BSR ≈ 1500 sales/month
        5000: 500,     # Top 5000 BSR ≈ 500 sales/month
        10000: 300,    # Top 10000 BSR ≈ 300 sales/month
        50000: 100,    # Top 50000 BSR ≈ 100 sales/month
        100000: 50,    # Top 100000 BSR ≈ 50 sales/month
        500000: 10     # Top 500000 BSR ≈ 10 sales/month
    }
    
    def analyze_market(self, product: Dict) -> MarketMetrics:
        metrics = MarketMetrics()
        
        try:
            # Estimate monthly sales
            if product.get('bsr'):
                metrics.estimated_sales = self._estimate_monthly_sales(product['bsr'])
                metrics.estimated_revenue = metrics.estimated_sales * product.get('price', 0)
            
            # Calculate profit margin
            metrics.profit_margin = self._calculate_profit_margin(product)
            
            # Evaluate listing quality
            metrics.listing_quality = self._evaluate_listing_quality(product)
            
            # Analyze competition
            metrics.competition_score = self._analyze_competition(product)
            
            # Check seasonality
            metrics.seasonality = self._analyze_seasonality(product)
            
            # Calculate overall opportunity score
            metrics.opportunity_score = self._calculate_opportunity_score(metrics)
            
        except Exception as e:
            logger.error(f"Error in market analysis: {str(e)}")
            
        return metrics

    def analyze_product(self, product: Dict) -> Dict:
        """Compatibility helper for UI: return a flat dict with expected keys.
        Expects a product dict with at least 'price' and optionally 'bsr', 'seller_info', etc.
        """
        if not isinstance(product, dict):
            return {}
        metrics = self.analyze_market(product)
        return {
            'estimated_monthly_sales': metrics.estimated_sales,
            'profit_margin': metrics.profit_margin,
            'listing_quality': metrics.listing_quality,
            'competition_score': metrics.competition_score,
            'seasonality': metrics.seasonality,
            'opportunity_score': metrics.opportunity_score
        }

    def get_trend_data(self, asin: str, period: str) -> Dict:
        """Return simple placeholder trend data expected by the UI."""
        try:
            # Placeholder trends; in a real impl, fetch historical data
            return {
                'price_trend': 'Stable',
                'demand_trend': 'Stable',
                'competition_trend': 'Stable',
                'trend_data': None
            }
        except Exception:
            return {
                'price_trend': 'Stable',
                'demand_trend': 'Stable',
                'competition_trend': 'Stable',
                'trend_data': None
            }
    
    def _estimate_monthly_sales(self, bsr: int) -> int:
        # Find the closest BSR bracket
        closest_bsr = min(self.BSR_SALES_MAP.keys(), key=lambda x: abs(x - bsr))
        base_sales = self.BSR_SALES_MAP[closest_bsr]
        
        # Adjust based on difference from bracket
        ratio = closest_bsr / bsr if bsr > 0 else 1
        return int(base_sales * ratio)
    
    def _calculate_profit_margin(self, product: Dict) -> float:
        try:
            price = product.get('price') or 0
            if price <= 0:
                return 0
                
            # Estimate Amazon fees
            fba_fee = self._estimate_fba_fees(price)
            referral_fee = price * 0.15  # 15% referral fee
            
            # Estimate product cost (assumption: 25% of sale price)
            product_cost = price * 0.25
            
            # Calculate margin
            total_cost = fba_fee + referral_fee + product_cost
            margin = ((price - total_cost) / price) * 100
            
            return max(0, round(margin, 2))
            
        except Exception as e:
            logger.error(f"Error calculating profit margin: {str(e)}")
            return 0
    
    def _estimate_fba_fees(self, price: float) -> float:
        # Simplified FBA fee estimation
        if price <= 10:
            return 2.92
        elif price <= 30:
            return 3.70
        else:
            return 4.90 + (price * 0.05)  # Base fee + 5% for items over $30
    
    def _evaluate_listing_quality(self, product: Dict) -> int:
        score = 0
        
        # Title quality (5 points max)
        title = product.get('title', '')
        if title:
            words = len(title.split())
            if 5 <= words <= 10:
                score += 3
            elif words > 10:
                score += 5
        
        # Image quality (3 points max)
        images = product.get('images_count') or 0
        if images >= 7:
            score += 3
        elif images >= 5:
            score += 2
        elif images >= 3:
            score += 1
        
        # Rating quality (2 points max)
        rating = product.get('rating') or 0
        reviews = product.get('reviews') or 0
        if rating >= 4.5 and reviews >= 100:
            score += 2
        elif rating >= 4.0 and reviews >= 50:
            score += 1
        
        return score
    
    def _analyze_competition(self, product: Dict) -> float:
        score = 5.0  # Start with middle score
        
        seller_info = product.get('seller_info', {})
        
        # Analyze number of sellers
        total_sellers = seller_info.get('total_sellers') or 0
        if total_sellers == 0:
            score += 2  # No competition
        elif 1 <= total_sellers <= 5:
            score += 1  # Low competition
        elif total_sellers > 20:
            score -= 2  # High competition
        
        # Check seller types
        if seller_info.get('amazon_seller'):
            score -= 2  # Amazon as competitor is challenging
        
        fba_count = seller_info.get('fba_count') or 0
        if fba_count > 10:
            score -= 1  # Many FBA sellers
        
        # Price competition
        prices = seller_info.get('prices', {})
        # Filter to numeric values only to avoid None comparisons
        fba_prices = [p for p in prices.get('fba', []) if isinstance(p, (int, float))]
        if fba_prices:
            price_range = max(fba_prices) - min(fba_prices)
            avg_price = sum(fba_prices) / len(fba_prices)
            if avg_price and price_range > (avg_price * 0.3):  # >30% price spread
                score -= 1  # High price competition
        
        return max(0, min(10, score))
    
    def _analyze_seasonality(self, product: Dict) -> List[str]:
        # This would normally use historical sales data
        # For now, return placeholder based on category
        category = product.get('category', '').lower()
        
        if any(term in category for term in ['christmas', 'halloween', 'holiday']):
            return ['Q4']
        elif any(term in category for term in ['summer', 'beach', 'pool']):
            return ['Q2', 'Q3']
        elif any(term in category for term in ['winter', 'snow']):
            return ['Q1', 'Q4']
        
        return ['All Year']
    
    def _calculate_opportunity_score(self, metrics: MarketMetrics) -> float:
        # Weight different factors
        weights = {
            'sales': 0.3,
            'margin': 0.25,
            'listing': 0.15,
            'competition': 0.3
        }
        
        # Normalize metrics to 0-10 scale
        sales_score = min(10, metrics.estimated_sales / 100)
        margin_score = min(10, metrics.profit_margin / 10)
        listing_score = metrics.listing_quality
        competition_score = metrics.competition_score
        
        # Calculate weighted score
        score = (
            (sales_score * weights['sales']) +
            (margin_score * weights['margin']) +
            (listing_score * weights['listing']) +
            (competition_score * weights['competition'])
        )
        
        return round(score, 2)