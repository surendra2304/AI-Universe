"""Cross-Market Multi-Agent Debate Engine with Macro, Liquidity, and Correlation Specialists."""

from typing import Any

from app.analysis.cross_asset import cross_asset_engine
from app.analysis.liquidity_intel import liquidity_intel
from app.analysis.market_regime_intel import regime_intel


class MultiMarketDebateEngine:
    """Deliberates cross-venue arbitrage, global liquidity conditions, and portfolio concentration."""

    def conduct_cross_market_debate(self, portfolio_positions: dict[str, float]) -> dict[str, Any]:
        """Runs multi-agent market deliberation."""
        corr_data = cross_asset_engine.analyze_portfolio_correlation(portfolio_positions)
        reg_data = regime_intel.classify_market_regime()
        liq_data = liquidity_intel.analyze_asset_liquidity("BTCUSDT")

        specialist_deliberations = [
            {
                "specialist": "Macro Analyst",
                "findings": f"Macro Regime: {reg_data['macro_regime']}. BTC Dominance: {reg_data['leading_indicators']['btc_dominance_trend']}.",
                "bias": "BULLISH_RISK_ON",
                "confidence": 0.85
            },
            {
                "specialist": "Liquidity Analyst",
                "findings": f"Global Liquidity Score: {liq_data['global_liquidity_score']}. Best Execution: {liq_data['best_execution_venue']}.",
                "bias": "FAVOR_DEEP_POOLS",
                "confidence": 0.89
            },
            {
                "specialist": "Correlation Analyst",
                "findings": f"Portfolio BTC Correlation: {corr_data['weighted_btc_correlation']}. Concentration Risk: {corr_data['concentration_risk_warning']}.",
                "bias": "CAUTION_ON_CORRELATION" if corr_data['concentration_risk_warning'] else "BALANCED",
                "confidence": 0.88
            }
        ]

        consensus = "EXPAND_CORE_ALLOCATION" if reg_data["macro_regime"] == "RISK_ON" and not corr_data["concentration_risk_warning"] else "DEFENSIVE_DIVERSIFICATION"

        return {
            "portfolio_market_consensus": consensus,
            "overall_confidence": 0.87,
            "specialist_deliberations": specialist_deliberations,
            "regime_intelligence": reg_data,
            "liquidity_intelligence": liq_data,
            "correlation_analysis": corr_data
        }


multi_market_debate = MultiMarketDebateEngine()
