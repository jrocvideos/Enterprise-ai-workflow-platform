"""Health and metrics endpoints."""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.config import get_settings
from app.integrations.db_client import get_db, MongoDBClient
from app.integrations.redis_client import get_redis, RedisClient
from app.integrations.llm_client import get_llm_client

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    services: dict
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health status."""
    settings = get_settings()
    
    # Check DB
    db_client = MongoDBClient()
    db_healthy = await db_client.health_check()
    
    # Check Redis
    redis_client = await get_redis()
    redis_healthy = await redis_client.health_check()
    
    # Determine overall status
    all_healthy = db_healthy and redis_healthy
    status = "healthy" if all_healthy else "degraded"
    
    return HealthResponse(
        status=status,
        services={
            "database": db_healthy,
            "redis": redis_healthy,
            "api": True
        },
        version=settings.app_name
    )


@router.get("/metrics")
async def metrics():
    """Prometheus-style metrics placeholder."""
    # In production, use prometheus_client
    return {
        "requests_total": 0,
        "requests_duration_seconds": 0,
        "llm_requests_total": 0,
        "tickets_created_total": 0
    }