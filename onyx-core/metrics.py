"""
ONYX Prometheus Metrics for Core Service

Provides Prometheus metrics collection and exposure for the ONYX core service.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, CONTENT_TYPE_LATEST
from prometheus_client.core import REGISTRY
from prometheus_client.exposition import generate_latest
from fastapi import APIRouter, Response
from typing import Dict, Any
import time
import asyncio
import os
import logging
from contextlib import asynccontextmanager
import threading

# Get logger
try:
    from logger import get_logger
    logger = get_logger()
except ImportError:
    logger = logging.getLogger(__name__)

# Create metrics router
router = APIRouter()

# Custom registry for ONYX metrics
REGISTRY = CollectorRegistry()

# HTTP request metrics
HTTP_REQUESTS_TOTAL = Counter(
    'onyx_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

HTTP_REQUEST_DURATION = Histogram(
    'onyx_http_request_duration_seconds',
    'Duration of HTTP requests in seconds',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY
)

HTTP_REQUESTS_ACTIVE = Gauge(
    'onyx_http_requests_active',
    'Number of active HTTP requests',
    registry=REGISTRY
)

# System metrics
SYSTEM_UPTIME = Gauge(
    'onyx_system_uptime_seconds',
    'System uptime in seconds',
    registry=REGISTRY
)

SYSTEM_MEMORY_USAGE = Gauge(
    'onyx_system_memory_usage_bytes',
    'System memory usage in bytes',
    ['type'],
    registry=REGISTRY
)

SYSTEM_CPU_USAGE = Gauge(
    'onyx_system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=REGISTRY
)

SYSTEM_DISK_USAGE = Gauge(
    'onyx_system_disk_usage_bytes',
    'System disk usage in bytes',
    ['type'],
    registry=REGISTRY
)

# Application metrics
APPLICATION_UPTIME = Gauge(
    'onyx_application_uptime_seconds',
    'Application uptime in seconds',
    registry=REGISTRY
)

PYTHON_MEMORY_USAGE = Gauge(
    'onyx_python_memory_usage_bytes',
    'Python memory usage in bytes',
    ['type'],
    registry=REGISTRY
)

TASK_EXECUTIONS_TOTAL = Counter(
    'onyx_task_executions_total',
    'Total number of task executions',
    ['task_type', 'status'],
    registry=REGISTRY
)

TASK_EXECUTION_DURATION = Histogram(
    'onyx_task_execution_duration_seconds',
    'Duration of task executions in seconds',
    ['task_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=REGISTRY
)

DATABASE_CONNECTIONS = Gauge(
    'onyx_database_connections_active',
    'Number of active database connections',
    ['database'],
    registry=REGISTRY
)

DATABASE_QUERIES_TOTAL = Counter(
    'onyx_database_queries_total',
    'Total number of database queries',
    ['database', 'operation', 'status'],
    registry=REGISTRY
)

DATABASE_QUERY_DURATION = Histogram(
    'onyx_database_query_duration_seconds',
    'Duration of database queries in seconds',
    ['database', 'operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=REGISTRY
)

VECTOR_DB_OPERATIONS_TOTAL = Counter(
    'onyx_vector_db_operations_total',
    'Total number of vector database operations',
    ['operation', 'status'],
    registry=REGISTRY
)

VECTOR_DB_OPERATION_DURATION = Histogram(
    'onyx_vector_db_operation_duration_seconds',
    'Duration of vector database operations in seconds',
    ['operation'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0],
    registry=REGISTRY
)

CACHE_OPERATIONS_TOTAL = Counter(
    'onyx_cache_operations_total',
    'Total number of cache operations',
    ['cache', 'operation', 'status'],
    registry=REGISTRY
)

ERRORS_TOTAL = Counter(
    'onyx_errors_total',
    'Total number of errors',
    ['error_type', 'component'],
    registry=REGISTRY
)

class MetricsCollector:
    """Collects and manages application metrics"""

    def __init__(self):
        self.start_time = time.time()
        self.active_requests = 0
        self.system_metrics_thread = None
        self.start_system_metrics_collection()

    def start_system_metrics_collection(self):
        """Start collecting system metrics in background thread"""
        def collect_system_metrics():
            try:
                import psutil

                while True:
                    # System uptime
                    SYSTEM_UPTIME.set(time.time())

                    # Memory metrics
                    memory = psutil.virtual_memory()
                    SYSTEM_MEMORY_USAGE.labels(type='total').set(memory.total)
                    SYSTEM_MEMORY_USAGE.labels(type='available').set(memory.available)
                    SYSTEM_MEMORY_USAGE.labels(type='used').set(memory.used)
                    SYSTEM_MEMORY_USAGE.labels(type='percent').set(memory.percent)

                    # CPU metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    SYSTEM_CPU_USAGE.set(cpu_percent)

                    # Disk metrics
                    disk = psutil.disk_usage('/')
                    SYSTEM_DISK_USAGE.labels(type='total').set(disk.total)
                    SYSTEM_DISK_USAGE.labels(type='used').set(disk.used)
                    SYSTEM_DISK_USAGE.labels(type='free').set(disk.free)
                    SYSTEM_DISK_USAGE.labels(type='percent').set(
                        (disk.used / disk.total) * 100
                    )

                    # Application uptime
                    APPLICATION_UPTIME.set(time.time() - self.start_time)

                    # Python memory (if available)
                    try:
                        import sys
                        if hasattr(sys, '_getframe'):
                            import resource
                            usage = resource.getrusage(resource.RUSAGE_SELF)
                            PYTHON_MEMORY_USAGE.labels(type='max_rss').set(usage.ru_maxrss * 1024)
                    except ImportError:
                        pass

                    time.sleep(30)  # Collect every 30 seconds

            except Exception as e:
                logger.error("system_metrics_collection_failed", {
                    "error": str(e),
                    "type": type(e).__name__
                })

        self.system_metrics_thread = threading.Thread(target=collect_system_metrics, daemon=True)
        self.system_metrics_thread.start()

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        HTTP_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).observe(duration)

        logger.debug("http_request_recorded", {
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration * 1000
        })

    def increment_active_requests(self):
        """Increment active requests counter"""
        self.active_requests += 1
        HTTP_REQUESTS_ACTIVE.set(self.active_requests)

    def decrement_active_requests(self):
        """Decrement active requests counter"""
        self.active_requests = max(0, self.active_requests - 1)
        HTTP_REQUESTS_ACTIVE.set(self.active_requests)

    def record_task_execution(self, task_type: str, status: str, duration: float):
        """Record task execution metrics"""
        TASK_EXECUTIONS_TOTAL.labels(
            task_type=task_type,
            status=status
        ).inc()

        TASK_EXECUTION_DURATION.labels(
            task_type=task_type
        ).observe(duration)

        logger.info("task_execution_recorded", {
            "task_type": task_type,
            "status": status,
            "duration_ms": duration * 1000
        })

    def record_database_query(self, database: str, operation: str, status: str, duration: float):
        """Record database query metrics"""
        DATABASE_QUERIES_TOTAL.labels(
            database=database,
            operation=operation,
            status=status
        ).inc()

        DATABASE_QUERY_DURATION.labels(
            database=database,
            operation=operation
        ).observe(duration)

        logger.debug("database_query_recorded", {
            "database": database,
            "operation": operation,
            "status": status,
            "duration_ms": duration * 1000
        })

    def record_vector_db_operation(self, operation: str, status: str, duration: float):
        """Record vector database operation metrics"""
        VECTOR_DB_OPERATIONS_TOTAL.labels(
            operation=operation,
            status=status
        ).inc()

        VECTOR_DB_OPERATION_DURATION.labels(
            operation=operation
        ).observe(duration)

        logger.debug("vector_db_operation_recorded", {
            "operation": operation,
            "status": status,
            "duration_ms": duration * 1000
        })

    def record_cache_operation(self, cache: str, operation: str, status: str):
        """Record cache operation metrics"""
        CACHE_OPERATIONS_TOTAL.labels(
            cache=cache,
            operation=operation,
            status=status
        ).inc()

        logger.debug("cache_operation_recorded", {
            "cache": cache,
            "operation": operation,
            "status": status
        })

    def record_error(self, error_type: str, component: str, error: Exception = None):
        """Record error metrics"""
        ERRORS_TOTAL.labels(
            error_type=error_type,
            component=component
        ).inc()

        logger.error("error_recorded", {
            "error_type": error_type,
            "component": component,
            "message": str(error) if error else "Unknown error"
        })

    def set_database_connections(self, database: str, count: int):
        """Set active database connections count"""
        DATABASE_CONNECTIONS.labels(database=database).set(count)

    def cleanup(self):
        """Cleanup metrics collector"""
        if self.system_metrics_thread and self.system_metrics_thread.is_alive():
            # Note: Thread will exit on its own due to daemon=True
            pass

        REGISTRY.clear()

# Global metrics collector instance
_metrics_collector: MetricsCollector = None

def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

@asynccontextmanager
async def track_http_request(method: str, endpoint: str):
    """Context manager for tracking HTTP requests"""
    collector = get_metrics_collector()
    collector.increment_active_requests()

    start_time = time.time()
    status_code = 200  # Default status

    try:
        yield
    except Exception as e:
        status_code = 500
        collector.record_error("http_exception", "api", e)
        raise
    finally:
        duration = time.time() - start_time
        collector.record_http_request(method, endpoint, status_code, duration)
        collector.decrement_active_requests()

@asynccontextmanager
async def track_task_execution(task_type: str):
    """Context manager for tracking task execution"""
    collector = get_metrics_collector()

    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception as e:
        status = "failed"
        collector.record_error("task_exception", task_type, e)
        raise
    finally:
        duration = time.time() - start_time
        collector.record_task_execution(task_type, status, duration)

@asynccontextmanager
async def track_database_query(database: str, operation: str):
    """Context manager for tracking database queries"""
    collector = get_metrics_collector()

    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception as e:
        status = "failed"
        collector.record_error("database_exception", f"{database}_{operation}", e)
        raise
    finally:
        duration = time.time() - start_time
        collector.record_database_query(database, operation, status, duration)

@asynccontextmanager
async def track_vector_db_operation(operation: str):
    """Context manager for tracking vector database operations"""
    collector = get_metrics_collector()

    start_time = time.time()
    status = "success"

    try:
        yield
    except Exception as e:
        status = "failed"
        collector.record_error("vector_db_exception", operation, e)
        raise
    finally:
        duration = time.time() - start_time
        collector.record_vector_db_operation(operation, status, duration)

# Convenience functions
def record_user_interaction(action: str, component: str):
    """Record user interaction metrics"""
    # Add to custom metrics if needed
    logger.info("user_interaction", {"action": action, "component": component})

def record_api_call(endpoint: str, method: str, status: str, duration: float):
    """Record API call metrics"""
    collector = get_metrics_collector()
    collector.record_http_request(method, endpoint, int(status), duration)

def record_error(error_type: str, component: str, error: Exception = None):
    """Record error metrics"""
    collector = get_metrics_collector()
    collector.record_error(error_type, component, error)