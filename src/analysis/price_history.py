"""
CamelCamelCamel Price History Scraper
FREE alternative to Keepa for getting historical price data.
Note: Scrapes CamelCamelCamel which tracks Amazon price history.
"""

import logging
import requests
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


@dataclass
class PriceHistoryPoint:
    date: str
    price: float
    source: str  # 'amazon', '3p_new', '3p_used'


@dataclass  
class PriceHistory:
    asin: str
    current_price: float
    lowest_price: float
    highest_price: float
    average_price: float
    price_drop_percentage: float  # Current vs highest
    is_at_lowest: bool
    is_near_lowest: bool  # Within 10% of lowest
    listing_age_months: int
    price_stability: str  # 'stable', 'volatile', 'declining', 'rising'
    history_points: List[PriceHistoryPoint]


class CamelPriceScraper:
    """
    Scrape price history from CamelCamelCamel (free Keepa alternative).
    
    CamelCamelCamel tracks Amazon price history and is free to use.
    This scraper extracts their chart data.
    
    Usage:
        scraper = CamelPriceScraper()
        history = scraper.get_price_history('B08XYZ123')
        
        print(f"Lowest ever: ${history.lowest_price}")
        print(f"Is near lowest: {history.is_near_lowest}")
    """
    
    BASE_URL = "https://camelcamelcamel.com/product"
    
    # Marketplace suffixes
    MARKETPLACES = {
        'US': '',
        'UK': '/uk',
        'DE': '/de',
        'FR': '/fr',
        'CA': '/ca',
        'ES': '/es',
        'IT': '/it',
        'AU': '/au',
        'JP': '/jp',
    }
    
    def __init__(self, marketplace: str = 'US'):
        self.ua = UserAgent()
        self.marketplace = marketplace
        self.session = requests.Session()
        
        logger.info(f"CamelPriceScraper initialized for {marketplace}")
    
    def _get_headers(self) -> Dict:
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def get_price_history(self, asin: str) -> Optional[PriceHistory]:
        """
        Get price history for a product from CamelCamelCamel.
        
        Args:
            asin: Amazon product ASIN
            
        Returns:
            PriceHistory object or None if failed
        """
        try:
            suffix = self.MARKETPLACES.get(self.marketplace, '')
            url = f"{self.BASE_URL}{suffix}/{asin}"
            
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=15
            )
            
            if response.status_code == 404:
                logger.warning(f"Product {asin} not found on CamelCamelCamel")
                return None
            
            if not response.ok:
                logger.error(f"Failed to fetch Camel page: {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return self._parse_price_history(soup, asin)
            
        except Exception as e:
            logger.error(f"Error getting price history for {asin}: {str(e)}")
            return None
    
    def _parse_price_history(self, soup: BeautifulSoup, asin: str) -> Optional[PriceHistory]:
        """Parse price history from CamelCamelCamel page."""
        try:
            # Find the price summary section
            # CamelCamelCamel shows: Current, Lowest, Highest, Average
            
            prices = {
                'current': 0,
                'lowest': 0,
                'highest': 0,
                'average': 0
            }
            
            # Try to find price table/stats
            stats_section = soup.find('table', {'class': 'product_pane'})
            if not stats_section:
                stats_section = soup.find('div', {'class': 'prices'})
            
            # Extract prices from various possible locations
            price_patterns = [
                (r'Current.*?\$?([\d,]+\.?\d*)', 'current'),
                (r'Lowest.*?\$?([\d,]+\.?\d*)', 'lowest'),
                (r'Highest.*?\$?([\d,]+\.?\d*)', 'highest'),
                (r'Average.*?\$?([\d,]+\.?\d*)', 'average'),
            ]
            
            page_text = soup.get_text()
            
            for pattern, key in price_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        prices[key] = float(match.group(1).replace(',', ''))
                    except:
                        pass
            
            # Alternative: look for specific elements
            for stat_row in soup.find_all('tr'):
                row_text = stat_row.get_text().lower()
                price_elem = stat_row.find('td', {'class': 'amazon'}) or stat_row.find('td')
                
                if price_elem:
                    try:
                        price_text = price_elem.get_text()
                        price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                        if price_match:
                            price_val = float(price_match.group(1).replace(',', ''))
                            
                            if 'current' in row_text:
                                prices['current'] = price_val
                            elif 'lowest' in row_text or 'low' in row_text:
                                prices['lowest'] = price_val
                            elif 'highest' in row_text or 'high' in row_text:
                                prices['highest'] = price_val
                            elif 'average' in row_text or 'avg' in row_text:
                                prices['average'] = price_val
                    except:
                        continue
            
            # Calculate derived metrics
            current = prices['current'] or prices['average']
            lowest = prices['lowest'] or current
            highest = prices['highest'] or current
            average = prices['average'] or current
            
            if current <= 0:
                logger.warning(f"Could not extract valid price data for {asin}")
                return None
            
            # Price drop percentage
            price_drop = ((highest - current) / highest * 100) if highest > 0 else 0
            
            # Is at/near lowest
            is_at_lowest = current <= lowest * 1.02  # Within 2%
            is_near_lowest = current <= lowest * 1.10  # Within 10%
            
            # Estimate listing age from first data point
            # CamelCamelCamel typically starts tracking when product is listed
            listing_age = self._estimate_listing_age(soup)
            
            # Determine price stability
            if highest > 0 and lowest > 0:
                volatility = (highest - lowest) / average if average > 0 else 0
                if volatility < 0.1:
                    stability = 'stable'
                elif volatility < 0.3:
                    stability = 'moderate'
                else:
                    stability = 'volatile'
                    
                # Check trend
                if current < average * 0.9:
                    stability = 'declining'
                elif current > average * 1.1:
                    stability = 'rising'
            else:
                stability = 'unknown'
            
            return PriceHistory(
                asin=asin,
                current_price=current,
                lowest_price=lowest,
                highest_price=highest,
                average_price=average,
                price_drop_percentage=round(price_drop, 1),
                is_at_lowest=is_at_lowest,
                is_near_lowest=is_near_lowest,
                listing_age_months=listing_age,
                price_stability=stability,
                history_points=[]  # Would need chart parsing for detailed history
            )
            
        except Exception as e:
            logger.error(f"Error parsing price history: {str(e)}")
            return None
    
    def _estimate_listing_age(self, soup: BeautifulSoup) -> int:
        """Estimate product listing age from CamelCamelCamel data."""
        try:
            # Look for "First tracked" or similar text
            page_text = soup.get_text()
            
            # Pattern: "Tracked since: January 2020" or similar
            date_patterns = [
                r'tracked since[:\s]*([\w\s,]+\d{4})',
                r'first tracked[:\s]*([\w\s,]+\d{4})',
                r'since[:\s]*([\w]+\s+\d{4})',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    try:
                        date_str = match.group(1).strip()
                        # Parse various date formats
                        for fmt in ['%B %Y', '%b %Y', '%B %d, %Y', '%m/%d/%Y']:
                            try:
                                first_date = datetime.strptime(date_str, fmt)
                                months = (datetime.now() - first_date).days // 30
                                return max(0, months)
                            except:
                                continue
                    except:
                        continue
            
            # Default: assume recent if can't determine
            return 0
            
        except:
            return 0
    
    def is_price_good(self, asin: str) -> Dict:
        """
        Quick check if current price is good (near lowest).
        
        Returns:
            Dict with 'is_good', 'reason', 'current', 'lowest'
        """
        history = self.get_price_history(asin)
        
        if not history:
            return {
                'is_good': None,
                'reason': 'Could not fetch price history',
                'current': None,
                'lowest': None
            }
        
        if history.is_at_lowest:
            return {
                'is_good': True,
                'reason': 'Price is at all-time low!',
                'current': history.current_price,
                'lowest': history.lowest_price
            }
        elif history.is_near_lowest:
            return {
                'is_good': True,
                'reason': 'Price is within 10% of lowest',
                'current': history.current_price,
                'lowest': history.lowest_price
            }
        elif history.current_price > history.average_price * 1.1:
            return {
                'is_good': False,
                'reason': 'Price is above average - wait for drop',
                'current': history.current_price,
                'lowest': history.lowest_price
            }
        else:
            return {
                'is_good': True,
                'reason': 'Price is reasonable',
                'current': history.current_price,
                'lowest': history.lowest_price
            }
    
    def get_listing_age(self, asin: str) -> int:
        """
        Get estimated listing age in months.
        Useful for detecting newly boosted products.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Age in months, or -1 if unknown
        """
        history = self.get_price_history(asin)
        return history.listing_age_months if history else -1
