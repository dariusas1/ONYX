"""
Integration Tests for Search Services

Tests real API integrations with SerpAPI and Exa (requires API keys).
Tests are skipped if API keys are not configured.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import pytest
import os
import time
import asyncio
from datetime import datetime

from services.search_manager import SearchManager
from services.serpapi_client import SerpAPIClient
from services.exa_client import ExaClient
from services.cache_manager import CacheManager
from services.rate_limiter import RateLimiter


# Skip all tests if API keys are not configured
pytestmark = pytest.mark.skipif(
    not os.getenv("SERPAPI_API_KEY") or not os.getenv("EXA_API_KEY"),
    reason="API keys not configured (SERPAPI_API_KEY or EXA_API_KEY missing)"
)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_serpapi_search():
    """AC7.2.3: Verify SerpAPI integration works."""
    manager = SearchManager()

    try:
        result = await manager.search_web(
            query="Python programming language",
            source="serpapi",
            num_results=5
        )

        # Verify search succeeded
        assert result.source == "serpapi"
        assert len(result.results) <= 5
        assert result.search_time_ms < 3000  # <3s target (AC7.2.4)

        # Verify result structure (AC7.2.2)
        for item in result.results:
            assert len(item.title) > 0
            assert item.url.startswith("http")
            assert len(item.snippet) <= 200
            assert item.domain != ""
            assert item.position >= 1
            assert item.position <= 5

        print(f"✓ SerpAPI search successful: {len(result.results)} results in {result.search_time_ms}ms")

    finally:
        await manager.close()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_exa_search():
    """AC7.2.3: Verify Exa integration works."""
    manager = SearchManager()

    try:
        result = await manager.search_web(
            query="artificial intelligence recent developments",
            source="exa",
            num_results=5
        )

        # Verify search succeeded
        assert result.source == "exa"
        assert len(result.results) <= 5
        assert result.search_time_ms < 3000  # <3s target (AC7.2.4)

        # Verify result structure (AC7.2.2)
        for item in result.results:
            assert len(item.title) > 0
            assert item.url.startswith("http")
            assert len(item.snippet) <= 200
            assert item.domain != ""
            # Exa should provide relevance scores
            assert item.relevance_score is not None

        print(f"✓ Exa search successful: {len(result.results)} results in {result.search_time_ms}ms")

    finally:
        await manager.close()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_time_range_filtering():
    """AC7.2.5: Verify time range filtering works."""
    manager = SearchManager()

    try:
        result = await manager.search_web(
            query="tech news",
            source="serpapi",
            time_range="past_week"
        )

        assert result.source == "serpapi"
        assert len(result.results) > 0

        print(f"✓ Time range filtering successful: {len(result.results)} results from past week")

    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_cache_integration():
    """AC7.2.6: Verify cache hit/miss cycle."""
    manager = SearchManager()

    try:
        # First search - should be cache miss
        result1 = await manager.search_web(
            query="unique test query 12345",
            source="serpapi",
            num_results=3
        )

        assert result1.cached is False
        first_search_time = result1.search_time_ms

        # Second search - should be cache hit
        result2 = await manager.search_web(
            query="unique test query 12345",
            source="serpapi",
            num_results=3
        )

        assert result2.cached is True
        assert result2.search_time_ms < 100  # Should be fast (<50ms target)
        assert result2.search_time_ms < first_search_time  # Should be faster than API call

        print(f"✓ Cache integration successful:")
        print(f"  Cache miss: {first_search_time}ms")
        print(f"  Cache hit: {result2.search_time_ms}ms")

    finally:
        await manager.close()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_performance_latency():
    """AC7.2.4: Verify latency <3s for search operations."""
    manager = SearchManager()

    try:
        latencies = []

        # Run 10 searches (limited to avoid quota consumption)
        for i in range(10):
            start = time.time()
            result = await manager.search_web(
                query=f"test query {i}",
                source="serpapi",
                num_results=3
            )
            latency = time.time() - start
            latencies.append(latency)

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        # Calculate percentiles
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.5)]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"✓ Performance test results:")
        print(f"  p50: {p50:.2f}s")
        print(f"  p95: {p95:.2f}s")
        print(f"  p99: {p99:.2f}s")

        # Verify p95 latency <3s
        assert p95 < 3.0, f"p95 latency {p95:.2f}s should be <3s"

    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality."""
    limiter = RateLimiter()

    try:
        # Reset rate limits
        await limiter.reset_all()

        # Check initial state
        remaining = await limiter.get_remaining_tokens("serpapi")
        assert remaining == 100

        # Acquire token
        result = await limiter.acquire_token("serpapi")
        assert result is True

        # Check decremented
        remaining = await limiter.get_remaining_tokens("serpapi")
        assert remaining == 99

        print(f"✓ Rate limiting functional: {remaining} tokens remaining")

    finally:
        await limiter.close()


@pytest.mark.asyncio
async def test_serpapi_client_directly():
    """Test SerpAPI client directly."""
    client = SerpAPIClient()

    results = await client.search(
        query="OpenAI",
        engine="google",
        num=3
    )

    assert len(results) <= 3
    for result in results:
        assert "title" in result
        assert "url" in result
        assert "snippet" in result
        assert "domain" in result

    print(f"✓ SerpAPI client test successful: {len(results)} results")


@pytest.mark.asyncio
async def test_exa_client_directly():
    """Test Exa client directly."""
    client = ExaClient()

    results = await client.search(
        query="machine learning frameworks",
        num_results=3,
        use_autoprompt=True
    )

    assert len(results) <= 3
    for result in results:
        assert "title" in result
        assert "url" in result
        assert "snippet" in result
        assert "domain" in result
        assert "relevance_score" in result

    print(f"✓ Exa client test successful: {len(results)} results")


@pytest.mark.asyncio
async def test_auto_fallback():
    """AC7.2.3: Test automatic fallback from SerpAPI to Exa."""
    manager = SearchManager()

    try:
        # This should try SerpAPI first, then Exa if needed
        result = await manager.search_web(
            query="test auto fallback",
            source="auto",
            num_results=3
        )

        # Should get results from one of the sources
        assert result.source in ["serpapi", "exa"]
        assert len(result.results) > 0

        print(f"✓ Auto fallback test successful: used {result.source}")

    finally:
        await manager.close()


@pytest.mark.asyncio
async def test_cache_manager_integration():
    """Test cache manager with Redis."""
    cache = CacheManager()

    try:
        # Set value
        test_data = {
            "key": "value",
            "timestamp": datetime.utcnow().isoformat()
        }

        success = await cache.set("test:integration:key", test_data, ttl=60)
        assert success is True

        # Get value
        cached = await cache.get("test:integration:key")
        assert cached is not None
        assert cached["key"] == "value"

        # Check exists
        exists = await cache.exists("test:integration:key")
        assert exists is True

        # Get TTL
        ttl = await cache.get_ttl("test:integration:key")
        assert ttl is not None
        assert ttl > 0

        # Delete
        deleted = await cache.delete("test:integration:key")
        assert deleted is True

        # Verify deleted
        cached = await cache.get("test:integration:key")
        assert cached is None

        print("✓ Cache manager integration test successful")

    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_search_stats():
    """Test search statistics retrieval."""
    manager = SearchManager()

    try:
        stats = await manager.get_search_stats()

        assert "serpapi" in stats
        assert "exa" in stats

        assert "remaining_tokens" in stats["serpapi"]
        assert "reset_in_seconds" in stats["serpapi"]
        assert "max_tokens" in stats["serpapi"]

        print(f"✓ Search stats test successful:")
        print(f"  SerpAPI: {stats['serpapi']['remaining_tokens']}/{stats['serpapi']['max_tokens']} tokens")
        print(f"  Exa: {stats['exa']['remaining_tokens']}/{stats['exa']['max_tokens']} tokens")

    finally:
        await manager.close()
