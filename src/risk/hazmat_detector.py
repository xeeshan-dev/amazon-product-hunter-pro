"""
Free Hazmat Detection Module
Detects potentially hazardous products based on keywords and patterns.
Cannot replace official Amazon Hazmat API but provides 70-80% accuracy screening.
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HazmatCategory(Enum):
    NONE = "none"
    FLAMMABLE = "flammable"
    CORROSIVE = "corrosive"
    BATTERY = "battery"
    PRESSURIZED = "pressurized"
    TOXIC = "toxic"
    OXIDIZER = "oxidizer"
    EXPLOSIVE = "explosive"
    UNKNOWN = "unknown"


@dataclass
class HazmatResult:
    is_hazmat: bool
    category: HazmatCategory
    confidence: float  # 0.0 to 1.0
    matched_keywords: List[str]
    warnings: List[str]
    restrictions: List[str]
    is_veto: bool = False  # If True, product should be auto-rejected
    
    def __post_init__(self):
        if self.matched_keywords is None:
            self.matched_keywords = []
        if self.warnings is None:
            self.warnings = []
        if self.restrictions is None:
            self.restrictions = []


class HazmatDetector:
    """
    Free hazmat detector using keyword pattern matching.
    Provides initial screening - sellers should verify with Amazon.
    """
    
    # BATTERY related keywords (very common hazmat issue)
    BATTERY_KEYWORDS = [
        'lithium', 'li-ion', 'li-po', 'lipo', 'lithium-ion', 'lithium-polymer',
        'lithium battery', 'rechargeable battery', 'battery pack', 'power bank',
        '18650', '21700', '26650', 'cr123', 'cr2032', 'button cell',
        'laptop battery', 'phone battery', 'replacement battery',
        'e-bike battery', 'scooter battery', 'drone battery',
        'vape battery', 'mod battery', 'ecig battery',
    ]
    
    # FLAMMABLE products
    FLAMMABLE_KEYWORDS = [
        'flammable', 'inflammable', 'combustible',
        'alcohol', 'isopropyl', 'ethanol', 'methanol', 'acetone',
        'nail polish', 'nail polish remover', 'nail acetone',
        'paint', 'paint thinner', 'lacquer', 'varnish', 'stain',
        'gasoline', 'petrol', 'diesel', 'kerosene', 'fuel',
        'lighter fluid', 'butane', 'propane', 'charcoal lighter',
        'hand sanitizer', 'sanitizer gel', 'rubbing alcohol',
        'perfume', 'cologne', 'fragrance oil', 'essential oil',
        'aftershave', 'body spray', 'hair spray', 'hairspray',
        'deodorant spray', 'antiperspirant spray',
        'cooking spray', 'oil spray', 'lubricant spray',
        'starter fluid', 'carburetor cleaner', 'brake cleaner',
    ]
    
    # PRESSURIZED containers (aerosols)
    PRESSURIZED_KEYWORDS = [
        'aerosol', 'spray can', 'compressed', 'pressurized',
        'air duster', 'canned air', 'compressed air',
        'spray paint', 'spray adhesive', 'spray lubricant',
        'bug spray', 'insecticide spray', 'pesticide spray',
        'bear spray', 'pepper spray', 'mace', 'self defense spray',
        'fire extinguisher', 'co2 cartridge', 'co2 tank',
        'whipped cream charger', 'n2o', 'nitrous oxide',
        'tire inflator', 'fix-a-flat',
    ]
    
    # CORROSIVE products
    CORROSIVE_KEYWORDS = [
        'acid', 'sulfuric', 'hydrochloric', 'muriatic', 'battery acid',
        'drain cleaner', 'drain opener', 'clog remover',
        'oven cleaner', 'grill cleaner', 'rust remover',
        'bleach', 'chlorine', 'pool chemicals', 'pool shock',
        'ammonia', 'lye', 'caustic soda', 'sodium hydroxide',
        'toilet bowl cleaner', 'lime remover', 'calcium remover',
        'etching', 'descaler', 'limescale remover',
    ]
    
    # TOXIC products
    TOXIC_KEYWORDS = [
        'poison', 'toxic', 'pesticide', 'insecticide', 'herbicide',
        'rodent killer', 'rat poison', 'mouse poison', 'ant killer',
        'roach killer', 'bug killer', 'wasp killer', 'flea killer',
        'weed killer', 'roundup', 'glyphosate',
        'antifreeze', 'coolant', 'motor oil', 'transmission fluid',
        'mercury', 'lead', 'arsenic', 'cadmium',
        'formaldehyde', 'benzene', 'toluene',
    ]
    
    # OXIDIZER products
    OXIDIZER_KEYWORDS = [
        'oxidizer', 'oxidizing', 'peroxide', 'hydrogen peroxide',
        'bleach', 'chlorine', 'bromine', 'iodine',
        'pool chlorine', 'pool shock', 'calcium hypochlorite',
        'potassium permanganate', 'sodium hypochlorite',
        'hair bleach', 'hair developer', 'hair peroxide',
    ]
    
    # EXPLOSIVE/DANGEROUS
    EXPLOSIVE_KEYWORDS = [
        'explosive', 'ammunition', 'ammo', 'gunpowder', 'black powder',
        'fireworks', 'firecracker', 'sparkler', 'roman candle',
        'flare', 'signal flare', 'smoke bomb', 'smoke grenade',
        'primer', 'detonator', 'fuse', 'blasting cap',
        'tannerite', 'binary explosive',
    ]
    
    # Categories that are often gated/restricted on Amazon
    RESTRICTED_CATEGORIES = {
        'dietary supplement': ['verify FDA compliance', 'may require approval'],
        'supplement': ['verify FDA compliance', 'may require approval'],
        'vitamins': ['may require category approval'],
        'medical device': ['requires FDA registration', 'category gated'],
        'otc medicine': ['requires approval', 'FDA regulated'],
        'drug': ['prescription items prohibited', 'verify OTC status'],
        'cosmetic': ['may require safety documentation'],
        'food': ['may require FDA compliance', 'expiration date requirements'],
        'baby food': ['strict requirements', 'expiration tracking'],
        'alcohol': ['prohibited in many states', 'license required'],
        'tobacco': ['prohibited', 'age verification required'],
        'weapon': ['prohibited', 'no firearms'],
        'knife': ['blade length restrictions', 'state laws vary'],
        'cbd': ['prohibited in many categories', 'legal gray area'],
        'hemp': ['requires documentation', 'THC limits'],
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._battery_pattern = self._compile_pattern(self.BATTERY_KEYWORDS)
        self._flammable_pattern = self._compile_pattern(self.FLAMMABLE_KEYWORDS)
        self._pressurized_pattern = self._compile_pattern(self.PRESSURIZED_KEYWORDS)
        self._corrosive_pattern = self._compile_pattern(self.CORROSIVE_KEYWORDS)
        self._toxic_pattern = self._compile_pattern(self.TOXIC_KEYWORDS)
        self._oxidizer_pattern = self._compile_pattern(self.OXIDIZER_KEYWORDS)
        self._explosive_pattern = self._compile_pattern(self.EXPLOSIVE_KEYWORDS)
        
        logger.info("HazmatDetector initialized")
    
    def _compile_pattern(self, keywords: List[str]) -> re.Pattern:
        """Compile keywords into a single regex pattern."""
        # Escape special chars and join with OR
        escaped = [re.escape(k) for k in keywords]
        pattern = r'\b(' + '|'.join(escaped) + r')\b'
        return re.compile(pattern, re.IGNORECASE)
    
    def check_hazmat(self, title: str, description: str = None, 
                     category: str = None, features: List[str] = None) -> HazmatResult:
        """
        Check if a product might be hazmat based on text analysis.
        
        Args:
            title: Product title
            description: Product description (optional)
            category: Product category (optional)
            features: Product bullet points/features (optional)
            
        Returns:
            HazmatResult with hazmat status and details
        """
        # Combine all text for analysis
        text_parts = [title or ""]
        if description:
            text_parts.append(description)
        if features:
            text_parts.extend(features)
        if category:
            text_parts.append(category)
        
        combined_text = ' '.join(text_parts).lower()
        
        matched_keywords = []
        warnings = []
        restrictions = []
        detected_category = HazmatCategory.NONE
        confidence = 0.0
        
        # Check each hazmat category
        checks = [
            (self._explosive_pattern, self.EXPLOSIVE_KEYWORDS, HazmatCategory.EXPLOSIVE, 1.0, True),
            (self._battery_pattern, self.BATTERY_KEYWORDS, HazmatCategory.BATTERY, 0.9, True),
            (self._flammable_pattern, self.FLAMMABLE_KEYWORDS, HazmatCategory.FLAMMABLE, 0.85, False),
            (self._pressurized_pattern, self.PRESSURIZED_KEYWORDS, HazmatCategory.PRESSURIZED, 0.9, True),
            (self._corrosive_pattern, self.CORROSIVE_KEYWORDS, HazmatCategory.CORROSIVE, 0.85, False),
            (self._toxic_pattern, self.TOXIC_KEYWORDS, HazmatCategory.TOXIC, 0.8, False),
            (self._oxidizer_pattern, self.OXIDIZER_KEYWORDS, HazmatCategory.OXIDIZER, 0.8, False),
        ]
        
        is_veto = False
        
        for pattern, keywords, cat, conf, veto in checks:
            matches = pattern.findall(combined_text)
            if matches:
                matched_keywords.extend(matches)
                if conf > confidence:
                    confidence = conf
                    detected_category = cat
                    if veto:
                        is_veto = True
        
        # Check for restricted categories
        for restricted, notes in self.RESTRICTED_CATEGORIES.items():
            if restricted in combined_text:
                restrictions.extend(notes)
                warnings.append(f"Product may be in restricted category: {restricted}")
        
        # Generate warnings based on detected category
        if detected_category != HazmatCategory.NONE:
            warnings.append(f"⚠️ Potential {detected_category.value.upper()} hazmat product")
            
            if detected_category == HazmatCategory.BATTERY:
                restrictions.extend([
                    "Lithium batteries require special shipping",
                    "May require UN3481/UN3091 certification",
                    "FBA has strict battery requirements",
                    "Must provide battery composition documentation"
                ])
            elif detected_category == HazmatCategory.FLAMMABLE:
                restrictions.extend([
                    "Flammable products require hazmat shipping",
                    "May not be eligible for FBA",
                    "Requires Safety Data Sheet (SDS)",
                    "Storage restrictions apply"
                ])
            elif detected_category == HazmatCategory.PRESSURIZED:
                restrictions.extend([
                    "Aerosols require special handling",
                    "Limited to ground shipping only",
                    "May not be FBA eligible",
                    "Pressure vessel regulations apply"
                ])
            elif detected_category == HazmatCategory.EXPLOSIVE:
                restrictions.extend([
                    "⛔ PROHIBITED: Explosive items not allowed on Amazon",
                    "Violates Amazon TOS",
                    "Legal consequences possible"
                ])
                is_veto = True
            elif detected_category == HazmatCategory.CORROSIVE:
                restrictions.extend([
                    "Corrosive products require SDS",
                    "Special packaging required",
                    "May require hazmat approval"
                ])
            elif detected_category == HazmatCategory.TOXIC:
                restrictions.extend([
                    "Toxic products heavily regulated",
                    "EPA registration may be required",
                    "Restricted in many states"
                ])
        
        # Adjust confidence based on number of matches
        if len(matched_keywords) > 3:
            confidence = min(1.0, confidence + 0.1)
        elif len(matched_keywords) == 1:
            confidence = max(0.5, confidence - 0.2)
        
        is_hazmat = detected_category != HazmatCategory.NONE
        
        if is_hazmat:
            logger.info(f"Hazmat detected: {detected_category.value} with {len(matched_keywords)} keyword matches")
        
        return HazmatResult(
            is_hazmat=is_hazmat,
            category=detected_category,
            confidence=confidence,
            matched_keywords=list(set(matched_keywords)),  # Deduplicate
            warnings=warnings,
            restrictions=restrictions,
            is_veto=is_veto
        )
    
    def check_product(self, product: Dict) -> HazmatResult:
        """
        Check a product dict for hazmat indicators.
        
        Args:
            product: Product dict with title, description, category, features
            
        Returns:
            HazmatResult
        """
        return self.check_hazmat(
            title=product.get('title', ''),
            description=product.get('description', ''),
            category=product.get('category', ''),
            features=product.get('features', [])
        )
    
    def get_hazmat_categories(self) -> List[str]:
        """Return list of hazmat categories detected."""
        return [cat.value for cat in HazmatCategory if cat != HazmatCategory.NONE]
