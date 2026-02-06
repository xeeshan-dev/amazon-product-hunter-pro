"""
Simple FastAPI backend for development (no Redis required)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import sys
import os
import logging
import time
import random

# Add src path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, os.path.join(parent_dir, 'src'))
sys.path.insert(0, parent_dir)

# Import analysis modules
from scraper.amazon_scraper import AmazonScraper
from analysis.enhanced_scoring import EnhancedOpportunityScorer
from analysis.fba_calculator import FBAFeeCalculator
from risk.brand_risk import BrandRiskChecker
from risk.hazmat_detector import HazmatDetector
from analysis.keyword_tool import FreeKeywordTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Amazon Hunter Pro API",
    version="2.0.0",
    description="Amazon product research API"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize tools
tools = {
    'scraper': AmazonScraper(),
    'scorer': EnhancedOpportunityScorer(),
    'fee_calc': FBAFeeCalculator(),
    'brand_checker': BrandRiskChecker(),
    'hazmat': HazmatDetector(),
    'keyword_tool': FreeKeywordTool()
}


# Helper function for brand extraction
import re

def extract_brand_from_title(title: str) -> str:
    """Extract brand from product title using multiple heuristics"""
    if not title:
        return ''
    
    title = title.strip()
    
    # Method 1: "by BrandName" pattern
    match = re.search(r'\bby\s+([A-Z][A-Za-z0-9&\-\s]{2,30})', title)
    if match:
        brand = match.group(1).strip()
        brand = re.sub(r'\s+(for|with|in|and|or|the)$', '', brand, flags=re.IGNORECASE)
        return brand
    
    # Method 2: All-caps at start
    match = re.match(r'^([A-Z][A-Z0-9&\-]{2,15})\s+', title)
    if match:
        return match.group(1)
    
    # Method 3: Title-case at start
    match = re.match(r'^([A-Z][a-z]+(?:[A-Z][a-z]+)*)\s+', title)
    if match:
        brand = match.group(1)
        if brand.lower() not in ['the', 'best', 'premium', 'new', 'improved', 'original']:
            return brand
    
    # Fallback: first word
    words = title.split()
    return re.sub(r'[^\w\-&]', '', words[0]) if words else ''


# Models
class SearchRequest(BaseModel):
    keyword: str
    marketplace: str = "US"
    pages: int = 1
    min_rating: float = 3.0
    skip_risky_brands: bool = True
    skip_hazmat: bool = True
    # New filter parameters
    skip_amazon_seller: bool = True
    skip_brand_seller: bool = True
    min_margin: float = 20.0
    min_sales: int = 50
    max_sales: int = 1000
    fetch_seller_info: bool = True  # Whether to fetch detailed seller info


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": "development"
    }


# Search endpoint
@app.post("/api/search")
async def search_products(request: SearchRequest):
    try:
        logger.info(f"Search request: {request.keyword} (filters: amazon_seller={request.skip_amazon_seller}, brand_seller={request.skip_brand_seller}, sales={request.min_sales}-{request.max_sales})")
        
        # Log seller info fetching strategy
        if request.skip_amazon_seller or request.skip_brand_seller:
            logger.info(f"🔍 Seller info fetching: ENABLED (will fetch for ALL products)")
        else:
            logger.info(f"⚡ Seller info fetching: DISABLED (faster search)")
        
        # Marketplace URLs
        marketplace_urls = {
            "US": "https://www.amazon.com",
            "UK": "https://www.amazon.co.uk",
            "DE": "https://www.amazon.de"
        }
        
        # Scrape
        scraper = AmazonScraper(base_url=marketplace_urls.get(request.marketplace))
        products = scraper.search_products(request.keyword, pages=request.pages)
        
        logger.info(f"Found {len(products)} products")
        
        # Process
        processed_results = []
        total_market_revenue = 0
        
        # REMOVED: seller_info_fetch_count limit
        # We now fetch seller info for ALL products if filters are active
        
        for product in products:
            # Rating filter
            rating = float(product.get('rating') or 0)
            if rating < request.min_rating:
                continue
            
            # Score
            score_result = tools['scorer'].calculate_score(product)
            product['enhanced_score'] = score_result.total_score
            product['score_breakdown'] = {
                'demand': score_result.demand_pillar.score,
                'competition': score_result.competition_pillar.score,
                'profit': score_result.profit_pillar.score
            }
            product['is_vetoed'] = score_result.is_vetoed
            product['veto_reasons'] = score_result.veto_details
            
            # Risk checks
            brand_risk = tools['brand_checker'].check_brand(
                product.get('brand', ''),
                product.get('title', '')
            )
            product['risks'] = {
                'brand_risk': brand_risk.risk_level.value,
                'brand_reason': brand_risk.reason
            }
            
            if request.skip_risky_brands and brand_risk.is_veto:
                continue
            
            hazmat = tools['hazmat'].check_product(product)
            product['risks']['hazmat'] = hazmat.is_hazmat
            product['risks']['hazmat_category'] = hazmat.category.value if hazmat.category else None
            
            if request.skip_hazmat and hazmat.is_veto:
                continue
            
            # Financials
            price = product.get('price', 0) or 0
            sales = product.get('estimated_sales', 0) or 0
            revenue = price * sales
            product['est_revenue'] = revenue
            total_market_revenue += revenue
            
            # Fees
            fees = tools['fee_calc'].calculate_all_fees(price, category=product.get('category'))
            product['fees_breakdown'] = {
                'referral': fees.referral_fee,
                'fba': fees.fba_fulfillment_fee,
                'storage': fees.monthly_storage_fee,
                'total': fees.total_amazon_fees
            }
            
            # Profit
            cogs = price * 0.25
            net = price - fees.total_amazon_fees - cogs
            product['est_profit'] = net
            product['margin'] = (net / price * 100) if price > 0 else 0
            
            # =========================================
            # NEW: Apply Margin Filter
            # =========================================
            if product['margin'] < request.min_margin:
                continue
            
            # =========================================
            # NEW: Apply Sales Range Filter
            # =========================================
            if sales < request.min_sales or sales > request.max_sales:
                continue
            
            # =========================================
            # NEW: Fetch Seller Info (BEFORE filtering, so we can filter by seller)
            # ⭐ KEY CHANGE: No more 25-product limit when filters are active
            # =========================================
            if request.skip_amazon_seller or request.skip_brand_seller:
                # If filters are active, we MUST fetch seller info for ALL products
                try:
                    asin = product.get('asin')
                    if asin:
                        seller_summary = scraper.get_seller_summary(asin)
                        product['seller_info'] = seller_summary
                        
                        # Extract brand from title if not available
                        brand = product.get('brand', '')
                        if not brand:
                            brand = extract_brand_from_title(product.get('title', ''))
                        product['brand'] = brand
                        
                        logger.debug(f"[{asin}] Fetched seller: {seller_summary.get('seller_name')}, brand: {brand}")
                        
                        # Add delay to avoid rate limiting (random 0.5-1.5s)
                        time.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    logger.warning(f"Failed to fetch seller info for {asin}: {e}")
                    product['seller_info'] = {'amazon_seller': False, 'total_sellers': 0, 'seller_name': None}
            else:
                # If filters are OFF, skip fetching seller info (faster)
                product['seller_info'] = {'amazon_seller': False, 'total_sellers': 0, 'seller_name': None}
            
            # =========================================
            # NEW: Apply Skip Amazon Seller Filter
            # =========================================
            if request.skip_amazon_seller and product.get('seller_info', {}).get('amazon_seller', False):
                logger.info(f"Skipping product {product.get('asin')} - Amazon is seller")
                continue
            
            # =========================================
            # NEW: Apply Skip Brand as Seller Filter
            # This checks if the seller name matches the brand name
            # =========================================
            if request.skip_brand_seller:
                seller_name = product.get('seller_info', {}).get('seller_name', '') or ''
                brand = product.get('brand', '') or ''
                
                if seller_name and brand and len(brand) >= 3:
                    seller_lower = seller_name.lower().strip()
                    brand_lower = brand.lower().strip()
                    
                    # Remove common business suffixes for better matching
                    seller_clean = re.sub(r'\b(llc|inc|corp|ltd|store|shop|official|direct|usa|us)\b', '', seller_lower, flags=re.IGNORECASE).strip()
                    brand_clean = re.sub(r'\b(llc|inc|corp|ltd|store|shop|official|direct|usa|us)\b', '', brand_lower, flags=re.IGNORECASE).strip()
                    
                    # Check if brand matches seller (multiple patterns)
                    if (brand_lower in seller_lower or
                        seller_lower in brand_lower or
                        (seller_clean and brand_clean and (brand_clean in seller_clean or seller_clean in brand_clean))):
                        logger.info(f"⛔ Filtered {product.get('asin')}: Brand=Seller (seller='{seller_name}' brand='{brand}')")
                        continue
            
            processed_results.append(product)
        
        # Market share
        for p in processed_results:
            if total_market_revenue > 0:
                p['market_share'] = (p['est_revenue'] / total_market_revenue) * 100
            else:
                p['market_share'] = 0
        
        # Sort by revenue
        processed_results.sort(key=lambda x: x.get('est_revenue', 0), reverse=True)
        
        return {
            "summary": {
                "total_products": len(processed_results),
                "total_revenue": total_market_revenue,
                "avg_revenue": total_market_revenue / len(processed_results) if processed_results else 0,
                "avg_sales": sum(p.get('estimated_sales', 0) for p in processed_results) / len(processed_results) if processed_results else 0
            },
            "results": processed_results[:50],
            "metadata": {
                "keyword": request.keyword,
                "marketplace": request.marketplace,
                "filters_applied": {
                    "min_rating": request.min_rating,
                    "min_margin": request.min_margin,
                    "sales_range": f"{request.min_sales}-{request.max_sales}",
                    "skip_amazon_seller": request.skip_amazon_seller,
                    "skip_brand_seller": request.skip_brand_seller
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Keywords endpoint
@app.get("/api/keywords")
async def get_keywords(q: str):
    try:
        suggestions = tools['keyword_tool'].get_autocomplete_suggestions(q)
        return {
            "keyword": q,
            "suggestions": [
                {
                    "keyword": s.keyword,
                    "source": s.source,
                    "relevance": s.relevance_score
                }
                for s in suggestions
            ]
        }
    except Exception as e:
        logger.error(f"Keyword search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
