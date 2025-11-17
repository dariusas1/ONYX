"""
Token Refresh Background Worker

This module implements automatic OAuth token refresh for users with tokens
expiring within 1 hour. Runs periodically (every 15 minutes) to prevent
mid-request token expiry failures.

Uses APScheduler for task scheduling.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import traceback

from utils.database import get_db_service
from services.google_oauth import get_oauth_service
from utils.log_masking import create_masked_logger

logger = create_masked_logger(__name__)

# Token expiry buffer (refresh if expires within 1 hour)
TOKEN_EXPIRY_BUFFER_HOURS = 1

# Maximum retries for failed refreshes
MAX_RETRIES = 3


class TokenRefreshWorker:
    """
    Background worker for automatic OAuth token refresh.

    Periodically checks for tokens expiring within a configured buffer
    and refreshes them before expiry to prevent API call failures.
    """

    def __init__(self):
        """Initialize token refresh worker"""
        self.db_service = get_db_service()
        self.oauth_service = get_oauth_service()
        self.refresh_count = 0
        self.error_count = 0

    def get_expiring_tokens(self) -> List[Dict[str, Any]]:
        """
        Find all tokens expiring within the buffer period.

        Returns:
            List of user/token records requiring refresh
        """
        try:
            now = datetime.utcnow()
            expiry_threshold = now + timedelta(hours=TOKEN_EXPIRY_BUFFER_HOURS)

            # Query database for tokens expiring soon
            expiring = self.db_service.query_tokens(
                provider="google_drive",
                expiry_before=expiry_threshold,
                expiry_after=now,
            )

            logger.info(
                f"Found {len(expiring)} tokens expiring within {TOKEN_EXPIRY_BUFFER_HOURS} hour(s)"
            )
            return expiring

        except Exception as e:
            logger.error(f"Failed to query expiring tokens: {e}", exc_info=True)
            return []

    def refresh_token(self, user_id: str, refresh_token: str) -> bool:
        """
        Refresh an expired or expiring access token.

        Args:
            user_id: User UUID
            refresh_token: OAuth refresh token

        Returns:
            True if refresh successful, False otherwise
        """
        try:
            logger.info(f"Refreshing token for user {user_id}")

            # Decrypt refresh token
            from utils.encryption import get_encryption_service

            encryption_service = get_encryption_service()
            decrypted_refresh = encryption_service.decrypt(refresh_token)

            # Call Google OAuth refresh endpoint
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            # Create temporary credentials object for refresh
            creds = Credentials(
                token=None,
                refresh_token=decrypted_refresh,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.oauth_service.client_id,
                client_secret=self.oauth_service.client_secret,
            )

            # Refresh the token
            request = Request()
            creds.refresh(request)

            # Store refreshed tokens
            new_expiry = datetime.utcnow() + timedelta(seconds=3600)
            if creds.expiry:
                new_expiry = creds.expiry

            success = self.oauth_service.store_tokens(
                user_id=user_id,
                access_token=creds.token,
                refresh_token=creds.refresh_token,
                expiry=new_expiry,
                scopes=list(creds.scopes) if creds.scopes else [],
            )

            if success:
                logger.info(f"Successfully refreshed token for user {user_id}")
                self.refresh_count += 1
            else:
                logger.error(f"Failed to store refreshed tokens for user {user_id}")
                self.error_count += 1

            return success

        except Exception as e:
            logger.error(f"Failed to refresh token for user {user_id}: {e}")
            logger.debug(traceback.format_exc())
            self.error_count += 1
            return False

    def execute(self) -> Dict[str, Any]:
        """
        Execute token refresh for all expiring tokens.

        This is called by the scheduler periodically.

        Returns:
            Dictionary with refresh statistics
        """
        try:
            logger.info("Starting token refresh job")
            start_time = datetime.utcnow()

            # Reset counters
            self.refresh_count = 0
            self.error_count = 0

            # Get expiring tokens
            expiring_tokens = self.get_expiring_tokens()

            if not expiring_tokens:
                logger.info("No tokens requiring refresh")
                return {
                    "status": "success",
                    "refreshed_count": 0,
                    "error_count": 0,
                    "duration_seconds": (
                        datetime.utcnow() - start_time
                    ).total_seconds(),
                }

            # Refresh each token
            for token_record in expiring_tokens:
                user_id = token_record.get("user_id")
                refresh_token = token_record.get("encrypted_refresh_token")

                if not user_id or not refresh_token:
                    logger.warning(f"Invalid token record: {token_record}")
                    continue

                # Attempt refresh with retries
                retry_count = 0
                while retry_count < MAX_RETRIES:
                    if self.refresh_token(user_id, refresh_token):
                        break
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        logger.info(
                            f"Retrying token refresh for user {user_id} (attempt {retry_count + 1}/{MAX_RETRIES})"
                        )

            # Summary
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"Token refresh job completed: {self.refresh_count} refreshed, "
                f"{self.error_count} errors in {duration:.2f}s"
            )

            return {
                "status": "success" if self.error_count == 0 else "partial",
                "refreshed_count": self.refresh_count,
                "error_count": self.error_count,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Token refresh job failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "refreshed_count": self.refresh_count,
                "error_count": self.error_count,
            }


def create_scheduler():
    """
    Create and configure APScheduler for token refresh.

    Usage:
        scheduler = create_scheduler()
        scheduler.start()

    Returns:
        Configured scheduler instance
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler()

        # Create worker instance
        worker = TokenRefreshWorker()

        # Schedule job to run every 15 minutes
        scheduler.add_job(
            worker.execute,
            trigger=IntervalTrigger(minutes=15),
            id="token_refresh_job",
            name="OAuth Token Refresh",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        logger.info("Token refresh scheduler created with 15-minute interval")

        return scheduler

    except ImportError:
        logger.warning(
            "APScheduler not installed. Token refresh requires: pip install apscheduler"
        )
        return None


# Global scheduler instance
_scheduler = None


def get_scheduler():
    """
    Get or create the token refresh scheduler.

    Returns:
        Configured scheduler instance or None if APScheduler unavailable
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler


def start_token_refresh_job():
    """
    Start the token refresh background job.

    Should be called during application startup.
    """
    try:
        scheduler = get_scheduler()
        if scheduler and not scheduler.running:
            scheduler.start()
            logger.info("Token refresh background job started")
        elif scheduler:
            logger.info("Token refresh scheduler already running")
    except Exception as e:
        logger.error(f"Failed to start token refresh job: {e}", exc_info=True)


def stop_token_refresh_job():
    """
    Stop the token refresh background job.

    Should be called during application shutdown.
    """
    try:
        global _scheduler
        if _scheduler and _scheduler.running:
            _scheduler.shutdown()
            logger.info("Token refresh background job stopped")
            _scheduler = None
    except Exception as e:
        logger.error(f"Failed to stop token refresh job: {e}", exc_info=True)


if __name__ == "__main__":
    # Manual test
    logger.info("Testing token refresh worker (manual execution)")
    worker = TokenRefreshWorker()
    result = worker.execute()
    print(f"Result: {result}")
