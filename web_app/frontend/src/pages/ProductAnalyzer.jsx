import { useState } from 'react'
import { AlertTriangle, ArrowUpRight, Loader2, Search, ShieldCheck, TrendingUp } from 'lucide-react'
import { getProductAnalysis, getProductHistory } from '../services/productIntelligence'

export default function ProductAnalyzer() {
    const [asin, setAsin] = useState('')
    const [marketplace, setMarketplace] = useState('US')
    const [data, setData] = useState(null)
    const [history, setHistory] = useState(null)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    async function analyze(event) {
        event.preventDefault()
        if (!asin.trim()) return
        setLoading(true); setError(''); setData(null); setHistory(null)
        try {
            const [analysis, timeline] = await Promise.all([getProductAnalysis(asin.trim(), marketplace), getProductHistory(asin.trim(), marketplace)])
            setData(analysis.data); setHistory(timeline.data)
        } catch (requestError) {
            setError(requestError.response?.status === 404 ? 'No product observation or provider result was found for this ASIN.' : 'Unable to analyze this product right now.')
        } finally { setLoading(false) }
    }

    return <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6"><div className="max-w-2xl"><h1 className="text-2xl font-semibold">ASIN Analyzer</h1><p className="mt-1 text-sm text-slate-400">Inspect one product using canonical observations, deterministic analytics, and provider data.</p><form onSubmit={analyze} className="mt-6 flex flex-col gap-3 sm:flex-row"><div className="flex flex-1 items-center border border-slate-700 bg-slate-900 px-3"><Search className="h-5 w-5 text-slate-500" /><input value={asin} onChange={event => setAsin(event.target.value.toUpperCase())} placeholder="Enter an Amazon ASIN" className="min-w-0 flex-1 bg-transparent px-3 py-3 text-sm outline-none" /></div><select value={marketplace} onChange={event => setMarketplace(event.target.value)} className="border border-slate-700 bg-slate-900 px-3 py-3 text-sm"><option>US</option><option>UK</option><option>DE</option></select><button disabled={loading} className="flex items-center justify-center gap-2 bg-cyan-500 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-60">{loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}Analyze</button></form>{error && <p className="mt-3 text-sm text-red-300">{error}</p>}</div>{data && <AnalysisResult data={data} history={history} />}</div>
}

function AnalysisResult({ data, history }) {
    const overview = data.overview
    const cards = [
        ['Opportunity score', data.recommendation.score == null ? 'N/A' : `${data.recommendation.score.toFixed(0)}/100`],
        ['Price', money(data.profitability.price)],
        ['Estimated sales', formatEstimate(data.estimates.monthly_sales)],
        ['Estimated margin', percent(data.profitability.margin)],
    ]
    return <section className="mt-10"><div className="border-b border-slate-800 pb-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><h2 className="text-xl font-semibold">{overview.title}</h2><p className="mt-1 text-sm text-slate-400">{overview.asin} · {overview.marketplace} · {overview.brand || 'Unknown brand'}</p></div>{overview.product_url && <a href={overview.product_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm text-cyan-300 hover:text-cyan-200">View listing <ArrowUpRight className="h-4 w-4" /></a>}</div></div><div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{cards.map(([label, value]) => <div key={label} className="border border-slate-800 bg-slate-900/60 p-4"><p className="text-xs text-slate-400">{label}</p><p className="mt-2 text-xl font-semibold">{value}</p></div>)}</div><div className="mt-8 grid gap-6 lg:grid-cols-3"><section className="border border-slate-800 p-5"><h3 className="flex items-center gap-2 font-semibold"><TrendingUp className="h-4 w-4 text-cyan-400" />Trends</h3><dl className="mt-4 space-y-3 text-sm"><Row label="Price trend" value={data.trends.price.trend} /><Row label="BSR trend" value={data.trends.bsr.trend} /><Row label="Review growth" value={data.trends.reviews.growth_pct == null ? 'Insufficient Data' : percent(data.trends.reviews.growth_pct)} /><Row label="Score trend" value={data.trends.opportunity_score.trend} /></dl></section><section className="border border-slate-800 p-5"><h3 className="flex items-center gap-2 font-semibold"><ShieldCheck className="h-4 w-4 text-emerald-400" />Risk and competition</h3><dl className="mt-4 space-y-3 text-sm"><Row label="Brand risk" value={data.risk.brand_risk || 'Unknown'} /><Row label="Hazmat" value={data.risk.hazmat ? 'Potentially flagged' : 'No flag'} /><Row label="Seller count" value={data.competition.seller_count ?? 'N/A'} /><Row label="Reviews" value={data.competition.reviews?.toLocaleString() ?? 'N/A'} /></dl></section><section className="border border-slate-800 p-5"><h3 className="flex items-center gap-2 font-semibold"><AlertTriangle className="h-4 w-4 text-amber-400" />Recommendation</h3><p className="mt-4 text-lg font-semibold text-cyan-300">{data.recommendation.label}</p><p className="mt-2 text-sm text-slate-400">Data freshness: {data.data_quality.status}. Source: {data.data_quality.source || 'Unavailable'}.</p></section></div>{history?.history?.length ? <section className="mt-8"><h3 className="mb-3 font-semibold">Observation history</h3><div className="overflow-x-auto border border-slate-800"><table className="w-full min-w-[600px] text-left text-sm"><thead className="bg-slate-900 text-slate-400"><tr><th className="px-4 py-3">Observed</th><th className="px-4 py-3">Price</th><th className="px-4 py-3">BSR</th><th className="px-4 py-3">Reviews</th><th className="px-4 py-3">Score</th></tr></thead><tbody>{history.history.map(item => <tr key={item.id} className="border-t border-slate-800"><td className="px-4 py-3 text-slate-400">{new Date(item.recorded_at).toLocaleString()}</td><td className="px-4 py-3">{money(item.price)}</td><td className="px-4 py-3">{item.bsr?.toLocaleString() ?? 'N/A'}</td><td className="px-4 py-3">{item.reviews?.toLocaleString() ?? 'N/A'}</td><td className="px-4 py-3">{item.opportunity_score?.toFixed(0) ?? 'N/A'}</td></tr>)}</tbody></table></div></section> : null}</section>
}

function Row({ label, value }) { return <div className="flex items-center justify-between gap-3"><dt className="text-slate-400">{label}</dt><dd className="text-right text-slate-100">{value}</dd></div> }
function money(value) { return value == null ? 'N/A' : `$${value.toFixed(2)}` }
function percent(value) { return value == null ? 'N/A' : `${value.toFixed(1)}%` }
function formatEstimate(estimate) { return estimate.value == null ? 'N/A' : `${estimate.value.toLocaleString()} (${estimate.lower_bound.toLocaleString()}-${estimate.upper_bound.toLocaleString()})` }
