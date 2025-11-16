"""
Summary Memory Storage Service
Story 4-4: Auto-Summarization Pipeline

This service handles storing auto-generated summaries as memories,
including duplicate detection and integration with the memory injection system.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import asyncpg
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class StoredSummary:
    """Data structure for a stored summary."""
    id: str
    conversation_id: str
    user_id: str
    summary: str
    key_topics: List[str]
    sentiment: float
    confidence: float
    message_range: Dict[str, int]
    processing_time: int
    created_at: datetime

class SummaryMemoryStorage:
    """
    Service for storing summaries as memories with duplicate detection.

    Features:
    - Duplicate summary detection using similarity
    - Storage in both conversation_summaries and user_memories tables
    - High confidence scores for auto-generated summaries
    - Metadata preservation for traceability and analytics
    - Conflict resolution with existing summary memories
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.similarity_threshold = 0.8
        self.duplicate_window_hours = 1  # Check for duplicates within 1 hour

        # Performance metrics
        self.metrics = {
            'summaries_stored': 0,
            'duplicates_prevented': 0,
            'errors': 0,
            'avg_storage_time': 0
        }

        logger.info("SummaryMemoryStorage initialized")

    async def store_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary_result: "SummarizationResult",
        message_range: Dict[str, int]
    ) -> str:
        """
        Store a summary as a memory.

        Args:
            user_id: The user ID
            conversation_id: The conversation ID
            summary_result: The summarization result
            message_range: The message range that was summarized

        Returns:
            The ID of the stored memory record
        """
        start_time = datetime.utcnow()

        try:
            # Check for duplicate summaries
            existing_memory = await self._find_duplicate_summary(
                user_id,
                conversation_id,
                summary_result.summary
            )

            if existing_memory:
                self.metrics['duplicates_prevented'] += 1
                logger.info(f"Duplicate summary found, skipping storage for conversation {conversation_id}")
                return existing_memory['id']

            # Store in conversation_summaries table
            summary_record = await self._store_conversation_summary(
                user_id,
                conversation_id,
                summary_result,
                message_range
            )

            # Also store as a memory for injection
            memory_record = await self._store_as_memory(
                user_id,
                conversation_id,
                summary_result,
                message_range
            )

            # Update metrics
            storage_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            self._update_avg_storage_time(storage_time)
            self.metrics['summaries_stored'] += 1

            logger.info(f"Summary stored successfully for conversation {conversation_id}: "
                       f"summary_id={summary_record['id']}, memory_id={memory_record['id']}")

            return memory_record['id']

        except Exception as error:
            self.metrics['errors'] += 1
            logger.error(f"Error storing summary for conversation {conversation_id}: {error}")
            raise ValueError(f"Failed to store summary: {error.message}")

    async def _find_duplicate_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check for duplicate summaries within the time window.

        Args:
            user_id: The user ID
            conversation_id: The conversation ID
            summary: The summary text

        Returns:
            Existing summary record if duplicate found, None otherwise
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT id, summary, created_at
                    FROM user_memories
                    WHERE user_id = $1
                        AND conversation_id = $2
                        AND category = 'summary'
                        AND source_type = 'auto_summary'
                        AND similarity(fact, $3) > $4
                        AND created_at > NOW() - INTERVAL '1 hour'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    user_id,
                    conversation_id,
                    summary,
                    self.similarity_threshold
                )

                if result:
                    return {
                        'id': str(result['id']),
                        'summary': result['summary'],
                        'created_at': result['created_at']
                    }

                return None

        except Exception as error:
            logger.error(f"Error checking duplicate summary for conversation {conversation_id}: {error}")
            return None

    async def _store_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary_result: "SummarizationResult",
        message_range: Dict[str, int]
    ) -> Dict[str, Any]:
        """Store summary in conversation_summaries table."""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    INSERT INTO conversation_summaries
                    (user_id, conversation_id, summary, key_topics, sentiment_score,
                     message_range_start, message_range_end, processing_time,
                     generated_by, metadata, is_deleted)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, FALSE)
                    RETURNING id, created_at
                    """,
                    user_id,
                    conversation_id,
                    summary_result.summary,
                    json.dumps(summary_result.key_topics),
                    summary_result.sentiment,
                    message_range['start'],
                    message_range['end'],
                    summary_result.processing_time,
                    'auto_summary',
                    json.dumps({
                        'confidence': summary_result.confidence,
                        'model': summary_result.model,
                        'prompt_version': summary_result.prompt_version,
                        'message_count': message_range['end'] - message_range['start'] + 1,
                        'topics_count': len(summary_result.key_topics),
                        'processing_time_ms': summary_result.processing_time
                    })
                )

                return {
                    'id': str(result['id']),
                    'created_at': result['created_at']
                }

        except Exception as error:
            logger.error(f"Error storing conversation summary: {error}")
            raise

    async def _store_as_memory(
        self,
        user_id: str,
        conversation_id: str,
        summary_result: "SummarizationResult",
        message_range: Dict[str, int]
    ) -> Dict[str, Any]:
        """Store summary as a memory in user_memories table."""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    INSERT INTO user_memories
                    (user_id, fact, category, confidence, source_type, source_message_id,
                     conversation_id, metadata, expires_at, is_deleted)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, FALSE)
                    RETURNING id, created_at
                    """,
                    user_id,
                    summary_result.summary,
                    'summary',
                    summary_result.confidence,  # High confidence for auto-generated summaries
                    'auto_summary',
                    None,  # No specific source message for summaries
                    conversation_id,
                    json.dumps({
                        'topics': summary_result.key_topics,
                        'sentiment': summary_result.sentiment,
                        'message_range': message_range,
                        'processing_time': summary_result.processing_time,
                        'model': summary_result.model,
                        'prompt_version': summary_result.prompt_version,
                        'generated_at': datetime.utcnow().isoformat()
                    }),
                    None  # No expiration for summaries
                )

                return {
                    'id': str(result['id']),
                    'created_at': result['created_at']
                }

        except Exception as error:
            logger.error(f"Error storing summary as memory: {error}")
            raise

    async def get_conversation_summaries(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 10
    ) -> List[StoredSummary]:
        """
        Get all summaries for a conversation.

        Args:
            conversation_id: The conversation ID
            user_id: The user ID
            limit: Maximum number of summaries to return

        Returns:
            List of stored summaries
        """
        try:
            async with self.db_pool.acquire() as conn:
                records = await conn.fetch(
                    """
                    SELECT cs.id, cs.conversation_id, cs.user_id, cs.summary,
                           cs.key_topics, cs.sentiment_score, cs.message_range_start,
                           cs.message_range_end, cs.processing_time, cs.created_at
                    FROM conversation_summaries cs
                    WHERE cs.conversation_id = $1
                        AND cs.user_id = $2
                        AND cs.is_deleted = FALSE
                    ORDER BY cs.created_at DESC
                    LIMIT $3
                    """,
                    conversation_id,
                    user_id,
                    limit
                )

                summaries = []
                for record in records:
                    try:
                        key_topics = json.loads(record['key_topics']) if record['key_topics'] else []
                    except (json.JSONDecodeError, TypeError):
                        key_topics = []

                    summary = StoredSummary(
                        id=str(record['id']),
                        conversation_id=str(record['conversation_id']),
                        user_id=str(record['user_id']),
                        summary=record['summary'],
                        key_topics=key_topics,
                        sentiment=float(record['sentiment_score'] or 0),
                        confidence=0.9,  # Default confidence for auto-generated summaries
                        message_range={
                            'start': record['message_range_start'],
                            'end': record['message_range_end']
                        },
                        processing_time=record['processing_time'] or 0,
                        created_at=record['created_at']
                    )
                    summaries.append(summary)

                return summaries

        except Exception as error:
            logger.error(f"Error getting conversation summaries for {conversation_id}: {error}")
            return []

    async def get_user_summaries(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[StoredSummary]:
        """
        Get summaries for a user across all conversations.

        Args:
            user_id: The user ID
            limit: Maximum number of summaries to return
            offset: Number of summaries to skip

        Returns:
            List of stored summaries
        """
        try:
            async with self.db_pool.acquire() as conn:
                records = await conn.fetch(
                    """
                    SELECT cs.id, cs.conversation_id, cs.user_id, cs.summary,
                           cs.key_topics, cs.sentiment_score, cs.message_range_start,
                           cs.message_range_end, cs.processing_time, cs.created_at
                    FROM conversation_summaries cs
                    WHERE cs.user_id = $1
                        AND cs.is_deleted = FALSE
                    ORDER BY cs.created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    user_id,
                    limit,
                    offset
                )

                summaries = []
                for record in records:
                    try:
                        key_topics = json.loads(record['key_topics']) if record['key_topics'] else []
                    except (json.JSONDecodeError, TypeError):
                        key_topics = []

                    summary = StoredSummary(
                        id=str(record['id']),
                        conversation_id=str(record['conversation_id']),
                        user_id=str(record['user_id']),
                        summary=record['summary'],
                        key_topics=key_topics,
                        sentiment=float(record['sentiment_score'] or 0),
                        confidence=0.9,
                        message_range={
                            'start': record['message_range_start'],
                            'end': record['message_range_end']
                        },
                        processing_time=record['processing_time'] or 0,
                        created_at=record['created_at']
                    )
                    summaries.append(summary)

                return summaries

        except Exception as error:
            logger.error(f"Error getting user summaries for {user_id}: {error}")
            return []

    async def delete_summary(self, summary_id: str, user_id: str) -> bool:
        """
        Soft delete a summary.

        Args:
            summary_id: The summary ID
            user_id: The user ID (for authorization)

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Delete from conversation_summaries
                result1 = await conn.execute(
                    """
                    UPDATE conversation_summaries
                    SET is_deleted = TRUE, updated_at = NOW()
                    WHERE id = $1 AND user_id = $2
                    """,
                    summary_id,
                    user_id
                )

                # Delete from user_memories
                result2 = await conn.execute(
                    """
                    UPDATE user_memories
                    SET is_deleted = TRUE, updated_at = NOW()
                    WHERE id = $1 AND user_id = $2 AND category = 'summary'
                    """,
                    summary_id,
                    user_id
                )

                deleted_rows1 = int(result1.split()[-1]) if result1 else 0
                deleted_rows2 = int(result2.split()[-1]) if result2 else 0

                success = deleted_rows1 > 0 or deleted_rows2 > 0
                if success:
                    logger.info(f"Summary {summary_id} deleted for user {user_id}")

                return success

        except Exception as error:
            logger.error(f"Error deleting summary {summary_id}: {error}")
            return False

    async def get_summary_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about summaries for a user.

        Args:
            user_id: The user ID

        Returns:
            Dictionary with summary statistics
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Total summaries
                total_summaries = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM conversation_summaries
                    WHERE user_id = $1 AND is_deleted = FALSE
                    """,
                    user_id
                ) or 0

                # Summaries by sentiment
                sentiment_stats = await conn.fetch(
                    """
                    SELECT
                        CASE
                            WHEN sentiment_score >= 0.3 THEN 'positive'
                            WHEN sentiment_score <= -0.3 THEN 'negative'
                            ELSE 'neutral'
                        END as sentiment_category,
                        COUNT(*) as count
                    FROM conversation_summaries
                    WHERE user_id = $1 AND is_deleted = FALSE
                    GROUP BY sentiment_category
                    """,
                    user_id
                )

                # Average processing time
                avg_processing_time = await conn.fetchval(
                    """
                    SELECT AVG(processing_time)
                    FROM conversation_summaries
                    WHERE user_id = $1 AND is_deleted = FALSE
                        AND processing_time IS NOT NULL
                    """,
                    user_id
                ) or 0

                # Recent activity (last 7 days)
                recent_summaries = await conn.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM conversation_summaries
                    WHERE user_id = $1 AND is_deleted = FALSE
                        AND created_at >= NOW() - INTERVAL '7 days'
                    """,
                    user_id
                ) or 0

                # Format sentiment stats
                sentiment_distribution = {
                    'positive': 0,
                    'negative': 0,
                    'neutral': 0
                }

                for row in sentiment_stats:
                    sentiment_distribution[row['sentiment_category']] = row['count']

                return {
                    'total_summaries': total_summaries,
                    'sentiment_distribution': sentiment_distribution,
                    'avg_processing_time_ms': int(avg_processing_time),
                    'recent_summaries_7d': recent_summaries,
                    'updated_at': datetime.utcnow().isoformat()
                }

        except Exception as error:
            logger.error(f"Error getting summary statistics for {user_id}: {error}")
            return {'error': str(error), 'updated_at': datetime.utcnow().isoformat()}

    def _update_avg_storage_time(self, storage_time: int):
        """Update the average storage time metric."""
        current_avg = self.metrics['avg_storage_time']
        count = self.metrics['summaries_stored']

        if count == 1:
            self.metrics['avg_storage_time'] = storage_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.metrics['avg_storage_time'] = int(
                alpha * storage_time + (1 - alpha) * current_avg
            )

    async def get_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        return {
            **self.metrics,
            'updated_at': datetime.utcnow().isoformat()
        }

    async def cleanup_old_summaries(self, days_to_keep: int = 365):
        """Clean up very old summaries (older than 1 year by default)."""
        try:
            async with self.db_pool.acquire() as conn:
                # Soft delete old summaries
                result = await conn.execute(
                    """
                    UPDATE conversation_summaries
                    SET is_deleted = TRUE, updated_at = NOW()
                    WHERE created_at < NOW() - INTERVAL '%s days'
                        AND is_deleted = FALSE
                    """,
                    days_to_keep
                )

                deleted_count = int(result.split()[-1]) if result else 0
                logger.info(f"Cleaned up {deleted_count} old summaries")
                return deleted_count

        except Exception as error:
            logger.error(f"Error cleaning up old summaries: {error}")
            return 0


# Factory function for easy instantiation
def create_summary_memory_storage(db_pool: asyncpg.Pool) -> SummaryMemoryStorage:
    """Create and initialize SummaryMemoryStorage."""
    return SummaryMemoryStorage(db_pool)