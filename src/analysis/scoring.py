import numpy as np
from typing import Dict
from config.settings import Config

class ProductScorer:
    def __init__(self):
        self.weight_bsr = Config.BSR_WEIGHT
        self.weight_reviews = Config.REVIEWS_WEIGHT
        self.weight_margin = Config.MARGIN_WEIGHT
        
    def calculate_opportunity_score(self, product: Dict) -> float:
        # Ensure we have numeric values, not None
        bsr = product.get('bsr') or 0
        reviews = product.get('reviews') or 0
        price = product.get('price') or 0
        
        bsr_score = self._normalize_bsr(bsr)
        reviews_score = self._normalize_reviews(reviews)
        margin_score = self._calculate_margin_score(price)
        
        return (
            bsr_score * self.weight_bsr +
            reviews_score * self.weight_reviews +
            margin_score * self.weight_margin
        )
    
    def _normalize_bsr(self, bsr: int) -> float:
        if not bsr:
            return 0
        # Lower BSR is better
        return 1 - min(np.log10(bsr) / 6, 1)
    
    def _normalize_reviews(self, reviews: int) -> float:
        if not reviews:
            return 0
        # Prefer products with fewer reviews (less competition)
        return 1 - min(np.log10(reviews + 1) / 4, 1)
    
    def _calculate_margin_score(self, price: float) -> float:
        if not price or price <= 0:
            return 0
        
        # Calculate fees based on config
        referral_fee = price * Config.REFERRAL_FEE_PERCENTAGE
        fba_fee = Config.BASE_FBA_FEE + (price * Config.FBA_PERCENTAGE)
        estimated_cost = price * 0.3  # Assumed COGS is 30% of selling price
        
        margin = price - (referral_fee + fba_fee + estimated_cost)
        margin_percentage = margin / price if price > 0 else 0
        
        return min(max(margin_percentage, 0), 1)