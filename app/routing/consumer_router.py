"""Multi-Consumer Router and Usage Attribution for Trading Bot, FORGE, FRIDAY, and Human users."""

import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ConsumerType = Literal["trading_bot", "forge", "friday", "human", "nexus", "sentinel", "intelx", "futuris"]


class ConsumerProfile(BaseModel):
    name: ConsumerType
    rate_limit_per_hour: int
    priority: int  # Higher is higher priority
    mode: str
    description: str


class ConsumerUsageRecord(BaseModel):
    consumer: ConsumerType
    total_calls: int = 0
    total_tokens: int = 0
    total_latency_seconds: float = 0.0
    estimated_cost_usd: float = 0.0


class MultiConsumerRouter:
    """Manages consumer identity, rate-limit policies, priority queues, and usage accounting."""

    PROFILES: Dict[ConsumerType, ConsumerProfile] = {
        "futuris": ConsumerProfile(
            name="futuris",
            rate_limit_per_hour=150,
            priority=2,
            mode="statistical_grounding",
            description="Futuris predictive forecasting and statistical grounding engine."
        ),
        "intelx": ConsumerProfile(
            name="intelx",
            rate_limit_per_hour=200,
            priority=2,
            mode="research_reasoning",
            description="IntelX autonomous deep research and evidence verification engine."
        ),
        "sentinel": ConsumerProfile(
            name="sentinel",
            rate_limit_per_hour=100,
            priority=2,
            mode="security_intelligence",
            description="Autonomous cybersecurity posture & threat analysis engine."
        ),
        "nexus": ConsumerProfile(
            name="nexus",
            rate_limit_per_hour=200,
            priority=2,
            mode="intelligence_routing",
            description="Nexus high-throughput intelligence decision engine."
        ),
        "forge": ConsumerProfile(
            name="forge",
            rate_limit_per_hour=200,
            priority=1,
            mode="code_generation",
            description="Autonomous software engineering engine with heavy per-file code generation."
        ),
        "trading_bot": ConsumerProfile(
            name="trading_bot",
            rate_limit_per_hour=20,
            priority=2,
            mode="conservative_advisory",
            description="Algorithmic trading consultation with isolated queue and strict bounds."
        ),
        "friday": ConsumerProfile(
            name="friday",
            rate_limit_per_hour=100,
            priority=3,
            mode="assistant",
            description="General purpose intelligence assistant."
        ),
        "human": ConsumerProfile(
            name="human",
            rate_limit_per_hour=50,
            priority=4,
            mode="interactive",
            description="Direct human developer queries with detailed explanations."
        )
    }

    def __init__(self) -> None:
        self.usage_records: Dict[ConsumerType, ConsumerUsageRecord] = {
            k: ConsumerUsageRecord(consumer=k) for k in self.PROFILES.keys()
        }

    def identify_consumer(self, api_key_or_header: Optional[str]) -> ConsumerType:
        """Determines the consumer from API key, header, or default fallback."""
        if not api_key_or_header:
            return "forge"  # Default for forge service paths
        val = api_key_or_header.lower()
        if "nexus" in val:
            return "nexus"
        elif "forge" in val:
            return "forge"
        elif "trading" in val or "bot" in val:
            return "trading_bot"
        elif "friday" in val:
            return "friday"
        return "human"

    def record_usage(self, consumer: ConsumerType, tokens: int, latency_sec: float) -> None:
        """Accumulates usage metrics."""
        rec = self.usage_records.get(consumer)
        if rec:
            rec.total_calls += 1
            rec.total_tokens += tokens
            rec.total_latency_seconds += latency_sec
            rec.estimated_cost_usd += (tokens / 1000.0) * 0.0005  # $0.0005 per 1k tokens proxy

    def get_usage(self, consumer: Optional[ConsumerType] = None) -> Dict[str, Any]:
        """Returns usage stats."""
        if consumer and consumer in self.usage_records:
            return self.usage_records[consumer].model_dump()
        return {k: v.model_dump() for k, v in self.usage_records.items()}


consumer_router = MultiConsumerRouter()
