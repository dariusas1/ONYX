"""
Log Masking Utility

This module provides regex-based credential masking for sensitive data in logs.
Prevents accidental exposure of OAuth tokens, API keys, and other credentials.
"""

import re
import logging
from typing import Dict, List

# Regex patterns for sensitive data
SENSITIVE_PATTERNS = {
    # OAuth tokens (Google, generic)
    "access_token": r"(access_token[\"':\s]*)[\"']?([a-zA-Z0-9\-._~+/]+=*)[\"']?",
    "refresh_token": r"(refresh_token[\"':\s]*)[\"']?([a-zA-Z0-9\-._~+/]+=*)[\"']?",
    "authorization": r"(Authorization[\"':\s]*Bearer\s+)([a-zA-Z0-9\-._~+/]+=*)",
    # API keys
    "api_key": r"(api[_-]?key[\"':\s]*)[\"']?([a-zA-Z0-9\-._~+/]{20,})[\"']?",
    "api_secret": r"(api[_-]?secret[\"':\s]*)[\"']?([a-zA-Z0-9\-._~+/]{20,})[\"']?",
    # AWS credentials
    "aws_access_key": r"(AKIA[0-9A-Z]{16})",
    "aws_secret_key": r"(aws_secret_access_key[\"':\s]*)[\"']?([a-zA-Z0-9/+=]{40})[\"']?",
    # Database credentials
    "password": r"(password[\"':\s]*)[\"']([^\"']{1,256})[\"']",
    "db_password": r"(postgres://[^:]+:)([^@]+)(@)",
    # JWT tokens
    "jwt": r"(eyJ[a-zA-Z0-9_\-\.]+\.eyJ[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9_\-\.]+)",
    # OAuth state parameter
    "oauth_state": r"(state[\"':\s]*)[\"']([a-zA-Z0-9\-._~]+)[\"']?",
}

# Redaction replacement
REDACTION_REPLACEMENT = r"\1[REDACTED]"


class LogMaskingFilter(logging.Filter):
    """
    Logging filter that redacts sensitive data from log messages.

    Usage:
        logger = logging.getLogger(__name__)
        logger.addFilter(LogMaskingFilter())
    """

    def __init__(self, patterns: Dict[str, str] | None = None):
        """
        Initialize filter with redaction patterns.

        Args:
            patterns: Optional dict of {name: regex_pattern} to override defaults
        """
        super().__init__()
        self.patterns = patterns or SENSITIVE_PATTERNS

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Redact sensitive data from log record.

        Args:
            record: LogRecord to filter

        Returns:
            True to allow record through (always returns True)
        """
        # Redact message
        if isinstance(record.msg, str):
            record.msg = self._redact_message(record.msg)

        # Redact exception text if present
        if record.exc_text:
            record.exc_text = self._redact_message(record.exc_text)

        # Redact args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, (tuple, list)):
                record.args = tuple(self._redact_value(arg) for arg in record.args)

        return True

    def _redact_message(self, message: str) -> str:
        """
        Redact all sensitive patterns from message.

        Args:
            message: Message to redact

        Returns:
            Redacted message
        """
        for pattern_name, pattern in self.patterns.items():
            try:
                message = re.sub(
                    pattern,
                    REDACTION_REPLACEMENT,
                    message,
                    flags=re.IGNORECASE,
                    count=0,  # Replace all occurrences
                )
            except re.error as e:
                # Log pattern error but don't crash
                print(f"Error in redaction pattern '{pattern_name}': {e}")
                continue

        return message

    def _redact_value(self, value) -> str:
        """
        Redact sensitive values in any format.

        Args:
            value: Value to potentially redact

        Returns:
            Redacted value or original if not sensitive
        """
        if not isinstance(value, str):
            return value

        return self._redact_message(value)


def create_masked_logger(name: str) -> logging.Logger:
    """
    Create a logger with masking filter enabled.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance with masking filter applied
    """
    logger = logging.getLogger(name)
    logger.addFilter(LogMaskingFilter())
    return logger


def redact_string(value: str, patterns: Dict[str, str] | None = None) -> str:
    """
    Redact sensitive data from a string value.

    Args:
        value: String to redact
        patterns: Optional custom redaction patterns

    Returns:
        Redacted string
    """
    filter_obj = LogMaskingFilter(patterns)
    return filter_obj._redact_message(value)


def redact_dict(data: Dict, patterns: Dict[str, str] | None = None) -> Dict:
    """
    Redact sensitive data from dictionary values.

    Args:
        data: Dictionary to redact
        patterns: Optional custom redaction patterns

    Returns:
        Dictionary with values redacted
    """
    filter_obj = LogMaskingFilter(patterns)
    return {k: filter_obj._redact_value(v) for k, v in data.items()}


# Convenience: Export default filter instance
DEFAULT_MASK_FILTER = LogMaskingFilter()


def mask_credentials(func):
    """
    Decorator to mask credentials in function logs.

    Usage:
        @mask_credentials
        def my_function():
            logger.info(f"Token: {token}")
    """

    def wrapper(*args, **kwargs):
        # Get function logger
        logger = logging.getLogger(func.__module__)
        logger.addFilter(DEFAULT_MASK_FILTER)

        try:
            return func(*args, **kwargs)
        finally:
            logger.removeFilter(DEFAULT_MASK_FILTER)

    return wrapper


if __name__ == "__main__":
    # Test masking functionality
    test_messages = [
        'access_token: "ya29.a0AfH6SMBx_test_token_12345"',
        "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test",
        "api_key='sk-1234567890abcdefgh'",
        "password: 'MySecretPassword123'",
    ]

    print("Testing Log Masking:")
    print("-" * 50)

    for msg in test_messages:
        masked = redact_string(msg)
        print(f"Original:  {msg}")
        print(f"Masked:    {masked}")
        print()
