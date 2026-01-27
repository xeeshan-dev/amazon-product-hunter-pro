import { useState } from 'react'
import axios from 'axios'
import { Search, Loader2, TrendingUp, DollarSign, ShoppingCart, AlertTriangle, X as CloseIcon, Filter, Globe, ShieldAlert, Download, Calculator, Award, Info } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Utility for class merging
function cn(...inputs) {
    return twMerge(clsx(inputs))
}

const API_URL = 'http://127.0.0.1:8001/api'

// Export utilities
const exportToCSV = (products, keyword) => {
    const headers = ['Rank', 'Title', 'ASIN', 'Price', 'Revenue', 'Sales', 'Margin%', 'Profit', 'Score', 'Rating', 'Reviews', 'BSR', 'Vetoed']
    const rows = products.map((p, idx) => [
        idx + 1, `"${p.title?.replace(/"/g, '""')}"`, p.asin, p.price?.toFixed(2), p.est_revenue?.toFixed(0),
        Math.round(p.estimated_sales), p.margin?.toFixed(1), p.est_profit?.toFixed(2), p.enhanced_score,
        p.rating, p.reviews, p.bsr, p.is_vetoed ? 'YES' : 'NO'
    ])
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `amazon-hunter-${keyword}-${Date.now()}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
}

const exportToJSON = (data, keyword) => {
    const json = JSON.stringify({ exported_at: new Date().toISOString(), keyword, ...data }, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `amazon-hunter-${keyword}-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
}

function App() {
    const [selectedProduct, setSelectedProduct] = useState(null)
    const [keyword, setKeyword] = useState('')
    const [loading, setLoading] = useState(false)
    const [data, setData] = useState(null)
    const [error, setError] = useState(null)
    const [marketplace, setMarketplace] = useState('US')
    const [minRating, setMinRating] = useState(3.0)
    const [skipRisky, setSkipRisky] = useState(true)
    const [showFilters, setShowFilters] = useState(false)
    const [minMargin, setMinMargin] = useState(20)
    const [showProfitCalc, setShowProfitCalc] = useState(false)
    const [showWinnersOnly, setShowWinnersOnly] = useState(false)
    const [skipAmazonSeller, setSkipAmazonSeller] = useState(true)
    const [skipBrandSeller, setSkipBrandSeller] = useState(true)
    const [minSales, setMinSales] = useState(50)
    const [maxSales, setMaxSales] = useState(1000)

    // NEW: Saved Searches & Watchlist (with localStorage)
    const [savedSearches, setSavedSearches] = useState(() => {
        const saved = localStorage.getItem('savedSearches')
        return saved ? JSON.parse(saved) : []
    })
    const [watchlist, setWatchlist] = useState(() => {
        const saved = localStorage.getItem('watchlist')
        return saved ? JSON.parse(saved) : []
    })

    // NEW: Product Comparison
    const [selectedForComparison, setSelectedForComparison] = useState([])
    const [showComparison, setShowComparison] = useState(false)

    // NEW: Enhanced Sorting
    const [sortBy, setSortBy] = useState('score') // score, price, sales, margin, revenue
    const [sortOrder, setSortOrder] = useState('desc') // asc, desc

    // NEW: UI State
    const [showSavedSearches, setShowSavedSearches] = useState(false)
    const [showWatchlist, setShowWatchlist] = useState(false)

    const handleSearch = async (e) => {
        e.preventDefault()
        if (!keyword.trim()) return

        setLoading(true)
        setError(null)
        setData(null)

        try {
            const response = await axios.post(`${API_URL}/search`, {
                keyword,
                marketplace,
                min_rating: minRating,
                skip_risky_brands: skipRisky,
                skip_hazmat: skipRisky,
                pages: 2, // default to 2 pages
                // Send all filter parameters to backend
                skip_amazon_seller: skipAmazonSeller,
                skip_brand_seller: skipBrandSeller,
                min_margin: minMargin,
                min_sales: minSales,
                max_sales: maxSales,
                fetch_seller_info: true
            })
            setData(response.data)
        } catch (err) {
            setError('Failed to fetch data. Please try again.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    // NEW: Save Search Function
    const saveCurrentSearch = () => {
        const searchName = prompt('Name this search:')
        if (!searchName) return

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
        }

        const updated = [...savedSearches, searchData]
        setSavedSearches(updated)
        localStorage.setItem('savedSearches', JSON.stringify(updated))
        alert('Search saved successfully!')
    }

    // NEW: Load Search Function
    const loadSearch = (search) => {
        setKeyword(search.keyword)
        setMarketplace(search.marketplace)
        setMinRating(search.filters.minRating)
        setMinMargin(search.filters.minMargin)
        setSkipRisky(search.filters.skipRisky)
        setSkipAmazonSeller(search.filters.skipAmazonSeller)
        setSkipBrandSeller(search.filters.skipBrandSeller)
        setMinSales(search.filters.minSales)
        setMaxSales(search.filters.maxSales)
        setShowSavedSearches(false)
    }

    // NEW: Delete Search Function
    const deleteSearch = (id) => {
        if (!confirm('Delete this saved search?')) return
        const updated = savedSearches.filter(s => s.id !== id)
        setSavedSearches(updated)
        localStorage.setItem('savedSearches', JSON.stringify(updated))
    }

    // NEW: Add to Watchlist
    const addToWatchlist = (product) => {
        if (watchlist.find(p => p.asin === product.asin)) {
            alert('Product already in watchlist!')
            return
        }

        const updated = [...watchlist, {
            ...product,
            addedAt: new Date().toISOString()
        }]
        setWatchlist(updated)
        localStorage.setItem('watchlist', JSON.stringify(updated))
        alert('Added to watchlist!')
    }

    // NEW: Remove from Watchlist
    const removeFromWatchlist = (asin) => {
        const updated = watchlist.filter(p => p.asin !== asin)
        setWatchlist(updated)
        localStorage.setItem('watchlist', JSON.stringify(updated))
    }

    // NEW: Toggle Comparison
    const toggleComparison = (product) => {
        if (selectedForComparison.find(p => p.asin === product.asin)) {
            setSelectedForComparison(selectedForComparison.filter(p => p.asin !== product.asin))
        } else if (selectedForComparison.length < 5) {
            setSelectedForComparison([...selectedForComparison, product])
        } else {
            alert('Maximum 5 products can be compared!')
        }
    }

    // NEW: Sort Products
    const sortProducts = (products) => {
        return [...products].sort((a, b) => {
            let aVal, bVal

            switch (sortBy) {
                case 'price':
                    aVal = a.price || 0
                    bVal = b.price || 0
                    break
                case 'sales':
                    aVal = a.estimated_sales || 0
                    bVal = b.estimated_sales || 0
                    break
                case 'margin':
                    aVal = a.margin || 0
                    bVal = b.margin || 0
                    break
                case 'revenue':
                    aVal = a.est_revenue || 0
                    bVal = b.est_revenue || 0
                    break
                default: // score
                    aVal = a.enhanced_score || 0
                    bVal = b.enhanced_score || 0
            }

            return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
        })
    }

    // NEW: Saved Searches Panel Component
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
                                    e.stopPropagation()
                                    deleteSearch(search.id)
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
    )

    // NEW: Watchlist Panel Component
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
    )

    // NEW: Comparison Modal Component
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
                                const values = selectedForComparison.map(p => p[key])
                                const bestValue = highlight === 'max' ? Math.max(...values) : highlight === 'min' ? Math.min(...values) : null

                                return (
                                    <tr key={key} className="border-b border-slate-800">
                                        <td className="p-3 font-medium text-slate-300">{label}</td>
                                        {selectedForComparison.map(p => {
                                            const value = p[key]
                                            const isBest = highlight && value === bestValue
                                            return (
                                                <td
                                                    key={p.asin}
                                                    className={`p-3 ${isBest ? 'text-green-400 font-bold' : 'text-slate-300'}`}
                                                >
                                                    {format(value)}
                                                </td>
                                            )
                                        })}
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>

                <div className="mt-6 flex justify-end gap-4">
                    <button
                        onClick={() => {
                            setSelectedForComparison([])
                            setShowComparison(false)
                        }}
                        className="px-6 py-2 bg-slate-700 rounded-lg hover:bg-slate-600"
                    >
                        Clear & Close
                    </button>
                </div>
            </motion.div>
        </div>
    )

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 to-slate-900 text-white p-6 font-sans">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center space-y-4"
                >
                    <h1 className="text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-cyan-400">
                        Amazon Hunter Pro
                    </h1>
                    <p className="text-slate-400 text-lg">Advanced Product Intelligence & Market Analysis</p>

                    {/* NEW: Action Buttons */}
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

                {/* Search & Filters */}
                <div className="max-w-2xl mx-auto relative z-10 space-y-4">

                    {/* Market & Filter Toggle */}
                    <div className="flex justify-center gap-4">
                        <div className="flex bg-slate-800 rounded-lg p-1 border border-slate-700">
                            {['US', 'UK', 'DE'].map((m) => (
                                <button
                                    key={m}
                                    onClick={() => setMarketplace(m)}
                                    className={cn(
                                        "px-4 py-1.5 rounded-md text-sm font-medium transition-all text-white",
                                        marketplace === m ? "bg-indigo-600 shadow-lg" : "text-slate-400 hover:text-white"
                                    )}
                                >
                                    {m}
                                </button>
                            ))}
                        </div>
                        <button
                            onClick={() => setShowFilters(!showFilters)}
                            className={cn(
                                "flex items-center gap-2 px-4 py-2 rounded-lg border transition-all text-sm font-medium",
                                showFilters ? "bg-indigo-600/20 border-indigo-500/50 text-indigo-300" : "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                            )}
                        >
                            <Filter className="w-4 h-4" /> Filters
                        </button>
                    </div>

                    {/* Collapsible Filters */}
                    <AnimatePresence>
                        {showFilters && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="overflow-hidden"
                            >
                                <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-4">
                                    <div>
                                        <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
                                            <ShieldAlert className="w-4 h-4 text-orange-400" /> Risk Controls
                                        </label>
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-3 bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                                                <input
                                                    type="checkbox"
                                                    checked={skipRisky}
                                                    onChange={(e) => setSkipRisky(e.target.checked)}
                                                    className="w-4 h-4 rounded border-slate-600 text-indigo-600 focus:ring-indigo-500 bg-slate-800"
                                                />
                                                <span className="text-sm text-slate-300">Skip High Risk & Hazmat</span>
                                            </div>
                                            <div className="flex items-center gap-3 bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                                                <input
                                                    type="checkbox"
                                                    checked={skipAmazonSeller}
                                                    onChange={(e) => setSkipAmazonSeller(e.target.checked)}
                                                    className="w-4 h-4 rounded border-slate-600 text-indigo-600 focus:ring-indigo-500 bg-slate-800"
                                                />
                                                <span className="text-sm text-slate-300">Skip Amazon as Seller</span>
                                            </div>
                                            <div className="flex items-center gap-3 bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                                                <input
                                                    type="checkbox"
                                                    checked={skipBrandSeller}
                                                    onChange={(e) => setSkipBrandSeller(e.target.checked)}
                                                    className="w-4 h-4 rounded border-slate-600 text-indigo-600 focus:ring-indigo-500 bg-slate-800"
                                                />
                                                <span className="text-sm text-slate-300">Skip Brand as Seller</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
                                            <TrendingUp className="w-4 h-4 text-green-400" /> Quality Filters
                                        </label>
                                        <div className="space-y-3">
                                            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                                                <label className="text-xs text-slate-400 mb-1 block">Min Rating: {minRating}</label>
                                                <input
                                                    type="range"
                                                    min="1"
                                                    max="5"
                                                    step="0.5"
                                                    value={minRating}
                                                    onChange={(e) => setMinRating(parseFloat(e.target.value))}
                                                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                                                />
                                                <div className="flex justify-between text-xs text-slate-500 mt-1">
                                                    <span>1.0</span>
                                                    <span>5.0</span>
                                                </div>
                                            </div>
                                            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                                                <label className="text-xs text-slate-400 mb-1 block">Min Margin: {minMargin}%</label>
                                                <input
                                                    type="range"
                                                    min="10"
                                                    max="50"
                                                    step="5"
                                                    value={minMargin}
                                                    onChange={(e) => setMinMargin(parseInt(e.target.value))}
                                                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                                                />
                                                <div className="flex justify-between text-xs text-slate-500 mt-1">
                                                    <span>10%</span>
                                                    <span>50%</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div>
                                        <label className="flex items-center gap-2 text-sm font-medium text-slate-300 mb-2">
                                            <ShoppingCart className="w-4 h-4 text-blue-400" /> Sales Range
                                        </label>
                                        <div className="space-y-3">
                                            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                                                <label className="text-xs text-slate-400 mb-1 block">Min Sales: {minSales}/mo</label>
                                                <input
                                                    type="range"
                                                    min="10"
                                                    max="500"
                                                    step="10"
                                                    value={minSales}
                                                    onChange={(e) => setMinSales(parseInt(e.target.value))}
                                                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                                />
                                                <div className="flex justify-between text-xs text-slate-500 mt-1">
                                                    <span>10</span>
                                                    <span>500</span>
                                                </div>
                                            </div>
                                            <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-800">
                                                <label className="text-xs text-slate-400 mb-1 block">Max Sales: {maxSales}/mo</label>
                                                <input
                                                    type="range"
                                                    min="100"
                                                    max="2000"
                                                    step="100"
                                                    value={maxSales}
                                                    onChange={(e) => setMaxSales(parseInt(e.target.value))}
                                                    className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                                                />
                                                <div className="flex justify-between text-xs text-slate-500 mt-1">
                                                    <span>100</span>
                                                    <span>2000</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                    <form onSubmit={handleSearch} className="relative group">
                        <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl blur opacity-30 group-hover:opacity-100 transition duration-500"></div>
                        <div className="relative flex items-center bg-slate-800 rounded-xl border border-slate-700 shadow-xl overflow-hidden">
                            <Search className="ml-4 text-slate-400 w-6 h-6" />
                            <input
                                type="text"
                                value={keyword}
                                onChange={(e) => setKeyword(e.target.value)}
                                placeholder="Enter product keyword (e.g. 'yoga mat')..."
                                className="w-full bg-transparent outline-none border-none focus:ring-0 text-lg py-4 px-4 text-white placeholder-slate-500"
                            />
                            <button
                                type="submit"
                                disabled={loading}
                                className="mr-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {loading ? <Loader2 className="animate-spin w-5 h-5" /> : 'Hunt'}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Error State */}
                {error && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-center"
                    >
                        {error}
                    </motion.div>
                )}

                {/* Main Content */}
                {data && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="space-y-8"
                    >
                        {/* Market Overview Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <StatCard
                                title="Total Market Revenue"
                                value={`$${data.summary.total_revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                                icon={DollarSign}
                                color="text-green-400"
                            />
                            <StatCard
                                title="Avg Revenue/Listing"
                                value={`$${data.summary.avg_revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
                                icon={TrendingUp}
                                color="text-blue-400"
                            />
                            <StatCard
                                title="Avg Monthly Sales"
                                value={Math.round(data.summary.avg_sales).toLocaleString()}
                                icon={ShoppingCart}
                                color="text-purple-400"
                            />
                            <StatCard
                                title="Products Analyzed"
                                value={data.summary.total_products}
                                icon={Search}
                                color="text-orange-400"
                            />
                        </div>

                        {/* Action Bar */}
                        <div className="flex flex-wrap gap-3 items-center justify-between bg-slate-800/30 rounded-xl p-4 border border-slate-700/50">
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setShowWinnersOnly(!showWinnersOnly)}
                                    className={cn(
                                        "flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all",
                                        showWinnersOnly
                                            ? "bg-green-600 text-white"
                                            : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                                    )}
                                >
                                    <Award className="w-4 h-4" />
                                    {showWinnersOnly ? 'Showing Winners' : 'Show Winners Only'}
                                </button>
                                <button
                                    onClick={() => setShowProfitCalc(true)}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-all"
                                >
                                    <Calculator className="w-4 h-4" />
                                    Profit Calculator
                                </button>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={() => exportToCSV(data.results, keyword)}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-600 hover:bg-green-500 text-white font-medium transition-all"
                                >
                                    <Download className="w-4 h-4" />
                                    Export CSV
                                </button>
                                <button
                                    onClick={() => exportToJSON(data, keyword)}
                                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition-all"
                                >
                                    <Download className="w-4 h-4" />
                                    Export JSON
                                </button>
                            </div>
                        </div>

                        {/* Split View: Chart + Top Products */}
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                            {/* Market Share Chart */}
                            <div className="lg:col-span-1 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6">
                                <h3 className="text-xl font-bold mb-6 text-slate-200">Market Dominance</h3>
                                <div className="h-[400px]">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={data.results.slice(0, 10)} layout="vertical" margin={{ left: 0 }}>
                                            <XAxis type="number" hide />
                                            <YAxis
                                                dataKey="title"
                                                type="category"
                                                width={100}
                                                tickFormatter={(val) => val.length > 15 ? val.substring(0, 15) + '...' : val}
                                                tick={{ fill: '#94a3b8', fontSize: 12 }}
                                            />
                                            <Tooltip
                                                contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                                                formatter={(value) => [`$${value.toLocaleString()}`, 'Revenue']}
                                                labelFormatter={(label) => label.substring(0, 50)}
                                            />
                                            <Bar dataKey="est_revenue" radius={[0, 4, 4, 0]}>
                                                {data.results.slice(0, 10).map((entry, index) => (
                                                    <Cell key={`cell-${index}`} fill={index === 0 ? '#818cf8' : '#4f46e5'} fillOpacity={index === 0 ? 1 : 0.6} />
                                                ))}
                                            </Bar>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Product List */}
                            <div className="lg:col-span-2 space-y-4">
                                <div className="flex justify-between items-center px-2">
                                    <div>
                                        <h3 className="text-xl font-bold text-slate-200">Top Opportunities</h3>
                                        <span className="text-xs text-slate-400 mt-1 block">
                                            Showing {data.results.filter(p => {
                                                if (showWinnersOnly && (p.is_vetoed || p.enhanced_score < 75 || p.margin < 30)) return false
                                                if (p.margin < minMargin) return false
                                                if (skipAmazonSeller && p.seller_info?.amazon_seller) return false
                                                if (skipBrandSeller && p.seller_info?.seller_name && p.brand) {
                                                    const sellerLower = p.seller_info.seller_name.toLowerCase()
                                                    const brandLower = p.brand.toLowerCase()
                                                    if (sellerLower.includes(brandLower) || brandLower.includes(sellerLower)) return false
                                                }
                                                const sales = p.estimated_sales || 0
                                                if (sales < minSales || sales > maxSales) return false
                                                return true
                                            }).length} of {data.results.length} products
                                        </span>
                                    </div>
                                    <span className="text-sm text-slate-400">
                                        {showWinnersOnly ? 'Winners Only' : 'Click for Details'}
                                    </span>
                                </div>

                                {/* NEW: Sorting Controls */}
                                <div className="flex justify-between items-center px-2 py-2 bg-slate-800/30 rounded-lg">
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

                                <div className="grid gap-4">
                                    {sortProducts(data.results
                                        .filter(p => {
                                            // Winner filter
                                            if (showWinnersOnly) {
                                                if (p.is_vetoed || p.enhanced_score < 75 || p.margin < 30) return false
                                            }

                                            // Margin filter
                                            if (p.margin < minMargin) return false

                                            // Amazon seller filter
                                            if (skipAmazonSeller && p.seller_info?.amazon_seller) return false

                                            // Brand seller filter (check if seller name matches brand name)
                                            if (skipBrandSeller && p.seller_info?.seller_name && p.brand) {
                                                const sellerLower = p.seller_info.seller_name.toLowerCase()
                                                const brandLower = p.brand.toLowerCase()
                                                if (sellerLower.includes(brandLower) || brandLower.includes(sellerLower)) {
                                                    return false
                                                }
                                            }

                                            // Sales range filter
                                            const sales = p.estimated_sales || 0
                                            if (sales < minSales || sales > maxSales) return false

                                            return true
                                        }))
                                        .map((product, idx) => (
                                            <ProductCard
                                                key={product.asin}
                                                product={product}
                                                rank={idx + 1}
                                                onClick={() => setSelectedProduct(product)}
                                                onToggleComparison={toggleComparison}
                                                onAddToWatchlist={addToWatchlist}
                                                isSelected={selectedForComparison.find(p => p.asin === product.asin)}
                                            />
                                        ))}
                                </div>
                            </div>

                        </div>
                    </motion.div>
                )}
            </div>

            {/* Profit Calculator Modal */}
            <AnimatePresence>
                {showProfitCalc && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setShowProfitCalc(false)}
                            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                        />
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="relative z-10 w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-6"
                        >
                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                    <Calculator className="w-6 h-6 text-indigo-400" />
                                    Profit Calculator
                                </h2>
                                <button onClick={() => setShowProfitCalc(false)} className="p-2 hover:bg-slate-800 rounded-full transition-colors">
                                    <CloseIcon className="w-6 h-6 text-slate-400" />
                                </button>
                            </div>
                            <div className="text-center text-slate-400 py-8">
                                <Calculator className="w-16 h-16 mx-auto mb-4 text-slate-600" />
                                <p>Profit calculator coming soon!</p>
                                <p className="text-sm mt-2">Use the product details to see profit breakdown</p>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Product Detail Modal */}
            <AnimatePresence>
                {selectedProduct && (
                    <ProductDetailModal
                        product={selectedProduct}
                        onClose={() => setSelectedProduct(null)}
                    />
                )}
            </AnimatePresence>
        </div>
    )
}

function StatCard({ title, value, icon: Icon, color }) {
    return (
        <motion.div
            whileHover={{ y: -5 }}
            className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6 flex flex-col justify-between h-32"
        >
            <div className="flex justify-between items-start">
                <span className="text-slate-400 font-medium text-sm uppercase">{title}</span>
                <div className={`p-2 rounded-lg bg-slate-700/50 ${color}`}>
                    <Icon className="w-5 h-5" />
                </div>
            </div>
            <span className="text-3xl font-bold text-slate-100">{value}</span>
        </motion.div>
    )
}

function ProductCard({ product, rank, onClick, onToggleComparison, onAddToWatchlist, isSelected }) {
    const isVetoed = product.is_vetoed
    const isWinner = !isVetoed && product.enhanced_score >= 75 && product.margin >= 30

    return (
        <motion.div
            layoutId={`product-${product.asin}`}
            onClick={onClick}
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            whileHover={{ scale: 1.01, backgroundColor: 'rgba(30, 41, 59, 1)' }}
            viewport={{ once: true }}
            className={cn(
                "group relative bg-slate-800 rounded-xl border p-5 transition-all cursor-pointer",
                isVetoed ? "border-red-500/30 bg-red-900/10" :
                    isWinner ? "border-green-500/50 bg-green-900/10" :
                        "border-slate-700 hover:border-indigo-500/50"
            )}
        >
            {/* NEW: Comparison & Watchlist Controls */}
            <div className="absolute top-3 right-3 flex gap-2 z-10">
                <label
                    className="flex items-center gap-1 px-2 py-1 bg-slate-900/80 rounded hover:bg-slate-800 cursor-pointer"
                    onClick={(e) => e.stopPropagation()}
                >
                    <input
                        type="checkbox"
                        checked={!!isSelected}
                        onChange={(e) => {
                            e.stopPropagation()
                            onToggleComparison(product)
                        }}
                        className="w-4 h-4 rounded border-slate-600 text-indigo-600"
                    />
                    <span className="text-xs text-slate-400">Compare</span>
                </label>
                <button
                    onClick={(e) => {
                        e.stopPropagation()
                        onAddToWatchlist(product)
                    }}
                    className="p-1.5 bg-slate-900/80 rounded hover:bg-slate-800"
                    title="Add to Watchlist"
                >
                    <Award className="w-4 h-4 text-yellow-400" />
                </button>
            </div>

            <div className="flex flex-col md:flex-row gap-6">
                {/* Rank */}
                <div className="flex-shrink-0 flex items-center justify-center w-16 text-2xl font-bold text-slate-500">
                    #{rank}
                </div>

                {/* Content */}
                <div className="flex-grow space-y-3">
                    <div className="flex justify-between items-start gap-4">
                        <h3 className="text-lg font-semibold text-slate-200 group-hover:text-indigo-400 transition-colors line-clamp-2">
                            {product.title}
                        </h3>
                        <div className="flex gap-2">
                            {isWinner && (
                                <span className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-bold border border-green-500/30 flex items-center whitespace-nowrap gap-1">
                                    <Award className="w-3 h-3" /> WINNER
                                </span>
                            )}
                            {isVetoed && (
                                <span className="px-3 py-1 rounded-full bg-red-500/20 text-red-400 text-xs font-bold border border-red-500/20 flex items-center whitespace-nowrap gap-1">
                                    <AlertTriangle className="w-3 h-3" /> VETOED
                                </span>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm pointer-events-none">
                        <div className="bg-slate-900/50 rounded-lg p-3">
                            <span className="block text-slate-500 text-xs mb-1">Price</span>
                            <span className="block text-white font-mono">${product.price?.toFixed(2)}</span>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-3">
                            <span className="block text-slate-500 text-xs mb-1">Est. Revenue</span>
                            <span className="block text-green-400 font-mono font-bold">${product.est_revenue?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-3">
                            <span className="block text-slate-500 text-xs mb-1">Est. Sales</span>
                            <span className="block text-blue-400 font-mono">{Math.round(product.estimated_sales)?.toLocaleString()}/mo</span>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-3">
                            <span className="block text-slate-500 text-xs mb-1">Market Share</span>
                            <span className="block text-purple-400 font-mono">{product.market_share?.toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

function ProductDetailModal({ product, onClose }) {

    // Prepare data for Chart
    // Prepare data for Chart
    const chartData = [
        { subject: 'Demand', A: product.score_breakdown?.demand ?? 0, fullMark: 100 },
        { subject: 'Competition', A: product.score_breakdown?.competition ?? 0, fullMark: 100 },
        { subject: 'Profit', A: product.score_breakdown?.profit ?? 0, fullMark: 100 },
    ]

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            />

            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="relative z-10 w-full max-w-4xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto"
            >
                {/* Header */}
                <div className="p-6 border-b border-slate-700 flex justify-between items-start gap-4">
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-2">{product.title}</h2>
                        <a href={product.url} target="_blank" className="text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1">
                            View on Amazon ↗
                        </a>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition-colors">
                        <CloseIcon className="w-6 h-6 text-slate-400" />
                    </button>
                </div>

                <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Charts & Score */}
                    <div className="space-y-6">
                        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                            <h3 className="text-lg font-semibold text-slate-300 mb-4 text-center">Opportunity Breakdown</h3>
                            <div className="h-[250px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
                                        <PolarGrid stroke="#334155" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                                        <Radar
                                            name="Score"
                                            dataKey="A"
                                            stroke="#818cf8"
                                            strokeWidth={3}
                                            fill="#6366f1"
                                            fillOpacity={0.3}
                                        />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f1f5f9' }}
                                        />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="text-center mt-2">
                                <span className="text-4xl font-bold text-white">{product.enhanced_score}</span>
                                <span className="text-slate-500 text-lg">/100</span>
                                <p className="text-sm text-slate-400 mt-1">Total Opportunity Score</p>
                            </div>
                        </div>

                        {/* Financials */}
                        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                            <h3 className="text-lg font-semibold text-slate-300 mb-4">Financial Analysis</h3>
                            <div className="space-y-3">
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Monthly Revenue</span>
                                    <span className="text-white font-mono font-bold">${product.est_revenue?.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Est. Profit (Net)</span>
                                    <span className="text-green-400 font-mono font-bold">${product.est_profit?.toFixed(2)} / unit</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Margin</span>
                                    <span className={cn("font-mono font-bold", product.margin > 20 ? "text-green-400" : "text-yellow-400")}>
                                        {product.margin?.toFixed(0)}%
                                    </span>
                                </div>
                                <div className="h-px bg-slate-700 my-2" />
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Referral Fee</span>
                                    <span className="text-slate-300">${product.fees_breakdown?.referral?.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">FBA Fee</span>
                                    <span className="text-slate-300">${product.fees_breakdown?.fba?.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Text Details */}
                    <div className="space-y-6">
                        {/* Risk Analysis */}
                        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                            <h3 className="text-lg font-semibold text-slate-300 mb-4">Risk Assessment</h3>
                            <div className="space-y-4">
                                <div>
                                    <span className="text-xs font-bold text-slate-500 uppercase">Brand Risk</span>
                                    <div className={cn("mt-1 flex items-center gap-2",
                                        product.risks?.brand_risk === 'CRITICAL' ? "text-red-400" :
                                            product.risks?.brand_risk === 'HIGH' ? "text-orange-400" : "text-green-400"
                                    )}>
                                        {product.risks?.brand_risk === 'CRITICAL' || product.risks?.brand_risk === 'HIGH' ? <AlertTriangle className="w-4 h-4" /> : null}
                                        <span className="font-medium">{product.risks?.brand_risk}</span>
                                    </div>
                                    <p className="text-xs text-slate-500 mt-1">{product.risks?.brand_reason}</p>
                                </div>
                                <div>
                                    <span className="text-xs font-bold text-slate-500 uppercase">Hazmat Status</span>
                                    <div className={cn("mt-1", product.risks?.hazmat ? "text-red-400" : "text-green-400")}>
                                        {product.risks?.hazmat ? "⚠️ HAZMAT WARNING" : "✅ CLEAR"}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Veto Details */}
                        {product.is_vetoed && (
                            <div className="bg-red-900/20 rounded-xl p-6 border border-red-500/30">
                                <h3 className="text-lg font-semibold text-red-400 mb-2 flex items-center gap-2">
                                    <AlertTriangle className="w-5 h-5" /> Veto Reasons
                                </h3>
                                <ul className="list-disc list-inside space-y-1 text-red-200/80 text-sm">
                                    {(Array.isArray(product.veto_reasons) ? product.veto_reasons : [product.veto_reasons]).map((reason, i) => (
                                        <li key={i}>{reason}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50">
                            <h3 className="text-lg font-semibold text-slate-300 mb-4">Product Specs</h3>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="block text-slate-500 text-xs">Reviews</span>
                                    <span className="text-white">{product.reviews?.toLocaleString()}</span>
                                </div>
                                <div>
                                    <span className="block text-slate-500 text-xs">Rating</span>
                                    <span className="text-white">⭐ {product.rating}</span>
                                </div>
                                <div>
                                    <span className="block text-slate-500 text-xs">BSR</span>
                                    <span className="text-white">#{product.bsr?.toLocaleString()}</span>
                                </div>
                                <div>
                                    <span className="block text-slate-500 text-xs">Category</span>
                                    <span className="text-white truncate">{product.category}</span>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </motion.div>

            {/* NEW: Saved Searches Panel */}
            <AnimatePresence>
                {showSavedSearches && <SavedSearchesPanel />}
            </AnimatePresence>

            {/* NEW: Watchlist Panel */}
            <AnimatePresence>
                {showWatchlist && <WatchlistPanel />}
            </AnimatePresence>

            {/* NEW: Comparison Modal */}
            <AnimatePresence>
                {showComparison && <ComparisonModal />}
            </AnimatePresence>
        </div>
    )
}

export default App
