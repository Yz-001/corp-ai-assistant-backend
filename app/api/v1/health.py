"""Health check API endpoints."""

from fastapi import APIRouter
from sqlalchemy import select
from app.core.database import engine
from app.core.redis import redis_client
from app.schemas import BaseResponse

router = APIRouter()


@router.get("/health", response_model=dict)
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/health/db", response_model=BaseResponse[dict])
async def db_health_check():
    """Database health check."""
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        return BaseResponse(data={"status": "healthy", "message": "Database connection OK"})
    except Exception as e:
        return BaseResponse(
            code=5001,
            message=f"Database connection failed: {str(e)}",
            data={"status": "unhealthy"}
        )


@router.get("/health/redis", response_model=BaseResponse[dict])
async def redis_health_check():
    """Redis health check."""
    try:
        await redis_client.ping()
        return BaseResponse(data={"status": "healthy", "message": "Redis connection OK"})
    except Exception as e:
        return BaseResponse(
            code=5002,
            message=f"Redis connection failed: {str(e)}",
            data={"status": "unhealthy"}
        )


@router.get("/health/all", response_model=BaseResponse[dict])
async def all_health_check():
    """All services health check."""
    results = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
    }
    
    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        results["database"] = "healthy"
    except Exception as e:
        results["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        await redis_client.ping()
        results["redis"] = "healthy"
    except Exception as e:
        results["redis"] = f"unhealthy: {str(e)}"
    
    all_healthy = all(v == "healthy" for v in results.values())
    
    return BaseResponse(
        data=results,
        message="All services healthy" if all_healthy else "Some services unhealthy"
    )