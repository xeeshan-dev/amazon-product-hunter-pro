# 🚀 Amazon Hunter Pro - Quick Start Guide

## ✅ Current Status: FULLY OPERATIONAL

Both the backend and frontend are **currently running** and ready to use!

---

## 🌐 Access the Application

**Simply open your browser and go to:**

### 👉 http://localhost:5173

---

## 📊 What You'll See

The application interface includes:

### 1. **Header**
   - "Amazon Hunter Pro" title with gradient effect
   - "Advanced Product Intelligence & Market Analysis" subtitle

### 2. **Search Controls**
   - **Marketplace Selector**: Choose US, UK, or DE
   - **Filters Button**: Click to expand/collapse advanced filters
   - **Search Bar**: Enter product keywords (e.g., "yoga mat", "water bottle")
   - **Hunt Button**: Click to start the search

### 3. **Advanced Filters Panel** (Click "Filters" to expand)
   
   **Risk Controls:**
   - ☑️ Skip High Risk & Hazmat
   - ☑️ Skip Amazon as Seller
   - ☑️ Skip Brand as Seller
   
   **Quality Filters:**
   - 🎚️ Min Rating: 3.0 (adjust 1.0 - 5.0)
   - 🎚️ Min Margin: 20% (adjust 10% - 50%)
   
   **Sales Range:**
   - 🎚️ Min Sales: 50/mo (adjust 10 - 500)
   - 🎚️ Max Sales: 1000/mo (adjust 100 - 2000)

### 4. **Results Display**
   - **Market Overview Cards**: Revenue, Sales, Products stats
   - **Market Dominance Chart**: Bar chart of top products
   - **Product List**: Detailed cards with all metrics
   - **Badges**: 🏆 WINNER (high score) or ⚠️ VETOED (risky)

---

## 🎯 How to Use - Step by Step

### Step 1: Open the Application
```
Open browser → Navigate to http://localhost:5173
```

### Step 2: Configure Filters (Optional)
```
1. Click "Filters" button
2. Adjust sliders and checkboxes as needed
3. Filters apply automatically when you search
```

### Step 3: Search for Products
```
1. Enter keyword (e.g., "yoga mat")
2. Click "Hunt" button
3. Wait for results (may take 10-30 seconds)
```

### Step 4: Review Results
```
1. Check market overview stats
2. Review product list
3. Click any product card for detailed analysis
```

### Step 5: Filter Results Further
```
1. Use "Show Winners Only" button for best opportunities
2. Adjust filters and results update instantly
3. Export data using CSV or JSON buttons
```

---

## 💡 Example Search

### Finding Profitable Reselling Opportunities

**Goal:** Find products with good demand, low competition, and no Amazon/brand sellers

**Settings:**
1. **Marketplace:** US
2. **Keyword:** "water bottle"
3. **Filters:**
   - ✅ Skip Amazon as Seller
   - ✅ Skip Brand as Seller
   - Min Rating: 4.0
   - Min Margin: 25%
   - Sales Range: 100-500/month

**Expected Results:**
- Products with 4+ star ratings
- 25%+ profit margins
- 100-500 sales/month (sweet spot)
- No Amazon competition
- Third-party reselling opportunities

---

## 🎨 Understanding the Interface

### Product Cards Show:
- **Rank**: Position by revenue
- **Title**: Product name
- **Badge**: WINNER (good) or VETOED (risky)
- **Price**: Current selling price
- **Est. Revenue**: Monthly revenue estimate
- **Est. Sales**: Monthly sales estimate
- **Market Share**: % of total market

### Click a Product Card to See:
- **Radar Chart**: Score breakdown (Demand, Competition, Profit)
- **Total Score**: Overall opportunity score (0-100)
- **Financial Analysis**: Revenue, profit, margin, fees
- **Risk Assessment**: Brand risk, hazmat status
- **Product Specs**: Reviews, rating, BSR, category
- **Veto Reasons**: Why product was flagged (if applicable)

---

## 📈 Understanding the Scores

### Opportunity Score (0-100)
- **75-100**: 🏆 WINNER - Excellent opportunity
- **50-74**: Good opportunity
- **25-49**: Moderate opportunity
- **0-24**: Poor opportunity

### Score Components:
1. **Demand** (0-100): Based on sales volume, reviews, BSR
2. **Competition** (0-100): Based on number of sellers, ratings
3. **Profit** (0-100): Based on margin, fees, pricing

### Badges:
- **🏆 WINNER**: Score ≥75 AND Margin ≥30% AND Not Vetoed
- **⚠️ VETOED**: Failed critical checks (high risk, hazmat, etc.)

---

## 🔧 Advanced Features

### Export Data
- **CSV Export**: Spreadsheet format for analysis
- **JSON Export**: Full data with metadata

### Profit Calculator
- Click "Profit Calculator" button
- (Coming soon - currently shows placeholder)

### Show Winners Only
- Toggle to see only high-scoring products
- Filters: Score ≥75, Margin ≥30%, Not Vetoed

---

## 🎯 Filter Strategy Guide

### For New Sellers (Low Risk)
```
✅ Skip Amazon as Seller
✅ Skip Brand as Seller
✅ Skip High Risk & Hazmat
Min Rating: 4.0
Min Margin: 30%
Sales Range: 50-300/month
```

### For Experienced Sellers (Higher Volume)
```
✅ Skip Amazon as Seller
❌ Skip Brand as Seller (can negotiate)
✅ Skip High Risk & Hazmat
Min Rating: 3.5
Min Margin: 20%
Sales Range: 200-1000/month
```

### For Quick Wins (Fast Movers)
```
✅ Skip Amazon as Seller
✅ Skip Brand as Seller
❌ Skip High Risk & Hazmat
Min Rating: 4.5
Min Margin: 25%
Sales Range: 100-500/month
```

---

## 🚦 Service Status

### Backend API
- **URL**: http://127.0.0.1:8001
- **Status**: ✅ Running
- **Health Check**: http://127.0.0.1:8001/health

### Frontend App
- **URL**: http://localhost:5173
- **Status**: ✅ Running
- **Framework**: React + Vite

---

## 🐛 Troubleshooting

### Application Not Loading?
1. Check both services are running (see terminal windows)
2. Verify URLs: Backend (8001), Frontend (5173)
3. Clear browser cache and refresh

### No Results?
1. Try relaxing filter criteria
2. Use more general keywords
3. Check backend logs for errors

### Filters Not Working?
1. Filters apply when you click "Hunt"
2. Some filters need seller info (limited to 25 products)
3. Check "Showing X of Y products" count

### Slow Searches?
1. First search takes longer (scraping Amazon)
2. Reduce number of pages in backend
3. Disable seller info fetching if not needed

---

## 📞 Need Help?

### Check Documentation
- `STATUS.md` - Full application status
- `CONTINUATION_SUMMARY.md` - What was completed
- `test_api.py` - API testing script

### View Logs
- **Backend**: Check terminal running uvicorn
- **Frontend**: Check browser DevTools console (F12)

---

## 🎉 You're Ready!

**Everything is set up and running. Just open http://localhost:5173 and start hunting for profitable products!**

### Quick Test:
1. Go to http://localhost:5173
2. Enter "yoga mat" in search
3. Click "Hunt"
4. Wait for results
5. Explore the data!

---

**Happy Hunting! 🎯**

*Last Updated: 2026-01-24*
