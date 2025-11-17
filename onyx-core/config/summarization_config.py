"""
Summarization Configuration for ONYX

Configuration settings for the auto-summarization pipeline
including LLM settings, performance thresholds, and monitoring.

Story 4-4: Auto-Summarization Pipeline
"""

import os
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class SummarizationConfig:
    """Configuration for auto-summarization pipeline"""

    # Trigger Settings
    TRIGGER_INTERVAL: int = 10  # Messages between summaries
    COOLDOWN_SECONDS: int = 60  # Minimum time between summaries
    MAX_CONCURRENT_JOBS: int = 2  # Concurrent summarization jobs

    # LLM Settings
    LITELLM_PROXY_URL: str = "http://litellm-proxy:4000"
    DEEPSEEK_MODEL: str = "deepseek-main"
    SUMMARIZATION_TIMEOUT_SECONDS: int = 30
    SUMMARIZATION_MAX_RETRIES: int = 3
    SUMMARIZATION_RETRY_DELAY_MS: int = 1000

    # Summary Quality Settings
    MIN_SUMMARY_LENGTH: int = 20
    MAX_SUMMARY_LENGTH: int = 300
    TEMPERATURE: float = 0.3
    MAX_TOKENS: int = 150
    AUTO_SUMMARY_CONFIDENCE: float = 0.9

    # Duplicate Detection
    SUMMARY_DUPLICATE_THRESHOLD: float = 0.8
    SUMMARY_DUPLICATE_WINDOW_HOURS: int = 1

    # Performance Settings
    TARGET_PROCESSING_TIME_MS: int = 2000
    MAX_PROCESSING_TIME_MS: int = 10000
    TARGET_SUCCESS_RATE: float = 95.0
    QUEUE_PROCESSING_TIMEOUT_SECONDS: int = 30
    JOB_TIMEOUT_SECONDS: int = 120

    # Worker Settings
    WORKER_HEALTH_CHECK_INTERVAL: int = 60
    WORKER_METRICS_INTERVAL: int = 300
    WORKER_LOG_LEVEL: str = "INFO"

    # Monitoring and Analytics
    METRICS_RETENTION_DAYS: int = 90
    TRIGGER_LOGS_RETENTION_DAYS: int = 30
    PERFORMANCE_ALERT_THRESHOLD_MS: int = 5000
    FAILURE_RATE_ALERT_THRESHOLD: float = 10.0

    # Memory and Storage
    SUMMARY_MEMORY_CATEGORY: str = "summary"
    SUMMARY_MEMORY_SOURCE_TYPE: str = "auto_summary"
    MAX_SUMMARY_TOPICS: int = 5
    SENTIMENT_ANALYSIS_ENABLED: bool = True

    # Background Processing
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = None
    REDIS_DB: int = 0
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # Database Settings
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "manus"
    POSTGRES_USER: str = "manus"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20

    @classmethod
    def from_environment(cls) -> 'SummarizationConfig':
        """Create configuration from environment variables"""
        return cls(
            # Trigger Settings
            TRIGGER_INTERVAL=int(os.getenv("SUMMARIZATION_TRIGGER_INTERVAL", "10")),
            COOLDOWN_SECONDS=int(os.getenv("SUMMARIZATION_COOLDOWN_SECONDS", "60")),
            MAX_CONCURRENT_JOBS=int(os.getenv("MAX_CONCURRENT_SUMMARIZATION_JOBS", "2")),

            # LLM Settings
            LITELLM_PROXY_URL=os.getenv("LITELLM_PROXY_URL", "http://litellm-proxy:4000"),
            DEEPSEEK_MODEL=os.getenv("DEEPSEEK_MODEL", "deepseek-main"),
            SUMMARIZATION_TIMEOUT_SECONDS=int(os.getenv("SUMMARIZATION_TIMEOUT_SECONDS", "30")),
            SUMMARIZATION_MAX_RETRIES=int(os.getenv("SUMMARIZATION_MAX_RETRIES", "3")),
            SUMMARIZATION_RETRY_DELAY_MS=int(os.getenv("SUMMARIZATION_RETRY_DELAY_MS", "1000")),

            # Summary Quality Settings
            MIN_SUMMARY_LENGTH=int(os.getenv("SUMMARIZATION_MIN_LENGTH", "20")),
            MAX_SUMMARY_LENGTH=int(os.getenv("SUMMARIZATION_MAX_LENGTH", "300")),
            TEMPERATURE=float(os.getenv("SUMMARIZATION_TEMPERATURE", "0.3")),
            MAX_TOKENS=int(os.getenv("SUMMARIZATION_MAX_TOKENS", "150")),
            AUTO_SUMMARY_CONFIDENCE=float(os.getenv("AUTO_SUMMARY_CONFIDENCE", "0.9")),

            # Duplicate Detection
            SUMMARY_DUPLICATE_THRESHOLD=float(os.getenv("SUMMARIZATION_DUPLICATE_THRESHOLD", "0.8")),
            SUMMARY_DUPLICATE_WINDOW_HOURS=int(os.getenv("SUMMARIZATION_DUPLICATE_WINDOW_HOURS", "1")),

            # Performance Settings
            TARGET_PROCESSING_TIME_MS=int(os.getenv("TARGET_PROCESSING_TIME_MS", "2000")),
            MAX_PROCESSING_TIME_MS=int(os.getenv("MAX_PROCESSING_TIME_MS", "10000")),
            TARGET_SUCCESS_RATE=float(os.getenv("TARGET_SUCCESS_RATE", "95.0")),
            QUEUE_PROCESSING_TIMEOUT_SECONDS=int(os.getenv("QUEUE_PROCESSING_TIMEOUT_SECONDS", "30")),
            JOB_TIMEOUT_SECONDS=int(os.getenv("SUMMARIZATION_JOB_TIMEOUT_SECONDS", "120")),

            # Worker Settings
            WORKER_HEALTH_CHECK_INTERVAL=int(os.getenv("WORKER_HEALTH_CHECK_INTERVAL", "60")),
            WORKER_METRICS_INTERVAL=int(os.getenv("WORKER_METRICS_INTERVAL", "300")),
            WORKER_LOG_LEVEL=os.getenv("WORKER_LOG_LEVEL", "INFO"),

            # Monitoring and Analytics
            METRICS_RETENTION_DAYS=int(os.getenv("METRICS_RETENTION_DAYS", "90")),
            TRIGGER_LOGS_RETENTION_DAYS=int(os.getenv("TRIGGER_LOGS_RETENTION_DAYS", "30")),
            PERFORMANCE_ALERT_THRESHOLD_MS=int(os.getenv("PERFORMANCE_ALERT_THRESHOLD_MS", "5000")),
            FAILURE_RATE_ALERT_THRESHOLD=float(os.getenv("FAILURE_RATE_ALERT_THRESHOLD", "10.0")),

            # Memory and Storage
            SUMMARY_MEMORY_CATEGORY=os.getenv("SUMMARY_MEMORY_CATEGORY", "summary"),
            SUMMARY_MEMORY_SOURCE_TYPE=os.getenv("SUMMARY_MEMORY_SOURCE_TYPE", "auto_summary"),
            MAX_SUMMARY_TOPICS=int(os.getenv("MAX_SUMMARY_TOPICS", "5")),
            SENTIMENT_ANALYSIS_ENABLED=os.getenv("SENTIMENT_ANALYSIS_ENABLED", "true").lower() == "true",

            # Background Processing
            REDIS_HOST=os.getenv("REDIS_HOST", "localhost"),
            REDIS_PORT=int(os.getenv("REDIS_PORT", "6379")),
            REDIS_PASSWORD=os.getenv("REDIS_PASSWORD"),
            REDIS_DB=int(os.getenv("REDIS_DB", "0")),
            REDIS_SOCKET_TIMEOUT=int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            REDIS_SOCKET_CONNECT_TIMEOUT=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5")),

            # Database Settings
            POSTGRES_HOST=os.getenv("POSTGRES_HOST", "localhost"),
            POSTGRES_PORT=int(os.getenv("POSTGRES_PORT", "5432")),
            POSTGRES_DB=os.getenv("POSTGRES_DB", "manus"),
            POSTGRES_USER=os.getenv("POSTGRES_USER", "manus"),
            POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD", ""),
            POSTGRES_POOL_SIZE=int(os.getenv("POSTGRES_POOL_SIZE", "10")),
            POSTGRES_MAX_OVERFLOW=int(os.getenv("POSTGRES_MAX_OVERFLOW", "20"))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            field.name: getattr(self, field.name)
            for field in self.__dataclass_fields__.values()
        }

    def validate(self) -> Dict[str, str]:
        """Validate configuration and return any errors"""
        errors = {}

        # Validate numeric ranges
        if self.TRIGGER_INTERVAL <= 0:
            errors["TRIGGER_INTERVAL"] = "Must be positive integer"

        if self.COOLDOWN_SECONDS < 0:
            errors["COOLDOWN_SECONDS"] = "Must be non-negative integer"

        if self.MAX_CONCURRENT_JOBS <= 0 or self.MAX_CONCURRENT_JOBS > 10:
            errors["MAX_CONCURRENT_JOBS"] = "Must be between 1 and 10"

        if self.TEMPERATURE < 0 or self.TEMPERATURE > 2:
            errors["TEMPERATURE"] = "Must be between 0 and 2"

        if self.MAX_TOKENS <= 0 or self.MAX_TOKENS > 1000:
            errors["MAX_TOKENS"] = "Must be between 1 and 1000"

        if self.AUTO_SUMMARY_CONFIDENCE < 0 or self.AUTO_SUMMARY_CONFIDENCE > 1:
            errors["AUTO_SUMMARY_CONFIDENCE"] = "Must be between 0 and 1"

        if self.MIN_SUMMARY_LENGTH >= self.MAX_SUMMARY_LENGTH:
            errors["SUMMARY_LENGTH"] = "MIN_SUMMARY_LENGTH must be less than MAX_SUMMARY_LENGTH"

        if self.SUMMARY_DUPLICATE_THRESHOLD < 0 or self.SUMMARY_DUPLICATE_THRESHOLD > 1:
            errors["SUMMARY_DUPLICATE_THRESHOLD"] = "Must be between 0 and 1"

        if self.TARGET_SUCCESS_RATE < 0 or self.TARGET_SUCCESS_RATE > 100:
            errors["TARGET_SUCCESS_RATE"] = "Must be between 0 and 100"

        # Validate URLs
        if not self.LITELLM_PROXY_URL.startswith("http"):
            errors["LITELLM_PROXY_URL"] = "Must be a valid HTTP URL"

        # Validate Redis configuration
        if self.REDIS_PORT <= 0 or self.REDIS_PORT > 65535:
            errors["REDIS_PORT"] = "Must be a valid port number"

        # Validate PostgreSQL configuration
        if self.POSTGRES_PORT <= 0 or self.POSTGRES_PORT > 65535:
            errors["POSTGRES_PORT"] = "Must be a valid port number"

        return errors

    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration as dictionary"""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "password": self.REDIS_PASSWORD,
            "db": self.REDIS_DB,
            "decode_responses": True,
            "socket_connect_timeout": self.REDIS_SOCKET_CONNECT_TIMEOUT,
            "socket_timeout": self.REDIS_SOCKET_TIMEOUT,
            "retry_on_timeout": True
        }

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration as dictionary"""
        return {
            "host": self.POSTGRES_HOST,
            "port": self.POSTGRES_PORT,
            "database": self.POSTGRES_DB,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD,
            "pool_size": self.POSTGRES_POOL_SIZE,
            "max_overflow": self.POSTGRES_MAX_OVERFLOW
        }

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration as dictionary"""
        return {
            "model": self.DEEPSEEK_MODEL,
            "temperature": self.TEMPERATURE,
            "max_tokens": self.MAX_TOKENS,
            "timeout": self.SUMMARIZATION_TIMEOUT_SECONDS,
            "max_retries": self.SUMMARIZATION_MAX_RETRIES,
            "retry_delay": self.SUMMARIZATION_RETRY_DELAY_MS
        }

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    def get_worker_config(self) -> Dict[str, Any]:
        """Get worker configuration as dictionary"""
        return {
            "max_concurrent_jobs": self.MAX_CONCURRENT_JOBS,
            "job_timeout": self.JOB_TIMEOUT_SECONDS,
            "health_check_interval": self.WORKER_HEALTH_CHECK_INTERVAL,
            "metrics_interval": self.WORKER_METRICS_INTERVAL,
            "log_level": self.WORKER_LOG_LEVEL
        }


# Global configuration instance
_config = None


def get_summarization_config() -> SummarizationConfig:
    """Get or create summarization configuration instance"""
    global _config
    if _config is None:
        _config = SummarizationConfig.from_environment()

        # Validate configuration
        errors = _config.validate()
        if errors:
            error_messages = [f"{field}: {error}" for field, error in errors.items()]
            raise ValueError(f"Configuration validation failed: {'; '.join(error_messages)}")

    return _config


def reload_summarization_config() -> SummarizationConfig:
    """Reload configuration from environment"""
    global _config
    _config = SummarizationConfig.from_environment()
    return _config