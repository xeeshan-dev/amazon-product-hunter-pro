import { useState } from 'react'
import { Calculator, X as CloseIcon } from 'lucide-react'
import { motion } from 'framer-motion'

export default function ProfitCalculator({ onClose }) {
    const [price, setPrice] = useState(25)
    const [cogs, setCogs] = useState(10)
    const [units, setUnits] = useState(100)
    
    const referralFee = price * 0.15
    const fbaFee = price < 15 ? 3.5 : price < 30 ? 4.5 : 5.5
    const totalFees = referralFee + fbaFee
    const profit = price - cogs - totalFees
    const margin = (profit / price) * 100
    const monthlyProfit = profit * units
    const roi = (profit / cogs) * 100
    
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
                className="relative z-10 w-full max-w-2xl bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-6"
            >
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Calculator className="w-6 h-6 text-indigo-400" />
                        Profit Calculator
                    </h2>
                    <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition-colors">
                        <CloseIcon className="w-6 h-6 text-slate-400" />
                    </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Inputs */}
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Selling Price ($)
                            </label>
                            <input
                                type="number"
                                value={price}
                                onChange={(e) => setPrice(parseFloat(e.target.value) || 0)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Cost of Goods ($)
                            </label>
                            <input
                                type="number"
                                value={cogs}
                                onChange={(e) => setCogs(parseFloat(e.target.value) || 0)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Monthly Units
                            </label>
                            <input
                                type="number"
                                value={units}
                                onChange={(e) => setUnits(parseInt(e.target.value) || 0)}
                                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white"
                            />
                        </div>
                    </div>
                    
                    {/* Results */}
                    <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
                        <h3 className="font-semibold text-slate-200 mb-3">Breakdown</h3>
                        <div className="flex justify-between text-sm">
                            <span className="text-slate-400">Referral Fee (15%)</span>
                            <span className="text-white">${referralFee.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-slate-400">FBA Fee (est.)</span>
                            <span className="text-white">${fbaFee.toFixed(2)}</span>
                        </div>
                        <div className="h-px bg-slate-700 my-2" />
                        <div className="flex justify-between text-sm font-bold">
                            <span className="text-slate-300">Profit per Unit</span>
                            <span className={profit > 0 ? 'text-green-400' : 'text-red-400'}>
                                ${profit.toFixed(2)}
                            </span>
                        </div>
                        <div className="flex justify-between text-sm font-bold">
                            <span className="text-slate-300">Margin</span>
                            <span className={margin > 20 ? 'text-green-400' : 'text-yellow-400'}>
                                {margin.toFixed(1)}%
                            </span>
                        </div>
                        <div className="flex justify-between text-sm font-bold">
                            <span className="text-slate-300">ROI</span>
                            <span className="text-indigo-400">{roi.toFixed(0)}%</span>
                        </div>
                        <div className="h-px bg-slate-700 my-2" />
                        <div className="flex justify-between text-lg font-bold">
                            <span className="text-white">Monthly Profit</span>
                            <span className="text-green-400">${monthlyProfit.toFixed(0)}</span>
                        </div>
                    </div>
                </div>
            </motion.div>
        </div>
    )
}
