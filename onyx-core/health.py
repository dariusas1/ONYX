from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import time
import asyncio
import os
from datetime import datetime

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    response_time: str
    version: str
    environment: str
    services: Dict[str, Dict[str, Any]]
    uptime: float


class ServiceHealth(BaseModel):
    status: str
    error: Optional[str] = None
    response_time: str


async def check_database_health() -> ServiceHealth:
    """Check PostgreSQL database connection"""
    start_time = time.time()
    try:
        # This would be implemented with actual database connection
        # For now, simulate healthy connection
        await asyncio.sleep(0.01)  # Simulate connection time
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(status="healthy", response_time=f"{response_time:.2f}ms")
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(
            status="unhealthy", error=str(e), response_time=f"{response_time:.2f}ms"
        )


async def check_qdrant_health() -> ServiceHealth:
    """Check Qdrant vector database connection"""
    start_time = time.time()
    try:
        from rag_service import get_rag_service

        rag_service = await get_rag_service()
        health_info = await rag_service.health_check()

        response_time = (time.time() - start_time) * 1000
        if health_info["status"] == "healthy":
            return ServiceHealth(
                status="healthy", response_time=f"{response_time:.2f}ms"
            )
        else:
            return ServiceHealth(
                status="unhealthy",
                error=health_info.get("error", "Unknown error"),
                response_time=f"{response_time:.2f}ms",
            )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(
            status="unhealthy", error=str(e), response_time=f"{response_time:.2f}ms"
        )


async def check_redis_health() -> ServiceHealth:
    """Check Redis connection"""
    start_time = time.time()
    try:
        # This would be implemented with actual Redis client
        # For now, simulate healthy connection
        await asyncio.sleep(0.005)  # Simulate connection time
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(status="healthy", response_time=f"{response_time:.2f}ms")
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(
            status="unhealthy", error=str(e), response_time=f"{response_time:.2f}ms"
        )


async def check_google_api_health() -> ServiceHealth:
    """Check Google API connectivity"""
    start_time = time.time()
    try:
        # This would be implemented with actual Google API client
        # For now, simulate healthy connection
        await asyncio.sleep(0.05)  # Simulate API call time
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(status="healthy", response_time=f"{response_time:.2f}ms")
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealth(
            status="unhealthy", error=str(e), response_time=f"{response_time:.2f}ms"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint"""
    start_time = time.time()

    try:
        # Run all health checks concurrently
        db_health, qdrant_health, redis_health, google_health = await asyncio.gather(
            check_database_health(),
            check_qdrant_health(),
            check_redis_health(),
            check_google_api_health(),
            return_exceptions=True,
        )

        # Handle exceptions in health checks
        services = {}

        if isinstance(db_health, Exception):
            services["database"] = ServiceHealth(
                status="unhealthy", error=str(db_health), response_time="0ms"
            )
        else:
            services["database"] = db_health

        if isinstance(qdrant_health, Exception):
            services["qdrant"] = ServiceHealth(
                status="unhealthy", error=str(qdrant_health), response_time="0ms"
            )
        else:
            services["qdrant"] = qdrant_health

        if isinstance(redis_health, Exception):
            services["redis"] = ServiceHealth(
                status="unhealthy", error=str(redis_health), response_time="0ms"
            )
        else:
            services["redis"] = redis_health

        if isinstance(google_health, Exception):
            services["google_api"] = ServiceHealth(
                status="unhealthy", error=str(google_health), response_time="0ms"
            )
        else:
            services["google_api"] = google_health

        # Determine overall health
        overall_healthy = all(
            service.status == "healthy" for service in services.values()
        )

        total_response_time = (time.time() - start_time) * 1000

        response = HealthResponse(
            status="healthy" if overall_healthy else "unhealthy",
            timestamp=datetime.utcnow().isoformat() + "Z",
            response_time=f"{total_response_time:.2f}ms",
            version=os.getenv("APP_VERSION", "1.0.0"),
            environment=os.getenv("PYTHON_ENV", "development"),
            services=services,
            uptime=time.time(),
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "error": str(e),
            },
        )


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes/Docker"""
    # Simple readiness check - service is ready if it can respond
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes/Docker"""
    # Simple liveness check - service is alive if it can respond
    return {"status": "alive"}
