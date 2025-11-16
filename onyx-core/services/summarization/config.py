"""
Summarization Configuration
Story 4-4: Auto-Summarization Pipeline

Centralized configuration management for the summarization pipeline.
"""

import os
from typing import Dict, Any


class SummarizationConfig:
    """Configuration settings for the summarization pipeline."""

    # Trigger Service Configuration
    TRIGGER_INTERVAL: int = int(os.getenv('SUMMARIZATION_TRIGGER_INTERVAL', '10'))
    TRIGGER_PRIORITY_RECENT_HOURS: int = int(os.getenv('SUMMARIZATION_PRIORITY_RECENT_HOURS', '2'))
    DUPLICATE_CHECK_HOURS: int = int(os.getenv('SUMMARIZATION_DUPLICATE_CHECK_HOURS', '1'))
    CLEANUP_DAYS: int = int(os.getenv('SUMMARIZATION_CLEANUP_DAYS', '30'))

    # LLM Summarization Configuration
    LITELLM_BASE_URL: str = os.getenv('LITELLM_BASE_URL', 'http://litellm-proxy:4000')
    LLM_MODEL: str = os.getenv('SUMMARIZATION_LLM_MODEL', 'deepseek-main')
    LLM_TEMPERATURE: float = float(os.getenv('SUMMARIZATION_LLM_TEMPERATURE', '0.3'))
    LLM_MAX_TOKENS: int = int(os.getenv('SUMMARIZATION_LLM_MAX_TOKENS', '150'))
    LLM_TIMEOUT: int = int(os.getenv('SUMMARIZATION_LLM_TIMEOUT', '30'))

    # Summary Length Constraints
    SUMMARY_MIN_LENGTH: int = int(os.getenv('SUMMARY_MIN_LENGTH', '20'))
    SUMMARY_MAX_LENGTH: int = int(os.getenv('SUMMARY_MAX_LENGTH', '300'))

    # Topic Extraction Configuration
    TOPICS_MIN_COUNT: int = int(os.getenv('SUMMARIZATION_TOPICS_MIN_COUNT', '1'))
    TOPICS_MAX_COUNT: int = int(os.getenv('SUMMARIZATION_TOPICS_MAX_COUNT', '5'))
    TOPICS_MAX_LENGTH: int = int(os.getenv('SUMMARIZATION_TOPICS_MAX_LENGTH', '50'))

    # Worker Configuration
    WORKER_CONCURRENCY: int = int(os.getenv('SUMMARY_WORKER_CONCURRENCY', '2'))
    WORKER_MAX_RETRIES: int = int(os.getenv('SUMMARY_WORKER_MAX_RETRIES', '3'))
    WORKER_JOB_DELAY: int = int(os.getenv('SUMMARY_WORKER_JOB_DELAY', '1000'))
    WORKER_REMOVE_ON_COMPLETE: int = int(os.getenv('SUMMARY_WORKER_REMOVE_ON_COMPLETE', '100'))
    WORKER_REMOVE_ON_FAIL: int = int(os.getenv('SUMMARY_WORKER_REMOVE_ON_FAIL', '50'))

    # Queue Configuration
    QUEUE_DEFAULT_ATTEMPTS: int = int(os.getenv('SUMMARIZATION_QUEUE_DEFAULT_ATTEMPTS', '3'))
    QUEUE_BACKOFF: str = os.getenv('SUMMARIZATION_QUEUE_BACKOFF', 'exponential')
    QUEUE_PRIORITY_MIN: int = int(os.getenv('SUMMARIZATION_QUEUE_PRIORITY_MIN', '1'))
    QUEUE_PRIORITY_MAX: int = int(os.getenv('SUMMARIZATION_QUEUE_PRIORITY_MAX', '10'))

    # Memory Storage Configuration
    STORAGE_SIMILARITY_THRESHOLD: float = float(os.getenv('SUMMARIZATION_SIMILARITY_THRESHOLD', '0.85'))
    STORAGE_SIMILARITY_CHECK_DAYS: int = int(os.getenv('SUMMARIZATION_SIMILARITY_CHECK_DAYS', '7'))

    # Performance Metrics
    METRICS_SUCCESS_RATE_WINDOW: str = os.getenv('SUMMARIZATION_METRICS_SUCCESS_RATE_WINDOW', '24 hours')
    METRICS_PROCESSING_TIME_WINDOW: str = os.getenv('SUMMARIZATION_METRICS_PROCESSING_TIME_WINDOW', '24 hours')

    # Redis Configuration for BullMQ
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """Get LLM configuration as dictionary."""
        return {
            'base_url': cls.LITELLM_BASE_URL,
            'model': cls.LLM_MODEL,
            'temperature': cls.LLM_TEMPERATURE,
            'max_tokens': cls.LLM_MAX_TOKENS,
            'timeout': cls.LLM_TIMEOUT
        }

    @classmethod
    def get_worker_config(cls) -> Dict[str, Any]:
        """Get worker configuration as dictionary."""
        return {
            'concurrency': cls.WORKER_CONCURRENCY,
            'max_retries': cls.WORKER_MAX_RETRIES,
            'job_delay': cls.WORKER_JOB_DELAY,
            'remove_on_complete': cls.WORKER_REMOVE_ON_COMPLETE,
            'remove_on_fail': cls.WORKER_REMOVE_ON_FAIL
        }

    @classmethod
    def get_queue_config(cls) -> Dict[str, Any]:
        """Get BullMQ queue configuration as dictionary."""
        return {
            'attempts': cls.QUEUE_DEFAULT_ATTEMPTS,
            'backoff': cls.QUEUE_BACKOFF,
            'removeOnComplete': cls.WORKER_REMOVE_ON_COMPLETE,
            'removeOnFail': cls.WORKER_REMOVE_ON_FAIL,
            'delay': cls.WORKER_JOB_DELAY
        }

    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Get Redis configuration as dictionary."""
        return {
            'host': cls.REDIS_HOST,
            'port': cls.REDIS_PORT,
            'db': cls.REDIS_DB
        }

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration values."""
        errors = []

        # Validate numeric ranges
        if cls.TRIGGER_INTERVAL <= 0:
            errors.append("TRIGGER_INTERVAL must be positive")

        if not (1 <= cls.QUEUE_PRIORITY_MIN <= cls.QUEUE_PRIORITY_MAX <= 10):
            errors.append("Queue priority must be between 1 and 10")

        if cls.SUMMARY_MIN_LENGTH >= cls.SUMMARY_MAX_LENGTH:
            errors.append("SUMMARY_MIN_LENGTH must be less than SUMMARY_MAX_LENGTH")

        if cls.TOPICS_MIN_COUNT >= cls.TOPICS_MAX_COUNT:
            errors.append("TOPICS_MIN_COUNT must be less than TOPICS_MAX_COUNT")

        if not (0.0 <= cls.STORAGE_SIMILARITY_THRESHOLD <= 1.0):
            errors.append("STORAGE_SIMILARITY_THRESHOLD must be between 0.0 and 1.0")

        if not (0.0 <= cls.LLM_TEMPERATURE <= 2.0):
            errors.append("LLM_TEMPERATURE must be between 0.0 and 2.0")

        if cls.LLM_TIMEOUT <= 0:
            errors.append("LLM_TIMEOUT must be positive")

        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            return False

        return True


# Import logger after configuration to avoid circular imports
import logging
logger = logging.getLogger(__name__)

# Global configuration instance
config = SummarizationConfig()