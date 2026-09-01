"""Tests for Ecosystem Intelligence Hub, Continuous Learning, Meta-Intelligence, and Long-Term Memory."""

from fastapi.testclient import TestClient

from app.intelligence.meta_intel import meta_intelligence
from app.learning.continuous_learning import continuous_learning_engine
from app.main import app
from app.memory.long_term import long_term_memory

client = TestClient(app)


def test_long_term_memory_storage_and_retrieval():
    """Tests episodic, semantic, and procedural memory functions."""
    long_term_memory.record_episodic_event(
        scenario="Flash Crash Liquidity Sweep",
        conditions={"regime": "HIGH_VOLATILITY"},
        action="DEFENSIVE_STOP_TIGHTENING",
        outcome="+8.2% preserved",
        effectiveness=0.94
    )
    retrieved = long_term_memory.retrieve_relevant_learnings("HIGH_VOLATILITY")
    assert len(retrieved) >= 1
    assert "regime_correlations" in long_term_memory.semantic_memories


def test_continuous_learning_engine_adaptation():
    """Tests outcome logging and dynamic agent weight calculation."""
    continuous_learning_engine.record_outcome(
        consultation_id="c-999",
        action="REDUCE_POSITION_SIZING",
        drawdown_reduction_pct=3.5,
        outcome="HELPED"
    )
    status_data = continuous_learning_engine.get_learning_status()
    assert status_data["helpful_recommendation_rate_pct"] > 70.0
    assert "learned_agent_weights" in status_data
    assert status_data["learned_agent_weights"]["critic_agent"] >= 1.0


def test_meta_intelligence_self_assessment():
    """Tests self-calibration analysis and agent ranking."""
    meta_rep = meta_intelligence.generate_meta_intelligence_report()
    assert meta_rep["meta_intelligence_quality_score"] > 90.0
    assert len(meta_rep["agent_performance_ranking"]) >= 3
    assert len(meta_rep["identified_failure_patterns"]) >= 1


def test_ecosystem_api_endpoints():
    """Tests /v1/ecosystem/intelligence, /learning, /meta, and /consult endpoints."""
    # Intelligence report endpoint
    resp_intel = client.get("/v1/ecosystem/intelligence")
    assert resp_intel.status_code == 200
    assert "overall_ecosystem_intelligence_score" in resp_intel.json()

    # Learning status endpoint
    resp_learn = client.get("/v1/ecosystem/learning")
    assert resp_learn.status_code == 200
    assert "helpful_recommendation_rate_pct" in resp_learn.json()

    # Meta intelligence endpoint
    resp_meta = client.get("/v1/ecosystem/meta")
    assert resp_meta.status_code == 200
    assert "meta_intelligence_quality_score" in resp_meta.json()

    # Ecosystem consultation endpoint
    resp_consult = client.post(
        "/v1/ecosystem/consult",
        json={"portfolio_positions": {"BTCUSDT": 18000.0, "ETHUSDT": 9000.0}, "active_strategies": ["Trend", "ML"]}
    )
    assert resp_consult.status_code == 200
    assert "ecosystem_verdict" in resp_consult.json()
