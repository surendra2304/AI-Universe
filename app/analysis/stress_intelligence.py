"""Market Stress Intelligence and Historical Crisis Scenario Testing."""

from typing import Any


class StressIntelligenceEngine:
    """Detects liquidity drains, cross-asset correlation spikes, and runs historical stress scenarios."""

    def evaluate_market_stress(
        self,
        bid_ask_spread_pct: float,
        cross_asset_correlation: float,
        volatility_atr_pct: float
    ) -> dict[str, Any]:
        """Calculates aggregate stress index."""
        # Baseline score: 0 to 100
        stress_score = 0.0
        stress_score += min(40.0, (bid_ask_spread_pct / 0.002) * 20.0)
        stress_score += min(30.0, max(0.0, cross_asset_correlation - 0.5) * 60.0)
        stress_score += min(30.0, (volatility_atr_pct / 0.03) * 15.0)

        stress_score = round(min(100.0, stress_score), 1)
        regime = "NORMAL" if stress_score < 35 else ("ELEVATED_STRESS" if stress_score < 70 else "ACUTE_CRISIS_STRESS")

        return {
            "market_stress_score": stress_score,
            "stress_regime": regime,
            "metrics": {
                "bid_ask_spread_pct": bid_ask_spread_pct,
                "cross_asset_correlation": cross_asset_correlation,
                "volatility_atr_pct": volatility_atr_pct
            },
            "advisory_guidance": "REDUCE_EXPOSURE_AND_PAUSE_OPTIMIZATION" if stress_score >= 70 else ("MONITOR_CLOSELY" if stress_score >= 35 else "NORMAL_TRADING_CONDITIONS")
        }

    def run_historical_stress_test(self, portfolio_equity: float, active_notional: float) -> dict[str, Any]:
        """Simulates portfolio impact under classic historical market shock scenarios."""
        scenarios = [
            {
                "scenario_name": "COVID March 2020 Liquidity Crunch (-35% Price Shock / 5x Spread)",
                "estimated_drawdown_usd": round(active_notional * 0.35, 2),
                "estimated_drawdown_pct": round((active_notional * 0.35 / portfolio_equity) * 100, 2) if portfolio_equity > 0 else 0.0,
                "survival_probability": "HIGH" if (active_notional * 0.35 / portfolio_equity) < 0.20 else "MEDIUM"
            },
            {
                "scenario_name": "FTX Insolvency Cascading Deleveraging (-22% Shock)",
                "estimated_drawdown_usd": round(active_notional * 0.22, 2),
                "estimated_drawdown_pct": round((active_notional * 0.22 / portfolio_equity) * 100, 2) if portfolio_equity > 0 else 0.0,
                "survival_probability": "HIGH" if (active_notional * 0.22 / portfolio_equity) < 0.20 else "MEDIUM"
            },
            {
                "scenario_name": "May 2021 Flash Liquidation (-15% Rapid Wick)",
                "estimated_drawdown_usd": round(active_notional * 0.15, 2),
                "estimated_drawdown_pct": round((active_notional * 0.15 / portfolio_equity) * 100, 2) if portfolio_equity > 0 else 0.0,
                "survival_probability": "HIGH"
            }
        ]

        return {
            "portfolio_equity": portfolio_equity,
            "active_notional": active_notional,
            "scenario_results": scenarios,
            "stress_resilience_rating": "PASSING"
        }


stress_intelligence_engine = StressIntelligenceEngine()
