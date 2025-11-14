"""
Browser Manager Service for Headless Browser Automation

This module provides a singleton browser manager for headless browser automation
using Playwright. It manages browser lifecycle, navigation, screenshot capture,
and resource cleanup.

Key Features:
- Singleton pattern for single browser instance constraint
- Headless Chrome browser automation
- Page navigation with configurable wait strategies
- Screenshot capture (full-page PNG)
- Text content extraction
- Memory monitoring and auto-restart threshold
- Comprehensive error handling and logging

Performance Targets:
- Browser startup: <2s
- Page navigation: <3s (95th percentile)
- Page interaction: <1s
- Browser cleanup: <500ms

Resource Management:
- Max 1 browser instance active (serial execution)
- Memory limit: 500MB per browser instance
- Auto-restart at 800MB threshold
"""

from playwright.async_api import async_playwright, Browser, Page, BrowserContext, Playwright
from typing import Optional, Literal, List
import asyncio
import psutil
import logging
import os
import re
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BrowserManager:
    """
    Singleton browser manager for headless automation.

    Manages the lifecycle of a single Playwright browser instance, ensuring
    serial execution and proper resource cleanup. Implements memory monitoring
    with automatic restart when memory usage exceeds threshold.
    """

    _instance: Optional['BrowserManager'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize browser manager with default settings."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright: Optional[Playwright] = None
        self.max_memory_mb = 800  # Auto-restart threshold
        self._is_initialized = False

        # Serial execution lock for browser operations
        self._operation_lock = asyncio.Lock()

        # Browser process tracking for accurate memory monitoring
        self._browser_process: Optional[psutil.Process] = None

        # Zombie process monitoring
        self._zombie_monitor_task: Optional[asyncio.Task] = None
        self._zombie_monitor_interval = 300  # 5 minutes

        # URL blocklist for security (internal IPs, localhost, etc.)
        self._url_blocklist = [
            r'^https?://localhost[:/]',
            r'^https?://127\.',
            r'^https?://10\.',
            r'^https?://172\.(1[6-9]|2[0-9]|3[01])\.',
            r'^https?://192\.168\.',
            r'^https?://169\.254\.',
            r'^file://',
        ]

        # Get configuration from environment
        self.headless = os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true'
        self.timeout = int(os.getenv('BROWSER_TIMEOUT', '10000'))

        logger.info("BrowserManager instance created")

    @classmethod
    async def get_instance(cls) -> 'BrowserManager':
        """
        Get or create the singleton BrowserManager instance.

        Returns:
            BrowserManager: The singleton instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    logger.info("BrowserManager singleton instance initialized")
        return cls._instance

    def _validate_url(self, url: str) -> None:
        """
        Validate URL before navigation to prevent security issues.

        Args:
            url: The URL to validate

        Raises:
            ValueError: If URL is invalid or blocked
        """
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL format: {url}")

            # Only allow http and https
            if parsed.scheme not in ['http', 'https']:
                raise ValueError(f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed.")

        except Exception as e:
            raise ValueError(f"URL validation failed: {e}")

        # Check against blocklist (internal IPs, localhost, etc.)
        for pattern in self._url_blocklist:
            if re.match(pattern, url, re.IGNORECASE):
                raise ValueError(
                    f"URL blocked for security: {url} matches pattern {pattern}. "
                    "Navigation to internal/local addresses is not allowed."
                )

        logger.debug(f"URL validation passed: {url}")

    def _find_browser_processes(self) -> List[psutil.Process]:
        """
        Find all Chromium/browser processes spawned by this manager.

        Returns:
            List[psutil.Process]: List of browser processes
        """
        browser_processes = []
        try:
            current_process = psutil.Process()
            children = current_process.children(recursive=True)

            for child in children:
                try:
                    # Look for chromium/chrome processes
                    if any(name in child.name().lower() for name in ['chromium', 'chrome', 'firefox']):
                        browser_processes.append(child)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.warning(f"Error finding browser processes: {e}")

        return browser_processes

    async def _monitor_zombie_processes(self):
        """
        Background task to monitor and cleanup zombie browser processes.

        Runs every 5 minutes to detect orphaned browser processes that may
        have leaked outside the normal cleanup flow.
        """
        logger.info("Starting zombie process monitoring (5-minute interval)")

        try:
            while True:
                await asyncio.sleep(self._zombie_monitor_interval)

                # Check if browser is supposed to be running
                if not self.browser or not self.browser.is_connected():
                    # Browser is not running, check for zombie processes
                    zombie_processes = self._find_browser_processes()

                    if zombie_processes:
                        logger.warning(
                            f"Found {len(zombie_processes)} zombie browser process(es). "
                            "Cleaning up..."
                        )

                        for proc in zombie_processes:
                            try:
                                logger.info(f"Killing zombie process: {proc.name()} (PID: {proc.pid})")
                                proc.kill()
                                proc.wait(timeout=5)
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
                                logger.warning(f"Error killing zombie process {proc.pid}: {e}")
                    else:
                        logger.debug("No zombie processes found")

        except asyncio.CancelledError:
            logger.info("Zombie process monitoring stopped")
            raise
        except Exception as e:
            logger.error(f"Error in zombie process monitoring: {e}")

    async def launch(self) -> Browser:
        """
        Launch headless browser if not already running.

        Launches Chromium in headless mode with optimized settings for
        containerized deployment. Reuses existing browser if already connected.

        Returns:
            Browser: The launched browser instance

        Raises:
            Exception: If browser fails to launch
        """
        if self.browser and self.browser.is_connected():
            logger.info("Browser already running and connected")
            return self.browser

        logger.info("Launching headless browser...")

        try:
            # Start Playwright
            self.playwright = await async_playwright().start()

            # Launch Chromium browser with optimized settings
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-blink-features=AutomationControlled',
                ]
            )

            # Create persistent context with default settings
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Manus Internal Bot (+https://m3rcury.com/manus-bot)',
                java_script_enabled=True,
                ignore_https_errors=False,
            )

            # Track browser process for accurate memory monitoring
            # Wait a moment for browser process to start
            await asyncio.sleep(0.5)
            browser_processes = self._find_browser_processes()
            if browser_processes:
                # Track the main browser process (usually the first one)
                self._browser_process = browser_processes[0]
                logger.info(f"Tracking browser process PID: {self._browser_process.pid}")
            else:
                logger.warning("Could not find browser process for memory tracking")

            # Start zombie process monitoring
            if not self._zombie_monitor_task or self._zombie_monitor_task.done():
                self._zombie_monitor_task = asyncio.create_task(self._monitor_zombie_processes())
                logger.info("Zombie process monitoring task started")

            self._is_initialized = True
            logger.info("Browser launched successfully")
            return self.browser

        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            await self.cleanup()
            raise

    async def navigate(
        self,
        url: str,
        wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load",
        javascript_timeout: int = 5000
    ) -> Page:
        """
        Navigate to URL and return page object.

        Enforces serial execution to prevent concurrent page creation.
        Validates URL before navigation to prevent security issues.
        Enhanced for scraping workloads with JavaScript support.

        Args:
            url: The URL to navigate to
            wait_until: Wait strategy - 'load', 'domcontentloaded', or 'networkidle'
            javascript_timeout: Additional timeout for JavaScript rendering (ms)

        Returns:
            Page: The page object after navigation

        Raises:
            ValueError: If URL is invalid or blocked
            Exception: If navigation fails or times out
        """
        # Validate URL first (P2 fix)
        self._validate_url(url)

        # Enforce serial execution (P0 fix)
        async with self._operation_lock:
            if not self.browser or not self.browser.is_connected():
                await self.launch()

            # Check memory usage before creating new page
            await self.check_memory()

            page = await self.context.new_page()
            logger.info(f"Navigating to {url} (wait_until={wait_until})")

            try:
                # Set up page monitoring for scraping
                await page.add_init_script("""
                    // Add scraping detection monitoring
                    window.addEventListener('error', (e) => {
                        console.error('Page error:', e.error);
                    });

                    // Monitor resource loading
                    let resourceCount = 0;
                    const observer = new PerformanceObserver((list) => {
                        resourceCount += list.getEntries().length;
                    });
                    observer.observe({entryTypes: ['resource']});

                    window.scrapingMetrics = {
                        resourceCount: () => resourceCount,
                        startTime: Date.now()
                    };
                """)

                # Navigate with extended timeout for scraping
                scrape_timeout = max(self.timeout, javascript_timeout)
                await page.goto(url, wait_until=wait_until, timeout=scrape_timeout)

                # Additional wait for JavaScript-heavy sites
                if wait_until == "load":
                    await page.wait_for_load_state("networkidle", timeout=2000)

                logger.info(f"Navigation complete: {url}")
                return page

            except Exception as e:
                logger.error(f"Navigation failed for {url}: {e}")
                await page.close()
                raise

    async def screenshot(self, page: Page, full_page: bool = True) -> bytes:
        """
        Capture screenshot of page.

        Enforces serial execution to prevent concurrent screenshot operations.

        Args:
            page: The page to capture
            full_page: Whether to capture the full scrollable page

        Returns:
            bytes: PNG screenshot data
        """
        # Enforce serial execution for screenshot operations
        async with self._operation_lock:
            logger.info(f"Capturing screenshot (full_page={full_page})")

            try:
                screenshot_bytes = await page.screenshot(
                    full_page=full_page,
                    type='png'
                )
                logger.info(f"Screenshot captured: {len(screenshot_bytes)} bytes")
                return screenshot_bytes
            except Exception as e:
                logger.error(f"Screenshot capture failed: {e}")
                raise

    async def extract_text(self, page: Page) -> str:
        """
        Extract visible text content from page.

        Args:
            page: The page to extract text from

        Returns:
            str: The visible text content
        """
        logger.info("Extracting text content from page")

        try:
            text_content = await page.inner_text('body')
            logger.info(f"Text extracted: {len(text_content)} characters")
            return text_content
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise

    async def scrape_page(self, url: str, max_execution_time_ms: int = 5000) -> dict:
        """
        High-level scraping method optimized for content extraction.

        Provides complete scraping workflow with performance monitoring
        and timeout enforcement. Designed specifically for Story 7-3 requirements.

        Args:
            url: The URL to scrape
            max_execution_time_ms: Maximum allowed execution time in milliseconds

        Returns:
            Dictionary with page, content, and performance metrics

        Raises:
            ValueError: If URL is invalid or blocked
            Exception: If scraping fails or exceeds time limit
        """
        start_time = asyncio.get_event_loop().time()

        # Validate URL and calculate timeout
        self._validate_url(url)
        scrape_timeout = min(max(self.timeout, 5000), max_execution_time_ms)

        logger.info(f"Starting optimized scrape: {url} (timeout: {scrape_timeout}ms)")

        # Enforce serial execution
        async with self._operation_lock:
            if not self.browser or not self.browser.is_connected():
                await self.launch()

            # Check memory before operation
            memory_before = await self.check_memory()

            page = None
            try:
                # Create page with scraping optimizations
                page = await self.context.new_page()

                # Set up scraping optimizations
                await page.add_init_script("""
                    // Optimize for scraping
                    window.addEventListener('load', () => {
                        console.log('Page fully loaded for scraping');
                    });

                    // Prevent automatic redirects that might interfere
                    let originalOpen = window.open;
                    window.open = function(url, target, features) {
                        console.log('Blocked popup:', url);
                        return null;
                    };
                """)

                # Navigate with timeout enforcement
                navigation_start = asyncio.get_event_loop().time()
                await page.goto(url, wait_until="load", timeout=scrape_timeout)
                navigation_time = (asyncio.get_event_loop().time() - navigation_start) * 1000

                # Wait for dynamic content
                content_start = asyncio.get_event_loop().time()
                await page.wait_for_load_state("networkidle", timeout=2000)
                content_time = (asyncio.get_event_loop().time() - content_start) * 1000

                # Evaluate page content quality
                content_metrics = await page.evaluate("""
                    () => {
                        const body = document.body;
                        const text = body ? (body.innerText || body.textContent || '') : '';
                        const links = document.querySelectorAll('a').length;
                        const images = document.querySelectorAll('img').length;
                        const scripts = document.querySelectorAll('script').length;

                        return {
                            text_length: text.length,
                            word_count: text.split(/\\s+/).filter(w => w.length > 0).length,
                            link_count: links,
                            image_count: images,
                            script_count: scripts,
                            has_title: !!document.title,
                            title_length: document.title ? document.title.length : 0
                        };
                    }
                """)

                total_time = (asyncio.get_event_loop().time() - start_time) * 1000

                # Performance validation for AC7.3.5 (<5s requirement)
                if total_time > max_execution_time_ms:
                    logger.warning(f"Scraping exceeded {max_execution_time_ms}ms limit: {total_time:.2f}ms")

                memory_after = await self.check_memory()
                memory_delta = memory_after - memory_before

                metrics = {
                    "execution_time_ms": round(total_time, 2),
                    "navigation_time_ms": round(navigation_time, 2),
                    "content_time_ms": round(content_time, 2),
                    "memory_before_mb": memory_before,
                    "memory_after_mb": memory_after,
                    "memory_delta_mb": memory_delta,
                    "content_metrics": content_metrics,
                    "performance_ok": total_time <= max_execution_time_ms
                }

                logger.info(f"Scraping completed: {url} ({total_time:.2f}ms, {content_metrics['text_length']} chars)")

                return {
                    "page": page,
                    "metrics": metrics,
                    "success": True
                }

            except asyncio.TimeoutError:
                logger.error(f"Scraping timeout for {url} after {scrape_timeout}ms")
                if page:
                    await page.close()
                raise Exception(f"Scraping timeout: {url}")

            except Exception as e:
                logger.error(f"Scraping failed for {url}: {e}")
                if page:
                    await page.close()
                raise

    async def close_page(self, page: Page) -> None:
        """
        Close a page and release resources.

        Args:
            page: The page to close
        """
        if page and not page.is_closed():
            try:
                await page.close()
                logger.info("Page closed successfully")
            except Exception as e:
                logger.error(f"Error closing page: {e}")

    async def cleanup(self) -> None:
        """
        Close browser and release all resources.

        Performs complete cleanup of browser context, browser instance,
        and Playwright runtime. Also stops zombie process monitoring.
        Safe to call multiple times.
        """
        logger.info("Starting browser cleanup")

        try:
            # Stop zombie process monitoring task
            if self._zombie_monitor_task and not self._zombie_monitor_task.done():
                logger.info("Stopping zombie process monitoring task")
                self._zombie_monitor_task.cancel()
                try:
                    await self._zombie_monitor_task
                except asyncio.CancelledError:
                    pass
                self._zombie_monitor_task = None

            # Close all pages in context first
            if self.context:
                try:
                    pages = self.context.pages
                    for page in pages:
                        if not page.is_closed():
                            await page.close()
                except Exception as e:
                    logger.warning(f"Error closing pages: {e}")

            # Close context
            if self.context:
                try:
                    await self.context.close()
                    logger.info("Browser context closed")
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")
                finally:
                    self.context = None

            # Close browser
            if self.browser:
                try:
                    await self.browser.close()
                    logger.info("Browser closed")
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                finally:
                    self.browser = None

            # Stop playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                    logger.info("Playwright stopped")
                except Exception as e:
                    logger.warning(f"Error stopping Playwright: {e}")
                finally:
                    self.playwright = None

            # Clear browser process tracking
            self._browser_process = None

            self._is_initialized = False
            logger.info("Browser cleanup complete")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def check_memory(self) -> int:
        """
        Check current memory usage in MB.

        Monitors browser process memory usage (not Python process) and
        automatically triggers browser restart if memory exceeds threshold.

        Returns:
            int: Current memory usage in MB (browser process only)
        """
        if not self.browser or not self.browser.is_connected():
            return 0

        try:
            # P0 FIX: Track browser process memory, not Python process
            total_memory_mb = 0

            # If we have a tracked browser process, use it
            if self._browser_process:
                try:
                    if self._browser_process.is_running():
                        memory_mb = self._browser_process.memory_info().rss / 1024 / 1024
                        total_memory_mb += memory_mb
                    else:
                        # Process died, clear tracking
                        self._browser_process = None
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Process no longer exists, clear tracking
                    self._browser_process = None

            # Also check all browser child processes (comprehensive tracking)
            browser_processes = self._find_browser_processes()
            if browser_processes:
                for proc in browser_processes:
                    try:
                        memory_mb = proc.memory_info().rss / 1024 / 1024
                        total_memory_mb += memory_mb
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            logger.debug(f"Browser memory usage: {total_memory_mb:.2f}MB")

            # Check against threshold
            if total_memory_mb > self.max_memory_mb:
                logger.warning(
                    f"Browser memory usage high: {total_memory_mb:.2f}MB "
                    f"(threshold: {self.max_memory_mb}MB). Restarting browser..."
                )
                await self.cleanup()
                await self.launch()

            return int(total_memory_mb)

        except Exception as e:
            logger.error(f"Error checking memory: {e}")
            return 0

    async def is_healthy(self) -> bool:
        """
        Check if browser is healthy and connected.

        Returns:
            bool: True if browser is connected and operational
        """
        return (
            self._is_initialized and
            self.browser is not None and
            self.browser.is_connected() and
            self.context is not None
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


# Convenience function for simple use cases
async def create_browser_manager() -> BrowserManager:
    """
    Create and return a BrowserManager instance.

    Returns:
        BrowserManager: Initialized browser manager
    """
    manager = await BrowserManager.get_instance()
    await manager.launch()
    return manager
