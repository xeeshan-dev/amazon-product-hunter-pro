import { useEffect, useState } from 'react'
import { AlertCircle, ArrowRight, BellRing, Crosshair, Eye, Search, Sparkles, Trophy } from 'lucide-react'
import AuthRequired from '../components/common/AuthRequired'
import { getAccessToken } from '../services/apiClient'
import { getDashboard } from '../services/productIntelligence'
import { navigate } from '../app/navigation'

const kpis = [
    { key: 'tracked_products', label: 'Tracked products', icon: Eye, tile: 'bg-brand-500/15 text-brand-300 ring-brand-500/30' },
    { key: 'unread_alerts', label: 'Unread alerts', icon: BellRing, tile: 'bg-gold-500/15 text-gold-400 ring-gold-500/30' },
    { key: 'strong_opportunities', label: 'Strong opportunities', icon: Trophy, tile: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30' },
]

function statusPill(status) {
    const s = (status || '').toLowerCase()
    if (s === 'completed') return 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30'
    if (s === 'running') return 'bg-sky-500/15 text-sky-300 ring-sky-500/30 animate-pulse'
    if (s === 'failed') return 'bg-rose-500/15 text-rose-300 ring-rose-500/30'
    return 'bg-slate-500/15 text-slate-400 ring-slate-500/30'
}

export default function Dashboard() {
    const [data, setData] = useState(null)
    const [error, setError] = useState('')
    const token = getAccessToken()

    useEffect(() => {
        if (!token) return
        getDashboard().then(response => setData(response.data)).catch(() => setError('Unable to load dashboard data.'))
    }, [token])

    if (!token) return <AuthRequired />
    if (error) return <PageMessage icon={AlertCircle} message={error} />
    if (!data) return <PageMessage icon={Crosshair} message="Loading workspace..." />

    const opportunities = Array.isArray(data.strong_opportunities) ? data.strong_opportunities : []
    const tracked = Array.isArray(data.tracked_products) ? data.tracked_products : []

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-widest text-brand-300">Workspace</p>
                    <h1 className="mt-1 font-display text-2xl font-bold text-white">Research Dashboard</h1>
                    <p className="mt-1 text-sm text-slate-400">Your latest activity and strongest sourcing signals.</p>
                </div>
                <button onClick={() => navigate('/hunter')} className="btn-primary">
                    <Search className="h-4 w-4" /> New search
                </button>
            </div>

            {/* KPI tiles */}
            <section aria-label="Key metrics" className="grid gap-4 sm:grid-cols-3">
                {kpis.map(({ key, label, icon: Icon, tile }) => (
                    <button
                        key={key}
                        onClick={() => navigate('/hunter')}
                        className="panel group p-5 text-left transition-all duration-150 hover:border-brand-500/40 hover:shadow-elev2"
                    >
                        <div className="flex items-center justify-between">
                            <span className={`icon-tile ${tile}`}><Icon className="h-5 w-5" /></span>
                            <ArrowRight className="h-4 w-4 text-slate-600 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-brand-300" />
                        </div>
                        <p className="mt-4 font-display text-3xl font-bold text-white">{data[key] ?? 0}</p>
                        <p className="mt-1 text-sm text-slate-400">{label}</p>
                    </button>
                ))}
            </section>

            <div className="grid gap-6 lg:grid-cols-5">
                {/* Recent searches */}
                <section aria-label="Recent searches" className="panel lg:col-span-3">
                    <header className="flex items-center justify-between border-b border-line px-5 py-4">
                        <h2 className="text-sm font-semibold text-slate-200">Recent searches</h2>
                        <button onClick={() => navigate('/searches')} className="text-xs font-medium text-brand-300 hover:text-brand-200">View all →</button>
                    </header>
                    {data.recent_searches?.length ? (
                        <div className="overflow-x-auto">
                            <table className="w-full min-w-[520px] text-left text-sm">
                                <thead>
                                    <tr className="text-[11px] uppercase tracking-wide text-slate-500">
                                        <th className="px-5 py-3 font-medium">Keyword</th>
                                        <th className="px-5 py-3 font-medium">Market</th>
                                        <th className="px-5 py-3 font-medium">Results</th>
                                        <th className="px-5 py-3 font-medium">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.recent_searches.map(search => (
                                        <tr key={search.id} className="border-t border-line/60 transition-colors hover:bg-white/[0.03]">
                                            <td className="px-5 py-3 font-medium text-slate-100">{search.keyword}</td>
                                            <td className="px-5 py-3 text-slate-400">{search.marketplace}</td>
                                            <td className="px-5 py-3 font-mono text-slate-300">{search.result_count}</td>
                                            <td className="px-5 py-3">
                                                <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ${statusPill(search.status)}`}>
                                                    {search.status}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <EmptyState
                            icon={Search}
                            title="No searches yet"
                            body="Run your first product hunt to populate your research history."
                            action={<button onClick={() => navigate('/hunter')} className="btn-primary mt-4"><Sparkles className="h-4 w-4" /> Start hunting</button>}
                        />
                    )}
                </section>

                {/* Strong opportunities */}
                <section aria-label="Strong opportunities" className="panel lg:col-span-2">
                    <header className="flex items-center gap-2 border-b border-line px-5 py-4">
                        <Trophy className="h-4 w-4 text-gold-400" />
                        <h2 className="text-sm font-semibold text-slate-200">Strong opportunities</h2>
                    </header>
                    {opportunities.length ? (
                        <ul className="divide-y divide-line/60">
                            {opportunities.slice(0, 6).map(item => (
                                <li key={item.asin ?? item.title} className="flex items-center justify-between gap-3 px-5 py-3">
                                    <div className="min-w-0">
                                        <p className="truncate text-sm font-medium text-slate-200">{item.title || item.asin}</p>
                                        <p className="text-[11px] text-slate-500">{item.asin}{item.marketplace ? ` · ${item.marketplace}` : ''}</p>
                                    </div>
                                    {item.opportunity_score != null && (
                                        <span className="shrink-0 rounded-md bg-emerald-500/15 px-2 py-1 font-mono text-xs font-bold text-emerald-300 ring-1 ring-emerald-500/30">
                                            {Math.round(item.opportunity_score)}
                                        </span>
                                    )}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <EmptyState icon={Trophy} title="Nothing confirmed yet" body="Winners you validate in Product Hunter will be collected here." />
                    )}
                </section>
            </div>

            {/* Tracked products strip */}
            {tracked.length > 0 && (
                <section aria-label="Tracked products" className="panel">
                    <header className="flex items-center gap-2 border-b border-line px-5 py-4">
                        <Eye className="h-4 w-4 text-brand-300" />
                        <h2 className="text-sm font-semibold text-slate-200">Tracked products</h2>
                        <span className="rounded-full bg-ink-700 px-2 py-0.5 text-[11px] text-slate-400">{tracked.length}</span>
                    </header>
                    <div className="flex flex-wrap gap-2 p-4">
                        {tracked.map(t => (
                            <button key={t.asin} onClick={() => navigate('/analyzer')} className="btn-ghost !py-1.5 text-xs">
                                {t.asin}
                            </button>
                        ))}
                    </div>
                </section>
            )}
        </div>
    )
}

function EmptyState({ icon: Icon, title, body, action }) {
    return (
        <div className="flex flex-col items-center px-6 py-12 text-center">
            <span className="icon-tile bg-ink-700 text-slate-500 ring-line"><Icon className="h-5 w-5" /></span>
            <p className="mt-3 text-sm font-medium text-slate-300">{title}</p>
            <p className="mt-1 max-w-xs text-xs text-slate-500">{body}</p>
            {action}
        </div>
    )
}

function PageMessage({ icon: Icon, message }) {
    return (
        <div className="mx-auto flex max-w-xl flex-col items-center px-6 py-20 text-center">
            <Icon className="h-7 w-7 text-slate-500" />
            <p className="mt-3 text-sm text-slate-400">{message}</p>
        </div>
    )
}