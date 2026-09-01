"""Unit tests for SQLite persistent memory storage."""

from datetime import datetime

import pytest
import pytest_asyncio

from app.memory.base import MemoryRecord, RunRecord, TaskRecord
from app.memory.sqlite import SQLiteMemory


@pytest_asyncio.fixture
async def memory_store():
    store = SQLiteMemory(db_path=":memory:")
    await store.initialize()
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_agent_persistence(memory_store):
    agent_data = {
        "id": "critic",
        "name": "Red Team Critic",
        "role": "Critic",
        "model_provider": "gemini",
        "model_name": "gemini-2.5-flash",
        "status": "active",
        "strengths": ["adversarial critique", "fallacy detection"]
    }
    await memory_store.save_agent(agent_data)

    # Upsert with modified status
    agent_data["status"] = "paused"
    await memory_store.save_agent(agent_data)


@pytest.mark.asyncio
async def test_task_save_and_retrieve(memory_store):
    task = TaskRecord(
        id="task_test_001",
        question="What is the architectural goal of Inference?",
        mode="debate",
        status="running",
        metadata={"priority": "high"}
    )
    await memory_store.save_task(task)

    retrieved = await memory_store.get_task("task_test_001")
    assert retrieved is not None
    assert retrieved.id == "task_test_001"
    assert retrieved.question == "What is the architectural goal of Inference?"
    assert retrieved.status == "running"
    assert retrieved.metadata.get("priority") == "high"

    # Update task result and status
    retrieved.status = "completed"
    retrieved.result = "A local-first multi-agent intelligence platform."
    retrieved.confidence = 0.95
    retrieved.completed_at = datetime.utcnow()
    await memory_store.save_task(retrieved)

    updated = await memory_store.get_task("task_test_001")
    assert updated.status == "completed"
    assert updated.result == "A local-first multi-agent intelligence platform."
    assert updated.confidence == 0.95


@pytest.mark.asyncio
async def test_run_audit_persistence(memory_store):
    task = TaskRecord(id="task_002", question="Test question")
    await memory_store.save_task(task)

    run = RunRecord(
        id="run_test_001",
        task_id="task_002",
        agent_id="researcher",
        provider="gemini",
        model="gemini-2.5-flash",
        stage="round_1_analysis",
        prompt_tokens=100,
        completion_tokens=200,
        latency_seconds=1.25,
        status="completed"
    )
    await memory_store.save_run(run)


@pytest.mark.asyncio
async def test_agent_memory_scoping_and_search(memory_store):
    # Create memories for two distinct agents
    mem1 = MemoryRecord(
        id="mem_1",
        agent_id="architect",
        content="Prefers modular decoupling over tight integration.",
        importance=0.9,
        context_tags=["architecture", "principles"]
    )
    mem2 = MemoryRecord(
        id="mem_2",
        agent_id="architect",
        content="Standardizes on REST API with typed Pydantic contracts.",
        importance=0.7,
        context_tags=["api", "contracts"]
    )
    mem3 = MemoryRecord(
        id="mem_3",
        agent_id="security",
        content="Enforces zero-secret storage in logs and prompts.",
        importance=0.95,
        context_tags=["security", "secrets"]
    )

    await memory_store.save_memory(mem1)
    await memory_store.save_memory(mem2)
    await memory_store.save_memory(mem3)

    # Verify strict agent scoping
    architect_mems = await memory_store.get_agent_memories("architect")
    assert len(architect_mems) == 2
    assert architect_mems[0].id == "mem_1"  # Highest importance first
    assert architect_mems[1].id == "mem_2"

    security_mems = await memory_store.get_agent_memories("security")
    assert len(security_mems) == 1
    assert security_mems[0].id == "mem_3"

    # Search memories across all agents
    all_matched = await memory_store.search_memories("modular")
    assert len(all_matched) == 1
    assert all_matched[0].agent_id == "architect"

    # Search scoped to security
    sec_matched = await memory_store.search_memories("secret", agent_id="security")
    assert len(sec_matched) == 1
    assert sec_matched[0].id == "mem_3"
