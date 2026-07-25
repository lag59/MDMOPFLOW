from fastapi import APIRouter
from app.core.config import settings
from app.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    operation_id="health_get",
    summary="Health check",
    description="Returns service health status and runtime environment.",
    responses={200: {"description": "Service is reachable."}},
)
async def health():
    return {"status": "ok", "service": "mdm-opsflow-backend", "environment": settings.ENVIRONMENT}
