"""Tests for Cross-Market Data Aggregation, Correlation Matrix, Regime Intelligence, Liquidity Analysis, and Debate Specialists."""

import pytest
from fastapi.testclient import TestClient

from app.analysis.cross_asset import cross_asset_engine
from app.analysis.liquidity_intel import liquidity_intel
from app.analysis.market_regime_intel import regime_intel
from app.debate.market_debate import multi_market_debate
from app.main import app

client = TestClient(app)


def test_cross_exchange_endpoint():
    """Tests GET /v1/market/cross-exchange/{asset}."""
    resp = client.get("/v1/market/cross-exchange/BTC")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "BTCUSDT"
    assert "consolidated_mid_price" in data
    assert "exchange_breakdown" in data
    assert "binance" in data["exchange_breakdown"]
    assert "bybit" in data["exchange_breakdown"]


def test_correlation_matrix_and_portfolio_analysis():
    """Tests cross-asset correlation computation and concentration warnings."""
    corr_data = cross_asset_engine.get_correlation_matrix()
    assert "BTC" in corr_data["matrix_24h"]
    assert "SP500" in corr_data["matrix_24h"]["BTC"]

    # Test portfolio analysis
    positions = {"BTCUSDT": 20000.0, "ETHUSDT": 5000.0}
    analysis = cross_asset_engine.analyze_portfolio_correlation(positions)
    assert analysis["weighted_btc_correlation"] > 0.80
    assert analysis["concentration_risk_warning"] is True


def test_regime_classification_endpoint():
    """Tests GET /v1/market/regime."""
    resp = client.get("/v1/market/regime")
    assert resp.status_code == 200
    data = resp.json()
    assert "macro_regime" in data
    assert "transition_probabilities_48h" in data
    assert "stay_current_regime" in data["transition_probabilities_48h"]


def test_liquidity_analysis_endpoint():
    """Tests GET /v1/market/liquidity/{asset}."""
    resp = client.get("/v1/market/liquidity/ETH")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "ETHUSDT"
    assert "slippage_estimates" in data
    assert "order_50k_usd" in data["slippage_estimates"]


def test_portfolio_market_debate_endpoint():
    """Tests POST /v1/market/portfolio-analysis multi-agent deliberation."""
    payload = {"positions": {"BTCUSDT": 10000.0, "ETHUSDT": 5000.0, "SOLUSDT": 2000.0}}
    resp = client.post("/v1/market/portfolio-analysis", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "portfolio_market_consensus" in data
    assert len(data["specialist_deliberations"]) == 3
    specialist_names = [s["specialist"] for s in data["specialist_deliberations"]]
    assert "Macro Analyst" in specialist_names
    assert "Liquidity Analyst" in specialist_names
    assert "Correlation Analyst" in specialist_names
