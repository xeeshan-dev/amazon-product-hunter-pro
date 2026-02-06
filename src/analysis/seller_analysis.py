import logging
from typing import Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SellerInfo:
    fba_count: int = 0
    fbm_count: int = 0
    amazon_seller: bool = False
    total_sellers: int = 0
    prices: Dict[str, float] = None
    seller_name: str = None  # ← ADDED
    brand_is_seller: bool = False  # ← ADDED

    def __post_init__(self):
        if self.prices is None:
            self.prices = {
                'fba': [],
                'fbm': [],
                'amazon': None
            }

class SellerAnalyzer:
    def _is_amazon_name(self, name: str) -> bool:
        try:
            if not name:
                return False
            n = str(name).strip().lower()
            amazon_indicators = [
                'amazon.com', 'amazon', 'sold by amazon', 'amazon.com services',
                'amazon.com services llc', 'amazon services llc', 'amazon eu sarl',
                'amazon.com.ca', 'amazon.co.uk', 'amazon.de', 'amazon.fr',
                'amazon.it', 'amazon.es', 'amazon.nl', 'amazon.se', 'amazon.pl',
                'amazon.com.au', 'amazon.co.jp', 'amazon.in', 'amazon.com.mx',
                'amazon.com.br', 'amazon.ca', 'amazon.co.uk', 'amazon.de',
                'amazon.fr', 'amazon.it', 'amazon.es', 'amazon.nl', 'amazon.se',
                'amazon.pl', 'amazon.com.au', 'amazon.co.jp', 'amazon.in',
                'amazon.com.mx', 'amazon.com.br', 'amazon marketplace',
                'amazon fulfillment', 'amazon logistics', 'amazon retail'
            ]
            return any(k in n for k in amazon_indicators)
        except Exception:
            return False
    
    def _extract_buy_box_seller_name(self, soup) -> str:
        """Extract the Buy Box seller name from product page"""
        import re
        from typing import Optional
        
        try:
            # Method 1: merchant-info div
            merchant_div = soup.find('div', {'id': 'merchant-info'})
            if merchant_div:
                text = merchant_div.get_text()
                match = re.search(r'Sold by\s+([^\n.]+)', text)
                if match:
                    seller = match.group(1).strip()
                    seller = re.sub(r'\s+and\s+Fulfilled.*$', '', seller, flags=re.IGNORECASE)
                    if seller and not self._is_amazon_name(seller):
                        return seller
            
            # Method 2: sellerProfileTriggerId
            seller_link = soup.find('a', {'id': 'sellerProfileTriggerId'})
            if seller_link:
                seller = seller_link.get_text().strip()
                if not self._is_amazon_name(seller):
                    return seller
            
            # Method 3: Search for "Ships from and sold by"
            for elem in soup.find_all(['div', 'span']):
                text = elem.get_text()
                if 'Sold by' in text or 'Ships from and sold by' in text:
                    match = re.search(r'(?:sold by|Ships from and sold by)\s+([^\n.]+)', text, re.IGNORECASE)
                    if match:
                        seller = match.group(1).strip()
                        seller = re.sub(r'\s+and\s+.*$', '', seller, flags=re.IGNORECASE)
                        if seller and not self._is_amazon_name(seller):
                            return seller
            
            return None
        except Exception as e:
            logger.error(f"Error extracting seller name: {e}")
            return None
    
    def analyze_sellers(self, soup, asin: str = None, headers: dict = None, session=None, referer: str = None) -> SellerInfo:
        # Initialize seller info
        seller_info = SellerInfo()
        
        # First check the Buy Box seller
        try:
            if soup is None:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup('', 'html.parser')
            buy_box_info = self._analyze_buy_box_seller(soup)
        except Exception:
            buy_box_info = {'is_amazon': False, 'price': None, 'fulfillment': None}
        seller_info.amazon_seller = buy_box_info['is_amazon']
        
        # Extract seller name
        seller_info.seller_name = self._extract_buy_box_seller_name(soup)
        logger.debug(f"[ASIN {asin}] Extracted seller name: {seller_info.seller_name}")
        
        # Then analyze all sellers using sprite/AOD and fallbacks
        other_sellers = []
        try:
            # Prefer All Offers Display (AOD) sprite or AJAX endpoint
            sprite_content = self._get_sprite_content_from_soup_or_ajax(
                soup, asin=asin, headers=headers, session=session, referer=referer
            )
            if sprite_content:
                other_sellers = self._parse_sprite_sellers(sprite_content)
        except Exception as e:
            logger.error(f"Error using AOD sprite: {str(e)}")
        
        # Fallback to scanning page sections if no sellers found
        if not other_sellers:
            other_sellers = self._analyze_other_sellers(soup)
            
        # If still no sellers found, try to get basic seller info from main page
        if not other_sellers and asin:
            other_sellers = self._get_sellers_from_main_page(asin, headers, session)
        
        # Combine the information
        seller_info.fba_count = len([s for s in other_sellers if s.get('fulfillment') == 'FBA'])
        seller_info.fbm_count = len([s for s in other_sellers if s.get('fulfillment') == 'FBM'])
        seller_info.total_sellers = len(other_sellers) + 1  # +1 for buy box seller

        # Amazon presence: buy box OR any seller named Amazon
        amazon_in_offers = any(self._is_amazon_name(s.get('seller_name')) for s in other_sellers)
        seller_info.amazon_seller = bool(buy_box_info.get('is_amazon')) or amazon_in_offers
        
        # Debug logging
        if buy_box_info.get('is_amazon'):
            logger.info(f"Amazon detected in buy box for ASIN {asin}")
        if amazon_in_offers:
            amazon_sellers = [s.get('seller_name') for s in other_sellers if self._is_amazon_name(s.get('seller_name'))]
            logger.info(f"Amazon detected in other offers for ASIN {asin}: {amazon_sellers}")
        logger.info(f"Final Amazon seller status for ASIN {asin}: {seller_info.amazon_seller}")

        # Get price information (numeric only)
        seller_info.prices = {
            'fba': [s.get('price') for s in other_sellers if s.get('fulfillment') == 'FBA' and isinstance(s.get('price'), (int, float))],
            'fbm': [s.get('price') for s in other_sellers if s.get('fulfillment') == 'FBM' and isinstance(s.get('price'), (int, float))],
            'amazon': buy_box_info.get('price') if buy_box_info.get('is_amazon') else None
        }
        
        return seller_info
    
    def _analyze_buy_box_seller(self, soup) -> dict:
        result = {'is_amazon': False, 'price': None, 'fulfillment': None}
        
        try:
            # Conservative Amazon seller detection (avoid false positives)
            def has_text(selector_text: str) -> bool:
                return soup.find(text=lambda t: t and selector_text in t.lower()) is not None
            
            # Also check specific elements that commonly contain seller info
            def has_seller_text(selector_text: str) -> bool:
                seller_elements = [
                    soup.find('div', {'id': 'merchant-info'}),
                    soup.find('div', {'id': 'seller-info'}),
                    soup.find('span', {'id': 'merchant-info'}),
                    soup.find('span', {'id': 'seller-info'}),
                    soup.find('div', {'class': 'a-section a-spacing-small'}),
                    soup.find('div', {'class': 'a-section a-spacing-mini'})
                ]
                for elem in seller_elements:
                    if elem and selector_text in elem.get_text().lower():
                        return True
                return False

            amazon_phrases = [
                'ships from and sold by amazon',
                'sold by amazon.com',
                'amazon.com services llc',
                'sold by: amazon.com',
                'ships from and sold by amazon.com',
                'sold by amazon',
                'amazon.com services',
                'amazon services llc',
                'amazon eu sarl',
                'amazon marketplace',
                'amazon fulfillment',
                'amazon logistics',
                'amazon retail',
                'ships from amazon',
                'sold by: amazon',
                'amazon.com, inc.',
                'amazon.com inc',
                'amazon digital services',
                'amazon digital services llc'
            ]
            result['is_amazon'] = any(has_text(p) for p in amazon_phrases) or any(has_seller_text(p) for p in amazon_phrases)
            
            # Check for FBA fulfillment
            fba_indicators = [
                soup.find(text=lambda t: t and 'fulfilled by amazon' in str(t).lower()),
                soup.find('i', {'class': ['a-icon-prime', 'a-icon-premium']}),
                soup.find('span', {'class': ['a-icon-prime', 'a-icon-premium']}),
                soup.find(lambda tag: tag.name in ['span', 'div', 'p'] and
                                    tag.string and
                                    'prime' in tag.get('class', [''])[0].lower())
            ]
            
            result['fulfillment'] = 'FBA' if any(indicator for indicator in fba_indicators if indicator) else 'FBM'
            
            # Get price from multiple locations
            price_selectors = [
                {'tag': 'span', 'attrs': {'id': ['price_inside_buybox', 'priceblock_ourprice', 'newBuyBoxPrice']}},
                {'tag': 'span', 'attrs': {'class': 'a-price-whole'}},
                {'tag': 'span', 'attrs': {'class': 'a-color-price'}},
                {'tag': 'span', 'attrs': {'class': 'a-offscreen'}},
                {'tag': 'span', 'attrs': {'class': 'a-price'}},
                {'tag': 'span', 'attrs': {'id': 'price'}}
            ]
            
            for selector in price_selectors:
                price_elem = soup.find(selector['tag'], selector['attrs'])
                if price_elem:
                    try:
                        price_text = price_elem.get_text().strip()
                        # Remove any currency symbols and clean up
                        price = float(''.join(filter(lambda x: x.isdigit() or x == '.', price_text)))
                        if price > 0:
                            result['price'] = price
                            break
                    except:
                        continue
                
        except Exception as e:
            logger.error(f"Error analyzing Buy Box seller: {str(e)}")
            
        return result

    def _analyze_other_sellers(self, soup) -> list:
        sellers = []
        
        try:
            # First try to find the seller sprite iframe
            sprite_iframe = soup.find('iframe', {'id': 'all-offers-display-scroller'})
            if sprite_iframe:
                # If iframe found, we need to get its content
                sprite_content = self._get_sprite_content(sprite_iframe.get('src'))
                if sprite_content:
                    return self._parse_sprite_sellers(sprite_content)
            
            # Fallback to looking in multiple sections for seller info
            seller_sections = [
                # Main other sellers section
                soup.find('div', {'id': ['aod-offer-list', 'olp_feature_div']}),
                # More buying choices section
                soup.find('div', {'id': ['mbc', 'mbc-offers-container']}),
                # Secondary sections
                soup.find('div', {'id': ['other-sellers', 'bottomSlotAnchor']}),
                # Optional sections that might contain seller info
                soup.find('div', {'class': ['a-box-group', 'a-spacing-small']})
            ]
            
            for section in seller_sections:
                if not section:
                    continue
                    
                # Find seller entries in this section
                seller_entries = section.find_all(['div', 'span', 'li'], {
                    'class': [
                        'aod-offer', 'olp-new', 'mbc-offer-row',
                        'pa_mbc_on_amazon_offer', 'a-spacing-mini',
                        'olpOffer', 'mbcOfferRow'
                    ]
                })
                
                for entry in seller_entries:
                    seller_info = {'fulfillment': 'FBM', 'price': None}
                    
                    # Check for FBA/Prime indicators
                    fba_indicators = [
                        # Prime badge
                        entry.find('i', {'class': ['a-icon-prime', 'a-icon-premium']}),
                        # FBA text
                        entry.find(text=lambda t: t and 'fulfilled by amazon' in str(t).lower()),
                        # Prime logo
                        entry.find('span', {'aria-label': lambda x: x and 'prime' in x.lower()}),
                        # Prime eligible text
                        entry.find(text=lambda t: t and 'prime eligible' in str(t).lower()),
                        # Prime icon
                        entry.find('i', {'aria-label': lambda x: x and 'prime' in x.lower()})
                    ]
                    
                    if any(indicator for indicator in fba_indicators if indicator):
                        seller_info['fulfillment'] = 'FBA'
                    
                    # Try to find price in multiple formats
                    price_elements = [
                        # Standard price formats
                        entry.find(['span', 'div'], {'class': [
                            'a-price', 'olp-price', 'a-color-price',
                            'pa_mbc_on_amazon_price', 'a-size-large'
                        ]}),
                        # Whole price part
                        entry.find('span', {'class': 'a-price-whole'}),
                        # Any element with price-like text
                        entry.find(lambda tag: tag.name in ['span', 'div'] and
                                              tag.string and
                                              '$' in tag.string)
                    ]
                    
                    for price_elem in price_elements:
                        if price_elem:
                            try:
                                price_text = price_elem.get_text().strip()
                                # Extract price value and clean it
                                price = float(''.join(filter(lambda x: x.isdigit() or x == '.', price_text)))
                                if price > 0:
                                    seller_info['price'] = price
                                    sellers.append(seller_info)
                                    break
                            except:
                                continue
                            
        except Exception as e:
            print(f"Error analyzing other sellers: {str(e)}")
            
        return sellers

    def _get_sprite_content_from_soup_or_ajax(self, soup, asin: str = None, headers: dict = None, session=None, referer: str = None) -> str:
        """
        Try to retrieve seller sprite (AOD) HTML via iframe src, AJAX, or offer-listing page.
        This is faster than parsing the main product page.
        """
        if not asin or not session:
            return None
            
        try:
            import requests
            sess = session or requests.Session()
            req_headers = headers.copy() if headers else {}
            
            # Amazon's All Offers Display AJAX endpoint (recommended)
            aod_url = f"https://www.amazon.com/gp/aod/ajax/ref=dp_aod_NEW_mbc?asin={asin}"
            
            # Enhanced headers to mimic real browser behavior
            req_headers.update({
                'Accept': 'text/html,*/*',
                'Referer': referer or f'https://www.amazon.com/dp/{asin}',
                'X-Requested-With': 'XMLHttpRequest',
                'accept-language': 'en-US,en;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1'
            })

            # Set location/locale cookies so Prime badges render
            try:
                sess.cookies.set('i18n-prefs', 'USD', domain='.amazon.com')
                sess.cookies.set('lc-main', 'en_US', domain='.amazon.com')
                # Use a common US ZIP to surface Prime (e.g., Los Angeles 90001)
                sess.cookies.set('x-amz-aod-zip', '90001', domain='.amazon.com')
            except Exception:
                pass

            # Try primary AOD endpoint first
            try:
                response = sess.get(aod_url, headers=req_headers, timeout=10)
                
                if response.status_code == 200:
                    logger.debug(f"[{asin}] Successfully fetched AOD data")
                    return response.text
                else:
                    logger.warning(f"[{asin}] AOD endpoint returned {response.status_code}")
            except Exception as e:
                logger.error(f"[{asin}] Error fetching AOD data: {e}")

            # Fallback: Try multiple AOD endpoints
            if asin:
                aod_endpoints = [
                    # Standard endpoints
                    f'https://www.amazon.com/gp/aod/ajax?asin={asin}',
                    f'https://www.amazon.com/gp/aod/ajax/ref=dp_aod?asin={asin}',
                    f'https://www.amazon.com/gp/aod/ajax/ref=dp_aod_all?asin={asin}',
                    f'https://www.amazon.com/gp/aod/ajax/ref=dp_aod_new?asin={asin}',
                    # Prime-eligible variants to expose FBA offers
                    f'https://www.amazon.com/gp/aod/ajax?asin={asin}&isPrimeEligible=true',
                    f'https://www.amazon.com/gp/aod/ajax/ref=dp_aod?asin={asin}&isPrimeEligible=true',
                ]
                
                for endpoint in aod_endpoints:
                    try:
                        resp = sess.get(endpoint, headers=req_headers, timeout=10)
                        if resp.ok and resp.text:
                            logger.debug(f"[{asin}] Fetched from fallback: {endpoint}")
                            # Check for various offer indicators
                            if any(indicator in resp.text for indicator in ['aod-offer', 'olpOffer', 'offer', 'seller', 'prime']):
                                return resp.text
                    except Exception as e:
                        logger.debug(f"Failed to fetch from {endpoint}: {str(e)}")
                        continue

            # Look for iframe on the page
            if soup:
                sprite_iframe = soup.find('iframe', {'id': 'all-offers-display-scroller'})
                if sprite_iframe and sprite_iframe.get('src'):
                    url = sprite_iframe.get('src')
                    if url.startswith('/'):
                        url = f'https://www.amazon.com{url}'
                    try:
                        resp = sess.get(url, headers=req_headers, timeout=10)
                        if resp.ok and resp.text:
                            return resp.text
                    except Exception as e:
                        logger.debug(f"Failed to fetch iframe content: {str(e)}")

            # Fallback to offer-listing page
            if asin:
                offer_url = f'https://www.amazon.com/gp/offer-listing/{asin}'
                try:
                    resp = sess.get(offer_url, headers=req_headers, timeout=10)
                    if resp.ok and resp.text:
                        return resp.text
                except Exception as e:
                    logger.debug(f"Failed to fetch offer-listing page: {str(e)}")

        except Exception as e:
            logger.error(f"Error getting AOD/offers content: {str(e)}")
            
        return None
            
    def _parse_sprite_sellers(self, content: str) -> list:
        """Parse seller information from AOD sprite or offer-listing HTML."""
        from bs4 import BeautifulSoup
        sellers = []
        try:
            soup = BeautifulSoup(content, 'html.parser')

            # Enhanced AOD structure detection with multiple selectors
            offers = []
            
            # Try multiple selectors for different Amazon structures
            offer_selectors = [
                'div.aod-offer',
                'div[class*="aod-offer"]',
                'div.olpOffer',
                'div[class*="olpOffer"]',
                'li.olpOfferRow',
                'div[class*="olpOfferRow"]',
                'div.mbc-offer-row',
                'div[class*="mbc-offer"]',
                'div[class*="offer"]',
                'div[class*="seller"]',
                'div[class*="prime"]',
                'div[data-testid*="offer"]',
                'div[data-testid*="seller"]'
            ]
            
            for selector in offer_selectors:
                found_offers = soup.select(selector)
                if found_offers:
                    offers = found_offers
                    logger.info(f"Found {len(offers)} seller offers using selector: {selector}")
                    break
            
            # If no offers found with selectors, try broader search
            if not offers:
                # Look for any div/li that might contain seller info
                potential_offers = soup.find_all(['div', 'li'], {
                    'class': lambda x: x and any(keyword in x.lower() for keyword in 
                        ['offer', 'seller', 'prime', 'aod', 'olp', 'mbc'])
                })
                if potential_offers:
                    offers = potential_offers
                    logger.info(f"Found {len(offers)} potential seller offers using broad search")

            logger.info(f"Total offers to parse: {len(offers)}")
            
            for offer in offers:
                seller_info = {'fulfillment': 'FBM', 'price': None, 'seller_name': None}

                # Enhanced price detection with multiple selectors
                price_selectors = [
                    'span.a-price-whole',
                    'span.a-offscreen', 
                    'span.a-color-price',
                    'span.olpOfferPrice',
                    'span.a-price',
                    'span.pa_mbc_on_amazon_price',
                    'div.a-price-whole',
                    'div.a-offscreen',
                    'span[class*="price"]',
                    'div[class*="price"]',
                    'span[class*="cost"]',
                    'div[class*="cost"]'
                ]
                
                price_elem = None
                for selector in price_selectors:
                    price_elem = offer.select_one(selector)
                    if price_elem:
                        break
                
                # Fallback: find any element with price-like text
                if not price_elem:
                    price_elem = offer.find(lambda tag: tag.name in ['span', 'div'] and 
                                          tag.get_text() and 
                                          '$' in tag.get_text() and
                                          any(char.isdigit() for char in tag.get_text()))

                if price_elem:
                    try:
                        price_text = price_elem.get_text().strip()
                        # Clean price text - remove currency symbols and extract number
                        import re
                        # More flexible price regex
                        price_patterns = [
                            r'\$?([\d,]+\.?\d*)',  # $123.45 or 123.45
                            r'([\d,]+\.?\d*)\s*\$',  # 123.45 $
                            r'([\d,]+\.?\d*)',  # Just numbers
                        ]
                        
                        for pattern in price_patterns:
                            price_match = re.search(pattern, price_text.replace(',', ''))
                            if price_match:
                                price = float(price_match.group(1))
                                if price > 0:
                                    seller_info['price'] = price
                                    break
                    except Exception as e:
                        logger.debug(f"Error parsing price: {str(e)}")
                
                # If still no price, try to extract from the entire offer text
                if not seller_info['price']:
                    try:
                        offer_text = offer.get_text()
                        import re
                        price_matches = re.findall(r'\$?([\d,]+\.?\d*)', offer_text)
                        for match in price_matches:
                            try:
                                price = float(match.replace(',', ''))
                                if 0.01 <= price <= 10000:  # Reasonable price range
                                    seller_info['price'] = price
                                    break
                            except:
                                continue
                    except Exception as e:
                        logger.debug(f"Error extracting price from offer text: {str(e)}")

                # Enhanced FBA/Prime detection with current Amazon indicators
                fba_indicators = [
                    # Prime badges and icons (updated selectors)
                    offer.find('i', {'class': lambda x: x and any(cls in x for cls in [
                        'a-icon-prime', 'a-icon-premium', 'a-icon-prime-day', 'prime', 'fba'
                    ])}),
                    offer.find('span', {'class': lambda x: x and any(cls in x for cls in [
                        'a-icon-prime', 'a-icon-premium', 'prime', 'fba', 'amazon'
                    ])}),
                    # SVG prime logos
                    offer.find('svg', {'aria-label': lambda x: x and 'prime' in x.lower()}),
                    offer.find('svg', {'class': lambda x: x and 'prime' in x.lower()}),
                    offer.find('span', {'aria-label': lambda x: x and any(phrase in x.lower() for phrase in [
                        'prime', 'fulfilled by amazon', 'fba', 'amazon prime'
                    ])}),
                    
                    # FBA text indicators (expanded)
                    offer.find(text=lambda t: t and any(phrase in t.lower() for phrase in [
                        'fulfilled by amazon', 'fba', 'amazon fba',
                        'prime eligible', 'prime delivery', 'amazon prime',
                        'ships from amazon', 'prime shipping', 'prime member'
                    ])),
                    
                    # Prime delivery badges (expanded)
                    offer.find('span', {'class': lambda x: x and any(cls in x for cls in [
                        'prime', 'fba', 'amazon', 'fulfilled'
                    ])}),
                    offer.find('div', {'class': lambda x: x and any(cls in x for cls in [
                        'prime', 'fba', 'amazon', 'fulfilled'
                    ])}),
                    
                    # Data attributes often present in AOD DOM
                    offer.find(attrs={'data-fulfillment': 'amazon'}),
                    offer.find(attrs={'data-fulfillment-method': 'amazon'}),
                    offer.find(attrs={'data-isprimeoffer': ['1', 'true']}),
                    offer.find(attrs={'data-prime': 'true'}),
                    offer.find(attrs={'data-fba': 'true'})
                ]
                
                # Check for FBA indicators
                has_fba_indicator = any(indicator for indicator in fba_indicators if indicator)
                
                # Additional text-based detection (expanded)
                offer_text = offer.get_text(' ').lower()
                fba_text_indicators = [
                    'fulfilled by amazon', 'fba', 'amazon fba',
                    'prime eligible', 'prime delivery', 'amazon prime',
                    'ships from amazon', 'prime shipping', 'prime member',
                    'amazon.com', 'sold by amazon', 'amazon seller'
                ]
                has_fba_text = any(indicator in offer_text for indicator in fba_text_indicators)
                
                # Check for Prime/FBA in class names
                offer_classes = ' '.join(offer.get('class', [])).lower()
                has_fba_class = any(cls in offer_classes for cls in ['prime', 'fba', 'amazon', 'fulfilled'])
                
                if has_fba_indicator or has_fba_text or has_fba_class:
                    seller_info['fulfillment'] = 'FBA'
                    logger.info(f"✅ FBA seller detected! Price: ${seller_info['price']}, Indicators: {has_fba_indicator}, Text: {has_fba_text}, Class: {has_fba_class}")
                else:
                    logger.debug(f"FBM seller detected. Price: ${seller_info['price']}, Indicators: {has_fba_indicator}, Text: {has_fba_text}, Class: {has_fba_class}")

                # Extract seller name if available (expanded selectors)
                seller_name_elem = (
                    offer.select_one('.aod-offer-soldBy a, .aod-offer-soldBy, .olpSellerName a, .olpSellerName, .aod-seller-name, [data-testid*="seller"]')
                    or offer.find(['span','div','a'], {'id': lambda x: x and 'soldby' in x.lower()})
                    or offer.find(['span','div','a'], {'class': lambda x: x and any(k in x.lower() for k in ['sold-by', 'seller', 'merchant'])})
                )
                if seller_name_elem:
                    seller_info['seller_name'] = seller_name_elem.get_text(strip=True)

                # Add sellers regardless of price (for testing FBA detection)
                sellers.append(seller_info)
                logger.debug(f"Added seller: {seller_info['fulfillment']} - ${seller_info['price']}")
                
        except Exception as e:
            logger.error(f"Error parsing sprite sellers: {str(e)}")
            
        logger.info(f"Parsed {len(sellers)} sellers: {len([s for s in sellers if s['fulfillment'] == 'FBA'])} FBA, {len([s for s in sellers if s['fulfillment'] == 'FBM'])} FBM")
        return sellers
    
    def _get_sellers_from_main_page(self, asin: str, headers: dict, session) -> list:
        """Fallback method to get basic seller info from main product page."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            sess = session or requests.Session()
            product_url = f"https://www.amazon.com/dp/{asin}"
            
            response = sess.get(product_url, headers=headers, timeout=10)
            if not response.ok:
                return []
                
            soup = BeautifulSoup(response.content, 'html.parser')
            sellers = []
            
            # Look for seller information on the main page
            # Check for "Other Sellers" section
            other_sellers_section = soup.find('div', {'id': 'olp_feature_div'}) or soup.find('div', {'id': 'aod-container'})
            
            if other_sellers_section:
                # Try to find seller offers in the main page
                offers = other_sellers_section.find_all(['div', 'li'], {
                    'class': lambda x: x and any(keyword in x.lower() for keyword in 
                        ['offer', 'seller', 'prime', 'aod', 'olp'])
                })
                
                for offer in offers:
                    seller_info = {'fulfillment': 'FBM', 'price': None, 'seller_name': None}
                    
                    # Try to extract price
                    price_elem = offer.find(['span', 'div'], {'class': lambda x: x and 'price' in x.lower()})
                    if price_elem:
                        try:
                            price_text = price_elem.get_text().strip()
                            import re
                            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                            if price_match:
                                price = float(price_match.group())
                                if price > 0:
                                    seller_info['price'] = price
                        except Exception:
                            pass
                    
                    # Check for FBA indicators
                    offer_text = offer.get_text(' ').lower()
                    if any(indicator in offer_text for indicator in ['prime', 'fba', 'amazon', 'fulfilled by amazon']):
                        seller_info['fulfillment'] = 'FBA'
                    
                    if seller_info['price']:
                        sellers.append(seller_info)
            
            # If no sellers found in other sellers section, create a basic seller entry
            if not sellers:
                # Check if Amazon is the seller (buy box)
                buy_box_section = soup.find('div', {'id': 'merchant-info'}) or soup.find('div', {'id': 'seller-info'})
                if buy_box_section:
                    buy_box_text = buy_box_section.get_text(' ').lower()
                    if 'amazon' in buy_box_text or 'prime' in buy_box_text:
                        # Create a basic FBA seller entry
                        sellers.append({
                            'fulfillment': 'FBA',
                            'price': None,
                            'seller_name': 'Amazon.com'
                        })
                    else:
                        # Create a basic FBM seller entry
                        sellers.append({
                            'fulfillment': 'FBM',
                            'price': None,
                            'seller_name': 'Other Seller'
                        })
            
            logger.info(f"Found {len(sellers)} sellers from main page: {len([s for s in sellers if s['fulfillment'] == 'FBA'])} FBA, {len([s for s in sellers if s['fulfillment'] == 'FBM'])} FBM")
            return sellers
            
        except Exception as e:
            logger.error(f"Error getting sellers from main page: {str(e)}")
            return []
    
    def meets_criteria(self, seller_info: SellerInfo, min_fba: int = 4, max_fba: int = 5, min_fbm: int = 2, max_fbm: int = 3, allow_amazon: bool = False) -> bool:
        # Require both FBA and FBM to be in specified ranges
        fba_ok = min_fba <= (seller_info.fba_count or 0) <= max_fba
        fbm_ok = min_fbm <= (seller_info.fbm_count or 0) <= max_fbm
        amazon_ok = True if allow_amazon else not bool(seller_info.amazon_seller)

        logger.info(
            f"Checking criteria: FBA {seller_info.fba_count} in [{min_fba},{max_fba}] => {fba_ok}, "
            f"FBM {seller_info.fbm_count} in [{min_fbm},{max_fbm}] => {fbm_ok}, "
            f"Amazon allowed={allow_amazon}, is Amazon={seller_info.amazon_seller} => {amazon_ok}"
        )

        return fba_ok and fbm_ok and amazon_ok