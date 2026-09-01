"""Integration and Unit Tests for Advanced Market Intelligence, Sentiment, On-Chain, and ML Predictions."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_market_analysis_endpoint():
    """Tests the GET /v1/trading/market/analysis multi-agent deliberation endpoint."""
    resp = client.get("/v1/trading/market/analysis?symbol=BTCUSDT")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "BTCUSDT"
    assert "overall_consensus" in data
    assert "overall_confidence" in data
    assert "technical_indicators" in data
    assert "sentiment_analysis" in data
    assert "onchain_analytics" in data
    assert "price_predictions" in data
    assert len(data["specialist_deliberations"]) == 4


def test_market_sentiment_endpoint():
    """Tests the GET /v1/trading/market/sentiment NLP extraction endpoint."""
    resp = client.get("/v1/trading/market/sentiment?symbol=BTC")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "BTC"
    sentiment = data["sentiment"]
    assert "overall_score" in sentiment
    assert "classification" in sentiment
    assert "extracted_entities" in sentiment
    assert "detected_events" in sentiment


def test_onchain_metrics_endpoint():
    """Tests the GET /v1/trading/market/onchain blockchain metrics endpoint."""
    resp = client.get("/v1/trading/market/onchain?symbol=BTC")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "BTC"
    assert "network_health" in data
    assert "whale_movements" in data
    assert "exchange_flows" in data
    assert len(data["whale_movements"]) >= 1


def test_ml_price_prediction_endpoint():
    """Tests the POST /v1/trading/predict ML forecasting endpoint."""
    payload = {
        "symbol": "BTCUSDT",
        "current_price": 65200.0
    }
    resp = client.post("/v1/trading/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "BTCUSDT"
    pred = data["prediction"]
    assert "forecast_direction" in pred
    assert "horizons" in pred
    assert "1h" in pred["horizons"]
    assert "4h" in pred["horizons"]
    assert "24h" in pred["horizons"]
    assert "confidence_interval" in pred["horizons"]["24h"]


def test_market_monitor_alerts_endpoint():
    """Tests the GET /v1/trading/monitor/alerts anomaly detector endpoint."""
    resp = client.get("/v1/trading/monitor/alerts?symbol=BTCUSDT")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "BTCUSDT"
    assert "active_alerts_count" in data
    assert "alerts" in data


def test_historical_analysis_endpoint():
    """Tests the GET /v1/trading/history/analysis endpoint."""
    resp = client.get("/v1/trading/history/analysis?symbol=BTCUSDT")
    assert resp.status_code == 200
    data = resp.json()

    assert data["symbol"] == "BTCUSDT"
    assert "indicators" in data
    assert data["candle_count"] > 0
