"""FastAPI Router for Core FORGE Intelligence Services (Generate, Plan, Review, Debug, Tests)."""

from fastapi import APIRouter, status

from app.services.architecture_planning import (
    ArchitecturePlanRequest,
    ArchitecturePlanResponse,
    architecture_planning_service,
)
from app.services.code_generation import (
    CodeGenerationRequest,
    CodeGenerationResponse,
    code_generation_service,
)
from app.services.code_review import (
    CodeReviewRequest,
    CodeReviewResponse,
    code_review_service,
)
from app.services.debugging import (
    DebugRequest,
    DebugResponse,
    debugging_service,
)
from app.services.test_generation import (
    TestGenerationRequest,
    TestGenerationResponse,
    test_generation_service,
)

forge_router = APIRouter(prefix="/v1/forge", tags=["FORGE Intelligence Services"])


@forge_router.post("/generate-code", response_model=CodeGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_code_endpoint(req: CodeGenerationRequest):
    """Generates production-quality code for a specific file based on architectural constraints."""
    return await code_generation_service.generate_code(req)


@forge_router.post("/plan-architecture", response_model=ArchitecturePlanResponse, status_code=status.HTTP_200_OK)
async def plan_architecture_endpoint(req: ArchitecturePlanRequest):
    """Deconstructs goals into architecture specs, component manifests, and tech stacks."""
    return await architecture_planning_service.plan_architecture(req)


@forge_router.post("/review-code", response_model=CodeReviewResponse, status_code=status.HTTP_200_OK)
async def review_code_endpoint(req: CodeReviewRequest):
    """Multi-agent code review debate covering correctness, security vulnerabilities, and complexity."""
    return await code_review_service.review_code(req)


@forge_router.post("/debug", response_model=DebugResponse, status_code=status.HTTP_200_OK)
async def debug_endpoint(req: DebugRequest):
    """Diagnoses runtime errors and produces surgical patch fixes."""
    return await debugging_service.diagnose_and_fix(req)


@forge_router.post("/generate-tests", response_model=TestGenerationResponse, status_code=status.HTTP_200_OK)
async def generate_tests_endpoint(req: TestGenerationRequest):
    """Generates automated test suites (pytest/jest/playwright) covering happy paths and edge cases."""
    return await test_generation_service.generate_tests(req)
