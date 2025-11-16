"""
Memory Injection Service for ONYX

This service provides memory injection functionality to automatically
inject relevant memories and standing instructions into LLM context.

Story 4-3: Memory Injection & Agent Integration
"""

import os
import time
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


@dataclass
class MemoryInjection:
    """Memory injection result"""
    user_id: str
    conversation_id: str
    standing_instructions: List[Dict[str, Any]]
    memories: List[Dict[str, Any]]
    injection_text: str
    injection_time: int
    performance_stats: Dict[str, Any]


@dataclass
class CachedInjection:
    """Cached memory injection with TTL"""
    injection: MemoryInjection
    timestamp: float
    ttl: int = 300  # 5 minutes TTL


class MemoryInjectionService:
    """Service for memory injection and LLM context preparation"""

    def __init__(self):
        """Initialize memory injection service"""
        self.connection_string = self._build_connection_string()
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
        self.max_cache_size = 100

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
        conn = psycopg2.connect(self.connection_string)
        return conn

    # =========================================================================
    # Memory Injection Core Methods
    # =========================================================================

    async def prepare_injection(
        self,
        user_id: str,
        conversation_id: str,
        current_message: Optional[str] = None
    ) -> MemoryInjection:
        """
        Prepare memory injection for LLM context

        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            current_message: Optional current message for context filtering

        Returns:
            MemoryInjection with top memories and instructions
        """
        start_time = time.time()

        # Check cache first
        cache_key = f"{user_id}:{conversation_id}"
        cached = self._get_cached_injection(cache_key)
        if cached:
            logger.debug(f"Using cached injection for user {user_id}")
            cached.injection_time = int((time.time() - start_time) * 1000)
            return cached.injection

        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Parallel fetch of instructions and memories
                instructions = await self._get_top_standing_instructions(cur, user_id)
                memories = await self._get_top_memories(cur, user_id, current_message)

                # Format for LLM injection
                injection_text = self._format_for_llm(instructions, memories)

                # Create injection object
                injection = MemoryInjection(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    standing_instructions=instructions,
                    memories=memories,
                    injection_text=injection_text,
                    injection_time=int((time.time() - start_time) * 1000),
                    performance_stats={
                        "instructions_count": len(instructions),
                        "memories_count": len(memories),
                        "cache_hit": False,
                        "database_time_ms": None  # Can be enhanced with timing
                    }
                )

                # Log injection for analytics
                await self._log_injection(
                    cur, user_id, conversation_id,
                    len(memories), len(instructions),
                    "chat", injection.injection_time, True, None
                )

                # Cache the result
                self._cache_injection(cache_key, injection)

                conn.commit()
                return injection

        except Exception as e:
            logger.error(f"Failed to prepare injection for user {user_id}: {e}")
            # Log failed injection
            try:
                conn = self._get_connection()
                with conn.cursor() as cur:
                    await self._log_injection(
                        cur, user_id, conversation_id,
                        0, 0, "chat", int((time.time() - start_time) * 1000),
                        False, str(e)
                    )
                    conn.commit()
            except:
                pass

            # Return minimal injection on error
            return MemoryInjection(
                user_id=user_id,
                conversation_id=conversation_id,
                standing_instructions=[],
                memories=[],
                injection_text="",
                injection_time=int((time.time() - start_time) * 1000),
                performance_stats={
                    "instructions_count": 0,
                    "memories_count": 0,
                    "cache_hit": False,
                    "error": str(e)
                }
            )

    async def _get_top_standing_instructions(
        self,
        cursor,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top standing instructions using priority scoring"""
        try:
            cursor.execute(
                """
                SELECT * FROM get_top_standing_instructions(%s, %s)
                ORDER BY priority_score DESC
                """,
                (user_id, limit)
            )
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get standing instructions: {e}")
            return []

    async def _get_top_memories(
        self,
        cursor,
        user_id: str,
        current_message: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get top 5 memories using composite scoring algorithm"""
        try:
            cursor.execute(
                """
                WITH ranked_memories AS (
                    SELECT
                        id, user_id, fact, category, confidence, source_type,
                        created_at, access_count, last_accessed_at,
                        -- Composite scoring algorithm with configurable weights
                        (confidence * 0.5 +
                         EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0 * -0.001 +
                         COALESCE(access_count, 0) * 0.01 +
                         CASE WHEN source_type = 'auto_summary' THEN 0.2 ELSE 0 END +
                         CASE WHEN category = 'priority' THEN 0.1 ELSE 0 END +
                         CASE WHEN category = 'decision' THEN 0.05 ELSE 0 END +
                         CASE WHEN category = 'goal' THEN 0.03 ELSE 0 END
                        ) as memory_score
                    FROM user_memories
                    WHERE user_id = %s
                        AND is_deleted = FALSE
                        AND (expires_at IS NULL OR expires_at > NOW())
                )
                SELECT id, user_id, fact, category, confidence, source_type,
                       created_at, access_count, last_accessed_at, memory_score
                FROM ranked_memories
                ORDER BY memory_score DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get top memories: {e}")
            return []

    def _format_for_llm(
        self,
        instructions: List[Dict[str, Any]],
        memories: List[Dict[str, Any]]
    ) -> str:
        """Format memories and instructions for LLM consumption"""
        injection_parts = []

        # Add standing instructions
        if instructions:
            injection_parts.append("STANDING INSTRUCTIONS:")
            for i, instruction in enumerate(instructions, 1):
                instruction_text = instruction.get('instruction_text', '')
                if instruction_text:
                    injection_parts.append(f"{i}. {instruction_text}")
            injection_parts.append("")  # Empty line for separation

        # Add user context (memories)
        if memories:
            injection_parts.append("USER CONTEXT (Key memories):")
            for i, memory in enumerate(memories, 1):
                fact = memory.get('fact', '')
                category = memory.get('category', 'unknown')
                confidence = memory.get('confidence', 0.8)
                created_at = memory.get('created_at')
                source_type = memory.get('source_type', 'manual')

                # Format age
                age = self._format_age(created_at) if created_at else "unknown"
                source = self._format_source(source_type)

                injection_parts.append(
                    f"{i}. {fact} ({category}, {int(confidence * 100)}% confidence, {age} ago, {source})"
                )
            injection_parts.append("")  # Empty line for separation

        return "\n".join(injection_parts)

    def _format_age(self, created_at) -> str:
        """Format memory age in human readable format"""
        if not created_at:
            return "unknown"

        now = datetime.now()
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        delta = now - created_at
        hours = int(delta.total_seconds() / 3600)

        if hours < 1:
            return "just now"
        elif hours < 24:
            return f"{hours}h"
        else:
            days = hours // 24
            if days < 7:
                return f"{days}d"
            else:
                weeks = days // 7
                return f"{weeks}w"

    def _format_source(self, source_type: str) -> str:
        """Format source type for display"""
        source_map = {
            'manual': 'manual',
            'extracted_from_chat': 'extracted',
            'auto_summary': 'summary',
            'standing_instruction': 'instruction'
        }
        return source_map.get(source_type, source_type)

    # =========================================================================
    # Caching Methods
    # =========================================================================

    def _get_cached_injection(self, cache_key: str) -> Optional[CachedInjection]:
        """Get cached injection if not expired"""
        if cache_key not in self.cache:
            return None

        cached = self.cache[cache_key]
        if time.time() - cached.timestamp > cached.ttl:
            del self.cache[cache_key]
            return None

        return cached

    def _cache_injection(self, cache_key: str, injection: MemoryInjection):
        """Cache injection with TTL"""
        # Implement simple LRU eviction if cache is full
        if len(self.cache) >= self.max_cache_size:
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k].timestamp)
            del self.cache[oldest_key]

        self.cache[cache_key] = CachedInjection(
            injection=injection,
            timestamp=time.time(),
            ttl=self.cache_ttl
        )

    # =========================================================================
    # Analytics and Logging
    # =========================================================================

    async def _log_injection(
        self,
        cursor,
        user_id: str,
        conversation_id: str,
        memories_count: int,
        instructions_count: int,
        injection_type: str,
        performance_ms: int,
        success: bool,
        error_message: Optional[str]
    ):
        """Log injection event for analytics"""
        try:
            cursor.execute(
                """
                INSERT INTO memory_injection_logs (
                    user_id, conversation_id, memories_count, injection_type,
                    performance_ms, success, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, conversation_id, memories_count + instructions_count,
                 injection_type, performance_ms, success, error_message)
            )
        except Exception as e:
            logger.error(f"Failed to log injection: {e}")

    async def get_injection_analytics(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get injection analytics for user"""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_injections,
                        AVG(performance_ms) as avg_performance_ms,
                        COUNT(CASE WHEN success = TRUE THEN 1 END) as successful_injections,
                        COUNT(CASE WHEN success = FALSE THEN 1 END) as failed_injections,
                        SUM(memories_count) as total_memories_injected
                    FROM memory_injection_logs
                    WHERE user_id = %s
                        AND created_at >= NOW() - INTERVAL '%s days'
                    """,
                    (user_id, days)
                )
                result = cur.fetchone()

                if result:
                    return {
                        "period_days": days,
                        "total_injections": result['total_injections'],
                        "avg_performance_ms": float(result['avg_performance_ms'] or 0),
                        "success_rate": (result['successful_injections'] /
                                      result['total_injections'] * 100) if result['total_injections'] > 0 else 0,
                        "total_memories_injected": result['total_memories_injected'] or 0,
                        "cache_hit_rate": self._get_cache_hit_rate()
                    }
                else:
                    return {"period_days": days, "total_injections": 0}

        except Exception as e:
            logger.error(f"Failed to get injection analytics: {e}")
            return {"error": str(e)}

    def _get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # This is a simplified version - can be enhanced with actual hit tracking
        return len(self.cache) / max(self.max_cache_size, 1) * 100

    # =========================================================================
    # Context-Aware Filtering
    # =========================================================================

    async def get_context_aware_memories(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        limit: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Get memories filtered by conversation context
        Enhanced for better relevance scoring
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Extract keywords from current message for semantic matching
                keywords = self._extract_keywords(current_message)

                if keywords:
                    # Build semantic search query
                    keyword_conditions = []
                    params = [user_id]

                    for keyword in keywords[:5]:  # Limit to top 5 keywords
                        keyword_conditions.append("fact ILIKE %s")
                        params.append(f"%{keyword}%")

                    where_clause = " OR ".join(keyword_conditions)

                    cur.execute(
                        f"""
                        WITH semantic_memories AS (
                            SELECT id, user_id, fact, category, confidence, source_type,
                                   created_at, access_count, last_accessed_at,
                                   -- Boost score for keyword matches
                                   (confidence * 0.4 +
                                    access_count * 0.02 +
                                    CASE WHEN category = 'priority' THEN 0.15 ELSE 0 END +
                                    CASE WHEN category = 'decision' THEN 0.1 ELSE 0 END +
                                    CASE WHEN category = 'goal' THEN 0.05 ELSE 0 END
                                   ) as relevance_score
                            FROM user_memories
                            WHERE user_id = %s
                                AND is_deleted = FALSE
                                AND ({where_clause})
                                AND (expires_at IS NULL OR expires_at > NOW())
                        )
                        SELECT id, user_id, fact, category, confidence, source_type,
                               created_at, access_count, last_accessed_at, relevance_score
                        FROM semantic_memories
                        ORDER BY relevance_score DESC
                        LIMIT %s
                        """,
                        params + [limit]
                    )
                else:
                    # Fallback to standard top memories
                    return await self._get_top_memories(cur, user_id, current_message, limit)

                results = cur.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get context-aware memories: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for semantic matching"""
        if not text:
            return []

        # Simple keyword extraction - can be enhanced with NLP
        import re

        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                     'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                     'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us',
                     'them', 'my', 'your', 'his', 'its', 'our', 'their', 'what', 'when',
                     'where', 'why', 'how', 'this', 'that', 'these', 'those'}

        # Extract words (3+ characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter stop words and return unique keywords
        keywords = list(set([word for word in words if word not in stop_words]))

        return keywords[:10]  # Return top 10 keywords


# Global memory injection service instance
_memory_injection_service = None


def get_memory_injection_service() -> MemoryInjectionService:
    """Get or create memory injection service instance"""
    global _memory_injection_service
    if _memory_injection_service is None:
        _memory_injection_service = MemoryInjectionService()
    return _memory_injection_service