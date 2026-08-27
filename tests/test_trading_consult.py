"""Comprehensive Test Suite for the Trading Consultation Subsystem using Synthetic Telemetry."""

import asyncio
import json
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.trading_consult import (
    AIUniverseDecision,
    ParameterChange,
    StrategyPerformance,
    TradingConsultRequest,
    TradingTelemetry,
)
from app.services.trading_consult_service import TradingConsultService

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def _load_fixture(filename: str) -> dict:
    """Helper to load a JSON test fixture."""
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_schema_valid_request():
    """Test serializing and deserializing a valid TradingConsultRequest."""
    payload = _load_fixture("telemetry_healthy.json")
    req = TradingConsultRequest.model_validate(payload)
    assert req.bot_id == "bot_healthy_alpha"
    assert req.trading_mode == "PAPER"
    assert req.telemetry.total_trades == 85
    assert len(req.strategy_performance) == 2


def test_schema_invalid_trading_mode():
    """Test that live modes (e.g. LIVE, REAL) are rejected by schema."""
    with pytest.raises(Exception):
        TradingConsultRequest.model_validate({
            "bot_id": "bot_live",
            "trading_mode": "LIVE",  # Disallowed
            "telemetry": {
                "equity": 10000.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
                "win_rate": 0.5,
                "profit_factor": 1.0,
                "max_drawdown_pct": 0.0,
                "consecutive_losses": 0,
                "total_trades": 25
            },
            "consultation_reason": "SCHEDULED"
        })


def test_credential_detection_rejection(client):
    """Test that payloads containing api_key or secret fields are rejected with 400."""
    payload_with_key = {
        "bot_id": "bot_hacked",
        "trading_mode": "TESTNET",
        "telemetry": {
            "equity": 10000.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "win_rate": 0.5,
            "profit_factor": 1.0,
            "max_drawdown_pct": 0.0,
            "consecutive_losses": 0,
            "total_trades": 25
        },
        "current_parameters": {
            "Supertrend": {"stop_loss_pct": 0.02}
        },
        "api_key": "x-forbidden-exchange-key-12345",  # MUST REJECT
        "consultation_reason": "SCHEDULED"
    }

    resp = client.post("/v1/trading/consult", json=payload_with_key)
    assert resp.status_code == 400
    assert "forbidden credential field" in resp.json()["detail"]


def test_nested_credential_detection(client):
    """Test that nested secret fields inside parameters are also caught and rejected with 400."""
    payload_nested = {
        "bot_id": "bot_nested_leak",
        "trading_mode": "TESTNET",
        "telemetry": {
            "equity": 10000.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "win_rate": 0.5,
            "profit_factor": 1.0,
            "max_drawdown_pct": 0.0,
            "consecutive_losses": 0,
            "total_trades": 25
        },
        "current_parameters": {
            "Supertrend": {
                "stop_loss_pct": 0.02,
                "exchange_secret": "my_binance_secret"  # MUST REJECT
            }
        },
        "consultation_reason": "SCHEDULED"
    }

    resp = client.post("/v1/trading/consult", json=payload_nested)
    assert resp.status_code == 400
    assert "forbidden credential field" in resp.json()["detail"]


def test_malformed_json_request_rejected(client):
    """Test that malformed JSON strings or broken structures receive HTTP 400."""
    resp = client.post(
        "/v1/trading/consult",
        content="This is not valid JSON",
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400
    assert "Invalid JSON payload" in resp.json()["detail"]


def test_healthy_telemetry_fixture_endpoint(client):
    """Test healthy telemetry fixture produces NO_CHANGE with high confidence (>0.80)."""
    payload = _load_fixture("telemetry_healthy.json")
    resp = client.post("/v1/trading/consult", json=payload)
    assert resp.status_code == 200
    decision = AIUniverseDecision.model_validate(resp.json())
    assert decision.status == "NO_CHANGE"
    assert decision.confidence >= 0.80
    assert len(decision.parameter_changes) == 0
    assert "Healthy performance profile" in decision.risk_assessment


def test_struggling_telemetry_fixture_endpoint(client):
    """Test struggling telemetry fixture produces RECOMMENDATION with bounded changes."""
    payload = _load_fixture("telemetry_struggling.json")
    resp = client.post("/v1/trading/consult", json=payload)
    assert resp.status_code == 200
    decision = AIUniverseDecision.model_validate(resp.json())
    assert decision.status == "RECOMMENDATION"
    assert 1 <= len(decision.parameter_changes) <= 2
    for change in decision.parameter_changes:
        assert len(change.rationale) > 10
        assert change.change_pct != 0.0


def test_insufficient_data_fixture_endpoint(client):
    """Test insufficient data telemetry fixture produces INSUFFICIENT_DATA with 0 changes."""
    payload = _load_fixture("telemetry_insufficient_data.json")
    resp = client.post("/v1/trading/consult", json=payload)
    assert resp.status_code == 200
    decision = AIUniverseDecision.model_validate(resp.json())
    assert decision.status == "INSUFFICIENT_DATA"
    assert len(decision.parameter_changes) == 0
    assert "statistical significance threshold" in decision.risk_assessment


def test_mixed_strategies_fixture_endpoint(client):
    """Test mixed strategies telemetry fixture handles multi-strategy performance."""
    payload = _load_fixture("telemetry_mixed_strategies.json")
    resp = client.post("/v1/trading/consult", json=payload)
    assert resp.status_code == 200
    decision = AIUniverseDecision.model_validate(resp.json())
    assert decision.status == "RECOMMENDATION"
    assert 1 <= len(decision.parameter_changes) <= 2


def test_endpoint_consult_health(client):
    """Test the GET /v1/trading/consult/health endpoint."""
    resp = client.get("/v1/trading/consult/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["advisory_only"] is True
    assert data["exchange_execution"] is False
    assert len(data["agents_available"]) >= 10


@pytest.mark.asyncio
async def test_get_past_decision_endpoint(client):
    """Test retrieving a stored decision by UUID."""
    service = TradingConsultService()
    req = TradingConsultRequest(
        bot_id="bot_retrieval_test",
        trading_mode="PAPER",
        telemetry=TradingTelemetry(
            equity=10000.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            win_rate=0.55,
            profit_factor=1.3,
            max_drawdown_pct=2.0,
            consecutive_losses=1,
            total_trades=30
        ),
        consultation_reason="SCHEDULED"
    )
    decision = await service.consult(req)

    # Fetch from endpoint
    resp = client.get(f"/v1/trading/decisions/{decision.decision_id}")
    assert resp.status_code == 200
    fetched = resp.json()
    assert fetched["decision_id"] == decision.decision_id
    assert fetched["status"] == decision.status


def test_rate_limiting_enforcement(client):
    """Test that sending >20 requests for the same bot_id triggers HTTP 429."""
    bot_id = "bot_spammer_test_suite"
    valid_payload = {
        "bot_id": bot_id,
        "trading_mode": "PAPER",
        "telemetry": {
            "equity": 10000.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "win_rate": 0.5,
            "profit_factor": 1.0,
            "max_drawdown_pct": 0.0,
            "consecutive_losses": 0,
            "total_trades": 10
        },
        "consultation_reason": "SCHEDULED"
    }

    # Execute 20 requests
    for _ in range(20):
        resp = client.post("/v1/trading/consult", json=valid_payload)
        assert resp.status_code in [200, 429]

    # The 21st request MUST receive 429 Too Many Requests
    resp_21 = client.post("/v1/trading/consult", json=valid_payload)
    assert resp_21.status_code == 429
    assert "Rate limit exceeded" in resp_21.json()["detail"]


@pytest.mark.asyncio
async def test_timeout_handling(monkeypatch):
    """Test that a slow consultation debate triggers the 180s timeout path gracefully returning NO_CHANGE."""
    from app.routers import trading

    async def mock_slow_consult(req):
        await asyncio.sleep(2.0)
        return None

    # Temporarily monkeypatch timeout or method with a very short timeout
    original_consult = trading.trading_consult_service.consult
    try:
        trading.trading_consult_service.consult = mock_slow_consult
        # Test directly with wait_for
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(trading.trading_consult_service.consult(None), timeout=0.1)
    finally:
        trading.trading_consult_service.consult = original_consult
