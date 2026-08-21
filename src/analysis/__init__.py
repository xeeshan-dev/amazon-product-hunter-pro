"""Analysis package exports.

The package initializer intentionally avoids importing every analysis module at
startup. Some optional analyzers pull in heavy NLP/scientific dependencies, so
exports are resolved lazily when accessed through ``analysis.<Name>``.
"""

from importlib import import_module

_EXPORTS = {
    "MarketAnalyzer": ("analysis.market_analysis", "MarketAnalyzer"),
    "MarketMetrics": ("analysis.market_analysis", "MarketMetrics"),
    "SellerAnalyzer": ("analysis.seller_analysis", "SellerAnalyzer"),
    "SellerInfo": ("analysis.seller_analysis", "SellerInfo"),
    "ProductScorer": ("analysis.scoring", "ProductScorer"),
    "SentimentAnalyzer": ("analysis.sentiment", "SentimentAnalyzer"),
    "EnhancedOpportunityScorer": (
        "analysis.enhanced_scoring",
        "EnhancedOpportunityScorer",
    ),
    "OpportunityScore": ("analysis.enhanced_scoring", "OpportunityScore"),
    "FBAFeeCalculator": ("analysis.fba_calculator", "FBAFeeCalculator"),
    "ProductDimensions": ("analysis.fba_calculator", "ProductDimensions"),
    "calculate_fba_fees": ("analysis.fba_calculator", "calculate_fba_fees"),
    "BSRTracker": ("analysis.bsr_tracker", "BSRTracker"),
    "BSRTrend": ("analysis.bsr_tracker", "BSRTrend"),
    "CamelPriceScraper": ("analysis.price_history", "CamelPriceScraper"),
    "PriceHistory": ("analysis.price_history", "PriceHistory"),
    "FreeKeywordTool": ("analysis.keyword_tool", "FreeKeywordTool"),
    "ReverseASINResult": ("analysis.keyword_tool", "ReverseASINResult"),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module 'analysis' has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
