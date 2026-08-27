"""Usage Analytics Engine for Multi-Consumer Tracking (FORGE, Trading Bot, FRIDAY, Human)."""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RequestAnalyticsRecord(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    consumer: str
    service: str
    provider: str
    tokens_in: int = 0
    tokens_out: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    confidence: float = 0.90
    cost_usd: float = 0.0


class UsageAnalyticsEngine:
    """Aggregates per-request tokens, latency, cost attribution, and daily ceiling budgets."""

    def __init__(self) -> None:
        self.records: List[RequestAnalyticsRecord] = [
            RequestAnalyticsRecord(consumer="forge", service="generate-code", provider="groq", tokens_in=500, tokens_out=800, total_tokens=1300, latency_ms=32.4, success=True, confidence=0.92, cost_usd=0.00065),
            RequestAnalyticsRecord(consumer="forge", service="plan-architecture", provider="nvidia", tokens_in=800, tokens_out=1200, total_tokens=2000, latency_ms=85.1, success=True, confidence=0.95, cost_usd=0.00100),
            RequestAnalyticsRecord(consumer="trading_bot", service="trading_consult", provider="groq", tokens_in=400, tokens_out=600, total_tokens=1000, latency_ms=45.0, success=True, confidence=0.88, cost_usd=0.00050),
            RequestAnalyticsRecord(consumer="friday", service="general_query", provider="gemini", tokens_in=200, tokens_out=300, total_tokens=500, latency_ms=28.0, success=True, confidence=0.94, cost_usd=0.00025)
        ]
        self.daily_budget_usd = 10.0
        self.alert_threshold_pct = 0.80

    def log_request(
        self,
        consumer: str,
        service: str,
        provider: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        success: bool = True,
        confidence: float = 0.90
    ) -> None:
        total_tokens = tokens_in + tokens_out
        cost_usd = (total_tokens / 1000.0) * 0.0005  # $0.0005 per 1k token proxy
        self.records.append(
            RequestAnalyticsRecord(
                consumer=consumer,
                service=service,
                provider=provider,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                success=success,
                confidence=confidence,
                cost_usd=cost_usd
            )
        )

    def get_overview(self) -> Dict[str, Any]:
        total_calls = len(self.records)
        total_tokens = sum(r.total_tokens for r in self.records)
        total_cost = sum(r.cost_usd for r in self.records)
        avg_latency = (sum(r.latency_ms for r in self.records) / total_calls) if total_calls > 0 else 0.0

        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "average_latency_ms": round(avg_latency, 2),
            "daily_budget_usd": self.daily_budget_usd,
            "budget_used_pct": round((total_cost / max(0.1, self.daily_budget_usd)) * 100.0, 2),
            "ceiling_alert_active": (total_cost / max(0.1, self.daily_budget_usd)) >= self.alert_threshold_pct
        }

    def get_consumer_breakdown(self, consumer_id: str) -> Dict[str, Any]:
        c_records = [r for r in self.records if r.consumer.lower() == consumer_id.lower()]
        total_calls = len(c_records)
        return {
            "consumer": consumer_id,
            "calls": total_calls,
            "tokens": sum(r.total_tokens for r in c_records),
            "cost_usd": round(sum(r.cost_usd for r in c_records), 4),
            "success_rate_pct": round((sum(1 for r in c_records if r.success) / max(1, total_calls)) * 100.0, 1)
        }

    def get_service_breakdown(self, service_name: str) -> Dict[str, Any]:
        s_records = [r for r in self.records if r.service.lower() == service_name.lower()]
        total_calls = len(s_records)
        return {
            "service": service_name,
            "calls": total_calls,
            "tokens": sum(r.total_tokens for r in s_records),
            "avg_latency_ms": round((sum(r.latency_ms for r in s_records) / max(1, total_calls)), 2)
        }

    def get_providers_comparison(self) -> Dict[str, Any]:
        providers = ["gemini", "groq", "mistral", "openrouter", "nvidia", "cohere", "huggingface"]
        res = {}
        for p in providers:
            p_recs = [r for r in self.records if r.provider.lower() == p]
            calls = len(p_recs)
            res[p] = {
                "calls": calls,
                "tokens": sum(r.total_tokens for r in p_recs),
                "cost_usd": round(sum(r.cost_usd for r in p_recs), 4),
                "avg_latency_ms": round(sum(r.latency_ms for r in p_recs) / max(1, calls), 1) if calls > 0 else 0.0
            }
        return res


usage_analytics = UsageAnalyticsEngine()
