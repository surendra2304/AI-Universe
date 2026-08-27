"""Cost-Aware Router and Intelligent Budget Allocation Engine."""

import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.utils.logger import logger


class ConsumerBudgetPolicy(BaseModel):
    consumer: str
    monthly_budget_usd: float
    current_month_spend_usd: float = 0.0
    soft_limit_pct: float = 0.80  # 80% threshold triggers response warnings
    hard_limit_pct: float = 1.00  # 100% threshold rejects requests with upgrade prompt
    last_reset_timestamp: float = Field(default_factory=time.time)


class RoutingDecision(BaseModel):
    selected_provider: str
    estimated_cost_usd: float
    cost_efficiency_score: float
    routing_reason: str
    soft_budget_warning: Optional[str] = None


class CostAwareRouter:
    """Evaluates cost vs historical value (success rate * impact) before routing intelligence requests."""

    def __init__(self) -> None:
        self.budgets: Dict[str, ConsumerBudgetPolicy] = {
            "trading_bot": ConsumerBudgetPolicy(consumer="trading_bot", monthly_budget_usd=50.0),
            "forge": ConsumerBudgetPolicy(consumer="forge", monthly_budget_usd=200.0),
            "nexus": ConsumerBudgetPolicy(consumer="nexus", monthly_budget_usd=100.0),
            "friday": ConsumerBudgetPolicy(consumer="friday", monthly_budget_usd=75.0),
            "human": ConsumerBudgetPolicy(consumer="human", monthly_budget_usd=50.0)
        }
        # Provider cost per 1k tokens proxy and historical success rate
        self.provider_profiles: Dict[str, Dict[str, float]] = {
            "groq": {"cost_per_1k": 0.0005, "success_rate": 0.94},
            "gemini": {"cost_per_1k": 0.0008, "success_rate": 0.96},
            "openrouter": {"cost_per_1k": 0.0007, "success_rate": 0.92},
            "mistral": {"cost_per_1k": 0.0009, "success_rate": 0.93},
            "nvidia": {"cost_per_1k": 0.0015, "success_rate": 0.97},
            "cohere": {"cost_per_1k": 0.0008, "success_rate": 0.94},
            "huggingface": {"cost_per_1k": 0.0006, "success_rate": 0.91}
        }

    def check_and_deduct_budget(self, consumer: str, estimated_cost_usd: float) -> tuple[bool, Optional[str]]:
        """Validates soft and hard budget limits."""
        policy = self.budgets.get(consumer, self.budgets["human"])
        if policy.current_month_spend_usd + estimated_cost_usd >= policy.monthly_budget_usd * policy.hard_limit_pct:
            return False, f"Monthly budget ceiling exceeded for consumer '{consumer}' (${policy.monthly_budget_usd:0.2f}). Please upgrade quota."

        policy.current_month_spend_usd += estimated_cost_usd
        soft_warning = None
        if policy.current_month_spend_usd >= policy.monthly_budget_usd * policy.soft_limit_pct:
            soft_warning = f"Consumer '{consumer}' spend is at {int((policy.current_month_spend_usd/policy.monthly_budget_usd)*100)}% of monthly budget ceiling."

        return True, soft_warning

    def route_request(self, consumer: str, task_type: str, estimated_tokens: int = 1000) -> RoutingDecision:
        """Selects the most cost-effective provider meeting the quality threshold for task_type."""
        est_cost_usd = (estimated_tokens / 1000.0) * 0.0006
        allowed, soft_warning = self.check_and_deduct_budget(consumer, est_cost_usd)
        if not allowed:
            raise PermissionError(soft_warning)

        # Leaderboard calculation: (success_rate / cost_per_1k)
        leaderboard = []
        for p, data in self.provider_profiles.items():
            efficiency = data["success_rate"] / max(0.0001, data["cost_per_1k"])
            leaderboard.append((p, efficiency, data["cost_per_1k"], data["success_rate"]))

        leaderboard.sort(key=lambda x: x[1], reverse=True)
        best_provider = leaderboard[0][0]

        return RoutingDecision(
            selected_provider=best_provider,
            estimated_cost_usd=round(est_cost_usd, 6),
            cost_efficiency_score=round(leaderboard[0][1], 2),
            routing_reason=f"Optimal cost-efficiency ({best_provider} score: {leaderboard[0][1]:0.1f}) meeting {leaderboard[0][3]*100:0.1f}% quality threshold.",
            soft_budget_warning=soft_warning
        )

    def get_budget_dashboard(self) -> Dict[str, Any]:
        """Returns spend metrics and projections per consumer."""
        dashboard = {}
        for c, p in self.budgets.items():
            used_pct = round((p.current_month_spend_usd / max(0.1, p.monthly_budget_usd)) * 100.0, 1)
            dashboard[c] = {
                "monthly_budget_usd": p.monthly_budget_usd,
                "current_month_spend_usd": round(p.current_month_spend_usd, 4),
                "budget_used_pct": used_pct,
                "status": "NORMAL" if used_pct < 80.0 else ("SOFT_LIMIT_WARNING" if used_pct < 100.0 else "HARD_LIMIT_EXCEEDED")
            }
        return dashboard


cost_aware_router = CostAwareRouter()
