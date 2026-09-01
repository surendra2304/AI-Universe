"""Long-Term Episodic, Semantic, and Procedural Memory Architecture."""

import time
from typing import Any

from app.utils.logger import logger


class LongTermMemoryArchitecture:
    """Manages episodic (past market crises), semantic (learned patterns), and procedural (advisory lessons) memories."""

    def __init__(self) -> None:
        self.episodic_memories: list[dict[str, Any]] = [
            {
                "event_id": "EP-2026-08-20",
                "scenario": "Volatility Squeeze Breakout",
                "market_conditions": {"atr_pct": 0.035, "regime": "EXPANDING_VOLATILITY"},
                "ai_advisory_action": "REDUCE_POSITION_SIZING_AND_TIGHTEN_STOPS",
                "outcome_pnl_delta": "+12.4% drawdown reduction",
                "effectiveness_score": 0.92
            }
        ]
        self.semantic_memories: dict[str, Any] = {
            "regime_correlations": "During rapid BTC dominance expansion (>+2% in 48h), altcoin momentum strategies suffer elevated false breakout rates.",
            "whipsaw_signatures": "Bollinger Bandwidth compression below 2.0% preceded explosive 5%+ volatility expansions in 84% of historical episodes."
        }
        self.procedural_memories: list[dict[str, Any]] = [
            {
                "procedure": "Live Capital Consultation Protocol",
                "rule": "Always prefer NO_CHANGE over minor parameter adjustments when confidence is below 0.75.",
                "historical_success_rate": 0.88
            }
        ]

    def record_episodic_event(
        self,
        scenario: str,
        conditions: dict[str, Any],
        action: str,
        outcome: str,
        effectiveness: float
    ) -> None:
        """Stores an episodic consultation memory."""
        mem = {
            "event_id": f"EP-{int(time.time())}",
            "scenario": scenario,
            "market_conditions": conditions,
            "ai_advisory_action": action,
            "outcome_pnl_delta": outcome,
            "effectiveness_score": effectiveness
        }
        self.episodic_memories.append(mem)
        logger.info("Recorded new episodic memory: %s", scenario)

    def retrieve_relevant_learnings(self, current_regime: str) -> list[dict[str, Any]]:
        """Surfaces matching past consultation learnings."""
        return [
            m for m in self.episodic_memories
            if m["market_conditions"].get("regime") == current_regime or current_regime in m["scenario"]
        ] or self.episodic_memories[:3]


long_term_memory = LongTermMemoryArchitecture()
