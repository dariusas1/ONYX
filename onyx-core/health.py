from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Dict, Any, Optional
import time
import asyncio
import os
import psutil
import sys
from datetime import datetime
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY
from prometheus_client.exposition import generate_latest

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    response_time: str
    version: str
    environment: str
    service: str
    uptime: float
    services: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Any]
    checks: Dict[str, int]
    endpoints: Dict[str, str]


class ServiceHealth(BaseModel):
    status: str
    error: Optional[str] = None
    response_time: str


class SystemMetrics(BaseModel):
    uptime: float
    uptime_formatted: str
    memory: Dict[str, Any]
    cpu: Dict[str, Any]
    disk: Dict[str, Any]
    python_version: str
    platform: str
    process_info: Dict[str, Any]


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


def get_system_metrics() -> SystemMetrics:
    """Get comprehensive system metrics"""
    try:
        # Process information
        process = psutil.Process()
        uptime_seconds = time.time() - process.create_time()

        # Memory metrics
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()

        # CPU metrics
        cpu_percent = process.cpu_percent(interval=0.1)

        # Disk metrics
        disk_usage = psutil.disk_usage('/')

        # System-wide metrics
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=0.1)

        # Format values
        def format_bytes(bytes_value):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_value < 1024.0:
                    return f"{bytes_value:.2f} {unit}"
                bytes_value /= 1024.0
            return f"{bytes_value:.2f} PB"

        def format_uptime(seconds):
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)

            parts = []
            if days > 0: parts.append(f"{days}d")
            if hours > 0: parts.append(f"{hours}h")
            if minutes > 0: parts.append(f"{minutes}m")
            parts.append(f"{secs}s")

            return " ".join(parts)

        return SystemMetrics(
            uptime=uptime_seconds,
            uptime_formatted=format_uptime(uptime_seconds),
            memory={
                "rss": format_bytes(memory_info.rss),
                "vms": format_bytes(memory_info.vms),
                "shared": format_bytes(memory_info.shared),
                "text": format_bytes(memory_info.text),
                "lib": format_bytes(memory_info.lib),
                "data": format_bytes(memory_info.data),
                "dirty": format_bytes(memory_info.dirty),
                "percent": round(memory_percent, 2),
                "system_total": format_bytes(system_memory.total),
                "system_available": format_bytes(system_memory.available),
                "system_percent": round(system_memory.percent, 2)
            },
            cpu={
                "process_percent": round(cpu_percent, 2),
                "system_percent": round(system_cpu, 2),
                "core_count": psutil.cpu_count(),
                "current_freq": psutil.cpu_freq().current if psutil.cpu_freq() else None
            },
            disk={
                "total": format_bytes(disk_usage.total),
                "used": format_bytes(disk_usage.used),
                "free": format_bytes(disk_usage.free),
                "percent": round((disk_usage.used / disk_usage.total) * 100, 2)
            },
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            platform=sys.platform,
            process_info={
                "pid": process.pid,
                "ppid": process.ppid(),
                "name": process.name(),
                "status": process.status(),
                "threads": process.num_threads(),
                "files": process.num_fds(),
                "connections": len(process.connections())
            }
        )

    except Exception as e:
        # Fallback metrics if psutil fails
        return SystemMetrics(
            uptime=time.time() - time.time(),  # Will be 0, but at least won't crash
            uptime_formatted="0s",
            memory={"error": f"Failed to get memory metrics: {str(e)}"},
            cpu={"error": f"Failed to get CPU metrics: {str(e)}"},
            disk={"error": f"Failed to get disk metrics: {str(e)}"},
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            platform=sys.platform,
            process_info={"error": f"Failed to get process metrics: {str(e)}"}
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check endpoint with enhanced metrics"""
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

        # Get system metrics
        system_metrics = get_system_metrics()

        # Determine overall health
        overall_healthy = all(
            service.status == "healthy" for service in services.values()
        )

        total_response_time = (time.time() - start_time) * 1000

        # Build enhanced response
        response = HealthResponse(
            status="healthy" if overall_healthy else "unhealthy",
            timestamp=datetime.utcnow().isoformat() + "Z",
            response_time=f"{total_response_time:.2f}ms",
            version=os.getenv("APP_VERSION", "1.0.0"),
            environment=os.getenv("PYTHON_ENV", "development"),
            service=os.getenv("SERVICE_NAME", "onyx-core"),
            uptime=system_metrics.uptime,
            services=services,
            metrics=system_metrics.dict(),
            checks={
                "total": len(services),
                "healthy": len([s for s in services.values() if s.status == "healthy"]),
                "unhealthy": len([s for s in services.values() if s.status == "unhealthy"])
            },
            endpoints={
                "health": "/health",
                "health_ready": "/health/ready",
                "health_live": "/health/live",
                "metrics": "/metrics"
            }
        )

        # Add additional metadata
        if os.getenv("GIT_COMMIT"):
            response.metrics["git_commit"] = os.getenv("GIT_COMMIT")

        if os.getenv("BUILD_DATE"):
            response.metrics["build_date"] = os.getenv("BUILD_DATE")

        # Log health check results
        try:
            from logger import get_logger
            logger = get_logger()

            logger.info("health_check_completed", {
                "status": response.status,
                "total_dependencies": response.checks["total"],
                "healthy_dependencies": response.checks["healthy"],
                "response_time_ms": total_response_time,
                "uptime_seconds": system_metrics.uptime,
                "memory_percent": system_metrics.memory.get("percent", 0),
                "cpu_percent": system_metrics.cpu.get("process_percent", 0)
            })
        except ImportError:
            # Logger not available, skip logging
            pass

        return response

    except Exception as e:
        # Log health check failure
        try:
            from logger import get_logger
            logger = get_logger()
            logger.error("health_check_failed", {
                "error": str(e),
                "traceback": str(e.__traceback__) if e.__traceback__ else None
            }, str(e))
        except ImportError:
            pass

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


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Import metrics module here to avoid circular imports
        from metrics import get_metrics_collector

        # Get the ONYX registry
        onyx_registry = get_metrics_collector().REGISTRY

        # Generate metrics in Prometheus format
        output = generate_latest(onyx_registry)

        return Response(
            content=output,
            media_type=CONTENT_TYPE_LATEST,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except ImportError:
        # Fallback if metrics module not available
        return Response(
            content="# Prometheus metrics not available\n",
            media_type=CONTENT_TYPE_LATEST,
            status=503
        )
    except Exception as e:
        logger.error("metrics_endpoint_failed", {
            "error": str(e),
            "type": type(e).__name__
        })

        return Response(
            content="# Metrics collection failed\n",
            media_type=CONTENT_TYPE_LATEST,
            status=500
        )
