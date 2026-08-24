# AI Universe — System Architecture

## 1. Architectural Philosophy
AI Universe is designed as a **local-first, provider-agnostic multi-agent intelligence platform**. Rather than performing fictional or unbounded autonomous operations, it provides structured multi-model reasoning, adversarial debate, verifiable claim extraction, evaluation, and learning.

## 2. Core Subsystems
1. **API Layer (`app/api`)**: Exposes FastAPI endpoints for client applications, CLI, and FRIDAY integration.
2. **Orchestrator Core (`app/core`)**: Coordinates tasks, determines execution paths, manages lifecycle.
3. **Task Router (`app/agents/router.py`)**: Classifies complexity (Fast, Review, Debate) to prevent excessive agent fan-out.
4. **Agent Registry & Manager (`app/agents`)**: Manages agent identities, prompts, capabilities, and memory boundaries.
5. **Debate Engine (`app/agents/debate.py`)**: Implements the 6-round structured debate protocol.
6. **Multi-Provider Gateway (`app/providers`)**: Unified abstraction for Gemini, Groq, Cerebras, Mistral, and OpenRouter.
7. **Memory Layer (`app/memory`)**: SQLite-backed 4-layer persistent memory scoped by `agent_id`.
8. **Evaluator Subsystem (`app/evaluation`)**: Multi-dimensional scoring (Correctness, Reasoning, Evidence, Safety, Efficiency).
9. **Learning Store (`app/learning`)**: Historical strategy optimization based on empirical outcomes.
