import { BarChart3, Crosshair, History, LayoutDashboard, Settings, Target } from 'lucide-react'
import { navigate } from '../../app/navigation'

const navigation = [
    { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, hint: 'Your workspace' },
    { href: '/hunter', label: 'Product Hunter', icon: Crosshair, hint: 'Find opportunities' },
    { href: '/analyzer', label: 'ASIN Analyzer', icon: Target, hint: 'Deep-dive one product' },
    { href: '/searches', label: 'Search History', icon: History, hint: 'Past research' },
]

function isActive(currentPath, href) {
    return currentPath === href || (href === '/hunter' && (currentPath === '/' || currentPath === '/keywords' || currentPath === '/watchlist' || currentPath === '/tracking'))
}

export default function AppShell({ children }) {
    const currentPath = window.location.pathname

    const NavButton = ({ href, label, icon: Icon }) => {
        const active = isActive(currentPath, href)
        return (
            <button
                onClick={() => navigate(href)}
                aria-current={active ? 'page' : undefined}
                className={`group relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                    active
                        ? 'bg-brand-gradient text-white shadow-glow-brand'
                        : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
                }`}
            >
                <Icon className={`h-[18px] w-[18px] shrink-0 ${active ? 'text-white' : 'text-slate-500 group-hover:text-brand-300'}`} />
                <span className="truncate">{label}</span>
                {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-white/90" />}
            </button>
        )
    }

    return (
        <div className="flex min-h-screen text-slate-200">
            {/* ── Sidebar (desktop) ── */}
            <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-line bg-ink-950/80 backdrop-blur-xl lg:flex">
                <button
                    onClick={() => navigate('/dashboard')}
                    className="flex items-center gap-3 px-5 py-5 text-left"
                    title="Amazon Hunter Pro home"
                >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-gradient shadow-glow-brand">
                        <BarChart3 className="h-5 w-5 text-white" />
                    </div>
                    <div>
                        <p className="font-display text-sm font-bold leading-tight text-white">Amazon Hunter</p>
                        <p className="text-[11px] font-medium uppercase tracking-wider text-gold-400">Pro</p>
                    </div>
                </button>

                <nav aria-label="Main navigation" className="mt-2 flex flex-col gap-1 px-3">
                    <p className="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-widest text-slate-600">Workspace</p>
                    {navigation.map(item => <NavButton key={item.href} {...item} />)}
                </nav>

                <div className="mt-auto space-y-1 px-3 pb-4">
                    <p className="mb-2 mt-4 border-t border-line pt-3" />
                    <NavButton href="/settings" label="Settings" icon={Settings} />
                    <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-[11px] text-slate-600">
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                        API v2.0 · connected
                    </div>
                </div>
            </aside>

            {/* ── Mobile top bar ── */}
            <header className="fixed inset-x-0 top-0 z-40 border-b border-line bg-ink-950/95 backdrop-blur-xl lg:hidden">
                <div className="flex items-center gap-3 px-4 py-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-gradient shadow-glow-brand">
                        <BarChart3 className="h-4 w-4 text-white" />
                    </div>
                    <p className="font-display text-sm font-bold text-white">Amazon Hunter Pro</p>
                </div>
                <nav aria-label="Mobile navigation" className="flex gap-1 overflow-x-auto px-2 pb-2">
                    {[...navigation, { href: '/settings', label: 'Settings', icon: Settings }].map(({ href, label, icon: Icon }) => {
                        const active = isActive(currentPath, href)
                        return (
                            <button
                                key={href}
                                onClick={() => navigate(href)}
                                className={`flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium ${
                                    active ? 'bg-brand-500/20 text-brand-300 ring-1 ring-brand-500/40' : 'text-slate-400'
                                }`}
                            >
                                <Icon className="h-3.5 w-3.5" />{label}
                            </button>
                        )
                    })}
                </nav>
            </header>

            {/* ── Content ── */}
            <div className="flex min-h-screen w-full flex-col lg:pl-60">
                <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-16 pt-20 sm:px-6 lg:pt-8">{children}</main>
                <footer className="border-t border-line px-6 py-4 text-center text-[11px] text-slate-600">
                    Amazon Hunter Pro · Research tooling for FBA sellers · Not affiliated with Amazon.com
                </footer>
            </div>
        </div>
    )
}
