"""
Unit Tests for Search Manager

Tests search orchestration, caching, and fallback logic.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from services.search_manager import SearchManager, SearchResult, SearchResultItem


@pytest.mark.asyncio
async def test_search_web_invocation():
    """AC7.2.1: Verify search_web can be invoked."""
    manager = SearchManager()

    mock_results = [
        {
            "title": "Test Result",
            "url": "https://example.com",
            "snippet": "Test snippet",
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": None
        }
    ]

    with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=mock_results)):
        with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
            with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)):
                with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                    result = await manager.search_web(query="test query")

                    assert isinstance(result, SearchResult)
                    assert result.query == "test query"
                    assert result.source == "serpapi"
                    assert len(result.results) == 1


@pytest.mark.asyncio
async def test_search_result_schema():
    """AC7.2.2: Verify result schema has all required fields."""
    manager = SearchManager()

    mock_results = [
        {
            "title": "Test Result",
            "url": "https://example.com/page",
            "snippet": "This is a test snippet with enough text to make it realistic",
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": None
        }
    ]

    with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=mock_results)):
        with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
            with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)):
                with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                    result = await manager.search_web(query="test")

                    # Verify SearchResult schema
                    assert result.query == "test"
                    assert result.source in ["serpapi", "exa"]
                    assert isinstance(result.results, list)
                    assert result.total_results == 1
                    assert result.search_time_ms > 0
                    assert result.cached is False
                    assert isinstance(result.timestamp, datetime)

                    # Verify SearchResultItem schema
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
        "results": [
            {
                "title": "Cached Result",
                "url": "https://example.com",
                "snippet": "Cached snippet",
                "position": 1,
                "domain": "example.com",
                "publish_date": None,
                "relevance_score": None
            }
        ],
        "total_results": 1,
        "timestamp": datetime.utcnow().isoformat()
    }

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=cached_data)):
        result = await manager.search_web(query="cached query")

        assert result.cached is True
        assert result.search_time_ms < 100  # Should be fast
        assert result.query == "cached query"
        assert len(result.results) == 1


@pytest.mark.asyncio
async def test_cache_miss():
    """AC7.2.6: Verify new API call on cache miss."""
    manager = SearchManager()

    mock_results = [
        {
            "title": "New Result",
            "url": "https://example.com",
            "snippet": "New snippet",
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": None
        }
    ]

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
        with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=mock_results)):
            with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)) as mock_set:
                    result = await manager.search_web(query="new query")

                    assert result.cached is False
                    # Verify cache.set was called to cache the result
                    mock_set.assert_called_once()
                    call_args = mock_set.call_args
                    assert call_args[1]['ttl'] == 86400  # 24h


@pytest.mark.asyncio
async def test_serpapi_source_selection():
    """AC7.2.3: Verify SerpAPI is used when source='serpapi'."""
    manager = SearchManager()

    mock_results = [
        {
            "title": "SerpAPI Result",
            "url": "https://example.com",
            "snippet": "SerpAPI snippet",
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": None
        }
    ]

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
        with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)):
            with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=mock_results)) as mock_serpapi:
                    with patch.object(manager.exa, 'search', new=AsyncMock(return_value=[])) as mock_exa:
                        result = await manager.search_web(query="test", source="serpapi")

                        assert result.source == "serpapi"
                        mock_serpapi.assert_called_once()
                        mock_exa.assert_not_called()


@pytest.mark.asyncio
async def test_exa_source_selection():
    """AC7.2.3: Verify Exa is used when source='exa'."""
    manager = SearchManager()

    mock_results = [
        {
            "title": "Exa Result",
            "url": "https://example.com",
            "snippet": "Exa snippet",
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": 0.95
        }
    ]

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
        with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)):
            with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                with patch.object(manager.exa, 'search', new=AsyncMock(return_value=mock_results)) as mock_exa:
                    with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=[])) as mock_serpapi:
                        result = await manager.search_web(query="test", source="exa")

                        assert result.source == "exa"
                        mock_exa.assert_called_once()
                        mock_serpapi.assert_not_called()


@pytest.mark.asyncio
async def test_auto_fallback():
    """AC7.2.3: Verify SerpAPI → Exa fallback when source='auto'."""
    manager = SearchManager()

    exa_results = [
        {
            "title": "Exa Fallback Result",
            "url": "https://example.com",
            "snippet": "Exa fallback snippet",
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": 0.90
        }
    ]

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
        with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)):
            # SerpAPI rate limited, should fallback to Exa
            with patch.object(manager.rate_limiter, 'acquire_token') as mock_rate_limiter:
                # First call (SerpAPI): rate limited (False)
                # Second call (Exa): allowed (True)
                mock_rate_limiter.side_effect = [False, True]

                with patch.object(manager.exa, 'search', new=AsyncMock(return_value=exa_results)):
                    result = await manager.search_web(query="test", source="auto")

                    assert result.source == "exa"
                    assert len(result.results) == 1


@pytest.mark.asyncio
async def test_invalid_query():
    """Test error handling for invalid query."""
    manager = SearchManager()

    with pytest.raises(ValueError, match="Query cannot be empty"):
        await manager.search_web(query="")

    with pytest.raises(ValueError, match="Query cannot be empty"):
        await manager.search_web(query="   ")


@pytest.mark.asyncio
async def test_invalid_num_results():
    """Test error handling for invalid num_results."""
    manager = SearchManager()

    with pytest.raises(ValueError, match="num_results must be between 1 and 10"):
        await manager.search_web(query="test", num_results=0)

    with pytest.raises(ValueError, match="num_results must be between 1 and 10"):
        await manager.search_web(query="test", num_results=11)


@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key normalization."""
    manager = SearchManager()

    # Test query normalization (lowercase, strip)
    key1 = manager._generate_cache_key("Test Query", "auto", None, "google")
    key2 = manager._generate_cache_key("test query", "auto", None, "google")
    key3 = manager._generate_cache_key("  Test Query  ", "auto", None, "google")

    # All should generate the same cache key
    assert key1 == key2 == key3

    # Different sources should generate different keys
    key_serpapi = manager._generate_cache_key("test", "serpapi", None, "google")
    key_exa = manager._generate_cache_key("test", "exa", None, "google")
    assert key_serpapi != key_exa


@pytest.mark.asyncio
async def test_time_range_filtering():
    """AC7.2.5: Verify time range parameter is passed correctly."""
    manager = SearchManager()

    mock_results = [
        {
            "title": "Recent Result",
            "url": "https://example.com",
            "snippet": "Recent snippet",
            "position": 1,
            "domain": "example.com",
            "publish_date": None,
            "relevance_score": None
        }
    ]

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
        with patch.object(manager.cache, 'set', new=AsyncMock(return_value=True)):
            with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=True)):
                with patch.object(manager.serpapi, 'search', new=AsyncMock(return_value=mock_results)) as mock_serpapi:
                    result = await manager.search_web(
                        query="test",
                        source="serpapi",
                        time_range="past_week"
                    )

                    # Verify time_range was passed to SerpAPI client
                    mock_serpapi.assert_called_once()
                    call_args = mock_serpapi.call_args
                    assert call_args[1]['time_range'] == "past_week"


@pytest.mark.asyncio
async def test_all_providers_failed():
    """Test error handling when all providers fail."""
    manager = SearchManager()

    with patch.object(manager.cache, 'get', new=AsyncMock(return_value=None)):
        with patch.object(manager.rate_limiter, 'acquire_token', new=AsyncMock(return_value=False)):
            # All providers rate limited
            with pytest.raises(RuntimeError, match="All search providers failed or rate limited"):
                await manager.search_web(query="test", source="auto")


@pytest.mark.asyncio
async def test_get_search_stats():
    """Test search statistics retrieval."""
    manager = SearchManager()

    with patch.object(manager.rate_limiter, 'get_remaining_tokens') as mock_remaining:
        with patch.object(manager.rate_limiter, 'get_reset_time') as mock_reset:
            mock_remaining.side_effect = [50, 20]  # SerpAPI, then Exa
            mock_reset.side_effect = [3600, 7200]  # SerpAPI, then Exa

            stats = await manager.get_search_stats()

            assert stats["serpapi"]["remaining_tokens"] == 50
            assert stats["serpapi"]["reset_in_seconds"] == 3600
            assert stats["serpapi"]["max_tokens"] == 100

            assert stats["exa"]["remaining_tokens"] == 20
            assert stats["exa"]["reset_in_seconds"] == 7200
            assert stats["exa"]["max_tokens"] == 33
