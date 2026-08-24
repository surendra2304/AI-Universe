# AI Universe REST API Reference

AI Universe exposes clean, typed FastAPI REST endpoints for orchestration, structured multi-agent debates, evaluations, and benchmarks.

---

## Endpoints

### 1. Ask a Question
`POST /ask`

Auto-routes the question to Fast, Review, or Debate mode based on semantic triggers, budget, and latency guardrails.

**Request Body:**
```json
{
  "question": "How do I implement an asynchronous token bucket in Python?",
  "mode": "auto",
  "max_agents": 5,
  "require_evidence": true,
  "max_budget": 0.05,
  "max_latency": 15.0
}
```

**Response (200 OK):**
```json
{
  "task_id": "task_a1b2c3d4e5f6",
  "run_id": "run_01a2b3c4d5e6",
  "answer": "...",
  "mode_used": "fast",
  "provider": "gemini",
  "models_used": ["gemini-2.5-flash"],
  "agents_used": ["coder"],
  "confidence": 0.90,
  "latency_seconds": 0.45,
  "total_tokens": 180,
  "unresolved_disagreements": [],
  "key_evidence": []
}
```

---

### 2. Trigger Structured Debate
`POST /debate`

Explicitly triggers the 6-Round Structured Multi-Agent Debate Engine.

**Request Body:**
```json
{
  "question": "Compare microservices vs modular monolith for low-latency fintech platforms.",
  "max_agents": 5,
  "require_evidence": true
}
```

**Response (200 OK):**
```json
{
  "task_id": "task_e1f2a3b4c5d6",
  "run_id": "deb_9876543210ab",
  "answer": "Synthesized consensus recommendation...",
  "mode_used": "debate",
  "agents_used": ["architect", "security_analyst", "coder", "critic", "strategist"],
  "models_used": ["gemini-2.5-pro", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-pro"],
  "confidence": 0.88,
  "unresolved_disagreements": [
    "Trade-off between extreme low-latency vs strict cross-node consistency requires empirical load validation."
  ],
  "key_evidence": [
    "Verified modular decoupling minimizes single points of failure."
  ],
  "total_tokens": 820,
  "latency_seconds": 2.85
}
```

---

### 3. Trigger Benchmark / Comparison Experiment
`POST /experiments`

**Request Body:**
```json
{
  "experiment_type": "baseline_vs_debate",
  "question": "What is the optimal caching architecture for read-heavy workloads?"
}
```

**Response (200 OK):**
```json
{
  "id": "exp_comp_1234567890ab",
  "hypothesis": "Does multi-agent structured debate outperform single-agent baseline on reasoning quality?",
  "status": "completed",
  "result": {
    "winner": "debate",
    "score_difference": 0.12,
    "fast_baseline": { "score": 0.82, "latency": 0.45 },
    "multi_agent_debate": { "score": 0.94, "latency": 2.10 }
  }
}
```

---

### 4. Query Task or Experiment by ID
- `GET /tasks/{task_id}`: Returns audit details, execution status, and final answer.
- `GET /experiments/{experiment_id}`: Returns experiment metrics and configuration.
- `GET /health`: Returns service health status (`{"status": "healthy"}`).
