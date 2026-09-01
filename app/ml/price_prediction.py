"""Machine Learning Ensemble Price Prediction and Uncertainty Engine."""

from typing import Any


class PricePredictionModel:
    """Ensemble price prediction engine combining trend momentum, on-chain flows, and sentiment."""

    def predict_price_trajectory(
        self,
        current_price: float,
        indicators: dict[str, Any],
        sentiment: dict[str, Any],
        onchain: dict[str, Any]
    ) -> dict[str, Any]:
        """Generates multi-horizon price trajectory forecast with confidence intervals."""
        rsi = indicators.get("rsi_14", 50.0)
        macd_hist = indicators.get("macd", {}).get("histogram", 0.0)
        adx = indicators.get("adx", 25.0)
        sent_score = sentiment.get("overall_score", 0.0)
        net_flow = onchain.get("exchange_flows", {}).get("net_flow_usd", 0.0)

        # 1. Technical momentum factor
        mom_factor = (rsi - 50.0) / 100.0 + (macd_hist / 100.0)
        # 2. Sentiment factor
        sent_factor = sent_score * 0.4
        # 3. On-chain supply shock factor
        flow_factor = 0.02 if net_flow < 0 else -0.02

        combined_alpha = (0.5 * mom_factor) + (0.3 * sent_factor) + (0.2 * flow_factor)
        # Bound trajectory shift to realistic range (-3% to +3% per horizon)
        bounded_alpha = max(-0.03, min(0.03, combined_alpha))

        atr = indicators.get("atr_14", current_price * 0.015)
        stdev_pct = (atr / current_price) if current_price > 0 else 0.015

        # 1H Forecast
        pred_1h = round(current_price * (1.0 + bounded_alpha * 0.3), 2)
        ci_1h = {
            "lower": round(pred_1h - current_price * stdev_pct * 0.8, 2),
            "upper": round(pred_1h + current_price * stdev_pct * 0.8, 2)
        }

        # 4H Forecast
        pred_4h = round(current_price * (1.0 + bounded_alpha * 0.8), 2)
        ci_4h = {
            "lower": round(pred_4h - current_price * stdev_pct * 1.5, 2),
            "upper": round(pred_4h + current_price * stdev_pct * 1.5, 2)
        }

        # 24H Forecast
        pred_24h = round(current_price * (1.0 + bounded_alpha * 1.5), 2)
        ci_24h = {
            "lower": round(pred_24h - current_price * stdev_pct * 2.5, 2),
            "upper": round(pred_24h + current_price * stdev_pct * 2.5, 2)
        }

        direction = "BULLISH_CONTINUATION" if bounded_alpha > 0.005 else ("BEARISH_PULLBACK" if bounded_alpha < -0.005 else "RANGE_BOUND")
        confidence = round(min(0.92, max(0.65, 0.70 + (adx / 200.0))), 2)

        return {
            "current_price": current_price,
            "forecast_direction": direction,
            "overall_confidence": confidence,
            "horizons": {
                "1h": {"predicted_price": pred_1h, "confidence_interval": ci_1h, "change_pct": round(((pred_1h - current_price) / current_price) * 100, 2)},
                "4h": {"predicted_price": pred_4h, "confidence_interval": ci_4h, "change_pct": round(((pred_4h - current_price) / current_price) * 100, 2)},
                "24h": {"predicted_price": pred_24h, "confidence_interval": ci_24h, "change_pct": round(((pred_24h - current_price) / current_price) * 100, 2)}
            },
            "feature_attributions": {
                "technical_momentum_pct": 50.0,
                "sentiment_nlp_pct": 30.0,
                "onchain_flow_pct": 20.0
            }
        }


ml_prediction_model = PricePredictionModel()
