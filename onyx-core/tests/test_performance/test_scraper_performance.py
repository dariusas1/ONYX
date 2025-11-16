"""
Performance Tests for URL Scraping

Test cases to verify <5s execution time requirement and performance benchmarks.

Author: ONYX Core Team
Story: 7-3-url-scraping-content-extraction
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import statistics

from services.scraper_service import ScraperService, ScrapedContent
from services.cache_manager import CacheManager


class TestScraperPerformance:
    """Performance tests for ScraperService."""

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

    @pytest.fixture
    def mock_html_content(self):
        """Sample HTML content for testing."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Performance Test Article</title>
            <meta name="author" content="Performance Test Author">
            <meta property="article:published_time" content="2024-01-15T10:00:00Z">
            <meta name="description" content="This is a performance test article with sufficient content for testing the scraping service performance under various conditions and ensuring it meets the execution time requirements.">
        </head>
        <body>
            <header>
                <nav>
                    <ul>
                        <li><a href="/">Home</a></li>
                        <li><a href="/about">About</a></li>
                        <li><a href="/contact">Contact</a></li>
                    </ul>
                </nav>
            </header>
            <main>
                <article>
                    <h1>Performance Test Article</h1>
                    <h2>Introduction</h2>
                    <p>This is a comprehensive performance test article designed to evaluate the scraping service's performance characteristics. The article contains multiple paragraphs, headings, and various HTML elements that would typically be found in a real-world web page. This ensures that our performance tests accurately reflect the processing requirements for typical content extraction scenarios.</p>

                    <h2>Content Structure</h2>
                    <p>The article is structured with multiple sections and subsections to simulate real-world content. Each section contains substantial text content that needs to be processed by the Mozilla Readability algorithm. This includes removing navigation elements, advertisements, and other non-content elements while preserving the main article content in a clean, readable format.</p>

                    <h3>Technical Details</h3>
                    <p>The performance testing involves measuring the time taken for various operations including page navigation, HTML content extraction, Readability processing, Markdown conversion, and metadata extraction. These operations must complete within the specified time limits to ensure a good user experience and efficient resource utilization.</p>

                    <h2>Performance Requirements</h2>
                    <p>The scraping service must meet strict performance requirements including sub-5-second execution time for the complete scraping workflow. This includes all operations from URL validation through content extraction and formatting. The service should also maintain good performance under concurrent requests and handle various types of web content efficiently.</p>

                    <h3>Benchmarking Methodology</h3>
                    <p>Performance benchmarks are conducted using multiple sample URLs with varying content types and sizes. Execution times are measured for individual operations as well as the complete end-to-end workflow. Statistical analysis is performed to ensure performance consistency across multiple runs and different content types.</p>

                    <h2>Optimization Strategies</h2>
                    <p>Various optimization strategies are employed to ensure optimal performance including efficient HTML parsing, content caching, rate limiting, and memory management. The service is designed to handle large volumes of scraping requests while maintaining consistent performance and resource utilization patterns.</p>

                    <h3>Caching Implementation</h3>
                    <p>Intelligent caching mechanisms are implemented to minimize repeated processing of the same URLs. This includes both short-term memory caching and persistent Redis-based caching with appropriate TTL values. Cache hit rates are monitored to ensure optimal cache utilization and performance improvement.</p>

                    <h2>Error Handling Performance</h2>
                    <p>Error handling is designed to be efficient and fast, ensuring that failed requests don't significantly impact overall performance. The service quickly identifies and handles various error conditions including invalid URLs, network failures, and content extraction errors while maintaining responsive performance characteristics.</p>

                    <h2>Conclusion</h2>
                    <p>This comprehensive performance test article provides a realistic scenario for evaluating the scraping service's performance. The content includes various HTML elements, sufficient text length, and typical metadata structures that would be found in real-world web pages. The performance testing ensures the service meets the specified requirements and provides optimal user experience.</p>
                </article>
            </main>
            <footer>
                <p>&copy; 2024 Performance Test. All rights reserved.</p>
                <div id="analytics">
                    <!-- Analytics tracking code -->
                </div>
            </footer>
        </body>
        </html>
        """

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_single_scrape_performance_under_5s(self, mock_browser_manager_class, scraper_service, mock_html_content):
        """Test that single URL scraping completes in under 5 seconds."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Mock page with realistic content
        mock_page = AsyncMock()
        mock_page.content.return_value = mock_html_content
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        # Measure execution time
        start_time = time.time()
        result = await scraper_service.scrape_url("https://example.com/performance-test")
        execution_time = time.time() - start_time

        # Assertions
        assert result.error is None, f"Scraping failed with error: {result.error}"
        assert execution_time < 5.0, f"Execution time {execution_time:.2f}s exceeds 5s requirement"
        assert result.execution_time_ms is not None
        assert result.execution_time_ms < 5000, f"Reported time {result.execution_time_ms}ms exceeds 5000ms"

        # Verify content was properly extracted
        assert result.title == "Performance Test Article"
        assert result.author == "Performance Test Author"
        assert "Performance Test Article" in result.text_content
        assert "# Performance Test Article" in result.markdown_content
        assert result.word_count > 500  # Should have substantial content

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_multiple_scrapes_performance_distribution(self, mock_browser_manager_class, scraper_service, mock_html_content):
        """Test performance distribution across multiple scrapes."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Mock page
        mock_page = AsyncMock()
        mock_page.content.return_value = mock_html_content
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        # Perform multiple scrapes
        num_scrapes = 10
        execution_times = []

        for i in range(num_scrapes):
            start_time = time.time()
            result = await scraper_service.scrape_url(f"https://example.com/test{i}")
            execution_time = time.time() - start_time
            execution_times.append(execution_time)

            assert result.error is None, f"Scraping {i} failed with error: {result.error}"

        # Performance analysis
        avg_time = statistics.mean(execution_times)
        p95_time = statistics.quantiles(execution_times, n=20)[18]  # 95th percentile
        max_time = max(execution_times)
        min_time = min(execution_times)

        # Assertions
        assert avg_time < 5.0, f"Average time {avg_time:.2f}s exceeds 5s requirement"
        assert p95_time < 5.0, f"95th percentile time {p95_time:.2f}s exceeds 5s requirement"
        assert max_time < 10.0, f"Maximum time {max_time:.2f}s exceeds 10s hard limit"
        assert min_time < 3.0, f"Minimum time {min_time:.2f}s should be under 3s for good performance"

        print(f"Performance statistics for {num_scrapes} scrapes:")
        print(f"  Average: {avg_time:.2f}s")
        print(f"  95th percentile: {p95_time:.2f}s")
        print(f"  Maximum: {max_time:.2f}s")
        print(f"  Minimum: {min_time:.2f}s")

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_content_extraction_performance_components(self, mock_browser_manager_class, scraper_service, mock_html_content):
        """Test individual component performance within the scraping workflow."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Mock page
        mock_page = AsyncMock()
        mock_page.content.return_value = mock_html_content
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        # Test metadata extraction performance
        start_time = time.time()
        metadata = scraper_service._extract_metadata(mock_html_content, "https://example.com")
        metadata_time = time.time() - start_time

        assert metadata_time < 0.1, f"Metadata extraction {metadata_time:.3f}s should be under 100ms"

        # Test HTML cleaning performance
        start_time = time.time()
        cleaned_html, error = scraper_service._clean_html_with_readability(mock_html_content, "https://example.com")
        cleaning_time = time.time() - start_time

        assert cleaning_time < 0.5, f"HTML cleaning {cleaning_time:.3f}s should be under 500ms"
        assert error is None

        # Test Markdown conversion performance
        start_time = time.time()
        markdown = scraper_service._convert_to_markdown(cleaned_html)
        conversion_time = time.time() - start_time

        assert conversion_time < 0.2, f"Markdown conversion {conversion_time:.3f}s should be under 200ms"

        print(f"Component performance breakdown:")
        print(f"  Metadata extraction: {metadata_time:.3f}s")
        print(f"  HTML cleaning: {cleaning_time:.3f}s")
        print(f"  Markdown conversion: {conversion_time:.3f}s")

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_cache_performance_improvement(self, mock_browser_manager_class, scraper_service, mock_cache_manager, mock_html_content):
        """Test that caching provides significant performance improvement."""
        # Mock browser manager for first scrape
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        mock_page = AsyncMock()
        mock_page.content.return_value = mock_html_content
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        url = "https://example.com/cache-test"

        # First scrape (should use browser)
        start_time = time.time()
        result1 = await scraper_service.scrape_url(url)
        first_scrape_time = time.time() - start_time

        assert result1.error is None

        # Mock cache hit for second scrape
        cached_data = result1.to_dict()
        mock_cache_manager.get.return_value = cached_data

        # Second scrape (should use cache)
        start_time = time.time()
        result2 = await scraper_service.scrape_url(url)
        second_scrape_time = time.time() - start_time

        # Cache should be significantly faster
        assert second_scrape_time < first_scrape_time / 2, f"Cache should be at least 2x faster"

        # Verify cached results are identical
        assert result1.url == result2.url
        assert result1.title == result2.title
        assert result1.text_content == result2.text_content

        print(f"Cache performance improvement:")
        print(f"  First scrape: {first_scrape_time:.3f}s")
        print(f"  Cached scrape: {second_scrape_time:.3f}s")
        print(f"  Speedup: {first_scrape_time / second_scrape_time:.1f}x")

    @pytest.mark.asyncio
    async def test_rate_limiter_performance_impact(self, scraper_service):
        """Test that rate limiting doesn't significantly impact performance when not needed."""
        # Test rate limiter with different domains (should not wait)
        domains = ["domain1.com", "domain2.com", "domain3.com", "domain4.com", "domain5.com"]

        start_time = time.time()

        for domain in domains:
            await scraper_service.rate_limiter.wait_if_needed(domain)

        total_time = time.time() - start_time

        # Should be very fast since all domains are different
        assert total_time < 0.1, f"Rate limiting for different domains took {total_time:.3f}s, should be < 100ms"

    @pytest.mark.asyncio
    async def test_rate_limiter_enforcement(self, scraper_service):
        """Test that rate limiting properly enforces delays."""
        domain = "test.com"

        # First request
        start_time = time.time()
        await scraper_service.rate_limiter.wait_if_needed(domain)
        first_request_time = time.time() - start_time

        # Second request to same domain should wait
        start_time = time.time()
        await scraper_service.rate_limiter.wait_if_needed(domain)
        second_request_time = time.time() - start_time

        # First request should be fast, second should wait
        assert first_request_time < 0.1, f"First request took {first_request_time:.3f}s, should be < 100ms"
        assert second_request_time >= 1.9, f"Second request took {second_request_time:.3f}s, should wait ~2s"

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_batch_scraping_performance_scaling(self, mock_browser_manager_class, scraper_service, mock_html_content):
        """Test batch scraping performance with increasing URL counts."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        mock_page = AsyncMock()
        mock_page.content.return_value = mock_html_content
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        # Test with different batch sizes
        batch_sizes = [1, 3, 5, 10]
        performance_data = {}

        for batch_size in batch_sizes:
            urls = [f"https://example.com/batch-test-{i}" for i in range(batch_size)]

            start_time = time.time()
            results = await scraper_service.batch_scrape(urls)
            total_time = time.time() - start_time
            avg_time = total_time / batch_size

            performance_data[batch_size] = {
                "total_time": total_time,
                "avg_time": avg_time,
                "success_rate": sum(1 for r in results if not r.error) / len(results)
            }

            # All should succeed
            assert performance_data[batch_size]["success_rate"] == 1.0
            assert avg_time < 5.0, f"Average time {avg_time:.2f}s for batch size {batch_size} exceeds 5s"

        print("Batch scraping performance:")
        for batch_size, data in performance_data.items():
            print(f"  Batch size {batch_size}: total {data['total_time']:.2f}s, avg {data['avg_time']:.2f}s")

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_memory_usage_during_scraping(self, mock_browser_manager_class, scraper_service, mock_html_content):
        """Test memory usage during scraping operations."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        mock_page = AsyncMock()
        mock_page.content.return_value = mock_html_content
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        # Monitor memory usage during scraping
        initial_memory = await mock_browser_manager.check_memory()

        # Perform multiple scrapes
        for i in range(5):
            result = await scraper_service.scrape_url(f"https://example.com/memory-test-{i}")
            assert result.error is None

        final_memory = await mock_browser_manager.check_memory()

        # Memory growth should be minimal (assuming browser manager manages memory properly)
        # This test mainly verifies that memory monitoring doesn't break scraping
        assert isinstance(initial_memory, int)
        assert isinstance(final_memory, int)

    @pytest.mark.asyncio
    @patch('services.scraper_service.BrowserManager')
    async def test_large_content_handling_performance(self, mock_browser_manager_class, scraper_service):
        """Test performance with large HTML content."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_browser_manager

        # Generate large HTML content
        large_content = "<html><head><title>Large Article</title></head><body><article>"
        for i in range(1000):  # 1000 paragraphs
            large_content += f"<p>This is paragraph {i} with substantial content that simulates a large article. " * 10 + "</p>"
        large_content += "</article></body></html>"

        mock_page = AsyncMock()
        mock_page.content.return_value = large_content
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page = AsyncMock()

        # Test performance with large content
        start_time = time.time()
        result = await scraper_service.scrape_url("https://example.com/large-content")
        execution_time = time.time() - start_time

        # Should still meet performance requirements even with large content
        assert result.error is None
        assert execution_time < 5.0, f"Large content scraping took {execution_time:.2f}s, should be < 5s"
        assert result.word_count > 10000, "Large content should have substantial word count"

        print(f"Large content performance:")
        print(f"  Content size: {len(large_content)} characters")
        print(f"  Word count: {result.word_count}")
        print(f"  Execution time: {execution_time:.2f}s")