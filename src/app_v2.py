"""
Amazon Product Hunter Pro v2.0
Enhanced with FREE tools:
- Brand Risk Detection (IP Claims)
- Hazmat Detection
- Keyword Research (Amazon Autocomplete)
- BSR Tracking
- Price History (CamelCamelCamel)
- Accurate FBA Fee Calculator
- 3-Pillar Opportunity Scoring with Veto Logic
"""

import streamlit as st
import pandas as pd
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.amazon_scraper import AmazonScraper
from analysis.scoring import ProductScorer
from analysis.sentiment import SentimentAnalyzer
from analysis.seller_analysis import SellerInfo
from analysis.market_analysis import MarketAnalyzer

# Import enhanced modules
from analysis.enhanced_scoring import EnhancedOpportunityScorer, ScoreStatus
from analysis.fba_calculator import FBAFeeCalculator, ProductDimensions
from analysis.bsr_tracker import BSRTracker
from analysis.keyword_tool import FreeKeywordTool
from risk.brand_risk import BrandRiskChecker, RiskLevel
from risk.hazmat_detector import HazmatDetector

import logging

# Configure page
st.set_page_config(
    page_title="Amazon Product Hunter Pro v2.0",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        margin: 0;
    }
    
    .main-header p {
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    .version-badge {
        background: rgba(255,255,255,0.2);
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #4f46e5;
        margin-bottom: 1rem;
    }
    
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        margin: 0;
        text-transform: uppercase;
    }
    
    .risk-badge-critical {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: 600;
        display: inline-block;
    }
    
    .risk-badge-high {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: 600;
        display: inline-block;
    }
    
    .risk-badge-safe {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: 600;
        display: inline-block;
    }
    
    .score-excellent {
        color: #10b981;
        font-weight: 700;
    }
    
    .score-good {
        color: #3b82f6;
        font-weight: 700;
    }
    
    .score-marginal {
        color: #f59e0b;
        font-weight: 700;
    }
    
    .score-poor {
        color: #ef4444;
        font-weight: 700;
    }
    
    .pillar-card {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    
    .pillar-title {
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    
    .veto-warning {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 600;
    }
    
    .product-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
    }
    
    .product-card * {
        color: #1e293b !important;
    }
    
    .success-message {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
    }
    
    .warning-message {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
    }
    
    .info-box {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize enhanced components
@st.cache_resource
def init_components():
    return {
        'brand_checker': BrandRiskChecker(),
        'hazmat_detector': HazmatDetector(),
        'fee_calculator': FBAFeeCalculator(),
        'enhanced_scorer': EnhancedOpportunityScorer(),
        'keyword_tool': FreeKeywordTool(),
        'bsr_tracker': BSRTracker(),
    }


def get_score_class(score: float) -> str:
    if score >= 80:
        return "score-excellent"
    elif score >= 60:
        return "score-good"
    elif score >= 40:
        return "score-marginal"
    else:
        return "score-poor"


def display_risk_badges(product: dict, components: dict):
    """Display IP and Hazmat risk badges."""
    brand = product.get('brand', '')
    title = product.get('title', '')
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Brand/IP Risk
        brand_result = components['brand_checker'].check_brand(brand, title)
        
        if brand_result.risk_level == RiskLevel.CRITICAL:
            st.markdown('<div class="risk-badge-critical">⛔ IP RISK: CRITICAL</div>', unsafe_allow_html=True)
            st.error(f"**{brand_result.reason}**")
        elif brand_result.risk_level == RiskLevel.HIGH:
            st.markdown('<div class="risk-badge-high">⚠️ IP RISK: HIGH</div>', unsafe_allow_html=True)
            st.warning(brand_result.reason)
        else:
            st.markdown('<div class="risk-badge-safe">✅ IP Risk: Low</div>', unsafe_allow_html=True)
    
    with col2:
        # Hazmat Risk
        hazmat_result = components['hazmat_detector'].check_product(product)
        
        if hazmat_result.is_veto:
            st.markdown('<div class="risk-badge-critical">⛔ HAZMAT: BLOCKED</div>', unsafe_allow_html=True)
            st.error(f"Category: {hazmat_result.category.value}")
        elif hazmat_result.is_hazmat:
            st.markdown('<div class="risk-badge-high">⚠️ HAZMAT: WARNING</div>', unsafe_allow_html=True)
            st.warning(f"Possible {hazmat_result.category.value} - verify with Amazon")
        else:
            st.markdown('<div class="risk-badge-safe">✅ Hazmat: Clear</div>', unsafe_allow_html=True)


def display_enhanced_score(product: dict, components: dict):
    """Display 3-pillar opportunity score."""
    scorer = components['enhanced_scorer']
    
    # Calculate enhanced score
    score_result = scorer.calculate_score(product)
    
    # Check for veto
    if score_result.is_vetoed:
        st.markdown(f'''
        <div class="veto-warning">
            ⛔ PRODUCT VETOED: {score_result.veto_details}
        </div>
        ''', unsafe_allow_html=True)
        return score_result
    
    # Display total score
    score_class = get_score_class(score_result.total_score)
    
    st.markdown(f'''
    <div style="text-align: center; margin: 1rem 0;">
        <span class="{score_class}" style="font-size: 3rem;">{score_result.total_score}</span>
        <span style="font-size: 1.5rem; color: #64748b;">/100</span>
        <p style="color: #64748b;">Opportunity Score ({score_result.status.value.upper()})</p>
        <p style="font-size: 0.8rem; color: #94a3b8;">Confidence: {score_result.confidence*100:.0f}%</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Display pillar breakdown
    st.markdown("### 📊 Score Breakdown")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f'''
        <div class="pillar-card">
            <div class="pillar-title">📈 Demand & Trend (40%)</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{score_result.demand_pillar.score}/100</div>
        </div>
        ''', unsafe_allow_html=True)
        for note in score_result.demand_pillar.notes:
            st.caption(note)
    
    with col2:
        st.markdown(f'''
        <div class="pillar-card">
            <div class="pillar-title">🏆 Competition (35%)</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{score_result.competition_pillar.score}/100</div>
        </div>
        ''', unsafe_allow_html=True)
        for note in score_result.competition_pillar.notes:
            st.caption(note)
    
    with col3:
        st.markdown(f'''
        <div class="pillar-card">
            <div class="pillar-title">💰 Profit & Risk (25%)</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{score_result.profit_pillar.score}/100</div>
        </div>
        ''', unsafe_allow_html=True)
        for note in score_result.profit_pillar.notes:
            st.caption(note)
    
    # Insights
    if score_result.strengths:
        st.success("**Strengths:** " + ", ".join(score_result.strengths))
    if score_result.weaknesses:
        st.warning("**Weaknesses:** " + ", ".join(score_result.weaknesses))
    if score_result.recommendations:
        st.info("**Recommendations:** " + " | ".join(score_result.recommendations))
    
    return score_result


def display_fee_breakdown(product: dict, components: dict):
    """Display accurate FBA fee breakdown."""
    calculator = components['fee_calculator']
    price = product.get('price', 0) or 0
    
    if price <= 0:
        st.warning("No price data available for fee calculation")
        return
    
    # Calculate fees
    fees = calculator.calculate_all_fees(price, category=product.get('category'))
    
    st.markdown("### 💵 FBA Fee Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Referral Fee", f"${fees.referral_fee:.2f}", 
                 delta=f"{fees.referral_fee_percentage*100:.0f}%")
    
    with col2:
        st.metric("FBA Fee", f"${fees.fba_fulfillment_fee:.2f}",
                 delta=fees.size_tier)
    
    with col3:
        st.metric("Storage (est)", f"${fees.monthly_storage_fee:.2f}",
                 delta="per month")
    
    with col4:
        st.metric("Total Fees", f"${fees.total_amazon_fees:.2f}",
                 delta=f"{(fees.total_amazon_fees/price*100):.0f}% of price")
    
    # Profit calculation
    cogs_estimate = price * 0.25  # Estimate COGS at 25%
    net_profit = price - fees.total_amazon_fees - cogs_estimate
    margin = (net_profit / price * 100) if price > 0 else 0
    
    if margin >= 30:
        st.success(f"💰 Est. Profit: ${net_profit:.2f} ({margin:.1f}% margin) - Good!")
    elif margin >= 20:
        st.info(f"💵 Est. Profit: ${net_profit:.2f} ({margin:.1f}% margin) - Acceptable")
    else:
        st.warning(f"⚠️ Est. Profit: ${net_profit:.2f} ({margin:.1f}% margin) - Low margin")
    
    if fees.notes:
        for note in fees.notes:
            st.caption(note)


def display_enhanced_results(products: list, components: dict):
    """Display products with enhanced analysis."""
    st.markdown("## 🏆 Product Analysis Results")
    
    if not products:
        st.warning("No products found. Try adjusting your search criteria.")
        return
    
    # Calculate scores for all products first
    scored_products = []
    total_revenue_market = 0
    
    for product in products:
        score_result = components['enhanced_scorer'].calculate_score(product)
        product['enhanced_score'] = score_result.total_score
        product['score_status'] = score_result.status.value
        product['is_vetoed'] = score_result.is_vetoed
        
        # Calculate revenue for market sizing
        price = product.get('price')
        if price is None:
            price = 0
        sales = product.get('estimated_sales', 0)
        product['est_revenue'] = price * sales
        total_revenue_market += product['est_revenue']
        
        scored_products.append(product)
    
    # Filter out vetoed products for stats
    viable_products = [p for p in scored_products if not p.get('is_vetoed')]
    
    # Market Overview
    st.markdown("### 📊 Market Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Market Revenue", f"${total_revenue_market:,.0f}")
    with col2:
        avg_revenue = total_revenue_market / len(products) if products else 0
        st.metric("Avg Revenue/Listing", f"${avg_revenue:,.0f}")
    with col3:
        avg_sales = sum(p.get('estimated_sales', 0) for p in products) / len(products) if products else 0
        st.metric("Avg Monthly Sales", f"{avg_sales:,.0f}")
    with col4:
        st.metric("Products Analyzed", len(products))
        
    # Market Share Chart (Revenue)
    if total_revenue_market > 0:
        cleaned_products = []
        for p in scored_products:
            title = p.get('title', 'Unknown')
            if len(title) > 30:
                title = title[:30] + '...'
            cleaned_products.append({
                'Product': title,
                'Revenue': p.get('est_revenue', 0)
            })
        
        # Limit to top 15 for chart clarity
        cleaned_products.sort(key=lambda x: x['Revenue'], reverse=True)
        top_products = cleaned_products[:15]
        
        st.bar_chart(pd.DataFrame(top_products).set_index('Product'))
    
    st.markdown("---")
    
    # Products Summary Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Products Found", len(products))
    with col2:
        st.metric("Viable Products", len(viable_products))
    with col3:
        vetoed_count = len([p for p in scored_products if p.get('is_vetoed')])
        st.metric("Vetoed (Risky)", vetoed_count)

    # Sort by Revenue (High to Low)
    scored_products.sort(key=lambda x: x.get('est_revenue', 0), reverse=True)
    
    # Display each product
    for i, product in enumerate(scored_products[:10], 1):
        with st.container():
            st.markdown(f'<div class="product-card">', unsafe_allow_html=True)
            
            # Title and rank
            title = product.get('title', 'Unknown Product')[:100]
            
            # Risk/Veto status
            if product.get('is_vetoed'):
                st.markdown(f"### #{i} {title} <span class='risk-badge-critical' style='font-size: 0.8rem; vertical-align: middle;'>⛔ VETOED</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"### #{i} {title}")
            
            # Risk badges
            display_risk_badges(product, components)
            
            # Quick metrics
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                price = product.get('price')
                st.metric("Price", f"${price:.2f}" if price else "N/A")
            with col2:
                st.metric("Rating", f"{product.get('rating', 0)}⭐")
            with col3:
                sales = product.get('estimated_sales', 0)
                st.metric("Est. Sales", f"{sales:,.0f}/mo")
            with col4:
                rev = product.get('est_revenue', 0)
                st.metric("Est. Rev", f"${rev:,.0f}")
            with col5:
                # Calculate real-time market share based on this result set
                share = (product.get('est_revenue', 0) / total_revenue_market * 100) if total_revenue_market > 0 else 0
                st.metric("Mkt Share", f"{share:.1f}%")
            with col6:
                bsr = product.get('bsr')
                st.metric("BSR", f"#{bsr:,}" if bsr else "N/A")
            
            # Expandable details
            with st.expander("📊 View Detailed Analysis"):
                display_enhanced_score(product, components)
                st.markdown("---")
                display_fee_breakdown(product, components)
            
            # Link
            st.markdown(f"🔗 [View on Amazon]({product.get('url', '#')})")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")


def keyword_research_tab(components: dict):
    """Keyword research tool tab."""
    st.markdown("## 🔑 Free Keyword Research")
    st.info("Uses Amazon's autocomplete API - no subscription needed!")
    
    keyword = st.text_input("Enter seed keyword", placeholder="e.g., dog leash")
    
    col1, col2 = st.columns(2)
    with col1:
        expand_alphabet = st.checkbox("Expand with A-Z", value=True)
    with col2:
        include_questions = st.checkbox("Include question keywords", value=False)
    
    if st.button("🔍 Get Keywords", use_container_width=True):
        if not keyword:
            st.warning("Please enter a keyword")
            return
        
        with st.spinner("Fetching keyword suggestions..."):
            tool = components['keyword_tool']
            
            if expand_alphabet:
                suggestions = tool.get_alphabet_suggestions(keyword)
            else:
                suggestions = tool.get_autocomplete_suggestions(keyword)
            
            if include_questions:
                suggestions.extend(tool.get_question_keywords(keyword))
            
            if suggestions:
                st.success(f"Found {len(suggestions)} keyword suggestions!")
                
                # Display as DataFrame
                df = pd.DataFrame([
                    {'Keyword': s.keyword, 'Source': s.source, 'Relevance': f"{s.relevance_score*100:.0f}%"}
                    for s in suggestions
                ])
                st.dataframe(df, use_container_width=True)
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Keywords CSV",
                    csv,
                    "keywords.csv",
                    "text/csv"
                )
            else:
                st.warning("No suggestions found. Try a different keyword.")


def bsr_tracker_tab(components: dict):
    """BSR tracking tool tab."""
    st.markdown("## 📈 BSR Tracker (Build Your Own History)")
    st.info("Track products over time to build your own historical data - FREE!")
    
    tracker = components['bsr_tracker']
    
    # Show current stats
    stats = tracker.get_tracking_stats()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Products Tracked", stats.get('total_asins_tracked', 0))
    with col2:
        st.metric("Total Snapshots", stats.get('total_snapshots', 0))
    with col3:
        st.metric("Oldest Data", stats.get('oldest_data', 'N/A')[:10] if stats.get('oldest_data') else 'N/A')
    
    st.markdown("---")
    
    # Add new product to track
    st.markdown("### Add Product to Track")
    asin_to_track = st.text_input("Enter ASIN to track", placeholder="B08XYZ123")
    
    col1, col2 = st.columns(2)
    with col1:
        bsr_input = st.number_input("Current BSR", min_value=1, value=10000)
    with col2:
        price_input = st.number_input("Current Price ($)", min_value=0.01, value=29.99)
    
    if st.button("➕ Add Snapshot", use_container_width=True):
        if asin_to_track:
            success = tracker.add_snapshot(asin_to_track, bsr_input, price_input)
            if success:
                st.success(f"Added snapshot for {asin_to_track}")
            else:
                st.error("Failed to add snapshot")
    
    st.markdown("---")
    
    # View tracked products
    st.markdown("### View Tracked Products")
    tracked = tracker.get_tracked_asins()
    
    if tracked:
        selected_asin = st.selectbox("Select product", tracked)
        
        if st.button("📊 Show Trend"):
            trend = tracker.get_trend(selected_asin)
            if trend:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current BSR", f"#{trend.current_bsr:,}")
                with col2:
                    st.metric("30-Day Avg", f"#{trend.avg_bsr_30d:,.0f}")
                with col3:
                    st.metric("Trend", trend.trend_direction.upper())
                
                st.metric("Stability Score", f"{10 - trend.bsr_variance*10:.1f}/10")
                
                if trend.is_seasonal:
                    st.warning("⚠️ Product shows seasonal patterns")
            else:
                st.warning("Not enough data yet. Keep tracking!")
    else:
        st.info("No products being tracked yet. Add some above!")


def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🚀 Amazon Product Hunter Pro <span class="version-badge">v2.0 FREE</span></h1>
        <p>Enhanced with IP Risk Detection, Hazmat Alerts, 3-Pillar Scoring & More!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize components
    components = init_components()
    
    # Tabs for different tools
    tab1, tab2, tab3 = st.tabs(["🔍 Product Hunt", "🔑 Keyword Research", "📈 BSR Tracker"])
    
    with tab1:
        # Sidebar for product hunting
        with st.sidebar:
            st.markdown("### 🎯 Search Settings")
            
            keyword = st.text_input("Search Keyword", placeholder="Enter product keyword")
            
            market = st.selectbox("Marketplace", ["US", "UK", "DE"])
            market_base = {
                "US": "https://www.amazon.com",
                "UK": "https://www.amazon.co.uk", 
                "DE": "https://www.amazon.de",
            }[market]
            
            st.markdown("### ⭐ Filters")
            min_rating = st.slider("Min Rating", 1.0, 5.0, 3.0)
            
            st.markdown("### ️ Risk Filters")
            skip_risky_brands = st.checkbox("Skip High IP Risk Brands", value=True)
            skip_hazmat = st.checkbox("Skip Potential Hazmat", value=True)
            
            hunt_button = st.button("🚀 Hunt Products", use_container_width=True)
        
        # Main area
        if hunt_button:
            if not keyword:
                st.warning("Please enter a search keyword")
            else:
                st.markdown(f'<div class="success-message">🔍 Searching for: {keyword}</div>', unsafe_allow_html=True)
                
                progress = st.progress(0)
                status = st.empty()
                
                with st.spinner("Hunting..."):
                    try:
                        # Initialize scraper
                        status.text("🔧 Initializing...")
                        progress.progress(10)
                        
                        scraper = AmazonScraper(base_url=market_base)
                        scorer = ProductScorer()
                        market_analyzer = MarketAnalyzer()
                        
                        # Scrape
                        status.text("🕷️ Scraping Amazon...")
                        progress.progress(30)
                        
                        products = scraper.search_products(keyword, pages=2)
                        logger.info(f"Found {len(products)} initial products")
                        
                        # Fast filtering - NO seller API calls
                        status.text("🔍 Filtering products...")
                        progress.progress(50)
                        
                        filtered = []
                        for product in products:
                            # Rating filter
                            rating = float(product.get('rating') or 0)
                            if rating < min_rating:
                                continue
                            
                            # Risk filters (fast - local checks only)
                            if skip_risky_brands:
                                brand_result = components['brand_checker'].check_brand(
                                    product.get('brand', ''),
                                    product.get('title', '')
                                )
                                if brand_result.is_veto:
                                    continue
                            
                            if skip_hazmat:
                                hazmat_result = components['hazmat_detector'].check_product(product)
                                if hazmat_result.is_veto:
                                    continue
                            
                            filtered.append(product)
                        
                        progress.progress(90)
                        status.text("📊 Calculating scores...")
                        
                        # Display results
                        progress.progress(100)
                        status.text("✅ Complete!")
                        
                        display_enhanced_results(filtered, components)
                        
                        # Export
                        if filtered:
                            df = pd.DataFrame(filtered)
                            st.download_button(
                                "📥 Download Results CSV",
                                df.to_csv(index=False),
                                "product_hunt_results.csv",
                                "text/csv"
                            )
                        
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        logger.error(f"Hunt error: {str(e)}")
    
    with tab2:
        keyword_research_tab(components)
    
    with tab3:
        bsr_tracker_tab(components)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.8rem;">
        <p>Amazon Product Hunter Pro v2.0 - Built with FREE tools</p>
        <p>⚠️ All data is for research purposes only. Always verify before sourcing.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
