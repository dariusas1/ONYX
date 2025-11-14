"""
Search Manager Service for ONYX Core

Unified interface for web search using SerpAPI and Exa.
Provides automatic fallback, caching, and rate limiting.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

from typing import Literal, Optional, List
from datetime import datetime
import time
import logging
from pydantic import BaseModel, Field

from .serpapi_client import SerpAPIClient
from .exa_client import ExaClient
from .cache_manager import CacheManager
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SearchResultItem(BaseModel):
    """Individual search result item."""
    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Full URL to page")
    snippet: str = Field(..., description="Excerpt (100-200 chars)")
    position: int = Field(..., description="Ranking position (1-based)")
    domain: str = Field(..., description="Domain extracted from URL")
    publish_date: Optional[datetime] = Field(None, description="Publication date if available")
    relevance_score: Optional[float] = Field(None, description="Exa relevance score (0-1)")


class SearchResult(BaseModel):
    """Search result with metadata."""
    query: str = Field(..., description="Original search query")
    source: Literal["serpapi", "exa"] = Field(..., description="Actual provider used")
    results: List[SearchResultItem] = Field(..., description="List of search results")
    total_results: int = Field(..., description="Total number of results")
    search_time_ms: int = Field(..., description="Total execution time in milliseconds")
    cached: bool = Field(..., description="Whether result was from cache")
    timestamp: datetime = Field(..., description="When search was executed")


class SearchManager:
    """Unified search manager for SerpAPI and Exa."""

    def __init__(self):
        """Initialize search manager with all dependencies."""
        self.serpapi = SerpAPIClient()
        self.exa = ExaClient()
        self.cache = CacheManager()
        self.rate_limiter = RateLimiter()
        logger.info("SearchManager initialized")

    async def search_web(
        self,
        query: str,
        source: Literal["serpapi", "exa", "auto"] = "auto",
        num_results: int = 5,
        time_range: Optional[Literal["past_day", "past_week", "past_month", "past_year"]] = None,
        engine: Literal["google", "bing"] = "google"
    ) -> SearchResult:
        """
        Search the web using SerpAPI or Exa.

        Args:
            query: Search query string
            source: Search provider ("serpapi", "exa", or "auto" for fallback)
            num_results: Number of results to return (default: 5, max: 10)
            time_range: Filter by time range (optional)
            engine: Search engine for SerpAPI (google or bing)

        Returns:
            SearchResult with results and metadata

        Raises:
            ValueError: Invalid parameters
            RuntimeError: All search providers failed
        """
        start_time = time.time()

        # Validate parameters
        if not query or len(query.strip()) == 0:
            raise ValueError("Query cannot be empty")
        if num_results < 1 or num_results > 10:
            raise ValueError("num_results must be between 1 and 10")

        logger.info(f"Web search request: query='{query}', source={source}, num_results={num_results}")

        # Check cache first
        cache_key = self._generate_cache_key(query, source, time_range, engine)
        cached_result = await self.cache.get(cache_key)

        if cached_result:
            logger.info(f"Cache hit for query: {query}")
            search_time_ms = int((time.time() - start_time) * 1000)
            cached_result["cached"] = True
            cached_result["search_time_ms"] = search_time_ms
            return SearchResult(**cached_result)

        logger.info(f"Cache miss for query: {query}, source: {source}")

        # Execute search with fallback
        result_data = None
        last_error = None

        try:
            if source == "serpapi" or source == "auto":
                # Try SerpAPI first
                if await self.rate_limiter.acquire_token("serpapi"):
                    try:
                        result_data = await self._search_serpapi(query, num_results, time_range, engine)
                        logger.info(f"SerpAPI search successful for query: {query}")
                    except Exception as e:
                        logger.warning(f"SerpAPI search failed: {e}")
                        last_error = e
                        if source == "serpapi":
                            raise  # Don't fallback if explicitly requested SerpAPI
                else:
                    logger.warning("SerpAPI rate limited")
                    if source == "serpapi":
                        raise RuntimeError("SerpAPI rate limited")

            # Fallback to Exa if SerpAPI failed or source is exa/auto
            if result_data is None and (source == "exa" or source == "auto"):
                if await self.rate_limiter.acquire_token("exa"):
                    try:
                        result_data = await self._search_exa(query, num_results, time_range)
                        logger.info(f"Exa search successful for query: {query}")
                    except Exception as e:
                        logger.warning(f"Exa search failed: {e}")
                        last_error = e
                        if source == "exa":
                            raise  # Don't fallback if explicitly requested Exa
                else:
                    logger.warning("Exa rate limited")
                    if source == "exa":
                        raise RuntimeError("Exa rate limited")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Search failed: {e}") from e

        # Check if we got results
        if result_data is None:
            error_msg = "All search providers failed or rate limited"
            if last_error:
                error_msg = f"{error_msg}: {last_error}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Calculate timing
        search_time_ms = int((time.time() - start_time) * 1000)
        result_data["search_time_ms"] = search_time_ms
        result_data["cached"] = False
        result_data["timestamp"] = datetime.utcnow()

        # Cache result for 24h
        await self.cache.set(cache_key, result_data, ttl=86400)  # 24h in seconds

        logger.info(
            f"Search completed: query='{query}', source={result_data['source']}, "
            f"results={len(result_data['results'])}, time={search_time_ms}ms"
        )

        return SearchResult(**result_data)

    async def _search_serpapi(
        self,
        query: str,
        num_results: int,
        time_range: Optional[str],
        engine: str
    ) -> dict:
        """
        Execute search via SerpAPI.

        Args:
            query: Search query
            num_results: Number of results
            time_range: Time range filter
            engine: Search engine (google or bing)

        Returns:
            Search result dict
        """
        logger.info(f"Executing SerpAPI search (engine: {engine})")
        results = await self.serpapi.search(
            query=query,
            engine=engine,
            num=num_results,
            time_range=time_range
        )
        return {
            "query": query,
            "source": "serpapi",
            "results": results,
            "total_results": len(results)
        }

    async def _search_exa(
        self,
        query: str,
        num_results: int,
        time_range: Optional[str]
    ) -> dict:
        """
        Execute search via Exa.

        Args:
            query: Search query
            num_results: Number of results
            time_range: Time range filter

        Returns:
            Search result dict
        """
        logger.info("Executing Exa semantic search")
        results = await self.exa.search(
            query=query,
            num_results=num_results,
            time_range=time_range,
            use_autoprompt=True
        )
        return {
            "query": query,
            "source": "exa",
            "results": results,
            "total_results": len(results)
        }

    def _generate_cache_key(
        self,
        query: str,
        source: str,
        time_range: Optional[str],
        engine: str
    ) -> str:
        """
        Generate cache key from search parameters.

        Cache keys are normalized (lowercase, stripped) to maximize cache hits.

        Args:
            query: Search query
            source: Search source
            time_range: Time range filter
            engine: Search engine

        Returns:
            Cache key string
        """
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()

        # Build cache key
        key_parts = [
            "search",
            source,
            normalized_query,
            time_range or "all",
            engine if source == "serpapi" else ""
        ]

        # Filter out empty parts and join
        cache_key = ":".join(filter(None, key_parts))

        logger.debug(f"Generated cache key: {cache_key}")
        return cache_key

    async def get_search_stats(self) -> dict:
        """
        Get search statistics (rate limit status, etc.).

        Returns:
            Dictionary with search statistics
        """
        serpapi_remaining = await self.rate_limiter.get_remaining_tokens("serpapi")
        exa_remaining = await self.rate_limiter.get_remaining_tokens("exa")
        serpapi_reset = await self.rate_limiter.get_reset_time("serpapi")
        exa_reset = await self.rate_limiter.get_reset_time("exa")

        return {
            "serpapi": {
                "remaining_tokens": serpapi_remaining,
                "reset_in_seconds": serpapi_reset,
                "max_tokens": 100
            },
            "exa": {
                "remaining_tokens": exa_remaining,
                "reset_in_seconds": exa_reset,
                "max_tokens": 33
            }
        }

    async def close(self):
        """Close all connections and cleanup resources."""
        try:
            await self.serpapi.close()
            await self.exa.close()
            await self.cache.close()
            await self.rate_limiter.close()
            logger.info("SearchManager connections closed")
        except Exception as e:
            logger.error(f"Error closing SearchManager connections: {e}")
