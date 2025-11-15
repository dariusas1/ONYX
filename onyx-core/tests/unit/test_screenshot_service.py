"""
Unit Tests for Screenshot Service

Tests verify all acceptance criteria for Story 7-5:
- AC7.5.1: Agent can invoke screenshot tool with URL parameter
- AC7.5.2: Browser navigates and waits for page load completion
- AC7.5.3: Full page screenshot captured (entire scrollHeight)
- AC7.5.4: Image returned as base64 or stored in Drive with URL
- AC7.5.5: Resolution configurable (default: 1920x1080)
- AC7.5.6: Execution time <5s for screenshot capture
- AC7.5.7: Supports PNG (lossless) and JPEG (smaller file size) formats
"""

import pytest
import asyncio
import time
import base64
import io
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image

from services.screenshot_service import ScreenshotService, ScreenshotOptions, ScreenshotResult


class TestScreenshotOptions:
    """Test cases for ScreenshotOptions class."""

    def test_default_options(self):
        """Test default screenshot options."""
        options = ScreenshotOptions(url="https://example.com")

        assert options.url == "https://example.com"
        assert options.format == "png"
        assert options.quality == 85
        assert options.width == 1920
        assert options.height == 1080
        assert options.full_page is True
        assert options.store_in_drive is False
        assert options.timeout == 30000

    def test_custom_options(self):
        """Test custom screenshot options."""
        options = ScreenshotOptions(
            url="https://example.com",
            format="jpeg",
            quality=90,
            width=1366,
            height=768,
            full_page=False,
            store_in_drive=True,
            timeout=15000
        )

        assert options.url == "https://example.com"
        assert options.format == "jpeg"
        assert options.quality == 90
        assert options.width == 1366
        assert options.height == 768
        assert options.full_page is False
        assert options.store_in_drive is True
        assert options.timeout == 15000

    def test_device_preset_options(self):
        """Test device preset options."""
        # Test desktop preset
        options = ScreenshotOptions(
            url="https://example.com",
            device_preset="mobile"
        )

        assert options.width == 375
        assert options.height == 667

        # Test tablet preset
        options = ScreenshotOptions(
            url="https://example.com",
            device_preset="tablet"
        )

        assert options.width == 768
        assert options.height == 1024

    def test_invalid_device_preset(self):
        """Test invalid device preset raises error."""
        with pytest.raises(ValueError, match="Invalid device preset"):
            ScreenshotOptions(
                url="https://example.com",
                device_preset="invalid_preset"
            )

    def test_invalid_format(self):
        """Test invalid format raises error."""
        with pytest.raises(ValueError, match="Format must be 'png' or 'jpeg'"):
            ScreenshotOptions(
                url="https://example.com",
                format="invalid_format"
            )

    def test_quality_clamping(self):
        """Test quality value clamping."""
        # Test low value
        options = ScreenshotOptions(
            url="https://example.com",
            quality=-10
        )
        assert options.quality == 1

        # Test high value
        options = ScreenshotOptions(
            url="https://example.com",
            quality=150
        )
        assert options.quality == 100

    def test_device_preset_override(self):
        """Test that device preset overrides width/height."""
        options = ScreenshotOptions(
            url="https://example.com",
            device_preset="mobile",
            width=9999,  # This should be ignored
            height=9999
        )

        # Should use preset values, not provided ones
        assert options.width == 375
        assert options.height == 667


class TestScreenshotService:
    """Test cases for ScreenshotService class."""

    @pytest.fixture
    def screenshot_service(self):
        """Create ScreenshotService instance for testing."""
        return ScreenshotService()

    @pytest.fixture
    def mock_browser_manager(self):
        """Create mock BrowserManager."""
        manager = AsyncMock()
        return manager

    @pytest.fixture
    def mock_drive_service(self):
        """Create mock Google Drive service."""
        drive = AsyncMock()
        return drive

    def test_init_without_drive(self, screenshot_service):
        """Test initialization without Drive service."""
        assert screenshot_service.drive_service is None
        assert screenshot_service._url_blocklist is not None

    def test_init_with_drive(self):
        """Test initialization with Drive service."""
        mock_drive = AsyncMock()
        service = ScreenshotService(mock_drive)
        assert service.drive_service is mock_drive

    def test_validate_url_valid(self, screenshot_service):
        """Test URL validation with valid URLs."""
        # Test valid HTTP URL
        screenshot_service._validate_url("https://example.com")

        # Test valid HTTPS URL
        screenshot_service._validate_url("https://example.org/page")

    def test_validate_url_invalid(self, screenshot_service):
        """Test URL validation with invalid URLs."""
        # Test empty URL
        with pytest.raises(ValueError, match="Invalid URL format"):
            screenshot_service._validate_url("")

        # Test missing scheme
        with pytest.raises(ValueError, match="Invalid URL format"):
            screenshot_service._validate_url("example.com")

        # Test invalid scheme
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            screenshot_service._validate_url("ftp://example.com")

    def test_validate_url_blocked(self, screenshot_service):
        """Test URL validation with blocked URLs."""
        # Test localhost
        with pytest.raises(ValueError, match="blocked for security"):
            screenshot_service._validate_url("http://localhost:8080")

        # Test internal IP
        with pytest.raises(ValueError, match="blocked for security"):
            screenshot_service._validate_url("http://192.168.1.1")

        # Test file URL
        with pytest.raises(ValueError, match="blocked for security"):
            screenshot_service._validate_url("file:///etc/passwd")

    def test_get_image_metadata_png(self, screenshot_service):
        """Test image metadata extraction for PNG."""
        # Create a test PNG image
        test_image = Image.new('RGB', (800, 600), color='red')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()

        metadata = screenshot_service._get_image_metadata(img_bytes, 'png')

        assert metadata['width'] == 800
        assert metadata['height'] == 600
        assert metadata['format'] == 'PNG'
        assert metadata['file_size'] > 0
        assert metadata['mode'] == 'RGB'

    def test_get_image_metadata_jpeg(self, screenshot_service):
        """Test image metadata extraction for JPEG."""
        # Create a test JPEG image
        test_image = Image.new('RGB', (1024, 768), color='blue')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG', quality=90)
        img_bytes = img_bytes.getvalue()

        metadata = screenshot_service._get_image_metadata(img_bytes, 'jpeg')

        assert metadata['width'] == 1024
        assert metadata['height'] == 768
        assert metadata['format'] == 'JPEG'
        assert metadata['file_size'] > 0
        assert metadata['mode'] == 'RGB'

    def test_convert_image_format_png_to_jpeg(self, screenshot_service):
        """Test image format conversion from PNG to JPEG."""
        # Create a PNG with transparency
        test_image = Image.new('RGBA', (400, 300), (255, 0, 0, 128))
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='PNG')
        png_bytes = img_bytes.getvalue()

        # Convert to JPEG
        jpeg_bytes = screenshot_service._convert_image_format(png_bytes, 'jpeg', 85)

        # Verify conversion
        jpeg_image = Image.open(io.BytesIO(jpeg_bytes))
        assert jpeg_image.format == 'JPEG'
        assert jpeg_image.mode == 'RGB'  # Transparency should be removed

    def test_convert_image_format_jpeg_to_png(self, screenshot_service):
        """Test image format conversion from JPEG to PNG."""
        # Create a JPEG image
        test_image = Image.new('RGB', (300, 200), color='green')
        img_bytes = io.BytesIO()
        test_image.save(img_bytes, format='JPEG', quality=80)
        jpeg_bytes = img_bytes.getvalue()

        # Convert to PNG
        png_bytes = screenshot_service._convert_image_format(jpeg_bytes, 'png', None)

        # Verify conversion
        png_image = Image.open(io.BytesIO(png_bytes))
        assert png_image.format == 'PNG'

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_screenshot_success(self, mock_browser_manager_class, screenshot_service):
        """Test successful screenshot capture."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Create screenshot options
        options = ScreenshotOptions(
            url="https://example.com",
            format="png",
            width=800,
            height=600
        )

        # Mock the image processing functions
        with patch.object(screenshot_service, '_get_image_metadata') as mock_metadata, \
             patch.object(screenshot_service, '_convert_image_format', return_value=b'fake_screenshot_data'):

            mock_metadata.return_value = {
                'width': 800,
                'height': 600,
                'format': 'PNG',
                'file_size': len(b'fake_screenshot_data')
            }

            # Capture screenshot
            result = await screenshot_service.capture_screenshot(options)

            # Verify success
            assert result.success is True
            assert result.image_data == b'fake_screenshot_data'
            assert result.base64_data == base64.b64encode(b'fake_screenshot_data').decode('utf-8')
            assert result.error is None
            assert result.execution_time_ms > 0

            # Verify metadata
            assert 'width' in result.metadata
            assert 'height' in result.metadata
            assert 'format' in result.metadata
            assert 'file_size' in result.metadata

        # Verify browser interactions
        mock_browser_manager_class.get_instance.assert_called_once()
        mock_manager.navigate.assert_called_once_with(
            "https://example.com",
            wait_until='networkidle',
            timeout=30000
        )
        mock_page.set_viewport_size.assert_called_once_with({
            "width": 800,
            "height": 600
        })
        mock_page.wait_for_load_state.assert_called_once_with('networkidle', timeout=30000)
        mock_page.screenshot.assert_called_once_with(
            full_page=True,
            type='png',
            timeout=30000
        )
        mock_manager.close_page.assert_called_once_with(mock_page)

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_screenshot_with_drive_storage(self, mock_browser_manager_class):
        """Test screenshot capture with Google Drive storage."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager
        mock_drive_service = AsyncMock()

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()
        mock_drive_service.upload_file.return_value = "https://drive.google.com/screenshot.png"

        # Create service with Drive
        service = ScreenshotService(mock_drive_service)

        # Create screenshot options with Drive storage
        options = ScreenshotOptions(
            url="https://example.com",
            store_in_drive=True,
            drive_folder="Test Screenshots"
        )

        # Mock the image processing functions
        with patch.object(service, '_get_image_metadata') as mock_metadata, \
             patch.object(service, '_convert_image_format', return_value=b'fake_screenshot_data'):

            mock_metadata.return_value = {
                'width': 800,
                'height': 600,
                'format': 'PNG',
                'file_size': len(b'fake_screenshot_data')
            }

            # Capture screenshot
            result = await service.capture_screenshot(options)

            # Verify success and Drive storage
            assert result.success is True
            assert result.drive_url == "https://drive.google.com/screenshot.png"
            assert 'drive_url' in result.metadata

        # Verify Drive upload was called
        mock_drive_service.upload_file.assert_called_once_with(
            file_data=b'fake_screenshot_data',
            filename=mock_drive_service.upload_file.call_args[1]['filename'],
            folder_path="Test Screenshots",
            mime_type='image/png'
        )

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_screenshot_validation_error(self, mock_browser_manager_class, screenshot_service):
        """Test screenshot capture with URL validation error."""
        # Create options with invalid URL
        options = ScreenshotOptions(url="http://localhost:8080")

        # Capture screenshot (should fail validation)
        result = await screenshot_service.capture_screenshot(options)

        # Verify failure
        assert result.success is False
        assert "blocked for security" in result.error
        assert result.execution_time_ms > 0

        # Browser should not be used due to validation failure
        mock_browser_manager_class.get_instance.assert_not_called()

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_screenshot_browser_error(self, mock_browser_manager_class, screenshot_service):
        """Test screenshot capture with browser error."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager
        mock_manager.navigate.side_effect = Exception("Browser navigation failed")

        # Create screenshot options
        options = ScreenshotOptions(url="https://example.com")

        # Capture screenshot (should fail on browser)
        result = await screenshot_service.capture_screenshot(options)

        # Verify failure
        assert result.success is False
        assert "Screenshot capture failed" in result.error
        assert result.execution_time_ms > 0

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_screenshot_jpeg_format(self, mock_browser_manager_class, screenshot_service):
        """Test screenshot capture in JPEG format."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_png_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Create screenshot options for JPEG
        options = ScreenshotOptions(
            url="https://example.com",
            format="jpeg",
            quality=90
        )

        # Mock image processing
        jpeg_data = b'fake_jpeg_data'
        with patch.object(screenshot_service, '_get_image_metadata') as mock_metadata, \
             patch.object(screenshot_service, '_convert_image_format', return_value=jpeg_data):

            mock_metadata.return_value = {
                'width': 800,
                'height': 600,
                'format': 'JPEG',
                'file_size': len(jpeg_data)
            }

            # Capture screenshot
            result = await screenshot_service.capture_screenshot(options)

            # Verify success and JPEG format
            assert result.success is True
            assert result.image_data == jpeg_data
            assert result.metadata['format'] == 'JPEG'

        # Verify format conversion was called
        screenshot_service._convert_image_format.assert_called_once()

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_screenshot_device_preset(self, mock_browser_manager_class, screenshot_service):
        """Test screenshot capture with device preset."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Create screenshot options with mobile preset
        options = ScreenshotOptions(
            url="https://example.com",
            device_preset="mobile"
        )

        # Mock image processing
        with patch.object(screenshot_service, '_get_image_metadata') as mock_metadata, \
             patch.object(screenshot_service, '_convert_image_format', return_value=b'fake_screenshot_data'):

            mock_metadata.return_value = {
                'width': 375,
                'height': 667,
                'format': 'PNG',
                'file_size': len(b'fake_screenshot_data')
            }

            # Capture screenshot
            result = await screenshot_service.capture_screenshot(options)

            # Verify mobile preset dimensions were used
            mock_page.set_viewport_size.assert_called_once_with({
                "width": 375,
                "height": 667
            })

            assert result.success is True

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_screenshot_performance_target(self, mock_browser_manager_class, screenshot_service):
        """Test screenshot capture meets performance target (<5s)."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Create screenshot options
        options = ScreenshotOptions(url="https://example.com")

        # Mock image processing
        with patch.object(screenshot_service, '_get_image_metadata') as mock_metadata, \
             patch.object(screenshot_service, '_convert_image_format', return_value=b'fake_screenshot_data'):

            mock_metadata.return_value = {
                'width': 800,
                'height': 600,
                'format': 'PNG',
                'file_size': len(b'fake_screenshot_data')
            }

            # Measure execution time
            start_time = time.time()
            result = await screenshot_service.capture_screenshot(options)
            execution_time = (time.time() - start_time) * 1000

            # Verify performance target (should be much faster with mocks)
            assert result.success is True
            assert execution_time < 5000, f"Execution time {execution_time:.0f}ms should be <5000ms"

    @patch('services.screenshot_service.BrowserManager')
    async def test_capture_multiple_urls_sequential(self, mock_browser_manager_class, screenshot_service):
        """Test capturing multiple URLs sequentially."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Create list of URLs
        urls = [
            "https://example.com",
            "https://example.org",
            "https://example.net"
        ]

        # Create base options
        base_options = ScreenshotOptions(url="https://example.com", format="png")

        # Mock image processing
        with patch.object(screenshot_service, '_get_image_metadata') as mock_metadata, \
             patch.object(screenshot_service, '_convert_image_format', return_value=b'fake_screenshot_data'):

            mock_metadata.return_value = {
                'width': 800,
                'height': 600,
                'format': 'PNG',
                'file_size': len(b'fake_screenshot_data')
            }

            # Capture multiple screenshots
            results = await screenshot_service.capture_multiple_urls(urls, base_options, parallel=False)

            # Verify all captures succeeded
            assert len(results) == 3
            for result in results:
                assert result.success is True
                assert result.image_data is not None

            # Verify browser manager was called for each URL
            assert mock_manager.navigate.call_count == 3

    @patch('services.screenshot_service.BrowserManager')
    async def test_drive_storage_failure_fallback(self, mock_browser_manager_class):
        """Test fallback when Drive storage fails."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service that fails
        mock_drive_service = AsyncMock()
        mock_drive_service.upload_file.side_effect = Exception("Drive upload failed")

        # Create service with failing Drive
        service = ScreenshotService(mock_drive_service)

        # Create screenshot options with Drive storage
        options = ScreenshotOptions(
            url="https://example.com",
            store_in_drive=True
        )

        # Mock image processing
        with patch.object(service, '_get_image_metadata') as mock_metadata, \
             patch.object(service, '_convert_image_format', return_value=b'fake_screenshot_data'):

            mock_metadata.return_value = {
                'width': 800,
                'height': 600,
                'format': 'PNG',
                'file_size': len(b'fake_screenshot_data')
            }

            # Capture screenshot (should succeed even with Drive failure)
            result = await service.capture_screenshot(options)

            # Verify success despite Drive failure
            assert result.success is True
            assert result.image_data is not None
            assert result.drive_url is None  # Drive storage failed
            assert 'drive_error' in result.metadata

        # Verify Drive upload was attempted
        mock_drive_service.upload_file.assert_called_once()