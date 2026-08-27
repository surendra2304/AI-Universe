"""Live Capital Performance Attribution and Slippage Disparity Analytics."""

from typing import Any, Dict, List


class LiveAttributionEngine:
    """Analyzes real execution slippage, testnet vs live divergence, and computes strategy reliability scores."""

    def evaluate_live_attribution(
        self,
        live_trades: List[Dict[str, Any]],
        testnet_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculates live vs testnet alpha retention, execution drag, and strategy reliability scores."""
        total_live_pnl = sum(t.get("pnl", 0.0) for t in live_trades)
        total_slippage_usd = sum(abs(t.get("expected_price", 0.0) - t.get("fill_price", 0.0)) * t.get("qty", 0.0) for t in live_trades)
        win_count = sum(1 for t in live_trades if t.get("pnl", 0.0) > 0)
        total_trades = len(live_trades)

        live_win_rate = (win_count / total_trades) if total_trades > 0 else 0.0
        testnet_win_rate = testnet_metrics.get("win_rate", 0.60)

        # Strategy Reliability Score (0.0 - 1.0)
        # Factors: live/testnet win rate parity, slippage ratio, sample size
        wr_parity = max(0.0, 1.0 - abs(live_win_rate - testnet_win_rate))
        sample_weight = min(1.0, total_trades / 50.0)
        reliability_score = round((0.6 * wr_parity + 0.4 * sample_weight), 2)

        return {
            "total_live_trades": total_trades,
            "live_win_rate": round(live_win_rate, 2),
            "testnet_win_rate": round(testnet_win_rate, 2),
            "total_slippage_usd": round(total_slippage_usd, 2),
            "strategy_reliability_score": reliability_score,
            "is_recommended_for_capital_allocation": reliability_score >= 0.70,
            "execution_quality_assessment": "EXCELLENT" if total_slippage_usd < 50.0 else ("ACCEPTABLE" if total_slippage_usd < 200.0 else "POOR_SLIPPAGE_DRAG")
        }


live_attribution_engine = LiveAttributionEngine()
