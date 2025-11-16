"""
Prometheus Metrics Collection for ONYX Core

Implements Prometheus metrics for Python FastAPI service with <10ms response time target
Tracks HTTP requests, response times, error rates, and business metrics
"""

import time
import logging
from functools import wraps
from typing import Dict, Any, Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import base64

logger = logging.getLogger(__name__)

# Create a custom registry
REGISTRY = CollectorRegistry()

# HTTP Request Metrics
HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'Duration of HTTP requests in seconds',
    ['method', 'endpoint', 'status_code', 'service'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
    registry=REGISTRY
)

HTTP_REQUEST_TOTAL = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code', 'service'],
    registry=REGISTRY
)

HTTP_REQUEST_ACTIVE = Gauge(
    'http_requests_active',
    'Number of active HTTP requests',
    ['service'],
    registry=REGISTRY
)

# Business Metrics for ONYX
ONYX_CHAT_DURATION = Histogram(
    'onyx_chat_duration_seconds',
    'Duration of ONYX chat interactions',
    ['model', 'user_id', 'success'],
    buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 5.0, 10.0, 15.0],
    registry=REGISTRY
)

ONYX_RAG_RETRIEVAL_DURATION = Histogram(
    'onyx_rag_retrieval_duration_seconds',
    'Duration of RAG retrieval operations',
    ['vector_count', 'similarity_threshold'],
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
    registry=REGISTRY
)

ONYX_TASK_COMPLETION = Counter(
    'onyx_task_completion_total',
    'Total number of completed tasks',
    ['task_type', 'success', 'duration_category'],
    registry=REGISTRY
)

ONYX_ACTIVE_AGENTS = Gauge(
    'onyx_active_agents',
    'Number of active agents',
    ['agent_type', 'status'],
    registry=REGISTRY
)

ONYX_ACTIVE_CONNECTIONS = Gauge(
    'onyx_active_connections_total',
    'Total number of active connections',
    registry=REGISTRY
)

# RAG Quality Metrics
ONYX_RAG_RETRIEVAL_ACCURACY = Gauge(
    'onyx_rag_retrieval_accuracy_score',
    'RAG retrieval accuracy score (0-1)',
    registry=REGISTRY
)

ONYX_RAG_RETRIEVAL_RELEVANCE = Gauge(
    'onyx_rag_retrieval_relevance_score',
    'RAG retrieval relevance score (0-1)',
    registry=REGISTRY
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for Prometheus metrics collection"""

    def __init__(self, app, service_name: str = "onyx-core"):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # Increment active requests
        HTTP_REQUEST_ACTIVE.labels(service=self.service_name).inc()

        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Extract endpoint (fallback to URL path)
            endpoint = getattr(request.state, 'endpoint',
                              request.url.path.replace('/api/v1', '') if '/api/v1' in request.url.path
                              else request.url.path)

            # Record metrics
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=str(response.status_code),
                service=self.service_name
            ).observe(duration)

            HTTP_REQUEST_TOTAL.labels(
                method=request.method,
                endpoint=endpoint,
                status_code=str(response.status_code),
                service=self.service_name
            ).inc()

            return response

        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time

            # Record error metrics
            endpoint = getattr(request.state, 'endpoint', request.url.path)

            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                endpoint=endpoint,
                status_code='500',
                service=self.service_name
            ).observe(duration)

            HTTP_REQUEST_TOTAL.labels(
                method=request.method,
                endpoint=endpoint,
                status_code='500',
                service=self.service_name
            ).inc()

            raise

        finally:
            # Decrement active requests
            HTTP_REQUEST_ACTIVE.labels(service=self.service_name).dec()


def basic_auth_required(func):
    """Decorator for basic authentication on metrics endpoints"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Try to extract request from args/kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if not request:
            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                    break

        if not request:
            raise HTTPException(status_code=500, detail="Could not extract request")

        # Check Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            raise HTTPException(status_code=401, detail="Missing authentication")

        try:
            # Decode credentials
            auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = auth_decoded.split(':', 1)

            # Validate credentials
            valid_username = "admin"  # TODO: Use environment variables
            valid_password = "admin"  # TODO: Use environment variables

            if username != valid_username or password != valid_password:
                raise HTTPException(status_code=401, detail="Invalid credentials")

        except Exception:
            raise HTTPException(status_code=401, detail="Invalid authentication")

        return await func(*args, **kwargs)

    return wrapper


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics endpoint with <10ms response time target"""

    start_time = time.perf_counter()

    try:
        # Generate metrics
        metrics_data = generate_latest(REGISTRY)

        # Calculate response time
        duration_ms = (time.perf_counter() - start_time) * 1000

        if duration_ms > 10:
            logger.warning(f"Metrics endpoint took {duration_ms:.2f}ms (>10ms target)")

        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        raise HTTPException(status_code=500, detail="Error generating metrics")


# Business metric helper functions
def record_chat_duration(model: str, user_id: str, success: bool, duration: float):
    """Record chat interaction duration"""
    ONYX_CHAT_DURATION.labels(
        model=model,
        user_id=user_id,
        success='true' if success else 'false'
    ).observe(duration)


def record_rag_retrieval(vector_count: int, similarity_threshold: float, duration: float):
    """Record RAG retrieval duration"""
    ONYX_RAG_RETRIEVAL_DURATION.labels(
        vector_count=str(vector_count),
        similarity_threshold=str(similarity_threshold)
    ).observe(duration)


def record_task_completion(task_type: str, success: bool, duration: float):
    """Record task completion"""
    if duration < 1:
        duration_category = 'fast'
    elif duration < 5:
        duration_category = 'medium'
    else:
        duration_category = 'slow'

    ONYX_TASK_COMPLETION.labels(
        task_type=task_type,
        success='true' if success else 'false',
        duration_category=duration_category
    ).inc()


def set_active_agents(agent_type: str, status: str, count: int):
    """Set active agents count"""
    ONYX_ACTIVE_AGENTS.labels(
        agent_type=agent_type,
        status=status
    ).set(count)


def set_active_connections(count: int):
    """Set active connections count"""
    ONYX_ACTIVE_CONNECTIONS.set(count)


def set_rag_quality(accuracy: float, relevance: float):
    """Set RAG quality scores"""
    ONYX_RAG_RETRIEVAL_ACCURACY.set(accuracy)
    ONYX_RAG_RETRIEVAL_RELEVANCE.set(relevance)


# Export metrics for advanced usage
__all__ = [
    'PrometheusMiddleware',
    'metrics_endpoint',
    'basic_auth_required',
    'record_chat_duration',
    'record_rag_retrieval',
    'record_task_completion',
    'set_active_agents',
    'set_active_connections',
    'set_rag_quality',
    'REGISTRY',
    'HTTP_REQUEST_DURATION',
    'HTTP_REQUEST_TOTAL',
    'HTTP_REQUEST_ACTIVE',
    'ONYX_CHAT_DURATION',
    'ONYX_RAG_RETRIEVAL_DURATION',
    'ONYX_TASK_COMPLETION',
    'ONYX_ACTIVE_AGENTS',
    'ONYX_ACTIVE_CONNECTIONS',
    'ONYX_RAG_RETRIEVAL_ACCURACY',
    'ONYX_RAG_RETRIEVAL_RELEVANCE'
]