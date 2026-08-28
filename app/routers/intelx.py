"""FastAPI Router for IntelX Deep Research Intelligence Endpoints."""

from fastapi import APIRouter, HTTPException, Path, status
from app.services.intelx_intelligence import (
    IntelXResearchRequest,
    IntelXResearchResponse,
    intelx_intelligence_service,
)

intelx_router = APIRouter(prefix="/v1/intelx", tags=["IntelX Deep Research Intelligence"])


@intelx_router.post("/research", response_model=IntelXResearchResponse, status_code=status.HTTP_200_OK)
async def process_intelx_research_role(request: IntelXResearchRequest):
    """Processes role-specific research requests for IntelX (planner, extractor, verifier, analyst, critic, synthesizer)."""
    return await intelx_intelligence_service.execute_research_role(request)


@intelx_router.get("/research/{request_id}", status_code=status.HTTP_200_OK)
async def get_intelx_research_record(request_id: str = Path(..., description="Unique ID of previous IntelX research request")):
    """Retrieves full request and response record with provenance for research audit and verification."""
    record = intelx_intelligence_service.get_provenance(request_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research record for request_id '{request_id}' not found in provenance ledger."
        )
    return record
