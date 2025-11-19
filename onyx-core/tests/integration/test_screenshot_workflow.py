"""
Integration tests for screenshot workflow.

Tests end-to-end screenshot capture with real browser automation.
"""

import pytest
import asyncio
import base64
from playwright.async_api import async_playwright, Browser
from fastapi.testclient import TestClient
from unittest.mock import patch
import tempfile
import os

# Import the components to test
from onyx.api.web_tools import app, ScreenshotRequest
from onyx.services.browser_manager import BrowserManager


class TestScreenshotWorkflow:
    """Integration tests for screenshot functionality."""

    @pytest.fixture(scope="class")
    async def browser(self):
        """Create a real browser instance for integration tests."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            yield browser
            await browser.close()

    @pytest.fixture(scope="class")
    async def browser_manager(self, browser):
        """Create BrowserManager instance for testing."""
        manager = BrowserManager()
        manager.browser = browser
        manager.context = await browser.new_context()
        manager._is_initialized = True
        yield manager
        # Cleanup
        if manager.context:
            await manager.context.close()

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_current_user(self):
        """Mock authenticated user."""
        return {"user_id": "integration_test_user", "email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_real_screenshot_capture(self, browser_manager):
        """Test actual screenshot capture with simple HTML content."""
        # Create a test page with some content
        page = await browser_manager.context.new_page()

        # Set content to a simple test page
        await page.set_content("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #f0f0f0; padding: 20px; }
                .content { margin: 20px 0; }
                .footer { background: #f0f0f0; padding: 10px; text-align: center; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Test Page Title</h1>
            </div>
            <div class="content">
                <p>This is a test paragraph for screenshot integration testing.</p>
                <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
            </div>
            <div class="footer">
                <p>Footer content</p>
            </div>
        </body>
        </html>
        """)

        try:
            # Test full page screenshot
            screenshot_bytes = await browser_manager.screenshot(page, full_page=True, format="png")

            # Verify screenshot was captured
            assert len(screenshot_bytes) > 1000  # Should be a reasonable size PNG
            assert screenshot_bytes.startswith(b'\x89PNG\r\n\x1a\n')  # PNG header

            # Test element-specific screenshot
            header_screenshot = await browser_manager.screenshot(
                page,
                selector=".header",
                format="png"
            )
            assert len(header_screenshot) > 500
            assert header_screenshot.startswith(b'\x89PNG\r\n\x1a\n')

            # Test JPEG format
            jpeg_screenshot = await browser_manager.screenshot(
                page,
                full_page=True,
                format="jpeg",
                quality=80
            )
            assert len(jpeg_screenshot) > 1000
            assert jpeg_screenshot.startswith(b'\xff\xd8\xff')  # JPEG header

            # Test base64 encoding
            base64_screenshot = await browser_manager.screenshot_base64(
                page,
                full_page=True,
                format="png"
            )
            assert base64_screenshot.startswith("data:image/png;base64,")

            # Verify base64 can be decoded back
            decoded_data = base64.b64decode(base64_screenshot.split(',')[1])
            assert decoded_data.startswith(b'\x89PNG\r\n\x1a\n')

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_viewport_configuration(self, browser_manager):
        """Test screenshot with custom viewport dimensions."""
        page = await browser_manager.context.new_page()

        try:
            # Set content that will be affected by viewport
            await page.set_content("""
            <html>
            <head><style>
                body { margin: 0; width: 100vw; height: 100vh; background: linear-gradient(45deg, #ff0000, #0000ff); }
                .size { position: absolute; bottom: 10px; right: 10px; background: white; padding: 5px; }
            </style></head>
            <body>
                <div class="size" id="dimensions"></div>
                <script>
                    document.getElementById('dimensions').textContent = window.innerWidth + 'x' + window.innerHeight;
                </script>
            </body>
            </html>
            """)

            # Test custom viewport
            custom_width, custom_height = 800, 600
            await browser_manager.screenshot(
                page,
                width=custom_width,
                height=custom_height,
                format="png"
            )

            # Verify viewport was set (check that page.viewport_size was called)
            # Note: In a real scenario, you'd verify the screenshot dimensions match the viewport

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_screenshot_performance(self, browser_manager):
        """Test screenshot performance timing."""
        page = await browser_manager.context.new_page()

        try:
            # Simple test page
            await page.set_content("<html><body><h1>Performance Test</h1></body></html>")

            # Time multiple screenshot captures
            import time
            start_time = time.time()

            for i in range(5):
                screenshot_bytes = await browser_manager.screenshot(page, full_page=True, format="png")
                assert len(screenshot_bytes) > 1000

            elapsed_time = time.time() - start_time
            avg_time = elapsed_time / 5

            # Performance assertion (should be under 2 seconds per screenshot on average)
            assert avg_time < 2.0, f"Average screenshot time {avg_time:.2f}s exceeds performance target"
            assert elapsed_time < 5.0, f"Total time {elapsed_time:.2f}s for 5 screenshots exceeds performance target"

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_element_selector_error_handling(self, browser_manager):
        """Test error handling for invalid CSS selectors."""
        page = await browser_manager.context.new_page()

        try:
            await page.set_content("<html><body><p>Test content</p></body></html>")

            # Test with non-existent selector
            with pytest.raises(ValueError, match="Element not found for selector"):
                await browser_manager.screenshot(
                    page,
                    selector=".nonexistent-element"
                )

            # Test with invalid selector syntax
            with pytest.raises(Exception):  # Playwright will raise an error for invalid syntax
                await browser_manager.screenshot(
                    page,
                    selector="##invalid##selector##"
                )

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_screenshot_quality_comparison(self, browser_manager):
        """Test different quality settings for JPEG format."""
        page = await browser_manager.context.new_page()

        try:
            # Create a page with some visual complexity
            await page.set_content("""
            <html>
            <head><style>
                body {
                    background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4, #ffeaa7);
                    margin: 0; padding: 50px;
                    font-size: 24px;
                    font-weight: bold;
                }
            </style></head>
            <body>
                <h1>Quality Test</h1>
                <p>This page has gradients and colors to test JPEG compression.</p>
            </body>
            </html>
            """)

            # Capture with different quality levels
            high_quality = await browser_manager.screenshot(page, format="jpeg", quality=90)
            medium_quality = await browser_manager.screenshot(page, format="jpeg", quality=70)
            low_quality = await browser_manager.screenshot(page, format="jpeg", quality=30)

            # High quality should be larger than low quality
            assert len(high_quality) > len(medium_quality) > len(low_quality)

            # All should be valid JPEGs
            for screenshot in [high_quality, medium_quality, low_quality]:
                assert screenshot.startswith(b'\xff\xd8\xff')  # JPEG header

        finally:
            await page.close()

    @pytest.mark.asyncio
    async def test_browser_manager_singleton_behavior(self):
        """Test that BrowserManager maintains singleton behavior."""
        manager1 = await BrowserManager.get_instance()
        manager2 = await BrowserManager.get_instance()

        # Should be the same instance
        assert manager1 is manager2

        # Should have the same operation lock
        assert manager1._operation_lock is manager2._operation_lock


# API Integration Tests (these would require a running server)
class TestScreenshotAPIIntegration:
    """Integration tests for screenshot API endpoint."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_current_user(self):
        """Mock authenticated user."""
        return {"user_id": "api_test_user", "email": "api-test@example.com"}

    @patch('onyx.api.web_tools.BrowserManager.get_instance')
    @patch('onyx.api.web_tools.require_authenticated_user')
    def test_api_screenshot_request_validation(self, mock_auth, mock_get_instance, client, mock_current_user):
        """Test API request validation."""
        mock_auth.return_value = mock_current_user

        # Test invalid URL format
        response = client.post(
            "/tools/screenshot",
            json={
                "url": "not-a-valid-url",
                "format": "png"
            }
        )
        assert response.status_code == 422  # Validation error

    @patch('onyx.api.web_tools.BrowserManager.get_instance')
    @patch('onyx.api.web_tools.require_authenticated_user')
    def test_api_jpeg_quality_validation(self, mock_auth, mock_get_instance, client, mock_current_user):
        """Test API validation for JPEG quality parameter."""
        mock_auth.return_value = mock_current_user

        # Test quality parameter with PNG format (should fail)
        response = client.post(
            "/tools/screenshot",
            json={
                "url": "https://example.com",
                "format": "png",
                "quality": 80  # Invalid: quality only applies to JPEG
            }
        )
        assert response.status_code == 422  # Validation error

    @patch('onyx.api.web_tools.BrowserManager.get_instance')
    @patch('onyx.api.web_tools.require_authenticated_user')
    def test_api_dimension_validation(self, mock_auth, mock_get_instance, client, mock_current_user):
        """Test API validation for viewport dimensions."""
        mock_auth.return_value = mock_current_user

        # Test invalid viewport dimensions
        response = client.post(
            "/tools/screenshot",
            json={
                "url": "https://example.com",
                "width": 50  # Too small (minimum 100)
            }
        )
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__])