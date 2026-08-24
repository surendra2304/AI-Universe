"""Curated golden benchmark dataset."""

GOLDEN_BENCHMARK_PROMPTS = [
    {"domain": "architecture", "prompt": "What architecture should I use for a local-first multi-agent AI system?"},
    {"domain": "coding", "prompt": "Implement a rate-limiter with token bucket algorithm in async Python."},
    {"domain": "debugging", "prompt": "Diagnose why async sqlite connections deadlocked under concurrent writes."},
    {"domain": "security", "prompt": "Perform threat modeling for an agent allowed to execute shell commands."},
    {"domain": "fact_checking", "prompt": "Verify the claim: Cerebras CS-3 delivers 125 petaflops of AI compute."},
    {"domain": "strategy", "prompt": "Compare trade-offs between dense vs mixture-of-experts models for code synthesis."}
]
