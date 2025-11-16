"""
Scraper Service for ONYX Core

Provides URL content extraction using Mozilla Readability algorithm.
Integrates with BrowserManager for page navigation and handles HTML cleaning,
metadata extraction, and Markdown conversion.

Author: ONYX Core Team
Story: 7-3-url-scraping-content-extraction
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import html2text

from services.cache_manager import CacheManager
from services.browser_manager import BrowserManager

logger = logging.getLogger(__name__)

# Optional dependencies with graceful fallback
try:
    from readability import Document
    READABILITY_AVAILABLE = True
    logger.info("Mozilla Readability library available")
except ImportError:
    READABILITY_AVAILABLE = False
    logger.warning("Mozilla Readability library not available, using basic extraction")


class ScrapedContent:
    """Data model for scraped content with metadata."""

    def __init__(
        self,
        url: str,
        title: str = "Untitled",
        text_content: str = "",
        markdown_content: str = "",
        author: Optional[str] = None,
        publish_date: Optional[datetime] = None,
        excerpt: Optional[str] = None,
        word_count: int = 0,
        error: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        scraped_at: Optional[datetime] = None
    ):
        self.url = url
        self.title = title
        self.text_content = text_content
        self.markdown_content = markdown_content
        self.author = author
        self.publish_date = publish_date
        self.excerpt = excerpt or self._generate_excerpt(text_content)
        self.word_count = word_count or self._calculate_word_count(text_content)
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.scraped_at = scraped_at or datetime.now(timezone.utc)

    def _generate_excerpt(self, text: str, max_length: int = 200) -> str:
        """Generate excerpt from text content."""
        if not text:
            return ""

        # Remove extra whitespace and get first part
        clean_text = re.sub(r'\s+', ' ', text.strip())
        if len(clean_text) <= max_length:
            return clean_text

        excerpt = clean_text[:max_length].rstrip()
        if len(excerpt) < len(clean_text):
            excerpt += "..."
        return excerpt

    def _calculate_word_count(self, text: str) -> int:
        """Calculate word count from text."""
        if not text:
            return 0

        # Split on whitespace and count non-empty words
        words = [word for word in text.split() if word.strip()]
        return len(words)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "title": self.title,
            "text_content": self.text_content,
            "markdown_content": self.markdown_content,
            "author": self.author,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "excerpt": self.excerpt,
            "word_count": self.word_count,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapedContent':
        """Create instance from dictionary."""
        # Parse date fields
        publish_date = None
        if data.get("publish_date"):
            try:
                publish_date = datetime.fromisoformat(data["publish_date"])
            except (ValueError, TypeError):
                logger.warning(f"Could not parse publish_date: {data.get('publish_date')}")

        scraped_at = None
        if data.get("scraped_at"):
            try:
                scraped_at = datetime.fromisoformat(data["scraped_at"])
            except (ValueError, TypeError):
                logger.warning(f"Could not parse scraped_at: {data.get('scraped_at')}")

        return cls(
            url=data.get("url", ""),
            title=data.get("title", "Untitled"),
            text_content=data.get("text_content", ""),
            markdown_content=data.get("markdown_content", ""),
            author=data.get("author"),
            publish_date=publish_date,
            excerpt=data.get("excerpt"),
            word_count=data.get("word_count", 0),
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms"),
            scraped_at=scraped_at
        )


class RateLimiter:
    """Rate limiter for respectful scraping per domain."""

    def __init__(self, delay_seconds: int = 2):
        self.delay_seconds = delay_seconds
        self._last_request_time: Dict[str, float] = {}

    async def wait_if_needed(self, domain: str):
        """Wait if needed to respect rate limits."""
        if not domain or domain == "unknown":
            return

        current_time = asyncio.get_event_loop().time()
        last_time = self._last_request_time.get(domain, 0)

        time_since_last = current_time - last_time
        if time_since_last < self.delay_seconds:
            wait_time = self.delay_seconds - time_since_last
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for domain {domain}")
            await asyncio.sleep(wait_time)

        self._last_request_time[domain] = asyncio.get_event_loop().time()


class ScraperService:
    """Main scraper service for URL content extraction."""

    def __init__(self, cache_manager: CacheManager):
        """Initialize scraper service with dependencies."""
        self.cache_manager = cache_manager
        self.rate_limiter = RateLimiter(delay_seconds=2)

        # HTML to Markdown converter
        self.html2text_converter = html2text.HTML2Text()
        self.html2text_converter.body_width = 0  # Don't wrap lines

        logger.info("ScraperService initialized")

    def _generate_cache_key(self, url: str) -> str:
        """Generate cache key for URL."""
        return f"scraped:{hashlib.sha256(url.encode()).hexdigest()}"

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting."""
        try:
            parsed = urlparse(url)
            return parsed.netloc or "unknown"
        except Exception:
            return "unknown"

    def _validate_url(self, url: str) -> bool:
        """Validate URL format and scheme."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False
            if parsed.scheme not in ['http', 'https']:
                return False
            return True
        except Exception:
            return False

    def _clean_html_with_readability(self, html_content: str, url: str) -> tuple[str, Optional[str]]:
        """
        Clean HTML using Mozilla Readability algorithm.

        Returns:
            Tuple of (cleaned_html, error_message)
        """
        if not READABILITY_AVAILABLE:
            # Fallback to basic HTML cleaning
            return self._basic_html_cleaning(html_content), None

        try:
            doc = Document(html_content)
            cleaned_html = doc.summary()

            # Check if extracted content is sufficient
            if len(cleaned_html.strip()) < 100:
                return cleaned_html, "Extracted content too short (< 100 characters)"

            return cleaned_html, None

        except Exception as e:
            logger.error(f"Readability processing failed for {url}: {e}")
            return self._basic_html_cleaning(html_content), f"Readability processing failed: {str(e)}"

    def _basic_html_cleaning(self, html_content: str) -> str:
        """Basic HTML cleaning without Readability library."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()

            # Remove common advertisement containers
            for element in soup.find_all(['div', 'section'], class_=re.compile(r'ad|advertisement|banner|sidebar', re.I)):
                element.decompose()

            # Extract main content areas
            content_areas = []

            # Try common content selectors
            for selector in ['article', 'main', '[role="main"]', '.content', '.post-content', '.entry-content']:
                elements = soup.select(selector)
                if elements:
                    content_areas.extend(elements)

            # If no specific content areas found, use body
            if not content_areas:
                content_areas = [soup.find('body')] or [soup]

            # Combine text from content areas
            cleaned_content = '\n'.join(area.get_text(strip=True) for area in content_areas if area)

            return cleaned_content.strip()

        except Exception as e:
            logger.error(f"Basic HTML cleaning failed: {e}")
            return ""

    def _convert_to_markdown(self, html_content: str) -> str:
        """Convert HTML to Markdown format."""
        try:
            if not html_content.strip():
                return ""

            # Basic HTML wrapper if needed
            if not html_content.strip().startswith('<'):
                html_content = f"<div>{html_content}</div>"

            markdown = self.html2text_converter.handle(html_content)
            return markdown.strip()

        except Exception as e:
            logger.error(f"HTML to Markdown conversion failed: {e}")
            # Return plain text as fallback
            return html_content

    def _extract_metadata(self, html_content: str, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML content."""
        metadata = {
            "url": url,
            "title": None,
            "author": None,
            "publish_date": None,
            "excerpt": None
        }

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract title
            title = None

            # Try meta title first
            title_meta = soup.find('meta', property='og:title')
            if title_meta:
                title = title_meta.get('content', '').strip()

            # Try title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text().strip()

            # Try h1 as last resort
            if not title:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text().strip()

            metadata["title"] = title or "Untitled"

            # Extract author
            author = None

            # Try various author meta tags
            for selector in [
                'meta[name="author"]',
                'meta[property="article:author"]',
                'meta[name="article:author"]',
                'meta[name="creator"]'
            ]:
                author_meta = soup.select_one(selector)
                if author_meta:
                    author = author_meta.get('content', '').strip()
                    if author:
                        break

            metadata["author"] = author

            # Extract publish date
            publish_date = None

            # Try various date meta tags
            date_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="article:published_time"]',
                'meta[name="published_date"]',
                'meta[name="date"]',
                'meta[property="og:updated_time"]',
                'time[datetime]'
            ]

            for selector in date_selectors:
                date_meta = soup.select_one(selector)
                if date_meta:
                    date_str = date_meta.get('content') or date_meta.get('datetime')
                    if date_str:
                        publish_date = self._parse_date(date_str)
                        if publish_date:
                            break

            metadata["publish_date"] = publish_date

            # Extract excerpt from description
            description = None

            for selector in [
                'meta[name="description"]',
                'meta[property="og:description"]',
                'meta[name="excerpt"]'
            ]:
                desc_meta = soup.select_one(selector)
                if desc_meta:
                    description = desc_meta.get('content', '').strip()
                    if description:
                        break

            metadata["excerpt"] = description

        except Exception as e:
            logger.error(f"Metadata extraction failed for {url}: {e}")

        return metadata

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into datetime object."""
        if not date_str:
            return None

        try:
            from dateutil import parser
            return parser.parse(date_str)
        except ImportError:
            # Fallback without dateutil
            try:
                # Try ISO format first
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except ValueError:
                # Try common formats
                formats = [
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%B %d, %Y',
                    '%d %B %Y'
                ]

                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
        except Exception:
            pass

        return None

    async def scrape_url(self, url: str, force_refresh: bool = False) -> ScrapedContent:
        """
        Scrape URL and extract content.

        Args:
            url: URL to scrape
            force_refresh: Skip cache and force fresh scraping

        Returns:
            ScrapedContent with extracted data or error
        """
        start_time = asyncio.get_event_loop().time()

        # Validate URL
        if not self._validate_url(url):
            return ScrapedContent(
                url=url,
                title="Invalid URL",
                error=f"URL validation failed: Invalid URL format: {url}",
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

        # Check cache first (unless force refresh)
        if not force_refresh:
            cache_key = self._generate_cache_key(url)
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for URL: {url}")
                cached_content = ScrapedContent.from_dict(cached_data)
                cached_content.execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                return cached_content

        # Rate limiting
        domain = self._extract_domain(url)
        await self.rate_limiter.wait_if_needed(domain)

        try:
            logger.info(f"Scraping URL: {url}")

            # Get browser manager and navigate to page
            browser_manager = await BrowserManager.get_instance()
            page = await browser_manager.navigate(url, wait_until="domcontentloaded")

            # Get page HTML
            html_content = await page.content()

            # Extract metadata first (from raw HTML)
            metadata = self._extract_metadata(html_content, url)

            # Clean HTML using Readability
            cleaned_html, error = self._clean_html_with_readability(html_content, url)

            # Convert to Markdown
            markdown_content = self._convert_to_markdown(cleaned_html)

            # Create result
            result = ScrapedContent(
                url=url,
                title=metadata["title"],
                text_content=cleaned_html,
                markdown_content=markdown_content,
                author=metadata["author"],
                publish_date=metadata["publish_date"],
                excerpt=metadata["excerpt"],
                error=error,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

            # Cache successful results
            if not error or "too short" in error:
                cache_key = self._generate_cache_key(url)
                await self.cache_manager.set(cache_key, result.to_dict(), ttl=86400)  # 24h TTL

            # Clean up page
            await browser_manager.close_page(page)

            logger.info(f"Successfully scraped URL: {url} (error: {error})")
            return result

        except Exception as e:
            error_msg = f"Scraping failed: {str(e)}"
            logger.error(f"Error scraping URL {url}: {e}")

            return ScrapedContent(
                url=url,
                title="Scraping Failed",
                error=error_msg,
                execution_time_ms=int((asyncio.get_event_loop().time() - start_time) * 1000)
            )

    async def batch_scrape(self, urls: List[str], force_refresh: bool = False) -> List[ScrapedContent]:
        """
        Scrape multiple URLs sequentially with rate limiting.

        Args:
            urls: List of URLs to scrape
            force_refresh: Skip cache for all URLs

        Returns:
            List of ScrapedContent results
        """
        results = []

        logger.info(f"Starting batch scrape of {len(urls)} URLs")

        for url in urls:
            if not self._validate_url(url):
                results.append(ScrapedContent(
                    url=url,
                    title="Invalid URL",
                    error=f"URL validation failed: Invalid URL format: {url}"
                ))
                continue

            result = await self.scrape_url(url, force_refresh)
            results.append(result)

        successful = sum(1 for r in results if not r.error)
        logger.info(f"Batch scrape completed: {successful}/{len(urls)} successful")

        return results