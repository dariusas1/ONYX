"""
Unit Tests for Cache Manager

Tests Redis caching functionality.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from services.cache_manager import CacheManager


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test basic set and get operations."""
    manager = CacheManager()

    test_data = {
        "key": "value",
        "number": 42,
        "list": [1, 2, 3]
    }

    with patch.object(manager.redis, 'setex', new=AsyncMock(return_value=True)):
        with patch.object(manager.redis, 'get', new=AsyncMock(return_value=json.dumps(test_data))):
            # Set value
            result = await manager.set("test_key", test_data, ttl=3600)
            assert result is True

            # Get value
            cached = await manager.get("test_key")
            assert cached == test_data


@pytest.mark.asyncio
async def test_cache_miss():
    """Test cache miss returns None."""
    manager = CacheManager()

    with patch.object(manager.redis, 'get', new=AsyncMock(return_value=None)):
        result = await manager.get("nonexistent_key")
        assert result is None


@pytest.mark.asyncio
async def test_cache_delete():
    """Test cache deletion."""
    manager = CacheManager()

    with patch.object(manager.redis, 'delete', new=AsyncMock(return_value=1)):
        result = await manager.delete("test_key")
        assert result is True


@pytest.mark.asyncio
async def test_cache_exists():
    """Test checking if key exists."""
    manager = CacheManager()

    with patch.object(manager.redis, 'exists', new=AsyncMock(return_value=1)):
        result = await manager.exists("test_key")
        assert result is True

    with patch.object(manager.redis, 'exists', new=AsyncMock(return_value=0)):
        result = await manager.exists("nonexistent_key")
        assert result is False


@pytest.mark.asyncio
async def test_cache_get_ttl():
    """Test getting remaining TTL."""
    manager = CacheManager()

    # Key exists with TTL
    with patch.object(manager.redis, 'ttl', new=AsyncMock(return_value=3600)):
        ttl = await manager.get_ttl("test_key")
        assert ttl == 3600

    # Key doesn't exist
    with patch.object(manager.redis, 'ttl', new=AsyncMock(return_value=-2)):
        ttl = await manager.get_ttl("nonexistent_key")
        assert ttl is None

    # Key exists but no TTL
    with patch.object(manager.redis, 'ttl', new=AsyncMock(return_value=-1)):
        ttl = await manager.get_ttl("test_key")
        assert ttl == -1


@pytest.mark.asyncio
async def test_cache_error_handling():
    """Test error handling in cache operations."""
    manager = CacheManager()

    # Get error
    with patch.object(manager.redis, 'get', new=AsyncMock(side_effect=Exception("Redis error"))):
        result = await manager.get("test_key")
        assert result is None

    # Set error
    with patch.object(manager.redis, 'setex', new=AsyncMock(side_effect=Exception("Redis error"))):
        result = await manager.set("test_key", {"data": "value"})
        assert result is False

    # Delete error
    with patch.object(manager.redis, 'delete', new=AsyncMock(side_effect=Exception("Redis error"))):
        result = await manager.delete("test_key")
        assert result is False


@pytest.mark.asyncio
async def test_cache_json_decode_error():
    """Test handling of JSON decode errors."""
    manager = CacheManager()

    with patch.object(manager.redis, 'get', new=AsyncMock(return_value="invalid json {")):
        result = await manager.get("test_key")
        assert result is None
