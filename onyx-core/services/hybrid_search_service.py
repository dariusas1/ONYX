"""
Hybrid Search Service Module

This module provides hybrid search functionality that combines semantic vector search
with keyword BM25 search for optimal relevance and performance.
"""

import os
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from .rag_service import RAGService, SearchResult
from .keyword_search_service import KeywordSearchService, KeywordSearchResult

logger = logging.getLogger(__name__)

# Constants
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3
DEFAULT_HYBRID_LIMIT = 5
DEFAULT_SEARCH_TIMEOUT_MS = 200
RECENCY_BOOST_DAYS = 30
RECENCY_BOOST_FACTOR = 1.10


@dataclass
class HybridSearchResult:
    """Data class for hybrid search results with combined scoring"""

    doc_id: str
    title: str
    content: str
    source_type: str
    source_id: str
    created_at: datetime
    updated_at: datetime
    permissions: List[str]
    metadata: Dict[str, Any]
    semantic_score: float
    keyword_score: float
    combined_score: float
    content_preview: str
    rank: int


class HybridSearchService:
    """Hybrid Search Service combining semantic and keyword search with result fusion"""

    def __init__(self):
        """Initialize hybrid search service"""
        self.semantic_weight = float(os.getenv("SEMANTIC_WEIGHT", SEMANTIC_WEIGHT))
        self.keyword_weight = float(os.getenv("KEYWORD_WEIGHT", KEYWORD_WEIGHT))
        self.timeout_ms = int(os.getenv("HYBRID_SEARCH_TIMEOUT_MS", DEFAULT_SEARCH_TIMEOUT_MS))
        self.recency_boost_days = int(os.getenv("RECENCY_BOOST_DAYS", RECENCY_BOOST_DAYS))
        self.recency_boost_factor = float(os.getenv("RECENCY_BOOST_FACTOR", RECENCY_BOOST_FACTOR))
        self.default_limit = int(os.getenv("HYBRID_SEARCH_DEFAULT_LIMIT", DEFAULT_HYBRID_LIMIT))

        # Services will be initialized lazily
        self.rag_service = None
        self.keyword_search_service = None

        # Performance tracking
        self._search_stats = {
            'total_searches': 0,
            'total_latency_ms': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

    async def _ensure_services_initialized(self):
        """Ensure search services are initialized"""
        if self.rag_service is None:
            from ..rag_service import get_rag_service
            self.rag_service = await get_rag_service()

        if self.keyword_search_service is None:
            from .keyword_search_service import get_keyword_search_service
            self.keyword_search_service = await get_keyword_search_service()

    async def search(
        self,
        query: str,
        user_permissions: List[str] = None,
        source_filter: Optional[str] = None,
        limit: int = None,
        include_recency_boost: bool = True,
        query_type: str = "auto"  # auto, semantic, keyword, hybrid
    ) -> List[HybridSearchResult]:
        """
        Execute hybrid search combining semantic and keyword approaches

        Args:
            query: Search query string
            user_permissions: List of user permissions/email addresses
            source_filter: Optional filter for document source type
            limit: Maximum number of results to return
            include_recency_boost: Whether to apply recency boosting
            query_type: Type of search to perform

        Returns:
            List of hybrid search results with combined scores
        """
        await self._ensure_services_initialized()

        if limit is None:
            limit = self.default_limit

        start_time = time.time()

        try:
            # Default permissions if not provided
            if user_permissions is None:
                user_permissions = ['*']

            # Determine search strategy based on query type
            if query_type == "semantic":
                results = await self._semantic_only_search(
                    query, user_permissions, source_filter, limit, include_recency_boost
                )
            elif query_type == "keyword":
                results = await self._keyword_only_search(
                    query, user_permissions, source_filter, limit, include_recency_boost
                )
            else:  # auto or hybrid
                results = await self._hybrid_search(
                    query, user_permissions, source_filter, limit, include_recency_boost
                )

            # Update performance stats
            latency_ms = (time.time() - start_time) * 1000
            self._update_performance_stats(latency_ms)

            logger.info(
                f"Hybrid search completed in {latency_ms:.2f}ms: {len(results)} results "
                f"for query: '{query}' (type: {query_type})"
            )

            return results

        except Exception as e:
            logger.error(f"Hybrid search failed for query '{query}': {e}")
            # Return empty results instead of raising to maintain service availability
            return []

    async def _hybrid_search(
        self,
        query: str,
        user_permissions: List[str],
        source_filter: Optional[str],
        limit: int,
        include_recency_boost: bool
    ) -> List[HybridSearchResult]:
        """Execute parallel hybrid search combining semantic and keyword approaches"""

        # Execute both searches in parallel
        tasks = [
            self._execute_semantic_search(query, user_permissions, source_filter),
            self._execute_keyword_search(query, user_permissions, source_filter, include_recency_boost)
        ]

        try:
            semantic_results, keyword_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout_ms / 1000.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"Hybrid search timeout after {self.timeout_ms}ms for query: '{query}'")
            # Fallback to semantic search only
            return await self._semantic_only_search(query, user_permissions, source_filter, limit, include_recency_boost)

        # Handle exceptions from individual searches
        if isinstance(semantic_results, Exception):
            logger.error(f"Semantic search failed: {semantic_results}")
            semantic_results = []
        if isinstance(keyword_results, Exception):
            logger.error(f"Keyword search failed: {keyword_results}")
            keyword_results = []

        # Fuse results with combined scoring
        fused_results = self._fuse_results(
            semantic_results, keyword_results, include_recency_boost
        )

        # Return top results
        return fused_results[:limit]

    async def _semantic_only_search(
        self,
        query: str,
        user_permissions: List[str],
        source_filter: Optional[str],
        limit: int,
        include_recency_boost: bool
    ) -> List[HybridSearchResult]:
        """Execute semantic search only"""

        semantic_results = await self._execute_semantic_search(query, user_permissions, source_filter)

        # Convert semantic results to hybrid results format
        hybrid_results = []
        for i, result in enumerate(semantic_results[:limit]):
            combined_score = result.score * self.semantic_weight

            if include_recency_boost:
                combined_score = self._apply_recency_boost(combined_score, result.metadata.get('created_at'))

            hybrid_result = HybridSearchResult(
                doc_id=result.doc_id,
                title=result.title,
                content=result.text,
                source_type=result.source,
                source_id=result.metadata.get('source_id', ''),
                created_at=result.metadata.get('created_at', datetime.now()),
                updated_at=result.metadata.get('updated_at', datetime.now()),
                permissions=result.metadata.get('permissions', ['*']),
                metadata=result.metadata,
                semantic_score=result.score,
                keyword_score=0.0,
                combined_score=combined_score,
                content_preview=result.text[:200] + "..." if len(result.text) > 200 else result.text,
                rank=i + 1
            )
            hybrid_results.append(hybrid_result)

        return hybrid_results

    async def _keyword_only_search(
        self,
        query: str,
        user_permissions: List[str],
        source_filter: Optional[str],
        limit: int,
        include_recency_boost: bool
    ) -> List[HybridSearchResult]:
        """Execute keyword search only"""

        keyword_results = await self._execute_keyword_search(
            query, user_permissions, source_filter, include_recency_boost
        )

        # Convert keyword results to hybrid results format
        hybrid_results = []
        for i, result in enumerate(keyword_results[:limit]):
            combined_score = result.bm25_score * self.keyword_weight

            if include_recency_boost:
                combined_score = self._apply_recency_boost(combined_score, result.created_at)

            hybrid_result = HybridSearchResult(
                doc_id=result.doc_id,
                title=result.title,
                content=result.content,
                source_type=result.source_type,
                source_id=result.source_id,
                created_at=result.created_at,
                updated_at=result.updated_at,
                permissions=result.permissions,
                metadata=result.metadata,
                semantic_score=0.0,
                keyword_score=result.bm25_score,
                combined_score=combined_score,
                content_preview=result.content_preview,
                rank=i + 1
            )
            hybrid_results.append(hybrid_result)

        return hybrid_results

    async def _execute_semantic_search(
        self,
        query: str,
        user_permissions: List[str],
        source_filter: Optional[str]
    ) -> List[SearchResult]:
        """Execute semantic search using RAG service"""

        # Note: RAG service uses user_email for permissions, we need to convert
        user_email = user_permissions[0] if user_permissions and user_permissions != ['*'] else None

        # Set appropriate top_k for more candidates (we'll filter later)
        semantic_results = await self.rag_service.search(
            query=query,
            top_k=10,  # Get more candidates for better fusion
            source_filter=source_filter,
            user_email=user_email,
            score_threshold=0.3  # Lower threshold for more candidates
        )

        return semantic_results

    async def _execute_keyword_search(
        self,
        query: str,
        user_permissions: List[str],
        source_filter: Optional[str],
        include_recency_boost: bool = True
    ) -> List[KeywordSearchResult]:
        """Execute keyword search using keyword search service"""

        keyword_results = await self.keyword_search_service.search(
            query=query,
            user_permissions=user_permissions,
            source_filter=source_filter,
            limit=10,  # Get more candidates for better fusion
            include_recency_boost=include_recency_boost
        )

        return keyword_results

    def _fuse_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[KeywordSearchResult],
        include_recency_boost: bool = True
    ) -> List[HybridSearchResult]:
        """
        Fuse semantic and keyword search results with weighted scoring

        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            include_recency_boost: Whether to apply recency boosting

        Returns:
            Fused and ranked hybrid search results
        """
        merged_docs = {}  # doc_id -> HybridSearchResult

        # Process semantic results
        for result in semantic_results:
            doc_id = result.doc_id
            created_at = result.metadata.get('created_at', datetime.now())

            hybrid_result = HybridSearchResult(
                doc_id=result.doc_id,
                title=result.title,
                content=result.text,
                source_type=result.source,
                source_id=result.metadata.get('source_id', ''),
                created_at=created_at,
                updated_at=result.metadata.get('updated_at', datetime.now()),
                permissions=result.metadata.get('permissions', ['*']),
                metadata=result.metadata,
                semantic_score=result.score,
                keyword_score=0.0,
                combined_score=result.score * self.semantic_weight,
                content_preview=result.text[:200] + "..." if len(result.text) > 200 else result.text,
                rank=0  # Will be assigned after sorting
            )

            # Apply recency boost if enabled
            if include_recency_boost:
                hybrid_result.combined_score = self._apply_recency_boost(
                    hybrid_result.combined_score, created_at
                )

            merged_docs[doc_id] = hybrid_result

        # Merge keyword results
        for result in keyword_results:
            doc_id = result.doc_id

            if doc_id in merged_docs:
                # Update existing document with keyword score
                existing = merged_docs[doc_id]
                existing.keyword_score = result.bm25_score
                existing.combined_score = (
                    existing.semantic_score * self.semantic_weight +
                    result.bm25_score * self.keyword_weight
                )

                # Apply recency boost again with updated combined score
                if include_recency_boost:
                    existing.combined_score = self._apply_recency_boost(
                        existing.combined_score, result.created_at
                    )
            else:
                # Add new document from keyword search
                combined_score = result.bm25_score * self.keyword_weight

                if include_recency_boost:
                    combined_score = self._apply_recency_boost(combined_score, result.created_at)

                hybrid_result = HybridSearchResult(
                    doc_id=result.doc_id,
                    title=result.title,
                    content=result.content,
                    source_type=result.source_type,
                    source_id=result.source_id,
                    created_at=result.created_at,
                    updated_at=result.updated_at,
                    permissions=result.permissions,
                    metadata=result.metadata,
                    semantic_score=0.0,
                    keyword_score=result.bm25_score,
                    combined_score=combined_score,
                    content_preview=result.content_preview,
                    rank=0  # Will be assigned after sorting
                )

                merged_docs[doc_id] = hybrid_result

        # Convert to list and sort by combined score
        fused_results = list(merged_docs.values())
        fused_results.sort(key=lambda x: x.combined_score, reverse=True)

        # Assign ranks
        for i, result in enumerate(fused_results):
            result.rank = i + 1

        return fused_results

    def _apply_recency_boost(self, score: float, created_at: datetime) -> float:
        """Apply recency boost to search score"""
        if created_at is None:
            return score

        now = datetime.now(created_at.tzinfo)
        age_days = (now - created_at).days

        if age_days <= self.recency_boost_days:
            return score * self.recency_boost_factor
        else:
            return score

    def _update_performance_stats(self, latency_ms: float):
        """Update performance statistics"""
        self._search_stats['total_searches'] += 1
        self._search_stats['total_latency_ms'] += latency_ms

    def classify_query_type(self, query: str) -> str:
        """
        Classify query type for optimal search strategy

        Args:
            query: Search query string

        Returns:
            Query type classification: semantic, keyword, or mixed
        """
        query_lower = query.lower()

        # Keyword-dominant indicators
        keyword_indicators = [
            'project-', 'ticket-', 'bug-', 'issue-', 'doc-', 'file-',
            '@', '#', 'http', 'www.', '.com', '.org',
            'date:', 'from:', 'to:', 'subject:', 'file:',
            'exact phrase', "in quotes", 'contains'
        ]

        # Semantic-dominant indicators
        semantic_indicators = [
            'what is', 'how to', 'why does', 'explain', 'describe',
            'summarize', 'compare', 'analyze', 'best practices',
            'overview', 'introduction', 'guide'
        ]

        # Count indicators
        keyword_count = sum(1 for indicator in keyword_indicators if indicator in query_lower)
        semantic_count = sum(1 for indicator in semantic_indicators if indicator in query_lower)

        # Check for quoted phrases (indicates exact match preference)
        if '"' in query:
            keyword_count += 2

        # Check for email addresses, URLs, IDs
        import re
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', query):
            keyword_count += 2
        if re.search(r'https?://', query):
            keyword_count += 2

        # Classify based on indicator counts
        if keyword_count > semantic_count + 1:
            return "keyword"
        elif semantic_count > keyword_count + 1:
            return "semantic"
        else:
            return "mixed"

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check on hybrid search service"""
        await self._ensure_services_initialized()

        try:
            # Get health status from both services
            semantic_health = await self.rag_service.health_check()
            keyword_health = await self.keyword_search_service.health_check()

            # Calculate average latency
            avg_latency_ms = (
                self._search_stats['total_latency_ms'] /
                max(1, self._search_stats['total_searches'])
            )

            health_info = {
                "status": "healthy" if (
                    semantic_health.get("status") == "healthy" and
                    keyword_health.get("status") == "healthy"
                ) else "degraded",
                "configuration": {
                    "semantic_weight": self.semantic_weight,
                    "keyword_weight": self.keyword_weight,
                    "timeout_ms": self.timeout_ms,
                    "recency_boost_days": self.recency_boost_days,
                    "recency_boost_factor": self.recency_boost_factor,
                    "default_limit": self.default_limit
                },
                "services": {
                    "semantic_search": semantic_health,
                    "keyword_search": keyword_health
                },
                "performance": {
                    "total_searches": self._search_stats['total_searches'],
                    "average_latency_ms": round(avg_latency_ms, 2),
                    "cache_hits": self._search_stats['cache_hits'],
                    "cache_misses": self._search_stats['cache_misses']
                }
            }

            return health_info

        except Exception as e:
            logger.error(f"Hybrid search health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics"""
        await self._ensure_services_initialized()

        try:
            # Get stats from both services
            keyword_stats = await self.keyword_search_service.get_search_stats()

            stats = {
                "hybrid_search": {
                    "total_searches": self._search_stats['total_searches'],
                    "average_latency_ms": round(
                        self._search_stats['total_latency_ms'] /
                        max(1, self._search_stats['total_searches']), 2
                    ) if self._search_stats['total_searches'] > 0 else 0,
                    "cache_hits": self._search_stats['cache_hits'],
                    "cache_misses": self._search_stats['cache_misses'],
                    "configuration": {
                        "semantic_weight": self.semantic_weight,
                        "keyword_weight": self.keyword_weight,
                        "timeout_ms": self.timeout_ms
                    }
                },
                "keyword_search": keyword_stats
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {}

    async def close(self):
        """Close all service connections"""
        if self.keyword_search_service:
            await self.keyword_search_service.close()

        # RAG service doesn't have a close method currently
        logger.info("Hybrid search service closed")


# Global hybrid search service instance
hybrid_search_service = None


async def get_hybrid_search_service() -> HybridSearchService:
    """Get or create hybrid search service instance"""
    global hybrid_search_service
    if hybrid_search_service is None:
        hybrid_search_service = HybridSearchService()
    return hybrid_search_service