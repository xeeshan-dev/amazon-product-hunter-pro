# 🚀 Amazon Hunter Pro - Quick Technical Reference

## 📋 At a Glance

**What it does**: Finds profitable Amazon products by scraping data, analyzing opportunities, and filtering risks.

**Tech Stack**: React + FastAPI + BeautifulSoup + TailwindCSS

**Architecture**: 3-tier web application (Frontend → Backend → Amazon)

---

## 🔧 Technology Stack

### Frontend (Port 5173)
- **React 18.2** - UI framework
- **Vite 5.0** - Build tool (faster than Webpack)
- **TailwindCSS 3.3** - Utility-first CSS
- **Framer Motion 10.16** - Animations
- **Recharts 2.10** - Charts (Bar, Radar)
- **Axios 1.6** - HTTP client

### Backend (Port 8001)
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server
- **BeautifulSoup4** - HTML parsing
- **Requests** - HTTP library
- **Pydantic** - Data validation

---

## 📊 Data Sources

### 1. Amazon Search Results
**URL**: `amazon.com/s?k={keyword}&page={page}`
**Data**: ASIN, title, price, rating, reviews

### 2. Product Detail Pages
**URL**: `amazon.com/dp/{ASIN}`
**Data**: BSR, description, features, images

### 3. Seller Information (AOD)
**URL**: `amazon.com/gp/aod/ajax/...?asin={ASIN}`
**Data**: FBA/FBM sellers, Amazon seller status, prices

---

## 🎯 Scoring System (3 Pillars)

```
Total Score = (Demand × 40%) + (Competition × 35%) + (Profit × 25%)
```

### Pillar 1: Demand & Trend (40%)
- **BSR Score** (40%) - Lower BSR = higher score
- **BSR Stability** (30%) - Consistent demand
- **Sales Velocity** (30%) - Monthly sales volume

### Pillar 2: Competition (35%)
- **FBA Seller Count** (40%) - Sweet spot: 3-15 sellers
- **Review Vulnerability** (35%) - Competitors with <400 reviews
- **Amazon Presence** (25%) - Amazon NOT a seller = 100 points

### Pillar 3: Profit & Risk (25%)
- **Profit Margin** (50%) - Target: 30%+
- **Price Point** (25%) - Sweet spot: $20-$50
- **Risk Factors** (25%) - IP risk, hazmat

---

## 🔍 Filter Pipeline (8 Stages)

```
1. Rating < min_rating → SKIP
2. Brand risk + skip_risky_brands → SKIP
3. Hazmat + skip_hazmat → SKIP
4. Margin < min_margin → SKIP
5. Sales outside range → SKIP
6. Fetch seller info (top 25 only)
7. Amazon seller + skip_amazon_seller → SKIP
8. Brand seller + skip_brand_seller → SKIP
```

---

## 💰 Financial Calculations

### Sales Estimation
```python
Sales = 40,000 × (BSR ^ -0.4)
# Example: BSR 10,000 → ~125 sales/month
```

### FBA Fees
```python
Referral Fee = price × 15%  # Most categories
FBA Fee = $2.50 to $5.42    # Based on size
Storage Fee = $0.75/cu ft   # Monthly
```

### Profit Margin
```python
Net Profit = Price - Amazon Fees - COGS
Margin = (Net Profit / Price) × 100
# Target: 30%+
```

---

## 🎨 Frontend Components

```
App.jsx
├── Search Controls (marketplace, filters, search bar)
├── Filters Panel (collapsible)
│   ├── Risk Controls (3 checkboxes)
│   ├── Quality Filters (2 sliders)
│   └── Sales Range (2 sliders)
├── Results Section
│   ├── Market Overview Cards (4 stats)
│   ├── Action Bar (export, calculator)
│   ├── Market Dominance Chart (bar chart)
│   └── Product Cards (clickable)
└── Modals
    ├── Product Detail (radar chart, financials)
    └── Profit Calculator
```

---

## 🔄 Data Flow

```
1. User enters "yoga mat" → Clicks "Hunt"
2. Frontend sends POST /api/search
3. Backend scrapes Amazon search results
4. Extracts product data (ASIN, price, rating, etc.)
5. Fetches seller info for top 25 products
6. Calculates scores (3-pillar system)
7. Checks risks (brand, hazmat)
8. Calculates fees and margins
9. Applies 8-stage filter pipeline
10. Returns JSON with filtered results
11. Frontend displays products with charts
```

---

## 📁 Key Files

```
amazon_hunter/
├── src/
│   ├── scraper/amazon_scraper.py       # 731 lines - Web scraping
│   ├── analysis/enhanced_scoring.py    # 622 lines - 3-pillar scoring
│   ├── analysis/fba_calculator.py      # Fee calculations
│   ├── risk/brand_risk.py              # 295 risky brands
│   └── risk/hazmat_detector.py         # 100+ hazmat keywords
├── web_app/
│   ├── backend/main.py                 # 262 lines - FastAPI app
│   └── frontend/src/App.jsx            # 792 lines - React UI
└── TECHNICAL_DOCUMENTATION.md          # Full docs
```

---

## 🚀 Running the App

### Backend
```bash
cd web_app/backend
python -m uvicorn main:app --reload --port 8001
```

### Frontend
```bash
cd web_app/frontend
npm run dev
```

### Access
- Frontend: http://localhost:5173
- Backend: http://127.0.0.1:8001
- API Docs: http://127.0.0.1:8001/docs

---

## 🎯 API Endpoints

### POST /api/search
**Request**:
```json
{
  "keyword": "yoga mat",
  "marketplace": "US",
  "pages": 2,
  "min_rating": 4.0,
  "skip_amazon_seller": true,
  "skip_brand_seller": true,
  "min_margin": 20.0,
  "min_sales": 50,
  "max_sales": 1000
}
```

**Response**:
```json
{
  "summary": {
    "total_products": 25,
    "total_revenue": 125000,
    "avg_revenue": 5000
  },
  "results": [
    {
      "asin": "B0XXXXXXXX",
      "title": "Premium Yoga Mat",
      "price": 29.99,
      "enhanced_score": 82,
      "margin": 43.7,
      "seller_info": {
        "amazon_seller": false,
        "fba_count": 8
      }
    }
  ]
}
```

---

## 🔒 Security Features

1. **User Agent Rotation** - Prevents Amazon blocking
2. **Rate Limiting** - Max 25 seller info fetches
3. **Input Validation** - Pydantic models
4. **Error Handling** - Try/catch everywhere
5. **CORS** - Configured for cross-origin requests

---

## 📈 Performance Optimizations

1. **Early Filtering** - Filter before expensive operations
2. **Session Reuse** - HTTP connection pooling
3. **Minimal Delays** - 0.5s between pages
4. **Data Limits** - Max 50 products returned
5. **Seller Info Limit** - Top 25 products only

---

## 🎓 Key Algorithms

### BSR to Sales Conversion
```python
def estimate_sales(bsr, category="default"):
    C = 40000  # Category constant
    k = 0.4    # Decay factor
    
    if bsr < 100:
        return 3000 + (100 - bsr) * 50
    else:
        return int(C * (bsr ** -k))
```

### Brand Seller Detection
```python
def is_brand_seller(product):
    seller = product['seller_info']['seller_name'].lower()
    brand = product['brand'].lower()
    
    # Check if seller name contains brand or vice versa
    return brand in seller or seller in brand
```

### Market Share Calculation
```python
def calculate_market_share(products):
    total_revenue = sum(p['est_revenue'] for p in products)
    
    for p in products:
        p['market_share'] = (p['est_revenue'] / total_revenue) * 100
```

---

## 🎨 Design System

### Colors
- **Background**: `#0f172a` (slate-900)
- **Accent**: `#6366f1` (indigo-500)
- **Success**: `#10b981` (green-500)
- **Warning**: `#f59e0b` (amber-500)
- **Error**: `#ef4444` (red-500)

### Typography
- **Font**: System fonts (San Francisco, Segoe UI, etc.)
- **Sizes**: 12px (xs), 14px (sm), 16px (base), 20px (lg), 24px (xl)

### Spacing
- **Scale**: 4px, 8px, 12px, 16px, 24px, 32px, 48px

---

## 🐛 Common Issues

### No Products Showing
**Cause**: Filters too strict
**Fix**: Uncheck filters, lower min margin, widen sales range

### Slow Searches
**Cause**: Fetching seller info for many products
**Fix**: Reduce pages or disable seller info fetching

### Amazon Blocking
**Cause**: Too many requests
**Fix**: Increase delays, reduce pages, use VPN

---

## 📚 Resources

- **Full Documentation**: `TECHNICAL_DOCUMENTATION.md`
- **Quick Start**: `QUICK_START.md`
- **Troubleshooting**: `TROUBLESHOOTING.md`
- **Status**: `STATUS.md`

---

## ✨ Summary

**Amazon Hunter Pro** scrapes Amazon, analyzes products using a 3-pillar scoring system, filters risks, and presents insights through a modern React UI.

**Key Features**:
- ✅ Real-time Amazon scraping
- ✅ 3-pillar opportunity scoring
- ✅ 8-stage filter pipeline
- ✅ Risk detection (IP, hazmat)
- ✅ FBA fee calculations
- ✅ Modern, animated UI
- ✅ CSV/JSON export

**Perfect for**: Amazon FBA sellers looking for profitable product opportunities.

---

*Version: 2.0 | Last Updated: 2026-01-24*
