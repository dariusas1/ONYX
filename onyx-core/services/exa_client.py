"""
Exa Client for ONYX Core

Integrates with Exa AI for semantic/neural web search.
Provides relevance-scored search results with autoprompt optimization.

Author: ONYX Core Team
Story: 7-2-web-search-tool-serpapi-exa
"""

import os
import aiohttp
from typing import Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ExaClient:
    """Client for Exa AI semantic search."""

    def __init__(self):
        """Initialize Exa client."""
        self.api_key = os.getenv("EXA_API_KEY")
        if not self.api_key:
            logger.warning("EXA_API_KEY environment variable not set")
            # Don't raise error here - allow service to start without API key
            # Error will be raised when search() is called

        self.base_url = "https://api.exa.ai/search"
        self.session = None  # Lazy-initialized aiohttp session for connection reuse
        logger.info("ExaClient initialized")

    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session for connection reuse.

        Returns:
            Active aiohttp ClientSession
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            logger.debug("Created new aiohttp session for Exa")
        return self.session

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
            query: Search query string
            num_results: Number of results to return (1-10)
            time_range: Time range filter (past_day, past_week, past_month, past_year)
            use_autoprompt: Use Exa's autoprompt feature for query optimization

        Returns:
            List of search result items with normalized schema

        Raises:
            ValueError: If API key not configured
            RuntimeError: If API call fails
        """
        if not self.api_key:
            raise ValueError("EXA_API_KEY environment variable not set")

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
            if start_date:
                body["start_published_date"] = start_date.isoformat()
                logger.debug(f"Exa time filter applied: {time_range} -> {start_date.isoformat()}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Exa search: query='{query}', num_results={num_results}, autoprompt={use_autoprompt}")

        # Make API request (reuse session for better performance)
        try:
            session = await self._get_session()
            async with session.post(
                self.base_url,
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Exa error: {response.status} - {error_text}")
                    raise RuntimeError(f"Exa error: {response.status} - {error_text}")

                data = await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"Exa connection error: {e}")
            raise RuntimeError(f"Exa connection error: {e}") from e
        except Exception as e:
            logger.error(f"Exa unexpected error: {e}")
            raise RuntimeError(f"Exa unexpected error: {e}") from e

        # Parse results
        results = []
        exa_results = data.get("results", [])

        for idx, item in enumerate(exa_results[:num_results], start=1):
            # Extract domain from URL
            url = item.get("url", "")
            domain = self._extract_domain(url)

            # Get snippet (Exa provides "text" field)
            snippet = item.get("text", "")
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
                "publish_date": self._parse_date(item.get("published_date")),
                "relevance_score": item.get("score")  # Exa provides relevance scores
            }
            results.append(result)

        logger.info(f"Exa returned {len(results)} results")
        return results

    def _calculate_start_date(self, time_range: str) -> Optional[datetime]:
        """
        Calculate start date from time range.

        Args:
            time_range: Time range string (past_day, past_week, past_month, past_year)

        Returns:
            Start datetime for filtering, or None if invalid
        """
        now = datetime.utcnow()

        time_map = {
            "past_day": timedelta(days=1),
            "past_week": timedelta(days=7),
            "past_month": timedelta(days=30),
            "past_year": timedelta(days=365)
        }

        if time_range in time_map:
            return now - time_map[time_range]

        logger.warning(f"Invalid time range: {time_range}")
        return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse date string to datetime.

        Args:
            date_str: ISO format date string

        Returns:
            Datetime object or None if parsing fails
        """
        if not date_str:
            return None
        try:
            # Handle both Z and +00:00 timezone formats
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None

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
        Test Exa connection and API key validity.

        Returns:
            True if connection successful, False otherwise
        """
        if not self.api_key:
            logger.error("Cannot test connection: API key not set")
            return False

        try:
            # Simple test query
            results = await self.search(query="test", num_results=1)
            logger.info("Exa connection test successful")
            return True
        except Exception as e:
            logger.error(f"Exa connection test failed: {e}")
            return False

    async def close(self):
        """Close aiohttp session and cleanup resources."""
        if self.session is not None and not self.session.closed:
            await self.session.close()
            logger.debug("Exa aiohttp session closed")
