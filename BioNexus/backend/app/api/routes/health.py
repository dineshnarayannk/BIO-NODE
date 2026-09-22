from fastapi import APIRouter
from ...schemas.health import HealthResponse
from ...db.session import check_db_connectivity

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Health check endpoint confirming API status and TiDB database connectivity."""
    db_status, detail = check_db_connectivity()

    overall_status = "ok" if db_status in ("connected", "unconfigured") else "degraded"

    return HealthResponse(
        status=overall_status,
        service="BioNexus API",
        database=db_status,
        detail=detail if overall_status == "degraded" else None,
    )
