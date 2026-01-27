"""
Accurate FBA Fee Calculator
Uses Amazon's actual fee structure with dimensional weight calculations.
Much more accurate than simple percentage estimates.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SizeTier(Enum):
    SMALL_STANDARD = "Small Standard"
    LARGE_STANDARD = "Large Standard"
    LARGE_BULKY = "Large Bulky"
    EXTRA_LARGE_0_50 = "Extra Large 0-50 lb"
    EXTRA_LARGE_50_70 = "Extra Large 50-70 lb"
    EXTRA_LARGE_70_150 = "Extra Large 70-150 lb"
    EXTRA_LARGE_150_PLUS = "Extra Large 150+ lb"


@dataclass
class ProductDimensions:
    length: float  # inches
    width: float  # inches
    height: float  # inches
    weight: float  # pounds
    
    @property
    def longest_side(self) -> float:
        return max(self.length, self.width, self.height)
    
    @property
    def median_side(self) -> float:
        sides = sorted([self.length, self.width, self.height])
        return sides[1]
    
    @property
    def shortest_side(self) -> float:
        return min(self.length, self.width, self.height)
    
    @property
    def dimensional_weight(self) -> float:
        """Calculate dimensional weight using Amazon's formula."""
        return (self.length * self.width * self.height) / 139
    
    @property
    def billable_weight(self) -> float:
        """Billable weight is greater of actual or dimensional weight."""
        return max(self.weight, self.dimensional_weight)
    
    @property
    def girth(self) -> float:
        """Girth = (shortest + median) * 2"""
        return (self.shortest_side + self.median_side) * 2
    
    @property
    def length_plus_girth(self) -> float:
        """Length + Girth (for size tier determination)"""
        return self.longest_side + self.girth


@dataclass
class FeeBreakdown:
    referral_fee: float
    referral_fee_percentage: float
    fba_fulfillment_fee: float
    monthly_storage_fee: float  # Estimated per unit
    total_amazon_fees: float
    size_tier: str
    billable_weight: float
    notes: List[str] = field(default_factory=list)


class FBAFeeCalculator:
    """
    Accurate FBA fee calculator using Amazon's actual fee structure.
    Updated for 2024 FBA fee rates.
    
    Key components:
    1. Size tier classification (determines base fee)
    2. Dimensional weight calculation
    3. Category-specific referral fees
    4. Monthly storage estimates
    """
    
    # Referral fee percentages by category (2024 rates)
    # Most categories are 15%, but many have exceptions
    REFERRAL_FEES = {
        # Standard 15% categories
        'default': 0.15,
        'home & garden': 0.15,
        'sports & outdoors': 0.15,
        'toys & games': 0.15,
        'office products': 0.15,
        'pet supplies': 0.15,
        'health & personal care': 0.15,
        'beauty': 0.15,
        'baby products': 0.15,
        'kitchen': 0.15,
        
        # Lower referral fee categories
        'electronics': 0.08,
        'computers': 0.08,
        'consumer electronics': 0.08,
        'camera': 0.08,
        'cell phones': 0.08,
        'video games': 0.15,  # 15% for games, 8% for consoles
        'video game consoles': 0.08,
        
        # Higher referral fee categories
        'jewelry': 0.20,  # 20% for items >$250, 5% for items ≤$250
        'watches': 0.16,
        'clothing': 0.17,
        'shoes': 0.15,
        'handbags': 0.15,
        'luggage': 0.15,
        
        # Tiered categories
        'furniture': 0.15,  # 15% for items >$200, otherwise varies
        'appliances': 0.15,  # 15% for items >$300, 8% below
        
        # Special categories
        'grocery': 0.15,  # 8% for items ≤$15
        'amazon device accessories': 0.45,  # Highest rate!
        'gift cards': 0.20,
    }
    
    # Minimum referral fees by category
    MIN_REFERRAL_FEES = {
        'default': 0.30,
        'jewelry': 2.00,
        'watches': 2.00,
        'clothing': 0.30,
        'shoes': 0.30,
    }
    
    # FBA Fulfillment fees by size tier (2024 rates - US marketplace)
    # Format: (weight_threshold_oz, base_fee)
    SMALL_STANDARD_FEES = [
        (2, 3.06),    # 0-2 oz
        (4, 3.15),    # 2-4 oz
        (6, 3.24),    # 4-6 oz
        (8, 3.33),    # 6-8 oz
        (10, 3.43),   # 8-10 oz
        (12, 3.53),   # 10-12 oz
        (14, 3.60),   # 12-14 oz
        (16, 3.65),   # 14-16 oz (1 lb)
    ]
    
    LARGE_STANDARD_FEES = [
        (4, 3.68),     # 0-4 oz
        (8, 3.90),     # 4-8 oz
        (12, 4.15),    # 8-12 oz
        (16, 4.55),    # 12-16 oz (1 lb)
        (24, 5.07),    # 1-1.5 lb
        (32, 5.41),    # 1.5-2 lb
        (48, 5.77),    # 2-3 lb
        (float('inf'), 5.77),  # 3+ lb: base + per-lb rate
    ]
    
    # Per-pound rate for large standard over 3 lb
    LARGE_STANDARD_PER_LB = 0.16
    
    # Large Bulky fees (replaced Oversize tiers)
    LARGE_BULKY_BASE = 9.61
    LARGE_BULKY_PER_LB = 0.38  # Per lb after first lb
    
    # Extra Large fees
    EXTRA_LARGE_FEES = {
        '0-50': (26.33, 0.38),    # Base + per lb
        '50-70': (40.12, 0.75),
        '70-150': (54.85, 0.75),
        '150+': (194.95, 0.19),
    }
    
    # Monthly storage fees (per cubic foot)
    STORAGE_FEES = {
        'standard': {
            'jan-sep': 0.78,
            'oct-dec': 2.40,  # Peak season
        },
        'oversize': {
            'jan-sep': 0.56,
            'oct-dec': 1.40,
        }
    }
    
    def __init__(self):
        logger.info("FBAFeeCalculator initialized with 2024 fee rates")
    
    def classify_size_tier(self, dims: ProductDimensions) -> SizeTier:
        """
        Classify product into Amazon's size tiers.
        
        Size tier criteria (2024):
        - Small Standard: ≤15" x 12" x 0.75", ≤16 oz
        - Large Standard: ≤18" x 14" x 8", ≤20 lb
        - Large Bulky: ≤59" longest, ≤30" median, ≤33" shortest, ≤50 lb
        - Extra Large: Everything else
        """
        l, w, h = dims.longest_side, dims.median_side, dims.shortest_side
        weight = dims.weight
        
        # Small Standard
        if (l <= 15 and w <= 12 and h <= 0.75 and weight <= 1):  # ≤16 oz = 1 lb
            return SizeTier.SMALL_STANDARD
        
        # Large Standard
        if (l <= 18 and w <= 14 and h <= 8 and weight <= 20):
            return SizeTier.LARGE_STANDARD
        
        # Large Bulky
        if (l <= 59 and w <= 33 and h <= 33 and weight <= 50):
            return SizeTier.LARGE_BULKY
        
        # Extra Large tiers
        if weight <= 50:
            return SizeTier.EXTRA_LARGE_0_50
        elif weight <= 70:
            return SizeTier.EXTRA_LARGE_50_70
        elif weight <= 150:
            return SizeTier.EXTRA_LARGE_70_150
        else:
            return SizeTier.EXTRA_LARGE_150_PLUS
    
    def get_referral_fee(self, price: float, category: str = None) -> Tuple[float, float]:
        """
        Calculate referral fee based on price and category.
        
        Args:
            price: Selling price
            category: Product category (optional)
            
        Returns:
            Tuple of (fee_amount, fee_percentage)
        """
        if not price or price <= 0:
            return (0, 0)
        
        # Normalize category
        cat_lower = (category or 'default').lower()
        
        # Find matching category
        percentage = self.REFERRAL_FEES.get('default', 0.15)
        for cat_key, rate in self.REFERRAL_FEES.items():
            if cat_key in cat_lower:
                percentage = rate
                break
        
        # Calculate fee
        fee = price * percentage
        
        # Apply minimum fee
        min_fee = self.MIN_REFERRAL_FEES.get('default', 0.30)
        for cat_key, min_rate in self.MIN_REFERRAL_FEES.items():
            if cat_key in cat_lower:
                min_fee = min_rate
                break
        
        fee = max(fee, min_fee)
        
        return (round(fee, 2), percentage)
    
    def get_fba_fee(self, dims: ProductDimensions) -> Tuple[float, SizeTier]:
        """
        Calculate FBA fulfillment fee based on dimensions and weight.
        
        Args:
            dims: ProductDimensions object
            
        Returns:
            Tuple of (fee_amount, size_tier)
        """
        size_tier = self.classify_size_tier(dims)
        billable_weight = dims.billable_weight
        weight_oz = billable_weight * 16  # Convert to ounces for lookup
        
        if size_tier == SizeTier.SMALL_STANDARD:
            # Find fee based on weight bracket
            for threshold, fee in self.SMALL_STANDARD_FEES:
                if weight_oz <= threshold:
                    return (fee, size_tier)
            return (self.SMALL_STANDARD_FEES[-1][1], size_tier)
        
        elif size_tier == SizeTier.LARGE_STANDARD:
            if weight_oz <= 48:  # Up to 3 lb
                for threshold, fee in self.LARGE_STANDARD_FEES:
                    if weight_oz <= threshold:
                        return (fee, size_tier)
            
            # Over 3 lb: base + per-lb rate
            base_fee = 5.77
            extra_weight = max(0, billable_weight - 3)  # Weight over 3 lb
            fee = base_fee + (extra_weight * self.LARGE_STANDARD_PER_LB)
            return (round(fee, 2), size_tier)
        
        elif size_tier == SizeTier.LARGE_BULKY:
            # Base fee + per-lb rate for weight over 1 lb
            extra_weight = max(0, billable_weight - 1)
            fee = self.LARGE_BULKY_BASE + (extra_weight * self.LARGE_BULKY_PER_LB)
            return (round(fee, 2), size_tier)
        
        else:
            # Extra Large tiers
            if size_tier == SizeTier.EXTRA_LARGE_0_50:
                base, per_lb = self.EXTRA_LARGE_FEES['0-50']
            elif size_tier == SizeTier.EXTRA_LARGE_50_70:
                base, per_lb = self.EXTRA_LARGE_FEES['50-70']
            elif size_tier == SizeTier.EXTRA_LARGE_70_150:
                base, per_lb = self.EXTRA_LARGE_FEES['70-150']
            else:
                base, per_lb = self.EXTRA_LARGE_FEES['150+']
            
            fee = base + (billable_weight * per_lb)
            return (round(fee, 2), size_tier)
    
    def estimate_storage_fee(self, dims: ProductDimensions, 
                            is_peak_season: bool = False) -> float:
        """
        Estimate monthly storage fee per unit.
        
        Args:
            dims: Product dimensions
            is_peak_season: True for Oct-Dec (higher rates)
            
        Returns:
            Monthly storage fee per unit
        """
        # Calculate cubic feet
        cubic_feet = (dims.length * dims.width * dims.height) / 1728
        
        # Determine if oversize
        size_tier = self.classify_size_tier(dims)
        is_oversize = size_tier not in [SizeTier.SMALL_STANDARD, SizeTier.LARGE_STANDARD]
        
        # Get rate
        tier_key = 'oversize' if is_oversize else 'standard'
        season_key = 'oct-dec' if is_peak_season else 'jan-sep'
        rate = self.STORAGE_FEES[tier_key][season_key]
        
        return round(cubic_feet * rate, 2)
    
    def calculate_all_fees(self, price: float, dims: ProductDimensions = None,
                          category: str = None, 
                          is_peak_season: bool = False) -> FeeBreakdown:
        """
        Calculate complete fee breakdown for a product.
        
        Args:
            price: Selling price
            dims: Product dimensions (optional - will use estimates if not provided)
            category: Product category
            is_peak_season: True for Oct-Dec
            
        Returns:
            FeeBreakdown with all fee details
        """
        notes = []
        
        # If no dimensions provided, estimate based on price
        if dims is None:
            dims = self._estimate_dimensions(price)
            notes.append("⚠️ Dimensions estimated - actual fees may vary")
        
        # Calculate each fee
        referral_fee, referral_pct = self.get_referral_fee(price, category)
        fba_fee, size_tier = self.get_fba_fee(dims)
        storage_fee = self.estimate_storage_fee(dims, is_peak_season)
        
        total_fees = referral_fee + fba_fee + storage_fee
        
        # Add relevant notes
        if size_tier in [SizeTier.LARGE_BULKY, SizeTier.EXTRA_LARGE_0_50]:
            notes.append("📦 Oversize item - higher fees and shipping restrictions")
        
        if referral_pct > 0.15:
            notes.append(f"⚠️ Category has {referral_pct*100:.0f}% referral fee (above standard 15%)")
        
        if is_peak_season:
            notes.append("📅 Peak season storage fees applied (Oct-Dec)")
        
        return FeeBreakdown(
            referral_fee=referral_fee,
            referral_fee_percentage=referral_pct,
            fba_fulfillment_fee=fba_fee,
            monthly_storage_fee=storage_fee,
            total_amazon_fees=round(total_fees, 2),
            size_tier=size_tier.value,
            billable_weight=round(dims.billable_weight, 2),
            notes=notes
        )
    
    def _estimate_dimensions(self, price: float) -> ProductDimensions:
        """
        Estimate dimensions based on price point.
        Used when actual dimensions are not available.
        
        This is a rough estimate - actual dimensions should be used when possible.
        """
        if price < 15:
            # Small, cheap items
            return ProductDimensions(6, 4, 1, 0.25)  # 4 oz
        elif price < 30:
            # Medium items
            return ProductDimensions(10, 6, 3, 0.75)  # 12 oz
        elif price < 50:
            # Standard items
            return ProductDimensions(12, 8, 4, 1.5)  # 1.5 lb
        elif price < 100:
            # Larger items
            return ProductDimensions(14, 10, 6, 3)  # 3 lb
        else:
            # Big ticket items
            return ProductDimensions(18, 14, 8, 5)  # 5 lb
    
    def calculate_profit(self, price: float, cogs: float, 
                        dims: ProductDimensions = None,
                        category: str = None) -> Dict:
        """
        Calculate net profit and margin.
        
        Args:
            price: Selling price
            cogs: Cost of goods (your cost to buy/make the product)
            dims: Product dimensions
            category: Product category
            
        Returns:
            Dict with profit breakdown
        """
        fees = self.calculate_all_fees(price, dims, category)
        
        net_profit = price - fees.total_amazon_fees - cogs
        margin = (net_profit / price * 100) if price > 0 else 0
        roi = (net_profit / cogs * 100) if cogs > 0 else 0
        
        return {
            'selling_price': price,
            'cogs': cogs,
            'referral_fee': fees.referral_fee,
            'fba_fee': fees.fba_fulfillment_fee,
            'storage_fee': fees.monthly_storage_fee,
            'total_amazon_fees': fees.total_amazon_fees,
            'net_profit': round(net_profit, 2),
            'profit_margin': round(margin, 1),
            'roi': round(roi, 1),
            'size_tier': fees.size_tier,
            'is_profitable': net_profit > 0 and margin >= 20,
            'notes': fees.notes
        }


# Convenience function for quick calculations
def calculate_fba_fees(price: float, length: float = None, width: float = None,
                      height: float = None, weight: float = None,
                      category: str = None) -> Dict:
    """
    Quick FBA fee calculation.
    
    Args:
        price: Selling price
        length, width, height: Dimensions in inches
        weight: Weight in pounds
        category: Product category
        
    Returns:
        Dict with fee breakdown
    """
    calc = FBAFeeCalculator()
    
    if all([length, width, height, weight]):
        dims = ProductDimensions(length, width, height, weight)
    else:
        dims = None
    
    fees = calc.calculate_all_fees(price, dims, category)
    
    return {
        'referral_fee': fees.referral_fee,
        'fba_fee': fees.fba_fulfillment_fee,
        'storage_fee': fees.monthly_storage_fee,
        'total_fees': fees.total_amazon_fees,
        'size_tier': fees.size_tier,
        'notes': fees.notes
    }
