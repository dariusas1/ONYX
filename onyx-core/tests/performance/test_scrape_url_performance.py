"""
Performance tests for Web Scraping functionality

Validates that all scraping operations meet the <5s execution time requirement (AC7.3.5)
and other performance criteria specified in the acceptance criteria.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict
from playwright.async_api import async_playwright

# Import modules to test
from services.browser_manager import BrowserManager
from api.web_scraping import ContentExtractor


class TestScrapingPerformanceRequirements:
    """Performance tests for Story 7.3 acceptance criteria."""

    @pytest.mark.asyncio
    async def test_ac7_3_5_execution_time_under_5_seconds(self):
        """
        AC7.3.5: Execution time <5s from navigation to clean content

        This is the critical performance requirement. Tests multiple URLs to ensure
        consistent performance across different page types.
        """
        browser_manager = await BrowserManager.get_instance()
        extractor = ContentExtractor()

        # Test URLs of different types and complexities
        test_urls = [
            ("https://example.com", "Simple static page"),
            ("https://httpbin.org/html", "Medium complexity HTML"),
            ("https://httpbin.org/forms/post", "Form page")
        ]

        performance_results = []

        for url, description in test_urls:
            print(f"\nTesting: {description} ({url})")

            # Measure complete scraping workflow
            start_time = time.time()

            try:
                # Step 1: Navigate and scrape (should be <5s total)
                scrape_result = await browser_manager.scrape_page(
                    url,
                    max_execution_time_ms=5000
                )

                page = scrape_result["page"]
                metrics = scrape_result["metrics"]

                # Step 2: Extract content
                html_content = await page.content()
                extraction_result = extractor.extract_content(html_content, url)

                end_time = time.time()
                total_execution_time = (end_time - start_time) * 1000  # Convert to ms

                performance_results.append({
                    "url": url,
                    "description": description,
                    "total_time_ms": total_execution_time,
                    "navigation_time_ms": metrics["execution_time_ms"],
                    "content_length": extraction_result["content_length"],
                    "word_count": metrics["content_metrics"]["word_count"],
                    "performance_ok": metrics["performance_ok"]
                })

                # Verify AC7.3.5 requirement
                assert total_execution_time <= 5000, (
                    f"AC7.3.5 FAILED: {url} took {total_execution_time:.2f}ms "
                    f"(exceeds 5000ms limit)"
                )

                print(f"✓ PASSED: {total_execution_time:.2f}ms, "
                      f"{extraction_result['content_length']} chars")

            finally:
                # Cleanup
                if 'page' in locals():
                    await browser_manager.close_page(page)

        # Statistical analysis
        times = [r["total_time_ms"] for r in performance_results]
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)

        print(f"\nPerformance Summary:")
        print(f"  Average time: {avg_time:.2f}ms")
        print(f"  Min time: {min_time:.2f}ms")
        print(f"  Max time: {max_time:.2f}ms")

        # Additional performance assertions
        assert avg_time <= 4000, f"Average time {avg_time:.2f}ms should be < 4000ms"
        assert max_time <= 5000, f"Max time {max_time:.2f}ms should be < 5000ms"

    @pytest.mark.asyncio
    async def test_memory_usage_during_scraping(self):
        """
        Test memory usage during scraping operations to ensure no memory leaks.

        While not explicitly in ACs, memory management is critical for production.
        """
        browser_manager = await BrowserManager.get_instance()

        initial_memory = await browser_manager.check_memory()
        print(f"Initial memory: {initial_memory}MB")

        # Perform multiple scraping operations
        memory_readings = [initial_memory]

        for i in range(5):
            result = await browser_manager.scrape_page(
                "https://example.com",
                max_execution_time_ms=5000
            )

            await browser_manager.close_page(result["page"])

            # Check memory after each operation
            current_memory = await browser_manager.check_memory()
            memory_readings.append(current_memory)

            print(f"Operation {i+1} memory: {current_memory}MB")

        # Analyze memory usage
        max_memory = max(memory_readings)
        memory_growth = max_memory - initial_memory

        print(f"Memory analysis:")
        print(f"  Initial: {initial_memory}MB")
        print(f"  Peak: {max_memory}MB")
        print(f"  Growth: {memory_growth}MB")

        # Memory should not exceed the configured limit
        assert max_memory <= browser_manager.max_memory_mb, (
            f"Memory usage {max_memory}MB exceeds limit {browser_manager.max_memory_mb}MB"
        )

        # Memory growth should be reasonable (<200MB for this test)
        assert memory_growth <= 200, (
            f"Memory growth {memory_growth}MB seems excessive"
        )

    @pytest.mark.asyncio
    async def test_content_extraction_performance(self):
        """
        Test performance of content extraction specifically.

        Content extraction should be fast (<1s for typical pages).
        """
        extractor = ContentExtractor()

        # Test HTML of different sizes
        test_cases = [
            ("<html><body><h1>Small</h1><p>Small content</p></body></html>", "Small page"),
            ("<html><body>" + "<p>Paragraph content. " * 100 + "</p></body></html>", "Medium page"),
            ("<html><body>" + "<div>Content block. " * 500 + "</div></body></html>", "Large page")
        ]

        for html_content, description in test_cases:
            print(f"\nTesting content extraction: {description}")

            start_time = time.time()
            result = extractor.extract_content(html_content, "https://example.com")
            end_time = time.time()

            extraction_time = (end_time - start_time) * 1000

            print(f"  Content length: {len(html_content)} chars")
            print(f"  Extracted: {result['content_length']} chars")
            print(f"  Time: {extraction_time:.2f}ms")

            # Content extraction should be fast
            assert extraction_time <= 1000, (
                f"Content extraction took {extraction_time:.2f}ms "
                f"for {description}, should be < 1000ms"
            )

            # Verify extraction quality
            assert result["content_length"] > 0, "No content extracted"
            assert "metadata" in result, "No metadata extracted"

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self):
        """
        Test performance when handling multiple requests (serial execution).

        Even though operations are serialized, overall throughput should be reasonable.
        """
        browser_manager = await BrowserManager.get_instance()

        num_requests = 3
        start_time = time.time()

        # Execute scraping requests sequentially (as designed)
        results = []
        for i in range(num_requests):
            url = f"https://httpbin.org/delay/{i % 2}"  # Alternate between 0s and 1s delays
            result = await browser_manager.scrape_page(url, max_execution_time_ms=5000)
            results.append(result)
            await browser_manager.close_page(result["page"])

        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        avg_time_per_request = total_time / num_requests

        print(f"Sequential performance ({num_requests} requests):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average per request: {avg_time_per_request:.2f}ms")

        # Each request should average less than 5 seconds
        assert avg_time_per_request <= 5000, (
            f"Average time per request {avg_time_per_request:.2f}ms "
            f"exceeds 5000ms limit"
        )

        # All individual requests should meet the requirement
        for i, result in enumerate(results):
            assert result["metrics"]["performance_ok"], (
                f"Request {i+1} failed performance requirement"
            )

    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """
        Test that error handling doesn't cause significant performance degradation.
        """
        browser_manager = await BrowserManager.get_instance()

        # Test various error scenarios
        error_scenarios = [
            ("https://nonexistent-domain-12345.com", "DNS resolution failure"),
            ("https://httpbin.org/status/404", "404 Not Found"),
            ("https://httpbin.org/status/500", "500 Server Error"),
        ]

        for url, description in error_scenarios:
            print(f"\nTesting error handling: {description}")

            start_time = time.time()

            try:
                result = await browser_manager.scrape_page(url, max_execution_time_ms=5000)
                # If it succeeds, that's fine (some test URLs might actually work)
                if result["page"]:
                    await browser_manager.close_page(result["page"])
            except Exception as e:
                # Expected for some scenarios
                print(f"  Expected error: {str(e)[:100]}")

            end_time = time.time()
            error_handling_time = (end_time - start_time) * 1000

            print(f"  Error handling time: {error_handling_time:.2f}ms")

            # Error handling should be fast (<10s worst case)
            assert error_handling_time <= 10000, (
                f"Error handling took {error_handling_time:.2f}ms, "
                f"should complete quickly even on errors"
            )

    def test_content_quality_metrics(self):
        """
        Test that extracted content meets quality standards.

        This isn't strictly performance but relates to AC7.3.3 and AC7.3.4.
        """
        extractor = ContentExtractor()

        # Test content with various elements
        html_content = """
        <html>
        <head>
            <title>Test Article</title>
            <meta name="author" content="Test Author">
        </head>
        <body>
            <script>var test = 'should be removed';</script>
            <style>.css { display: none; }</style>
            <nav>Navigation menu</nav>

            <main>
                <article>
                    <h1>Main Article Title</h1>
                    <p>This is the main content that should be preserved.</p>
                    <blockquote>Important quote that should be kept.</blockquote>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                </article>
            </main>

            <footer>Copyright notice</footer>
            <div class="ads">Advertisement</div>
        </body>
        </html>
        """

        result = extractor.extract_content(html_content, "https://example.com")

        # Content quality checks
        text_content = result["text_content"]

        # Main content should be preserved
        assert "Main Article Title" in text_content
        assert "This is the main content" in text_content
        assert "Important quote" in text_content
        assert "Item 1" in text_content

        # Scripts and styles should be removed
        assert "should be removed" not in text_content
        assert "display: none" not in text_content

        # Metadata should be extracted correctly
        metadata = result["metadata"]
        assert metadata["title"] == "Test Article"
        assert metadata["author"] == "Test Author"

        # Content length should be reasonable (not too short, not too long)
        assert 100 <= len(text_content) <= 10000  # Reasonable range


class TestPerformanceRegression:
    """
    Regression tests to ensure performance doesn't degrade over time.

    These tests establish performance baselines that should be maintained
    as the codebase evolves.
    """

    @pytest.mark.asyncio
    async def test_baseline_performance_metrics(self):
        """
        Establish baseline performance metrics for future regression testing.
        """
        browser_manager = await BrowserManager.get_instance()
        extractor = ContentExtractor()

        # Use a consistent test case
        test_url = "https://example.com"

        # Run multiple iterations to get stable measurements
        iterations = 3
        performance_data = []

        for i in range(iterations):
            print(f"Baseline test iteration {i+1}/{iterations}")

            # Complete workflow timing
            start_time = time.time()

            # Navigation and scraping
            scrape_result = await browser_manager.scrape_page(
                test_url,
                max_execution_time_ms=5000
            )

            page = scrape_result["page"]
            navigation_time = scrape_result["metrics"]["execution_time_ms"]

            # Content extraction
            html_content = await page.content()
            extraction_start = time.time()
            extraction_result = extractor.extract_content(html_content, test_url)
            extraction_time = (time.time() - extraction_start) * 1000

            total_time = (time.time() - start_time) * 1000

            performance_data.append({
                "total_time_ms": total_time,
                "navigation_time_ms": navigation_time,
                "extraction_time_ms": extraction_time,
                "content_length": extraction_result["content_length"]
            })

            await browser_manager.close_page(page)

        # Calculate statistics
        total_times = [d["total_time_ms"] for d in performance_data]
        nav_times = [d["navigation_time_ms"] for d in performance_data]
        extract_times = [d["extraction_time_ms"] for d in performance_data]

        baseline = {
            "avg_total_time_ms": statistics.mean(total_times),
            "avg_navigation_time_ms": statistics.mean(nav_times),
            "avg_extraction_time_ms": statistics.mean(extract_times),
            "max_total_time_ms": max(total_times),
            "min_total_time_ms": min(total_times)
        }

        print(f"\nPerformance Baseline Established:")
        print(f"  Average total time: {baseline['avg_total_time_ms']:.2f}ms")
        print(f"  Average navigation: {baseline['avg_navigation_time_ms']:.2f}ms")
        print(f"  Average extraction: {baseline['avg_extraction_time_ms']:.2f}ms")
        print(f"  Max total time: {baseline['max_total_time_ms']:.2f}ms")

        # Baseline assertions (these establish the current performance level)
        assert baseline["avg_total_time_ms"] <= 4000, "Baseline total time too high"
        assert baseline["avg_navigation_time_ms"] <= 3500, "Baseline navigation time too high"
        assert baseline["avg_extraction_time_ms"] <= 500, "Baseline extraction time too high"
        assert baseline["max_total_time_ms"] <= 5000, "Baseline max time exceeds requirement"

        # These values can be used for future regression testing
        # Store them in a file or test data for comparison in future runs
        return baseline


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])