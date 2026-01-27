import streamlit as st
import pandas as pd
from scraper.amazon_scraper import AmazonScraper
from analysis.scoring import ProductScorer
from analysis.sentiment import SentimentAnalyzer
from analysis.seller_analysis import SellerInfo
from analysis.market_analysis import MarketAnalyzer
import logging

# Configure page
st.set_page_config(
    page_title="Amazon Product Hunter Pro",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Main styling */
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
        font-size: 3rem;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header p {
        font-family: 'Inter', sans-serif;
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
    }
    
    .sidebar-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        text-align: center;
    }
    
    .sidebar-header h2 {
        margin: 0;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
    }
    
    /* Metric cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #4f46e5;
        margin-bottom: 1rem;
        transition: transform 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #64748b;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Product cards */
    .product-card {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 8px 30px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
    }
    
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
    }
    
    /* Ensure all text in product cards is dark */
    .product-card * {
        color: #1e293b !important;
    }
    
    .product-card h1,
    .product-card h2,
    .product-card h3,
    .product-card h4,
    .product-card h5,
    .product-card h6,
    .product-card p,
    .product-card div,
    .product-card span {
        color: #1e293b !important;
    }
    
    .product-title {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.3rem;
        color: #1e293b !important;
        margin-bottom: 1rem;
        line-height: 1.4;
    }
    
    .opportunity-badge {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 1rem;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4);
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%);
    }
    
    /* Success message */
    .success-message {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 600;
    }
    
    /* Warning message */
    .warning-message {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 600;
    }
    
    /* Error message */
    .error-message {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-weight: 600;
    }
    
    /* Stats grid */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0;
    }
    
    .stat-item {
        text-align: center;
        padding: 1rem;
        background: #f8fafc;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin: 0;
    }
    
    .stat-label {
        font-size: 0.8rem;
        color: #64748b;
        margin: 0.25rem 0 0 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Override Streamlit's default text colors */
    .stMarkdown {
        color: #1e293b !important;
    }
    
    .stMarkdown p {
        color: #1e293b !important;
    }
    
    .stMarkdown h1,
    .stMarkdown h2,
    .stMarkdown h3,
    .stMarkdown h4,
    .stMarkdown h5,
    .stMarkdown h6 {
        color: #1e293b !important;
    }
    
    /* Ensure all text in containers is dark */
    .stContainer {
        color: #1e293b !important;
    }
    
    .stContainer * {
        color: #1e293b !important;
    }
    
    /* Global text color override for better visibility */
    .main .block-container {
        color: #1e293b !important;
    }
    
    .main .block-container * {
        color: #1e293b !important;
    }
    
    /* Override any white text */
    .main .block-container p,
    .main .block-container div,
    .main .block-container span,
    .main .block-container h1,
    .main .block-container h2,
    .main .block-container h3,
    .main .block-container h4,
    .main .block-container h5,
    .main .block-container h6 {
        color: #1e293b !important;
    }
</style>
""", unsafe_allow_html=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def display_enhanced_results(products):
    st.markdown("## 🏆 Top Ranked Products Found")
    
    # Summary metrics
    if products:
        avg_score = sum(p.get('opportunity_score', 0) for p in products) / len(products)
        avg_rating = sum(float(p.get('rating', 0)) for p in products) / len(products)
        
        # Safe average price calculation
        prices_with_values = [float(p.get('price', 0)) for p in products if p.get('price') and p.get('price') != 'N/A']
        avg_price = sum(prices_with_values) / len(prices_with_values) if prices_with_values else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value">{len(products)}</p>
                <p class="metric-label">Products Found</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value">{avg_score:.1f}</p>
                <p class="metric-label">Avg Opportunity Score</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value">{avg_rating:.1f}⭐</p>
                <p class="metric-label">Avg Rating</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <p class="metric-value">${avg_price:.2f}</p>
                <p class="metric-label">Avg Price</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Product cards
    for i, product in enumerate(products, 1):
        with st.container():
            st.markdown(f"""
            <div class="product-card">
                <div class="opportunity-badge">
                    #{i} - Opportunity Score: {product['opportunity_score']:.1f}
                </div>
                <h3 class="product-title" style="color: #1e293b !important;">{product['title'][:100]}{'...' if len(product['title']) > 100 else ''}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Product metrics in a grid
            seller_info = product.get('seller_info', {})
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("**📊 Product Metrics**")
                st.metric("Rating", f"{product['rating']}⭐", delta=None)
                st.metric("BSR", f"#{product.get('bsr', 'N/A')}", delta=None)
                st.metric("Price", f"${product.get('price', 'N/A')}", delta=None)
            
            with col2:
                st.markdown("**👥 Seller Info**")
                st.metric("FBA Sellers", seller_info.get('fba_count', 0), delta=None)
                st.metric("FBM Sellers", seller_info.get('fbm_count', 0), delta=None)
                st.metric("Total Sellers", seller_info.get('total_sellers', 0), delta=None)
            
            with col3:
                st.markdown("**📈 Market Analysis**")
                st.metric("Est. Monthly Sales", f"{product.get('estimated_monthly_sales', 0)}", delta=None)
                st.metric("Reviews", f"{product.get('reviews', 0):,}", delta=None)
                st.metric("Competition Score", f"{product.get('competition_score', 0):.1f}/10", delta=None)
            
            with col4:
                st.markdown("**💰 Financial**")
                st.metric("Profit Margin", f"{product.get('profit_margin', 0):.1f}%", delta=None)
                st.metric("Listing Quality", f"{product.get('listing_quality', 0)}/10", delta=None)
                st.metric("ASIN", product['asin'], delta=None)
            
            # Price analysis
            prices = seller_info.get('prices', {})
            fba_prices_all = prices.get('fba', [])
            fbm_prices_all = prices.get('fbm', [])
            fba_prices = [p for p in fba_prices_all if isinstance(p, (int, float))]
            fbm_prices = [p for p in fbm_prices_all if isinstance(p, (int, float))]
            
            if fba_prices or fbm_prices:
                st.markdown("**💰 Price Analysis:**")
                price_col1, price_col2 = st.columns(2)
                
                with price_col1:
                    if fba_prices:
                        st.write(f"**FBA Prices:** ${min(fba_prices):.2f} - ${max(fba_prices):.2f}")
                
                with price_col2:
                    if fbm_prices:
                        st.write(f"**FBM Prices:** ${min(fbm_prices):.2f} - ${max(fbm_prices):.2f}")
            
            # Action buttons
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**🔗 [View on Amazon]({product['url']})**")
            with col2:
                if st.button(f"📋 Copy ASIN", key=f"copy_{i}"):
                    st.write(f"ASIN: {product['asin']}")
            
            st.markdown("---")

def show_analytics(products):
    st.markdown("## 📊 Product Analytics")
    
    if not products:
        return
    
    # Create DataFrame
    df = pd.DataFrame(products)
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Products", len(products))
    
    with col2:
        avg_score = df['opportunity_score'].mean()
        st.metric("Avg Opportunity Score", f"{avg_score:.1f}")
    
    with col3:
        avg_rating = df['rating'].mean()
        st.metric("Avg Rating", f"{avg_rating:.1f}⭐")
    
    with col4:
        # Safe average price calculation
        price_values = df['price'].dropna()
        avg_price = price_values.mean() if not price_values.empty else 0
        st.metric("Avg Price", f"${avg_price:.2f}")
    
    # Opportunity Score Distribution
    st.markdown("### 📈 Opportunity Score Distribution")
    score_counts = df['opportunity_score'].value_counts().sort_index()
    st.bar_chart(score_counts)
    
    # Top performing products
    st.markdown("### 🏆 Top 5 Products by Opportunity Score")
    top_products = df.nlargest(5, 'opportunity_score')[['title', 'opportunity_score', 'rating', 'price']]
    st.dataframe(top_products, use_container_width=True)
    
    # Price vs Rating scatter
    st.markdown("### 💰 Price vs Rating Analysis")
    scatter_data = df[['price', 'rating', 'opportunity_score']].dropna()
    if not scatter_data.empty:
        st.scatter_chart(
            scatter_data,
            x='price',
            y='rating',
            size='opportunity_score',
            use_container_width=True
        )

def main():
    # Beautiful header
    st.markdown("""
    <div class="main-header">
        <h1>🛒 Amazon Product Hunter Pro</h1>
        <p>Discover profitable products with advanced market analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar with beautiful styling
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-header">
            <h2>🎯 Search Strategy</h2>
        </div>
        """, unsafe_allow_html=True)
        
        search_method = st.radio(
            "Search Method", 
            ["Keyword Based", "Competitor Based"],
            help="Choose how to search for products",
            key="search_method"
        )
        
        if search_method == "Competitor Based":
            keyword = st.text_input(
                "Product ASIN or URL",
                placeholder="Enter ASIN or Amazon URL",
                help="Enter an ASIN or full Amazon URL to find similar products"
            )
            st.info("🔍 Enter an ASIN or full Amazon URL to find similar products")
        else:
            keyword = st.text_input(
                "Search Keyword",
                placeholder="Enter your search term",
                help="Enter keywords to search for products"
            )
            category = st.selectbox(
                "Category", 
                ["All Categories", "Health & Household", "Home & Kitchen", "Sports & Outdoors", 
                 "Beauty & Personal Care", "Pet Supplies"],
                help="Filter by product category"
            )
        
        # Market selector
        st.markdown("### 🌍 Market")
        market = st.selectbox(
            "Amazon Marketplace", 
            ["US", "UK", "DE"], 
            index=0,
            help="Choose marketplace to search"
        )
        market_base = {
            "US": "https://www.amazon.com",
            "UK": "https://www.amazon.co.uk",
            "DE": "https://www.amazon.de",
        }[market]
        
        # Quality filters
        st.markdown("### ⭐ Product Quality Filters")
        min_rating = st.slider(
            "Minimum Rating", 
            1.0, 5.0, 3.0,
            help="Only show products with good ratings"
        )
        max_bsr = st.number_input(
            "Maximum BSR", 
            100, 100000, 100000,
            help="Only show products with good Best Sellers Rank"
        )
        
        # Seller filters
        st.markdown("### 👥 Seller Requirements")
        fba_min = st.number_input("Min FBA sellers", 0, 20, 2)
        fbm_min = st.number_input("Min FBM sellers", 0, 20, 1)
        exclude_amazon = st.checkbox("Exclude Amazon as seller", value=True)
        
        # Hunt button
        hunt_button = st.button("🚀 Hunt Products", use_container_width=True)
    
    # Main content area
    if hunt_button:
        if not keyword:
            st.markdown("""
            <div class="warning-message">
                ⚠️ Please enter a search keyword or ASIN
            </div>
            """, unsafe_allow_html=True)
            return
            
        # Show search strategy info
        if search_method == "Competitor Based":
            st.markdown(f"""
            <div class="success-message">
                🔍 Analyzing similar products to: {keyword}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="success-message">
                🔍 Searching in {category} for: {keyword}
            </div>
            """, unsafe_allow_html=True)
            
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("Hunting for products..."):
            try:
                # Initialize components
                status_text.text("🔧 Initializing components...")
                progress_bar.progress(10)
                
                scraper = AmazonScraper(base_url=market_base)
                scorer = ProductScorer()
                sentiment_analyzer = SentimentAnalyzer()
                
                # Scrape products
                status_text.text("🕷️ Scraping Amazon products...")
                progress_bar.progress(30)
                
                logger.info(f"Starting search for keyword: {keyword}")
                products = scraper.search_products(keyword, pages=2)
                logger.info(f"Found {len(products)} products in initial search")
                
                # Initialize market analyzer
                status_text.text("📊 Analyzing market data...")
                progress_bar.progress(50)
                
                market_analyzer = MarketAnalyzer()
                
                # Filter products
                status_text.text("🔍 Filtering products...")
                progress_bar.progress(70)
                
                # Simplified filtering - focus on quality factors only (no price filter)
                filtered_products = []
                for product in products:
                    logger.info(f"Checking product {product.get('asin')}: Price=${product.get('price')}, Rating={product.get('rating')}, Reviews={product.get('reviews')}")
                    
                    # Get rating and BSR (no review count needed)
                    rating = product.get('rating')
                    bsr = product.get('bsr')
                    
                    # Convert to numeric values with better defaults
                    try:
                        rating = float(rating) if rating is not None else 0.0
                    except (ValueError, TypeError):
                        rating = 0.0
                    
                    # Essential quality filters only (rating and BSR)
                    if not (rating >= min_rating and
                           (bsr is None or bsr <= max_bsr)):
                        logger.info(f"Skipping product {product.get('asin')} - Rating: {rating}, BSR: {bsr}")
                        continue
                    
                    # Check seller requirements
                    if product.get('asin'):
                        seller_summary = scraper.get_seller_summary(product['asin'])
                        fba_count = seller_summary.get('fba_count', 0)
                        fbm_count = seller_summary.get('fbm_count', 0)
                        amazon_seller = seller_summary.get('amazon_seller', False)
                        
                        # Skip if Amazon is seller and we want to exclude it
                        if exclude_amazon and amazon_seller:
                            continue
                            
                        # Check minimum FBA/FBM sellers only
                        if not (fba_count >= fba_min and fbm_count >= fbm_min):
                            continue
                            
                        # Store seller info
                        product['seller_info'] = seller_summary
                    
                    # Add basic market analysis
                    market_metrics = market_analyzer.analyze_product(product)
                    product.update(market_metrics)
                    
                    filtered_products.append(product)
                    logger.info(f"Product {product.get('asin')} passed essential filters")
                
                # Calculate scores
                status_text.text("📈 Calculating opportunity scores...")
                progress_bar.progress(90)
                
                logger.info(f"After essential filtering: {len(filtered_products)} products")
                
                for product in filtered_products:
                    product['opportunity_score'] = scorer.calculate_opportunity_score(product)
                
                # Sort by opportunity score
                filtered_products.sort(key=lambda x: x.get('opportunity_score', 0), reverse=True)
                
                # Complete progress
                progress_bar.progress(100)
                status_text.text("✅ Analysis complete!")
                
                # Display results
                if filtered_products:
                    display_enhanced_results(filtered_products[:10])
                    
                    # Export options
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        df = pd.DataFrame(filtered_products)
                        st.download_button(
                            label="📊 Download as CSV",
                            data=df.to_csv(index=False),
                            file_name="amazon_products.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        if st.button("📈 View Analytics", use_container_width=True):
                            show_analytics(filtered_products)
                    
                    with col3:
                        if st.button("🔄 New Search", use_container_width=True):
                            st.rerun()
                else:
                    st.markdown("""
                    <div class="warning-message">
                        ⚠️ No products found matching the criteria. Try adjusting your filters.
                    </div>
                    """, unsafe_allow_html=True)
                    
            except Exception as e:
                logger.error(f"Error in main process: {str(e)}")
                st.markdown(f"""
                <div class="error-message">
                    ❌ An error occurred: {str(e)}
                </div>
                """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()