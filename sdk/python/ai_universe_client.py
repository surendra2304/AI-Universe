"""Python SDK Client for AI Universe Multi-Agent Intelligence Platform."""

import time
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field


class IntelligenceRequest(BaseModel):
    request_id: str
    task_type: str
    goal: str
    context: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    mode: str = "fast"


class AIUniverseClient:
    """Typed client for interacting with AI Universe intelligence endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.Client(base_url=self.base_url, headers=self.headers, timeout=timeout)

    def query_nexus_intelligence(self, request: IntelligenceRequest) -> Dict[str, Any]:
        """Queries Nexus decision intelligence endpoint."""
        resp = self.client.post("/v1/nexus/intelligence", json=request.model_dump())
        resp.raise_for_status()
        return resp.json()

    def generate_code(self, file_type: str, filename: str, context: Dict[str, Any], requirements: Optional[List[str]] = None) -> Dict[str, Any]:
        """Queries FORGE code generation endpoint."""
        payload = {
            "file_type": file_type,
            "filename": filename,
            "context": context,
            "requirements": requirements or []
        }
        resp = self.client.post("/v1/forge/generate-code", json=payload)
        resp.raise_for_status()
        return resp.json()

    def query_intelx_research(self, request_id: str, role: str, context: Dict[str, Any], evidence_with_spans: Optional[List[Dict[str, Any]]] = None, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Queries IntelX deep research intelligence endpoint."""
        payload = {
            "request_id": request_id,
            "role": role,
            "context": context,
            "evidence_with_spans": evidence_with_spans or [],
            "constraints": constraints or {}
        }
        resp = self.client.post("/v1/intelx/research", json=payload)
        resp.raise_for_status()
        return resp.json()

    def query_sentinel_analysis(self, request_id: str, analysis_type: str, target_context: Dict[str, Any], findings: Optional[List[Dict[str, Any]]] = None, threat_intel: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Queries Sentinel cybersecurity intelligence endpoint."""
        payload = {
            "request_id": request_id,
            "analysis_type": analysis_type,
            "target_context": target_context,
            "findings": findings or [],
            "threat_intel": threat_intel or {}
        }
        resp = self.client.post("/v1/sentinel/analyze", json=payload)
        resp.raise_for_status()
        return resp.json()

    def report_outcome(self, consumer: str, request_id: str, outcome: str, detail: Optional[str] = None, metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Reports downstream verification or execution outcome for self-optimization."""
        payload = {
            "consumer": consumer,
            "request_id": request_id,
            "outcome": outcome,
            "detail": detail or "",
            "measured_metrics": metrics or {}
        }
        resp = self.client.post("/v1/analytics/outcome", json=payload)
        resp.raise_for_status()
        return resp.json()
