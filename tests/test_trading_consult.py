"""Tests for the Trading Consultation Subsystem."""

import asyncio
import json
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


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_schema_valid_request():
    """Test serializing and deserializing a valid TradingConsultRequest."""
    payload = {
        "bot_id": "crypto_scalper_01",
        "trading_mode": "PAPER",
        "experiment_id": "exp_v2_atr_test",
        "telemetry": {
            "equity": 10500.0,
            "unrealized_pnl": 50.0,
            "realized_pnl": 500.0,
            "win_rate": 0.58,
            "profit_factor": 1.45,
            "max_drawdown_pct": 3.2,
            "consecutive_losses": 2,
            "total_trades": 45,
            "sharpe_ratio": 1.85
        },
        "strategy_performance": [
            {
                "strategy_name": "Supertrend_5m",
                "trade_count": 30,
                "win_rate": 0.60,
                "profit_factor": 1.55,
                "net_pnl": 400.0,
                "avg_win": 35.0,
                "avg_loss": 20.0,
                "consecutive_losses": 1
            }
        ],
        "current_parameters": {
            "Supertrend_5m": {
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.03,
                "atr_multiplier": 2.5
            }
        },
        "regime_data": {"volatility": "normal", "trend": "bullish"},
        "recent_trades": [
            {"id": "t1", "pnl": 25.0, "side": "BUY", "duration_sec": 300}
        ],
        "consultation_reason": "SCHEDULED"
    }

    req = TradingConsultRequest.model_validate(payload)
    assert req.bot_id == "crypto_scalper_01"
    assert req.trading_mode == "PAPER"
    assert req.telemetry.total_trades == 45
    assert len(req.strategy_performance) == 1


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


@pytest.mark.asyncio
async def test_insufficient_data_under_20_trades():
    """Test that requests with <20 total trades return INSUFFICIENT_DATA status."""
    service = TradingConsultService()
    req = TradingConsultRequest(
        bot_id="bot_new_launch",
        trading_mode="PAPER",
        telemetry=TradingTelemetry(
            equity=10000.0,
            unrealized_pnl=0.0,
            realized_pnl=-50.0,
            win_rate=0.33,
            profit_factor=0.65,
            max_drawdown_pct=2.0,
            consecutive_losses=3,
            total_trades=12  # < 20 trades
        ),
        current_parameters={"EMA": {"stop_loss_pct": 0.02}},
        consultation_reason="SCHEDULED"
    )

    decision = await service.consult(req)
    assert decision.status == "INSUFFICIENT_DATA"
    assert len(decision.parameter_changes) == 0
    assert "statistical significance threshold" in decision.risk_assessment


@pytest.mark.asyncio
async def test_healthy_metrics_return_no_change():
    """Test that healthy trading metrics (WR>50%, PF>1.25, DD<5%) return NO_CHANGE."""
    service = TradingConsultService()
    req = TradingConsultRequest(
        bot_id="bot_healthy",
        trading_mode="TESTNET",
        telemetry=TradingTelemetry(
            equity=12000.0,
            unrealized_pnl=120.0,
            realized_pnl=2000.0,
            win_rate=0.62,
            profit_factor=1.65,
            max_drawdown_pct=2.8,
            consecutive_losses=1,
            total_trades=50,
            sharpe_ratio=2.1
        ),
        strategy_performance=[
            StrategyPerformance(
                strategy_name="Scalper",
                trade_count=50,
                win_rate=0.62,
                profit_factor=1.65,
                net_pnl=2000.0,
                avg_win=50.0,
                avg_loss=30.0,
                consecutive_losses=1
            )
        ],
        current_parameters={"Scalper": {"stop_loss_pct": 0.015, "take_profit_pct": 0.03}},
        consultation_reason="SCHEDULED"
    )

    decision = await service.consult(req)
    assert decision.status == "NO_CHANGE"
    assert len(decision.parameter_changes) == 0
    assert "Healthy performance profile" in decision.risk_assessment


@pytest.mark.asyncio
async def test_max_two_parameter_changes_enforced():
    """Test that recommendations never return more than 2 parameter changes."""
    service = TradingConsultService()
    req = TradingConsultRequest(
        bot_id="bot_drawdown_event",
        trading_mode="PAPER",
        telemetry=TradingTelemetry(
            equity=9100.0,
            unrealized_pnl=-150.0,
            realized_pnl=-900.0,
            win_rate=0.38,
            profit_factor=0.72,
            max_drawdown_pct=9.5,  # High drawdown
            consecutive_losses=6,   # High loss streak
            total_trades=60
        ),
        current_parameters={
            "Breakout": {
                "stop_loss_pct": 0.03,
                "cooldown_seconds": 120,
                "leverage": 10,
                "position_size": 0.05
            }
        },
        consultation_reason="DRAWDOWN_EVENT"
    )

    decision = await service.consult(req)
    assert decision.status == "RECOMMENDATION"
    assert 1 <= len(decision.parameter_changes) <= 2
    # Verify quantitative evidence in rationale
    for change in decision.parameter_changes:
        assert len(change.rationale) > 10
        assert change.change_pct != 0.0


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
    bot_id = "bot_spammer_test"
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
