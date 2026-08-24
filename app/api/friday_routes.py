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
    """Payload for requests submitted by FRIDAY to AI Universe."""
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
                "platform": "AI Universe",
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
            mode_used="debate",
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
                "platform": "AI Universe",
                "version": "1.0.0",
                "rounds_completed": 6
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"FRIDAY debate orchestration failed: {str(exc)}"
        )
