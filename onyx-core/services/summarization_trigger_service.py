"""
Summarization Trigger Service for ONYX

This service monitors conversation message counts and triggers
auto-summarization pipeline every N messages (default: 10).

Story 4-4: Auto-Summarization Pipeline
"""

import os
import json
import time
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SummarizationTrigger:
    """Summarization trigger event data"""
    conversation_id: str
    message_id: str
    message_count: int
    user_id: str
    trigger_interval: int = 10


@dataclass
class SummarizationJob:
    """Background job data for summarization"""
    conversation_id: str
    message_id: str
    message_count: int
    user_id: str
    message_range: Dict[str, int]
    trigger_interval: int
    retry_count: int = 0
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class SummarizationTriggerService:
    """Service for detecting summarization triggers and queuing background jobs"""

    def __init__(self):
        """Initialize summarization trigger service"""
        self.connection_string = self._build_connection_string()
        self.redis_client = self._init_redis_client()
        self.trigger_interval = int(os.getenv("SUMMARIZATION_TRIGGER_INTERVAL", "10"))
        self.job_queue_key = "summarization:jobs"
        self.processing_key_prefix = "summarization:processing:"
        self.cooldown_period = int(os.getenv("SUMMARIZATION_COOLDOWN_SECONDS", "60"))

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "manus")
        user = os.getenv("POSTGRES_USER", "manus")
        password = os.getenv("POSTGRES_PASSWORD", "")
        return f"host={host} port={port} dbname={database} user={user} password={password}"

    def _init_redis_client(self):
        """Initialize Redis client for job queuing"""
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_password = os.getenv("REDIS_PASSWORD", None)

            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # Test connection
            client.ping()
            logger.info("Redis connection established for summarization service")
            return client

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)

    # =========================================================================
    # Trigger Detection Methods
    # =========================================================================

    async def should_trigger_summarization(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str
    ) -> Optional[SummarizationTrigger]:
        """
        Check if summarization should be triggered for this conversation

        Args:
            conversation_id: Conversation UUID
            message_id: Current message UUID
            user_id: User UUID

        Returns:
            SummarizationTrigger if should trigger, None otherwise
        """
        try:
            # Check if already processing this conversation
            processing_key = f"{self.processing_key_prefix}{conversation_id}"
            if self.redis_client.exists(processing_key):
                logger.debug(f"Summarization already in progress for conversation {conversation_id}")
                return None

            # Get message count for conversation
            message_count = await self._get_conversation_message_count(conversation_id)
            if message_count == 0:
                return None

            # Check if message count reaches trigger interval
            if message_count % self.trigger_interval == 0:
                # Check cooldown period to avoid too frequent summarizations
                last_summary_time = await self._get_last_summary_time(conversation_id)
                if last_summary_time and (time.time() - last_summary_time) < self.cooldown_period:
                    logger.debug(f"Summarization in cooldown period for conversation {conversation_id}")
                    return None

                return SummarizationTrigger(
                    conversation_id=conversation_id,
                    message_id=message_id,
                    message_count=message_count,
                    user_id=user_id,
                    trigger_interval=self.trigger_interval
                )

            return None

        except Exception as e:
            logger.error(f"Error checking summarization trigger for conversation {conversation_id}: {e}")
            return None

    async def process_trigger(self, trigger: SummarizationTrigger) -> bool:
        """
        Process a summarization trigger by queueing background job

        Args:
            trigger: SummarizationTrigger object

        Returns:
            True if job queued successfully, False otherwise
        """
        try:
            # Mark conversation as processing
            processing_key = f"{self.processing_key_prefix}{trigger.conversation_id}"
            self.redis_client.setex(processing_key, self.cooldown_period, "1")

            # Calculate message range for summarization (last 10 messages)
            message_range = {
                "start": max(1, trigger.message_count - self.trigger_interval + 1),
                "end": trigger.message_count
            }

            # Create job data
            job = SummarizationJob(
                conversation_id=trigger.conversation_id,
                message_id=trigger.message_id,
                message_count=trigger.message_count,
                user_id=trigger.user_id,
                message_range=message_range,
                trigger_interval=self.trigger_interval
            )

            # Queue job with priority based on conversation activity
            priority = self._calculate_job_priority(trigger)
            job_data = json.dumps(job.__dict__)

            # Add to Redis queue (using list as simple queue)
            self.redis_client.lpush(self.job_queue_key, job_data)

            # Log queuing event
            logger.info(
                f"Summarization job queued for conversation {trigger.conversation_id}, "
                f"messages {message_range['start']}-{message_range['end']}, "
                f"priority: {priority}"
            )

            # Track metrics
            await self._track_trigger_event(trigger, "job_queued", priority)
            return True

        except Exception as e:
            logger.error(f"Error processing summarization trigger: {e}")
            # Clear processing flag on error
            processing_key = f"{self.processing_key_prefix}{trigger.conversation_id}"
            self.redis_client.delete(processing_key)

            # Track failure
            await self._track_trigger_event(trigger, "job_queue_failed", 0, str(e))
            return False

    # =========================================================================
    # Background Job Processing Methods
    # =========================================================================

    async def get_next_job(self, timeout: int = 30) -> Optional[SummarizationJob]:
        """
        Get next summarization job from queue

        Args:
            timeout: Timeout in seconds for blocking pop

        Returns:
            SummarizationJob or None if no job available
        """
        try:
            # Use BRPOP for blocking job retrieval
            result = self.redis_client.brpop(self.job_queue_key, timeout)

            if result:
                _, job_data = result
                job_dict = json.loads(job_data)

                # Convert timestamps
                if 'created_at' in job_dict:
                    job_dict['created_at'] = job_dict['created_at']

                job = SummarizationJob(**job_dict)
                logger.debug(f"Retrieved summarization job for conversation {job.conversation_id}")
                return job

            return None

        except Exception as e:
            logger.error(f"Error getting next summarization job: {e}")
            return None

    async def complete_job(self, job: SummarizationJob, success: bool, error_message: str = None):
        """
        Mark a job as completed and clear processing flag

        Args:
            job: Completed SummarizationJob
            success: Whether job succeeded
            error_message: Error message if job failed
        """
        try:
            # Clear processing flag
            processing_key = f"{self.processing_key_prefix}{job.conversation_id}"
            self.redis_client.delete(processing_key)

            # Track completion metrics
            await self._track_job_completion(job, success, error_message)

            if success:
                logger.info(f"Summarization job completed for conversation {job.conversation_id}")
            else:
                logger.error(f"Summarization job failed for conversation {job.conversation_id}: {error_message}")

        except Exception as e:
            logger.error(f"Error completing summarization job: {e}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_conversation_message_count(self, conversation_id: str) -> int:
        """Get total message count for conversation"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM messages WHERE conversation_id = %s",
                    (conversation_id,)
                )
                result = cur.fetchone()
                return result[0] if result else 0

        except Exception as e:
            logger.error(f"Error getting message count for conversation {conversation_id}: {e}")
            return 0
        finally:
            if 'conn' in locals():
                conn.close()

    async def _get_last_summary_time(self, conversation_id: str) -> Optional[float]:
        """Get timestamp of last summary for conversation"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXTRACT(EPOCH FROM created_at) as timestamp
                    FROM conversation_summaries
                    WHERE conversation_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (conversation_id,)
                )
                result = cur.fetchone()
                return float(result[0]) if result and result[0] else None

        except Exception as e:
            logger.error(f"Error getting last summary time for conversation {conversation_id}: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def _calculate_job_priority(self, trigger: SummarizationTrigger) -> int:
        """Calculate job priority based on conversation activity"""
        # Higher priority for recent conversations with more messages
        base_priority = 10

        # Add priority based on message count (more active = higher priority)
        activity_bonus = min(trigger.message_count // 50, 5)

        return base_priority + activity_bonus

    async def _track_trigger_event(
        self,
        trigger: SummarizationTrigger,
        event_type: str,
        priority: int,
        error_message: str = None
    ):
        """Track trigger events for analytics"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO summarization_trigger_logs
                    (conversation_id, user_id, message_count, event_type, priority, error_message, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (trigger.conversation_id, trigger.user_id, trigger.message_count,
                     event_type, priority, error_message)
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to track trigger event: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    async def _track_job_completion(
        self,
        job: SummarizationJob,
        success: bool,
        error_message: str = None
    ):
        """Track job completion for analytics"""
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                processing_time = None
                if job.created_at:
                    created_time = datetime.fromisoformat(job.created_at.replace('Z', '+00:00'))
                    processing_time = int((datetime.utcnow() - created_time).total_seconds() * 1000)

                cur.execute(
                    """
                    INSERT INTO summarization_metrics
                    (conversation_id, user_id, processing_time_ms, success, error_message, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (job.conversation_id, job.user_id, processing_time, success, error_message)
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to track job completion: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    # =========================================================================
    # Monitoring and Management Methods
    # =========================================================================

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and metrics"""
        try:
            queue_length = self.redis_client.llen(self.job_queue_key)
            processing_count = len(self.redis_client.keys(f"{self.processing_key_prefix}*"))

            # Get recent metrics from database
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_jobs,
                        AVG(processing_time_ms) as avg_processing_time,
                        COUNT(CASE WHEN success = TRUE THEN 1 END) as successful_jobs,
                        COUNT(CASE WHEN success = FALSE THEN 1 END) as failed_jobs
                    FROM summarization_metrics
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    """
                )
                metrics = cur.fetchone()

            return {
                "queue_length": queue_length,
                "processing_count": processing_count,
                "trigger_interval": self.trigger_interval,
                "cooldown_period": self.cooldown_period,
                "last_24_hours": {
                    "total_jobs": metrics['total_jobs'],
                    "avg_processing_time_ms": float(metrics['avg_processing_time'] or 0),
                    "successful_jobs": metrics['successful_jobs'],
                    "failed_jobs": metrics['failed_jobs'],
                    "success_rate": (metrics['successful_jobs'] / metrics['total_jobs'] * 100) if metrics['total_jobs'] > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {"error": str(e)}
        finally:
            if 'conn' in locals():
                conn.close()

    async def clear_processing_flags(self):
        """Clear all processing flags (useful for recovery)"""
        try:
            keys = self.redis_client.keys(f"{self.processing_key_prefix}*")
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} processing flags")

            return len(keys) if keys else 0

        except Exception as e:
            logger.error(f"Error clearing processing flags: {e}")
            return 0


# Global service instance
_summarization_trigger_service = None


def get_summarization_trigger_service() -> SummarizationTriggerService:
    """Get or create summarization trigger service instance"""
    global _summarization_trigger_service
    if _summarization_trigger_service is None:
        _summarization_trigger_service = SummarizationTriggerService()
    return _summarization_trigger_service