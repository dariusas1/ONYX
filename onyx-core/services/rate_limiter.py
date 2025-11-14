"""
Rate Limiter Service for ONYX Core

Implements token bucket algorithm for API rate limiting using Redis.
Prevents API quota exhaustion for SerpAPI and Exa services.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import redis.asyncio as redis
import os
import logging
from typing import Literal
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for external API calls."""

    def __init__(self):
        """Initialize Redis connection and rate limits."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)

        # Rate limits per service (conservative to avoid quota exhaustion)
        self.limits = {
            "serpapi": {
                "tokens": 100,  # 100 searches per day
                "refill_seconds": 86400,  # Refill daily
                "description": "SerpAPI Google/Bing search"
            },
            "exa": {
                "tokens": 33,  # ~33 searches per day (1000/month)
                "refill_seconds": 86400,  # Refill daily
                "description": "Exa semantic search"
            }
        }

        logger.info("RateLimiter initialized with limits: serpapi=100/day, exa=33/day")

    async def acquire_token(self, service: Literal["serpapi", "exa"]) -> bool:
        """
        Acquire a rate limit token for a service.

        Uses token bucket algorithm: consume a token if available,
        otherwise reject the request.

        Args:
            service: Service name ("serpapi" or "exa")

        Returns:
            True if token acquired (request allowed), False if rate limited
        """
        if service not in self.limits:
            logger.error(f"Unknown service for rate limiting: {service}")
            return True  # Fail open (allow request for unknown services)

        key = f"ratelimit:{service}"

        try:
            # Get current token count
            tokens = await self.redis.get(key)

            if tokens is None:
                # Initialize bucket with max tokens
                limit = self.limits[service]["tokens"]
                await self.redis.set(key, limit)
                # Set expiration for auto-refill
                await self.redis.expire(key, self.limits[service]["refill_seconds"])
                tokens = limit
                logger.info(f"Rate limit bucket initialized for {service}: {limit} tokens")

            tokens = int(tokens) if tokens else 0

            # Atomically decrement first, then check result
            # This prevents race conditions under concurrent load
            new_count = await self.redis.decr(key)

            if new_count >= 0:
                # Token successfully acquired
                logger.debug(f"Rate limit token acquired for {service}, remaining: {new_count}")
                return True
            else:
                # We went negative - restore the token
                await self.redis.incr(key)
                logger.warning(f"Rate limit exceeded for {service}")
                return False

        except Exception as e:
            logger.error(f"Rate limiter error for {service}: {e}")
            # Fail open (allow request if rate limiter fails)
            return True

    async def get_remaining_tokens(self, service: Literal["serpapi", "exa"]) -> int:
        """
        Get remaining tokens for a service.

        Args:
            service: Service name

        Returns:
            Number of remaining tokens, or -1 if error
        """
        if service not in self.limits:
            logger.error(f"Unknown service: {service}")
            return -1

        key = f"ratelimit:{service}"

        try:
            tokens = await self.redis.get(key)
            if tokens is None:
                # Bucket not initialized yet
                return self.limits[service]["tokens"]
            return int(tokens)
        except Exception as e:
            logger.error(f"Error getting remaining tokens for {service}: {e}")
            return -1

    async def get_reset_time(self, service: Literal["serpapi", "exa"]) -> int:
        """
        Get time until token bucket resets (in seconds).

        Args:
            service: Service name

        Returns:
            Seconds until reset, or -1 if error
        """
        if service not in self.limits:
            logger.error(f"Unknown service: {service}")
            return -1

        key = f"ratelimit:{service}"

        try:
            ttl = await self.redis.ttl(key)
            if ttl == -2:  # Key doesn't exist
                return 0  # Will reset immediately when initialized
            if ttl == -1:  # Key exists but no expiration
                return 0
            return ttl
        except Exception as e:
            logger.error(f"Error getting reset time for {service}: {e}")
            return -1

    async def refill_tokens(self, service: Literal["serpapi", "exa"]) -> None:
        """
        Manually refill tokens for a service.

        This is typically called by a background job, but Redis expiration
        handles automatic refill in normal operation.

        Args:
            service: Service name
        """
        if service not in self.limits:
            logger.error(f"Unknown service: {service}")
            return

        key = f"ratelimit:{service}"
        limit = self.limits[service]["tokens"]
        refill_seconds = self.limits[service]["refill_seconds"]

        try:
            await self.redis.set(key, limit)
            await self.redis.expire(key, refill_seconds)
            logger.info(f"Rate limit tokens refilled for {service}: {limit} tokens")
        except Exception as e:
            logger.error(f"Error refilling tokens for {service}: {e}")

    async def reset_all(self) -> None:
        """Reset all rate limit buckets (for testing)."""
        try:
            for service in self.limits.keys():
                await self.refill_tokens(service)
            logger.info("All rate limit buckets reset")
        except Exception as e:
            logger.error(f"Error resetting rate limits: {e}")

    async def close(self):
        """Close Redis connection."""
        try:
            await self.redis.close()
            logger.info("RateLimiter connection closed")
        except Exception as e:
            logger.error(f"Error closing RateLimiter connection: {e}")
