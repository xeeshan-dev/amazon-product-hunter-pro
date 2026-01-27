# Quick Start Guide - Enhanced UI

## 🚀 Getting Started

### 1. Start the Application
```bash
# Terminal 1 - Backend API
cd amazon_hunter
py run_dev.py

# Terminal 2 - Frontend UI
cd web_app/frontend
npm run dev
```

### 2. Open in Browser
Navigate to: **http://localhost:5173**

---

## 🎯 New Features at a Glance

### Action Bar (Above Product List)
```
┌─────────────────────────────────────────────────────────────┐
│  [🏆 Show Winners Only]  [🧮 Profit Calculator]             │
│                                    [📥 Export CSV] [📥 JSON] │
└─────────────────────────────────────────────────────────────┘
```

### Enhanced Filters
```
┌──────────────────────────────────────────────────────────────┐
│  Risk Controls          Min Rating: 3.0      Min Margin: 20% │
│  ☑ Skip High Risk       ━━━━●━━━━━━          ━━━━━●━━━━━━   │
│                         1.0      5.0          10%      50%    │
└──────────────────────────────────────────────────────────────┘
```

### Product Card with Winner Badge
```
┌─────────────────────────────────────────────────────────────┐
│ #1  Premium Yoga Mat - Extra Thick...    [🏆 WINNER]        │
│                                                               │
│     Price        Revenue        Sales         Market Share   │
│     $24.99       $12,495        500/mo        15.2%          │
│                                                               │
│     Score: 82  |  Margin: 35%  |  Profit: $8.50/unit        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Using the Features

### Find Winning Products
1. **Search** for a keyword (e.g., "yoga mat")
2. **Wait** for results to load
3. **Click** "Show Winners Only" button
4. **Review** products with green 🏆 WINNER badges
5. **Click** any product for detailed analysis

### Export Your Data
1. **Complete** a search
2. **Click** "Export CSV" for Excel/Sheets
3. **Or click** "Export JSON" for programming
4. **File downloads** automatically

### Calculate Profits
1. **Click** "Profit Calculator" button
2. **Enter** your selling price
3. **Enter** your cost (COGS)
4. **Enter** estimated monthly sales
5. **See** instant profit breakdown

### Filter by Margin
1. **Click** "Filters" to expand
2. **Drag** "Min Margin" slider
3. **Products** below threshold hide automatically
4. **Focus** on profitable opportunities

---

## 🎨 Visual Indicators

### Product Status Colors
- **Green Border + 🏆 Badge** = Winning Product (Score ≥75, Margin ≥30%)
- **Red Border + ⚠️ Badge** = Vetoed Product (High risk, avoid)
- **Gray Border** = Normal Product (meets basic criteria)

### Score Interpretation
- **80-100** 🟢 Excellent (rare, act fast!)
- **75-79** 🟢 Very Good (winner threshold)
- **60-74** 🟡 Good (worth considering)
- **40-59** 🟡 Marginal (needs research)
- **0-39** 🔴 Poor (avoid)

### Margin Guidelines
- **40%+** 🟢 Excellent (room for ads)
- **30-39%** 🟢 Good (sustainable)
- **20-29%** 🟡 Acceptable (tight)
- **<20%** 🔴 Risky (avoid)

---

## 💡 Pro Tips

### Research Strategy
1. Start with broad search (no filters)
2. Review market overview cards
3. Enable "Show Winners Only"
4. Export top 10 winners to CSV
5. Analyze in Excel/Sheets
6. Use calculator to validate with your costs

### What Makes a Winner?
✅ High demand (good BSR, high sales)
✅ Low competition (3-15 FBA sellers)
✅ Good margins (30%+ profit)
✅ No IP risk (not vetoed)
✅ Stable pricing (not seasonal)

### Red Flags to Avoid
❌ Vetoed products (IP risk, hazmat)
❌ Amazon as seller (hard to compete)
❌ Too many FBA sellers (>20)
❌ Low margins (<20%)
❌ Very high BSR (>100,000)

---

## 🔧 Keyboard Shortcuts

- **Enter** - Submit search
- **Esc** - Close modals
- **Click product** - View details
- **Click outside modal** - Close

---

## 📱 Mobile Support

All features work on mobile:
- Responsive layout
- Touch-friendly buttons
- Swipe to scroll
- Tap to expand filters

---

## 🎯 Example Workflow

### Finding Your First Winner

1. **Search**: Enter "yoga mat"
   ```
   Results: 50 products found
   Total Market Revenue: $125,000/month
   ```

2. **Filter**: Click "Show Winners Only"
   ```
   Results: 8 winners found
   These products score 75+ with 30%+ margins
   ```

3. **Review**: Check top 3 winners
   ```
   #1: Score 82, Margin 35%, $12,495/mo revenue
   #2: Score 78, Margin 32%, $9,850/mo revenue
   #3: Score 76, Margin 31%, $8,200/mo revenue
   ```

4. **Export**: Click "Export CSV"
   ```
   File: amazon-hunter-yoga-mat-1737334567.csv
   Opens in Excel for deeper analysis
   ```

5. **Calculate**: Click "Profit Calculator"
   ```
   Selling Price: $24.99
   Your Cost: $10.00
   Monthly Units: 500
   
   Result: $6,750/month profit (27% margin)
   ```

6. **Decide**: Product #1 looks promising!
   - High score (82)
   - Good margin (35%)
   - Strong revenue ($12k/mo)
   - No veto flags
   - **Action**: Source samples and test!

---

## 🆘 Need Help?

### Check Status
- Backend: http://localhost:8000/health
- Frontend: http://localhost:5173

### Common Issues

**No products showing?**
- Lower the margin filter
- Disable "Winners Only"
- Try different keyword

**Export not working?**
- Check browser downloads
- Allow pop-ups
- Try different browser

**Calculator not showing?**
- Click button in action bar
- Check browser console (F12)
- Refresh page

**Backend error?**
- Check terminal for errors
- Restart: `py run_dev.py`
- Check Python dependencies

---

## 🎉 You're Ready!

Start finding winning products that generate real sales! 🚀

**Remember**: Winners have Score ≥75, Margin ≥30%, and No Veto flags.

Happy hunting! 🎯
