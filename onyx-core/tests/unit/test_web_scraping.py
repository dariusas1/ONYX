"""
Unit tests for Web Scraping API and Content Extraction

Tests the scraping functionality without requiring actual browser instances.
Uses mocking to isolate individual components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime

# Import the modules to test
from api.web_scraping import router, ScrapeUrlRequest, ContentExtractor
from main import app


class TestContentExtractor:
    """Test suite for ContentExtractor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ContentExtractor()

    def test_clean_markdown(self):
        """Test markdown cleaning functionality."""
        # Test excessive whitespace removal
        dirty_markdown = """
        This is a test



        With many empty lines

        And trailing spaces
        """
        expected = "This is a test\n\nWith many empty lines\n\nAnd trailing spaces"
        result = self.extractor._clean_markdown(dirty_markdown)
        assert result == expected

    def test_extract_metadata_basic(self):
        """Test basic metadata extraction."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="author" content="John Doe">
            <meta name="description" content="Test description">
            <meta property="og:site_name" content="Test Site">
        </head>
        <body>
            <h1>Test Content</h1>
        </body>
        </html>
        """

        metadata = self.extractor._extract_metadata(html, "https://example.com", Mock(title=lambda: "Test Page"))

        assert metadata["title"] == "Test Page"
        assert metadata["author"] == "John Doe"
        assert metadata["description"] == "Test description"
        assert metadata["site_name"] == "Test Site"
        assert metadata["url"] == "https://example.com"
        assert "extracted_at" in metadata

    def test_extract_metadata_with_dates(self):
        """Test metadata extraction with publication dates."""
        html = """
        <html>
        <head>
            <meta property="article:published_time" content="2023-01-01T00:00:00Z">
        </head>
        </html>
        """

        metadata = self.extractor._extract_metadata(html, "https://example.com", Mock(title=lambda: "Test"))

        assert metadata["publish_date"] == "2023-01-01T00:00:00Z"

    def test_fallback_extraction(self):
        """Test fallback extraction when readability fails."""
        html = """
        <html>
        <head><title>Fallback Test</title></head>
        <body>
            <nav>Navigation</nav>
            <script>console.log('test');</script>
            <main>Main content here</main>
            <footer>Footer</footer>
        </body>
        </html>
        """

        result = self.extractor._fallback_extraction(html, "https://example.com")

        assert "Main content here" in result["text_content"]
        assert "Navigation" not in result["text_content"]  # Should be removed
        assert "console.log" not in result["text_content"]  # Should be removed
        assert result["metadata"]["title"] == "Fallback Test"
        assert result["metadata"]["extraction_method"] == "fallback"

    @patch('api.web_scraping.Document')
    @patch('api.web_scraping.BeautifulSoup')
    def test_extract_content_success(self, mock_soup, mock_document):
        """Test successful content extraction."""
        # Mock readability document
        mock_doc = Mock()
        mock_doc.summary.return_value = "<main>Clean content</main>"
        mock_doc.title.return_value = "Test Article"
        mock_document.return_value = mock_doc

        # Mock BeautifulSoup
        mock_soup_instance = Mock()
        mock_soup.return_value = mock_soup_instance

        # Mock html2text
        self.extractor.html2text.handle = Mock(return_value="# Test Article\n\nClean content")

        html_content = "<html><body><h1>Test Article</h1><p>Clean content</p></body></html>"

        result = self.extractor.extract_content(html_content, "https://example.com")

        assert result["text_content"] == "# Test Article\n\nClean content"
        assert result["metadata"]["title"] == "Test Article"
        assert result["metadata"]["url"] == "https://example.com"
        assert "extracted_at" in result["metadata"]
        assert result["raw_html_length"] == len(html_content)
        assert result["content_length"] > 0


class TestWebScrapingAPI:
    """Test suite for Web Scraping API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch('api.web_scraping.BrowserManager.get_instance')
    @patch('api.web_scraping.content_extractor.extract_content')
    def test_scrape_url_success(self, mock_extract, mock_browser_manager):
        """Test successful URL scraping."""
        # Mock browser manager
        mock_manager = AsyncMock()
        mock_browser_manager.return_value = mock_manager

        # Mock page
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html><body>Test content</body></html>"
        mock_page.evaluate.return_value = {
            "has_content": True,
            "content_length": 1000,
            "has_dynamic_elements": False
        }

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock content extraction
        mock_extract.return_value = {
            "text_content": "# Test Article\n\nClean content",
            "metadata": {
                "title": "Test Article",
                "author": "Test Author",
                "url": "https://example.com"
            },
            "raw_html_length": 5000,
            "content_length": 200
        }

        request_data = {
            "url": "https://example.com",
            "wait_for_javascript": True,
            "timeout_seconds": 10,
            "extract_metadata": True
        }

        response = self.client.post("/tools/scrape_url", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["text_content"] == "# Test Article\n\nClean content"
        assert data["data"]["metadata"]["title"] == "Test Article"
        assert "performance" in data["data"]
        assert "execution_time_ms" in data["data"]["performance"]

        # Verify method calls
        mock_browser_manager.assert_called_once()
        mock_manager.navigate.assert_called_once_with(
            "https://example.com",
            wait_until="load"
        )
        mock_manager.close_page.assert_called_once()

    def test_scrape_url_invalid_url(self):
        """Test scraping with invalid URL."""
        request_data = {
            "url": "invalid-url",
            "wait_for_javascript": True,
            "timeout_seconds": 10
        }

        response = self.client.post("/tools/scrape_url", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_scrape_url_blocked_url(self):
        """Test scraping with blocked localhost URL."""
        request_data = {
            "url": "http://localhost:3000",
            "wait_for_javascript": True,
            "timeout_seconds": 10
        }

        response = self.client.post("/tools/scrape_url", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_URL"

    @patch('api.web_scraping.BrowserManager.get_instance')
    def test_scrape_url_navigation_failure(self, mock_browser_manager):
        """Test scraping when navigation fails."""
        # Mock browser manager that raises exception
        mock_manager = AsyncMock()
        mock_manager.navigate.side_effect = Exception("Navigation failed")
        mock_browser_manager.return_value = mock_manager

        request_data = {
            "url": "https://example.com",
            "wait_for_javascript": True,
            "timeout_seconds": 10
        }

        response = self.client.post("/tools/scrape_url", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"]["code"] == "BROWSER_ERROR"

    @patch('api.web_scraping.BrowserManager.get_instance')
    @patch('api.web_scraping.content_extractor.extract_content')
    def test_scrape_url_content_extraction_failure(self, mock_extract, mock_browser_manager):
        """Test scraping when content extraction fails."""
        # Mock browser manager
        mock_manager = AsyncMock()
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html></html>"
        mock_page.evaluate.return_value = {"has_content": True, "content_length": 0}

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()
        mock_browser_manager.return_value = mock_manager

        # Mock content extraction failure
        mock_extract.side_effect = Exception("Content extraction failed")

        request_data = {
            "url": "https://example.com",
            "wait_for_javascript": True,
            "timeout_seconds": 10
        }

        response = self.client.post("/tools/scrape_url", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONTENT_EXTRACTION_FAILED"

    @patch('api.web_scraping.BrowserManager.get_instance')
    def test_scrape_url_timeout_error(self, mock_browser_manager):
        """Test scraping with timeout error."""
        # Mock browser manager that raises timeout
        mock_manager = AsyncMock()
        mock_manager.navigate.side_effect = Exception("timeout")
        mock_browser_manager.return_value = mock_manager

        request_data = {
            "url": "https://example.com",
            "wait_for_javascript": True,
            "timeout_seconds": 10
        }

        response = self.client.post("/tools/scrape_url", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "NAVIGATION_FAILED"
        assert "timed out" in data["error"]["message"].lower()

    @patch('api.web_scraping.BrowserManager.get_instance')
    def test_scrape_url_health_check(self, mock_browser_manager):
        """Test health check endpoint."""
        # Mock browser manager
        mock_manager = AsyncMock()
        mock_manager.is_healthy.return_value = True
        mock_browser_manager.return_value = mock_manager

        response = self.client.get("/tools/scrape_url/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "scrape_url"
        assert data["browser_connected"] is True

    @patch('api.web_scraping.BrowserManager.get_instance')
    def test_scrape_url_health_check_unhealthy(self, mock_browser_manager):
        """Test health check endpoint when unhealthy."""
        # Mock browser manager
        mock_manager = AsyncMock()
        mock_manager.is_healthy.side_effect = Exception("Browser not available")
        mock_browser_manager.return_value = mock_manager

        response = self.client.get("/tools/scrape_url/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "error" in data


class TestScrapeUrlRequest:
    """Test suite for ScrapeUrlRequest model validation."""

    def test_valid_request(self):
        """Test valid request model."""
        request = ScrapeUrlRequest(
            url="https://example.com",
            wait_for_javascript=True,
            timeout_seconds=10
        )
        assert request.url == "https://example.com"
        assert request.wait_for_javascript is True
        assert request.timeout_seconds == 10

    def test_default_values(self):
        """Test request model with default values."""
        request = ScrapeUrlRequest(url="https://example.com")
        assert request.wait_for_javascript is True
        assert request.timeout_seconds == 10
        assert request.extract_metadata is True

    def test_invalid_url(self):
        """Test request model with invalid URL."""
        with pytest.raises(Exception):
            ScrapeUrlRequest(url="not-a-url")


if __name__ == "__main__":
    pytest.main([__file__])