"""
SerpAPI Client for ONYX Core

Integrates with SerpAPI for Google and Bing web search.
Provides structured search results with automatic result normalization.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import os
import aiohttp
from typing import Optional, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class SerpAPIClient:
    """Client for SerpAPI (Google/Bing search)."""

    def __init__(self):
        """Initialize SerpAPI client."""
        self.api_key = os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            logger.warning("SERPAPI_API_KEY environment variable not set")
            # Don't raise error here - allow service to start without API key
            # Error will be raised when search() is called

        self.base_url = "https://serpapi.com/search"
        self.session = None  # Lazy-initialized aiohttp session for connection reuse
        logger.info("SerpAPIClient initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session for connection reuse.

        Returns:
            Active aiohttp ClientSession
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp session for SerpAPI")
        return self.session

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
            query: Search query string
            engine: Search engine ("google" or "bing")
            num: Number of results to return (1-10)
            time_range: Time range filter (past_day, past_week, past_month, past_year)

        Returns:
            List of search result items with normalized schema

        Raises:
            ValueError: If API key not configured
            RuntimeError: If API call fails
        """
        if not self.api_key:
            raise ValueError("SERPAPI_API_KEY environment variable not set")

        # Build request parameters
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
                logger.debug(f"SerpAPI time filter applied: {time_range} -> {time_map[time_range]}")

        logger.info(f"SerpAPI search: query='{query}', engine={engine}, num={num}")

        # Make API request (reuse session for better performance)
        try:
            session = await self._get_session()
            async with session.get(
                self.base_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"SerpAPI error: {response.status} - {error_text}")
                    raise RuntimeError(f"SerpAPI error: {response.status} - {error_text}")

                data = await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"SerpAPI connection error: {e}")
            raise RuntimeError(f"SerpAPI connection error: {e}") from e
        except Exception as e:
            logger.error(f"SerpAPI unexpected error: {e}")
            raise RuntimeError(f"SerpAPI unexpected error: {e}") from e

        # Parse results
        results = []
        organic_results = data.get("organic_results", [])

        for idx, item in enumerate(organic_results[:num], start=1):
            # Extract domain from URL
            url = item.get("link", "")
            domain = self._extract_domain(url)

            # Get snippet (truncate to 200 chars)
            snippet = item.get("snippet", "")
            if len(snippet) > 200:
                # Truncate at word boundary, handle edge case of no spaces
                parts = snippet[:200].rsplit(" ", 1)
                snippet = parts[0] + "..." if len(parts) > 1 else snippet[:197] + "..."

            result = {
                "title": item.get("title", ""),
                "url": url,
                "snippet": snippet,
                "position": idx,
                "domain": domain,
                "publish_date": None,  # SerpAPI doesn't always provide this
                "relevance_score": None  # Not available in SerpAPI
            }
            results.append(result)

        logger.info(f"SerpAPI returned {len(results)} results")
        return results

    def _extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain name (without www. prefix)
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception as e:
            logger.warning(f"Failed to extract domain from URL '{url}': {e}")
            return ""

    async def test_connection(self) -> bool:
        """
        Test SerpAPI connection and API key validity.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.api_key:
            logger.error("Cannot test connection: API key not set")
            return False

        try:
            # Simple test query
            results = await self.search(query="test", num=1)
            logger.info("SerpAPI connection test successful")
            return True
        except Exception as e:
            logger.error(f"SerpAPI connection test failed: {e}")
            return False

    async def close(self):
        """Close aiohttp session and cleanup resources."""
        if self.session is not None and not self.session.closed:
            await self.session.close()
            logger.debug("SerpAPI aiohttp session closed")
