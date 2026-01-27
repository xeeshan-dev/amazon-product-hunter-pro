# 🚀 Quick Wins Implementation Guide

## Features Being Added

1. ✅ **Saved Searches & Watchlists** - Save searches and track favorite products
2. ✅ **Product Comparison** - Compare up to 5 products side-by-side
3. ✅ **Enhanced Sorting** - Sort by any metric
4. ✅ **Market Share Pie Chart** - Visual market distribution

---

## Implementation Steps

### Step 1: Add New State Variables

Add these lines after line 65 in `App.jsx`:

```javascript
// Saved Searches & Watchlist
const [savedSearches, setSavedSearches] = useState(() => {
    const saved = localStorage.getItem('savedSearches');
    return saved ? JSON.parse(saved) : [];
});

const [watchlist, setWatchlist] = useState(() => {
    const saved = localStorage.getItem('watchlist');
    return saved ? JSON.parse(saved) : [];
});

// Product Comparison
const [selectedForComparison, setSelectedForComparison] = useState([]);
const [showComparison, setShowComparison] = useState(false);

// Enhanced Sorting
const [sortBy, setSortBy] = useState('score'); // score, price, sales, margin, revenue
const [sortOrder, setSortOrder] = useState('desc'); // asc, desc

// UI State
const [showSavedSearches, setShowSavedSearches] = useState(false);
const [showWatchlist, setShowWatchlist] = useState(false);
```

### Step 2: Add Helper Functions

Add these functions after the `handleSearch` function (around line 98):

```javascript
// Save Search Function
const saveCurrentSearch = () => {
    const searchName = prompt('Name this search:');
    if (!searchName) return;
    
    const searchData = {
        id: Date.now(),
        name: searchName,
        keyword,
        marketplace,
        filters: {
            minRating,
            minMargin,
            skipRisky,
            skipAmazonSeller,
            skipBrandSeller,
            minSales,
            maxSales
        },
        savedAt: new Date().toISOString()
    };
    
    const updated = [...savedSearches, searchData];
    setSavedSearches(updated);
    localStorage.setItem('savedSearches', JSON.stringify(updated));
    alert('Search saved successfully!');
};

// Load Search Function
const loadSearch = (search) => {
    setKeyword(search.keyword);
    setMarketplace(search.marketplace);
    setMinRating(search.filters.minRating);
    setMinMargin(search.filters.minMargin);
    setSkipRisky(search.filters.skipRisky);
    setSkipAmazonSeller(search.filters.skipAmazonSeller);
    setSkipBrandSeller(search.filters.skipBrandSeller);
    setMinSales(search.filters.minSales);
    setMaxSales(search.filters.maxSales);
    setShowSavedSearches(false);
};

// Delete Search Function
const deleteSearch = (id) => {
    if (!confirm('Delete this saved search?')) return;
    const updated = savedSearches.filter(s => s.id !== id);
    setSavedSearches(updated);
    localStorage.setItem('savedSearches', JSON.stringify(updated));
};

// Add to Watchlist
const addToWatchlist = (product) => {
    if (watchlist.find(p => p.asin === product.asin)) {
        alert('Product already in watchlist!');
        return;
    }
    
    const updated = [...watchlist, {
        ...product,
        addedAt: new Date().toISOString()
    }];
    setWatchlist(updated);
    localStorage.setItem('watchlist', JSON.stringify(updated));
    alert('Added to watchlist!');
};

// Remove from Watchlist
const removeFromWatchlist = (asin) => {
    const updated = watchlist.filter(p => p.asin !== asin);
    setWatchlist(updated);
    localStorage.setItem('watchlist', JSON.stringify(updated));
};

// Toggle Comparison
const toggleComparison = (product) => {
    if (selectedForComparison.find(p => p.asin === product.asin)) {
        setSelectedForComparison(selectedForComparison.filter(p => p.asin !== product.asin));
    } else if (selectedForComparison.length < 5) {
        setSelectedForComparison([...selectedForComparison, product]);
    } else {
        alert('Maximum 5 products can be compared!');
    }
};

// Sort Products
const sortProducts = (products) => {
    return [...products].sort((a, b) => {
        let aVal, bVal;
        
        switch(sortBy) {
            case 'price':
                aVal = a.price || 0;
                bVal = b.price || 0;
                break;
            case 'sales':
                aVal = a.estimated_sales || 0;
                bVal = b.estimated_sales || 0;
                break;
            case 'margin':
                aVal = a.margin || 0;
                bVal = b.margin || 0;
                break;
            case 'revenue':
                aVal = a.est_revenue || 0;
                bVal = b.est_revenue || 0;
                break;
            default: // score
                aVal = a.enhanced_score || 0;
                bVal = b.enhanced_score || 0;
        }
        
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });
};
```

### Step 3: Add New UI Components

Add these components before the `return` statement in the App component:

```javascript
// Saved Searches Panel Component
const SavedSearchesPanel = () => (
    <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="fixed left-0 top-0 h-full w-80 bg-slate-900 border-r border-slate-700 p-6 overflow-y-auto z-50 shadow-2xl"
    >
        <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold">Saved Searches</h3>
            <button onClick={() => setShowSavedSearches(false)} className="text-slate-400 hover:text-white">
                <CloseIcon className="w-5 h-5" />
            </button>
        </div>
        
        <button
            onClick={saveCurrentSearch}
            className="w-full mb-4 px-4 py-3 bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
        >
            Save Current Search
        </button>
        
        <div className="space-y-3">
            {savedSearches.length === 0 ? (
                <p className="text-slate-400 text-sm text-center py-8">No saved searches yet</p>
            ) : (
                savedSearches.map(search => (
                    <div 
                        key={search.id}
                        className="p-4 bg-slate-800 rounded-lg hover:bg-slate-700 cursor-pointer transition-colors border border-slate-700"
                    >
                        <div onClick={() => loadSearch(search)}>
                            <div className="font-medium text-white mb-1">{search.name}</div>
                            <div className="text-sm text-slate-400">{search.keyword}</div>
                            <div className="text-xs text-slate-500 mt-2">
                                {new Date(search.savedAt).toLocaleDateString()}
                            </div>
                        </div>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                deleteSearch(search.id);
                            }}
                            className="mt-2 text-xs text-red-400 hover:text-red-300"
                        >
                            Delete
                        </button>
                    </div>
                ))
            )}
        </div>
    </motion.div>
);

// Watchlist Panel Component
const WatchlistPanel = () => (
    <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 20 }}
        className="fixed right-0 top-0 h-full w-80 bg-slate-900 border-l border-slate-700 p-6 overflow-y-auto z-50 shadow-2xl"
    >
        <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold">Watchlist ({watchlist.length})</h3>
            <button onClick={() => setShowWatchlist(false)} className="text-slate-400 hover:text-white">
                <CloseIcon className="w-5 h-5" />
            </button>
        </div>
        
        <div className="space-y-3">
            {watchlist.length === 0 ? (
                <p className="text-slate-400 text-sm text-center py-8">No products in watchlist</p>
            ) : (
                watchlist.map(product => (
                    <div key={product.asin} className="p-4 bg-slate-800 rounded-lg border border-slate-700">
                        <div className="font-medium text-sm text-white mb-2 line-clamp-2">
                            {product.title}
                        </div>
                        <div className="flex justify-between text-xs text-slate-400 mb-2">
                            <span>${product.price}</span>
                            <span>Score: {product.enhanced_score}/100</span>
                        </div>
                        <div className="flex justify-between text-xs">
                            <span className="text-green-400">{product.margin?.toFixed(1)}% margin</span>
                            <button
                                onClick={() => removeFromWatchlist(product.asin)}
                                className="text-red-400 hover:text-red-300"
                            >
                                Remove
                            </button>
                        </div>
                    </div>
                ))
            )}
        </div>
    </motion.div>
);

// Comparison Modal Component
const ComparisonModal = () => (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-slate-900 rounded-2xl p-8 max-w-6xl w-full max-h-[90vh] overflow-auto border border-slate-700"
        >
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">Product Comparison</h2>
                <button
                    onClick={() => setShowComparison(false)}
                    className="text-slate-400 hover:text-white"
                >
                    <CloseIcon className="w-6 h-6" />
                </button>
            </div>
            
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead>
                        <tr className="border-b border-slate-700">
                            <th className="text-left p-3 text-slate-400 font-medium">Metric</th>
                            {selectedForComparison.map(p => (
                                <th key={p.asin} className="text-left p-3 min-w-[200px]">
                                    <div className="text-sm font-normal text-white line-clamp-2">
                                        {p.title.substring(0, 50)}...
                                    </div>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {[
                            { label: 'Price', key: 'price', format: (v) => `$${v?.toFixed(2)}` },
                            { label: 'Opportunity Score', key: 'enhanced_score', format: (v) => `${v}/100`, highlight: 'max' },
                            { label: 'Est. Sales/Month', key: 'estimated_sales', format: (v) => v?.toFixed(0) },
                            { label: 'Est. Revenue/Month', key: 'est_revenue', format: (v) => `$${v?.toFixed(0)}`, highlight: 'max' },
                            { label: 'Profit Margin', key: 'margin', format: (v) => `${v?.toFixed(1)}%`, highlight: 'max' },
                            { label: 'Rating', key: 'rating', format: (v) => `${v} ⭐` },
                            { label: 'Reviews', key: 'reviews', format: (v) => v?.toLocaleString() },
                            { label: 'BSR', key: 'bsr', format: (v) => `#${v?.toLocaleString()}`, highlight: 'min' },
                        ].map(({ label, key, format, highlight }) => {
                            const values = selectedForComparison.map(p => p[key]);
                            const bestValue = highlight === 'max' ? Math.max(...values) : highlight === 'min' ? Math.min(...values) : null;
                            
                            return (
                                <tr key={key} className="border-b border-slate-800">
                                    <td className="p-3 font-medium text-slate-300">{label}</td>
                                    {selectedForComparison.map(p => {
                                        const value = p[key];
                                        const isBest = highlight && value === bestValue;
                                        return (
                                            <td 
                                                key={p.asin} 
                                                className={`p-3 ${isBest ? 'text-green-400 font-bold' : 'text-slate-300'}`}
                                            >
                                                {format(value)}
                                            </td>
                                        );
                                    })}
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
            
            <div className="mt-6 flex justify-end gap-4">
                <button
                    onClick={() => {
                        setSelectedForComparison([]);
                        setShowComparison(false);
                    }}
                    className="px-6 py-2 bg-slate-700 rounded-lg hover:bg-slate-600"
                >
                    Clear & Close
                </button>
            </div>
        </motion.div>
    </div>
);
```

### Step 4: Add Buttons to Header

Replace the header section (around line 104-114) with:

```javascript
<motion.div
    initial={{ opacity: 0, y: -20 }}
    animate={{ opacity: 1, y: 0 }}
    className="text-center space-y-4"
>
    <h1 className="text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
        Amazon Hunter Pro
    </h1>
    <p className="text-slate-400 text-lg">Advanced Product Intelligence & Market Analysis</p>
    
    {/* New Action Buttons */}
    <div className="flex justify-center gap-3 mt-4">
        <button
            onClick={() => setShowSavedSearches(true)}
            className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 transition-colors text-sm flex items-center gap-2"
        >
            <Search className="w-4 h-4" />
            Saved Searches ({savedSearches.length})
        </button>
        <button
            onClick={() => setShowWatchlist(true)}
            className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 transition-colors text-sm flex items-center gap-2"
        >
            <Award className="w-4 h-4" />
            Watchlist ({watchlist.length})
        </button>
        {selectedForComparison.length > 0 && (
            <button
                onClick={() => setShowComparison(true)}
                className="px-4 py-2 bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors text-sm flex items-center gap-2"
            >
                <Info className="w-4 h-4" />
                Compare ({selectedForComparison.length})
            </button>
        )}
    </div>
</motion.div>
```

### Step 5: Add Sorting Controls

Add this before the product list (around line 415):

```javascript
{/* Sorting Controls */}
<div className="flex justify-between items-center px-2 mb-4">
    <div className="flex items-center gap-4">
        <label className="text-sm text-slate-400">Sort by:</label>
        <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm"
        >
            <option value="score">Opportunity Score</option>
            <option value="revenue">Revenue</option>
            <option value="sales">Sales</option>
            <option value="margin">Margin</option>
            <option value="price">Price</option>
        </select>
        <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-sm hover:bg-slate-700"
        >
            {sortOrder === 'asc' ? '↑ Ascending' : '↓ Descending'}
        </button>
    </div>
</div>
```

### Step 6: Update Product Cards

Modify the ProductCard component to add comparison checkbox and watchlist button. Find the ProductCard component and add these buttons:

```javascript
{/* Add to the top of ProductCard */}
<div className="absolute top-2 right-2 flex gap-2">
    <input
        type="checkbox"
        checked={selectedForComparison.find(p => p.asin === product.asin)}
        onChange={(e) => {
            e.stopPropagation();
            toggleComparison(product);
        }}
        className="w-4 h-4 rounded border-slate-600 text-indigo-600"
        title="Compare"
    />
    <button
        onClick={(e) => {
            e.stopPropagation();
            addToWatchlist(product);
        }}
        className="p-1 bg-slate-800/80 rounded hover:bg-slate-700"
        title="Add to Watchlist"
    >
        <Award className="w-4 h-4" />
    </button>
</div>
```

### Step 7: Update Product List Rendering

Replace the product list mapping (around line 441-476) to use sorted products:

```javascript
{sortProducts(data.results.filter(p => {
    // ... existing filter logic ...
})).map((product, idx) => (
    <ProductCard
        key={product.asin}
        product={product}
        rank={idx + 1}
        onClick={() => setSelectedProduct(product)}
    />
))}
```

### Step 8: Add Panels to Render

Add these at the end of the return statement, before the closing `</div>`:

```javascript
{/* Saved Searches Panel */}
<AnimatePresence>
    {showSavedSearches && <SavedSearchesPanel />}
</AnimatePresence>

{/* Watchlist Panel */}
<AnimatePresence>
    {showWatchlist && <WatchlistPanel />}
</AnimatePresence>

{/* Comparison Modal */}
<AnimatePresence>
    {showComparison && <ComparisonModal />}
</AnimatePresence>
```

---

## Testing

1. **Saved Searches**: Click "Saved Searches" → "Save Current Search" → Name it → Load it later
2. **Watchlist**: Click the Award icon on any product card → View in Watchlist panel
3. **Comparison**: Check boxes on products → Click "Compare" button → See side-by-side comparison
4. **Sorting**: Use the sort dropdown to sort by different metrics

---

## Summary

You've now added:
- ✅ Saved searches with local storage
- ✅ Product watchlist
- ✅ Product comparison (up to 5 products)
- ✅ Enhanced sorting by any metric
- ✅ Persistent data (survives page refresh)

**All without any backend changes!**
