"""Dedicated API routes and typed contracts for FRIDAY integration."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.orchestrator import OrchestrationRequest, orchestrator
from app.core.security import verify_friday_api_key

friday_router = APIRouter(
    prefix="/v1/friday",
    tags=["FRIDAY Integration"],
    dependencies=[Depends(verify_friday_api_key)]
)


class FridayRequest(BaseModel):
    """Payload for requests submitted by FRIDAY to Inference."""
    question: str = Field(description="The complex query or task submitted by FRIDAY")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="FRIDAY's active system/environment context")
    max_latency: Optional[float] = Field(default=30.0, description="Hard SLA ceiling in seconds")
    max_budget: Optional[float] = Field(default=None, description="Max cost in USD")
    require_evidence: bool = Field(default=True, description="Enforce fact-checking and evidence provenance")
    caller_id: str = Field(default="friday_core", description="Identifier of the FRIDAY caller sub-module")


class FridayResponse(BaseModel):
    """Structured response returned to FRIDAY with full provenance and dissent metadata."""
    task_id: str
    run_id: str
    answer: str
    mode_used: str
    confidence: float = Field(ge=0.0, le=1.0)
    unresolved_disagreements: List[str] = Field(default_factory=list, description="Surviving technical dissent for FRIDAY decision-making")
    key_evidence: List[str] = Field(default_factory=list, description="Verified empirical claims and evidence")
    agents_used: List[str]
    models_used: List[str]
    latency_seconds: float
    total_tokens: int
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Audit trail and deliberation lineage")


@friday_router.post("/ask", response_model=FridayResponse, status_code=status.HTTP_200_OK)
async def friday_ask(request: FridayRequest) -> FridayResponse:
    """
    FRIDAY Fast/Review Question Answering Gateway.
    Automatically assigns optimal specialist or panel according to FRIDAY SLA constraints.
    """
    if not request.question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty.")

    orch_req = OrchestrationRequest(
        question=request.question,
        mode="auto",
        max_latency=request.max_latency,
        max_budget=request.max_budget,
        require_evidence=request.require_evidence,
        context_data={"caller_id": request.caller_id, **request.context_data}
    )

    try:
        result = await orchestrator.process_task(orch_req)
        return FridayResponse(
            task_id=result.task_id,
            run_id=result.run_id,
            answer=result.answer,
            mode_used=result.mode_used,
            confidence=result.confidence,
            unresolved_disagreements=result.unresolved_disagreements,
            key_evidence=result.key_evidence,
            agents_used=result.agents_used,
            models_used=result.models_used,
            latency_seconds=result.total_latency_seconds,
            total_tokens=result.total_tokens,
            provenance={
                "caller_id": request.caller_id,
                "platform": "Inference",
                "version": "1.0.0"
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FRIDAY task orchestration failed: {str(exc)}"
        )


@friday_router.post("/debate", response_model=FridayResponse, status_code=status.HTTP_200_OK)
async def friday_debate(request: FridayRequest) -> FridayResponse:
    """
    FRIDAY 6-Round Structured Multi-Agent Debate Gateway.
    Executes deep adversarial reasoning, returning calibrated confidence, surviving claims, and active dissent.
    """
    if not request.question.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty.")

    orch_req = OrchestrationRequest(
        question=request.question,
        mode="debate",
        max_latency=request.max_latency,
        max_budget=request.max_budget,
        require_evidence=request.require_evidence,
        context_data={"caller_id": request.caller_id, **request.context_data}
    )

    try:
        result = await orchestrator.process_task(orch_req)
        return FridayResponse(
            task_id=result.task_id,
            run_id=result.run_id,
            answer=result.answer,
            mode_used=result.mode_used,
            confidence=result.confidence,
            unresolved_disagreements=result.unresolved_disagreements,
            key_evidence=result.key_evidence,
            agents_used=result.agents_used,
            models_used=result.models_used,
            latency_seconds=result.total_latency_seconds,
            total_tokens=result.total_tokens,
            provenance={
                "caller_id": request.caller_id,
                "debate_id": result.run_id,
                "platform": "Inference",
                "version": "1.0.0",
                "mode_used": result.mode_used,
                "rounds_completed": 6 if result.mode_used == "debate" else 2
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FRIDAY debate orchestration failed: {str(exc)}"
        )


class AgentMetadata(BaseModel):
    """Detailed metadata for a specialist agent in Inference."""
    id: str
    name: str
    role: str
    purpose: str
    provider: str
    model: str
    strengths: List[str] = Field(default_factory=list)
    status: str = "active"


class FridayInfoResponse(BaseModel):
    """System metadata and active agent list for discovery."""
    platform: str = "Inference"
    version: str = "1.0.0"
    total_specialists: int
    active_cloud_providers: List[str]
    agents: List[AgentMetadata]


@friday_router.get("/agents", response_model=List[AgentMetadata], status_code=status.HTTP_200_OK)
async def list_friday_agents() -> List[AgentMetadata]:
    """
    Returns the live catalog of all 10 specialist agents, their cloud providers, and assigned models.
    Enables FRIDAY to query exact agent models without hallucination.
    """
    agents = orchestrator.registry.list_agents()
    return [
        AgentMetadata(
            id=a.id,
            name=a.name,
            role=a.role,
            purpose=a.purpose,
            provider=a.model_provider,
            model=a.model_name,
            strengths=a.strengths,
            status=a.status
        )
        for a in agents
    ]


@friday_router.get("/info", response_model=FridayInfoResponse, status_code=status.HTTP_200_OK)
async def get_friday_info() -> FridayInfoResponse:
    """
    Returns system status, active cloud providers, and specialist agent models.
    """
    agents = orchestrator.registry.list_agents()
    agent_metas = [
        AgentMetadata(
            id=a.id,
            name=a.name,
            role=a.role,
            purpose=a.purpose,
            provider=a.model_provider,
            model=a.model_name,
            strengths=a.strengths,
            status=a.status
        )
        for a in agents
    ]
    unique_providers = list({a.model_provider for a in agents})
    return FridayInfoResponse(
        total_specialists=len(agents),
        active_cloud_providers=unique_providers,
        agents=agent_metas
    )


class FridayStatusResponse(BaseModel):
    """Administrative status response returning live active agents, configured providers, and available models."""
    active_agents: List[str] = Field(description="List of active agent roles currently registered")
    configured_providers: List[str] = Field(description="List of provider names with valid API keys loaded from .env")
    available_models: List[str] = Field(description="List of specific model names mapped to active agents and providers")


@friday_router.get("/status", response_model=FridayStatusResponse, status_code=status.HTTP_200_OK)
async def get_friday_status() -> FridayStatusResponse:
    """
    Administrative status endpoint for FRIDAY.
    Returns:
    - active_agents: list of unique agent roles currently registered.
    - configured_providers: list of provider names with valid API keys loaded in .env.
    - available_models: list of specific model names mapped to those providers.
    """
    from app.core.config import settings

    # Check configured providers from .env settings (supports single or comma-separated lists)
    provider_names = ["Gemini", "Groq", "Mistral", "OpenRouter", "Cohere", "HuggingFace", "Nvidia"]
    configured_providers = [
        p for p in provider_names
        if len(settings.get_provider_keys(p)) > 0
    ]

    # Retrieve registered agents and their assigned models
    agents = orchestrator.registry.list_agents()
    active_agent_roles = [a.role for a in agents]
    available_models = list(dict.fromkeys([a.model_name for a in agents]))

    return FridayStatusResponse(
        active_agents=active_agent_roles,
        configured_providers=configured_providers,
        available_models=available_models
    )
