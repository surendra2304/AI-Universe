"""Unit & Integration Tests for Futuris Statistical Forecasting & Enhancement Endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_futuris_forecast_enhancement():
    """Tests POST /v1/futuris/enhance endpoint."""
    req = {
        "request_id": "futuris-test-001",
        "statistical_forecast": {
            "metric_name": "quarterly_arr_growth",
            "point_estimate": 0.28,
            "confidence_interval": [0.21, 0.35],
            "probability": 0.85,
            "model_used": "GARCH-ARIMA-Hybrid"
        },
        "target_context": {
            "sector": "enterprise_saas",
            "macro_environment": "rate_cut_cycle"
        },
        "contextual_factors": [
            "Upcoming regulatory disclosure window in EU"
        ],
        "question": "Given this ARR growth forecast, what structural risks should be factored into cash runway?"
    }
    resp = client.post("/v1/futuris/enhance", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "futuris-test-001"
    assert "enhanced_assessment" in data
    assert len(data["enhanced_assessment"]["key_risks"]) >= 2
    assert len(data["enhanced_assessment"]["contextual_drivers"]) >= 1
    assert data["confidence_adjustment"] > 0.0
    assert len(data["dissent"]) >= 1


def test_futuris_provenance_retrieval():
    """Tests GET /v1/futuris/enhance/{request_id} retrieval."""
    resp = client.get("/v1/futuris/enhance/futuris-test-001")
    assert resp.status_code == 200
    record = resp.json()
    assert "request" in record
    assert "response" in record
    assert record["request"]["request_id"] == "futuris-test-001"

    # Non-existent ID returns 404
    resp_404 = client.get("/v1/futuris/enhance/non_existent_futuris_id")
    assert resp_404.status_code == 404


def test_statistical_grounding_engine():
    """Tests StatisticalGroundingEngine retrieval for other consumers."""
    from app.services.futuris_enhancement import futuris_enhancement_service

    grounding = futuris_enhancement_service.grounding_engine.get_grounding_context("volatility_btc")
    assert grounding is not None
    assert grounding["metric"] == "volatility_btc"
    assert grounding["grounding_available"] is True
    assert len(grounding["ci_95"]) == 2
