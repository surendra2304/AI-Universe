"""Real-Time Market Monitor for Anomaly Detection, Volume Spikes, and Regime Alerts."""

import time
from typing import Any, Dict, List


class MarketMonitor:
    """Monitors real-time volatility, volume anomalies, sentiment shifts, and exchange orderbook dynamics."""

    def evaluate_market_alerts(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict[str, Any],
        sentiment: Dict[str, Any],
        orderbook: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generates real-time anomaly alerts based on market telemetry."""
        alerts = []
        now = time.time()

        rsi = indicators.get("rsi_14", 50.0)
        bw = indicators.get("bollinger_bands", {}).get("bandwidth_pct", 4.0)
        sent_score = sentiment.get("overall_score", 0.0)

        # 1. RSI Extremes
        if rsi >= 75.0:
            alerts.append({
                "severity": "WARNING",
                "type": "MOMENTUM_OVERBOUGHT",
                "message": f"{symbol} RSI reached {rsi:.1f} (Overbought threshold). Caution on long breakouts.",
                "timestamp": now
            })
        elif rsi <= 25.0:
            alerts.append({
                "severity": "WARNING",
                "type": "MOMENTUM_OVERSOLD",
                "message": f"{symbol} RSI dropped to {rsi:.1f} (Oversold threshold). Mean reversion potential.",
                "timestamp": now
            })

        # 2. Volatility Compression
        if bw < 2.5:
            alerts.append({
                "severity": "INFO",
                "type": "VOLATILITY_SQUEEZE",
                "message": f"{symbol} Bollinger Bandwidth compressed to {bw:.2f}%. High-probability explosive expansion imminent.",
                "timestamp": now
            })

        # 3. Sentiment Shift
        if abs(sent_score) > 0.6:
            alerts.append({
                "severity": "INFO",
                "type": "SENTIMENT_EXTREME",
                "message": f"Social/News sentiment scored extreme at {sent_score:+.2f}.",
                "timestamp": now
            })

        # 4. Orderbook Imbalance
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        if bids and asks:
            bid_vol = sum(q for _, q in bids[:5])
            ask_vol = sum(q for _, q in asks[:5])
            ratio = (bid_vol / ask_vol) if ask_vol > 0 else 1.0
            if ratio > 2.0:
                alerts.append({
                    "severity": "INFO",
                    "type": "ORDERBOOK_BID_WALL",
                    "message": f"Significant bid-side support ({bid_vol:.1f} vs {ask_vol:.1f} asks in top 5 levels).",
                    "timestamp": now
                })

        return alerts


market_monitor = MarketMonitor()
