import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import AuthRequired from '../components/common/AuthRequired'
import { getAccessToken } from '../services/apiClient'
import { getSearchHistory, getSearchResults } from '../services/productIntelligence'

const pageSize = 20

export default function SearchHistory() {
    const [history, setHistory] = useState(null)
    const [results, setResults] = useState(null)
    const [offset, setOffset] = useState(0)
    const [error, setError] = useState('')
    const token = getAccessToken()

    useEffect(() => { if (token) getSearchHistory({ limit: pageSize, offset }).then(response => { setHistory(response.data); setResults(null) }).catch(() => setError('Unable to load search history.')) }, [token, offset])
    if (!token) return <AuthRequired />
    if (error) return <p className="mx-auto max-w-7xl px-6 py-12 text-sm text-red-300">{error}</p>
    return <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6"><div className="mb-8"><h1 className="text-2xl font-semibold">Search history</h1><p className="mt-1 text-sm text-slate-400">Your persisted product searches, ordered by most recent.</p></div>{!history ? <p className="text-sm text-slate-400">Loading searches...</p> : <><div className="overflow-x-auto border border-slate-800"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-900 text-slate-400"><tr><th className="px-4 py-3 font-medium">Keyword</th><th className="px-4 py-3 font-medium">Market</th><th className="px-4 py-3 font-medium">Results</th><th className="px-4 py-3 font-medium">Created</th><th className="px-4 py-3" /></tr></thead><tbody>{history.searches.map(search => <tr key={search.id} className="border-t border-slate-800"><td className="px-4 py-3">{search.keyword}</td><td className="px-4 py-3 text-slate-300">{search.marketplace}</td><td className="px-4 py-3 text-slate-300">{search.result_count}</td><td className="px-4 py-3 text-slate-400">{new Date(search.created_at).toLocaleString()}</td><td className="px-4 py-3"><button onClick={() => getSearchResults(search.id).then(response => setResults({ search, ...response.data }))} className="text-cyan-300 hover:text-cyan-200">View results</button></td></tr>)}</tbody></table></div><div className="mt-4 flex items-center justify-between text-sm text-slate-400"><span>{history.total} searches</span><div className="flex gap-2"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))} className="border border-slate-700 p-2 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /></button><button disabled={offset + pageSize >= history.total} onClick={() => setOffset(offset + pageSize)} className="border border-slate-700 p-2 disabled:opacity-40"><ChevronRight className="h-4 w-4" /></button></div></div></>}{results && <section className="mt-10"><h2 className="mb-3 font-semibold">{results.search.keyword}</h2><div className="grid gap-3">{results.results.map(result => <div key={result.id} className="border border-slate-800 bg-slate-900/50 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-medium">{result.product.title}</p><p className="mt-1 text-xs text-slate-400">{result.product.asin} · Rank #{result.rank}</p></div><p className="text-lg font-semibold text-cyan-300">{result.score?.toFixed(0) ?? 'N/A'}</p></div><div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4"><Metric label="Price" value={formatCurrency(result.snapshot?.price)} /><Metric label="Sales" value={result.snapshot?.estimated_sales?.toLocaleString()} /><Metric label="Margin" value={result.snapshot?.margin == null ? 'N/A' : `${result.snapshot.margin.toFixed(1)}%`} /><Metric label="Reviews" value={result.snapshot?.reviews?.toLocaleString()} /></div></div>)}</div></section>}</div>
}

function Metric({ label, value }) { return <div><p className="text-xs text-slate-500">{label}</p><p className="mt-1 text-slate-200">{value ?? 'N/A'}</p></div> }
function formatCurrency(value) { return value == null ? 'N/A' : `$${value.toFixed(2)}` }
