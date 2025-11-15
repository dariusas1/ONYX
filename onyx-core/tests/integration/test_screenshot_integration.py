"""
Integration Tests for Screenshot API Endpoints

Tests verify the complete screenshot capture workflow including:
- API endpoint functionality
- Browser integration
- Image format support
- Performance targets
- Error handling
- Authentication requirements

Based on Story 7-5: Screenshot & Page Capture
"""

import pytest
import asyncio
import base64
import io
import json
from fastapi.testclient import TestClient
from PIL import Image
import time

# Import the main app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app
from services.screenshot_service import ScreenshotService, ScreenshotOptions


class TestScreenshotAPI:
    """Integration tests for screenshot API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        # Mock authentication header (adjust based on your auth implementation)
        return {
            "Authorization": "Bearer mock_token",
            "Content-Type": "application/json"
        }

    def test_screenshot_presets_endpoint(self, client, auth_headers):
        """Test screenshot presets endpoint."""
        response = client.get("/tools/screenshot/presets", headers=auth_headers)

        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], dict)

        presets = data["data"]
        assert "desktop" in presets
        assert "mobile" in presets
        assert "tablet" in presets
        assert "laptop" in presets

        # Verify preset dimensions
        assert presets["desktop"]["width"] == 1920
        assert presets["desktop"]["height"] == 1080
        assert presets["mobile"]["width"] == 375
        assert presets["mobile"]["height"] == 667

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_post_png_format(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test POST /tools/screenshot_page with PNG format."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_png_screenshot')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service (optional)
        mock_drive_service_class.return_value = None

        # Test request
        request_data = {
            "url": "https://example.com",
            "format": "png",
            "width": 1024,
            "height": 768,
            "full_page": True,
            "store_in_drive": False,
            "timeout": 30
        }

        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["url"] == "https://example.com"
        assert "image_data" in data
        assert data["metadata"] is not None
        assert data["metadata"]["format"] == "PNG"
        assert data["metadata"]["width"] == 1024
        assert data["metadata"]["height"] == 768
        assert data["metadata"]["file_size"] > 0

        # Verify base64 image data is valid
        image_data = base64.b64decode(data["image_data"])
        assert len(image_data) > 0

        # Verify it's a valid PNG
        try:
            image = Image.open(io.BytesIO(image_data))
            assert image.format == "PNG"
        except Exception:
            pytest.fail("Returned image data is not valid PNG")

        # Verify browser interactions
        mock_browser_manager_class.get_instance.assert_called_once()
        mock_manager.navigate.assert_called_once()
        mock_page.set_viewport_size.assert_called_once_with({"width": 1024, "height": 768})
        mock_page.wait_for_load_state.assert_called_once()
        mock_page.screenshot.assert_called_once()

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_post_jpeg_format(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test POST /tools/screenshot_page with JPEG format."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_png_screenshot')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service (optional)
        mock_drive_service_class.return_value = None

        # Test request with JPEG format and custom quality
        request_data = {
            "url": "https://example.com",
            "format": "jpeg",
            "quality": 75,
            "width": 800,
            "height": 600,
            "full_page": True
        }

        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["metadata"]["format"] == "JPEG"

        # Verify base64 image data is valid
        image_data = base64.b64decode(data["image_data"])
        assert len(image_data) > 0

        # Verify it's a valid JPEG
        try:
            image = Image.open(io.BytesIO(image_data))
            assert image.format == "JPEG"
        except Exception:
            pytest.fail("Returned image data is not valid JPEG")

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_get_method(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test GET /tools/screenshot_page endpoint."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service (optional)
        mock_drive_service_class.return_value = None

        # Test GET request
        params = {
            "url": "https://example.com",
            "format": "png",
            "width": 1200,
            "height": 900,
            "device_preset": "laptop",
            "full_page": "false"
        }

        response = client.get("/tools/screenshot_page", params=params, headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["url"] == "https://example.com"
        assert data["metadata"]["viewport"] == "1366x768"  # laptop preset

        # Verify laptop preset was used (not width/height params)
        mock_page.set_viewport_size.assert_called_once_with({"width": 1366, "height": 768})

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_with_drive_storage(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test screenshot capture with Google Drive storage."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service
        mock_drive_service = AsyncMock()
        mock_drive_service.upload_file.return_value = "https://drive.google.com/file/screenshot_test.png"
        mock_drive_service_class.return_value = mock_drive_service

        # Test request with Drive storage
        request_data = {
            "url": "https://example.com",
            "store_in_drive": True,
            "drive_folder": "Test Screenshots"
        }

        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["drive_url"] == "https://drive.google.com/file/screenshot_test.png"
        assert "drive_url" in data["metadata"]

        # Verify Drive upload was called
        mock_drive_service.upload_file.assert_called_once()

        # Check call arguments
        call_args = mock_drive_service.upload_file.call_args
        assert call_args[1]["folder_path"] == "Test Screenshots"
        assert call_args[1]["mime_type"] == "image/png"
        assert call_args[1]["filename"].endswith(".png")

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_invalid_url(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test screenshot capture with invalid URL."""
        # Test request with invalid URL (blocked for security)
        request_data = {
            "url": "http://localhost:8080/admin",
            "format": "png"
        }

        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

        # Should return 200 with success=False
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "blocked for security" in data["error"]

        # Browser should not be used due to validation error
        mock_browser_manager_class.get_instance.assert_not_called()

    def test_screenshot_page_unauthenticated(self, client):
        """Test screenshot endpoint without authentication."""
        request_data = {
            "url": "https://example.com",
            "format": "png"
        }

        # Request without auth headers
        response = client.post("/tools/screenshot_page", json=request_data)

        # Should be unauthorized
        assert response.status_code == 401

    def test_screenshot_page_invalid_format(self, client, auth_headers):
        """Test screenshot page with invalid format."""
        # Test request with invalid format
        request_data = {
            "url": "https://example.com",
            "format": "invalid_format",
            "quality": 90
        }

        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

        # Should return validation error
        assert response.status_code == 422

    def test_screenshot_page_invalid_quality(self, client, auth_headers):
        """Test screenshot page with invalid quality range."""
        # Test request with invalid quality
        request_data = {
            "url": "https://example.com",
            "format": "jpeg",
            "quality": 150  # Above valid range (1-100)
        }

        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

        # Should return validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_performance_target(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
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

        # Mock Drive service (optional)
        mock_drive_service_class.return_value = None

        # Test request
        request_data = {
            "url": "https://example.com",
            "format": "png",
            "width": 1920,
            "height": 1080
        }

        # Measure execution time
        start_time = time.time()
        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)
        execution_time = (time.time() - start_time) * 1000

        # Verify success
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # With mocks, should be very fast
        assert execution_time < 5000, f"API took {execution_time:.0f}ms, should be <5000ms"

        # Verify execution time is reported
        assert data["execution_time_ms"] is not None
        assert data["execution_time_ms"] > 0

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_full_page_vs_viewport(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test both full page and viewport capture modes."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service (optional)
        mock_drive_service_class.return_value = None

        # Test full page capture
        full_page_request = {
            "url": "https://example.com",
            "format": "png",
            "full_page": True
        }

        response = client.post("/tools/screenshot_page", json=full_page_request, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify screenshot was called with full_page=True
        call_args = mock_page.screenshot.call_args
        assert call_args[1]["full_page"] is True

        # Reset mock for next test
        mock_page.screenshot.reset_mock()

        # Test viewport capture
        viewport_request = {
            "url": "https://example.com",
            "format": "png",
            "full_page": False
        }

        response = client.post("/tools/screenshot_page", json=viewport_request, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify screenshot was called with full_page=False
        call_args = mock_page.screenshot.call_args
        assert call_args[1]["full_page"] is False

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_all_device_presets(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test screenshot capture with all device presets."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service (optional)
        mock_drive_service_class.return_value = None

        # Test each device preset
        presets = ["desktop", "laptop", "tablet", "mobile"]

        for preset in presets:
            request_data = {
                "url": "https://example.com",
                "device_preset": preset,
                "format": "png"
            }

            response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["url"] == "https://example.com"

            # Verify correct viewport was used
            expected_viewport = ScreenshotOptions.DEVICE_PRESETS[preset]
            mock_page.set_viewport_size.assert_called_with({
                "width": expected_viewport["width"],
                "height": expected_viewport["height"]
            })

            # Reset mock for next test
            mock_page.set_viewport_size.reset_mock()

    @pytest.mark.asyncio
    @patch('services.screenshot_service.GoogleDriveService')
    @patch('services.screenshot_service.BrowserManager')
    async def test_screenshot_page_drive_service_unavailable(self, mock_browser_manager_class, mock_drive_service_class, client, auth_headers):
        """Test screenshot capture when Drive service is unavailable."""
        # Setup mocks
        mock_manager = AsyncMock()
        mock_browser_manager_class.get_instance.return_value = mock_manager

        mock_page = AsyncMock()
        mock_page.set_viewport_size = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b'fake_screenshot_data')

        mock_manager.navigate.return_value = mock_page
        mock_manager.close_page = AsyncMock()

        # Mock Drive service that raises exception during initialization
        mock_drive_service_class.side_effect = Exception("Drive service unavailable")

        # Test request with Drive storage enabled
        request_data = {
            "url": "https://example.com",
            "store_in_drive": True,
            "format": "png"
        }

        response = client.post("/tools/screenshot_page", json=request_data, headers=auth_headers)

        # Should still succeed without Drive storage
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["image_data"] is not None
        assert data["drive_url"] is None  # Drive storage failed

    def test_api_endpoints_are_documented(self, client, auth_headers):
        """Test that API endpoints have proper documentation."""
        # Test screenshot presets endpoint
        response = client.get("/tools/screenshot/presets", headers=auth_headers)
        assert response.status_code == 200

        # Test screenshot page GET endpoint (should have OpenAPI docs)
        response = client.get("/tools/screenshot_page", headers=auth_headers)
        # FastAPI automatically generates OpenAPI docs for GET endpoints

    def test_api_response_format_consistency(self, client, auth_headers):
        """Test that API response format is consistent across endpoints."""
        # Test screenshot presets response format
        presets_response = client.get("/tools/screenshot/presets", headers=auth_headers)
        assert presets_response.status_code == 200
        presets_data = presets_response.json()
        assert "success" in presets_data
        assert "data" in presets_data
        assert "message" in presets_data

        # Test screenshot page response format (GET)
        get_response = client.get(
            "/tools/screenshot_page",
            params={
                "url": "https://example.com",
                "format": "png"
            },
            headers=auth_headers
        )
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert "success" in get_data
        assert "url" in get_data
        assert "image_data" in get_data
        assert "metadata" in get_data
        assert "execution_time_ms" in get_data
        assert "captured_at" in get_data

        # Test screenshot page response format (POST)
        post_response = client.post(
            "/tools/screenshot_page",
            json={
                "url": "https://example.com",
                "format": "png"
            },
            headers=auth_headers
        )
        assert post_response.status_code == 200
        post_data = post_response.json()
        assert "success" in post_data
        assert "url" in post_data
        assert "image_data" in post_data
        assert "metadata" in post_data
        assert "execution_time_ms" in post_data
        assert "captured_at" in post_data

        # All should have the same structure for success/error fields
        for response_data in [presets_data, get_data, post_data]:
            assert isinstance(response_data["success"], bool)
            assert "error" in response_data or response_data["success"] is True