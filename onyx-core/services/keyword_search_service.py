"""
Keyword Search Service Module

This module provides PostgreSQL full-text search functionality with BM25-like scoring
for the keyword search component of the hybrid search system.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncpg
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Constants
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_TIMEOUT_SECONDS = 5
RECENCY_BOOST_DAYS = 30
RECENCY_BOOST_FACTOR = 1.10


@dataclass
class KeywordSearchResult:
    """Data class for keyword search results"""

    doc_id: str
    title: str
    content: str
    source_type: str
    source_id: str
    created_at: datetime
    updated_at: datetime
    permissions: List[str]
    metadata: Dict[str, Any]
    bm25_score: float
    content_preview: str


class KeywordSearchService:
    """Keyword Search Service for PostgreSQL full-text search with BM25-like scoring"""

    def __init__(self):
        """Initialize keyword search service with PostgreSQL connection"""
        self.postgres_url = os.getenv("POSTGRES_URL", "postgresql://postgres:password@localhost:5432/onyx")
        self.pool = None
        self.timeout = int(os.getenv("KEYWORD_SEARCH_TIMEOUT_MS", 5000)) / 1000.0  # Convert to seconds
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure the database connection pool is initialized"""
        if not self._initialized:
            await self._init_connection_pool()
            self._initialized = True

    async def _init_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=2,
                max_size=10,
                command_timeout=self.timeout,
                server_settings={
                    'application_name': 'onyx-keyword-search',
                    'jit': 'off'  # Disable JIT for consistent query performance
                }
            )
            logger.info(f"Keyword search service initialized with PostgreSQL connection pool")

            # Verify search functions exist
            await self._verify_search_functions()

        except Exception as e:
            logger.error(f"Failed to initialize keyword search service: {e}")
            raise

    async def _verify_search_functions(self):
        """Verify that required search functions exist in the database"""
        try:
            async with self.pool.acquire() as conn:
                # Check if keyword_search function exists
                result = await conn.fetchval("""
                    SELECT 1 FROM information_schema.routines
                    WHERE routine_name = 'keyword_search'
                    AND routine_schema = 'public'
                """)

                if not result:
                    logger.warning("keyword_search function not found - please run migration 004-hybrid-search-keyword.sql")

        except Exception as e:
            logger.error(f"Failed to verify search functions: {e}")

    async def search(
        self,
        query: str,
        user_permissions: List[str] = None,
        source_filter: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        offset: int = 0,
        include_recency_boost: bool = True
    ) -> List[KeywordSearchResult]:
        """
        Perform keyword search with BM25-like scoring

        Args:
            query: Search query string
            user_permissions: List of user permissions/email addresses
            source_filter: Optional filter for document source type
            limit: Maximum number of results to return
            offset: Results offset for pagination
            include_recency_boost: Whether to apply recency boosting

        Returns:
            List of keyword search results with BM25 scores
        """
        await self._ensure_initialized()

        try:
            # Default permissions if not provided
            if user_permissions is None:
                user_permissions = ['*']

            async with self.pool.acquire() as conn:
                # Execute keyword search with BM25 scoring
                query_params = {
                    'query_text': query,
                    'user_permissions': user_permissions,
                    'source_filter': source_filter,
                    'limit_count': limit,
                    'offset_count': offset
                }

                results = await conn.fetch("""
                    SELECT * FROM keyword_search(
                        $1::text,
                        $2::text[],
                        $3::varchar,
                        $4::integer,
                        $5::integer
                    )
                """, query, user_permissions, source_filter, limit, offset)

                # Convert to KeywordSearchResult objects
                search_results = []
                for row in results:
                    result = KeywordSearchResult(
                        doc_id=row['doc_id'],
                        title=row['title'],
                        content=row['content'],
                        source_type=row['source_type'],
                        source_id=row['source_id'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        permissions=row['permissions'],
                        metadata=dict(row['metadata']) if row['metadata'] else {},
                        bm25_score=float(row['bm25_score']),
                        content_preview=row['content_preview']
                    )

                    # Apply recency boost if enabled
                    if include_recency_boost:
                        result.bm25_score = self._apply_recency_boost(
                            result.bm25_score,
                            result.created_at
                        )

                    search_results.append(result)

                # Sort by final score (BM25 score with potential recency boost)
                search_results.sort(key=lambda x: x.bm25_score, reverse=True)

                logger.info(
                    f"Keyword search completed: {len(search_results)} results for query: '{query}' "
                    f"(permissions: {len(user_permissions)}, source_filter: {source_filter})"
                )

                return search_results

        except Exception as e:
            logger.error(f"Keyword search failed for query '{query}': {e}")
            # Return empty results instead of raising to maintain service availability
            return []

    async def phrase_search(
        self,
        phrase: str,
        user_permissions: List[str] = None,
        source_filter: Optional[str] = None,
        limit: int = DEFAULT_SEARCH_LIMIT
    ) -> List[KeywordSearchResult]:
        """
        Perform exact phrase search

        Args:
            phrase: Exact phrase to search for
            user_permissions: List of user permissions/email addresses
            source_filter: Optional filter for document source type
            limit: Maximum number of results to return

        Returns:
            List of phrase search results
        """
        await self._ensure_initialized()

        try:
            # Default permissions if not provided
            if user_permissions is None:
                user_permissions = ['*']

            async with self.pool.acquire() as conn:
                # Execute phrase search
                results = await conn.fetch("""
                    SELECT * FROM phrase_search(
                        $1::text,
                        $2::text[],
                        $3::varchar,
                        $4::integer
                    )
                """, phrase, user_permissions, source_filter, limit)

                # Convert to KeywordSearchResult objects
                search_results = []
                for row in results:
                    search_results.append(KeywordSearchResult(
                        doc_id=row['doc_id'],
                        title=row['title'],
                        content=row['content'],
                        source_type=row['source_type'],
                        source_id=row['source_id'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        permissions=row['permissions'],
                        metadata=dict(row['metadata']) if row['metadata'] else {},
                        bm25_score=float(row['phrase_score']),
                        content_preview=row['content_preview']
                    ))

                logger.info(
                    f"Phrase search completed: {len(search_results)} results for phrase: '{phrase}'"
                )

                return search_results

        except Exception as e:
            logger.error(f"Phrase search failed for phrase '{phrase}': {e}")
            return []

    def _apply_recency_boost(self, score: float, created_at: datetime) -> float:
        """
        Apply recency boost to search score

        Args:
            score: Original BM25 score
            created_at: Document creation timestamp

        Returns:
            Score with recency boost applied
        """
        now = datetime.now(created_at.tzinfo)
        age_days = (now - created_at).days

        if age_days <= RECENCY_BOOST_DAYS:
            return score * RECENCY_BOOST_FACTOR
        else:
            return score

    async def sync_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        source_type: str,
        source_id: str,
        file_path: str = None,
        mime_type: str = None,
        file_size: int = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        permissions: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Sync a document to the keyword search index

        Args:
            doc_id: Unique document identifier
            title: Document title
            content: Document text content
            source_type: Source type (google_drive, slack, upload, web)
            source_id: Source-specific identifier
            file_path: Optional file path
            mime_type: Optional MIME type
            file_size: Optional file size
            created_at: Document creation timestamp
            updated_at: Document update timestamp
            permissions: List of user permissions
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        await self._ensure_initialized()

        try:
            # Set defaults
            if created_at is None:
                created_at = datetime.now()
            if updated_at is None:
                updated_at = datetime.now()
            if permissions is None:
                permissions = ['*']
            if metadata is None:
                metadata = {}

            async with self.pool.acquire() as conn:
                result = await conn.fetchval("""
                    SELECT sync_document_to_search(
                        $1::varchar,
                        $2::text,
                        $3::text,
                        $4::varchar,
                        $5::varchar,
                        $6::text,
                        $7::text,
                        $8::bigint,
                        $9::timestamptz,
                        $10::timestamptz,
                        $11::text[],
                        $12::jsonb
                    )
                """, doc_id, title, content, source_type, source_id, file_path,
                    mime_type, file_size, created_at, updated_at, permissions, metadata)

                success = bool(result)
                if success:
                    logger.debug(f"Document {doc_id} synced to keyword search index")
                else:
                    logger.warning(f"Failed to sync document {doc_id} to keyword search index")

                return success

        except Exception as e:
            logger.error(f"Error syncing document {doc_id} to keyword search: {e}")
            return False

    async def get_document_count(self) -> int:
        """Get total number of documents in the keyword search index"""
        await self._ensure_initialized()

        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval("SELECT COUNT(*) FROM documents_search")
                return count or 0

        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on keyword search service"""
        await self._ensure_initialized()

        try:
            async with self.pool.acquire() as conn:
                # Test basic connection
                await conn.fetchval("SELECT 1")

                # Check if search functions exist
                functions_exist = await conn.fetchval("""
                    SELECT COUNT(*) FROM information_schema.routines
                    WHERE routine_name IN ('keyword_search', 'phrase_search')
                    AND routine_schema = 'public'
                """)

                # Get document count
                doc_count = await self.get_document_count()

                # Get search statistics
                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_docs,
                        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as recent_docs,
                        AVG(content_length) as avg_content_length
                    FROM documents_search
                """)

                health_info = {
                    "status": "healthy",
                    "connection_pool_size": self.pool.get_size(),
                    "search_functions_available": functions_exist >= 2,
                    "document_count": doc_count,
                    "recent_documents_30d": int(stats['recent_docs']) if stats['recent_docs'] else 0,
                    "average_content_length": int(float(stats['avg_content_length'])) if stats['avg_content_length'] else 0,
                    "recency_boost_days": RECENCY_BOOST_DAYS,
                    "recency_boost_factor": RECENCY_BOOST_FACTOR,
                }

                return health_info

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_pool_size": self.pool.get_size() if self.pool else 0
            }

    async def get_search_stats(self) -> Dict[str, Any]:
        """Get detailed search statistics and performance metrics"""
        await self._ensure_initialized()

        try:
            async with self.pool.acquire() as conn:
                stats = await conn.fetch("SELECT * FROM analyze_search_performance()")

                return {row['metric_name']: row['metric_value'] for row in stats}

        except Exception as e:
            logger.error(f"Failed to get search stats: {e}")
            return {}

    async def refresh_stats(self) -> bool:
        """Refresh materialized statistics view"""
        await self._ensure_initialized()

        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT refresh_document_search_stats()")
                logger.info("Document search statistics refreshed")
                return True

        except Exception as e:
            logger.error(f"Failed to refresh search stats: {e}")
            return False

    async def close(self):
        """Close the database connection pool"""
        if self.pool:
            await self.pool.close()
            self._initialized = False
            logger.info("Keyword search service connection pool closed")


# Global keyword search service instance
keyword_search_service = None


async def get_keyword_search_service() -> KeywordSearchService:
    """Get or create keyword search service instance"""
    global keyword_search_service
    if keyword_search_service is None:
        keyword_search_service = KeywordSearchService()
    return keyword_search_service