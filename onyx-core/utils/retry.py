"""
Retry Utilities with Exponential Backoff

This module provides retry decorators and utilities for handling transient failures
with exponential backoff strategy.
"""

import time
import logging
from typing import Callable, Optional, Tuple, Type
from functools import wraps
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_DELAYS = [1, 5, 30]  # 1s, 5s, 30s as specified in AC3.2.7

# Retriable HTTP status codes
RETRIABLE_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests (rate limit)
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}


def is_retriable_error(exception: Exception) -> bool:
    """
    Determine if an exception is retriable

    Args:
        exception: Exception to check

    Returns:
        True if the exception should be retried
    """
    # Check for HTTP errors from Google API
    if isinstance(exception, HttpError):
        # Check if status code is retriable
        if exception.resp.status in RETRIABLE_STATUS_CODES:
            return True

    # Check for network-related exceptions
    if isinstance(exception, (TimeoutError, ConnectionError)):
        return True

    # Check for common network exceptions (from requests library)
    exception_name = type(exception).__name__
    if exception_name in ["ConnectionError", "Timeout", "ReadTimeout"]:
        return True

    return False


def get_error_category(exception: Exception) -> str:
    """
    Categorize an exception for logging and error tracking

    Args:
        exception: Exception to categorize

    Returns:
        Error category string
    """
    if isinstance(exception, HttpError):
        if exception.resp.status == 403:
            return "permission_denied"
        elif exception.resp.status == 429:
            return "rate_limit_exceeded"
        elif exception.resp.status in RETRIABLE_STATUS_CODES:
            return "network_timeout"
        else:
            return "api_error"

    if isinstance(exception, (TimeoutError, ConnectionError)):
        return "network_timeout"

    if "format" in str(exception).lower() or "mime" in str(exception).lower():
        return "invalid_format"

    return "unknown_error"


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_delays: Optional[list] = None,
    retriable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Decorator to retry a function with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_delays: List of delay times in seconds for each retry (default: [1, 5, 30])
        retriable_exceptions: Tuple of exception types to retry (default: auto-detect)

    Example:
        @retry_with_backoff(max_retries=3, backoff_delays=[1, 5, 30])
        def fetch_data():
            # Your code here
            pass
    """
    if backoff_delays is None:
        backoff_delays = DEFAULT_BACKOFF_DELAYS

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if exception is retriable
                    should_retry = False
                    if retriable_exceptions:
                        should_retry = isinstance(e, retriable_exceptions)
                    else:
                        should_retry = is_retriable_error(e)

                    # If not retriable or no more retries, raise immediately
                    if not should_retry or attempt >= max_retries:
                        error_category = get_error_category(e)
                        logger.error(
                            f"Function {func.__name__} failed after {attempt + 1} attempts: "
                            f"{error_category} - {str(e)}"
                        )
                        raise

                    # Log retry attempt
                    error_category = get_error_category(e)
                    delay = backoff_delays[min(attempt, len(backoff_delays) - 1)]
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): "
                        f"{error_category} - {str(e)}. Retrying in {delay}s..."
                    )

                    # Wait before retrying
                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def retry_async_with_backoff(
    func: Callable,
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_delays: Optional[list] = None,
    **kwargs
):
    """
    Async function to retry an async callable with exponential backoff

    Args:
        func: Async callable to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retry attempts
        backoff_delays: List of delay times in seconds
        **kwargs: Keyword arguments for func

    Returns:
        Result from func

    Raises:
        Last exception if all retries fail
    """
    import asyncio

    if backoff_delays is None:
        backoff_delays = DEFAULT_BACKOFF_DELAYS

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # Check if exception is retriable
            should_retry = is_retriable_error(e)

            # If not retriable or no more retries, raise immediately
            if not should_retry or attempt >= max_retries:
                error_category = get_error_category(e)
                logger.error(
                    f"Async function {func.__name__} failed after {attempt + 1} attempts: "
                    f"{error_category} - {str(e)}"
                )
                raise

            # Log retry attempt
            error_category = get_error_category(e)
            delay = backoff_delays[min(attempt, len(backoff_delays) - 1)]
            logger.warning(
                f"Async function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"{error_category} - {str(e)}. Retrying in {delay}s..."
            )

            # Wait before retrying
            await asyncio.sleep(delay)

    # This should never be reached, but just in case
    if last_exception:
        raise last_exception
