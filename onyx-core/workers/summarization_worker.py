"""
Summarization Background Worker
Story 4-4: Auto-Summarization Pipeline

This worker processes summarization jobs in the background using BullMQ,
including error handling, retry logic, and metrics tracking.
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncpg
import redis
from bullmq import Queue, Worker, Job
from dataclasses import dataclass

from ..services.summarization.summarizer import SummarizationRequest, SummarizationResult, create_conversation_summarizer
from ..services.summarization.storage import SummaryMemoryStorage

logger = logging.getLogger(__name__)

@dataclass
class WorkerConfig:
    """Configuration for the summarization worker."""
    redis_host: str = "localhost"
    redis_port: int = 6379
    concurrency: int = 2
    max_retries: int = 3
    job_timeout: int = 120  # seconds
    metrics_interval: int = 300  # seconds

class SummarizationWorker:
    """
    Background worker for processing summarization jobs.

    Features:
    - BullMQ job processing with Redis backend
    - Configurable concurrency and retry logic
    - Dead letter queue for failed jobs
    - Comprehensive error handling and logging
    - Performance metrics tracking
    - Graceful shutdown handling
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        redis_client: redis.Redis,
        config: Optional[WorkerConfig] = None
    ):
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.config = config or WorkerConfig()

        # Initialize services
        self.summarizer = create_conversation_summarizer()
        self.storage = SummaryMemoryStorage(db_pool)

        # Initialize BullMQ queue and worker
        self.queue = Queue(
            'summarization',
            {
                'redis': {
                    'host': self.config.redis_host,
                    'port': self.config.redis_port
                },
                'defaultJobOptions': {
                    'attempts': self.config.max_retries,
                    'backoff': 'exponential',
                    'removeOnComplete': 100,
                    'removeOnFail': 50,
                    'jobTimeout': self.config.job_timeout * 1000  # BullMQ uses milliseconds
                }
            }
        )

        self.worker = None
        self.is_running = False
        self.shutdown_event = asyncio.Event()

        # Performance metrics
        self.metrics = {
            'jobs_processed': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'total_processing_time': 0,
            'avg_processing_time': 0,
            'last_job_time': None,
            'start_time': None
        }

        logger.info("SummarizationWorker initialized")

    async def start(self):
        """Start the worker."""
        try:
            if self.is_running:
                logger.warning("Worker is already running")
                return

            self.is_running = True
            self.metrics['start_time'] = datetime.utcnow()

            # Create and start worker
            self.worker = Worker(
                'summarization',
                self._process_job,
                {
                    'redis': {
                        'host': self.config.redis_host,
                        'port': self.config.redis_port
                    },
                    'concurrency': self.config.concurrency
                }
            )

            # Set up event handlers
            self.worker.on('completed', self._on_job_completed)
            self.worker.on('failed', self._on_job_failed)
            self.worker.on('error', self._on_worker_error)

            logger.info(f"SummarizationWorker started with concurrency {self.config.concurrency}")

            # Start metrics reporting task
            asyncio.create_task(self._metrics_reporter())

        except Exception as error:
            logger.error(f"Error starting SummarizationWorker: {error}")
            self.is_running = False
            raise

    async def stop(self):
        """Stop the worker gracefully."""
        try:
            if not self.is_running:
                logger.warning("Worker is not running")
                return

            logger.info("Stopping SummarizationWorker...")
            self.shutdown_event.set()

            if self.worker:
                await self.worker.close()
                self.worker = None

            self.is_running = False
            logger.info("SummarizationWorker stopped")

        except Exception as error:
            logger.error(f"Error stopping SummarizationWorker: {error}")

    async def _process_job(self, job: Job) -> Optional[Dict[str, Any]]:
        """Process a single summarization job."""
        job_id = job.id
        job_data = job.data

        start_time = datetime.utcnow()

        try:
            logger.info(f"Processing summarization job {job_id} for conversation {job_data.get('conversation_id')}")

            # Update job status to processing
            await self._update_job_status(job_id, 'processing')

            # Validate job data
            if not self._validate_job_data(job_data):
                raise ValueError("Invalid job data structure")

            # Create summarization request
            request = SummarizationRequest(
                conversation_id=job_data['conversation_id'],
                message_range=job_data['message_range'],
                user_id=job_data['user_id']
            )

            # Generate summary
            summary_result = await self.summarizer.generate_summary(request)

            # Store summary as memory
            memory_id = await self.storage.store_summary(
                user_id=job_data['user_id'],
                conversation_id=job_data['conversation_id'],
                summary_result=summary_result,
                message_range=job_data['message_range']
            )

            # Track metrics
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await self._track_job_metrics(job_data, summary_result, processing_time, True)

            # Update job status to completed
            await self._update_job_status(job_id, 'completed', started_at=start_time, completed_at=datetime.utcnow())

            self.metrics['jobs_processed'] += 1
            self.metrics['jobs_completed'] += 1
            self.metrics['total_processing_time'] += processing_time
            self.metrics['avg_processing_time'] = self.metrics['total_processing_time'] // self.metrics['jobs_processed']
            self.metrics['last_job_time'] = datetime.utcnow()

            logger.info(f"Job {job_id} completed successfully: "
                       f"{summary_result.summary[:50]}..., "
                       f"processing time: {processing_time}ms")

            return {
                'memory_id': memory_id,
                'summary_length': len(summary_result.summary),
                'topics_count': len(summary_result.key_topics),
                'sentiment': summary_result.sentiment,
                'processing_time': processing_time
            }

        except Exception as error:
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Track failure metrics
            await self._track_job_metrics(job_data, None, processing_time, False, str(error))

            # Update job status to failed
            await self._update_job_status(job_id, 'failed', started_at=start_time, error_message=str(error))

            self.metrics['jobs_processed'] += 1
            self.metrics['jobs_failed'] += 1
            self.metrics['last_job_time'] = datetime.utcnow()

            logger.error(f"Job {job_id} failed: {error}")
            logger.debug(f"Job {job_id} traceback: {traceback.format_exc()}")

            # Let BullMQ handle retry logic
            raise error

    def _validate_job_data(self, job_data: Dict[str, Any]) -> bool:
        """Validate that job data contains all required fields."""
        required_fields = ['conversation_id', 'user_id', 'message_range', 'message_count']

        for field in required_fields:
            if field not in job_data:
                logger.error(f"Missing required field in job data: {field}")
                return False

        # Validate message_range
        message_range = job_data['message_range']
        if not isinstance(message_range, dict) or 'start' not in message_range or 'end' not in message_range:
            logger.error("Invalid message_range in job data")
            return False

        return True

    async def _update_job_status(
        self,
        job_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ):
        """Update job status in database."""
        try:
            async with self.db_pool.acquire() as conn:
                if status == 'processing':
                    await conn.execute(
                        """
                        UPDATE summarization_job_tracking
                        SET status = $1, started_at = $2, updated_at = NOW()
                        WHERE job_id = $3
                        """,
                        status, started_at or datetime.utcnow(), job_id
                    )
                elif status == 'completed':
                    await conn.execute(
                        """
                        UPDATE summarization_job_tracking
                        SET status = $1, completed_at = $2, updated_at = NOW()
                        WHERE job_id = $3
                        """,
                        status, completed_at or datetime.utcnow(), job_id
                    )
                elif status == 'failed':
                    await conn.execute(
                        """
                        UPDATE summarization_job_tracking
                        SET status = $1, error_message = $2, updated_at = NOW()
                        WHERE job_id = $3
                        """,
                        status, error_message, job_id
                    )
        except Exception as error:
            logger.error(f"Error updating job status for {job_id}: {error}")

    async def _track_job_metrics(
        self,
        job_data: Dict[str, Any],
        summary_result: Optional[SummarizationResult],
        processing_time: int,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Track job performance metrics."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO summarization_metrics
                    (conversation_id, user_id, processing_time, success, error_message,
                     message_range_start, message_range_end, summary_length, topics_count,
                     sentiment_score, model_version, prompt_version)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                    job_data['conversation_id'],
                    job_data['user_id'],
                    processing_time,
                    success,
                    error_message,
                    job_data['message_range']['start'],
                    job_data['message_range']['end'],
                    len(summary_result.summary) if summary_result else None,
                    len(summary_result.key_topics) if summary_result else None,
                    summary_result.sentiment if summary_result else None,
                    summary_result.model if summary_result else None,
                    summary_result.prompt_version if summary_result else None
                )
        except Exception as error:
            logger.error(f"Error tracking job metrics: {error}")

    async def _on_job_completed(self, job: Job, result: Any):
        """Handler for job completion events."""
        logger.info(f"Job {job.id} completed successfully")

    async def _on_job_failed(self, job: Job, error: Exception):
        """Handler for job failure events."""
        logger.error(f"Job {job.id} failed: {error}")

        # Check if this is a permanent failure (max retries reached)
        if job.opts.attemptsMade >= job.opts.attempts:
            logger.error(f"Job {job.id} failed permanently for conversation {job.data.get('conversation_id')}")
            # In production, you might want to send an alert here

    async def _on_worker_error(self, error: Exception):
        """Handler for worker error events."""
        logger.error(f"Worker error: {error}")

    async def _metrics_reporter(self):
        """Periodically report worker metrics."""
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.metrics_interval)

                if not self.is_running:
                    break

                metrics = await self.get_metrics()
                logger.info(f"Worker metrics: {metrics}")

            except asyncio.CancelledError:
                break
            except Exception as error:
                logger.error(f"Error in metrics reporter: {error}")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get worker performance metrics."""
        try:
            # Get queue metrics
            waiting = await self.queue.getWaiting()
            active = await self.queue.getActive()
            completed = await self.queue.getCompleted()
            failed = await self.queue.getFailed()

            # Calculate success rate
            total_jobs = self.metrics['jobs_processed']
            success_rate = (self.metrics['jobs_completed'] / total_jobs * 100) if total_jobs > 0 else 0

            # Calculate uptime
            uptime_seconds = 0
            if self.metrics['start_time']:
                uptime_seconds = int((datetime.utcnow() - self.metrics['start_time']).total_seconds())

            return {
                'worker': {
                    'is_running': self.is_running,
                    'uptime_seconds': uptime_seconds,
                    'jobs_processed': self.metrics['jobs_processed'],
                    'jobs_completed': self.metrics['jobs_completed'],
                    'jobs_failed': self.metrics['jobs_failed'],
                    'success_rate': round(success_rate, 2),
                    'avg_processing_time': self.metrics['avg_processing_time'],
                    'last_job_time': self.metrics['last_job_time'].isoformat() if self.metrics['last_job_time'] else None
                },
                'queue': {
                    'waiting': len(waiting),
                    'active': len(active),
                    'completed': len(completed),
                    'failed': len(failed)
                },
                'updated_at': datetime.utcnow().isoformat()
            }

        except Exception as error:
            logger.error(f"Error getting worker metrics: {error}")
            return {'error': str(error), 'updated_at': datetime.utcnow().isoformat()}

    async def cleanup_old_records(self, days_to_keep: int = 30):
        """Clean up old records."""
        try:
            async with self.db_pool.acquire() as conn:
                # Clean up old job tracking records
                result = await conn.execute(
                    """
                    DELETE FROM summarization_job_tracking
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    """,
                    days_to_keep
                )
                deleted_tracking = int(result.split()[-1]) if result else 0

                # Clean up old metrics (this uses the function we created in the migration)
                deleted_metrics = await conn.fetchval(
                    "SELECT cleanup_old_summarization_metrics($1)",
                    days_to_keep
                ) or 0

                logger.info(f"Cleaned up {deleted_tracking} old job tracking records and {deleted_metrics} old metrics")
                return deleted_tracking + deleted_metrics

        except Exception as error:
            logger.error(f"Error cleaning up old records: {error}")
            return 0


# Factory function for easy instantiation
def create_summarization_worker(
    db_pool: asyncpg.Pool,
    redis_client: redis.Redis,
    config: Optional[WorkerConfig] = None
) -> SummarizationWorker:
    """Create and initialize SummarizationWorker."""
    return SummarizationWorker(db_pool, redis_client, config)