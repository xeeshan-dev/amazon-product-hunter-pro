import { useEffect, useState } from 'react'
import ProductHunter from '../pages/ProductHunter'
import Dashboard from '../pages/Dashboard'
import ProductAnalyzer from '../pages/ProductAnalyzer'
import SearchHistory from '../pages/SearchHistory'
import AppShell from '../components/layout/AppShell'

const routes = {
    '/': Dashboard,
    '/hunter': ProductHunter,
    '/dashboard': Dashboard,
    '/analyzer': ProductAnalyzer,
    '/searches': SearchHistory,
    '/keywords': ProductHunter,
    '/watchlist': ProductHunter,
    '/tracking': ProductHunter,
    '/settings': ProductHunter,
}

export default function AppRouter() {
    const [, refresh] = useState(0)
    useEffect(() => {
        const onNavigation = () => refresh(value => value + 1)
        window.addEventListener('popstate', onNavigation)
        return () => window.removeEventListener('popstate', onNavigation)
    }, [])
    const Page = routes[window.location.pathname] || Dashboard
    return <AppShell><Page /></AppShell>
}
