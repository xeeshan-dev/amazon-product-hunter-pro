import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import random
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.settings import Config
from analysis.seller_analysis import SellerAnalyzer

class AmazonScraper:
    def __init__(self, base_url: Optional[str] = None):
        self.ua = UserAgent()
        self.base_url = base_url or Config.BASE_URL
        self.seller_analyzer = SellerAnalyzer()
        self.session = requests.Session()
        
    def _get_headers(self) -> Dict:
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Cookie': 'lc-main=en_US; i18n-prefs=USD; ubid-main=130-0000000-0000000',
        }
    
    def search_products(self, keyword: str, pages: int = 1, category: str = None, is_asin: bool = False) -> List[Dict]:
        """Fast product search - optimized for speed."""
        products = []
        
        try:
            if is_asin:
                product = self.get_product_details(keyword)
                if product:
                    self._add_market_metrics(product)
                    category = self._extract_category(product)
                    price = product.get('price', 0)
                    price_range = (max(0, price * 0.7), price * 1.3)
                    competitors = self._search_similar_products(category, price_range)
                    products.extend(competitors)
            else:
                # Fast keyword-based search
                for page in range(1, pages + 1):
                    url = f"{self.base_url}/s?k={keyword}"
                    if category and category != "All Categories":
                        url += f"&rh=n%3A{self._get_category_id(category)}"
                    url += f"&page={page}"
                    
                    response = self.session.get(url, headers=self._get_headers(), timeout=10)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    items = soup.find_all('div', {'data-component-type': 's-search-result'})
                    
                    for item in items:
                        product = self._extract_search_item_data(item)
                        if product and product.get('price'):  # Only keep with valid prices
                            # Heuristic BSR if missing
                            if 'bsr' not in product:
                                search_rank = (page - 1) * 48 + items.index(item) + 1
                                product['bsr'] = search_rank * 200 # roughly
                            
                            self._add_market_metrics(product)
                            products.append(product)
                    
                    # Minimal delay between pages
                    if page < pages:
                        time.sleep(0.5)

            # Post-processing: Calculate Market Share
            total_sales = sum(p.get('estimated_sales', 0) for p in products)
            if total_sales > 0:
                for p in products:
                    p['market_share'] = (p.get('estimated_sales', 0) / total_sales) * 100
        
        except Exception as e:
            logger.error(f"Error in product search: {str(e)}")
        
        return products

    def _get_category_id(self, category: str) -> str:
        # Map category names to Amazon category IDs
        category_map = {
            "Health & Household": "3760901",
            "Home & Kitchen": "1055398",
            "Sports & Outdoors": "3375251",
            "Beauty & Personal Care": "3760911",
            "Pet Supplies": "2619533011"
        }
        return category_map.get(category, "")

    def _add_market_metrics(self, product: Dict):
        try:
            # Set default values first
            product['estimated_sales'] = 0
            product['estimated_margin'] = 0
            product['seasonality'] = ['All Year']
            product['search_volume'] = 0
            product['market_share'] = 0
            
            # Only proceed with calculations if we have required data
            if product and isinstance(product, dict):
                # Estimate monthly sales using BSR and category benchmarks
                bsr = product.get('bsr')
                if bsr and isinstance(bsr, (int, float)) and bsr > 0:
                    product['estimated_sales'] = self._estimate_sales_from_bsr(bsr, product.get('category', 'Generic'))
                
                # Calculate profit margins
                price = product.get('price')
                if price and isinstance(price, (int, float)) and price > 0:
                    # Estimate costs (Amazon fees, shipping, product cost)
                    fba_fees = self._calculate_fba_fees(price, product.get('dimensions'))
                    estimated_cost = price * 0.25  # Assume 25% of price is product cost
                    product['estimated_margin'] = ((price - fba_fees - estimated_cost) / price) * 100
            
            # Analyze seasonality
            product['seasonality'] = self._analyze_seasonality(product.get('asin', ''))
            
            # Add search volume estimate
            product['search_volume'] = self._estimate_search_volume(product.get('title', ''))
            
            # Market share is calculated in post-processing
            
        except Exception as e:
            logger.error(f"Error adding market metrics: {str(e)}")
            # Set default values if error occurs
            product['estimated_sales'] = 0
            product['estimated_margin'] = 0
            product['seasonality'] = ['All Year']
            product['search_volume'] = 0
            product['market_share'] = 0

    def _add_listing_quality_score(self, product: Dict):
        # Set default score
        score = 0
        try:
            if not product or not isinstance(product, dict):
                product['listing_quality'] = score
                return
                
            # Title quality (length, keywords)
            title = product.get('title')
            if title and isinstance(title, str):
                title_len = len(title)
                if 50 <= title_len <= 150:
                    score += 3
                elif 30 <= title_len < 50:
                    score += 2
                score += self._count_keywords(title)
            
            # Image quality
            images_count_value = product.get('images_count')
            try:
                images_count_value = int(images_count_value) if images_count_value is not None else 0
            except Exception:
                images_count_value = 0
            if images_count_value >= 6:
                score += 2
            
            # Description quality
            if isinstance(product.get('description'), str) and product.get('description'):
                desc_len = len(product['description'])
                if desc_len >= 1000:
                    score += 3
                elif desc_len >= 500:
                    score += 2
            
            # Reviews quality
            try:
                rating_value = float(product.get('rating')) if product.get('rating') is not None else 0.0
            except Exception:
                rating_value = 0.0
            try:
                reviews_value = int(product.get('reviews')) if product.get('reviews') is not None else 0
            except Exception:
                reviews_value = 0
            if rating_value >= 4.5 and reviews_value >= 100:
                score += 2
            
            product['listing_quality'] = min(10, score)
            
        except Exception as e:
            logger.error(f"Error calculating listing quality: {str(e)}")
            product['listing_quality'] = 0
    
    def get_product_details(self, asin: str) -> Optional[Dict]:
        url = f"{self.base_url}/dp/{asin}"
        
        try:
            response = self.session.get(url, headers=self._get_headers())
            soup = BeautifulSoup(response.content, 'html.parser')
            
            try:
                return self._extract_product_details(soup, asin)
            except AttributeError:
                # This happens when seller_info doesn't have expected attributes
                logger.warning(f"Could not analyze sellers for product {asin}")
                return None
            
        except Exception as e:
            logger.error(f"Error scraping product {asin}: {str(e)}")
            return None
    
    def get_seller_summary(self, asin: str) -> Dict:
        """Quickly fetch seller counts via AOD sprite/AJAX without full product parse."""
        try:
            headers = self._get_headers()
            referer_url = f"{self.base_url}/dp/{asin}"
            info = self.seller_analyzer.analyze_sellers(
                soup=None,
                asin=asin,
                headers=headers,
                session=self.session,
                referer=referer_url
            )
            return {
                'fba_count': info.fba_count,
                'fbm_count': info.fbm_count,
                'amazon_seller': info.amazon_seller,
                'total_sellers': info.total_sellers,
                'prices': info.prices,
                'seller_name': info.seller_name  # ← ADDED
            }
        except Exception as e:
            logger.error(f"Error fetching seller summary for {asin}: {str(e)}")
            return {
                'fba_count': 0,
                'fbm_count': 0,
                'amazon_seller': False,
                'total_sellers': 0,
                'prices': {'fba': [], 'fbm': []},
                'seller_name': None  # ← ADDED
            }
            
    def _extract_search_item_data(self, item) -> Optional[Dict]:
        try:
            asin = item.get('data-asin')
            if not asin:
                return None
                
            # Title extraction
            title_elem = (
                item.find('h2', {'class': 'a-size-mini'}) or
                item.find('h2', {'class': 'a-size-base-plus'}) or
                item.find('h2', {'class': 'a-size-medium'}) or
                item.find('span', {'class': 'a-size-medium'}) or
                item.find('a', {'class': 'a-link-normal'})
            )
            title = title_elem.get_text().strip() if title_elem else None
            
            # Price extraction - look for the main price container first
            # Amazon uses 'a-price' class as the main price wrapper
            price_elem = item.find('span', {'class': 'a-price', 'data-a-color': 'base'})
            if not price_elem:
                price_elem = item.find('span', {'class': 'a-price'})
            if not price_elem:
                # Fallback to other price selectors
                price_elem = (
                    item.find('span', {'class': 'a-color-price'}) or
                    item.find('span', {'class': 'a-offscreen'}) or
                    item.find('span', {'class': 'sx-price'}) or
                    item.find('span', {'class': 'p13n-sc-price'}) or
                    item.find('span', class_=lambda x: x and 'price' in x.lower() if x else False)
                )
            
            # Enhanced rating extraction
            rating_elem = (
                item.find('span', {'class': 'a-icon-alt'}) or
                item.find('span', {'class': 'a-icon-star'}) or
                item.find('span', {'class': 'a-icon-star-small'}) or
                item.find('i', {'class': 'a-icon-star'}) or
                item.find('div', {'class': 'a-icon-row'}) or
                item.find('span', {'aria-label': lambda x: x and 'star' in x.lower()})
            )
            
            # Enhanced review extraction
            reviews_elem = (
                item.find('span', {'class': 'a-size-base'}) or
                item.find('span', {'class': 'a-size-small'}) or
                item.find('a', {'class': 'a-link-normal'}) or
                item.find('span', {'aria-label': lambda x: x and 'review' in x.lower()}) or
                item.find('span', text=lambda t: t and any(word in t.lower() for word in ['review', 'rating', 'star']))
            )
            
            # Extract data with improved methods
            price = self._extract_price(price_elem) if price_elem else None
            rating = self._extract_rating(rating_elem) if rating_elem else 0.0
            reviews = self._extract_reviews(reviews_elem) if reviews_elem else 0
            
            # Additional fallback for reviews - look in the entire item
            if reviews == 0:
                item_text = item.get_text()
                import re
                review_matches = re.findall(r'(\d{1,3}(?:,\d{3})*)\s*(?:reviews?|ratings?)', item_text, re.IGNORECASE)
                if review_matches:
                    try:
                        reviews = int(review_matches[0].replace(',', ''))
                    except:
                        pass
            
            return {
                'asin': asin,
                'title': title,
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'url': f"{self.base_url}/dp/{asin}"
            }
            
        except Exception as e:
            logger.debug(f"Error extracting search item data: {str(e)}")
            return None
    
    def _extract_product_details(self, soup, asin: str) -> Dict:
        referer_url = f"{self.base_url}/dp/{asin}"
        seller_info = self.seller_analyzer.analyze_sellers(
            soup,
            asin=asin,
            headers=self._get_headers(),
            session=self.session,
            referer=referer_url
        )
        
        details = {
            'asin': asin,
            'bsr': self._extract_bsr(soup),
            'description': self._extract_description(soup),
            'features': self._extract_features(soup),
            'images_count': self._extract_images_count(soup),
            'seller_info': {
                'fba_count': seller_info.fba_count if hasattr(seller_info, 'fba_count') else 0,
                'fbm_count': seller_info.fbm_count if hasattr(seller_info, 'fbm_count') else 0,
                'amazon_seller': seller_info.amazon_seller if hasattr(seller_info, 'amazon_seller') else False,
                'total_sellers': seller_info.total_sellers if hasattr(seller_info, 'total_sellers') else 0,
                'prices': {
                    'fba': seller_info.prices.get('fba', []) if hasattr(seller_info, 'prices') else [],
                    'fbm': seller_info.prices.get('fbm', []) if hasattr(seller_info, 'prices') else []
                }
            }
        }
        return details

    def _extract_price(self, elem) -> float:
        """Extract price - simplified and accurate."""
        import re
        try:
            if not elem:
                return None
            
            # Method 1: a-offscreen is MOST RELIABLE (screen reader text like "$29.99")
            offscreen = elem.find('span', {'class': 'a-offscreen'})
            if offscreen:
                price_text = offscreen.get_text().strip()
                # Match $XX.XX format exactly
                match = re.match(r'^\$?([\d,]+\.\d{2})$', price_text.replace('$', '$'))
                if match:
                    price = float(match.group(1).replace(',', ''))
                    if 0.50 <= price <= 5000:
                        return price
            
            # Method 2: Whole + Fraction parts (Amazon's visual display)
            whole_elem = elem.find('span', {'class': 'a-price-whole'})
            frac_elem = elem.find('span', {'class': 'a-price-fraction'})
            
            if whole_elem:
                whole_text = whole_elem.get_text().strip()
                # Remove trailing dot and extract just digits
                whole = ''.join(c for c in whole_text if c.isdigit())
                frac = '00'
                if frac_elem:
                    frac_text = frac_elem.get_text().strip()
                    frac = ''.join(c for c in frac_text if c.isdigit())[:2].ljust(2, '0')
                
                if whole:
                    try:
                        price = float(f"{whole}.{frac}")
                        if 0.50 <= price <= 5000:
                            return price
                    except:
                        pass
            
            # Method 3: Find $XX.XX pattern in text
            text = elem.get_text()
            match = re.search(r'\$([\d,]+\.\d{2})', text)
            if match:
                price = float(match.group(1).replace(',', ''))
                if 0.50 <= price <= 5000:
                    return price
            
            return None
        except:
            return None

    def _extract_rating(self, elem) -> float:
        try:
            if not elem:
                return 0.0
            text = elem.get_text().strip()
            # Extract rating from text like "4.6 out of 5 stars" or "4.6"
            import re
            rating_match = re.search(r'(\d+\.?\d*)', text)
            if rating_match:
                rating = float(rating_match.group(1))
                # Ensure rating is between 1-5
                if 1.0 <= rating <= 5.0:
                    return rating
            return 0.0
        except Exception as e:
            logger.debug(f"Error extracting rating: {str(e)}")
            return 0.0

    def _extract_reviews(self, elem) -> int:
        try:
            if not elem:
                return 0
            text = elem.get_text().strip()
            # Extract review count from text like "1,234" or "1234"
            import re
            # Remove common words and extract numbers
            text = re.sub(r'[^\d,]', '', text)
            if text:
                # Remove commas and convert to int
                review_count = int(text.replace(',', ''))
                return review_count
            return 0
        except Exception as e:
            logger.debug(f"Error extracting reviews: {str(e)}")
            return 0

    def _extract_bsr(self, soup) -> Optional[int]:
        try:
            import re
            
            # 1) Enhanced BSR extraction with multiple methods
            bsr_patterns = [
                # Direct ID-based extraction
                soup.find('span', {'id': 'salesrank'}),
                soup.find('span', {'id': 'SalesRank'}),
                soup.find('span', {'id': 'productSalesRank'}),
                
                # Class-based extraction
                soup.find('span', {'class': 'a-text-bold'}),
                soup.find('div', {'class': 'a-text-bold'}),
                
                # Text-based extraction
                soup.find(text=lambda t: t and 'best sellers rank' in t.lower()),
                soup.find(text=lambda t: t and 'sales rank' in t.lower()),
                soup.find(text=lambda t: t and '#1' in t and 'in' in t.lower())
            ]
            
            for elem in bsr_patterns:
                if elem:
                    try:
                        if hasattr(elem, 'get_text'):
                            text = elem.get_text()
                        else:
                            text = str(elem)
                        
                        # Extract BSR number using regex
                        bsr_match = re.search(r'#([\d,]+)', text)
                        if bsr_match:
                            bsr_num = int(bsr_match.group(1).replace(',', ''))
                            if bsr_num > 0:
                                logger.info(f"Extracted BSR: {bsr_num}")
                                return bsr_num
                    except Exception:
                        continue

            # 2) Enhanced product details table search
            details_selectors = [
                {'tag': 'ul', 'attrs': {'id': ['detailBullets_feature_div', 'productDetails_detailBullets_sections1']}},
                {'tag': 'table', 'attrs': {'class': ['prodDetTable', 'a-keyvalue']}},
                {'tag': 'div', 'attrs': {'id': ['productDetails_feature_div', 'detailBullets_feature_div']}},
                {'tag': 'div', 'attrs': {'class': ['a-section', 'a-spacing-small']}}
            ]
            
            for selector in details_selectors:
                sections = soup.find_all(selector['tag'], selector['attrs'])
                for section in sections:
                    text = section.get_text(" ", strip=True)
                    if 'best sellers rank' in text.lower() or 'sales rank' in text.lower():
                        # Multiple regex patterns for BSR
                        bsr_patterns = [
                            r'best sellers rank\s*#([\d,]+)',
                            r'sales rank\s*#([\d,]+)',
                            r'rank\s*#([\d,]+)',
                            r'#([\d,]+)\s*in\s+',
                            r'#([\d,]+)\s*\('
                        ]
                        
                        for pattern in bsr_patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                bsr_num = int(match.group(1).replace(',', ''))
                                if bsr_num > 0:
                                    logger.info(f"Extracted BSR from details: {bsr_num}")
                                    return bsr_num

            # 3) Fallback: search entire page for BSR patterns
            page_text = soup.get_text()
            bsr_patterns = [
                r'#([\d,]+)\s+in\s+[A-Za-z\s]+(?:\(|$)',  # #1,234 in Category
                r'best sellers rank\s*#([\d,]+)',
                r'sales rank\s*#([\d,]+)'
            ]
            
            for pattern in bsr_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    try:
                        bsr_num = int(match.replace(',', ''))
                        if 1 <= bsr_num <= 10000000:  # Reasonable BSR range
                            logger.info(f"Extracted BSR from page text: {bsr_num}")
                            return bsr_num
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.error(f"Error extracting BSR: {str(e)}")
        return None
            
    def _extract_description(self, soup) -> str:
        try:
            desc_elem = soup.find('div', {'id': 'productDescription'})
            return desc_elem.get_text().strip() if desc_elem else None
        except:
            return None
            
    def _extract_features(self, soup) -> List[str]:
        try:
            feature_list = soup.find('div', {'id': 'feature-bullets'})
            if feature_list:
                features = feature_list.find_all('span', {'class': 'a-list-item'})
                return [f.get_text().strip() for f in features]
            return []
        except:
            return []
            
    def _extract_images_count(self, soup) -> int:
        try:
            thumbs = soup.find_all('li', {'class': 'image'})
            return len(thumbs)
        except:
            return 0
            
    def _analyze_competition(self, product: Dict):
        try:
            # Set default values first
            product['competition_score'] = 5.0
            product['price_trend'] = 'Stable'
            product['demand_trend'] = 'Stable'
            product['competition_trend'] = 'Stable'
            
            if not product or not isinstance(product, dict):
                return
                
            # Initialize competition score (lower is better)
            score = 5.0  # Start at middle
            
            # Factor 1: Number of sellers
            seller_info = product.get('seller_info') or {}
            if seller_info and isinstance(seller_info, dict):
                total_sellers_raw = seller_info.get('total_sellers')
                try:
                    total_sellers = int(total_sellers_raw) if total_sellers_raw is not None else 0
                except Exception:
                    total_sellers = 0
                if isinstance(total_sellers, (int, float)):
                    if total_sellers <= 3:
                        score -= 2  # Low competition
                    elif total_sellers >= 10:
                        score += 2  # High competition
                
            # Factor 2: Amazon presence
            if bool(seller_info.get('amazon_seller', False)):
                score += 1.5  # Harder to compete with Amazon
                
            # Factor 3: Price competition
            fba_prices = (seller_info.get('prices') or {}).get('fba', [])
            if fba_prices:
                price_range = max(fba_prices) - min(fba_prices)
                try:
                    base_price = float(product.get('price')) if product.get('price') is not None else 0.0
                except Exception:
                    base_price = 0.0
                if price_range > base_price * 0.3:  # More than 30% price spread
                    score += 1  # High price competition
                    
            # Factor 4: Reviews and ratings
            try:
                reviews = int(product.get('reviews')) if product.get('reviews') is not None else 0
            except Exception:
                reviews = 0
            if reviews > 1000:
                score += 1  # Established products
            elif reviews < 100:
                score -= 1  # New opportunity
                
            # Factor 5: BSR position
            try:
                bsr = int(product.get('bsr')) if product.get('bsr') is not None else 0
            except Exception:
                bsr = 0
            if bsr and bsr < 1000:
                score += 1  # Top sellers are harder to compete with
                
            # Normalize score between 0-10
            product['competition_score'] = max(0, min(10, score))
            
            # Add trend data
            product['price_trend'] = self._analyze_price_trend(product['asin'])
            product['demand_trend'] = self._analyze_demand_trend(product['asin'])
            product['competition_trend'] = self._analyze_seller_trend(product['asin'])
            
        except Exception as e:
            logger.error(f"Error analyzing competition: {str(e)}")
            product['competition_score'] = 5.0  # Default to middle
            product['price_trend'] = 'Stable'
            product['demand_trend'] = 'Stable'
            product['competition_trend'] = 'Stable'

    def _estimate_sales_from_bsr(self, bsr: int, category: str) -> int:
        """
        Estimate monthly sales using a logarithmic regression model.
        Formula: Sales = C * (BSR ^ -k)
        """
        try:
            if not bsr or bsr <= 0:
                return 0
                
            # Category Constants (C, k)
            category_curves = {
                "Health & Household": (60000, 0.4),
                "Home & Kitchen": (50000, 0.4),
                "Beauty & Personal Care": (55000, 0.4),
                "Sports & Outdoors": (40000, 0.4),
                "Pet Supplies": (45000, 0.4),
                "Toys & Games": (45000, 0.45),
                "Electronics": (35000, 0.35),
                "default": (40000, 0.4)
            }
            
            C, k = category_curves.get(category, category_curves["default"])
            
            if bsr < 100:
                # Top 100 is often linear or exponential
                estimated_sales = 3000 + (100 - bsr) * 50
            else:
                import math
                estimated_sales = int(C * math.pow(bsr, -k))
                
            estimated_sales = min(estimated_sales, 50000)
            return max(0, int(estimated_sales))
            
        except Exception:
            return 0

    def _calculate_fba_fees(self, price: float, dimensions: Optional[Dict] = None) -> float:
        # Simple FBA fee estimation
        try:
            if not dimensions:
                # Default to small-standard size if dimensions unknown
                return max(2.50, price * 0.15)
                
            # Calculate based on product size
            volume = dimensions.get('length', 0) * dimensions.get('width', 0) * dimensions.get('height', 0)
            
            if volume < 20*8*4:  # Small standard-size
                return max(2.50, price * 0.15)
            elif volume < 18*14*8:  # Large standard-size
                return max(3.48, price * 0.15)
            else:  # Oversized
                return max(5.42, price * 0.15)
                
        except Exception:
            return price * 0.15  # Default to 15% if calculation fails

    def _count_keywords(self, text: str) -> int:
        # Count relevant keywords in text
        important_keywords = [
            'best', 'premium', 'professional', 'quality', 'new',
            'improved', 'authentic', 'original', 'official', 'genuine'
        ]
        return sum(1 for keyword in important_keywords if keyword.lower() in text.lower())

    def _analyze_seasonality(self, asin: str) -> List[str]:
        # Determine product seasonality (simplified)
        try:
            # This would normally use historical data
            # For now, return a simple default
            return ['All Year']
        except Exception:
            return ['All Year']

    def _analyze_price_trend(self, asin: str) -> str:
        # Analyze price trends (simplified)
        try:
            # This would normally analyze historical price data
            return 'Stable'
        except Exception:
            return 'Stable'

    def _analyze_demand_trend(self, asin: str) -> str:
        # Analyze demand trends (simplified)
        try:
            # This would normally analyze historical BSR and sales data
            return 'Stable'
        except Exception:
            return 'Stable'

    def _analyze_seller_trend(self, asin: str) -> str:
        # Analyze competition trends (simplified)
        try:
            # This would normally analyze historical seller data
            return 'Stable'
        except Exception:
            return 'Stable'

    def _estimate_search_volume(self, title: str) -> int:
        # Estimate monthly search volume using heuristics
        try:
            base_volume = 1000
            keyword_score = len(title.split())
            if keyword_score < 5:
                base_volume += 5000 # Head terms
            elif keyword_score < 10:
                base_volume += 2000
            return random.randint(base_volume, base_volume * 2)
        except Exception:
            return 0

    def _calculate_market_share(self, product: Dict) -> float:
        # Handled in search_products post-processing
        return product.get('market_share', 0.0)