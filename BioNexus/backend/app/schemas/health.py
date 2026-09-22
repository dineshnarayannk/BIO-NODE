from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response payload reporting service and database connectivity."""

    status: str = Field(default="ok", description="Overall health status ('ok' or 'degraded')")
    service: str = Field(default="BioNexus API", description="Service name")
    database: str = Field(
        default="connected",
        description="Database status ('connected', 'disconnected', or 'unconfigured')",
    )
    detail: Optional[str] = Field(
        default=None,
        description="Additional sanitized status detail when degraded",
    )
