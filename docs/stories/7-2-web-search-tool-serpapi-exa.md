# Story 7-2: Web Search Tool (SerpAPI or Exa)

**Story ID:** 7-2-web-search-tool-serpapi-exa
**Epic:** Epic 7 - Web Automation & Search
**Status:** drafted
**Priority:** P0 (Foundation - Independent)
**Estimated Effort:** 5 Story Points
**Sprint:** Sprint 7
**Owner:** TBD
**Created:** 2025-11-14

---

## User Story

**As a** Manus Internal agent
**I want** to search the web using SerpAPI (Google/Bing) or Exa (semantic search)
**So that** I can find current information, research topics, and gather external intelligence for strategic decision-making

---

## Context

This story implements the web search capability for Epic 7 (Web Automation & Search). Web search is a critical tool that enables Manus to access current information beyond its knowledge cutoff, research market trends, analyze competitor information, and gather intelligence from the broader internet. Unlike browser-based scraping (Story 7-3), this story focuses on structured search results from premium APIs.

The web search tool provides two complementary capabilities:
1. **SerpAPI** - Traditional Google/Bing search for broad information discovery
2. **Exa** - Semantic/neural search for finding conceptually related content

This is an independent story with no dependencies on browser automation (Story 7-1), making it ideal for parallel development.

### Why This Matters

Without web search capabilities, Manus cannot:
- Answer questions about recent events or current information
- Research competitors or market trends
- Find documentation, articles, or technical resources
- Verify information against external sources
- Conduct market intelligence or competitive analysis

Web search transforms Manus from a static knowledge base into a dynamic intelligence platform that can actively research and discover information on demand.

---

## Technical Context

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Onyx Core (Python) - Tool Orchestration               │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Search Manager: search_web(query, source, ...)  │ │
│  │                → SerpAPI → Google/Bing results    │ │
│  │                → Exa API → Semantic results       │ │
│  └───────────────────────────────────────────────────┘ │
└────┬──────────────────────┬───────────────────────┬─────┘
     │                      │                       │
     ↓                      ↓                       ↓
┌─────────┐          ┌──────────┐          ┌──────────────┐
│ SerpAPI │          │ Exa AI   │          │ Redis Cache  │
│ Google  │          │ Semantic │          │ 24h TTL      │
│ Bing    │          │ Search   │          │              │
└─────────┘          └──────────┘          └──────────────┘
```

### Key Components

1. **Search Manager** (`onyx-core/services/search_manager.py`):
   - Unified interface for multiple search providers
   - Automatic fallback from SerpAPI to Exa if one fails
   - Query parameter handling (time range, result count)
   - Result normalization into standard schema
   - Caching integration with Redis (24h TTL)

2. **SerpAPI Integration** (`onyx-core/services/serpapi_client.py`):
   - Google Search via SerpAPI REST API
   - Bing Search support (alternative engine)
   - Result parsing and normalization
   - Error handling for API failures
   - Rate limiting (100 searches/day)

3. **Exa Integration** (`onyx-core/services/exa_client.py`):
   - Semantic/neural search via Exa API
   - Autoprompt feature for query optimization
   - Relevance scoring and ranking
   - Result parsing and normalization
   - Rate limiting (1000 searches/month → ~33/day)

4. **Cache Layer** (`onyx-core/services/cache_manager.py`):
   - Redis-backed caching with 24h TTL
   - Cache key generation from query + parameters
   - Cache hit/miss tracking for metrics
   - Automatic eviction (LRU policy)

5. **Rate Limiter** (`onyx-core/services/rate_limiter.py`):
   - Token bucket algorithm per API
   - SerpAPI: 100 searches/day → ~4/hour
   - Exa: 1000 searches/month → ~33/day
   - Queue requests when rate limited
   - Background token refill job

### Data Models

**SearchRequest Schema:**
```python
class SearchRequest(BaseModel):
    query: str
    source: Literal["serpapi", "exa", "auto"] = "auto"
    num_results: int = 5
    time_range: Optional[Literal["past_day", "past_week", "past_month", "past_year"]] = None
    engine: Optional[Literal["google", "bing"]] = "google"  # SerpAPI only
    use_autoprompt: bool = True  # Exa only
```

**SearchResult Schema:**
```python
class SearchResult(BaseModel):
    query: str
    source: Literal["serpapi", "exa"]
    results: List[SearchResultItem]
    total_results: int
    search_time_ms: int
    cached: bool
    timestamp: datetime

class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str  # 100-200 chars
    position: int
    domain: str
    publish_date: Optional[datetime]
    relevance_score: Optional[float]  # Exa only
```

### Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| SerpAPI search | <2s | External API dependency |
| Exa search | <3s | External API dependency |
| Cache hit | <50ms | Redis lookup |
| Result parsing | <100ms | For 10 results |
| Total latency (cache miss) | <3s | Including API call + parsing |

### API Credentials

**Environment Variables Required:**
```bash
SERPAPI_API_KEY=your_serpapi_key_here
EXA_API_KEY=your_exa_key_here
REDIS_URL=redis://localhost:6379/0
```

**API Limits:**
- **SerpAPI**: 100 searches/day ($50/month plan)
- **Exa**: 1000 searches/month ($20/month plan)
- **Redis**: Self-hosted, unlimited

---

## Acceptance Criteria

### AC7.2.1: Agent Can Invoke search_web Tool With Query Parameter
**Given** the Onyx Core system is running
**When** the agent calls `search_web(query="Anthropic Claude pricing")`
**Then** the search tool is invoked successfully
**And** the query parameter is validated and processed
**And** a search request is sent to the configured search provider
**And** results are returned in the standard SearchResult schema

**Verification:**
- Unit test: `test_search_web_invocation()` verifies tool can be called
- Integration test: Search with "test query" returns valid SearchResult object
- Log verification: Search request logged with query, source, timestamp

---

### AC7.2.2: Returns Top-5 Results With Title, URL, Snippet, Domain, Position
**Given** a search has been executed successfully
**When** the results are returned
**Then** the response contains up to 5 search results (or fewer if less available)
**And** each result includes: title, url, snippet, domain, position
**And** snippet is 100-200 characters long
**And** position is numbered 1-5 (ranking order)
**And** domain is extracted from URL (e.g., "anthropic.com" from "https://www.anthropic.com/pricing")

**Verification:**
- Unit test: `test_search_result_schema()` validates all required fields present
- Integration test: Search returns exactly 5 results (or fewer for niche queries)
- Field validation: title non-empty, url valid HTTP/HTTPS, snippet 100-200 chars
- Position test: Verify positions are 1, 2, 3, 4, 5 in order

---

### AC7.2.3: Results From Google/Bing via SerpAPI or Semantic Search via Exa
**Given** the search tool is configured with API keys
**When** source="serpapi" is specified
**Then** results are fetched from Google via SerpAPI
**When** source="exa" is specified
**Then** results are fetched via Exa semantic search
**When** source="auto" is specified
**Then** SerpAPI is tried first, with fallback to Exa if it fails
**And** the actual source used is indicated in the response

**Verification:**
- Integration test: `test_serpapi_search()` verifies SerpAPI integration
- Integration test: `test_exa_search()` verifies Exa integration
- Integration test: `test_auto_fallback()` verifies SerpAPI → Exa fallback
- Mock test: Verify correct API endpoint called based on source parameter

---

### AC7.2.4: Latency <3s for Search API Calls (External Dependency)
**Given** the search tool is under normal load
**When** a search is executed (cache miss)
**Then** the total operation completes in <3s (95th percentile)
**And** SerpAPI calls complete in <2s (external dependency)
**And** Exa calls complete in <3s (external dependency)
**And** result parsing adds <100ms overhead

**Verification:**
- Performance test: 50 searches with timing, verify p95 <3s
- Latency logging: Log search_time_ms for all requests
- Metrics: Track p50, p95, p99 latencies in production
- Alert: Trigger if p95 exceeds 3s for sustained period

---

### AC7.2.5: Supports Time Range Filtering (Past Week/Month/Year)
**Given** a search request includes time_range parameter
**When** time_range="past_week" is specified
**Then** results are filtered to past 7 days (where supported by API)
**When** time_range="past_month" is specified
**Then** results are filtered to past 30 days
**When** time_range="past_year" is specified
**Then** results are filtered to past 365 days
**When** time_range is not specified
**Then** no time filtering is applied (all results)

**Verification:**
- Unit test: `test_time_range_filtering()` for each time range option
- Integration test: Search with time_range="past_week" returns recent results
- SerpAPI test: Verify `tbs=qdr:w` parameter passed for past week
- Exa test: Time range filtering via start_published_date parameter
- Validation: Results have publish_date within specified range (where available)

---

### AC7.2.6: Results Cached for 24h to Minimize API Costs
**Given** a search has been executed
**When** the same query is searched again within 24 hours
**Then** results are returned from Redis cache (no API call)
**And** cached=true is indicated in the response
**And** cache hit completes in <50ms
**When** 24 hours have passed
**Then** cache entry expires and new API call is made
**And** new results are cached for next 24h

**Verification:**
- Unit test: `test_cache_hit()` verifies cached results returned
- Unit test: `test_cache_miss()` verifies new API call on cache miss
- Integration test: First search cached=false, second search cached=true
- Performance test: Cache hit <50ms, cache miss ~2-3s
- TTL test: Verify cache expires after 24h (mock Redis TTL)
- Metrics: Track cache hit rate (target: >70%)

---

## Implementation Details

### Step 1: Search Manager Service

**File:** `onyx-core/services/search_manager.py`

```python
from typing import Literal, Optional
from datetime import datetime
import time
import logging
from pydantic import BaseModel
from .serpapi_client import SerpAPIClient
from .exa_client import ExaClient
from .cache_manager import CacheManager
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    position: int
    domain: str
    publish_date: Optional[datetime] = None
    relevance_score: Optional[float] = None

class SearchResult(BaseModel):
    query: str
    source: Literal["serpapi", "exa"]
    results: list[SearchResultItem]
    total_results: int
    search_time_ms: int
    cached: bool
    timestamp: datetime

class SearchManager:
    """Unified search manager for SerpAPI and Exa."""

    def __init__(self):
        self.serpapi = SerpAPIClient()
        self.exa = ExaClient()
        self.cache = CacheManager()
        self.rate_limiter = RateLimiter()

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
            num_results: Number of results to return (default: 5)
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
        try:
            if source == "serpapi" or source == "auto":
                # Try SerpAPI first
                if await self.rate_limiter.acquire_token("serpapi"):
                    result = await self._search_serpapi(query, num_results, time_range, engine)
                else:
                    logger.warning("SerpAPI rate limited, trying Exa")
                    if source == "serpapi":
                        raise RuntimeError("SerpAPI rate limited")
                    source = "exa"

            if source == "exa" or (source == "auto" and not result):
                # Try Exa
                if await self.rate_limiter.acquire_token("exa"):
                    result = await self._search_exa(query, num_results, time_range)
                else:
                    raise RuntimeError("Exa rate limited")

        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Try fallback if auto mode
            if source == "auto":
                try:
                    if await self.rate_limiter.acquire_token("exa"):
                        result = await self._search_exa(query, num_results, time_range)
                    else:
                        raise RuntimeError("All search providers rate limited or failed")
                except Exception as fallback_error:
                    logger.error(f"Fallback search also failed: {fallback_error}")
                    raise RuntimeError("All search providers failed") from e
            else:
                raise

        # Calculate timing
        search_time_ms = int((time.time() - start_time) * 1000)
        result["search_time_ms"] = search_time_ms
        result["cached"] = False
        result["timestamp"] = datetime.utcnow()

        # Cache result for 24h
        await self.cache.set(cache_key, result, ttl=86400)  # 24h in seconds

        logger.info(f"Search completed: {query}, source: {result['source']}, "
                   f"results: {len(result['results'])}, time: {search_time_ms}ms")

        return SearchResult(**result)

    async def _search_serpapi(
        self,
        query: str,
        num_results: int,
        time_range: Optional[str],
        engine: str
    ) -> dict:
        """Execute search via SerpAPI."""
        logger.info(f"Searching via SerpAPI (engine: {engine})")
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
        """Execute search via Exa."""
        logger.info("Searching via Exa (semantic search)")
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
        """Generate cache key from search parameters."""
        # Normalize query (lowercase, strip whitespace)
        normalized_query = query.lower().strip()
        key_parts = [
            "search",
            source,
            normalized_query,
            time_range or "all",
            engine if source == "serpapi" else ""
        ]
        return ":".join(filter(None, key_parts))
```

### Step 2: SerpAPI Client

**File:** `onyx-core/services/serpapi_client.py`

```python
import os
import aiohttp
from typing import Optional, List
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class SerpAPIClient:
    """Client for SerpAPI (Google/Bing search)."""

    def __init__(self):
        self.api_key = os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY environment variable not set")

        self.base_url = "https://serpapi.com/search"

    async def search(
        self,
        query: str,
        engine: str = "google",
        num: int = 5,
        time_range: Optional[str] = None
    ) -> List[dict]:
        """
        Search via SerpAPI.

        Args:
            query: Search query
            engine: Search engine (google or bing)
            num: Number of results
            time_range: Time range filter

        Returns:
            List of search result items
        """
        # Build parameters
        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": engine,
            "num": num
        }

        # Add time range filter (Google only)
        if time_range and engine == "google":
            time_map = {
                "past_day": "qdr:d",
                "past_week": "qdr:w",
                "past_month": "qdr:m",
                "past_year": "qdr:y"
            }
            if time_range in time_map:
                params["tbs"] = time_map[time_range]

        logger.debug(f"SerpAPI request: {params}")

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"SerpAPI error: {response.status} - {error_text}")

                data = await response.json()

        # Parse results
        results = []
        organic_results = data.get("organic_results", [])

        for idx, item in enumerate(organic_results[:num], start=1):
            # Extract domain from URL
            url = item.get("link", "")
            domain = self._extract_domain(url)

            result = {
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("snippet", "")[:200],  # Truncate to 200 chars
                "position": idx,
                "domain": domain,
                "publish_date": None,  # SerpAPI doesn't always provide this
                "relevance_score": None  # Not available in SerpAPI
            }
            results.append(result)

        logger.info(f"SerpAPI returned {len(results)} results")
        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""
```

### Step 3: Exa Client

**File:** `onyx-core/services/exa_client.py`

```python
import os
import aiohttp
from typing import Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ExaClient:
    """Client for Exa AI semantic search."""

    def __init__(self):
        self.api_key = os.getenv("EXA_API_KEY")
        if not self.api_key:
            raise ValueError("EXA_API_KEY environment variable not set")

        self.base_url = "https://api.exa.ai/search"

    async def search(
        self,
        query: str,
        num_results: int = 5,
        time_range: Optional[str] = None,
        use_autoprompt: bool = True
    ) -> List[dict]:
        """
        Search via Exa semantic search.

        Args:
            query: Search query
            num_results: Number of results
            time_range: Time range filter
            use_autoprompt: Use Exa's autoprompt feature

        Returns:
            List of search result items
        """
        # Build request body
        body = {
            "query": query,
            "num_results": num_results,
            "use_autoprompt": use_autoprompt,
            "type": "neural"  # Semantic search
        }

        # Add time range filter
        if time_range:
            start_date = self._calculate_start_date(time_range)
            body["start_published_date"] = start_date.isoformat()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.debug(f"Exa request: {body}")

        # Make API request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Exa error: {response.status} - {error_text}")

                data = await response.json()

        # Parse results
        results = []
        exa_results = data.get("results", [])

        for idx, item in enumerate(exa_results[:num_results], start=1):
            # Extract domain from URL
            url = item.get("url", "")
            domain = self._extract_domain(url)

            result = {
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("text", "")[:200],  # Truncate to 200 chars
                "position": idx,
                "domain": domain,
                "publish_date": self._parse_date(item.get("published_date")),
                "relevance_score": item.get("score")  # Exa provides relevance scores
            }
            results.append(result)

        logger.info(f"Exa returned {len(results)} results")
        return results

    def _calculate_start_date(self, time_range: str) -> datetime:
        """Calculate start date from time range."""
        now = datetime.utcnow()
        if time_range == "past_day":
            return now - timedelta(days=1)
        elif time_range == "past_week":
            return now - timedelta(days=7)
        elif time_range == "past_month":
            return now - timedelta(days=30)
        elif time_range == "past_year":
            return now - timedelta(days=365)
        return now

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""
```

### Step 4: Cache Manager

**File:** `onyx-core/services/cache_manager.py`

```python
import redis.asyncio as redis
import json
import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis-backed cache manager."""

    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[dict]:
        """Get cached value."""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: dict, ttl: int = 86400) -> bool:
        """Set cached value with TTL."""
        try:
            await self.redis.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
```

### Step 5: Rate Limiter

**File:** `onyx-core/services/rate_limiter.py`

```python
import redis.asyncio as redis
import os
import logging
from typing import Literal

logger = logging.getLogger(__name__)

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)

        # Rate limits per service
        self.limits = {
            "serpapi": {"tokens": 100, "refill_seconds": 86400},  # 100/day
            "exa": {"tokens": 33, "refill_seconds": 86400}  # ~33/day (1000/month)
        }

    async def acquire_token(self, service: Literal["serpapi", "exa"]) -> bool:
        """
        Acquire a rate limit token.

        Args:
            service: Service name

        Returns:
            True if token acquired, False if rate limited
        """
        key = f"ratelimit:{service}"

        try:
            # Get current token count
            tokens = await self.redis.get(key)

            if tokens is None:
                # Initialize bucket
                limit = self.limits[service]["tokens"]
                await self.redis.set(key, limit)
                tokens = limit

            tokens = int(tokens)

            if tokens > 0:
                # Consume token
                await self.redis.decr(key)
                logger.debug(f"Rate limit token acquired for {service}, remaining: {tokens - 1}")
                return True
            else:
                logger.warning(f"Rate limit exceeded for {service}")
                return False

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open (allow request if rate limiter fails)
            return True

    async def refill_tokens(self, service: Literal["serpapi", "exa"]) -> None:
        """Refill tokens for a service (called by background job)."""
        key = f"ratelimit:{service}"
        limit = self.limits[service]["tokens"]
        await self.redis.set(key, limit)
        logger.info(f"Rate limit tokens refilled for {service}: {limit}")
```

---

## Dependencies

### Blocking Dependencies
- **Epic 1**: Redis infrastructure for caching

### External Dependencies
- **SerpAPI**: Account with API key ($50/month, 100 searches/day)
- **Exa AI**: Account with API key ($20/month, 1000 searches/month)
- **Redis**: Self-hosted (from Epic 1)

### Package Dependencies

```python
# requirements.txt additions
aiohttp==3.9.0  # Async HTTP client
redis==5.0.0  # Redis client (already in Epic 1)
pydantic==2.5.0  # Data validation (already in project)
```

---

## Testing Strategy

### Unit Tests

**File:** `onyx-core/tests/unit/test_search_manager.py`

```python
import pytest
from services.search_manager import SearchManager, SearchResult
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_search_web_invocation():
    """AC7.2.1: Verify search_web can be invoked."""
    manager = SearchManager()

    with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=[])):
        with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
            with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                result = await manager.search_web(query="test query")

                assert isinstance(result, SearchResult)
                assert result.query == "test query"

@pytest.mark.asyncio
async def test_search_result_schema():
    """AC7.2.2: Verify result schema has all required fields."""
    manager = SearchManager()

    mock_results = [
        {
            "title": "Test Result",
            "url": "https://example.com/page",
            "snippet": "This is a test snippet" * 5,  # ~100 chars
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": None
        }
    ]

    with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=mock_results)):
        with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
            with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                result = await manager.search_web(query="test")

                assert len(result.results) == 1
                item = result.results[0]
                assert item.title == "Test Result"
                assert item.url == "https://example.com/page"
                assert len(item.snippet) <= 200
                assert item.position == 1
                assert item.domain == "example.com"

@pytest.mark.asyncio
async def test_cache_hit():
    """AC7.2.6: Verify cached results returned on cache hit."""
    manager = SearchManager()

    cached_data = {
        "query": "cached query",
        "source": "serpapi",
        "results": [],
        "total_results": 0,
        "timestamp": "2025-11-14T10:00:00"
    }

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=cached_data)):
        result = await manager.search_web(query="cached query")

        assert result.cached == True
        assert result.search_time_ms < 100  # Should be fast

@pytest.mark.asyncio
async def test_cache_miss():
    """AC7.2.6: Verify new API call on cache miss."""
    manager = SearchManager()

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
        with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=[])):
            with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)):
                    result = await manager.search_web(query="new query")

                    assert result.cached == False
                    # Verify cache.set was called to cache the result
                    manager.cache.set.assert_called_once()
```

### Integration Tests

**File:** `onyx-core/tests/integration/test_search_integration.py`

```python
import pytest
import os
from services.search_manager import SearchManager

# Only run if API keys are set
pytestmark = pytest.mark.skipif(
    not os.getenv("SERPAPI_API_KEY") or not os.getenv("EXA_API_KEY"),
    reason="API keys not configured"
)

@pytest.mark.asyncio
@pytest.mark.slow
async def test_serpapi_search():
    """AC7.2.3: Verify SerpAPI integration works."""
    manager = SearchManager()

    result = await manager.search_web(
        query="Python programming language",
        source="serpapi",
        num_results=5
    )

    assert result.source == "serpapi"
    assert len(result.results) <= 5
    assert result.search_time_ms < 3000  # <3s target

    # Verify result structure
    for item in result.results:
        assert len(item.title) > 0
        assert item.url.startswith("http")
        assert len(item.snippet) <= 200
        assert item.domain != ""

@pytest.mark.asyncio
@pytest.mark.slow
async def test_exa_search():
    """AC7.2.3: Verify Exa integration works."""
    manager = SearchManager()

    result = await manager.search_web(
        query="artificial intelligence recent developments",
        source="exa",
        num_results=5
    )

    assert result.source == "exa"
    assert len(result.results) <= 5
    assert result.search_time_ms < 3000  # <3s target

    # Exa should provide relevance scores
    for item in result.results:
        assert item.relevance_score is not None

@pytest.mark.asyncio
async def test_time_range_filtering():
    """AC7.2.5: Verify time range filtering works."""
    manager = SearchManager()

    result = await manager.search_web(
        query="tech news",
        source="serpapi",
        time_range="past_week"
    )

    assert result.source == "serpapi"
    # Results should be from past week (if publish_date available)

@pytest.mark.asyncio
async def test_performance_latency():
    """AC7.2.4: Verify latency <3s for search operations."""
    import time
    manager = SearchManager()

    latencies = []

    for i in range(10):
        start = time.time()
        result = await manager.search_web(query=f"test query {i}", source="serpapi")
        latency = time.time() - start
        latencies.append(latency)

    # Calculate p95
    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95)]

    assert p95 < 3.0, f"p95 latency {p95:.2f}s should be <3s"
```

---

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **API quota exhaustion** | High | Aggressive 24h caching, rate limiting, fallback between APIs |
| **API key exposure** | High | Store in environment variables, never log keys, encrypt at rest |
| **API downtime** | Medium | Automatic fallback from SerpAPI to Exa, graceful error handling |
| **Rate limit exceeded** | Medium | Token bucket algorithm, queue requests, alert when near limit |
| **Cache poisoning** | Low | Validate cached data before returning, TTL limits stale data |
| **Slow API response** | Low | 10s timeout on API calls, return partial results if available |

---

## Definition of Done

- [ ] Search Manager service implemented with unified interface
- [ ] SerpAPI integration complete with Google/Bing support
- [ ] Exa integration complete with semantic search
- [ ] Cache layer integrated with 24h TTL
- [ ] Rate limiter implemented with token bucket algorithm
- [ ] All 6 acceptance criteria verified and passing
- [ ] Unit tests: >90% coverage of search logic
- [ ] Integration tests: Real API calls (with API keys)
- [ ] Performance tests: p95 latency <3s verified
- [ ] Documentation: API usage documented in code
- [ ] Environment variables: API keys documented in .env.example
- [ ] Error handling: All API failures handled gracefully
- [ ] Code review: Approved by senior engineer
- [ ] Merged to main branch and deployed to staging

---

## Notes

### API Selection Rationale
- **SerpAPI** chosen for broad Google/Bing search coverage
- **Exa** chosen for semantic/neural search capabilities
- **Auto fallback** provides resilience and best-of-both-worlds

### Cost Management
- Aggressive caching (24h TTL) minimizes API costs
- Rate limiting prevents quota exhaustion
- SerpAPI: 100 searches/day = $50/month
- Exa: 1000 searches/month = $20/month
- **Total cost: $70/month for 130+ searches/day**

### Performance Optimization
- Cache hits return in <50ms (vs. 2-3s for API calls)
- Target >70% cache hit rate in production
- Parallel API calls not needed (serial is fast enough)

### Security Considerations
- API keys stored in environment variables (never in code)
- No query logging (privacy)
- Rate limiting prevents abuse
- Cache isolated per user (future enhancement)

---

## Related Stories

- **Story 7-1**: Playwright Browser Setup - Independent (no dependency)
- **Story 7-3**: URL Scraping & Content Extraction - Uses search results as input
- **Story 7-4**: Form Filling & Web Interaction - Independent
- **Story 7-5**: Screenshot & Page Capture - Independent

---

## References

- Epic 7 Technical Specification: `/home/user/ONYX/docs/epics/epic-7-tech-spec.md`
- PRD Section F6: Web Automation & Search
- SerpAPI Documentation: https://serpapi.com/search-api
- Exa AI Documentation: https://docs.exa.ai/reference/search
- Redis Caching: https://redis.io/docs/manual/client-side-caching/

---

## Development Notes

### Implementation Checklist

**Phase 1: Core Infrastructure (Day 1)**
- [ ] Create SearchManager service with unified interface
- [ ] Implement cache manager with Redis integration
- [ ] Implement rate limiter with token bucket algorithm
- [ ] Set up environment variables for API keys

**Phase 2: API Integrations (Day 2)**
- [ ] Implement SerpAPI client with Google/Bing support
- [ ] Implement Exa client with semantic search
- [ ] Add time range filtering for both providers
- [ ] Implement automatic fallback logic

**Phase 3: Testing (Day 3)**
- [ ] Write unit tests for search manager
- [ ] Write unit tests for SerpAPI client
- [ ] Write unit tests for Exa client
- [ ] Write integration tests (with real API calls)
- [ ] Write performance tests (p95 latency)

**Phase 4: Integration & Deployment (Day 4)**
- [ ] Integrate with Onyx Core tool system
- [ ] Add tool registration for Agent Mode
- [ ] Documentation and code review
- [ ] Deploy to staging and test end-to-end
- [ ] Monitor API usage and cache hit rates

### API Key Setup

**SerpAPI:**
1. Sign up at https://serpapi.com/
2. Choose plan: $50/month (100 searches/day)
3. Copy API key
4. Add to `.env`: `SERPAPI_API_KEY=your_key_here`

**Exa AI:**
1. Sign up at https://exa.ai/
2. Choose plan: $20/month (1000 searches/month)
3. Copy API key
4. Add to `.env`: `EXA_API_KEY=your_key_here`

**Redis:**
- Already configured from Epic 1
- Default: `REDIS_URL=redis://localhost:6379/0`

### Testing Without API Keys

For development without API keys, mock the external APIs:

```python
# In tests, mock the API clients
with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=mock_results)):
    result = await manager.search_web(query="test")
```

### Cost Monitoring

Monitor API usage daily to avoid unexpected costs:
- SerpAPI dashboard: https://serpapi.com/dashboard
- Exa dashboard: https://dashboard.exa.ai/
- Track cache hit rate (target: >70%)
- Alert if daily quota >80% consumed

---

**Story Created:** 2025-11-14
**Last Updated:** 2025-11-14
**Status:** drafted
