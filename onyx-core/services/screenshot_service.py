"""
Screenshot Service for Full-Page Page Capture

This module provides screenshot capture functionality for web pages using Playwright.
Supports multiple image formats (PNG, JPEG), configurable resolutions, and optional
Google Drive storage.

Key Features:
- Full-page screenshot capture (entire scrollHeight)
- PNG (lossless) and JPEG (smaller file size) formats
- Configurable resolution with mobile/tablet presets
- Base64 image encoding or Google Drive storage
- Performance optimization (<5s capture target)
- Comprehensive error handling and logging
- URL validation and security checks

Performance Targets:
- Screenshot capture: <5s (95th percentile)
- Image processing: <1s
- Storage upload: <2s (if Drive enabled)

Based on Story 7-5: Screenshot & Page Capture
"""

import io
import base64
import time
import logging
from datetime import datetime
from typing import Optional, Literal, Dict, Any, Union
from urllib.parse import urlparse
import re
import asyncio

from playwright.async_api import Page, Browser
from PIL import Image
# import pillow_avif  # Ensure AVIF support

from .browser_manager import BrowserManager
from .google_drive_sync import GoogleDriveService

# Configure logging
logger = logging.getLogger(__name__)


class ScreenshotOptions:
    """Configuration options for screenshot capture."""

    # Device presets for common viewport sizes
    DEVICE_PRESETS = {
        "desktop": {"width": 1920, "height": 1080},
        "laptop": {"width": 1366, "height": 768},
        "tablet": {"width": 768, "height": 1024},
        "mobile": {"width": 375, "height": 667},
        "mobile_large": {"width": 414, "height": 896}
    }

    def __init__(
        self,
        url: str,
        format: Literal["png", "jpeg"] = "png",
        quality: int = 85,
        width: Optional[int] = None,
        height: Optional[int] = None,
        device_preset: Optional[str] = None,
        full_page: bool = True,
        store_in_drive: bool = False,
        drive_folder: str = "Screenshots",
        timeout: int = 30000
    ):
        """
        Initialize screenshot options.

        Args:
            url: Target URL to capture
            format: Image format ('png' or 'jpeg')
            quality: Image quality for JPEG (1-100)
            width: Viewport width (pixels)
            height: Viewport height (pixels)
            device_preset: Device preset ('desktop', 'laptop', 'tablet', 'mobile')
            full_page: Capture full page or just viewport
            store_in_drive: Store screenshot in Google Drive
            drive_folder: Drive folder name for screenshots
            timeout: Screenshot timeout in milliseconds
        """
        self.url = url
        self.format = format.lower()
        self.quality = max(1, min(100, quality))  # Clamp between 1-100
        self.full_page = full_page
        self.store_in_drive = store_in_drive
        self.drive_folder = drive_folder
        self.timeout = timeout

        # Set viewport dimensions
        if device_preset:
            if device_preset not in self.DEVICE_PRESETS:
                raise ValueError(f"Invalid device preset. Must be one of: {list(self.DEVICE_PRESETS.keys())}")
            preset = self.DEVICE_PRESETS[device_preset]
            self.width = preset["width"]
            self.height = preset["height"]
        else:
            self.width = width or 1920
            self.height = height or 1080

        # Validate format
        if self.format not in ["png", "jpeg"]:
            raise ValueError("Format must be 'png' or 'jpeg'")


class ScreenshotResult:
    """Result of screenshot capture operation."""

    def __init__(
        self,
        success: bool,
        image_data: Optional[bytes] = None,
        base64_data: Optional[str] = None,
        drive_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time_ms: Optional[float] = None
    ):
        """
        Initialize screenshot result.

        Args:
            success: Whether capture was successful
            image_data: Raw image bytes
            base64_data: Base64-encoded image data
            drive_url: Google Drive URL (if stored)
            metadata: Capture metadata (dimensions, file size, etc.)
            error: Error message if capture failed
            execution_time_ms: Execution time in milliseconds
        """
        self.success = success
        self.image_data = image_data
        self.base64_data = base64_data
        self.drive_url = drive_url
        self.metadata = metadata or {}
        self.error = error
        self.execution_time_ms = execution_time_ms
        self.captured_at = datetime.utcnow().isoformat()


class ScreenshotService:
    """
    Service for capturing full-page screenshots of web pages.

    Provides high-performance screenshot capture with multiple format support,
    configurable resolutions, and optional Google Drive storage.
    """

    def __init__(self, drive_service: Optional[GoogleDriveService] = None):
        """
        Initialize screenshot service.

        Args:
            drive_service: Optional Google Drive service for file storage
        """
        self.drive_service = drive_service
        self.logger = logging.getLogger(__name__)

        # URL validation patterns (same as BrowserManager for consistency)
        self._url_blocklist = [
            r'^https?://localhost[:/]',
            r'^https?://127\.',
            r'^https?://10\.',
            r'^https?://172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^https?://192\.168\.',
            r'^https?://169\.254\.',
            r'^file://',
        ]

        self.logger.info("ScreenshotService initialized")

    def _validate_url(self, url: str) -> None:
        """
        Validate URL for security and format.

        Args:
            url: URL to validate

        Raises:
            ValueError: If URL is invalid or blocked
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")

            if parsed.scheme not in ['http', 'https']:
                raise ValueError("Invalid URL scheme. Only HTTP and HTTPS are allowed")

            # Check against security blocklist
            for pattern in self._url_blocklist:
                if re.match(pattern, url, re.IGNORECASE):
                    raise ValueError(f"URL blocked for security reasons: {url}")

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"URL validation failed: {str(e)}")

    def _convert_image_format(self, image_bytes: bytes, target_format: str, quality: int) -> bytes:
        """
        Convert image to target format and quality.

        Args:
            image_bytes: Input image bytes (PNG from Playwright)
            target_format: Target format ('png' or 'jpeg')
            quality: JPEG quality (1-100)

        Returns:
            Converted image bytes
        """
        try:
            # Load image with PIL
            image = Image.open(io.BytesIO(image_bytes))

            # Convert RGB for JPEG (no transparency support)
            if target_format == 'jpeg' and image.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparency
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # Convert to target format
            output = io.BytesIO()

            if target_format == 'png':
                image.save(output, format='PNG', optimize=True)
            else:  # jpeg
                image.save(output, format='JPEG', quality=quality, optimize=True)

            return output.getvalue()

        except Exception as e:
            self.logger.error(f"Image conversion failed: {str(e)}")
            # Return original image if conversion fails
            return image_bytes

    def _get_image_metadata(self, image_bytes: bytes, format: str) -> Dict[str, Any]:
        """
        Extract metadata from image bytes.

        Args:
            image_bytes: Image data
            format: Image format

        Returns:
            Dictionary with image metadata
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))

            return {
                "width": image.width,
                "height": image.height,
                "format": format.upper(),
                "file_size": len(image_bytes),
                "mode": image.mode,
                "has_transparency": image.mode in ('RGBA', 'LA') or 'transparency' in image.info
            }
        except Exception as e:
            self.logger.error(f"Failed to extract image metadata: {str(e)}")
            return {
                "format": format.upper(),
                "file_size": len(image_bytes),
                "error": "Metadata extraction failed"
            }

    async def capture_screenshot(self, options: ScreenshotOptions) -> ScreenshotResult:
        """
        Capture screenshot of web page with specified options.

        Args:
            options: Screenshot capture options

        Returns:
            ScreenshotResult with captured image or error details
        """
        start_time = time.time()

        try:
            # Validate URL
            self._validate_url(options.url)

            self.logger.info(f"Starting screenshot capture for: {options.url}")

            # Get browser manager
            browser_manager = await BrowserManager.get_instance()

            # Navigate to page
            self.logger.info(f"Navigating to: {options.url}")
            page = await browser_manager.navigate(
                options.url,
                wait_until='networkidle',
                timeout=options.timeout
            )

            try:
                # Set viewport size
                self.logger.info(f"Setting viewport to: {options.width}x{options.height}")
                await page.set_viewport_size({
                    "width": options.width,
                    "height": options.height
                })

                # Wait for page to load completely
                await page.wait_for_load_state('networkidle', timeout=options.timeout)

                # Capture screenshot
                self.logger.info(f"Capturing {'full page' if options.full_page else 'viewport'} screenshot")

                # Playwright returns PNG by default
                screenshot_bytes = await page.screenshot(
                    full_page=options.full_page,
                    type='png',  # Always capture as PNG first for quality
                    timeout=options.timeout
                )

                # Convert to target format if needed
                if options.format == 'jpeg':
                    self.logger.info(f"Converting to JPEG with quality: {options.quality}")
                    screenshot_bytes = self._convert_image_format(
                        screenshot_bytes, 'jpeg', options.quality
                    )

                # Get image metadata
                metadata = self._get_image_metadata(screenshot_bytes, options.format)
                metadata.update({
                    "url": options.url,
                    "full_page": options.full_page,
                    "viewport": f"{options.width}x{options.height}",
                    "capture_time": time.time()
                })

                # Convert to base64
                base64_data = base64.b64encode(screenshot_bytes).decode('utf-8')
                drive_url = None

                # Store in Google Drive if requested
                if options.store_in_drive and self.drive_service:
                    self.logger.info(f"Storing screenshot in Google Drive folder: {options.drive_folder}")
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"screenshot_{timestamp}.{options.format}"

                        drive_url = await self.drive_service.upload_file(
                            file_data=screenshot_bytes,
                            filename=filename,
                            folder_path=options.drive_folder,
                            mime_type=f'image/{options.format}'
                        )

                        metadata["drive_url"] = drive_url
                        self.logger.info(f"Screenshot stored in Drive: {drive_url}")

                    except Exception as drive_error:
                        self.logger.error(f"Failed to store in Google Drive: {str(drive_error)}")
                        # Don't fail the whole operation if Drive upload fails
                        metadata["drive_error"] = str(drive_error)

                execution_time = (time.time() - start_time) * 1000
                metadata["execution_time_ms"] = execution_time

                result = ScreenshotResult(
                    success=True,
                    image_data=screenshot_bytes,
                    base64_data=base64_data,
                    drive_url=drive_url,
                    metadata=metadata,
                    execution_time_ms=execution_time
                )

                self.logger.info(f"Screenshot captured successfully in {execution_time:.0f}ms")
                return result

            finally:
                # Always clean up the page
                await browser_manager.close_page(page)

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Screenshot capture failed: {str(e)}"
            self.logger.error(error_msg)

            return ScreenshotResult(
                success=False,
                error=error_msg,
                execution_time_ms=execution_time
            )

    async def capture_multiple_urls(
        self,
        urls: list[str],
        base_options: ScreenshotOptions,
        parallel: bool = False
    ) -> list[ScreenshotResult]:
        """
        Capture screenshots for multiple URLs.

        Args:
            urls: List of URLs to capture
            base_options: Base options for all captures
            parallel: Whether to process in parallel (experimental)

        Returns:
            List of ScreenshotResult objects
        """
        self.logger.info(f"Capturing {len(urls)} screenshots")

        if not parallel:
            # Sequential processing (safer)
            results = []
            for i, url in enumerate(urls):
                try:
                    options = ScreenshotOptions(url=url, **{
                        k: v for k, v in base_options.__dict__.items()
                        if k != 'url'
                    })
                    result = await self.capture_screenshot(options)
                    results.append(result)

                    self.logger.info(f"Completed {i+1}/{len(urls)} screenshots")

                except Exception as e:
                    error_msg = f"Failed to capture {url}: {str(e)}"
                    self.logger.error(error_msg)
                    results.append(ScreenshotResult(
                        success=False,
                        error=error_msg
                    ))

            return results
        else:
            # Parallel processing (experimental, may hit browser limits)
            tasks = []
            for url in urls:
                options = ScreenshotOptions(url=url, **{
                    k: v for k, v in base_options.__dict__.items()
                    if k != 'url'
                })
                tasks.append(self.capture_screenshot(options))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to result objects
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    final_results.append(ScreenshotResult(
                        success=False,
                        error=f"Parallel capture failed: {str(result)}"
                    ))
                else:
                    final_results.append(result)

            return final_results