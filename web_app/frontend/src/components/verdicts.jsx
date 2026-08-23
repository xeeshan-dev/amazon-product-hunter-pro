export const VERDICT_META = {
    'Strong research candidate': { label: 'Winner', sortRank: 4, cls: 'border-emerald-500/30 bg-emerald-500/15 text-emerald-300' },
    'Worth researching': { label: 'Worth Researching', sortRank: 3, cls: 'border-sky-500/30 bg-sky-500/15 text-sky-300' },
    'Needs validation': { label: 'Needs Validation', sortRank: 2, cls: 'border-amber-500/30 bg-amber-500/15 text-amber-300' },
    Deprioritize: { label: 'Deprioritize', sortRank: 1, cls: 'border-slate-600/40 bg-slate-500/15 text-slate-400' },
}

export function scoreTone(score) {
    if (score == null) return 'text-slate-500'
    if (score >= 70) return 'text-emerald-400'
    if (score >= 50) return 'text-amber-300'
    return 'text-red-400'
}

export function scoreChipBg(score) {
    if (score == null) return 'bg-slate-700/50 text-slate-400'
    if (score >= 70) return 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/40'
    if (score >= 50) return 'bg-amber-500/15 text-amber-300 ring-amber-500/40'
    return 'bg-red-500/15 text-red-300 ring-red-500/40'
}
