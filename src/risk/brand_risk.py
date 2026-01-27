"""
Free Brand Risk Detection Module
Detects risky brands that commonly file IP claims against sellers.
Data sourced from Reddit, Amazon Seller Forums, and community reports.
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # Auto-veto


@dataclass
class BrandRiskResult:
    brand_name: str
    risk_level: RiskLevel
    reason: str
    is_veto: bool = False  # If True, product should be auto-rejected
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BrandRiskChecker:
    """
    Free brand risk checker using curated blacklist.
    Updated manually from community sources.
    """
    
    # CRITICAL: Brands that WILL sue or file IP claims (instant account suspension risk)
    CRITICAL_BRANDS = {
        # Entertainment/Media Giants
        'disney', 'marvel', 'star wars', 'lucasfilm', 'pixar', 'abc',
        'warner bros', 'dc comics', 'batman', 'superman', 'harry potter',
        'nintendo', 'pokemon', 'pikachu', 'mario', 'zelda', 'game freak',
        'sony', 'playstation', 'xbox', 'microsoft', 'halo',
        'dreamworks', 'universal', 'nbcuniversal', 'paramount',
        'nickelodeon', 'spongebob', 'paw patrol', 'dora',
        'sesame street', 'muppets', 'jim henson',
        
        # Sports Leagues (VERY aggressive)
        'nfl', 'nba', 'mlb', 'nhl', 'mls', 'fifa', 'uefa',
        'super bowl', 'world cup', 'olympics', 'olympic',
        'ncaa', 'college football', 'march madness',
        
        # Sports Teams (all major leagues)
        'patriots', 'cowboys', 'lakers', 'yankees', 'red sox',
        'warriors', 'chiefs', 'eagles', 'packers', 'bears',
        
        # Luxury Brands (very aggressive legal teams)
        'louis vuitton', 'lv', 'gucci', 'prada', 'chanel', 'hermes',
        'rolex', 'cartier', 'tiffany', 'burberry', 'dior', 'fendi',
        'versace', 'armani', 'coach', 'michael kors', 'kate spade',
        'yves saint laurent', 'ysl', 'balenciaga', 'givenchy',
        
        # Tech Giants
        'apple', 'iphone', 'ipad', 'macbook', 'airpods', 'apple watch',
        'samsung', 'galaxy', 'google', 'pixel', 'chromecast',
        'amazon', 'alexa', 'echo', 'kindle', 'fire tv',
        'meta', 'facebook', 'instagram', 'oculus', 'quest',
        
        # Automotive
        'tesla', 'bmw', 'mercedes', 'audi', 'porsche', 'ferrari',
        'lamborghini', 'ford', 'chevrolet', 'toyota', 'honda',
        'jeep', 'harley davidson', 'harley-davidson',
        
        # Fashion/Apparel Giants
        'nike', 'adidas', 'under armour', 'puma', 'new balance',
        'jordan', 'air jordan', 'yeezy', 'supreme', 'off-white',
        'north face', 'patagonia', 'columbia', 'lululemon',
        'levis', "levi's", 'calvin klein', 'tommy hilfiger', 'ralph lauren',
        
        # Toys/Children
        'lego', 'mattel', 'barbie', 'hot wheels', 'fisher price',
        'hasbro', 'transformers', 'my little pony', 'nerf',
        'american girl', 'build a bear', 'build-a-bear',
        'funko', 'funko pop',
        
        # Consumer Electronics
        'bose', 'beats', 'jbl', 'sonos', 'bang & olufsen',
        'dyson', 'roomba', 'irobot', 'vitamix', 'kitchenaid',
        'cuisinart', 'ninja', 'instant pot', 'keurig', 'nespresso',
        
        # Beauty/Cosmetics
        'mac cosmetics', 'sephora', 'ulta', 'estee lauder',
        'clinique', 'lancome', 'maybelline', "l'oreal", 'loreal',
        'revlon', 'covergirl', 'nyx', 'urban decay', 'too faced',
        'kylie cosmetics', 'fenty', 'rare beauty', 'glossier',
        
        # Food/Beverage
        'coca cola', 'coca-cola', 'pepsi', 'red bull', 'monster energy',
        'starbucks', 'dunkin', 'mcdonalds', "mcdonald's", 'burger king',
        'oreo', 'nutella', 'hershey', "hershey's", 'nestle', 'mars',
        
        # Firearms/Weapons (often gated + IP issues)
        'glock', 'smith & wesson', 'remington', 'colt', 'ruger',
        'sig sauer', 'beretta', 'winchester', 'browning',
    }
    
    # HIGH RISK: Known to file claims but less aggressive
    HIGH_RISK_BRANDS = {
        # Home/Lifestyle
        'yeti', 'hydroflask', 'hydro flask', 'stanley', 'contigo',
        'tervis', 'swell', "s'well", 'corkcicle',
        'simplehuman', 'oxo', 'rubbermaid', 'tupperware',
        
        # Fitness
        'peloton', 'bowflex', 'nordictrack', 'theragun', 'hyperice',
        'fitbit', 'garmin', 'whoop', 'oura',
        
        # Outdoor/Sports Equipment
        'yeti', 'rtic', 'coleman', 'igloo',
        'callaway', 'titleist', 'taylormade', 'ping',
        'shimano', 'daiwa', 'penn',
        
        # Electronics Accessories
        'anker', 'belkin', 'logitech', 'razer', 'corsair',
        'steelseries', 'hyperx', 'elgato',
        
        # Pet Brands
        'kong', 'petsafe', 'furminator', 'greenies',
        
        # Baby/Kids
        'graco', 'chicco', 'uppababy', 'bugaboo', 'baby bjorn',
        'halo', 'owlet', 'snoo', 'ergobaby',
        
        # Health/Wellness
        'therabreath', 'crest', 'oral-b', 'philips sonicare',
        'braun', 'conair', 'revlon', 't3',
    }
    
    # MEDIUM RISK: Occasional claims or brand registry protected
    MEDIUM_RISK_BRANDS = {
        # General retail brands with active brand registry
        'crocs', 'skechers', 'vans', 'converse', 'asics',
        'osprey', 'jansport', 'herschel', 'fjallraven',
        'otter box', 'otterbox', 'spigen', 'lifeproof',
        'gopro', 'dji', 'ring', 'nest', 'wyze',
        'instant pot', 'ninja', 'vitamix', 'blendtec',
        'lodge', 'le creuset', 'staub', 'all-clad',
        'weber', 'traeger', 'big green egg', 'blackstone',
    }
    
    # Indicators that suggest brand protection/licensing
    BRAND_INDICATORS = [
        'official', 'licensed', 'authentic', 'genuine', 'original',
        'authorized', 'certified', 'trademark', '®', '™', '©',
        'exclusive', 'limited edition', 'collector',
        'by [brand]', 'from [brand]',
    ]
    
    # Keywords suggesting the listing IS the brand (not reselling)
    BRAND_OWNED_INDICATORS = [
        'visit the', 'brand:', 'by ', 'from ', 'official store',
        'authorized dealer', 'manufacturer direct',
    ]
    
    def __init__(self):
        # Combine all brands into normalized set for fast lookup
        self._critical = {b.lower() for b in self.CRITICAL_BRANDS}
        self._high = {b.lower() for b in self.HIGH_RISK_BRANDS}
        self._medium = {b.lower() for b in self.MEDIUM_RISK_BRANDS}
        
        logger.info(f"BrandRiskChecker initialized with {len(self._critical)} critical, "
                   f"{len(self._high)} high, {len(self._medium)} medium risk brands")
    
    def check_brand(self, brand_name: str, title: str = None, seller_name: str = None) -> BrandRiskResult:
        """
        Check if a brand has IP claim risk.
        
        Args:
            brand_name: The product brand
            title: Product title (for additional context)
            seller_name: Seller name (to check if brand-owned)
            
        Returns:
            BrandRiskResult with risk level and details
        """
        if not brand_name:
            return BrandRiskResult(
                brand_name="Unknown",
                risk_level=RiskLevel.LOW,
                reason="No brand information available",
                warnings=["Could not verify brand - proceed with caution"]
            )
        
        brand_lower = brand_name.lower().strip()
        title_lower = (title or "").lower()
        seller_lower = (seller_name or "").lower()
        warnings = []
        
        # Check CRITICAL brands first
        for critical_brand in self._critical:
            if critical_brand in brand_lower or critical_brand in title_lower:
                return BrandRiskResult(
                    brand_name=brand_name,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"'{critical_brand.title()}' is a high-litigation brand with aggressive IP enforcement",
                    is_veto=True,
                    warnings=[
                        "⛔ VETO: This brand is known to file IP claims",
                        "Selling this product risks account suspension",
                        "Do NOT source this product"
                    ]
                )
        
        # Check HIGH risk brands
        for high_brand in self._high:
            if high_brand in brand_lower or high_brand in title_lower:
                return BrandRiskResult(
                    brand_name=brand_name,
                    risk_level=RiskLevel.HIGH,
                    reason=f"'{high_brand.title()}' is a protected brand with Brand Registry",
                    is_veto=False,
                    warnings=[
                        "⚠️ HIGH RISK: This brand has filed IP claims before",
                        "Verify you have authorization to sell",
                        "Consider alternative products"
                    ]
                )
        
        # Check MEDIUM risk brands
        for medium_brand in self._medium:
            if medium_brand in brand_lower or medium_brand in title_lower:
                warnings.append(f"'{medium_brand.title()}' is a registered brand - verify authenticity")
                return BrandRiskResult(
                    brand_name=brand_name,
                    risk_level=RiskLevel.MEDIUM,
                    reason="Brand is registered but not known for aggressive enforcement",
                    warnings=warnings
                )
        
        # Check for brand indicators in title
        for indicator in self.BRAND_INDICATORS:
            if indicator.lower() in title_lower:
                warnings.append(f"Title contains '{indicator}' - may be brand-protected")
        
        # Check if seller is the brand (lower risk for them, higher for you)
        if brand_lower in seller_lower:
            warnings.append("Seller appears to be the brand owner - you may not be able to compete")
        
        # Default: SAFE or LOW risk
        if warnings:
            return BrandRiskResult(
                brand_name=brand_name,
                risk_level=RiskLevel.LOW,
                reason="Brand not in known risk database but has some indicators",
                warnings=warnings
            )
        
        return BrandRiskResult(
            brand_name=brand_name,
            risk_level=RiskLevel.SAFE,
            reason="Brand not found in IP risk database",
            warnings=[]
        )
    
    def check_product(self, product: Dict) -> BrandRiskResult:
        """
        Check a product dict for brand risk.
        
        Args:
            product: Product dict with 'brand', 'title', 'seller_name' keys
            
        Returns:
            BrandRiskResult
        """
        brand = product.get('brand', '')
        title = product.get('title', '')
        seller = product.get('seller_name', '')
        
        # Also extract brand from title if not provided
        if not brand and title:
            brand = self._extract_brand_from_title(title)
        
        return self.check_brand(brand, title, seller)
    
    def _extract_brand_from_title(self, title: str) -> str:
        """Try to extract brand name from title."""
        if not title:
            return ""
        
        # Common patterns: "Brand Name - Product Description" or "Brand Name Product"
        # Take first 2-3 words as potential brand
        words = title.split()
        if len(words) >= 2:
            # Check if first words match any known brand
            for i in range(min(3, len(words)), 0, -1):
                potential_brand = ' '.join(words[:i]).lower()
                if potential_brand in self._critical or potential_brand in self._high:
                    return potential_brand
        
        return ""
    
    def get_all_critical_brands(self) -> List[str]:
        """Return list of all critical (veto) brands."""
        return sorted(list(self.CRITICAL_BRANDS))
    
    def get_all_high_risk_brands(self) -> List[str]:
        """Return list of all high risk brands."""
        return sorted(list(self.HIGH_RISK_BRANDS))
    
    def add_brand_to_blacklist(self, brand: str, risk_level: str = "high"):
        """
        Add a brand to the blacklist (runtime only).
        For permanent additions, edit this file.
        """
        brand_lower = brand.lower()
        if risk_level == "critical":
            self._critical.add(brand_lower)
        elif risk_level == "high":
            self._high.add(brand_lower)
        else:
            self._medium.add(brand_lower)
        
        logger.info(f"Added '{brand}' to {risk_level} risk list")
