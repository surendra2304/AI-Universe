"""Unit tests for Inference Trading Analyst Agent and Decision Formulation."""

import pytest
from app.agents.trading_analyst import AIUniverseDecision, TradingAnalyst, create_trading_analyst_agent
from app.agents.registry import agent_registry
from app.agents.router import router


def test_trading_analyst_agent_registration():
    """Verify Trading Analyst agent is registered with specialized roles and models."""
    agent = agent_registry.get_agent("trading_analyst")
    assert agent is not None
    assert agent.id == "trading_analyst"
    assert agent.role == "Trading Analyst"
    assert "ADVISORY_ONLY" in agent.metadata.get("safety_constraint", "")
    assert len(agent.models) >= 2


def test_router_selects_trading_analyst_for_trading_queries():
    """Verify TaskRouter identifies trading queries and routes to trading_analyst."""
    specialist = router.detect_domain_specialist("How is the trading bot win rate and profit factor doing?")
    assert specialist == "trading_analyst"
    
    review_pair = router.select_review_pair("Should we tighten scalper stop loss and take profit parameters?")
    assert review_pair == ["trading_analyst", "strategist"]
    
    panel = router.select_debate_panel("Debate whether to increase position sizing given current drawdown", max_agents=4)
    assert "trading_analyst" in panel


def test_trading_analyst_evaluate_drawdown_tighten():
    """Verify high drawdown triggers conservative risk tightening recommendation."""
    analyst = TradingAnalyst()
    metrics = {
        "win_rate": 38.0,
        "profit_factor": 0.85,
        "consecutive_losses": 5,
        "max_drawdown": 6.5,
        "total_trades": 45,
        "unrealized_pnl": -120.50
    }
    
    decision = analyst.evaluate_performance(metrics)
    assert isinstance(decision, AIUniverseDecision)
    assert "Tighten Stop Loss" in decision.recommendation
    assert decision.confidence >= 0.90
    assert decision.suggested_parameters.get("stop_loss_pct") == 0.004
    assert decision.suggested_parameters.get("max_leverage") == 5
    assert len(decision.evidence) >= 4
    assert "HIGH RISK" in decision.risk_assessment


def test_trading_analyst_evaluate_strong_performance():
    """Verify strong metrics maintain scalper baseline and suggest trailing stop activation."""
    analyst = TradingAnalyst()
    metrics = {
        "win_rate": 68.5,
        "profit_factor": 1.72,
        "consecutive_losses": 1,
        "max_drawdown": 0.0,
        "total_trades": 120,
        "unrealized_pnl": 168.64
    }
    
    decision = analyst.evaluate_performance(metrics)
    assert isinstance(decision, AIUniverseDecision)
    assert "Maintain 0.5% SL / 0.3% TP" in decision.recommendation
    assert decision.confidence >= 0.90
    assert "trailing_stop_activation" in decision.suggested_parameters
    assert "LOW RISK" in decision.risk_assessment


def test_trading_analyst_evaluate_suboptimal_expectancy():
    """Verify low profit factor triggers calibrated risk:reward expansion."""
    analyst = TradingAnalyst()
    metrics = {
        "win_rate": 41.0,
        "profit_factor": 1.02,
        "consecutive_losses": 2,
        "max_drawdown": 1.5,
        "total_trades": 50,
        "unrealized_pnl": 10.0
    }
    
    decision = analyst.evaluate_performance(metrics)
    assert isinstance(decision, AIUniverseDecision)
    assert decision.suggested_parameters.get("stop_loss_pct") == 0.004
    assert decision.suggested_parameters.get("take_profit_pct") == 0.006
    assert "MODERATE RISK" in decision.risk_assessment
