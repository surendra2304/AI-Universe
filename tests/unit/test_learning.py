"""Unit tests for Learning Subsystem: PerformanceTracker and StrategyStore."""

import pytest
import pytest_asyncio
from app.learning.performance import PerformanceTracker
from app.learning.strategy_store import StrategyStore
from app.memory.base import ExperimentRecord
from app.memory.sqlite import SQLiteMemory


@pytest_asyncio.fixture
async def learning_env(tmp_path):
    test_db = str(tmp_path / "test_learning.db")
    memory = SQLiteMemory(db_path=test_db)
    await memory.initialize()
    tracker = PerformanceTracker(memory=memory)
    store = StrategyStore(memory=memory)
    return memory, tracker, store


@pytest.mark.asyncio
async def test_strategy_store_save_and_recommend(learning_env):
    memory, tracker, store = learning_env

    # 1. Initially no strategy for architecture
    rec_initial = await store.recommend_strategy("architect")
    assert rec_initial is None

    # 2. Save high-performing learned pattern
    await store.save_learned_pattern(
        task_type="architect",
        mode="debate",
        agents=["architect", "security_analyst", "critic"],
        score=0.92,
        provider="gemini",
        model="gemini-2.5-pro"
    )

    # 3. Retrieve recommendation
    rec = await store.recommend_strategy("architect")
    assert rec is not None
    assert rec.task_type == "architect"
    assert rec.recommended_mode == "debate"
    assert "security_analyst" in rec.recommended_agents
    assert rec.confidence >= 0.75
    assert rec.historical_score == 0.92
    assert rec.sample_size == 1

    # 4. Update with a second task outcome (moving average calculation)
    await store.save_learned_pattern(
        task_type="architect",
        mode="debate",
        agents=["architect", "security_analyst", "critic"],
        score=0.88
    )

    rec_updated = await store.recommend_strategy("architect")
    assert rec_updated.sample_size == 2
    assert rec_updated.historical_score == 0.90  # (0.92 + 0.88) / 2


@pytest.mark.asyncio
async def test_experiments_persistence(learning_env):
    memory, tracker, store = learning_env

    exp = ExperimentRecord(
        id="exp_001_multi_model",
        hypothesis="Does Gemini 2.5 Pro outperform Groq Llama-3.3 on architectural critique?",
        configuration={"models": ["gemini-2.5-pro", "groq:llama-3.3-70b"], "rounds": 6},
        status="completed",
        result={"winner": "gemini-2.5-pro", "score_diff": 0.08}
    )

    await memory.save_experiment(exp)

    retrieved = await memory.get_experiment("exp_001_multi_model")
    assert retrieved is not None
    assert retrieved.id == "exp_001_multi_model"
    assert retrieved.result["winner"] == "gemini-2.5-pro"
    assert retrieved.status == "completed"


@pytest.mark.asyncio
async def test_performance_tracker_statistics(learning_env):
    memory, tracker, store = learning_env

    await tracker.record_task_outcome(
        task_id="task_test_perf_01",
        task_type="coding",
        mode="fast",
        agents=["coder"],
        score=0.95,
        latency_s=0.9,
        tokens=350
    )

    stats = await tracker.compute_model_statistics()
    assert "top_reasoning_model" in stats
    assert "fastest_execution_model" in stats
    assert "most_effective_critic" in stats
