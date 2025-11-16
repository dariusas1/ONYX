"""
Summarization Health Checker
Story 4-4: Auto-Summarization Pipeline

Health checking and circuit breaker functionality for external services.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
import httpx
from dataclasses import dataclass, field

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class HealthStatus:
    """Health status for external services."""
    service_name: str
    is_healthy: bool
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None


@dataclass
class CircuitBreaker:
    """Circuit breaker for external service calls."""
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    expected_exception: type = Exception

    def __post_init__(self):
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable):
        """Decorator to wrap functions with circuit breaker logic."""
        async def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                    logger.info(f"Circuit breaker transitioning to HALF_OPEN for {func.__name__}")
                else:
                    raise Exception(f"Circuit breaker OPEN for {func.__name__}")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.last_failure_time is None:
            return True
        return datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout_seconds)

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            logger.info("Circuit breaker CLOSED after successful call")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")


class SummarizationHealthChecker:
    """
    Health checking service for summarization external dependencies.

    Features:
    - LiteLLM proxy health monitoring
    - Circuit breaker pattern for external calls
    - Health status tracking and metrics
    - Automatic recovery detection
    """

    def __init__(self):
        self.health_status: Dict[str, HealthStatus] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Initialize circuit breakers for external services
        self.circuit_breakers['litellm'] = CircuitBreaker(
            failure_threshold=int(os.getenv('SUMMARIZATION_CIRCUIT_FAILURE_THRESHOLD', '5')),
            recovery_timeout_seconds=int(os.getenv('SUMMARIZATION_CIRCUIT_RECOVERY_TIMEOUT', '60')),
            expected_exception=httpx.RequestError
        )

    async def check_litellm_health(self) -> HealthStatus:
        """
        Check LiteLLM proxy health.

        Returns:
            HealthStatus with current health information
        """
        service_name = 'litellm'
        start_time = datetime.utcnow()

        try:
            # Make health check request to LiteLLM proxy
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{config.LITELLM_BASE_URL}/health",
                    headers={"Content-Type": "application/json"}
                )

                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                if response.status_code == 200:
                    status = HealthStatus(
                        service_name=service_name,
                        is_healthy=True,
                        last_check=start_time,
                        response_time_ms=response_time,
                        consecutive_failures=0,
                        last_success=start_time
                    )
                else:
                    status = HealthStatus(
                        service_name=service_name,
                        is_healthy=False,
                        last_check=start_time,
                        response_time_ms=response_time,
                        error_message=f"HTTP {response.status_code}: {response.text}",
                        consecutive_failures=self._get_previous_failures(service_name) + 1
                    )

        except Exception as error:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            status = HealthStatus(
                service_name=service_name,
                is_healthy=False,
                last_check=start_time,
                response_time_ms=response_time,
                error_message=str(error),
                consecutive_failures=self._get_previous_failures(service_name) + 1
            )
            logger.error(f"LiteLLM health check failed: {error}")

        # Update stored status
        self.health_status[service_name] = status

        return status

    async def check_all_services(self) -> Dict[str, HealthStatus]:
        """
        Check health of all external services.

        Returns:
            Dictionary mapping service names to HealthStatus
        """
        # Check LiteLLM proxy
        litellm_status = await self.check_litellm_health()

        return {
            'litellm': litellm_status
        }

    def get_service_health(self, service_name: str) -> Optional[HealthStatus]:
        """
        Get current health status for a service.

        Args:
            service_name: Name of the service to check

        Returns:
            HealthStatus if available, None otherwise
        """
        return self.health_status.get(service_name)

    def is_service_healthy(self, service_name: str, max_age_seconds: int = 300) -> bool:
        """
        Check if a service is healthy within the time window.

        Args:
            service_name: Name of the service to check
            max_age_seconds: Maximum age of health check in seconds

        Returns:
            True if service is healthy and check is recent, False otherwise
        """
        status = self.get_service_health(service_name)
        if not status:
            return False

        age_seconds = (datetime.utcnow() - status.last_check).total_seconds()
        return status.is_healthy and age_seconds <= max_age_seconds

    def get_circuit_breaker(self, service_name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker for a service."""
        return self.circuit_breakers.get(service_name)

    async def get_health_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive health metrics.

        Returns:
            Dictionary with health metrics for all services
        """
        metrics = {
            'updated_at': datetime.utcnow().isoformat(),
            'services': {}
        }

        for service_name, status in self.health_status.items():
            circuit_breaker = self.circuit_breakers.get(service_name)

            metrics['services'][service_name] = {
                'is_healthy': status.is_healthy,
                'last_check': status.last_check.isoformat(),
                'response_time_ms': status.response_time_ms,
                'consecutive_failures': status.consecutive_failures,
                'last_success': status.last_success.isoformat() if status.last_success else None,
                'error_message': status.error_message,
                'circuit_breaker_state': circuit_breaker.state if circuit_breaker else None,
                'circuit_breaker_failures': circuit_breaker.failure_count if circuit_breaker else 0
            }

        # Overall health summary
        healthy_services = sum(1 for s in self.health_status.values() if s.is_healthy)
        total_services = len(self.health_status)

        metrics['summary'] = {
            'total_services': total_services,
            'healthy_services': healthy_services,
            'unhealthy_services': total_services - healthy_services,
            'overall_health': 'healthy' if healthy_services == total_services else 'degraded' if healthy_services > 0 else 'unhealthy'
        }

        return metrics

    def _get_previous_failures(self, service_name: str) -> int:
        """Get consecutive failures from previous health status."""
        previous_status = self.health_status.get(service_name)
        return previous_status.consecutive_failures if previous_status else 0

    async def start_health_monitoring(self, interval_seconds: int = 60):
        """
        Start continuous health monitoring in background.

        Args:
            interval_seconds: Interval between health checks
        """
        logger.info(f"Starting health monitoring with {interval_seconds}s interval")

        while True:
            try:
                await self.check_all_services()
                await asyncio.sleep(interval_seconds)
            except Exception as error:
                logger.error(f"Health monitoring error: {error}")
                await asyncio.sleep(interval_seconds)


# Global health checker instance
health_checker = SummarizationHealthChecker()


# Import for configuration
import os