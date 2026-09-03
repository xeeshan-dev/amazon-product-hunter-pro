import { LockKeyhole } from 'lucide-react'
import { navigate } from '../../app/navigation'

export default function AuthRequired() {
    return (
        <div className="mx-auto max-w-xl px-6 py-20 text-center">
            <LockKeyhole className="mx-auto h-8 w-8 text-cyan-400" />
            <h1 className="mt-4 text-xl font-semibold">Sign in required</h1>
            <p className="mt-2 text-sm text-slate-400">
                Dashboard and search history require authentication to protect your data.
            </p>
            <p className="mt-2 text-sm text-slate-500">
                You can continue using Product Hunter without signing in.
            </p>
            <button 
                onClick={() => navigate('/hunter')} 
                className="mt-6 rounded-lg border border-cyan-500/60 px-6 py-2.5 text-sm font-medium text-cyan-300 hover:bg-cyan-500/10 transition-colors"
            >
                Continue to Product Hunter →
            </button>
        </div>
    )
}
