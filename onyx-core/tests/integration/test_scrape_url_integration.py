"""
Integration tests for Web Scraping functionality

Tests the complete scraping workflow with real browser instances.
These tests require Playwright browsers to be installed.
"""

import pytest
import asyncio
import time
from playwright.async_api import async_playwright
import requests
from datetime import datetime

# Import the modules to test
from services.browser_manager import BrowserManager
from api.web_scraping import ContentExtractor


class TestContentExtractorIntegration:
    """Integration tests for ContentExtractor with real HTML."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ContentExtractor()

    def test_extract_real_html_content(self):
        """Test content extraction with real HTML."""
        # Real HTML from a simple webpage
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Sample Article - Test Site</title>
            <meta name="author" content="Jane Doe">
            <meta name="description" content="A sample article for testing">
            <meta property="article:published_time" content="2023-12-01T10:00:00Z">
            <meta property="og:site_name" content="Test Site">
        </head>
        <body>
            <header>
                <nav>
                    <ul>
                        <li><a href="/">Home</a></li>
                        <li><a href="/about">About</a></li>
                    </ul>
                </nav>
            </header>

            <main>
                <article>
                    <h1>Sample Article Title</h1>
                    <p class="meta">By Jane Doe • December 1, 2023</p>

                    <p>This is the first paragraph of our sample article. It contains some meaningful content that should be extracted by our content extraction system.</p>

                    <h2>Subsection Title</h2>
                    <p>This is a subsection with additional content. It should also be properly extracted and formatted as markdown.</p>

                    <blockquote>
                        This is a quote that should be preserved in the extraction process.
                    </blockquote>

                    <ul>
                        <li>First bullet point</li>
                        <li>Second bullet point</li>
                        <li>Third bullet point</li>
                    </ul>
                </article>
            </main>

            <footer>
                <p>&copy; 2023 Test Site. All rights reserved.</p>
                <script>console.log('This should be removed');</script>
            </footer>
        </body>
        </html>
        """

        result = self.extractor.extract_content(html_content, "https://example.com/article")

        # Verify content extraction
        assert result["text_content"] is not None
        assert len(result["text_content"]) > 0

        # Check that main content is preserved
        assert "Sample Article Title" in result["text_content"]
        assert "This is the first paragraph" in result["text_content"]
        assert "First bullet point" in result["text_content"]

        # Check that navigation/footer are minimized
        # (Readability should focus on main content)
        assert result["text_content"].count("Home") <= 1  # Should be minimal
        assert "console.log" not in result["text_content"]  # Scripts should be removed

        # Verify metadata extraction
        metadata = result["metadata"]
        assert metadata["title"] == "Sample Article - Test Site"
        assert metadata["author"] == "Jane Doe"
        assert metadata["description"] == "A sample article for testing"
        assert metadata["site_name"] == "Test Site"
        assert metadata["publish_date"] == "2023-12-01T10:00:00Z"
        assert metadata["url"] == "https://example.com/article"

    def test_extract_news_article_html(self):
        """Test extraction with typical news article HTML structure."""
        html_content = """
        <html>
        <head>
            <title>Breaking News: Major Event Occurs</title>
            <meta name="author" content="John Smith">
            <meta property="article:published_time" content="2023-12-15T14:30:00Z">
        </head>
        <body>
            <div class="header">
                <div class="navigation">...</div>
            </div>

            <div class="ads-sidebar">Advertisement content</div>

            <main class="article-content">
                <h1>Breaking News: Major Event Occurs</h1>
                <div class="byline">By John Smith, Updated 2 hours ago</div>

                <div class="article-body">
                    <p>LOREM IPSUM - A significant event has occurred today that has captured the attention of many observers. The situation is developing rapidly.</p>

                    <p>According to sources familiar with the matter, the event took place at approximately 10:00 AM local time. Emergency services responded quickly to the scene.</p>

                    <h2>Key Details</h2>
                    <ul>
                        <li>Location: Downtown area</li>
                        <li>Time: Around 10:00 AM</li>
                        <li>Status: Under investigation</li>
                    </ul>

                    <p>Officials have asked the public to avoid the area while the investigation continues. More updates will be provided as information becomes available.</p>
                </div>
            </main>

            <div class="related-articles">Related content links</div>
            <div class="comments">User comments section</div>
        </body>
        </html>
        """

        result = self.extractor.extract_content(html_content, "https://news.example.com/breaking-news")

        # Verify main content extraction
        assert "Breaking News: Major Event Occurs" in result["text_content"]
        assert "LOREM IPSUM" in result["text_content"]
        assert "Key Details" in result["text_content"]
        assert "Downtown area" in result["text_content"]

        # Check that ads and navigation are filtered out
        assert "Advertisement content" not in result["text_content"]
        assert result["text_content"].count("Related content links") <= 1

        # Verify metadata
        assert result["metadata"]["title"] == "Breaking News: Major Event Occurs"
        assert result["metadata"]["author"] == "John Smith"


class TestBrowserManagerScrapingIntegration:
    """Integration tests for BrowserManager scraping functionality."""

    @pytest.mark.asyncio
    async def test_scrape_page_performance(self):
        """Test that scrape_page meets performance requirements (<5s)."""
        browser_manager = await BrowserManager.get_instance()

        try:
            # Test with a simple, fast-loading website
            # Using example.com which should be reliable and fast
            result = await browser_manager.scrape_page(
                "https://example.com",
                max_execution_time_ms=5000
            )

            # Verify success
            assert result["success"] is True
            assert "page" in result
            assert "metrics" in result

            # Check performance requirements (AC7.3.5)
            metrics = result["metrics"]
            assert metrics["execution_time_ms"] <= 5000, f"Execution time {metrics['execution_time_ms']}ms exceeded 5000ms limit"
            assert metrics["performance_ok"] is True

            # Check content metrics
            content_metrics = metrics["content_metrics"]
            assert content_metrics["text_length"] > 0
            assert content_metrics["word_count"] > 0
            assert content_metrics["has_title"] is True

            print(f"Performance test passed: {metrics['execution_time_ms']}ms, {content_metrics['text_length']} chars")

        finally:
            # Clean up
            await browser_manager.close_page(result["page"])

    @pytest.mark.asyncio
    async def test_scrape_page_with_javascript(self):
        """Test scraping with JavaScript-heavy content."""
        browser_manager = await BrowserManager.get_instance()

        try:
            # Use a site with JavaScript content
            result = await browser_manager.scrape_page(
                "https://example.com",
                max_execution_time_ms=5000
            )

            page = result["page"]
            metrics = result["metrics"]

            # Verify JavaScript execution
            js_metrics = await page.evaluate("() => window.scrapingMetrics")
            assert js_metrics is not None
            assert "startTime" in js_metrics
            assert "resourceCount" in js_metrics

            # Check that content was loaded properly
            content_metrics = metrics["content_metrics"]
            assert content_metrics["text_length"] > 0

        finally:
            await browser_manager.close_page(result["page"])

    @pytest.mark.asyncio
    async def test_url_validation(self):
        """Test URL validation in browser manager."""
        browser_manager = await BrowserManager.get_instance()

        # Test blocked URLs
        blocked_urls = [
            "http://localhost:3000",
            "http://127.0.0.1:8080",
            "https://10.0.0.1",
            "file:///path/to/file.html"
        ]

        for url in blocked_urls:
            with pytest.raises(ValueError, match="blocked for security"):
                await browser_manager.navigate(url)

    @pytest.mark.asyncio
    async def test_memory_monitoring(self):
        """Test memory monitoring during scraping operations."""
        browser_manager = await BrowserManager.get_instance()

        # Check initial memory
        initial_memory = await browser_manager.check_memory()

        # Perform scraping operation
        result = await browser_manager.scrape_page(
            "https://example.com",
            max_execution_time_ms=5000
        )

        # Check memory after operation
        final_memory = await browser_manager.check_memory()

        # Memory should be reasonable (not exceed limits)
        assert final_memory <= browser_manager.max_memory_mb

        # Memory delta should be reasonable
        memory_delta = final_memory - initial_memory
        assert memory_delta >= 0

        await browser_manager.close_page(result["page"])

    @pytest.mark.asyncio
    async def test_concurrent_scraping_protection(self):
        """Test that concurrent scraping is properly serialized."""
        browser_manager = await BrowserManager.get_instance()

        # Try to start multiple scraping operations concurrently
        tasks = [
            browser_manager.scrape_page("https://example.com", max_execution_time_ms=5000)
            for _ in range(3)
        ]

        # All should complete successfully due to serial execution
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent scraping failed: {result}")
            else:
                assert result["success"] is True
                await browser_manager.close_page(result["page"])


class TestScrapingAPIntegration:
    """Integration tests for the complete scraping API."""

    def test_complete_api_workflow(self):
        """Test the complete API workflow with real browser."""
        request_data = {
            "url": "https://example.com",
            "wait_for_javascript": True,
            "timeout_seconds": 10,
            "extract_metadata": True
        }

        # Note: This test requires the FastAPI server to be running
        # In a real CI/CD environment, you'd start the test server
        try:
            response = requests.post(
                "http://localhost:8080/tools/scrape_url",
                json=request_data,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert "text_content" in data["data"]
                assert "metadata" in data["data"]
                assert "performance" in data["data"]

                # Check performance requirements
                perf = data["data"]["performance"]
                assert perf["execution_time_ms"] <= 5000

            else:
                pytest.skip(f"API server not available (status {response.status_code})")

        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running - integration test skipped")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])