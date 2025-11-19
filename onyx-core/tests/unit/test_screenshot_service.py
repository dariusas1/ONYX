"""
Unit tests for screenshot functionality.

Tests BrowserManager screenshot enhancements and API validation.
"""

import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from pydantic import ValidationError

# Import the models and functions to test
from onyx.api.web_tools import (
    ScreenshotRequest,
    ScreenshotResponse,
    ScreenshotResponseData,
    capture_screenshot
)
from onyx.services.browser_manager import BrowserManager


class TestScreenshotRequestValidation:
    """Test ScreenshotRequest Pydantic model validation."""

    def test_valid_screenshot_request_minimal(self):
        """Test valid screenshot request with minimal parameters."""
        request = ScreenshotRequest(url="https://example.com")
        assert request.url == "https://example.com"
        assert request.full_page is True
        assert request.format == "png"
        assert request.quality is None
        assert request.selector is None

    def test_valid_screenshot_request_full(self):
        """Test valid screenshot request with all parameters."""
        request = ScreenshotRequest(
            url="https://example.com",
            full_page=False,
            format="jpeg",
            quality=85,
            selector=".main-content",
            width=1920,
            height=1080,
            wait_strategy="domcontentloaded"
        )
        assert request.format == "jpeg"
        assert request.quality == 85
        assert request.selector == ".main-content"
        assert request.width == 1920
        assert request.height == 1080
        assert request.wait_strategy == "domcontentloaded"

    def test_invalid_quality_with_png(self):
        """Test that quality parameter is rejected for PNG format."""
        with pytest.raises(ValidationError) as exc_info:
            ScreenshotRequest(
                url="https://example.com",
                format="png",
                quality=85
            )
        assert "quality parameter only applies to JPEG format" in str(exc_info.value)

    def test_invalid_jpeg_quality_range(self):
        """Test that JPEG quality is validated to be within 1-100 range."""
        with pytest.raises(ValidationError):
            ScreenshotRequest(
                url="https://example.com",
                format="jpeg",
                quality=0  # Too low
            )

        with pytest.raises(ValidationError):
            ScreenshotRequest(
                url="https://example.com",
                format="jpeg",
                quality=101  # Too high
            )

    def test_invalid_viewport_dimensions(self):
        """Test that viewport dimensions are validated."""
        with pytest.raises(ValidationError):
            ScreenshotRequest(
                url="https://example.com",
                width=50  # Too small
            )

        with pytest.raises(ValidationError):
            ScreenshotRequest(
                url="https://example.com",
                height=5000  # Too large
            )


class TestBrowserManagerScreenshot:
    """Test enhanced BrowserManager screenshot functionality."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright Page object."""
        page = AsyncMock()
        page.viewport_size = {"width": 1280, "height": 720}
        page.screenshot = AsyncMock(return_value=b"fake_png_data")
        page.set_viewport_size = AsyncMock()
        page.query_selector = AsyncMock(return_value=MagicMock())
        return page

    @pytest.fixture
    def mock_element(self):
        """Create a mock Playwright ElementHandle."""
        element = AsyncMock()
        element.screenshot = AsyncMock(return_value=b"fake_element_data")
        return element

    @pytest.fixture
    async def browser_manager(self):
        """Create BrowserManager instance for testing."""
        manager = BrowserManager()
        # Mock the operation lock to avoid async complexity in tests
        manager._operation_lock = AsyncMock()
        manager._operation_lock.__aenter__ = AsyncMock(return_value=None)
        manager._operation_lock.__aexit__ = AsyncMock(return_value=None)
        return manager

    @pytest.mark.asyncio
    async def test_screenshot_base64_png(self, browser_manager, mock_page):
        """Test basic PNG screenshot with base64 encoding."""
        # Mock the page screenshot method
        mock_page.screenshot.return_value = b"fake_png_data"

        with patch.object(browser_manager._operation_lock, '__aenter__'), \
             patch.object(browser_manager._operation_lock, '__aexit__'):
            result = await browser_manager.screenshot_base64(
                page=mock_page,
                format="png"
            )

        # Verify base64 encoding
        assert result.startswith("data:image/png;base64,")
        # Decode and verify original data
        encoded_data = result.split(',')[1]
        decoded_data = base64.b64decode(encoded_data)
        assert decoded_data == b"fake_png_data"

    @pytest.mark.asyncio
    async def test_screenshot_with_selector(self, browser_manager, mock_page, mock_element):
        """Test element-specific screenshot capture."""
        # Mock element query and screenshot
        mock_page.query_selector.return_value = mock_element
        mock_element.screenshot.return_value = b"fake_element_data"

        with patch.object(browser_manager._operation_lock, '__aenter__'), \
             patch.object(browser_manager._operation_lock, '__aexit__'):
            result = await browser_manager.screenshot(
                page=mock_page,
                selector=".main-content",
                format="png"
            )

        assert result == b"fake_element_data"
        mock_page.query_selector.assert_called_once_with(".main-content")
        mock_element.screenshot.assert_called_once_with(type="png", quality=None)

    @pytest.mark.asyncio
    async def test_screenshot_with_viewport_override(self, browser_manager, mock_page):
        """Test screenshot with custom viewport dimensions."""
        with patch.object(browser_manager._operation_lock, '__aenter__'), \
             patch.object(browser_manager._operation_lock, '__aexit__'):
            await browser_manager.screenshot(
                page=mock_page,
                width=1920,
                height=1080,
                format="png"
            )

        # Verify viewport was set
        mock_page.set_viewport_size.assert_called_once_with({"width": 1920, "height": 1080})
        mock_page.screenshot.assert_called_once_with(full_page=True, type="png", quality=None)

    @pytest.mark.asyncio
    async def test_screenshot_element_not_found(self, browser_manager, mock_page):
        """Test error handling when selector element is not found."""
        mock_page.query_selector.return_value = None

        with patch.object(browser_manager._operation_lock, '__aenter__'), \
             patch.object(browser_manager._operation_lock, '__aexit__'), \
             pytest.raises(ValueError, match="Element not found for selector: .nonexistent"):
            await browser_manager.screenshot(
                page=mock_page,
                selector=".nonexistent"
            )

    @pytest.mark.asyncio
    async def test_screenshot_jpeg_quality(self, browser_manager, mock_page):
        """Test JPEG screenshot with quality settings."""
        with patch.object(browser_manager._operation_lock, '__aenter__'), \
             patch.object(browser_manager._operation_lock, '__aexit__'):
            await browser_manager.screenshot(
                page=mock_page,
                format="jpeg",
                quality=85
            )

        mock_page.screenshot.assert_called_once_with(
            full_page=True,
            type="jpeg",
            quality=85
        )


class TestScreenshotAPI:
    """Test screenshot API endpoint."""

    @pytest.fixture
    def mock_current_user(self):
        """Mock authenticated user."""
        return {"user_id": "test_user_123", "email": "test@example.com"}

    @pytest.fixture
    def mock_browser_manager(self):
        """Mock BrowserManager for API tests."""
        manager = AsyncMock()
        manager.navigate = AsyncMock()
        manager.screenshot_base64 = AsyncMock(return_value="data:image/png;base64,fake_data")
        manager.close_page = AsyncMock()
        return manager

    @pytest.mark.asyncio
    @patch('onyx.api.web_tools.BrowserManager.get_instance')
    async def test_screenshot_api_success(self, mock_get_instance, mock_browser_manager, mock_current_user):
        """Test successful screenshot API call."""
        mock_get_instance.return_value = mock_browser_manager
        mock_browser_manager.navigate.return_value = AsyncMock()
        mock_browser_manager.navigate.return_value.viewport_size = {"width": 1920, "height": 1080}

        # Mock page object
        mock_page = AsyncMock()
        mock_page.viewport_size = {"width": 1920, "height": 1080}
        mock_browser_manager.navigate.return_value = mock_page

        request = ScreenshotRequest(url="https://example.com")

        with patch('onyx.api.web_tools.asyncio.get_event_loop') as mock_event_loop:
            mock_event_loop.return_value.time.return_value = 123456789.0

            response = await capture_screenshot(request, mock_current_user)

        assert response.success is True
        assert response.data is not None
        assert response.data.url == "https://example.com"
        assert response.data.format == "png"
        assert response.data.full_page is True
        assert response.data.width == 1920
        assert response.data.height == 1080
        assert response.data.data_url == "data:image/png;base64,fake_data"
        assert "execution_time_ms" in response.data.__dict__

        # Verify browser manager methods were called
        mock_browser_manager.navigate.assert_called_once_with("https://example.com", wait_until="load")
        mock_browser_manager.screenshot_base64.assert_called_once()
        mock_browser_manager.close_page.assert_called_once()

    @pytest.mark.asyncio
    @patch('onyx.api.web_tools.BrowserManager.get_instance')
    async def test_screenshot_api_with_selector(self, mock_get_instance, mock_browser_manager, mock_current_user):
        """Test screenshot API with CSS selector."""
        mock_get_instance.return_value = mock_browser_manager

        # Mock page object
        mock_page = AsyncMock()
        mock_page.viewport_size = {"width": 1280, "height": 720}
        mock_browser_manager.navigate.return_value = mock_page

        request = ScreenshotRequest(
            url="https://example.com",
            selector=".main-content",
            format="jpeg",
            quality=75
        )

        with patch('onyx.api.web_tools.asyncio.get_event_loop') as mock_event_loop:
            mock_event_loop.return_value.time.return_value = 123456789.0

            response = await capture_screenshot(request, mock_current_user)

        assert response.success is True
        assert response.data.selector == ".main-content"
        assert response.data.format == "jpeg"

        # Verify correct parameters passed to screenshot method
        mock_browser_manager.screenshot_base64.assert_called_once_with(
            page=mock_page,
            full_page=True,
            format="jpeg",
            quality=75,
            selector=".main-content",
            width=None,
            height=None
        )

    @pytest.mark.asyncio
    @patch('onyx.api.web_tools.BrowserManager.get_instance')
    async def test_screenshot_api_navigation_error(self, mock_get_instance, mock_current_user):
        """Test screenshot API with navigation error."""
        mock_get_instance.side_effect = Exception("Navigation failed")

        request = ScreenshotRequest(url="https://example.com")

        with patch('onyx.api.web_tools.asyncio.get_event_loop') as mock_event_loop:
            mock_event_loop.return_value.time.return_value = 123456789.0

            with pytest.raises(HTTPException) as exc_info:
                await capture_screenshot(request, mock_current_user)

            assert exc_info.value.status_code == 500
            response_detail = exc_info.value.detail
            assert response_detail["code"] == "SCREENSHOT_CAPTURE_ERROR"
            assert "Navigation failed" in response_detail["message"]


class TestScreenshotResponseData:
    """Test ScreenshotResponseData model."""

    def test_screenshot_response_data_creation(self):
        """Test creating ScreenshotResponseData."""
        data = ScreenshotResponseData(
            url="https://example.com",
            format="png",
            full_page=True,
            data_url="data:image/png;base64,fake_data",
            width=1920,
            height=1080,
            file_size_bytes=12345,
            execution_time_ms=2500
        )

        assert data.url == "https://example.com"
        assert data.format == "png"
        assert data.full_page is True
        assert data.width == 1920
        assert data.height == 1080
        assert data.file_size_bytes == 12345
        assert data.execution_time_ms == 2500
        assert data.selector is None


if __name__ == "__main__":
    pytest.main([__file__])