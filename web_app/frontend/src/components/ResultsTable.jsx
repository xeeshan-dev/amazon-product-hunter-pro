import {memo} from 'react'
import {Star, Eye, Package, ChevronUp, ChevronDown, ShoppingCart} from 'lucide-react'
import {VERDICT_META, scoreChipBg} from './verdicts'

const money = (v, digits = 0) =>
    v == null ? '–' : `$${Number(v).toLocaleString(undefined, {maximumFractionDigits: digits})}`

const SORT_ACCESSORS = {
    score: p => p.enhanced_score || 0,
    price: p => p.price || 0,
    sales: p => p.estimated_sales || 0,
    margin: p => p.margin || 0,
    revenue: p => p.est_revenue || 0,
    reviews: p => p.reviews || 0,
    bsr: p => p.bsr || 0,
    sellers: p => p.seller_info?.total_sellers || 0,
    verdict: p => VERDICT_META[p.winning_product?.decision]?.sortRank || 0,
}

const COLUMNS = [
    {key: 'product', label: 'Product', sortable: false, className: 'min-w-[260px]'},
    {key: 'price', label: 'Price', sortable: true},
    {key: 'sales', label: 'Sales/mo', sortable: true},
    {key: 'revenue', label: 'Revenue', sortable: true},
    {key: 'margin', label: 'Margin', sortable: true},
    {key: 'profit', label: 'Profit/u', sortable: true},
    {key: 'reviews', label: 'Reviews', sortable: true},
    {key: 'bsr', label: 'BSR', sortable: true},
    {key: 'sellers', label: 'Sellers', sortable: true},
    {key: 'score', label: 'Score', sortable: true},
    {key: 'verdict', label: 'Verdict', sortable: true},
]

function Thumb({product}) {
    if (product.image_url) {
        return (
            <img
                src={product.image_url}
                alt=""
                loading="lazy"
                className="h-10 w-10 shrink-0 rounded border border-slate-700/60 bg-slate-800 object-cover"
            />
        )
    }
    return (
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-slate-700/60 bg-slate-800">
            <Package className="h-4 w-4 text-slate-500"/>
        </div>
    )
}

function ResultsTable({
                          products,
                          sortBy,
                          sortOrder,
                          onSort,
                          selectedForComparison,
                          onToggleComparison,
                          onAddToWatchlist,
                          onAddToTracking,
                          watchlist,
                          trackedProducts,
                          onRowClick,
                      }) {
    const sorted = [...products].sort((a, b) => {
        const acc = SORT_ACCESSORS[sortBy] || SORT_ACCESSORS.score
        const av = acc(a)
        const bv = acc(b)
        const cmp = av === bv ? 0 : av > bv ? 1 : -1
        return sortOrder === 'asc' ? cmp : -cmp
    })

    return (
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
            <table className="w-full min-w-[1080px] border-collapse text-xs">
                <thead>
                <tr className="border-b border-slate-800 bg-slate-900 text-left text-[11px] uppercase tracking-wide text-slate-400">
                    <th className="px-2 py-2.5 font-medium" title="Select for comparison">#</th>
                    {COLUMNS.map(col => (
                        <th
                            key={col.key}
                            className={`px-2 py-2.5 font-medium ${col.sortable ? 'cursor-pointer select-none hover:text-slate-200' : ''} ${col.className || ''}`}
                            onClick={col.sortable ? () => onSort(col.key) : undefined}
                        >
                            <span className="inline-flex items-center gap-1">
                                {col.label}
                                {col.sortable && sortBy === col.key && (
                                    sortOrder === 'desc'
                                        ? <ChevronDown className="h-3 w-3 text-cyan-400"/>
                                        : <ChevronUp className="h-3 w-3 text-cyan-400"/>
                                )}
                            </span>
                        </th>
                    ))}
                    <th className="px-2 py-2.5 text-right font-medium">Actions</th>
                </tr>
                </thead>
                <tbody>
                {sorted.map((p, idx) => {
                    const meta = VERDICT_META[p.winning_product?.decision]
                    const isSelected = !!selectedForComparison.find(c => c.asin === p.asin)
                    const isTracked = !!trackedProducts.find(t => t.asin === p.asin)
                    const inWatchlist = !!watchlist.find(w => w.asin === p.asin)
                    const sellerInfo = p.seller_info || {}
                    return (
                        <tr
                            key={p.asin}
                            onClick={() => onRowClick(p)}
                            className={`cursor-pointer border-b border-slate-800/60 transition-colors last:border-0 hover:bg-slate-800/40 ${isSelected ? 'bg-indigo-500/10' : ''}`}
                        >
                            <td className="px-2 py-2" onClick={e => e.stopPropagation()}>
                                <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => onToggleComparison(p)}
                                    className="h-3.5 w-3.5 rounded border-slate-600 bg-slate-800 accent-indigo-500"
                                />
                            </td>
                            <td className="px-2 py-2">
                                <div className="flex items-center gap-2">
                                    <span className="w-5 text-right font-mono text-slate-500">{idx + 1}</span>
                                    <Thumb product={p}/>
                                    <div className="max-w-[240px]">
                                        <p className="truncate font-medium text-slate-200" title={p.title}>{p.title}</p>
                                        <p className="truncate text-[11px] text-slate-500">
                                            {p.asin}{p.brand ? ` · ${p.brand}` : ''}
                                        </p>
                                    </div>
                                </div>
                            </td>
                            <td className="px-2 py-2 font-mono text-slate-300">{money(p.price, 2)}</td>
                            <td className="px-2 py-2 font-mono text-blue-300">{Math.round(p.estimated_sales || 0).toLocaleString()}</td>
                            <td className="px-2 py-2 font-mono font-semibold text-emerald-300">{money(p.est_revenue)}</td>
                            <td className={`px-2 py-2 font-mono ${(p.margin || 0) >= 25 ? 'text-emerald-300' : (p.margin || 0) >= 15 ? 'text-amber-300' : 'text-red-400'}`}>
                                {(p.margin ?? 0).toFixed(0)}%
                            </td>
                            <td className="px-2 py-2 font-mono text-emerald-400/90">{money(p.est_profit, 2)}</td>
                            <td className="px-2 py-2 font-mono text-slate-400">{(p.reviews || 0).toLocaleString()}</td>
                            <td className="px-2 py-2 font-mono text-slate-400">{p.bsr ? `#${p.bsr.toLocaleString()}` : '–'}</td>
                            <td className="px-2 py-2">
                                {sellerInfo.data_status === 'observed'
                                    ? <span className="font-mono text-slate-300">{sellerInfo.total_sellers ?? '–'}{sellerInfo.amazon_seller && <span className="ml-1 font-bold text-orange-400" title="Amazon sells this product">AMZ</span>}</span>
                                    : <span className="text-slate-600">n/a</span>}
                            </td>
                            <td className="px-2 py-2">
                                <span className={`inline-flex h-7 min-w-[2rem] items-center justify-center rounded-md px-1.5 font-mono text-sm font-bold ring-1 ${scoreChipBg(p.enhanced_score)}`}>
                                    {Math.round(p.enhanced_score ?? 0)}
                                </span>
                            </td>
                            <td className="px-2 py-2">
                                {meta && (
                                    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium ${meta.cls}`}>
                                        <ShoppingCart className="h-3 w-3"/>
                                        {meta.label}
                                    </span>
                                )}
                            </td>
                            <td className="px-2 py-2" onClick={e => e.stopPropagation()}>
                                <div className="flex items-center justify-end gap-1.5">
                                    <button
                                        onClick={() => onAddToWatchlist(p)}
                                        title={inWatchlist ? 'In watchlist' : 'Add to watchlist'}
                                        className={`rounded p-1.5 hover:bg-slate-700 ${inWatchlist ? 'text-yellow-400' : 'text-slate-500 hover:text-yellow-400'}`}
                                    >
                                        <Star className="h-4 w-4" fill={inWatchlist ? 'currentColor' : 'none'}/>
                                    </button>
                                    <button
                                        onClick={() => onAddToTracking(p)}
                                        title={isTracked ? 'Being tracked' : 'Track this product'}
                                        className={`rounded p-1.5 hover:bg-slate-700 ${isTracked ? 'text-cyan-400' : 'text-slate-500 hover:text-cyan-400'}`}
                                    >
                                        <Eye className="h-4 w-4"/>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    )
                })}
                {sorted.length === 0 && (
                    <tr>
                        <td colSpan={COLUMNS.length + 2} className="px-4 py-10 text-center text-slate-500">
                            No products match the current filters.
                        </td>
                    </tr>
                )}
                </tbody>
            </table>
        </div>
    )
}

export default memo(ResultsTable)