"""
Unit Tests for Scraper Service

Test cases for URL content extraction, metadata parsing, caching,
rate limiting, and error handling.

Author: ONYX Core Team
Story: 7-3-url-scraping-content-extraction
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from urllib.parse import urlparse

from services.scraper_service import ScraperService, ScrapedContent, RateLimiter
from services.cache_manager import CacheManager


class TestScrapedContent:
    """Test cases for ScrapedContent data model."""

    def test_scraped_content_creation(self):
        """Test creating a ScrapedContent instance."""
        content = ScrapedContent(
            url="https://example.com",
            title="Test Title",
            text_content="Test content",
            markdown_content="# Test Title\n\nTest content",
            author="Test Author",
            publish_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            word_count=100
        )

        assert content.url == "https://example.com"
        assert content.title == "Test Title"
        assert content.author == "Test Author"
        assert content.word_count == 100

    def test_scraped_content_serialization(self):
        """Test ScrapedContent to_dict serialization."""
        content = ScrapedContent(
            url="https://example.com",
            title="Test Title",
            text_content="Test content",
            markdown_content="# Test Title\n\nTest content",
            author="Test Author",
            publish_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            word_count=100
        )

        data = content.to_dict()

        assert data["url"] == "https://example.com"
        assert data["title"] == "Test Title"
        assert data["author"] == "Test Author"
        assert data["publish_date"] == "2024-01-15T10:00:00+00:00"
        assert data["word_count"] == 100

    def test_scraped_content_deserialization(self):
        """Test ScrapedContent from_dict deserialization."""
        data = {
            "url": "https://example.com",
            "title": "Test Title",
            "text_content": "Test content",
            "markdown_content": "# Test Title\n\nTest content",
            "author": "Test Author",
            "publish_date": "2024-01-15T10:00:00+00:00",
            "word_count": 100,
            "scraped_at": "2024-01-16T14:30:00+00:00"
        }

        content = ScrapedContent.from_dict(data)

        assert content.url == "https://example.com"
        assert content.title == "Test Title"
        assert content.author == "Test Author"
        assert isinstance(content.publish_date, datetime)
        assert content.word_count == 100


class TestRateLimiter:
    """Test cases for RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(delay_seconds=2)
        assert limiter.delay_seconds == 2
        assert limiter._last_request_time == {}

    @pytest.mark.asyncio
    async def test_rate_limiter_first_request(self):
        """Test first request should not wait."""
        limiter = RateLimiter(delay_seconds=1)

        start_time = asyncio.get_event_loop().time()
        await limiter.wait_if_needed("example.com")
        end_time = asyncio.get_event_loop().time()

        # Should be very fast (< 100ms)
        assert end_time - start_time < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_subsequent_requests(self):
        """Test subsequent requests should wait."""
        limiter = RateLimiter(delay_seconds=0.5)

        # First request
        await limiter.wait_if_needed("example.com")
        start_time = asyncio.get_event_loop().time()

        # Second request should wait
        await limiter.wait_if_needed("example.com")
        end_time = asyncio.get_event_loop().time()

        # Should wait at least delay_seconds
        assert end_time - start_time >= 0.5

    @pytest.mark.asyncio
    async def test_rate_limiter_different_domains(self):
        """Test different domains don't affect each other."""
        limiter = RateLimiter(delay_seconds=0.5)

        # First request to domain1
        await limiter.wait_if_needed("domain1.com")
        start_time = asyncio.get_event_loop().time()

        # Request to domain2 should not wait for domain1
        await limiter.wait_if_needed("domain2.com")
        end_time = asyncio.get_event_loop().time()

        # Should be very fast (< 100ms)
        assert end_time - start_time < 0.1


class TestScraperService:
    """Test cases for ScraperService."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock CacheManager fixture."""
        cache = AsyncMock(spec=CacheManager)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.exists = AsyncMock(return_value=False)
        return cache

    @pytest.fixture
    def scraper_service(self, mock_cache_manager):
        """ScraperService fixture with mocked cache."""
        return ScraperService(cache_manager=mock_cache_manager)

    def test_scraper_service_initialization(self, mock_cache_manager):
        """Test ScraperService initialization."""
        service = ScraperService(cache_manager=mock_cache_manager)
        assert service.cache_manager == mock_cache_manager
        assert isinstance(service.rate_limiter, RateLimiter)

    def test_generate_cache_key(self, scraper_service):
        """Test cache key generation."""
        url = "https://example.com/article"
        cache_key = scraper_service._generate_cache_key(url)

        # Should be consistent
        cache_key2 = scraper_service._generate_cache_key(url)
        assert cache_key == cache_key2

        # Should start with "scraped:"
        assert cache_key.startswith("scraped:")

        # Should be SHA256 hash (64 chars)
        assert len(cache_key) == 72  # "scraped:" + 64 char hash

    def test_extract_domain(self, scraper_service):
        """Test domain extraction from URLs."""
        assert scraper_service._extract_domain("https://example.com/path") == "example.com"
        assert scraper_service._extract_domain("https://sub.example.com/path") == "sub.example.com"
        assert scraper_service._extract_domain("http://example.org") == "example.org"
        assert scraper_service._extract_domain("invalid-url") == "unknown"

    def test_clean_html_with_readability_success(self, scraper_service):
        """Test successful HTML cleaning with Readability."""
        html_content = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <article>
                    <h1>Main Title</h1>
                    <p>This is the main content of the article.</p>
                    <p>More content here.</p>
                </article>
                <nav>Navigation</nav>
                <footer>Footer</footer>
            </body>
        </html>
        """

        cleaned_html, error = scraper_service._clean_html_with_readability(html_content, "https://example.com")

        assert error is None
        assert "Main Title" in cleaned_html
        assert "This is the main content" in cleaned_html
        assert len(cleaned_html.strip()) > 100

    def test_clean_html_with_readability_short_content(self, scraper_service):
        """Test Readability with very short content."""
        html_content = "<html><body><p>Short</p></body></html>"

        cleaned_html, error = scraper_service._clean_html_with_readability(html_content, "https://example.com")

        assert error == "Extracted content too short (< 100 characters)"

    def test_convert_to_markdown(self, scraper_service):
        """Test HTML to Markdown conversion."""
        html_content = """
        <h1>Title</h1>
        <p>Paragraph with <strong>bold</strong> text.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        """

        markdown = scraper_service._convert_to_markdown(html_content)

        assert "# Title" in markdown
        assert "**bold**" in markdown
        assert "* Item 1" in markdown
        assert "* Item 2" in markdown

    def test_extract_metadata(self, scraper_service):
        """Test metadata extraction from HTML."""
        html_content = """
        <html>
            <head>
                <title>Article Title</title>
                <meta name="author" content="John Doe">
                <meta property="article:published_time" content="2024-01-15T10:00:00Z">
                <meta name="description" content="Article description">
            </head>
            <body>
                <article>Content here</article>
            </body>
        </html>
        """

        metadata = scraper_service._extract_metadata(html_content, "https://example.com")

        assert metadata["title"] == "Article Title"
        assert metadata["author"] == "John Doe"
        assert isinstance(metadata["publish_date"], datetime)
        assert metadata["excerpt"] == "Article description"
        assert metadata["url"] == "https://example.com"

    def test_extract_metadata_opengraph(self, scraper_service):
        """Test metadata extraction with OpenGraph tags."""
        html_content = """
        <html>
            <head>
                <meta property="og:title" content="OG Title">
                <meta property="og:description" content="OG Description">
                <meta property="article:author" content="Jane Smith">
            </head>
            <body><p>Content</p></body>
        </html>
        """

        metadata = scraper_service._extract_metadata(html_content, "https://example.com")

        assert metadata["title"] == "OG Title"
        assert metadata["author"] == "Jane Smith"
        assert metadata["excerpt"] == "OG Description"

    def test_calculate_word_count(self, scraper_service):
        """Test word count calculation."""
        text = "This is a test sentence with multiple words."
        word_count = scraper_service._calculate_word_count(text)
        assert word_count == 8

        empty_text = ""
        word_count = scraper_service._calculate_word_count(empty_text)
        assert word_count == 0

        # Test with extra whitespace
        text_with_spaces = "  Word1   Word2    Word3  "
        word_count = scraper_service._calculate_word_count(text_with_spaces)
        assert word_count == 3

    @pytest.mark.asyncio
    async def test_scrape_url_invalid_url(self, scraper_service):
        """Test scraping with invalid URL."""
        result = await scraper_service.scrape_url("invalid-url")

        assert result.error is not None
        assert "URL validation failed" in result.error
        assert result.url == "invalid-url"
        assert result.title == "Invalid URL"

    @pytest.mark.asyncio
    async def test_scrape_url_invalid_scheme(self, scraper_service):
        """Test scraping with invalid URL scheme."""
        result = await scraper_service.scrape_url("ftp://example.com")

        assert result.error is not None
        assert "Invalid URL scheme" in result.error

    @pytest.mark.asyncio
    async def test_scrape_url_cache_hit(self, scraper_service, mock_cache_manager):
        """Test scraping with cache hit."""
        mock_cache_manager.get.return_value = {
            "url": "https://example.com",
            "title": "Cached Title",
            "text_content": "Cached content",
            "markdown_content": "Cached markdown",
            "word_count": 50,
            "scraped_at": "2024-01-15T10:00:00+00:00"
        }

        result = await scraper_service.scrape_url("https://example.com")

        # Should use cache
        mock_cache_manager.get.assert_called_once()
        assert result.title == "Cached Title"
        assert result.text_content == "Cached content"
        assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_scrape_url_force_refresh(self, scraper_service, mock_cache_manager):
        """Test scraping with force refresh (cache bypass)."""
        result = await scraper_service.scrape_url("https://example.com", force_refresh=True)

        # Should not check cache
        mock_cache_manager.get.assert_not_called()

        # Should have error due to mock browser not being available
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_batch_scrape_empty_list(self, scraper_service):
        """Test batch scraping with empty URL list."""
        results = await scraper_service.batch_scrape([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_scrape_success(self, scraper_service, mock_cache_manager):
        """Test successful batch scraping."""
        # Mock cache hits
        mock_cache_manager.get.return_value = {
            "url": "https://example.com",
            "title": "Test Title",
            "text_content": "Test content",
            "markdown_content": "# Test Title\n\nTest content",
            "word_count": 10,
            "scraped_at": "2024-01-15T10:00:00+00:00"
        }

        urls = ["https://example.com", "https://example.org"]
        results = await scraper_service.batch_scrape(urls)

        assert len(results) == 2
        for result in results:
            assert result.title == "Test Title"
            assert result.text_content == "Test content"

        # Should check cache for each URL
        assert mock_cache_manager.get.call_count == 2

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_scrape_url_success(self, mock_browser_manager_class, scraper_service):
        """Test successful URL scraping."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Mock page
        mock_page = AsyncMock()
        mock_page.content.return_value = """
        <html>
            <head>
                <title>Test Article</title>
                <meta name="author" content="Test Author">
                <meta property="article:published_time" content="2024-01-15T10:00:00Z">
            </head>
            <body>
                <article>
                    <h1>Test Article</h1>
                    <p>This is a test article with sufficient content to pass the readability algorithm.</p>
                    <p>Here is some more content to make sure we have enough characters for the extraction to work properly.</p>
                    <p>Additional content to ensure the article is long enough and contains meaningful text that can be extracted and processed by the content extraction algorithm.</p>
                </article>
            </body>
        </html>
        """
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        result = await scraper_service.scrape_url("https://example.com/article")

        # Should be successful
        assert result.error is None
        assert result.title == "Test Article"
        assert result.author == "Test Author"
        assert isinstance(result.publish_date, datetime)
        assert "Test Article" in result.text_content
        assert "# Test Article" in result.markdown_content
        assert result.word_count > 0
        assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_scrape_url_browser_error(self, mock_browser_manager_class, scraper_service):
        """Test URL scraping with browser error."""
        # Mock browser manager that raises exception
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager
        mock_browser_manager.navigate.side_effect = Exception("Browser navigation failed")

        result = await scraper_service.scrape_url("https://example.com/article")

        # Should have error
        assert result.error is not None
        assert "Browser navigation failed" in result.error
        assert result.title == "Scraping Failed"
        assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_scrape_url_readability_error(self, mock_browser_manager_class, scraper_service):
        """Test URL scraping with Readability error."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Mock page with problematic HTML
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html><body><p>Too short</p></body></html>"
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        result = await scraper_service.scrape_url("https://example.com/article")

        # Should have readability warning but still return content
        assert result.error is not None
        assert "too short" in result.error
        assert result.title == "Untitled"  # From basic extraction
        assert result.execution_time_ms is not None