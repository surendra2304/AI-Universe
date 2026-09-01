"""Tests for Deep Learning Models, Alternative Data Ingestion, Prediction Aggregation, and Accuracy Tracking."""

from fastapi.testclient import TestClient

from app.data.alternative_data import alt_data_engine
from app.main import app
from app.ml.deep_models import deep_models_engine
from app.ml.prediction_aggregator import prediction_aggregator

client = TestClient(app)


def test_deep_learning_price_predictor_inference():
    """Tests LSTM/Transformer inference and GARCH volatility forecasting."""
    res = deep_models_engine.predict_horizons(
        symbol="BTCUSDT",
        current_price=65200.0,
        recent_returns=[0.001, -0.002, 0.003, 0.002, 0.005]
    )
    assert res["symbol"] == "BTCUSDT"
    assert "horizons" in res
    assert "1h" in res["horizons"]
    assert "4h" in res["horizons"]
    assert "24h" in res["horizons"]
    assert res["inference_latency_ms"] < 100.0
    assert "volatility_forecast" in res


def test_alternative_data_engine():
    """Tests alternative data normalization (news, social, onchain, macro)."""
    data = alt_data_engine.get_consolidated_alternative_data("BTC")
    assert "news_intelligence" in data
    assert "social_intelligence" in data
    assert "onchain_intelligence" in data
    assert "macro_intelligence" in data
    assert data["onchain_intelligence"]["exchange_netflow_24h_usd"] < 0


def test_prediction_aggregation_engine():
    """Tests multi-source ensemble prediction aggregation."""
    res = prediction_aggregator.aggregate_prediction(
        symbol="BTCUSDT",
        current_price=65200.0,
        recent_returns=[0.002, 0.001, 0.004]
    )
    assert res["unified_direction"] in ("BULLISH", "BEARISH", "NEUTRAL")
    assert res["unified_confidence"] >= 0.60
    assert len(res["key_drivers"]) >= 1


def test_predictions_api_endpoints():
    """Tests GET /v1/predict/{asset}, GET /v1/intelligence/summary, and GET /v1/intelligence/accuracy."""
    # Predict endpoint
    resp_pred = client.get("/v1/predict/BTC")
    assert resp_pred.status_code == 200
    assert resp_pred.json()["symbol"] == "BTCUSDT"

    # Prediction history endpoint
    resp_hist = client.get("/v1/predict/BTC/history")
    assert resp_hist.status_code == 200
    assert len(resp_hist.json()["history"]) > 0

    # Intelligence summary endpoint
    resp_summary = client.get("/v1/intelligence/summary?asset=ETH")
    assert resp_summary.status_code == 200
    assert resp_summary.json()["asset"] == "ETH"

    # Accuracy report endpoint
    resp_acc = client.get("/v1/intelligence/accuracy")
    assert resp_acc.status_code == 200
    assert "overall_directional_accuracy_pct" in resp_acc.json()

    # Refresh endpoint
    resp_ref = client.post("/v1/predict/refresh")
    assert resp_ref.status_code == 200
    assert resp_ref.json()["status"] == "REFRESHED"
