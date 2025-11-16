"""
Integration Tests for Web Tools API

Test cases for web tools API endpoints including URL scraping,
batch scraping, health checks, and error handling.

Author: ONYX Core Team
Story: 7-3-url-scraping-content-extraction
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
import json
from datetime import datetime, timezone

from main import app
from api.web_tools import router
from services.scraper_service import ScrapedContent


class TestWebToolsAPI:
    """Integration tests for Web Tools API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_current_user(self):
        """Mock authenticated user."""
        return {
            "user_id": "test-user-123",
            "email": "test@example.com"
        }

    @pytest.fixture
    def mock_scraped_content(self):
        """Mock successful scraped content."""
        return ScrapedContent(
            url="https://example.com/article",
            title="Test Article",
            text_content="This is the article content with sufficient length for testing.",
            markdown_content="# Test Article\n\nThis is the article content with sufficient length for testing.",
            author="Test Author",
            publish_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            excerpt="This is the article excerpt.",
            word_count=15,
            execution_time_ms=2000
        )

    @pytest.fixture
    def mock_scraped_content_with_error(self):
        """Mock scraped content with error."""
        return ScrapedContent(
            url="https://example.com/article",
            title="Scraping Failed",
            text_content="",
            markdown_content="",
            error="Readability processing failed: Content too short",
            execution_time_ms=1000
        )

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_success(self, mock_scraper_service, mock_auth, client, mock_scraped_content, mock_current_user):
        """Test successful URL scraping."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.scrape_url.return_value = mock_scraped_content

        # Make request
        response = client.post("/tools/scrape_url", json={
            "url": "https://example.com/article",
            "force_refresh": False
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["url"] == "https://example.com/article"
        assert data["data"]["title"] == "Test Article"
        assert data["data"]["author"] == "Test Author"
        assert data["data"]["word_count"] == 15
        assert data["metadata"]["execution_time_ms"] == 2000
        assert data["metadata"]["cached"] is False
        assert data["metadata"]["user_id"] == "test-user-123"

        # Verify service was called correctly
        mock_scraper_service.scrape_url.assert_called_once_with(
            "https://example.com/article",
            force_refresh=False
        )

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_with_error(self, mock_scraper_service, mock_auth, client, mock_scraped_content_with_error, mock_current_user):
        """Test URL scraping with content extraction error."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.scrape_url.return_value = mock_scraped_content_with_error

        # Make request
        response = client.post("/tools/scrape_url", json={
            "url": "https://example.com/article",
            "force_refresh": False
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert data["data"]["title"] == "Scraping Failed"
        assert data["data"]["error"] == "Readability processing failed: Content too short"
        assert data["error"]["code"] == "CONTENT_EXTRACTION_ERROR"
        assert data["error"]["message"] == "Readability processing failed: Content too short"

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_cache_hit(self, mock_scraper_service, mock_auth, client, mock_scraped_content, mock_current_user):
        """Test URL scraping with cache hit."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.scrape_url.return_value = mock_scraped_content
        mock_scraper_service._generate_cache_key.return_value = "scraped:abcdef123456"

        # Mock cache manager to indicate cache hit
        mock_cache_manager = AsyncMock()
        mock_cache_manager.exists.return_value = True
        mock_scraper_service.cache_manager = mock_cache_manager

        # Make request
        response = client.post("/tools/scrape_url", json={
            "url": "https://example.com/article",
            "force_refresh": False
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["metadata"]["cached"] is True

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_invalid_url(self, mock_scraper_service, mock_auth, client, mock_current_user):
        """Test URL scraping with invalid URL."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.scrape_url.return_value = ScrapedContent(
            url="invalid-url",
            title="Invalid URL",
            text_content="",
            markdown_content="",
            error="URL validation failed: Invalid URL format: invalid-url",
            execution_time_ms=0
        )

        # Make request
        response = client.post("/tools/scrape_url", json={
            "url": "invalid-url",
            "force_refresh": False
        })

        # Should still return 200 but with error in data
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert "URL validation failed" in data["data"]["error"]

    def test_scrape_url_invalid_request_body(self, client):
        """Test scrape_url with invalid request body."""
        # Missing required field
        response = client.post("/tools/scrape_url", json={})

        assert response.status_code == 422  # Validation error

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_batch_scrape_success(self, mock_scraper_service, mock_auth, client, mock_scraped_content, mock_current_user):
        """Test successful batch URL scraping."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.batch_scrape.return_value = [mock_scraped_content, mock_scraped_content]

        # Make request
        response = client.post("/tools/batch_scrape", json={
            "urls": [
                "https://example.com/article1",
                "https://example.com/article2"
            ],
            "force_refresh": False
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["results"]) == 2
        assert data["summary"]["total_urls"] == 2
        assert data["summary"]["successful"] == 2
        assert data["summary"]["failed"] == 0
        assert data["summary"]["success_rate"] == 1.0
        assert data["summary"]["total_words"] == 30  # 15 * 2
        assert data["metadata"]["urls_processed"] == 2

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_batch_scrape_mixed_results(self, mock_scraper_service, mock_auth, client, mock_scraped_content, mock_scraped_content_with_error, mock_current_user):
        """Test batch URL scraping with mixed success/failure."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.batch_scrape.return_value = [mock_scraped_content, mock_scraped_content_with_error]

        # Make request
        response = client.post("/tools/batch_scrape", json={
            "urls": [
                "https://example.com/article1",
                "https://example.com/article2"
            ],
            "force_refresh": False
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True  # Overall success since at least one succeeded
        assert len(data["results"]) == 2
        assert data["summary"]["successful"] == 1
        assert data["summary"]["failed"] == 1
        assert data["summary"]["success_rate"] == 0.5

    @patch('api.web_tools.require_authenticated_user')
    def test_batch_scrape_too_many_urls(self, mock_auth, client, mock_current_user):
        """Test batch scraping with too many URLs."""
        # Setup mock
        mock_auth.return_value = mock_current_user

        # Make request with 11 URLs (exceeds limit of 10)
        response = client.post("/tools/batch_scrape", json={
            "urls": [f"https://example.com/article{i}" for i in range(11)],
            "force_refresh": False
        })

        # Should return 400 error
        assert response.status_code == 400
        error_data = response.json()

        assert error_data["detail"]["code"] == "TOO_MANY_URLS"
        assert "Maximum 10 URLs allowed" in error_data["detail"]["message"]

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.BrowserManager')
    @patch('api.web_tools.CacheManager')
    def test_scrape_health_check_healthy(self, mock_cache_manager_class, mock_browser_manager_class, mock_auth, client, mock_current_user):
        """Test health check with all services healthy."""
        # Setup mocks
        mock_auth.return_value = mock_current_user

        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.is_healthy.return_value = True
        mock_browser_manager.check_memory.return_value = 100
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Mock cache manager
        mock_cache_manager = AsyncMock()
        mock_cache_manager.set.return_value = True
        mock_cache_manager.get.return_value = {"test": True}
        mock_cache_manager.delete.return_value = True
        mock_cache_manager_class.return_value = mock_cache_manager

        # Make request
        response = client.get("/tools/scrape_health")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["healthy"] is True
        assert data["services"]["browser_manager"]["status"] == "healthy"
        assert data["services"]["browser_manager"]["memory_usage_mb"] == 100
        assert data["services"]["cache_manager"]["status"] == "healthy"
        assert "timestamp" in data

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.BrowserManager')
    @patch('api.web_tools.CacheManager')
    def test_scrape_health_check_unhealthy(self, mock_cache_manager_class, mock_browser_manager_class, mock_auth, client, mock_current_user):
        """Test health check with unhealthy services."""
        # Setup mocks
        mock_auth.return_value = mock_current_user

        # Mock unhealthy browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.is_healthy.return_value = False
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Mock unhealthy cache manager
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.side_effect = Exception("Redis connection failed")
        mock_cache_manager_class.return_value = mock_cache_manager

        # Make request
        response = client.get("/tools/scrape_health")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["healthy"] is False
        assert data["services"]["browser_manager"]["status"] == "unhealthy"
        assert data["services"]["cache_manager"]["status"] == "error"

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_service_unavailable(self, mock_scraper_service, mock_auth, client, mock_current_user):
        """Test scraping when scraper service is not initialized."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.scrape_url.side_effect = Exception("Service not initialized")

        # Make request
        response = client.post("/tools/scrape_url", json={
            "url": "https://example.com/article",
            "force_refresh": False
        })

        # Should return 500 error
        assert response.status_code == 500
        error_data = response.json()

        assert error_data["detail"]["code"] == "INTERNAL_SERVER_ERROR"
        assert "unexpected error occurred" in error_data["detail"]["message"]

    def test_scrape_url_unauthorized(self, client):
        """Test scrape_url without authentication."""
        # Mock authentication to raise exception
        with patch('api.web_tools.require_authenticated_user') as mock_auth:
            mock_auth.side_effect = Exception("Authentication failed")

            response = client.post("/tools/scrape_url", json={
                "url": "https://example.com/article",
                "force_refresh": False
            })

            # Should raise authentication exception
            assert response.status_code == 500

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_performance_timing(self, mock_scraper_service, mock_auth, client, mock_current_user):
        """Test that execution time is properly recorded."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.scrape_url.return_value = ScrapedContent(
            url="https://example.com/article",
            title="Test Article",
            text_content="Test content",
            markdown_content="# Test Article\n\nTest content",
            execution_time_ms=3500
        )

        # Make request
        response = client.post("/tools/scrape_url", json={
            "url": "https://example.com/article",
            "force_refresh": False
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Should include execution time in metadata
        assert "execution_time_ms" in data["metadata"]
        assert isinstance(data["metadata"]["execution_time_ms"], int)

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_request_validation(self, mock_scraper_service, mock_auth, client, mock_current_user):
        """Test request validation for various URL formats."""
        # Setup mocks
        mock_auth.return_value = mock_current_user

        # Test invalid URL formats
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Invalid scheme
            "javascript:alert('xss')",  # Dangerous scheme
        ]

        for invalid_url in invalid_urls:
            response = client.post("/tools/scrape_url", json={
                "url": invalid_url,
                "force_refresh": False
            })

            # Should handle invalid URLs gracefully (either 400 validation or 200 with error)
            assert response.status_code in [200, 400]

    @patch('api.web_tools.require_authenticated_user')
    @patch('api.web_tools.scraper_service')
    def test_scrape_url_optional_parameters(self, mock_scraper_service, mock_auth, client, mock_scraped_content, mock_current_user):
        """Test scrape_url with optional parameters."""
        # Setup mocks
        mock_auth.return_value = mock_current_user
        mock_scraper_service.scrape_url.return_value = mock_scraped_content

        # Test with only required parameter
        response = client.post("/tools/scrape_url", json={
            "url": "https://example.com/article"
        })

        assert response.status_code == 200

        # Verify service was called with default force_refresh=False
        mock_scraper_service.scrape_url.assert_called_once_with(
            "https://example.com/article",
            force_refresh=False
        )

        # Test with force_refresh=True
        response = client.post("/tools/scrape_url", json={
            "url": "https://example.com/article",
            "force_refresh": True
        })

        assert response.status_code == 200

        # Verify service was called with force_refresh=True
        mock_scraper_service.scrape_url.assert_called_with(
            "https://example.com/article",
            force_refresh=True
        )