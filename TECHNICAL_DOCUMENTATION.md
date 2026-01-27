# 📚 Amazon Hunter Pro - Complete Technical Documentation

## 🎯 Project Overview

**Amazon Hunter Pro** is an advanced product research tool for Amazon FBA sellers. It scrapes Amazon product data, analyzes market opportunities, calculates profitability, assesses risks, and presents insights through a modern web interface.

### **Purpose**
Help Amazon sellers identify profitable product opportunities by:
- Scraping real-time Amazon product data
- Analyzing demand, competition, and profit potential
- Filtering out risky products (IP issues, hazmat, Amazon sellers)
- Providing actionable insights with visual analytics

---

## 🏗️ System Architecture

### **Architecture Pattern: 3-Tier Web Application**

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React + Vite + TailwindCSS + Framer Motion + Recharts      │
│                    (Port 5173)                               │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST API
                         │ (JSON)
┌────────────────────────▼────────────────────────────────────┐
│                        BACKEND                               │
│            FastAPI + Uvicorn (Port 8001)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Layer (main.py)                     │   │
│  │  - /api/search (POST) - Product search               │   │
│  │  - /api/keywords (GET) - Keyword suggestions         │   │
│  │  - /health (GET) - Health check                      │   │
│  └───────────────────┬──────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼──────────────────────────────────┐   │
│  │           Business Logic Layer                       │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ AmazonScraper - Web scraping                   │  │   │
│  │  │ EnhancedOpportunityScorer - Scoring system     │  │   │
│  │  │ FBAFeeCalculator - Fee calculations            │  │   │
│  │  │ BrandRiskChecker - IP risk detection           │  │   │
│  │  │ HazmatDetector - Hazmat detection              │  │   │
│  │  │ FreeKeywordTool - Keyword suggestions          │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Requests
                         │ (BeautifulSoup + Requests)
┌────────────────────────▼────────────────────────────────────┐
│                    EXTERNAL DATA                             │
│                   Amazon.com API                             │
│  - Product search results                                    │
│  - Product detail pages                                      │
│  - Seller information (AOD endpoint)                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 💻 Technology Stack

### **Frontend Technologies**

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.2.0 | UI framework for building component-based interface |
| **Vite** | 5.0.8 | Build tool and dev server (faster than Webpack) |
| **TailwindCSS** | 3.3.6 | Utility-first CSS framework for styling |
| **Framer Motion** | 10.16.5 | Animation library for smooth transitions |
| **Recharts** | 2.10.3 | Chart library (Bar charts, Radar charts) |
| **Axios** | 1.6.2 | HTTP client for API requests |
| **Lucide React** | 0.294.0 | Icon library (modern, lightweight) |
| **clsx + tailwind-merge** | Latest | Utility for conditional CSS classes |

**Why these choices?**
- **React**: Industry standard, component reusability, large ecosystem
- **Vite**: Lightning-fast HMR (Hot Module Replacement), better DX than CRA
- **TailwindCSS**: Rapid UI development, consistent design system
- **Framer Motion**: Professional animations with minimal code
- **Recharts**: D3-based charts, React-friendly, customizable

### **Backend Technologies**

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Programming language |
| **FastAPI** | Latest | Modern async web framework |
| **Uvicorn** | Latest | ASGI server for FastAPI |
| **BeautifulSoup4** | Latest | HTML parsing for web scraping |
| **Requests** | Latest | HTTP library for making requests |
| **fake-useragent** | Latest | Random user agent generation |
| **Pydantic** | Latest | Data validation (built into FastAPI) |

**Why these choices?**
- **FastAPI**: Fast, automatic API docs, type hints, async support
- **BeautifulSoup**: Robust HTML parsing, handles malformed HTML
- **Requests**: Simple, reliable HTTP library

### **Additional Libraries**

| Library | Purpose |
|---------|---------|
| **logging** | Application logging and debugging |
| **dataclasses** | Structured data models |
| **enum** | Type-safe enumerations |
| **typing** | Type hints for better code quality |

---

## 📊 Data Flow Architecture

### **Complete Request Flow**

```
1. USER ACTION
   ↓
   User enters "yoga mat" → Clicks "Hunt"
   
2. FRONTEND (App.jsx)
   ↓
   - Collects search parameters + filters
   - Sends POST to /api/search
   
3. BACKEND API (main.py)
   ↓
   - Receives SearchRequest
   - Validates parameters
   
4. AMAZON SCRAPER (amazon_scraper.py)
   ↓
   - Builds search URL: amazon.com/s?k=yoga+mat&page=1
   - Sends HTTP request with fake user agent
   - Receives HTML response
   - Parses with BeautifulSoup
   - Extracts: ASIN, title, price, rating, reviews
   - Estimates BSR from search position
   
5. MARKET METRICS (amazon_scraper.py)
   ↓
   - Calculates estimated sales from BSR
   - Formula: Sales = 40000 * (BSR ^ -0.4)
   - Adds seasonality, search volume estimates
   
6. SELLER INFO (seller_analysis.py)
   ↓
   - For top 25 products only (rate limiting)
   - Fetches seller data via AOD endpoint
   - Extracts: FBA count, FBM count, Amazon seller status
   - Identifies seller names
   
7. SCORING SYSTEM (enhanced_scoring.py)
   ↓
   - Calculates 3-pillar score:
     * Demand (40%): BSR, stability, sales velocity
     * Competition (35%): FBA sellers, reviews, Amazon presence
     * Profit (25%): Margin, price point, risk factors
   - Checks veto conditions (IP risk, hazmat, low margin)
   
8. RISK ANALYSIS
   ↓
   a) Brand Risk (brand_risk.py)
      - Checks against 295 risky brands
      - Categories: CRITICAL, HIGH, MEDIUM, LOW
      - Brands like Nike, Apple, Disney = CRITICAL
   
   b) Hazmat Detection (hazmat_detector.py)
      - Scans title/description for keywords
      - Categories: Flammable, Toxic, Corrosive, etc.
      - 100+ hazmat keywords
   
9. FEE CALCULATION (fba_calculator.py)
   ↓
   - Referral fee (6-15% based on category)
   - FBA fulfillment fee (based on size/weight)
   - Storage fee (monthly)
   - Total Amazon fees
   
10. FILTERING (main.py)
    ↓
    Products filtered in this order:
    1. Rating < min_rating → SKIP
    2. Brand risk + skip_risky_brands → SKIP
    3. Hazmat + skip_hazmat → SKIP
    4. Margin < min_margin → SKIP
    5. Sales outside range → SKIP
    6. Amazon seller + skip_amazon_seller → SKIP
    7. Brand seller + skip_brand_seller → SKIP
    
11. RESPONSE ASSEMBLY
    ↓
    - Calculate market share for each product
    - Sort by revenue (descending)
    - Limit to top 50 products
    - Return JSON with summary + results
    
12. FRONTEND RENDERING (App.jsx)
    ↓
    - Displays market overview cards
    - Renders bar chart (market dominance)
    - Shows product cards with metrics
    - Applies client-side filters
    - Enables product detail modal on click
```

---

## 🔍 Data Sources & Scraping

### **Where Data Comes From**

#### **1. Amazon Search Results Page**
**URL Pattern**: `https://www.amazon.com/s?k={keyword}&page={page}`

**Data Extracted**:
- **ASIN**: Product identifier (from `data-asin` attribute)
- **Title**: Product name (from `h2` tags with specific classes)
- **Price**: Current price (from `span.a-price` → `span.a-offscreen`)
- **Rating**: Star rating (from `span.a-icon-alt`)
- **Reviews**: Review count (from `span.a-size-base`)

**Scraping Method**:
```python
# 1. Build URL
url = f"{base_url}/s?k={keyword}&page={page}"

# 2. Send request with fake user agent
response = session.get(url, headers=headers)

# 3. Parse HTML
soup = BeautifulSoup(response.content, 'html.parser')

# 4. Find all product cards
items = soup.find_all('div', {'data-component-type': 's-search-result'})

# 5. Extract data from each card
for item in items:
    asin = item.get('data-asin')
    title = item.find('h2').get_text()
    price_elem = item.find('span', {'class': 'a-offscreen'})
    price = extract_price(price_elem)
    # ... etc
```

#### **2. Amazon Product Detail Page**
**URL Pattern**: `https://www.amazon.com/dp/{ASIN}`

**Data Extracted**:
- **BSR (Best Sellers Rank)**: Sales rank in category
- **Description**: Product description
- **Features**: Bullet points
- **Images Count**: Number of product images
- **Category**: Product category

**BSR Extraction** (multiple fallback methods):
```python
# Method 1: Direct ID
bsr_elem = soup.find('span', {'id': 'salesrank'})

# Method 2: Text search
bsr_elem = soup.find(text=lambda t: 'best sellers rank' in t.lower())

# Method 3: Product details table
details = soup.find('table', {'class': 'prodDetTable'})
# Extract BSR from table rows

# Method 4: Regex on entire page
import re
match = re.search(r'#([\d,]+)\s+in\s+', page_text)
```

#### **3. Amazon Seller Information (AOD Endpoint)**
**URL Pattern**: `https://www.amazon.com/gp/aod/ajax/ref=...?asin={ASIN}`

**Data Extracted**:
- **FBA Seller Count**: Number of FBA sellers
- **FBM Seller Count**: Number of FBM sellers
- **Amazon Seller**: Whether Amazon sells it
- **Seller Names**: Names of sellers
- **Prices**: FBA and FBM price ranges

**Why AOD Endpoint?**
- Faster than parsing full product page
- Contains seller data in structured format
- Used for "Other sellers" modal on Amazon

**Rate Limiting**:
- Limited to 25 products per search
- Prevents Amazon from blocking requests
- Prioritizes top products by revenue

---

## 🧮 Scoring Algorithm

### **3-Pillar Scoring System**

The scoring system evaluates products on three pillars with weighted contributions:

```
Total Score = (Demand × 0.40) + (Competition × 0.35) + (Profit × 0.25)
```

#### **Pillar 1: Demand & Trend (40% weight)**

**Components**:
1. **BSR Score** (40% of pillar)
   - Excellent: BSR ≤ 5,000 → 100 points
   - Good: BSR ≤ 20,000 → 80 points
   - Average: BSR ≤ 50,000 → 60 points
   - Below Average: BSR ≤ 100,000 → 40 points
   - Poor: BSR > 100,000 → 20 points

2. **BSR Stability** (30% of pillar)
   - Variance < 0.2 → 100 points (stable demand)
   - Variance < 0.4 → 70 points
   - Variance < 0.6 → 40 points
   - Variance ≥ 0.6 → 20 points (seasonal/declining)

3. **Sales Velocity** (30% of pillar)
   - ≥ 500/month → 100 points
   - ≥ 300/month → 80 points
   - ≥ 100/month → 60 points
   - ≥ 30/month → 40 points
   - < 30/month → 20 points

**Formula**:
```python
demand_score = (bsr_score × 0.40) + (stability_score × 0.30) + (velocity_score × 0.30)
```

#### **Pillar 2: Competition (35% weight)**

**Components**:
1. **FBA Seller Count** (40% of pillar)
   - Sweet Spot (3-15 sellers) → 100 points
   - Too Few (< 3) → 40 points (low demand/gated)
   - Slightly High (16-20) → 60 points
   - Too Many (> 20) → 20 points (price war risk)

2. **Review Vulnerability** (35% of pillar)
   - ≥ 3 competitors with < 400 reviews → 100 points
   - 2 competitors with < 400 reviews → 70 points
   - 1 competitor with < 400 reviews → 50 points
   - All established (> 400 reviews) → 20 points

3. **Amazon Presence** (25% of pillar)
   - Amazon NOT a seller → 100 points
   - Amazon IS a seller → 0 points

**Formula**:
```python
competition_score = (fba_score × 0.40) + (vulnerability_score × 0.35) + (amazon_score × 0.25)
```

#### **Pillar 3: Profit & Risk (25% weight)**

**Components**:
1. **Profit Margin** (50% of pillar)
   - Excellent (≥ 40%) → 100 points
   - Good (≥ 30%) → 80 points
   - Acceptable (≥ 20%) → 60 points
   - Low (≥ 10%) → 30 points
   - Too Low (< 10%) → 0 points

2. **Price Point** (25% of pillar)
   - Ideal ($20-$50) → 100 points
   - Good ($15-$20 or $50-$75) → 80 points
   - Moderate ($10-$15 or $75-$100) → 60 points
   - Low (< $10) → 30 points (thin margins)
   - High (> $100) → 50 points (more capital)

3. **Risk Factors** (25% of pillar)
   - Start at 100 points
   - High IP risk → -40 points
   - Medium IP risk → -20 points
   - Hazmat (non-veto) → -30 points

**Formula**:
```python
profit_score = (margin_score × 0.50) + (price_score × 0.25) + (risk_score × 0.25)
```

### **Veto Logic (Auto-Reject)**

Certain conditions automatically reject a product regardless of score:

| Veto Reason | Condition | Why |
|-------------|-----------|-----|
| **IP Risk** | Brand in CRITICAL list (Nike, Apple, etc.) | Account suspension risk |
| **Hazmat** | Contains veto-level hazmat keywords | Shipping restrictions, fees |
| **Low Margin** | Profit margin < 10% | Not sustainable |

**Veto Brands** (examples):
- CRITICAL: Nike, Apple, Disney, Sony, Microsoft, Samsung, etc. (204 brands)
- HIGH: Adidas, Puma, Under Armour, etc. (61 brands)
- MEDIUM: Various smaller brands (30 brands)

**Veto Hazmat Keywords** (examples):
- Flammable: gasoline, propane, lighter fluid, etc.
- Toxic: pesticide, poison, arsenic, etc.
- Corrosive: acid, bleach, drain cleaner, etc.

---

## 💰 Financial Calculations

### **1. Sales Estimation from BSR**

**Formula**: Logarithmic regression model
```python
Sales = C × (BSR ^ -k)
```

**Category Constants**:
| Category | C | k |
|----------|---|---|
| Health & Household | 60,000 | 0.4 |
| Home & Kitchen | 50,000 | 0.4 |
| Beauty & Personal Care | 55,000 | 0.4 |
| Sports & Outdoors | 40,000 | 0.4 |
| Pet Supplies | 45,000 | 0.4 |
| Default | 40,000 | 0.4 |

**Example**:
```
BSR = 10,000 in Home & Kitchen
Sales = 50,000 × (10,000 ^ -0.4)
Sales = 50,000 × 0.0251
Sales ≈ 125 units/month
```

**Special Case** (Top 100):
```python
if bsr < 100:
    sales = 3000 + (100 - bsr) × 50
# BSR #1 = 3000 + 99×50 = 7,950/month
# BSR #50 = 3000 + 50×50 = 5,500/month
```

### **2. FBA Fee Calculation**

**Components**:
1. **Referral Fee** (6-15% based on category)
2. **FBA Fulfillment Fee** (based on size tier)
3. **Monthly Storage Fee** (based on cubic feet)

**Size Tiers**:
| Size | Dimensions | FBA Fee |
|------|------------|---------|
| Small Standard | < 20×8×4 in | $2.50 + 15% |
| Large Standard | < 18×14×8 in | $3.48 + 15% |
| Oversized | Larger | $5.42 + 15% |

**Example Calculation**:
```python
price = $29.99
category = "Home & Kitchen"

# Referral fee (15% for most categories)
referral_fee = price × 0.15 = $4.50

# FBA fee (assume small standard)
fba_fee = max(2.50, price × 0.15) = $4.50

# Storage fee (assume 0.5 cu ft)
storage_fee = 0.5 × $0.75 = $0.38

# Total Amazon fees
total_fees = $4.50 + $4.50 + $0.38 = $9.38
```

### **3. Profit Margin Calculation**

**Formula**:
```python
# Assumptions
price = $29.99
amazon_fees = $9.38
cogs = price × 0.25 = $7.50  # Assume 25% of price

# Net profit per unit
net_profit = price - amazon_fees - cogs
net_profit = $29.99 - $9.38 - $7.50 = $13.11

# Profit margin
margin = (net_profit / price) × 100
margin = ($13.11 / $29.99) × 100 = 43.7%
```

### **4. Revenue Estimation**

**Formula**:
```python
monthly_revenue = price × estimated_monthly_sales

# Example
price = $29.99
sales = 125/month
revenue = $29.99 × 125 = $3,748.75/month
```

### **5. Market Share Calculation**

**Formula**:
```python
# Calculate total market revenue
total_market_revenue = sum(product.revenue for product in all_products)

# Calculate each product's share
market_share = (product.revenue / total_market_revenue) × 100

# Example
product_revenue = $3,748.75
total_revenue = $50,000
market_share = ($3,748.75 / $50,000) × 100 = 7.5%
```

---

## 🎯 Filter Implementation

### **Filter Application Order**

Filters are applied in a specific order for efficiency:

```python
for product in products:
    # 1. RATING FILTER
    if rating < min_rating:
        continue  # Skip immediately
    
    # 2. CALCULATE SCORES & RISKS
    score = calculate_score(product)
    brand_risk = check_brand_risk(product)
    hazmat = check_hazmat(product)
    
    # 3. BRAND RISK FILTER
    if skip_risky_brands and brand_risk.is_veto:
        continue
    
    # 4. HAZMAT FILTER
    if skip_hazmat and hazmat.is_veto:
        continue
    
    # 5. CALCULATE FINANCIALS
    revenue = price × sales
    fees = calculate_fees(price)
    profit = price - fees - cogs
    margin = (profit / price) × 100
    
    # 6. MARGIN FILTER
    if margin < min_margin:
        continue
    
    # 7. SALES RANGE FILTER
    if sales < min_sales or sales > max_sales:
        continue
    
    # 8. FETCH SELLER INFO (top 25 only)
    if fetch_seller_info and count < 25:
        seller_info = get_seller_summary(asin)
    
    # 9. AMAZON SELLER FILTER
    if skip_amazon_seller and seller_info.amazon_seller:
        continue
    
    # 10. BRAND SELLER FILTER
    if skip_brand_seller and brand_matches_seller(product):
        continue
    
    # Product passed all filters!
    results.append(product)
```

### **Filter Logic Details**

#### **1. Rating Filter**
```python
rating = float(product.get('rating') or 0)
if rating < min_rating:  # e.g., 3.0
    continue
```

#### **2. Brand Risk Filter**
```python
brand_risk = brand_checker.check_brand(
    brand=product.get('brand', ''),
    title=product.get('title', '')
)

if skip_risky_brands and brand_risk.is_veto:
    continue  # Skip CRITICAL brands
```

#### **3. Hazmat Filter**
```python
hazmat = hazmat_detector.check_product(product)

if skip_hazmat and hazmat.is_veto:
    continue  # Skip products with hazmat keywords
```

#### **4. Margin Filter**
```python
margin = (net_profit / price) × 100

if margin < min_margin:  # e.g., 20%
    continue
```

#### **5. Sales Range Filter**
```python
sales = product.get('estimated_sales', 0)

if sales < min_sales or sales > max_sales:  # e.g., 50-1000
    continue
```

#### **6. Amazon Seller Filter**
```python
if skip_amazon_seller and product['seller_info']['amazon_seller']:
    continue  # Skip if Amazon is a seller
```

#### **7. Brand Seller Filter**
```python
seller_name = product['seller_info']['seller_name'].lower()
brand_name = product['brand'].lower()

# Check if seller name contains brand or vice versa
if brand_name in seller_name or seller_name in brand_name:
    continue  # Skip if brand owns the listing
```

---

## 🎨 Frontend Architecture

### **Component Structure**

```
App.jsx (Main Component)
├── Header
│   ├── Title
│   └── Subtitle
├── Search Controls
│   ├── Marketplace Selector (US/UK/DE)
│   ├── Filters Button
│   └── Search Bar + Hunt Button
├── Filters Panel (Collapsible)
│   ├── Risk Controls
│   │   ├── Skip High Risk & Hazmat
│   │   ├── Skip Amazon as Seller
│   │   └── Skip Brand as Seller
│   ├── Quality Filters
│   │   ├── Min Rating Slider
│   │   └── Min Margin Slider
│   └── Sales Range
│       ├── Min Sales Slider
│       └── Max Sales Slider
├── Results Section
│   ├── Market Overview Cards
│   │   ├── Total Market Revenue
│   │   ├── Avg Revenue/Listing
│   │   ├── Avg Monthly Sales
│   │   └── Products Analyzed
│   ├── Action Bar
│   │   ├── Show Winners Only Toggle
│   │   ├── Profit Calculator Button
│   │   ├── Export CSV Button
│   │   └── Export JSON Button
│   ├── Market Dominance Chart (Bar Chart)
│   └── Product Cards List
│       └── ProductCard (clickable)
└── Modals
    ├── Product Detail Modal
    │   ├── Radar Chart (Score Breakdown)
    │   ├── Financial Analysis
    │   ├── Risk Assessment
    │   └── Product Specs
    └── Profit Calculator Modal
```

### **State Management**

```javascript
// Search state
const [keyword, setKeyword] = useState('')
const [marketplace, setMarketplace] = useState('US')
const [loading, setLoading] = useState(false)
const [data, setData] = useState(null)
const [error, setError] = useState(null)

// Filter state
const [minRating, setMinRating] = useState(3.0)
const [minMargin, setMinMargin] = useState(20)
const [skipRisky, setSkipRisky] = useState(true)
const [skipAmazonSeller, setSkipAmazonSeller] = useState(true)
const [skipBrandSeller, setSkipBrandSeller] = useState(true)
const [minSales, setMinSales] = useState(50)
const [maxSales, setMaxSales] = useState(1000)

// UI state
const [showFilters, setShowFilters] = useState(false)
const [showWinnersOnly, setShowWinnersOnly] = useState(false)
const [selectedProduct, setSelectedProduct] = useState(null)
const [showProfitCalc, setShowProfitCalc] = useState(false)
```

### **API Integration**

```javascript
const handleSearch = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    try {
        const response = await axios.post(`${API_URL}/search`, {
            keyword,
            marketplace,
            min_rating: minRating,
            skip_risky_brands: skipRisky,
            skip_hazmat: skipRisky,
            skip_amazon_seller: skipAmazonSeller,
            skip_brand_seller: skipBrandSeller,
            min_margin: minMargin,
            min_sales: minSales,
            max_sales: maxSales,
            pages: 2,
            fetch_seller_info: true
        })
        
        setData(response.data)
    } catch (err) {
        setError('Failed to fetch data')
    } finally {
        setLoading(false)
    }
}
```

### **Styling Approach**

**TailwindCSS Utility Classes**:
```jsx
<div className="min-h-screen bg-gradient-to-br from-gray-900 to-slate-900 text-white p-6">
    <div className="max-w-7xl mx-auto space-y-8">
        {/* Content */}
    </div>
</div>
```

**Custom Design Tokens**:
- Background: `#0f172a` (slate-900) to `#1e293b` (slate-800)
- Accent: `#6366f1` (indigo-500) to `#818cf8` (indigo-400)
- Success: `#10b981` (green-500)
- Warning: `#f59e0b` (amber-500)
- Error: `#ef4444` (red-500)

**Animations**:
```jsx
<motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.5 }}
>
    {/* Content */}
</motion.div>
```

---

## 📁 Project Structure

```
amazon_hunter/
├── config/
│   ├── settings.py          # Configuration settings
│   └── categories.json      # Amazon category mappings
├── src/
│   ├── scraper/
│   │   ├── amazon_scraper.py      # Main scraper (731 lines)
│   │   └── __init__.py
│   ├── analysis/
│   │   ├── enhanced_scoring.py    # 3-pillar scoring (622 lines)
│   │   ├── fba_calculator.py      # FBA fee calculations
│   │   ├── keyword_tool.py        # Keyword suggestions
│   │   ├── seller_analysis.py     # Seller info extraction
│   │   ├── market_analysis.py     # Market metrics
│   │   └── __init__.py
│   ├── risk/
│   │   ├── brand_risk.py          # IP risk checker (295 brands)
│   │   ├── hazmat_detector.py     # Hazmat detection (100+ keywords)
│   │   └── __init__.py
│   └── data/
│       ├── risky_brands.json      # Brand blacklist
│       └── hazmat_keywords.json   # Hazmat keyword list
├── web_app/
│   ├── backend/
│   │   ├── main.py                # FastAPI application (262 lines)
│   │   ├── main_simple.py         # Alternative implementation
│   │   └── requirements.txt       # Python dependencies
│   └── frontend/
│       ├── src/
│       │   ├── App.jsx            # Main React component (792 lines)
│       │   ├── main.jsx           # React entry point
│       │   └── index.css          # Global styles
│       ├── index.html             # HTML template
│       ├── package.json           # Node dependencies
│       ├── vite.config.js         # Vite configuration
│       └── tailwind.config.js     # Tailwind configuration
├── tests/
│   ├── test_scraper.py
│   ├── test_scoring.py
│   └── test_filters.py
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── README.md               # Project overview
├── STATUS.md               # Current status
├── QUICK_START.md          # Getting started guide
├── TROUBLESHOOTING.md      # Common issues
└── TECHNICAL_DOCUMENTATION.md  # This file
```

---

## 🔄 Development Workflow

### **Starting the Application**

**1. Backend**:
```bash
cd web_app/backend
python -m uvicorn main:app --reload --port 8001
```

**2. Frontend**:
```bash
cd web_app/frontend
npm run dev
```

**3. Access**:
- Frontend: http://localhost:5173
- Backend API: http://127.0.0.1:8001
- API Docs: http://127.0.0.1:8001/docs

### **Development Tools**

**Backend**:
- FastAPI auto-reload on file changes
- Swagger UI at `/docs`
- ReDoc at `/redoc`
- Logging to console

**Frontend**:
- Vite HMR (instant updates)
- React DevTools
- Browser console for debugging

---

## 🚀 Performance Optimizations

### **1. Rate Limiting Protection**
```python
# Limit seller info fetching to prevent Amazon blocking
max_seller_info_fetches = 25
seller_info_fetch_count = 0

if seller_info_fetch_count < max_seller_info_fetches:
    seller_info = scraper.get_seller_summary(asin)
    seller_info_fetch_count += 1
```

### **2. Efficient Filtering**
- Early filtering (rating, brand risk) before expensive operations
- Seller info fetched only for products that pass initial filters
- Client-side filtering for instant UI updates

### **3. Caching Strategy**
```python
# Session reuse for HTTP requests
self.session = requests.Session()

# Fake user agent rotation
self.ua = UserAgent()
headers = {'User-Agent': self.ua.random}
```

### **4. Minimal Delays**
```python
# Small delay between pages (0.5s)
if page < pages:
    time.sleep(0.5)
```

### **5. Data Limits**
- Return max 50 products per search
- Fetch seller info for max 25 products
- Search max 2 pages by default

---

## 🔒 Security Considerations

### **1. User Agent Rotation**
```python
from fake_useragent import UserAgent
ua = UserAgent()
headers = {'User-Agent': ua.random}
```

### **2. CORS Configuration**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### **3. Input Validation**
```python
class SearchRequest(BaseModel):
    keyword: str
    marketplace: str = "US"
    pages: int = 1
    min_rating: float = 3.0
    # Pydantic validates types automatically
```

### **4. Error Handling**
```python
try:
    # Scraping logic
except Exception as e:
    logger.error(f"Error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

---

## 📊 API Endpoints

### **POST /api/search**

**Request**:
```json
{
  "keyword": "yoga mat",
  "marketplace": "US",
  "pages": 2,
  "min_rating": 4.0,
  "skip_risky_brands": true,
  "skip_hazmat": true,
  "skip_amazon_seller": true,
  "skip_brand_seller": true,
  "min_margin": 20.0,
  "min_sales": 50,
  "max_sales": 1000,
  "fetch_seller_info": true
}
```

**Response**:
```json
{
  "summary": {
    "total_products": 25,
    "total_revenue": 125000,
    "avg_revenue": 5000,
    "avg_sales": 150
  },
  "results": [
    {
      "asin": "B0XXXXXXXX",
      "title": "Premium Yoga Mat...",
      "price": 29.99,
      "rating": 4.6,
      "reviews": 1234,
      "bsr": 5000,
      "estimated_sales": 200,
      "est_revenue": 5998,
      "est_profit": 13.11,
      "margin": 43.7,
      "market_share": 4.8,
      "enhanced_score": 82,
      "score_breakdown": {
        "demand": 85,
        "competition": 78,
        "profit": 90
      },
      "is_vetoed": false,
      "veto_reasons": [],
      "risks": {
        "brand_risk": "LOW",
        "brand_reason": "No known issues",
        "hazmat": false,
        "hazmat_category": null
      },
      "seller_info": {
        "fba_count": 8,
        "fbm_count": 2,
        "amazon_seller": false,
        "total_sellers": 10,
        "seller_name": "YogaSupplyCo"
      },
      "fees_breakdown": {
        "referral": 4.50,
        "fba": 4.50,
        "storage": 0.38,
        "total": 9.38
      }
    }
  ],
  "metadata": {
    "keyword": "yoga mat",
    "marketplace": "US",
    "filters_applied": {
      "min_rating": 4.0,
      "min_margin": 20.0,
      "sales_range": "50-1000",
      "skip_amazon_seller": true,
      "skip_brand_seller": true
    }
  }
}
```

### **GET /api/keywords?q={query}**

**Request**: `GET /api/keywords?q=yoga`

**Response**:
```json
{
  "keyword": "yoga",
  "suggestions": [
    {
      "keyword": "yoga mat",
      "source": "amazon_autocomplete",
      "relevance": 0.95
    },
    {
      "keyword": "yoga blocks",
      "source": "amazon_autocomplete",
      "relevance": 0.87
    }
  ]
}
```

### **GET /health**

**Response**:
```json
{
  "status": "healthy",
  "version": "2.0"
}
```

---

## 🎓 Key Learnings & Best Practices

### **1. Web Scraping**
- Always use fake user agents
- Implement delays between requests
- Handle malformed HTML gracefully
- Have multiple fallback extraction methods
- Respect rate limits

### **2. Data Processing**
- Filter early to reduce processing
- Use efficient algorithms (single-pass where possible)
- Cache expensive operations
- Validate data at each step

### **3. API Design**
- Use Pydantic for validation
- Return structured, consistent responses
- Include metadata for debugging
- Implement proper error handling

### **4. Frontend Development**
- Use component composition
- Manage state efficiently
- Implement loading states
- Provide user feedback
- Make UI responsive

### **5. Scoring Systems**
- Use weighted pillars for flexibility
- Implement veto logic for deal-breakers
- Provide score breakdowns for transparency
- Generate actionable recommendations

---

## 📈 Future Enhancements

### **Potential Improvements**

1. **Data Persistence**
   - Add PostgreSQL database
   - Store search history
   - Track product trends over time

2. **Advanced Analytics**
   - Historical BSR tracking
   - Price trend analysis
   - Seasonality detection
   - Competitor monitoring

3. **User Features**
   - User authentication
   - Saved searches
   - Product watchlists
   - Email alerts

4. **Performance**
   - Redis caching
   - Background task queue (Celery)
   - Async scraping (aiohttp)
   - Database query optimization

5. **Additional Marketplaces**
   - Canada (CA)
   - France (FR)
   - Italy (IT)
   - Spain (ES)
   - Japan (JP)

6. **Export Features**
   - Excel export with formatting
   - PDF reports
   - Automated email reports

7. **Mobile App**
   - React Native app
   - Push notifications
   - Offline mode

---

## 🏁 Summary

**Amazon Hunter Pro** is a comprehensive product research tool that:

✅ **Scrapes** Amazon product data in real-time  
✅ **Analyzes** demand, competition, and profitability  
✅ **Scores** products using a 3-pillar weighted system  
✅ **Filters** out risky products (IP, hazmat, Amazon sellers)  
✅ **Visualizes** data with modern charts and UI  
✅ **Exports** results in CSV/JSON formats  

**Tech Stack**: React + FastAPI + BeautifulSoup + TailwindCSS  
**Architecture**: 3-tier web application  
**Data Source**: Amazon.com (search results + product pages + seller info)  
**Scoring**: 3-pillar system (Demand 40%, Competition 35%, Profit 25%)  
**Filters**: 8-stage filtering pipeline  

**Result**: A powerful tool that helps Amazon sellers find profitable product opportunities while avoiding risky products.

---

*Last Updated: 2026-01-24*  
*Version: 2.0*  
*Author: Amazon Hunter Pro Team*
