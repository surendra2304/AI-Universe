"""FastAPI API routes for AI Universe."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.orchestrator import OrchestrationRequest, orchestrator


router = APIRouter()


class AskRequest(BaseModel):
    """Payload for submitting a question to AI Universe."""
    question: str = Field(description="The user or system inquiry to analyze and answer")
    mode: str = Field(default="auto", description="auto, fast, review, debate")
    max_agents: int = Field(default=5, ge=1, le=10)
    require_evidence: bool = Field(default=True)
    max_budget: Optional[float] = Field(default=None, description="Max budget in USD for this task")
    max_latency: Optional[float] = Field(default=None, description="Max desired latency in seconds")
    context_data: Dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    """Structured response for the /ask endpoint."""
    task_id: str
    run_id: str
    answer: str
    mode_used: str
    provider: str
    models_used: List[str]
    agents_used: List[str]
    confidence: float
    latency_seconds: float
    total_tokens: int
    unresolved_disagreements: List[str] = Field(default_factory=list)
    key_evidence: List[str] = Field(default_factory=list)


class DebateRequest(BaseModel):
    """Payload for explicitly requesting a multi-agent structured debate."""
    question: str = Field(description="The question or proposal to debate")
    max_agents: int = Field(default=5, ge=2, le=10)
    require_evidence: bool = Field(default=True)
    max_budget: Optional[float] = Field(default=None, description="Max budget in USD for this debate")
    max_latency: Optional[float] = Field(default=None, description="Max desired latency in seconds")
    context_data: Dict[str, Any] = Field(default_factory=dict)


class DebateResponse(BaseModel):
    """Structured response for the /debate endpoint."""
    task_id: str
    run_id: str
    answer: str
    mode_used: str = "debate"
    agents_used: List[str]
    models_used: List[str]
    confidence: float
    unresolved_disagreements: List[str] = Field(default_factory=list)
    key_evidence: List[str] = Field(default_factory=list)
    total_tokens: int = 0
    latency_seconds: float = 0.0


@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
async def ask_question(request: AskRequest) -> AskResponse:
    """Submit a question to the AI Universe orchestrator (auto-routes to Fast, Review, or Debate)."""
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    orch_request = OrchestrationRequest(
        question=request.question,
        mode=request.mode,
        max_agents=request.max_agents,
        require_evidence=request.require_evidence,
        max_budget=request.max_budget,
        max_latency=request.max_latency,
        context_data=request.context_data
    )

    try:
        result = await orchestrator.process_task(orch_request)
        return AskResponse(
            task_id=result.task_id,
            run_id=result.run_id,
            answer=result.answer,
            mode_used=result.mode_used,
            provider="gemini",
            models_used=result.models_used,
            agents_used=result.agents_used,
            confidence=result.confidence,
            latency_seconds=result.total_latency_seconds,
            total_tokens=result.total_tokens,
            unresolved_disagreements=result.unresolved_disagreements,
            key_evidence=result.key_evidence
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task orchestration failed: {str(exc)}"
        )


@router.post("/debate", response_model=DebateResponse, status_code=status.HTTP_200_OK)
async def trigger_debate(request: DebateRequest) -> DebateResponse:
    """Explicitly trigger the 6-Round Structured Multi-Agent Debate Engine."""
    if not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    orch_request = OrchestrationRequest(
        question=request.question,
        mode="debate",
        max_agents=request.max_agents,
        require_evidence=request.require_evidence,
        max_budget=request.max_budget,
        max_latency=request.max_latency,
        context_data=request.context_data
    )

    try:
        result = await orchestrator.process_task(orch_request)
        return DebateResponse(
            task_id=result.task_id,
            run_id=result.run_id,
            answer=result.answer,
            mode_used="debate",
            agents_used=result.agents_used,
            models_used=result.models_used,
            confidence=result.confidence,
            unresolved_disagreements=result.unresolved_disagreements,
            key_evidence=result.key_evidence,
            total_tokens=result.total_tokens,
            latency_seconds=result.total_latency_seconds
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debate orchestration failed: {str(exc)}"
        )


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Retrieve details and state of a task by ID."""
    status_data = await orchestrator.get_task_status(task_id)
    if not status_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found."
        )
    return status_data
