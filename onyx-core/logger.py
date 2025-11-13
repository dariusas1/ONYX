"""
=============================================================================
ONYX Logging Utility
=============================================================================
Structured JSON logging for Python services
"""

import json
import logging
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager
import os


class StructuredLogger:
    """Structured JSON logger for ONYX services"""

    def __init__(self, service_name: str, log_level: str = "INFO"):
        self.service_name = service_name
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Configure structured JSON logger"""
        logger = logging.getLogger(self.service_name)
        logger.setLevel(self.log_level)

        # Remove existing handlers
        logger.handlers.clear()

        # Create JSON handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.log_level)

        # Set JSON formatter
        formatter = StructuredFormatter(self.service_name)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False

        return logger

    def log(
        self,
        level: str,
        action: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log structured event"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.lower(),
            "service": self.service_name,
            "action": action,
            "details": details,
            "user_id": user_id,
        }

        if error:
            log_entry["error"] = error

        getattr(self.logger, level.lower())(json.dumps(log_entry))

    def info(self, action: str, details: Dict[str, Any], user_id: Optional[str] = None):
        """Log info event"""
        self.log("INFO", action, details, user_id)

    def warn(self, action: str, details: Dict[str, Any], user_id: Optional[str] = None):
        """Log warning event"""
        self.log("WARN", action, details, user_id)

    def error(
        self,
        action: str,
        details: Dict[str, Any],
        error: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Log error event"""
        self.log("ERROR", action, details, user_id, error)

    def debug(
        self, action: str, details: Dict[str, Any], user_id: Optional[str] = None
    ):
        """Log debug event"""
        self.log("DEBUG", action, details, user_id)

    @contextmanager
    def timer(
        self,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ):
        """Context manager for timing operations"""
        start_time = time.time()
        operation_id = f"{action}_{int(start_time)}"

        self.info(
            f"{action}_started",
            {"operation_id": operation_id, **(details or {})},
            user_id,
        )

        try:
            yield operation_id

            duration = (time.time() - start_time) * 1000
            self.info(
                f"{action}_completed",
                {
                    "operation_id": operation_id,
                    "duration_ms": round(duration, 2),
                    **(details or {}),
                },
                user_id,
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.error(
                f"{action}_failed",
                {
                    "operation_id": operation_id,
                    "duration_ms": round(duration, 2),
                    "error_type": type(e).__name__,
                    **(details or {}),
                },
                str(e),
                user_id,
            )
            raise


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname.lower(),
            "service": self.service_name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["error"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry)


# Global logger instance
_logger = None


def get_logger(service_name: Optional[str] = None) -> StructuredLogger:
    """Get or create logger instance"""
    global _logger
    if _logger is None or (service_name and _logger.service_name != service_name):
        _logger = StructuredLogger(
            service_name or os.getenv("SERVICE_NAME") or "onyx-core",
            os.getenv("LOG_LEVEL", "INFO"),
        )
    return _logger


# Convenience functions
def log_info(action: str, details: Dict[str, Any], user_id: Optional[str] = None):
    """Log info event"""
    get_logger().info(action, details, user_id)


def log_warn(action: str, details: Dict[str, Any], user_id: Optional[str] = None):
    """Log warning event"""
    get_logger().warn(action, details, user_id)


def log_error(
    action: str,
    details: Dict[str, Any],
    error: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Log error event"""
    get_logger().error(action, details, error, user_id)


def log_debug(action: str, details: Dict[str, Any], user_id: Optional[str] = None):
    """Log debug event"""
    get_logger().debug(action, details, user_id)


@contextmanager
def log_timer(
    action: str, details: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None
):
    """Context manager for timing operations"""
    return get_logger().timer(action, details, user_id)


# Example usage
if __name__ == "__main__":
    logger = get_logger("test-service")

    # Basic logging
    logger.info("service_started", {"version": "1.0.0", "port": 8080})

    # With timer
    with logger.timer("database_query", {"query": "SELECT * FROM users"}):
        time.sleep(0.1)  # Simulate work

    # Error logging
    try:
        raise ValueError("Something went wrong")
    except Exception as e:
        logger.error(
            "validation_failed", {"field": "email", "value": "invalid"}, str(e)
        )
