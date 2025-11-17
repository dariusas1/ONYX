"""
Summary Memory Storage Service for ONYX

This service handles storing conversation summaries in both the conversation_summaries
table and as user memories for injection into future conversations.

Story 4-4: Auto-Summarization Pipeline
"""

import os
import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json

logger = logging.getLogger(__name__)


class SummaryMemoryStorage:
    """Service for storing summaries as memories and in conversation_summaries table"""

    def __init__(self):
        """Initialize summary memory storage service"""
        self.connection_string = self._build_connection_string()
        self.summary_confidence = float(os.getenv("AUTO_SUMMARY_CONFIDENCE", "0.9"))
        self.duplicate_threshold = float(os.getenv("SUMMARY_DUPLICATE_THRESHOLD", "0.8"))
        self.duplicate_time_window_hours = int(os.getenv("SUMMARY_DUPLICATE_WINDOW_HOURS", "1"))

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "manus")
        user = os.getenv("POSTGRES_USER", "manus")
        password = os.getenv("POSTGRES_PASSWORD", "")
        return f"host={host} port={port} dbname={database} user={user} password={password}"

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.connection_string)

    # =========================================================================
    # Core Storage Methods
    # =========================================================================

    async def store_summary(
        self,
        user_id: str,
        conversation_id: str,
        result: Any,
        message_range: Dict[str, int]
    ) -> str:
        """
        Store summary in both conversation_summaries table and as user memory

        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            result: SummarizationResult object
            message_range: Range of messages summarized

        Returns:
            Memory ID of the stored memory
        """
        try:
            # Check for duplicate summary first
            duplicate_memory_id = await self._find_duplicate_summary(user_id, conversation_id, result.summary)
            if duplicate_memory_id:
                logger.info(f"Found duplicate summary for conversation {conversation_id}, using existing memory {duplicate_memory_id}")
                return duplicate_memory_id

            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    # Start transaction
                    conn.autocommit = False

                    # Store in conversation_summaries table
                    summary_id = await self._store_conversation_summary(
                        cur, user_id, conversation_id, result, message_range
                    )

                    # Also store as user memory for injection
                    memory_id = await self._store_as_memory(
                        cur, user_id, conversation_id, result, message_range
                    )

                    conn.commit()

                    logger.info(
                        f"Stored summary for conversation {conversation_id}: "
                        f"summary_id={summary_id}, memory_id={memory_id}"
                    )

                    return memory_id

            except Exception as e:
                conn.rollback()
                raise
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error storing summary for conversation {conversation_id}: {e}")
            raise Exception(f"Failed to store summary: {str(e)}")

    async def _store_conversation_summary(
        self,
        cur,
        user_id: str,
        conversation_id: str,
        result: Any,
        message_range: Dict[str, int]
    ) -> str:
        """Store summary in conversation_summaries table"""
        try:
            cur.execute(
                """
                INSERT INTO conversation_summaries
                (conversation_id, user_id, summary_text, message_range_start, message_range_end,
                 key_topics, sentiment_score, confidence_score, processing_time_ms, model_used,
                 prompt_version, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
                """,
                (
                    conversation_id,
                    user_id,
                    result.summary,
                    message_range["start"],
                    message_range["end"],
                    Json(result.key_topics),
                    result.sentiment,
                    result.confidence,
                    result.processing_time,
                    result.model_used,
                    result.prompt_version or "1.0"
                )
            )

            result_row = cur.fetchone()
            summary_id = str(result_row[0]) if result_row else None

            logger.debug(f"Stored conversation summary with ID: {summary_id}")
            return summary_id

        except Exception as e:
            logger.error(f"Error storing conversation summary: {e}")
            raise

    async def _store_as_memory(
        self,
        cur,
        user_id: str,
        conversation_id: str,
        result: Any,
        message_range: Dict[str, int]
    ) -> str:
        """Store summary as user memory for injection"""
        try:
            # Create metadata for the memory
            metadata = {
                "type": "auto_summary",
                "conversation_id": conversation_id,
                "message_range": message_range,
                "key_topics": result.key_topics,
                "sentiment": result.sentiment,
                "processing_time_ms": result.processing_time,
                "model_used": result.model_used,
                "prompt_version": result.prompt_version or "1.0",
                "generated_at": datetime.utcnow().isoformat()
            }

            # Use the existing memory service pattern
            from services.memory_service import MemoryService

            # Since we can't easily import and use MemoryService here due to circular imports,
            # we'll directly insert into user_memories table
            cur.execute(
                """
                INSERT INTO user_memories
                (user_id, fact, category, confidence, source_type, source_message_id,
                 conversation_id, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
                """,
                (
                    user_id,
                    result.summary,
                    'summary',  # Category for auto-summaries
                    result.confidence,
                    'auto_summary',  # Source type
                    None,  # No specific source message
                    conversation_id,
                    Json(metadata)
                )
            )

            result_row = cur.fetchone()
            memory_id = str(result_row[0]) if result_row else None

            logger.debug(f"Stored summary as memory with ID: {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Error storing summary as memory: {e}")
            raise

    # =========================================================================
    # Duplicate Detection Methods
    # =========================================================================

    async def _find_duplicate_summary(
        self,
        user_id: str,
        conversation_id: str,
        summary_text: str
    ) -> Optional[str]:
        """
        Find duplicate summary to avoid redundant storage

        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            summary_text: Summary text to check for duplicates

        Returns:
            Memory ID of duplicate if found, None otherwise
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    # Check for very similar summaries in the same conversation
                    # within the time window using text similarity
                    cur.execute(
                        """
                        SELECT id, fact
                        FROM user_memories
                        WHERE user_id = %s
                            AND conversation_id = %s
                            AND category = 'summary'
                            AND source_type = 'auto_summary'
                            AND created_at > NOW() - INTERVAL '%s hours'
                        ORDER BY created_at DESC
                        LIMIT 5
                        """,
                        (user_id, conversation_id, self.duplicate_time_window_hours)
                    )

                    existing_memories = cur.fetchall()

                    for memory_id, existing_summary in existing_memories:
                        # Simple similarity check - can be enhanced with more sophisticated algorithms
                        similarity = self._calculate_text_similarity(summary_text, existing_summary)
                        if similarity >= self.duplicate_threshold:
                            logger.debug(
                                f"Found duplicate summary (similarity: {similarity:.2f}) "
                                f"for conversation {conversation_id}"
                            )
                            return str(memory_id)

                    return None

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error checking for duplicate summary: {e}")
            return None

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple text similarity using word overlap
        Can be enhanced with more sophisticated algorithms like cosine similarity
        """
        try:
            # Convert to lowercase and extract words
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            # Calculate Jaccard similarity
            intersection = words1.intersection(words2)
            union = words1.union(words2)

            if not union:
                return 0.0

            return len(intersection) / len(union)

        except Exception:
            return 0.0

    # =========================================================================
    # Memory Retrieval Methods
    # =========================================================================

    async def get_conversation_summaries(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all summaries for a conversation

        Args:
            conversation_id: Conversation UUID
            limit: Maximum number of summaries to return

        Returns:
            List of conversation summary records
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, conversation_id, user_id, summary_text, message_range_start,
                               message_range_end, key_topics, sentiment_score, confidence_score,
                               processing_time_ms, model_used, prompt_version, created_at, updated_at
                        FROM conversation_summaries
                        WHERE conversation_id = %s
                        ORDER BY message_range_end ASC
                        LIMIT %s
                        """,
                        (conversation_id, limit)
                    )

                    results = cur.fetchall()
                    summaries = []

                    for result in results:
                        summary_dict = dict(result)
                        # Parse JSON fields if they're strings
                        if summary_dict.get('key_topics') and isinstance(summary_dict['key_topics'], str):
                            summary_dict['key_topics'] = json.loads(summary_dict['key_topics'])
                        summaries.append(summary_dict)

                    return summaries

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error getting conversation summaries for {conversation_id}: {e}")
            return []

    async def get_user_summary_memories(
        self,
        user_id: str,
        limit: int = 20,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get summary memories for a user

        Args:
            user_id: User UUID
            limit: Maximum number of memories to return
            days: Number of days to look back

        Returns:
            List of summary memory records
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, fact, category, confidence, source_type,
                               source_message_id, conversation_id, metadata,
                               access_count, last_accessed_at, created_at, updated_at
                        FROM user_memories
                        WHERE user_id = %s
                            AND category = 'summary'
                            AND source_type = 'auto_summary'
                            AND is_deleted = FALSE
                            AND created_at > NOW() - INTERVAL '%s days'
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT %s
                        """,
                        (user_id, days, limit)
                    )

                    results = cur.fetchall()
                    memories = []

                    for result in results:
                        memory_dict = dict(result)
                        # Parse metadata if it's a string
                        if memory_dict.get('metadata') and isinstance(memory_dict['metadata'], str):
                            memory_dict['metadata'] = json.loads(memory_dict['metadata'])
                        memories.append(memory_dict)

                    return memories

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error getting user summary memories for {user_id}: {e}")
            return []

    # =========================================================================
    # Analytics and Monitoring Methods
    # =========================================================================

    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get storage service metrics"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Summary statistics
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) as total_summaries,
                            COUNT(DISTINCT conversation_id) as unique_conversations,
                            COUNT(DISTINCT user_id) as unique_users,
                            AVG(confidence_score) as avg_confidence,
                            AVG(processing_time_ms) as avg_processing_time,
                            AVG(sentiment_score) as avg_sentiment
                        FROM conversation_summaries
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                        """
                    )
                    summary_stats = cur.fetchone()

                    # Memory statistics
                    cur.execute(
                        """
                        SELECT
                            COUNT(*) as total_memories,
                            AVG(confidence) as avg_memory_confidence
                        FROM user_memories
                        WHERE category = 'summary'
                            AND source_type = 'auto_summary'
                            AND created_at > NOW() - INTERVAL '24 hours'
                        """
                    )
                    memory_stats = cur.fetchone()

                    # Recent activity
                    cur.execute(
                        """
                        SELECT
                            DATE_TRUNC('hour', created_at) as hour,
                            COUNT(*) as summaries_count
                        FROM conversation_summaries
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                        GROUP BY DATE_TRUNC('hour', created_at)
                        ORDER BY hour DESC
                        """
                    )
                    hourly_activity = cur.fetchall()

                    return {
                        "summary_stats": {
                            "total_summaries_24h": summary_stats['total_summaries'],
                            "unique_conversations_24h": summary_stats['unique_conversations'],
                            "unique_users_24h": summary_stats['unique_users'],
                            "avg_confidence_24h": float(summary_stats['avg_confidence'] or 0),
                            "avg_processing_time_ms_24h": float(summary_stats['avg_processing_time'] or 0),
                            "avg_sentiment_24h": float(summary_stats['avg_sentiment'] or 0)
                        },
                        "memory_stats": {
                            "total_memories_24h": memory_stats['total_memories'],
                            "avg_memory_confidence_24h": float(memory_stats['avg_memory_confidence'] or 0)
                        },
                        "hourly_activity": [dict(row) for row in hourly_activity],
                        "config": {
                            "summary_confidence": self.summary_confidence,
                            "duplicate_threshold": self.duplicate_threshold,
                            "duplicate_time_window_hours": self.duplicate_time_window_hours
                        }
                    }

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error getting service metrics: {e}")
            return {"error": str(e)}

    async def cleanup_old_summaries(self, days_to_keep: int = 90) -> int:
        """
        Clean up old conversation summaries (keeps memories, just cleans conversation_summaries table)

        Args:
            days_to_keep: Number of days to keep summaries

        Returns:
            Number of summaries cleaned up
        """
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM conversation_summaries
                        WHERE created_at < NOW() - INTERVAL '%s days'
                        """,
                        (days_to_keep,)
                    )

                    deleted_count = cur.rowcount
                    conn.commit()

                    logger.info(f"Cleaned up {deleted_count} old conversation summaries")
                    return deleted_count

            except Exception as e:
                conn.rollback()
                raise
            finally:
                conn.close()

        except Exception as e:
            logger.error(f"Error cleaning up old summaries: {e}")
            return 0


# Global service instance
_summary_memory_storage = None


def get_summary_memory_storage() -> SummaryMemoryStorage:
    """Get or create summary memory storage instance"""
    global _summary_memory_storage
    if _summary_memory_storage is None:
        _summary_memory_storage = SummaryMemoryStorage()
    return _summary_memory_storage