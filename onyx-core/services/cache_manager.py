"""
Cache Manager Service for ONYX Core

Provides Redis-backed caching with TTL support for search results and other data.
Used by SearchManager to cache API results and minimize external API costs.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import redis.asyncio as redis
import json
import os
import logging
from typing import Optional, Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis-backed cache manager for search results and general caching."""

    def __init__(self):
        """Initialize Redis connection."""
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        logger.info(f"CacheManager initialized with Redis URL: {self._mask_url_credentials(redis_url)}")

    def _mask_url_credentials(self, url: str) -> str:
        """
        Mask password in URL for secure logging.

        Args:
            url: Redis URL that may contain credentials

        Returns:
            URL with password masked as ***
        """
        try:
            parsed = urlparse(url)
            if parsed.password:
                # Replace password with ***
                netloc = f"{parsed.username or ''}:***@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                masked = parsed._replace(netloc=netloc)
                return urlunparse(masked)
            return url
        except Exception as e:
            logger.debug(f"Failed to mask URL credentials: {e}")
            return "redis://***"

    async def get(self, key: str) -> Optional[dict]:
        """
        Get cached value from Redis.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value as dict if found, None otherwise
        """
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(value)
            logger.debug(f"Cache miss for key: {key}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Cache get JSON decode error for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: dict, ttl: int = 86400) -> bool:
        """
        Set cached value in Redis with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 86400 = 24 hours)

        Returns:
            True if set successfully, False otherwise
        """
        try:
            # Convert datetime objects to ISO format strings
            json_value = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, json_value)
            logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete cached value from Redis.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            await self.redis.delete(key)
            logger.debug(f"Cache delete for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        try:
            result = await self.redis.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Cache exists check error for key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, None if key doesn't exist or error
        """
        try:
            ttl = await self.redis.ttl(key)
            if ttl == -2:  # Key doesn't exist
                return None
            if ttl == -1:  # Key exists but no TTL
                return -1
            return ttl
        except Exception as e:
            logger.error(f"Cache TTL check error for key {key}: {e}")
            return None

    async def close(self):
        """Close Redis connection."""
        try:
            await self.redis.close()
            logger.info("CacheManager connection closed")
        except Exception as e:
            logger.error(f"Error closing CacheManager connection: {e}")
