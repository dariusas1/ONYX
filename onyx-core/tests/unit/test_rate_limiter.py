"""
Unit Tests for Rate Limiter

Tests token bucket rate limiting functionality.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import pytest
from unittest.mock import AsyncMock, patch

from services.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_acquire_token_success():
    """Test successful token acquisition."""
    limiter = RateLimiter()

    with patch.object(limiter.redis, 'get', new=AsyncMock(return_value="50")):
        with patch.object(limiter.redis, 'decr', new=AsyncMock(return_value=49)):
            result = await limiter.acquire_token("serpapi")
            assert result is True


@pytest.mark.asyncio
async def test_acquire_token_initialization():
    """Test token bucket initialization on first use."""
    limiter = RateLimiter()

    with patch.object(limiter.redis, 'get', new=AsyncMock(return_value=None)):
        with patch.object(limiter.redis, 'set', new=AsyncMock(return_value=True)):
            with patch.object(limiter.redis, 'expire', new=AsyncMock(return_value=True)):
                result = await limiter.acquire_token("serpapi")
                assert result is True

                # Verify bucket initialized with correct limit
                limiter.redis.set.assert_called_once_with("ratelimit:serpapi", 100)


@pytest.mark.asyncio
async def test_acquire_token_rate_limited():
    """Test rate limiting when no tokens available."""
    limiter = RateLimiter()

    with patch.object(limiter.redis, 'get', new=AsyncMock(return_value="0")):
        result = await limiter.acquire_token("serpapi")
        assert result is False


@pytest.mark.asyncio
async def test_get_remaining_tokens():
    """Test getting remaining token count."""
    limiter = RateLimiter()

    with patch.object(limiter.redis, 'get', new=AsyncMock(return_value="25")):
        remaining = await limiter.get_remaining_tokens("serpapi")
        assert remaining == 25

    # Uninitialized bucket
    with patch.object(limiter.redis, 'get', new=AsyncMock(return_value=None)):
        remaining = await limiter.get_remaining_tokens("exa")
        assert remaining == 33  # Max tokens for Exa


@pytest.mark.asyncio
async def test_get_reset_time():
    """Test getting token bucket reset time."""
    limiter = RateLimiter()

    # Key exists with TTL
    with patch.object(limiter.redis, 'ttl', new=AsyncMock(return_value=3600)):
        reset_time = await limiter.get_reset_time("serpapi")
        assert reset_time == 3600

    # Key doesn't exist
    with patch.object(limiter.redis, 'ttl', new=AsyncMock(return_value=-2)):
        reset_time = await limiter.get_reset_time("serpapi")
        assert reset_time == 0


@pytest.mark.asyncio
async def test_refill_tokens():
    """Test manual token refill."""
    limiter = RateLimiter()

    with patch.object(limiter.redis, 'set', new=AsyncMock(return_value=True)):
        with patch.object(limiter.redis, 'expire', new=AsyncMock(return_value=True)):
            await limiter.refill_tokens("serpapi")

            # Verify refill with correct values
            limiter.redis.set.assert_called_once_with("ratelimit:serpapi", 100)
            limiter.redis.expire.assert_called_once()


@pytest.mark.asyncio
async def test_reset_all():
    """Test resetting all rate limit buckets."""
    limiter = RateLimiter()

    with patch.object(limiter, 'refill_tokens', new=AsyncMock()):
        await limiter.reset_all()

        # Verify all services were reset
        assert limiter.refill_tokens.call_count == 2  # serpapi + exa


@pytest.mark.asyncio
async def test_unknown_service():
    """Test handling of unknown service."""
    limiter = RateLimiter()

    # Should fail open (return True) for unknown service
    result = await limiter.acquire_token("unknown_service")
    assert result is True

    remaining = await limiter.get_remaining_tokens("unknown_service")
    assert remaining == -1


@pytest.mark.asyncio
async def test_rate_limiter_error_handling():
    """Test error handling in rate limiter."""
    limiter = RateLimiter()

    # Should fail open (allow request) on error
    with patch.object(limiter.redis, 'get', new=AsyncMock(side_effect=Exception("Redis error"))):
        result = await limiter.acquire_token("serpapi")
        assert result is True


@pytest.mark.asyncio
async def test_service_limits_configuration():
    """Test rate limit configuration for different services."""
    limiter = RateLimiter()

    assert limiter.limits["serpapi"]["tokens"] == 100
    assert limiter.limits["serpapi"]["refill_seconds"] == 86400

    assert limiter.limits["exa"]["tokens"] == 33
    assert limiter.limits["exa"]["refill_seconds"] == 86400
