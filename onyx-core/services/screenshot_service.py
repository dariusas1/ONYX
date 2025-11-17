"""
Screenshot Service for ONYX Core

Provides Playwright-backed page capture with configurable resolution,
formats, and audit metadata. Builds on BrowserManager to satisfy Epic 7
Story 7.5 acceptance criteria.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Literal, List

from services.browser_manager import BrowserManager

logger = logging.getLogger(__name__)


ImageFormat = Literal["png", "jpeg"]
WaitStrategy = Literal["load", "domcontentloaded", "networkidle"]


@dataclass
class ScreenshotOptions:
    """Normalized options for screenshot capture."""

    url: str
    full_page: bool = True
    width: int = 1920
    height: int = 1080
    image_format: ImageFormat = "png"
    quality: Optional[int] = None
    wait_until: WaitStrategy = "networkidle"


@dataclass
class ScreenshotResult:
    """Result object returned by ScreenshotService."""

    url: str
    format: ImageFormat
    width: int
    height: int
    base64_data: str
    execution_time_ms: int
    captured_at: datetime
    file_size_bytes: int
    storage_url: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "format": self.format,
            "width": self.width,
            "height": self.height,
            "image_base64": self.base64_data,
            "execution_time_ms": self.execution_time_ms,
            "captured_at": self.captured_at.isoformat(),
            "file_size_bytes": self.file_size_bytes,
            "storage_url": self.storage_url,
            "warnings": self.warnings,
        }


class ScreenshotService:
    """High-level orchestration for screenshot capture."""

    def __init__(self):
        self.max_dimension = int(os.getenv("SCREENSHOT_MAX_DIMENSION", "20000"))
        self.performance_budget_ms = int(os.getenv("SCREENSHOT_SLA_MS", "5000"))

    async def capture(self, options: ScreenshotOptions) -> ScreenshotResult:
        if options.width <= 0 or options.height <= 0:
            raise ValueError("width and height must be positive integers")
        if options.image_format not in ("png", "jpeg"):
            raise ValueError("image_format must be 'png' or 'jpeg'")
        if options.image_format == "jpeg" and options.quality is None:
            options.quality = 80

        start_time = asyncio.get_event_loop().time()
        browser_manager = await BrowserManager.get_instance()
        page = await browser_manager.navigate(options.url, wait_until=options.wait_until)
        warnings: List[str] = []

        try:
            await page.set_viewport_size({"width": options.width, "height": options.height})

            if options.full_page:
                scroll_height = await self._get_scroll_height(page)
                if scroll_height > self.max_dimension:
                    warnings.append(
                        f"Page height {scroll_height}px exceeds max {self.max_dimension}px; capture may be cropped"
                    )

            screenshot_bytes = await browser_manager.screenshot(
                page,
                full_page=options.full_page,
                image_type=options.image_format,
                quality=options.quality,
            )

            exec_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            if exec_time_ms > self.performance_budget_ms:
                warnings.append(
                    f"Screenshot capture exceeded target SLA ({exec_time_ms}ms > {self.performance_budget_ms}ms)"
                )

            encoded = base64.b64encode(screenshot_bytes).decode("utf-8")
            height = await self._resolve_height(page, options)

            return ScreenshotResult(
                url=options.url,
                format=options.image_format,
                width=options.width,
                height=height,
                base64_data=encoded,
                execution_time_ms=exec_time_ms,
                captured_at=datetime.now(timezone.utc),
                file_size_bytes=len(screenshot_bytes),
                storage_url=None,
                warnings=warnings,
            )
        finally:
            await browser_manager.close_page(page)

    async def _get_scroll_height(self, page) -> int:
        try:
            return await page.evaluate("() => document.documentElement.scrollHeight")
        except Exception:
            return 0

    async def _resolve_height(self, page, options: ScreenshotOptions) -> int:
        if not options.full_page:
            return options.height
        scroll_height = await self._get_scroll_height(page)
        return max(scroll_height, options.height) if scroll_height else options.height
