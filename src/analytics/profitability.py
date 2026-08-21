"""Profitability analytics.

This module centralizes the current fee/profit assumptions used by the search
pipeline. It preserves existing behavior while giving the assumptions a typed,
testable boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProfitabilityInput:
    selling_price: float
    estimated_sales: int = 0
    category: Optional[str] = None
    cogs_ratio: float = 0.25


@dataclass(frozen=True)
class FeeBreakdownOutput:
    referral: float
    fba: float
    storage: float
    total: float


@dataclass(frozen=True)
class ProfitabilityResult:
    revenue: float
    fees: FeeBreakdownOutput
    cogs: float
    net_profit: float
    margin: float


class ProfitabilityAnalyzer:
    """Calculate revenue, Amazon fees, estimated profit, and margin."""

    def __init__(self, fee_calculator):
        self.fee_calculator = fee_calculator

    def analyze(self, data: ProfitabilityInput) -> ProfitabilityResult:
        price = data.selling_price or 0
        sales = data.estimated_sales or 0
        revenue = price * sales

        fees = self.fee_calculator.calculate_all_fees(
            price,
            category=data.category,
        )
        fee_breakdown = FeeBreakdownOutput(
            referral=fees.referral_fee,
            fba=fees.fba_fulfillment_fee,
            storage=fees.monthly_storage_fee,
            total=fees.total_amazon_fees,
        )

        cogs = price * data.cogs_ratio
        net_profit = price - fees.total_amazon_fees - cogs
        margin = (net_profit / price * 100) if price > 0 else 0

        return ProfitabilityResult(
            revenue=revenue,
            fees=fee_breakdown,
            cogs=cogs,
            net_profit=net_profit,
            margin=margin,
        )
