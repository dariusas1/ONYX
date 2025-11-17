"""
Summarization Background Worker for ONYX

This worker processes summarization jobs from the queue using Redis,
generates conversation summaries, and stores them in the database.

Story 4-4: Auto-Summarization Pipeline
"""

import os
import json
import asyncio
import signal
import sys
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from services.summarization_trigger_service import get_summarization_trigger_service, SummarizationJob
from services.conversation_summarizer import get_conversation_summarizer, SummarizationRequest
from services.summary_memory_storage import get_summary_memory_storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/summarization_worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class SummarizationWorker:
    """Background worker for processing summarization jobs"""

    def __init__(self):
        """Initialize summarization worker"""
        self.trigger_service = get_summarization_trigger_service()
        self.summarizer = get_conversation_summarizer()
        self.storage_service = get_summary_memory_storage()
        self.running = False
        self.worker_id = f"worker-{os.getpid()}-{int(time.time())}"
        self.max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_SUMMARIZATION_JOBS", "2"))
        self.job_timeout = int(os.getenv("SUMMARIZATION_JOB_TIMEOUT_SECONDS", "120"))
        self.health_check_interval = int(os.getenv("WORKER_HEALTH_CHECK_INTERVAL", "60"))
        self.metrics_interval = int(os.getenv("WORKER_METRICS_INTERVAL", "300"))

        # Statistics
        self.stats = {
            "jobs_processed": 0,
            "jobs_successful": 0,
            "jobs_failed": 0,
            "total_processing_time_ms": 0,
            "start_time": time.time(),
            "last_job_time": None
        }

    async def start(self):
        """Start the worker process"""
        logger.info(f"Starting summarization worker {self.worker_id}")

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.running = True

        # Start background tasks
        tasks = [
            asyncio.create_task(self._job_processing_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._metrics_reporting_loop())
        ]

        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            await self._shutdown()

    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping summarization worker {self.worker_id}")
        self.running = False

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully")
        asyncio.create_task(self.stop())

    async def _job_processing_loop(self):
        """Main loop for processing jobs"""
        logger.info("Job processing loop started")

        while self.running:
            try:
                # Get next job from queue (blocking with timeout)
                job = await self.trigger_service.get_next_job(timeout=30)

                if job:
                    await self._process_job_with_timeout(job)
                else:
                    # No job available, brief sleep
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in job processing loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _process_job_with_timeout(self, job: SummarizationJob):
        """Process a job with timeout"""
        try:
            # Process job with timeout
            await asyncio.wait_for(
                self._process_single_job(job),
                timeout=self.job_timeout
            )
        except asyncio.TimeoutError:
            error_msg = f"Job processing timeout after {self.job_timeout}s"
            logger.error(f"{error_msg} for conversation {job.conversation_id}")
            await self._handle_job_failure(job, error_msg)
        except Exception as e:
            error_msg = f"Job processing error: {str(e)}"
            logger.error(f"{error_msg} for conversation {job.conversation_id}")
            await self._handle_job_failure(job, error_msg)

    async def _process_single_job(self, job: SummarizationJob):
        """Process a single summarization job"""
        job_start_time = time.time()

        try:
            logger.info(
                f"Processing summarization job for conversation {job.conversation_id}, "
                f"messages {job.message_range['start']}-{job.message_range['end']}"
            )

            # Create summarization request
            request = SummarizationRequest(
                conversation_id=job.conversation_id,
                message_range=job.message_range,
                user_id=job.user_id,
                max_summary_length=300,
                min_summary_length=20,
                temperature=0.3,
                max_tokens=150
            )

            # Generate summary
            result = await self.summarizer.generate_summary(request)

            # Store summary and create memory
            memory_id = await self.storage_service.store_summary(
                user_id=job.user_id,
                conversation_id=job.conversation_id,
                result=result,
                message_range=job.message_range
            )

            processing_time = int((time.time() - job_start_time) * 1000)

            # Update statistics
            self.stats["jobs_processed"] += 1
            self.stats["jobs_successful"] += 1
            self.stats["total_processing_time_ms"] += processing_time
            self.stats["last_job_time"] = time.time()

            # Log success
            logger.info(
                f"Successfully processed job for conversation {job.conversation_id}: "
                f"summary_id={memory_id}, processing_time={processing_time}ms"
            )

            # Mark job as completed
            await self.trigger_service.complete_job(job, True)

            # Track detailed metrics
            await self._track_job_metrics(job, result, processing_time, True)

        except Exception as e:
            processing_time = int((time.time() - job_start_time) * 1000)
            error_msg = str(e)

            logger.error(f"Failed to process job for conversation {job.conversation_id}: {error_msg}")

            # Mark job as failed
            await self.trigger_service.complete_job(job, False, error_msg)

            # Track failure metrics
            await self._track_job_metrics(job, None, processing_time, False, error_msg)

            # Update statistics
            self.stats["jobs_processed"] += 1
            self.stats["jobs_failed"] += 1
            self.stats["total_processing_time_ms"] += processing_time

    async def _handle_job_failure(self, job: SummarizationJob, error_message: str):
        """Handle job failure"""
        try:
            # Mark job as failed
            await self.trigger_service.complete_job(job, False, error_message)

            # Update statistics
            self.stats["jobs_processed"] += 1
            self.stats["jobs_failed"] += 1

        except Exception as e:
            logger.error(f"Error handling job failure: {e}")

    async def _track_job_metrics(
        self,
        job: SummarizationJob,
        result: Optional[Any],
        processing_time_ms: int,
        success: bool,
        error_message: str = None
    ):
        """Track detailed job metrics"""
        try:
            from services.summarization_trigger_service import get_summarization_trigger_service

            trigger_service = get_summarization_trigger_service()

            # Additional metrics can be tracked here
            if success and result:
                logger.info(
                    f"Job metrics - conversation: {job.conversation_id}, "
                    f"summary_length: {len(result.summary)}, "
                    f"topics: {len(result.key_topics)}, "
                    f"sentiment: {result.sentiment:.2f}, "
                    f"confidence: {result.confidence:.2f}, "
                    f"processing_time: {processing_time_ms}ms"
                )

        except Exception as e:
            logger.error(f"Error tracking job metrics: {e}")

    async def _health_check_loop(self):
        """Periodic health check and reporting"""
        logger.info("Health check loop started")

        while self.running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)

    async def _perform_health_check(self):
        """Perform worker health check"""
        try:
            uptime = time.time() - self.stats["start_time"]
            avg_processing_time = (
                self.stats["total_processing_time_ms"] / max(self.stats["jobs_processed"], 1)
            )
            success_rate = (
                (self.stats["jobs_successful"] / max(self.stats["jobs_processed"], 1)) * 100
            )

            health_status = {
                "worker_id": self.worker_id,
                "status": "healthy",
                "uptime_seconds": uptime,
                "jobs_processed": self.stats["jobs_processed"],
                "jobs_successful": self.stats["jobs_successful"],
                "jobs_failed": self.stats["jobs_failed"],
                "success_rate_percent": success_rate,
                "avg_processing_time_ms": avg_processing_time,
                "last_job_time": self.stats["last_job_time"]
            }

            logger.info(f"Worker health check: {json.dumps(health_status)}")

            # Log warnings for unhealthy conditions
            if success_rate < 90 and self.stats["jobs_processed"] > 10:
                logger.warning(f"Low success rate: {success_rate:.1f}%")

            if avg_processing_time > 5000:  # 5 seconds
                logger.warning(f"High average processing time: {avg_processing_time:.0f}ms")

        except Exception as e:
            logger.error(f"Health check failed: {e}")

    async def _metrics_reporting_loop(self):
        """Periodic detailed metrics reporting"""
        logger.info("Metrics reporting loop started")

        while self.running:
            try:
                await self._report_detailed_metrics()
                await asyncio.sleep(self.metrics_interval)
            except Exception as e:
                logger.error(f"Error in metrics reporting loop: {e}")
                await asyncio.sleep(self.metrics_interval)

    async def _report_detailed_metrics(self):
        """Report detailed worker and service metrics"""
        try:
            # Get service metrics
            queue_status = await self.trigger_service.get_queue_status()
            summarizer_metrics = await self.summarizer.get_service_metrics()
            storage_metrics = await self.storage_service.get_service_metrics()

            # Worker metrics
            uptime = time.time() - self.stats["start_time"]
            jobs_per_hour = (self.stats["jobs_processed"] / max(uptime / 3600, 1))

            detailed_metrics = {
                "worker_id": self.worker_id,
                "timestamp": datetime.utcnow().isoformat(),
                "worker": {
                    "uptime_seconds": uptime,
                    "jobs_processed": self.stats["jobs_processed"],
                    "jobs_successful": self.stats["jobs_successful"],
                    "jobs_failed": self.stats["jobs_failed"],
                    "jobs_per_hour": jobs_per_hour,
                    "success_rate_percent": (
                        (self.stats["jobs_successful"] / max(self.stats["jobs_processed"], 1)) * 100
                    )
                },
                "queue_status": queue_status,
                "summarizer_metrics": summarizer_metrics,
                "storage_metrics": storage_metrics
            }

            logger.info(f"Detailed metrics: {json.dumps(detailed_metrics, indent=2)}")

        except Exception as e:
            logger.error(f"Failed to report detailed metrics: {e}")

    async def _shutdown(self):
        """Clean shutdown of worker"""
        logger.info(f"Shutting down worker {self.worker_id}")

        # Report final statistics
        uptime = time.time() - self.stats["start_time"]
        logger.info(
            f"Worker {self.worker_id} final stats: "
            f"uptime={uptime:.1f}s, "
            f"jobs_processed={self.stats['jobs_processed']}, "
            f"jobs_successful={self.stats['jobs_successful']}, "
            f"jobs_failed={self.stats['jobs_failed']}"
        )

        # Clean up resources
        self.running = False


async def main():
    """Main entry point for the worker"""
    worker = SummarizationWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())