"""
Sync Scheduler Service

This module handles scheduled synchronization jobs for Google Drive.
Uses APScheduler for cron-like job scheduling.
"""

import asyncio
from typing import Optional
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from services.google_drive_sync import sync_google_drive
from utils.database import get_db_service

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Service for scheduling Google Drive sync jobs"""

    def __init__(self):
        """Initialize sync scheduler"""
        self.scheduler = AsyncIOScheduler()
        self.db_service = get_db_service()
        self.running = False

    def start(self):
        """Start the scheduler"""
        if not self.running:
            self.scheduler.start()
            self.running = True
            logger.info("Sync scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.running:
            self.scheduler.shutdown(wait=True)
            self.running = False
            logger.info("Sync scheduler stopped")

    def schedule_user_sync(
        self, user_id: str, interval_minutes: int = 10, immediate: bool = False
    ):
        """
        Schedule periodic sync for a user

        Args:
            user_id: User UUID
            interval_minutes: Sync interval in minutes (default: 10)
            immediate: If True, run sync immediately then schedule
        """
        job_id = f"sync-{user_id}"

        # Remove existing job if any
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed existing sync job for user {user_id}")

        # Add new job with cron trigger (every N minutes)
        self.scheduler.add_job(
            func=self._run_sync_job,
            trigger=CronTrigger(minute=f"*/{interval_minutes}"),
            args=[user_id],
            id=job_id,
            name=f"Google Drive sync for user {user_id}",
            replace_existing=True,
            max_instances=1,  # Prevent overlapping jobs
            coalesce=True,  # Combine missed runs
        )

        logger.info(
            f"Scheduled sync for user {user_id} every {interval_minutes} minutes (job_id: {job_id})"
        )

        # Run immediately if requested
        if immediate:
            asyncio.create_task(self._run_sync_job(user_id))

    def unschedule_user_sync(self, user_id: str):
        """
        Unschedule sync for a user

        Args:
            user_id: User UUID
        """
        job_id = f"sync-{user_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled sync for user {user_id}")

    async def trigger_manual_sync(
        self, user_id: str, full_sync: bool = False
    ) -> Optional[str]:
        """
        Trigger a manual sync job

        Args:
            user_id: User UUID
            full_sync: If True, perform full sync

        Returns:
            Job ID if successful
        """
        try:
            # Create sync job record
            job_id = self.db_service.create_sync_job(user_id, source_type="google_drive")

            if not job_id:
                logger.error(f"Failed to create sync job for user {user_id}")
                return None

            # Update job status to running
            self.db_service.update_sync_job(job_id, status="running")

            # Run sync in background
            asyncio.create_task(self._run_manual_sync(user_id, job_id, full_sync))

            logger.info(f"Triggered manual sync for user {user_id} (job_id: {job_id})")
            return job_id

        except Exception as e:
            logger.error(f"Failed to trigger manual sync: {e}")
            return None

    async def _run_sync_job(self, user_id: str):
        """
        Run scheduled sync job for a user

        Args:
            user_id: User UUID
        """
        try:
            logger.info(f"Running scheduled sync for user {user_id}")

            # Create sync job record
            job_id = self.db_service.create_sync_job(user_id, source_type="google_drive")

            if not job_id:
                logger.error(f"Failed to create sync job record for user {user_id}")
                return

            # Update status to running
            self.db_service.update_sync_job(job_id, status="running")

            # Run sync (incremental by default)
            stats = await sync_google_drive(user_id, full_sync=False)

            # Update job with results
            error_rate = (
                stats["files_failed"] / max(stats["files_processed"], 1)
                if stats["files_processed"] > 0
                else 0
            )

            if error_rate < 0.02:  # Success if error rate < 2%
                self.db_service.update_sync_job(
                    job_id,
                    status="success",
                    documents_synced=stats["files_indexed"] + stats["files_updated"],
                    documents_failed=stats["files_failed"],
                )
                logger.info(
                    f"Sync completed successfully for user {user_id}: {stats['files_indexed']} indexed, {stats['files_updated']} updated"
                )
            else:
                # High error rate
                error_message = f"Error rate {error_rate:.2%} exceeds threshold"
                self.db_service.update_sync_job(
                    job_id,
                    status="failed",
                    documents_synced=stats["files_indexed"] + stats["files_updated"],
                    documents_failed=stats["files_failed"],
                    error_message=error_message,
                    error_details={"errors": stats["errors"]},
                )
                logger.warning(f"Sync completed with high error rate for user {user_id}: {error_rate:.2%}")

        except Exception as e:
            logger.error(f"Sync job failed for user {user_id}: {e}")
            if job_id:
                self.db_service.update_sync_job(
                    job_id,
                    status="failed",
                    error_message=str(e),
                )

    async def _run_manual_sync(self, user_id: str, job_id: str, full_sync: bool):
        """
        Run manual sync job

        Args:
            user_id: User UUID
            job_id: Sync job ID
            full_sync: If True, perform full sync
        """
        try:
            logger.info(f"Running manual sync for user {user_id} (full_sync={full_sync})")

            # Run sync
            stats = await sync_google_drive(user_id, full_sync=full_sync)

            # Calculate error rate
            error_rate = (
                stats["files_failed"] / max(stats["files_processed"], 1)
                if stats["files_processed"] > 0
                else 0
            )

            # Update job status
            if error_rate < 0.02:
                self.db_service.update_sync_job(
                    job_id,
                    status="success",
                    documents_synced=stats["files_indexed"] + stats["files_updated"],
                    documents_failed=stats["files_failed"],
                )
            else:
                self.db_service.update_sync_job(
                    job_id,
                    status="failed",
                    documents_synced=stats["files_indexed"] + stats["files_updated"],
                    documents_failed=stats["files_failed"],
                    error_message=f"Error rate {error_rate:.2%} exceeds threshold",
                    error_details={"errors": stats["errors"]},
                )

        except Exception as e:
            logger.error(f"Manual sync failed for user {user_id}: {e}")
            self.db_service.update_sync_job(
                job_id,
                status="failed",
                error_message=str(e),
            )

    def get_scheduled_jobs(self) -> list:
        """Get list of scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "job_id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs


# Global scheduler instance
_scheduler = None


def get_scheduler() -> SyncScheduler:
    """Get or create scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SyncScheduler()
    return _scheduler


async def start_scheduler():
    """Start the global scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("Global sync scheduler started")


async def stop_scheduler():
    """Stop the global scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
    logger.info("Global sync scheduler stopped")
