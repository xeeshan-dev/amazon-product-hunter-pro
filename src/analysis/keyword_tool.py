"""
Free Keyword Research Module
Uses Amazon Autocomplete API (free!) to find keyword suggestions.
Also includes basic reverse ASIN functionality via search scraping.
"""

import logging
import requests
import time
import random
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)


@dataclass
class KeywordSuggestion:
    keyword: str
    source: str  # 'autocomplete', 'related', 'competitor'
    estimated_competition: str  # 'low', 'medium', 'high', 'unknown'
    relevance_score: float  # 0.0 to 1.0


@dataclass
class ReverseASINResult:
    asin: str
    keywords_found: List[Dict]  # [{'keyword': str, 'rank': int, 'page': int}]
    total_keywords: int


class FreeKeywordTool:
    """
    Free keyword research using Amazon's public autocomplete API.
    No API key required - uses the same endpoint as Amazon's search bar.
    """
    
    # Amazon Autocomplete API endpoint (public, no auth needed)
    AUTOCOMPLETE_URL = "https://completion.amazon.com/api/2017/suggestions"
    
    # Marketplace IDs
    MARKETPLACE_IDS = {
        'US': 'ATVPDKIKX0DER',
        'UK': 'A1F83G8C2ARO7P',
        'DE': 'A1PA6795UKMFR9',
        'FR': 'A13V1IB3VIYBER',
        'IT': 'APJ6JRA9NG5V4',
        'ES': 'A1RKKUPIHCS9HS',
        'CA': 'A2EUQ1WTGCTBG2',
        'JP': 'A1VC38T7YXB528',
        'AU': 'A39IBJ37TRP1C6',
    }
    
    def __init__(self, marketplace: str = 'US'):
        self.ua = UserAgent()
        self.marketplace = marketplace
        self.mid = self.MARKETPLACE_IDS.get(marketplace, 'ATVPDKIKX0DER')
        self.session = requests.Session()
        
        logger.info(f"FreeKeywordTool initialized for marketplace: {marketplace}")
    
    def _get_headers(self) -> Dict:
        return {
            'User-Agent': self.ua.random,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def get_autocomplete_suggestions(self, seed_keyword: str) -> List[KeywordSuggestion]:
        """
        Get keyword suggestions from Amazon's autocomplete API.
        
        Args:
            seed_keyword: The base keyword to get suggestions for
            
        Returns:
            List of KeywordSuggestion objects
        """
        suggestions = []
        
        try:
            params = {
                'mid': self.mid,
                'alias': 'aps',  # All departments
                'prefix': seed_keyword,
                'fresh': 0,
                'event': 'onFocusWithSearchTerm',
            }
            
            response = self.session.get(
                self.AUTOCOMPLETE_URL,
                params=params,
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.ok:
                data = response.json()
                for suggestion in data.get('suggestions', []):
                    keyword = suggestion.get('value', '')
                    if keyword and keyword.lower() != seed_keyword.lower():
                        suggestions.append(KeywordSuggestion(
                            keyword=keyword,
                            source='autocomplete',
                            estimated_competition='unknown',
                            relevance_score=0.8  # Autocomplete = high relevance
                        ))
            
            logger.info(f"Found {len(suggestions)} autocomplete suggestions for '{seed_keyword}'")
            
        except Exception as e:
            logger.error(f"Error getting autocomplete suggestions: {str(e)}")
        
        return suggestions
    
    def get_alphabet_suggestions(self, seed_keyword: str) -> List[KeywordSuggestion]:
        """
        Get expanded suggestions by appending letters a-z to seed keyword.
        This is how tools like Helium 10 expand keyword lists.
        
        Args:
            seed_keyword: Base keyword
            
        Returns:
            List of KeywordSuggestion objects
        """
        all_suggestions = []
        seen_keywords = set()
        
        # First get base suggestions
        base_suggestions = self.get_autocomplete_suggestions(seed_keyword)
        for s in base_suggestions:
            if s.keyword.lower() not in seen_keywords:
                seen_keywords.add(s.keyword.lower())
                all_suggestions.append(s)
        
        # Then expand with each letter
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            try:
                expanded_keyword = f"{seed_keyword} {letter}"
                letter_suggestions = self.get_autocomplete_suggestions(expanded_keyword)
                
                for s in letter_suggestions:
                    if s.keyword.lower() not in seen_keywords:
                        seen_keywords.add(s.keyword.lower())
                        s.relevance_score = 0.6  # Slightly lower for expanded
                        all_suggestions.append(s)
                
                # Small delay to avoid rate limiting
                time.sleep(random.uniform(0.1, 0.3))
                
            except Exception as e:
                logger.debug(f"Error expanding with letter {letter}: {str(e)}")
                continue
        
        logger.info(f"Found {len(all_suggestions)} total suggestions for '{seed_keyword}'")
        return all_suggestions
    
    def get_question_keywords(self, seed_keyword: str) -> List[KeywordSuggestion]:
        """
        Get question-based keywords (how, what, why, where, etc.)
        Great for content/SEO optimization.
        
        Args:
            seed_keyword: Base keyword
            
        Returns:
            List of KeywordSuggestion objects
        """
        question_words = ['how', 'what', 'why', 'where', 'when', 'which', 'who', 
                         'can', 'does', 'is', 'are', 'best', 'top', 'vs']
        
        all_suggestions = []
        seen_keywords = set()
        
        for q_word in question_words:
            try:
                query = f"{q_word} {seed_keyword}"
                suggestions = self.get_autocomplete_suggestions(query)
                
                for s in suggestions:
                    if s.keyword.lower() not in seen_keywords:
                        seen_keywords.add(s.keyword.lower())
                        s.source = 'question'
                        s.relevance_score = 0.7
                        all_suggestions.append(s)
                
                time.sleep(random.uniform(0.1, 0.2))
                
            except Exception:
                continue
        
        return all_suggestions
    
    def reverse_asin_basic(self, asin: str, test_keywords: List[str], 
                           base_url: str = "https://www.amazon.com") -> ReverseASINResult:
        """
        Basic reverse ASIN: check which keywords a product ranks for.
        This is a FREE but SLOW alternative to paid tools.
        
        Args:
            asin: Product ASIN to analyze
            test_keywords: List of keywords to test
            base_url: Amazon base URL
            
        Returns:
            ReverseASINResult with ranking data
        """
        from bs4 import BeautifulSoup
        
        keywords_found = []
        
        for keyword in test_keywords:
            try:
                # Search Amazon for this keyword
                search_url = f"{base_url}/s?k={keyword.replace(' ', '+')}"
                
                response = self.session.get(
                    search_url,
                    headers=self._get_headers(),
                    timeout=15
                )
                
                if not response.ok:
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all products on the page
                results = soup.find_all('div', {'data-asin': True})
                
                for rank, result in enumerate(results, 1):
                    result_asin = result.get('data-asin', '')
                    if result_asin == asin:
                        keywords_found.append({
                            'keyword': keyword,
                            'rank': rank,
                            'page': 1
                        })
                        logger.info(f"Found ASIN {asin} ranking #{rank} for '{keyword}'")
                        break
                
                # Rate limiting
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                logger.debug(f"Error checking keyword '{keyword}': {str(e)}")
                continue
        
        return ReverseASINResult(
            asin=asin,
            keywords_found=keywords_found,
            total_keywords=len(keywords_found)
        )
    
    def generate_keyword_variations(self, seed_keyword: str) -> List[str]:
        """
        Generate keyword variations for reverse ASIN testing.
        
        Args:
            seed_keyword: Base keyword
            
        Returns:
            List of keyword variations
        """
        variations = [seed_keyword]
        words = seed_keyword.split()
        
        # Singular/plural variations
        for i, word in enumerate(words):
            # Simple pluralization
            if word.endswith('s'):
                singular = word[:-1]
            else:
                singular = word
                plural = word + 's'
                
            # Create variation with singular
            new_words = words.copy()
            new_words[i] = singular
            variations.append(' '.join(new_words))
            
            # Create variation with plural
            if not word.endswith('s'):
                new_words = words.copy()
                new_words[i] = plural
                variations.append(' '.join(new_words))
        
        # Word order variations (for 2+ word phrases)
        if len(words) >= 2:
            variations.append(' '.join(reversed(words)))
        
        # Common modifiers
        modifiers = ['best', 'top', 'cheap', 'premium', 'professional', 
                    'for women', 'for men', 'for kids', 'small', 'large']
        for mod in modifiers:
            variations.append(f"{mod} {seed_keyword}")
            variations.append(f"{seed_keyword} {mod}")
        
        return list(set(variations))  # Deduplicate
    
    def analyze_keyword(self, keyword: str, base_url: str = "https://www.amazon.com") -> Dict:
        """
        Analyze a keyword's competition level by looking at search results.
        
        Args:
            keyword: Keyword to analyze
            base_url: Amazon base URL
            
        Returns:
            Dict with competition analysis
        """
        from bs4 import BeautifulSoup
        
        try:
            search_url = f"{base_url}/s?k={keyword.replace(' ', '+')}"
            
            response = self.session.get(
                search_url,
                headers=self._get_headers(),
                timeout=15
            )
            
            if not response.ok:
                return {'error': 'Failed to fetch search results'}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all products
            results = soup.find_all('div', {'data-asin': True})
            
            # Analyze competition metrics
            review_counts = []
            ratings = []
            prices = []
            sponsored_count = 0
            
            for result in results[:20]:  # Top 20 results
                # Check if sponsored
                if result.find('span', text=re.compile(r'sponsored', re.I)):
                    sponsored_count += 1
                
                # Get review count
                review_elem = result.find('span', {'class': 'a-size-base'})
                if review_elem:
                    try:
                        count = int(review_elem.get_text().replace(',', ''))
                        review_counts.append(count)
                    except:
                        pass
                
                # Get rating
                rating_elem = result.find('span', {'class': 'a-icon-alt'})
                if rating_elem:
                    try:
                        rating_text = rating_elem.get_text()
                        rating = float(re.search(r'(\d+\.?\d*)', rating_text).group(1))
                        ratings.append(rating)
                    except:
                        pass
                
                # Get price
                price_elem = result.find('span', {'class': 'a-price-whole'})
                if price_elem:
                    try:
                        price = float(price_elem.get_text().replace(',', '').replace('.', ''))
                        prices.append(price)
                    except:
                        pass
            
            # Calculate competition level
            avg_reviews = sum(review_counts) / len(review_counts) if review_counts else 0
            low_review_count = sum(1 for r in review_counts if r < 400)
            
            if avg_reviews < 200 and low_review_count >= 3:
                competition_level = 'low'
            elif avg_reviews < 500 and low_review_count >= 2:
                competition_level = 'medium'
            else:
                competition_level = 'high'
            
            return {
                'keyword': keyword,
                'total_results': len(results),
                'sponsored_count': sponsored_count,
                'avg_reviews': round(avg_reviews, 0),
                'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
                'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                'low_review_products': low_review_count,  # Products with <400 reviews
                'competition_level': competition_level,
                'opportunity_indicators': {
                    'weak_competitors': low_review_count >= 3,
                    'low_sponsored': sponsored_count <= 3,
                    'good_price_range': 15 <= (sum(prices) / len(prices) if prices else 0) <= 50
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing keyword '{keyword}': {str(e)}")
            return {'error': str(e)}
