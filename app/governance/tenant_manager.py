"""Multi-Tenant Isolation, API Governance, Row-Level Tenant Security, and Deduplication."""

import hashlib
import time
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.utils.logger import logger


class TenantPolicy(BaseModel):
    tenant_id: str
    name: str
    rate_limit_per_hour: int = 500
    daily_budget_usd: float = 25.0
    current_daily_spend_usd: float = 0.0
    hard_cutoff_enabled: bool = True
    active_keys: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)


class MultiTenantManager:
    """Manages tenant isolation, API key rotation, budget cutoffs, and request deduplication."""

    def __init__(self) -> None:
        self.tenants: Dict[str, TenantPolicy] = {
            "tenant_trading": TenantPolicy(
                tenant_id="tenant_trading",
                name="Algorithmic Trading Bot",
                rate_limit_per_hour=100,
                daily_budget_usd=15.0,
                active_keys=["key_trading_live_01", "key_trading_test_02"]
            ),
            "tenant_forge": TenantPolicy(
                tenant_id="tenant_forge",
                name="FORGE Code Engine",
                rate_limit_per_hour=1000,
                daily_budget_usd=50.0,
                active_keys=["key_forge_prod_01"]
            ),
            "tenant_nexus": TenantPolicy(
                tenant_id="tenant_nexus",
                name="Nexus Decision Subsystem",
                rate_limit_per_hour=500,
                daily_budget_usd=25.0,
                active_keys=["key_nexus_prod_01"]
            ),
            "tenant_sentinel": TenantPolicy(
                tenant_id="tenant_sentinel",
                name="Sentinel Security Engine",
                rate_limit_per_hour=100,
                daily_budget_usd=30.0,
                active_keys=["key_sentinel_prod_01"]
            ),
            "tenant_intelx": TenantPolicy(
                tenant_id="tenant_intelx",
                name="IntelX Research Engine",
                rate_limit_per_hour=200,
                daily_budget_usd=35.0,
                active_keys=["key_intelx_prod_01"]
            ),
            "tenant_default": TenantPolicy(
                tenant_id="tenant_default",
                name="Default Sandbox Tenant",
                rate_limit_per_hour=200,
                daily_budget_usd=10.0,
                active_keys=["key_default_sandbox"]
            )
        }
        # In-memory deduplication cache: hash -> (response_payload, expiry_timestamp)
        self.dedup_cache: Dict[str, Dict[str, Any]] = {}
        self.dedup_ttl_seconds = 300.0  # 5 minutes idempotency window

    def extract_tenant_id(self, auth_header: Optional[str], api_key: Optional[str]) -> str:
        token = (api_key or auth_header or "").strip()
        for t_id, policy in self.tenants.items():
            if any(k in token for k in policy.active_keys) or t_id in token.lower():
                return t_id
        if "forge" in token.lower():
            return "tenant_forge"
        elif "trading" in token.lower() or "bot" in token.lower():
            return "tenant_trading"
        elif "nexus" in token.lower():
            return "tenant_nexus"
        elif "sentinel" in token.lower():
            return "tenant_sentinel"
        elif "intelx" in token.lower():
            return "tenant_intelx"
        return "tenant_default"

    def check_tenant_budget(self, tenant_id: str, estimated_cost_usd: float = 0.001) -> bool:
        """Enforces hard budget cutoff."""
        policy = self.tenants.get(tenant_id, self.tenants["tenant_default"])
        if policy.hard_cutoff_enabled:
            if (policy.current_daily_spend_usd + estimated_cost_usd) > policy.daily_budget_usd:
                logger.error("[TENANT HARD CUTOFF] Tenant '%s' exceeded daily budget ($%0.2f).", tenant_id, policy.daily_budget_usd)
                return False
        policy.current_daily_spend_usd += estimated_cost_usd
        return True

    def rotate_tenant_key(self, tenant_id: str, old_key: str) -> str:
        """Rotates a tenant API key securely."""
        policy = self.tenants.get(tenant_id)
        if not policy:
            raise ValueError(f"Tenant '{tenant_id}' not found.")
        new_key = f"key_{tenant_id}_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]}"
        if old_key in policy.active_keys:
            policy.active_keys.remove(old_key)
        policy.active_keys.append(new_key)
        return new_key

    def check_deduplication(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Returns cached response if request_id was processed in the last 5 minutes."""
        entry = self.dedup_cache.get(request_id)
        if entry:
            if time.time() < entry["expires_at"]:
                logger.info("[DEDUP HIT] Returning cached response for request_id: %s", request_id)
                return entry["response"]
            else:
                del self.dedup_cache[request_id]
        return None

    def store_deduplication(self, request_id: str, response_payload: Dict[str, Any]) -> None:
        self.dedup_cache[request_id] = {
            "response": response_payload,
            "expires_at": time.time() + self.dedup_ttl_seconds
        }


tenant_manager = MultiTenantManager()
