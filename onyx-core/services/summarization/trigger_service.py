"""
Summarization Trigger Service
Story 4-4: Auto-Summarization Pipeline

This service detects when summarization should be triggered (every 10 messages)
and queues background jobs for processing.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import redis
from bullmq import Queue, Worker
import asyncpg
from dataclasses import dataclass

from .config import config

logger = logging.getLogger(__name__)

@dataclass
class SummarizationTrigger:
    """Data structure for summarization trigger information"""
    conversation_id: str
    message_id: str
    message_count: int
    user_id: str
    created_at: datetime

@dataclass
class SummarizationJob:
    """Data structure for summarization background job"""
    conversation_id: str
    message_id: str
    user_id: str
    message_count: int
    message_range: Dict[str, int]
    retry_count: int = 0
    priority: int = 5

class SummarizationTriggerService:
    """
    Service responsible for detecting summarization triggers and queuing background jobs.

    Features:
    - Message count monitoring per conversation
    - Configurable trigger intervals (default: 10 messages)
    - Background job queuing with BullMQ
    - Error handling and retry logic
    - Performance monitoring and alerting
    - Duplicate trigger prevention
    """

    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.TRIGGER_INTERVAL = config.TRIGGER_INTERVAL

        # Initialize BullMQ queue
        queue_config = config.get_queue_config()
        redis_config = config.get_redis_config()

        self.summarization_queue = Queue(
            'summarization',
            {
                'redis': {
                    'host': redis_client.connection_pool.connection_kwargs.get('host', redis_config['host']),
                    'port': redis_client.connection_pool.connection_kwargs.get('port', redis_config['port'])
                },
                'defaultJobOptions': {
                    'attempts': queue_config['attempts'],
                    'backoff': queue_config['backoff'],
                    'removeOnComplete': queue_config['removeOnComplete'],
                    'removeOnFail': queue_config['removeOnFail'],
                    'delay': queue_config['delay']
                }
            }
        )

        # Performance metrics
        self.metrics = {
            'triggers_detected': 0,
            'jobs_queued': 0,
            'duplicate_prevented': 0,
            'errors': 0
        }

        logger.info("SummarizationTriggerService initialized")

    async def should_trigger(self, conversation_id: str) -> Optional[SummarizationTrigger]:
        """
        Check if summarization should be triggered for a conversation.

        Args:
            conversation_id: The conversation ID to check

        Returns:
            SummarizationTrigger if trigger should occur, None otherwise
        """
        try:
            # Get message count for conversation
            message_count = await self._get_message_count(conversation_id)

            if message_count > 0 and message_count % self.TRIGGER_INTERVAL == 0:
                # Check if we already have a pending job for this trigger
                if await self._is_duplicate_trigger(conversation_id, message_count):
                    self.metrics['duplicate_prevented'] += 1
                    logger.info(f"Duplicate trigger prevented for conversation {conversation_id} at message {message_count}")
                    return None

                # Get latest message for context
                latest_message = await self._get_latest_message(conversation_id)
                if not latest_message:
                    logger.warning(f"No latest message found for conversation {conversation_id}")
                    return None

                trigger = SummarizationTrigger(
                    conversation_id=conversation_id,
                    message_id=latest_message['id'],
                    message_count=message_count,
                    user_id=latest_message['user_id'],
                    created_at=datetime.utcnow()
                )

                self.metrics['triggers_detected'] += 1
                logger.info(f"Summarization trigger detected for conversation {conversation_id} at message {message_count}")
                return trigger

            return None

        except Exception as error:
            self.metrics['errors'] += 1
            logger.error(f"Error checking summarization trigger for conversation {conversation_id}: {error}")
            return None

    async def process_trigger(self, trigger: SummarizationTrigger) -> bool:
        """
        Process a summarization trigger by queuing a background job.

        Args:
            trigger: The summarization trigger to process

        Returns:
            True if job was successfully queued, False otherwise
        """
        try:
            # Calculate message range for summarization (last 10 messages)
            message_range = {
                'start': trigger.message_count - 9,  # Last 10 messages
                'end': trigger.message_count
            }

            # Calculate job priority based on conversation recency
            priority = self._calculate_priority(trigger)

            # Create job data
            job_data = {
                'conversation_id': trigger.conversation_id,
                'message_id': trigger.message_id,
                'user_id': trigger.user_id,
                'message_count': trigger.message_count,
                'message_range': message_range,
                'created_at': trigger.created_at.isoformat(),
                'retry_count': 0
            }

            # Queue background job
            job = await self.summarization_queue.add(
                'summarize-conversation',
                job_data,
                {
                    'priority': priority,
                    'delay': 1000,  # 1 second delay to ensure message is fully processed
                    'removeOnComplete': 100,
                    'removeOnFail': 50
                }
            )

            # Track job in database
            await self._track_job(trigger, job.id, 'queued')

            self.metrics['jobs_queued'] += 1
            logger.info(f"Summarization job {job.id} queued for conversation {trigger.conversation_id}")

            return True

        except Exception as error:
            self.metrics['errors'] += 1
            logger.error(f"Error processing summarization trigger for conversation {trigger.conversation_id}: {error}")
            return False

    async def _get_message_count(self, conversation_id: str) -> int:
        """Get the total message count for a conversation."""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM messages
                    WHERE conversation_id = $1
                    AND role IN ('user', 'assistant')
                    AND is_deleted = FALSE
                    """,
                    conversation_id
                )
                return result or 0
        except Exception as error:
            logger.error(f"Error getting message count for conversation {conversation_id}: {error}")
            return 0

    async def _get_latest_message(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest message in a conversation."""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT id, user_id, content, created_at
                    FROM messages
                    WHERE conversation_id = $1
                    AND is_deleted = FALSE
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    conversation_id
                )

                if result:
                    return {
                        'id': str(result['id']),
                        'user_id': str(result['user_id']),
                        'content': result['content'],
                        'created_at': result['created_at']
                    }
                return None

        except Exception as error:
            logger.error(f"Error getting latest message for conversation {conversation_id}: {error}")
            return None

    async def _is_duplicate_trigger(self, conversation_id: str, message_count: int) -> bool:
        """
        Check if we already have a pending/processing job for this trigger.

        Args:
            conversation_id: The conversation ID
            message_count: The message count that triggered

        Returns:
            True if duplicate trigger detected, False otherwise
        """
        try:
            # Check in database
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM summarization_job_tracking
                    WHERE conversation_id = $1
                    AND message_count = $2
                    AND status IN ('queued', 'processing')
                    AND created_at > NOW() - INTERVAL $3 hours"
                    """,
                    conversation_id,
                    message_count,
                    config.DUPLICATE_CHECK_HOURS
                )

                return result > 0

        except Exception as error:
            logger.error(f"Error checking duplicate trigger for conversation {conversation_id}: {error}")
            return False

    async def _track_job(self, trigger: SummarizationTrigger, job_id: str, status: str) -> None:
        """Track job status in database."""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO summarization_job_tracking
                    (conversation_id, user_id, message_id, message_count,
                     message_range_start, message_range_end, job_id, status, queued_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    """,
                    trigger.conversation_id,
                    trigger.user_id,
                    trigger.message_id,
                    trigger.message_count,
                    trigger.message_count - 9,  # message_range_start
                    trigger.message_count,       # message_range_end
                    job_id,
                    status
                )
        except Exception as error:
            logger.error(f"Error tracking job {job_id}: {error}")

    def _calculate_priority(self, trigger: SummarizationTrigger) -> int:
        """
        Calculate job priority based on conversation recency.

        Args:
            trigger: The summarization trigger

        Returns:
            Priority value (higher = more important)
        """
        # Higher priority for recent conversations
        time_since_creation = datetime.utcnow() - trigger.created_at
        hours_since = time_since_creation.total_seconds() / 3600

        # Priority ranges from min to max based on recent hours
        priority = max(
            config.QUEUE_PRIORITY_MIN,
            min(config.QUEUE_PRIORITY_MAX, int(config.QUEUE_PRIORITY_MAX - hours_since / config.TRIGGER_PRIORITY_RECENT_HOURS))
        )
        return priority

    async def get_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        try:
            # Get additional metrics from database
            async with self.db_pool.acquire() as conn:
                # Success rate in configured window
                success_rate = await conn.fetchval(
                    "SELECT get_summarization_success_rate(NULL, $1)",
                    config.METRICS_SUCCESS_RATE_WINDOW
                ) or 0.0

                # Average processing time
                avg_processing_time = await conn.fetchval(
                    "SELECT get_avg_summarization_processing_time(NULL, $1)",
                    config.METRICS_PROCESSING_TIME_WINDOW
                ) or 0

                # Queue depth
                queue_depth = await self.summarization_queue.getWaiting()

            return {
                **self.metrics,
                'success_rate_24h': float(success_rate),
                'avg_processing_time_24h': avg_processing_time,
                'queue_depth': queue_depth,
                'updated_at': datetime.utcnow().isoformat()
            }

        except Exception as error:
            logger.error(f"Error getting metrics: {error}")
            return {
                **self.metrics,
                'error': str(error),
                'updated_at': datetime.utcnow().isoformat()
            }

    async def cleanup_old_records(self, days_to_keep: int = None) -> int:
        """Clean up old job tracking records."""
        try:
            if days_to_keep is None:
                days_to_keep = config.CLEANUP_DAYS

            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM summarization_job_tracking
                    WHERE created_at < NOW() - INTERVAL $1 days
                    """,
                    days_to_keep
                )

                # Extract row count from result string
                deleted_count = int(result.split()[-1]) if result else 0
                logger.info(f"Cleaned up {deleted_count} old job tracking records")
                return deleted_count

        except Exception as error:
            logger.error(f"Error cleaning up old records: {error}")
            return 0

    async def close(self):
        """Close the service and clean up resources."""
        try:
            await self.summarization_queue.close()
            logger.info("SummarizationTriggerService closed")
        except Exception as error:
            logger.error(f"Error closing SummarizationTriggerService: {error}")


# Factory function for easy instantiation
async def create_summarization_trigger_service(
    db_pool: asyncpg.Pool,
    redis_client: redis.Redis
) -> SummarizationTriggerService:
    """Create and initialize SummarizationTriggerService."""
    return SummarizationTriggerService(db_pool, redis_client)