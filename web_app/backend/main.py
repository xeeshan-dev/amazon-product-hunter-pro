from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
import asyncio
import logging

# Add src path to system path to import existing modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))  # amazon_hunter root
src_path = os.path.join(parent_dir, 'src')
sys.path.append(src_path)

# Import your existing tools
from scraper.amazon_scraper import AmazonScraper
from analysis.enhanced_scoring import EnhancedOpportunityScorer
from analysis.fba_calculator import FBAFeeCalculator
from risk.brand_risk import BrandRiskChecker
from risk.hazmat_detector import HazmatDetector
from analysis.keyword_tool import FreeKeywordTool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Amazon Hunter API", version="2.0")

# CORS middleware
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

# Input Models
class SearchRequest(BaseModel):
    keyword: str
    marketplace: str = "US"
    pages: int = 1
    min_rating: float = 3.0
    skip_risky_brands: bool = True
    skip_hazmat: bool = True
    # Advanced filter parameters
    skip_amazon_seller: bool = True
    skip_brand_seller: bool = True
    min_margin: float = 20.0
    min_sales: int = 50
    max_sales: int = 1000
    fetch_seller_info: bool = True

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0"}

@app.post("/api/search")
async def search_products(request: SearchRequest):
    try:
        logger.info(f"Search request: {request.keyword} (filters: amazon_seller={request.skip_amazon_seller}, brand_seller={request.skip_brand_seller}, sales={request.min_sales}-{request.max_sales})")
        
        # Marketplace URLs
        marketplace_urls = {
            "US": "https://www.amazon.com",
            "UK": "https://www.amazon.co.uk",
            "DE": "https://www.amazon.de"
        }
        
        # Scrape products
        scraper = AmazonScraper(base_url=marketplace_urls.get(request.marketplace))
        products = scraper.search_products(request.keyword, pages=request.pages)
        
        logger.info(f"Found {len(products)} products")
        
        # Process products
        processed_results = []
        total_market_revenue = 0
        
        # REMOVED: seller_info_fetch_count limit
        # We now fetch seller info for ALL products if filters are active

        # First pass: Scoring and Revenue
        for product in products:
            # 1. Rating Filter
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
            
            # Risk Checks
            brand_risk = tools['brand_checker'].check_brand(product.get('brand', ''), product.get('title', ''))
            product['risks'] = {
                'brand_risk': brand_risk.risk_level.value,
                'brand_reason': brand_risk.reason
            }
            
            # 2. Brand Risk Filter
            if request.skip_risky_brands and brand_risk.is_veto:
                continue
            
            hazmat = tools['hazmat'].check_product(product)
            product['risks']['hazmat'] = hazmat.is_hazmat
            product['risks']['hazmat_category'] = hazmat.category.value if hazmat.category else None

            # 3. Hazmat Filter
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
            
            # Estimated Profit
            cogs = price * 0.25 # Assumption
            net = price - fees.total_amazon_fees - cogs
            product['est_profit'] = net
            product['margin'] = (net / price * 100) if price > 0 else 0
            
            # 4. Margin Filter
            if product['margin'] < request.min_margin:
                continue
            
            # 5. Sales Range Filter
            if sales < request.min_sales or sales > request.max_sales:
                continue
            
            # 6. Fetch Seller Info (CONDITIONAL - only when filters need it)
            # ⭐ KEY CHANGE: No more 25-product limit when filters are active
            if request.skip_amazon_seller or request.skip_brand_seller:
                # If seller filters are active, fetch ALL seller info
                try:
                    asin = product.get('asin')
                    if asin:
                        seller_summary = scraper.get_seller_summary(asin)
                        product['seller_info'] = seller_summary
                        
                        # Extract brand if not available
                        brand = product.get('brand', '')
                        if not brand:
                            title = product.get('title', '')
                            brand = title.split(' ')[0] if title else ''
                        product['brand'] = brand
                        
                        logger.debug(f"[{asin}] seller='{seller_summary.get('seller_name')}' brand='{brand}'")
                        
                        # Rate limiting delay
                        import time, random
                        time.sleep(random.uniform(0.3, 0.7))
                except Exception as e:
                    logger.warning(f"Failed to fetch seller info for {asin}: {e}")
                    product['seller_info'] = {'amazon_seller': False, 'total_sellers': 0, 'seller_name': None}
            else:
                # Filters OFF - skip seller info for speed
                product['seller_info'] = {'amazon_seller': False, 'total_sellers': 0, 'seller_name': None}
            
            # 7. Skip Amazon Seller Filter
            if request.skip_amazon_seller and product.get('seller_info', {}).get('amazon_seller', False):
                logger.info(f"Skipping product {product.get('asin')} - Amazon is seller")
                continue
            
            # 8. Skip Brand as Seller Filter
            if request.skip_brand_seller:
                seller_name = product.get('seller_info', {}).get('seller_name', '') or ''
                brand = product.get('brand', '') or ''
                
                if seller_name and brand:
                    seller_lower = seller_name.lower()
                    brand_lower = brand.lower()
                    if brand_lower in seller_lower or seller_lower in brand_lower:
                        logger.info(f"Skipping product {product.get('asin')} - Seller '{seller_name}' matches brand '{brand}'")
                        continue
            
            processed_results.append(product)
            
        # Second pass: Market Share
        for p in processed_results:
            if total_market_revenue > 0:
                p['market_share'] = (p['est_revenue'] / total_market_revenue) * 100
            else:
                p['market_share'] = 0
                
        # Sorting by Revenue
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
    uvicorn.run(app, host="0.0.0.0", port=8001)
