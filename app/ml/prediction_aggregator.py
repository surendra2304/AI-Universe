"""Prediction Aggregation Engine combining Deep Learning, Technicals, Sentiment, and On-Chain."""

from typing import Any, Dict, List
from app.data.alternative_data import alt_data_engine
from app.ml.deep_models import deep_models_engine


class PredictionAggregationEngine:
    """Ensemble aggregator combining ML sequence models, TA signals, NLP sentiment, and on-chain metrics."""

    def aggregate_prediction(
        self,
        symbol: str,
        current_price: float,
        recent_returns: List[float]
    ) -> Dict[str, Any]:
        """Generates unified ensemble directional signal and key drivers."""
        dl_pred = deep_models_engine.predict_horizons(symbol, current_price, recent_returns)
        alt_data = alt_data_engine.get_consolidated_alternative_data(symbol)

        # Signal components
        lstm_signal = 1.0 if dl_pred["horizons"]["24h"]["predicted_direction"] == "BULLISH" else -1.0
        news_signal = 1.0 if alt_data["news_intelligence"]["sentiment_score"] > 0.2 else (-1.0 if alt_data["news_intelligence"]["sentiment_score"] < -0.2 else 0.0)
        onchain_signal = 1.0 if alt_data["onchain_intelligence"]["exchange_netflow_24h_usd"] < 0 else -1.0

        # Weighted composite score: 40% DL, 30% On-Chain, 30% News/Social
        composite_score = (0.40 * lstm_signal) + (0.30 * onchain_signal) + (0.30 * news_signal)

        direction = "BULLISH" if composite_score >= 0.25 else ("BEARISH" if composite_score <= -0.25 else "NEUTRAL")
        confidence = round(min(0.95, max(0.60, 0.70 + abs(composite_score) * 0.25)), 2)

        key_drivers = []
        if onchain_signal > 0:
            key_drivers.append("Exchange net outflows (institutional accumulation)")
        if news_signal > 0:
            key_drivers.append("Bullish news NLP sentiment")
        if lstm_signal > 0:
            key_drivers.append("LSTM/Transformer sequence momentum")

        return {
            "symbol": symbol.upper(),
            "current_price": current_price,
            "unified_direction": direction,
            "unified_confidence": confidence,
            "horizon": "24H",
            "key_drivers": key_drivers,
            "conflicting_signals": [] if abs(lstm_signal - news_signal) <= 1.0 else ["Deep Learning vs News Divergence"],
            "deep_learning_forecast": dl_pred,
            "alternative_data_snapshot": alt_data
        }


prediction_aggregator = PredictionAggregationEngine()
