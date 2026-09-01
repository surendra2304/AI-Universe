"""FastAPI Router for Nexus Intelligence Endpoints."""

from fastapi import APIRouter, HTTPException, Path, status

from app.services.nexus_intelligence import (
    IntelligenceRequest,
    IntelligenceResponse,
    nexus_intelligence_service,
)

nexus_router = APIRouter(prefix="/v1/nexus", tags=["Nexus Intelligence"])


@nexus_router.post("/intelligence", response_model=IntelligenceResponse, status_code=status.HTTP_200_OK)
async def process_nexus_intelligence(request: IntelligenceRequest):
    """Processes structured multi-mode intelligence requests with calibrated confidence and full provenance."""
    return await nexus_intelligence_service.process_request(request)


@nexus_router.get("/intelligence/{request_id}", status_code=status.HTTP_200_OK)
async def get_nexus_intelligence_record(request_id: str = Path(..., description="Unique ID of previous intelligence request")):
    """Retrieves full request and response record with complete provenance for audit and explanation."""
    record = nexus_intelligence_service.get_provenance(request_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intelligence record for request_id '{request_id}' not found in provenance ledger."
        )
    return record
