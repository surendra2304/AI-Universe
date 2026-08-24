# Architecture of AI Universe

AI Universe is a local-first, multi-agent intelligence platform designed for deep reasoning, structured adversarial debate, persistent empirical memory, and provider-agnostic LLM orchestration.

---

## 1. Core Architectural Tenets

1. **Independent Intelligence**: AI Universe is an autonomous intelligence engine. FRIDAY is an autonomous agent operating at the OS and application layer. They communicate over strict, typed API boundaries.
2. **Confidence is Not Correctness**: Authoritative prose is separated from empirical validity. LLM confidence scores are calibrated, and meaningful dissent is preserved rather than smoothed over.
3. **Graceful Cost & Latency Degradation**: Trivial questions are routed to fast single-agent execution, while complex trade-offs trigger 6-Round adversarial debates.
4. **Zero Secrets in Code or Memory**: All keys are strictly loaded via environment variables and sanitized in logs and database stores.

---

## 2. System Layering

```
 ┌──────────────────────────────────────────────────────────┐
 │                     FastAPI & CLI Layer                  │
 │   /ask   │   /debate   │   /experiments   │   /health    │
 └────────────────────────────┬─────────────────────────────┘
                              │
 ┌────────────────────────────▼─────────────────────────────┐
 │                     Task Router Layer                    │
 │  - Domain Specialist Allocation (10 Specialist Roles)    │
 │  - Budget & Latency Guardrails (Degradation Engine)      │
 │  - Strategy Store Learned Recommendations                │
 └────────────────────────────┬─────────────────────────────┘
                              │
 ┌────────────────────────────▼─────────────────────────────┐
 │                    Orchestrator Core                     │
 │  - Fast Mode (Single Specialist)                         │
 │  - Review Mode (Specialist Pair)                         │
 │  - Debate Engine (6-Round Structured Adversarial Panel)   │
 └──────────────────────┬──────────────────────┬────────────┘
                        │                      │
 ┌──────────────────────▼───────┐  ┌───────────▼────────────┐
 │       Provider Gateway       │  │   Memory Subsystem     │
 │  - Google Gemini Adapter     │  │  - SQLite (aiosqlite)  │
 │  - Groq Adapter              │  │  - Agents & Tasks      │
 │  - Cerebras Adapter          │  │  - Runs & Messages     │
 │  - Mistral Adapter           │  │  - Memories (Scoped)   │
 │  - OpenRouter Adapter        │  │  - Strategies & Exp.   │
 └──────────────────────────────┘  └────────────────────────┘
```

---

## 3. The 6-Round Structured Debate Protocol

- **Round 0: Problem Framing**: Primary strategist produces a canonical problem statement with declared assumptions.
- **Round 1: Parallel Independent Analysis**: Specialists execute concurrently via `asyncio.gather` without seeing peer responses.
- **Round 2: Cross-Review & Adversarial Critique**: The `Critic` attacks weak assumptions, unstated trade-offs, and failure modes.
- **Round 3: Specialist Rebuttal**: Proposal authors respond, defend validated decisions, and concede valid critiques.
- **Round 4: Evidence & Fact Checking**: The `Fact Checker` separates claims from verifiable evidence.
- **Round 5: Consensus Synthesis**: The `Synthesizer` builds a final recommendation integrating surviving claims.
- **Round 6: Confidence Calibration**: Unresolved disagreements are permanently recorded and confidence is calibrated.

---

## 4. Evaluation & Learning Loop

- **8 Rubric Dimensions**: `correctness`, `relevance`, `completeness`, `reasoning_quality`, `evidence_quality`, `safety`, `latency`, `usage_efficiency`.
- **Hybrid Scoring**: LLM-as-a-judge (`gemini-2.5-pro`) for semantic quality + deterministic mathematical calculation for latency and token budgets.
- **Strategy Store & Performance Tracker**: Moving average empirical tracking optimizing future task routing based on historical outcomes.
