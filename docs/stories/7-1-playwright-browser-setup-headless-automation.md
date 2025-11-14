# Story 7-1: Playwright Browser Setup - Headless Automation

**Story ID:** 7-1-playwright-browser-setup-headless-automation
**Epic:** Epic 7 - Web Automation & Search
**Status:** DRAFTED
**Priority:** P0 (Foundation - Blocking)
**Estimated Effort:** 8 Story Points
**Sprint:** Sprint 7
**Owner:** TBD
**Created:** 2025-11-13

---

## User Story

**As a** Manus Internal system
**I want** headless browser automation capabilities via Playwright in Docker
**So that** the agent can navigate websites, interact with pages, capture screenshots, and extract web content for autonomous research and intelligence gathering

---

## Context

This story implements the foundational browser automation layer for Epic 7 (Web Automation & Search). Playwright provides the headless Chrome/Firefox capabilities needed for all web-based operations including URL scraping, form filling, and screenshot capture. This is a blocking dependency for Stories 7-3, 7-4, and 7-5.

The browser automation runs in a dedicated Docker container with Playwright and headless browsers pre-installed, communicating with the main Onyx Core service via internal APIs. Performance is critical: browser startup must be <2s and page loads <5s to maintain acceptable user experience in Agent Mode.

### Why This Matters

Without reliable browser automation, Manus cannot:
- Render JavaScript-heavy websites (which is most modern web content)
- Extract clean article content from news sites and blogs
- Capture visual records of web pages for audit trails
- Fill forms for survey collection or lead generation
- Navigate multi-step web flows for complex research tasks

This foundational capability unlocks autonomous external intelligence gathering, transforming Manus from an internal knowledge system into a comprehensive strategic intelligence platform.

---

## Technical Context

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Onyx Core (Python) - Tool Orchestration               │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Browser Manager: manage_browser_lifecycle()      │ │
│  │                 → launch() → navigate() → close() │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ Internal API calls
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Playwright Container (Docker)                          │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Headless Chrome + Firefox                        │ │
│  │  Playwright Python API                            │ │
│  │  Browser Context Management                       │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Key Components

1. **Browser Manager** (`onyx-core/services/browser_manager.py`):
   - Singleton pattern for browser instance management
   - Launch browser with optimized headless settings
   - Navigate to URLs with configurable wait strategies
   - Close pages and cleanup resources properly
   - Monitor memory usage and implement auto-restart threshold

2. **Docker Configuration** (`docker-compose.yaml`):
   - Use official Microsoft Playwright Python image (v1.40.0)
   - Mount Onyx Core code for API access
   - Set environment variables for browser paths
   - Resource limits: 2GB RAM, 1.5 CPU cores
   - Health check: can launch browser and navigate to google.com

3. **Browser Settings**:
   - Headless mode: enabled (no GUI)
   - Browser engine: Chromium (primary), Firefox (fallback for testing)
   - Viewport: 1920x1080 default
   - User agent: Identify as Manus Bot with contact info
   - JavaScript: enabled (required for modern web)
   - Cookies: cleared after each session

### Performance Targets

| Operation | Target | Timeout | Notes |
|-----------|--------|---------|-------|
| Browser startup | <2s | 5s | First launch may be slower |
| Page navigation | <5s (95th %ile) | 10s | Varies by site |
| Page interaction | <1s | 3s | Click, fill, etc. |
| Browser cleanup | <500ms | 2s | Memory release |

### Resource Management

- **Max Concurrent Browsers**: 1 instance (serial execution)
- **Memory Limit**: 500MB per browser instance
- **CPU Limit**: 30% during page load, <10% idle
- **Auto-restart**: If memory >800MB, restart browser between operations
- **Zombie Process Detection**: Monitor for orphaned browser processes every 5 min

---

## Acceptance Criteria

### AC7.1.1: Playwright Browser Starts Without GUI in Docker Container
**Given** the Onyx Core system is running
**When** a tool requests browser automation
**Then** Playwright launches a headless Chrome browser without graphical interface
**And** the browser is accessible via Python API
**And** the browser process runs inside the Playwright Docker container

**Verification:**
- Unit test: `test_browser_launch_headless()` verifies no GUI process
- Integration test: Launch browser and verify `browser.is_connected()` returns True
- Docker logs show "Browser launched successfully" with no X11/GUI errors

---

### AC7.1.2: Browser Can Navigate to URLs and Interact With Pages (<3s Load Time)
**Given** a headless browser instance is running
**When** the system calls `navigate(url, wait_until="load")`
**Then** the browser navigates to the URL and waits for page load
**And** navigation completes in <3s for typical websites (95th percentile)
**And** the page content is accessible via `page.content()`
**And** the system can interact with page elements (click, type, select)

**Verification:**
- Integration test: Navigate to https://example.com and verify content
- Performance test: 100 navigations to various sites, measure p95 latency <3s
- Interaction test: Navigate to httpbin.org/forms/post, fill field, verify value

---

### AC7.1.3: Supports Screenshots and Data Extraction From Rendered Pages
**Given** a browser has navigated to a URL
**When** the system calls `screenshot(page, full_page=True)`
**Then** a full-page screenshot is captured as PNG bytes
**And** the screenshot includes content below the fold (entire scrollHeight)
**When** the system calls `extract_text(page)`
**Then** the visible text content is extracted and returned

**Verification:**
- Unit test: Navigate to test page, capture screenshot, verify file size >10KB
- Unit test: Extract text from https://example.com, verify "Example Domain" in output
- Visual test: Manually inspect screenshot to confirm full-page capture

---

### AC7.1.4: Performance - Page Load <3s, Interaction <1s for Typical Sites
**Given** the browser automation system is under normal load
**When** navigating to 100 different typical websites (news, blogs, corporate sites)
**Then** 95th percentile page load time is <3s
**When** performing interactions (click, fill_field, select_option)
**Then** each interaction completes in <1s

**Verification:**
- Load test: Automated script navigates to 100 URLs from test set
- Metrics logged: p50, p95, p99 latencies for navigation and interaction
- Performance dashboard: Real-time latency tracking in Grafana

---

### AC7.1.5: Max 1 Browser Instance Active (Serial Execution, No Parallel Browsers)
**Given** the Browser Manager is initialized
**When** multiple tools request browser automation concurrently
**Then** only 1 browser instance is active at any time
**And** subsequent requests are queued and processed serially
**And** the Browser Manager enforces single-instance constraint

**Verification:**
- Unit test: Attempt to launch 3 browsers concurrently, verify only 1 succeeds
- Integration test: Submit 5 concurrent web tasks, verify serial execution
- Monitoring: Resource usage shows only 1 browser process at any time

---

### AC7.1.6: Browser Cleanup - All Pages Closed After Operations Complete
**Given** a browser operation has completed (successful or failed)
**When** the operation finishes
**Then** all browser pages are closed via `page.close()`
**And** the browser context is closed via `context.close()`
**And** memory is released (verify with `psutil.Process.memory_info()`)
**And** no zombie browser processes remain

**Verification:**
- Unit test: After navigation, verify page and context are closed
- Integration test: Run 10 operations, check no memory leak (memory returns to baseline)
- Monitoring: Weekly check for zombie browser processes (alert if found)

---

## Implementation Details

### Step 1: Docker Configuration

**File:** `docker-compose.yaml`

```yaml
services:
  playwright:
    image: mcr.microsoft.com/playwright/python:v1.40.0-jammy
    container_name: onyx-playwright
    volumes:
      - ./onyx-core:/app
    working_dir: /app
    environment:
      - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
      - BROWSER_HEADLESS=true
      - BROWSER_TIMEOUT=10000
    command: python -m services.browser_manager
    restart: unless-stopped
    mem_limit: 2g
    cpus: 1.5
    healthcheck:
      test: ["CMD", "python", "-c", "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); p.chromium.launch(); p.stop()"]
      interval: 60s
      timeout: 10s
      retries: 3
    networks:
      - onyx-network
```

### Step 2: Browser Manager Service

**File:** `onyx-core/services/browser_manager.py`

```python
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Optional, Literal
import asyncio
import psutil
import logging

logger = logging.getLogger(__name__)

class BrowserManager:
    """Singleton browser manager for headless automation."""

    _instance: Optional['BrowserManager'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        self.max_memory_mb = 800  # Auto-restart threshold

    @classmethod
    async def get_instance(cls) -> 'BrowserManager':
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def launch(self) -> Browser:
        """Launch headless browser if not already running."""
        if self.browser and self.browser.is_connected():
            logger.info("Browser already running")
            return self.browser

        logger.info("Launching headless browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-first-run',
                '--no-zygote',
            ]
        )

        # Create persistent context with default settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Manus Internal Bot (+https://m3rcury.com/manus-bot)',
            java_script_enabled=True,
        )

        logger.info("Browser launched successfully")
        return self.browser

    async def navigate(
        self,
        url: str,
        wait_until: Literal["load", "domcontentloaded", "networkidle"] = "load"
    ) -> Page:
        """Navigate to URL and return page object."""
        if not self.browser:
            await self.launch()

        page = await self.context.new_page()
        logger.info(f"Navigating to {url}")

        try:
            await page.goto(url, wait_until=wait_until, timeout=10000)
            logger.info(f"Navigation complete: {url}")
            return page
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            await page.close()
            raise

    async def screenshot(self, page: Page, full_page: bool = True) -> bytes:
        """Capture screenshot of page."""
        logger.info(f"Capturing screenshot (full_page={full_page})")
        screenshot_bytes = await page.screenshot(full_page=full_page, type='png')
        logger.info(f"Screenshot captured: {len(screenshot_bytes)} bytes")
        return screenshot_bytes

    async def extract_text(self, page: Page) -> str:
        """Extract visible text content from page."""
        logger.info("Extracting text content")
        text_content = await page.inner_text('body')
        return text_content

    async def close_page(self, page: Page) -> None:
        """Close a page and release resources."""
        if page and not page.is_closed():
            await page.close()
            logger.info("Page closed")

    async def cleanup(self) -> None:
        """Close browser and release all resources."""
        logger.info("Starting browser cleanup")

        if self.context:
            await self.context.close()
            self.context = None

        if self.browser:
            await self.browser.close()
            self.browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None

        logger.info("Browser cleanup complete")

    async def check_memory(self) -> int:
        """Check current memory usage in MB."""
        if not self.browser:
            return 0

        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > self.max_memory_mb:
            logger.warning(f"Memory usage high: {memory_mb}MB. Restarting browser...")
            await self.cleanup()
            await self.launch()

        return int(memory_mb)
```

### Step 3: Integration Tests

**File:** `onyx-core/tests/integration/test_browser_manager.py`

```python
import pytest
from services.browser_manager import BrowserManager

@pytest.mark.asyncio
async def test_browser_launch_headless():
    """Verify browser launches in headless mode."""
    manager = await BrowserManager.get_instance()
    browser = await manager.launch()

    assert browser is not None
    assert browser.is_connected()

    # Verify headless by checking no X11 display
    import os
    assert os.environ.get('DISPLAY') is None

    await manager.cleanup()

@pytest.mark.asyncio
async def test_navigate_to_url():
    """Verify browser can navigate to URLs."""
    manager = await BrowserManager.get_instance()
    page = await manager.navigate('https://example.com')

    content = await page.content()
    assert 'Example Domain' in content

    await manager.close_page(page)
    await manager.cleanup()

@pytest.mark.asyncio
async def test_screenshot_capture():
    """Verify screenshot capture works."""
    manager = await BrowserManager.get_instance()
    page = await manager.navigate('https://example.com')

    screenshot_bytes = await manager.screenshot(page, full_page=True)

    assert len(screenshot_bytes) > 10000  # Should be >10KB
    assert screenshot_bytes[:8] == b'\x89PNG\r\n\x1a\n'  # PNG header

    await manager.close_page(page)
    await manager.cleanup()

@pytest.mark.asyncio
async def test_text_extraction():
    """Verify text extraction from pages."""
    manager = await BrowserManager.get_instance()
    page = await manager.navigate('https://example.com')

    text = await manager.extract_text(page)

    assert 'Example Domain' in text
    assert len(text) > 0

    await manager.close_page(page)
    await manager.cleanup()

@pytest.mark.asyncio
async def test_browser_cleanup():
    """Verify cleanup releases resources."""
    manager = await BrowserManager.get_instance()
    await manager.launch()

    initial_memory = await manager.check_memory()

    # Perform operations
    page = await manager.navigate('https://example.com')
    await manager.close_page(page)

    # Cleanup
    await manager.cleanup()

    # Verify browser is closed
    assert manager.browser is None
    assert manager.context is None

@pytest.mark.asyncio
async def test_single_instance_constraint():
    """Verify only one browser instance is active."""
    manager1 = await BrowserManager.get_instance()
    manager2 = await BrowserManager.get_instance()

    # Should be the same instance
    assert manager1 is manager2

    await manager1.cleanup()
```

---

## Dependencies

### Blocking Dependencies
- **Epic 1**: Docker environment and infrastructure setup
- **Environment**: Hostinger KVM 4 VPS with adequate resources

### External Dependencies
- **Playwright**: v1.40.0+ (Python library)
- **Playwright Browsers**: Chromium, Firefox (installed via Playwright)
- **Docker**: Official Microsoft Playwright Python image

### Package Dependencies

```python
# requirements.txt additions
playwright==1.40.0
psutil==5.9.0  # Memory monitoring
aiohttp==3.9.0  # Async HTTP for API integration
```

---

## Testing Strategy

### Unit Tests
- Browser launch and initialization
- Navigation to URLs with various wait strategies
- Screenshot capture in different formats
- Text extraction from various page structures
- Resource cleanup and memory release
- Error handling for timeouts and failed navigations

### Integration Tests
- End-to-end browser automation workflows
- Integration with Onyx Core tool system
- Docker container health checks
- Browser restart on memory threshold
- Concurrent request queuing (serial execution)

### Performance Tests
- Load test: 100 navigations to measure p95 latency
- Memory leak test: 50 operations, verify memory returns to baseline
- Browser startup time measurement
- Page interaction speed (click, type, select)

### Manual Verification
- Visual inspection of captured screenshots
- Verify headless operation (no GUI windows)
- Test against real websites (news, blogs, corporate sites)
- Verify user agent identification

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Memory leaks in Playwright** | High | Implement auto-restart at 800MB threshold; monitor memory usage |
| **Browser crashes on complex sites** | Medium | Retry logic with exponential backoff; fallback to text-only mode |
| **Slow page loads causing timeouts** | Medium | Set reasonable 10s timeout; return partial results on timeout |
| **Anti-bot detection blocks** | Medium | Use respectful user agent; rate limiting; defer complex sites |
| **Docker resource contention** | Low | Set mem_limit and cpus in docker-compose; monitor with Prometheus |

---

## Definition of Done

- [ ] Playwright Docker container deployed and running
- [ ] Browser Manager service implemented with all core methods
- [ ] All 6 acceptance criteria verified and passing
- [ ] Unit tests: >95% coverage of browser_manager.py
- [ ] Integration tests: All browser workflows passing
- [ ] Performance tests: p95 latency <3s for navigation, <1s for interaction
- [ ] Documentation: Browser Manager API documented in code
- [ ] Docker health check: Browser launch test passes every 60s
- [ ] Memory monitoring: Auto-restart at 800MB threshold working
- [ ] Code review: Approved by senior engineer
- [ ] Merged to main branch and deployed to staging

---

## Notes

### Browser Selection Rationale
- **Chromium** chosen as primary browser for best performance and compatibility
- **Firefox** available as fallback for testing edge cases
- **Headless mode** required for VPS deployment (no GUI)

### Performance Optimization
- Reuse browser context across operations (don't restart for each task)
- Implement page pooling if needed (future enhancement)
- Use `domcontentloaded` instead of `networkidle` when possible (faster)
- Disable images/CSS for text-only scraping (future enhancement)

### Security Considerations
- Browser runs in isolated Docker container
- No access to host filesystem beyond mounted volumes
- Cookies cleared after each session
- User agent identifies as Manus bot with contact info

---

## Related Stories

- **Story 7-2**: Web Search Tool (SerpAPI or Exa) - Independent
- **Story 7-3**: URL Scraping & Content Extraction - Depends on 7-1
- **Story 7-4**: Form Filling & Web Interaction - Depends on 7-1
- **Story 7-5**: Screenshot & Page Capture - Depends on 7-1

---

## References

- Epic 7 Technical Specification: `/home/user/ONYX/docs/epics/epic-7-tech-spec.md`
- PRD Section F6: Web Automation & Search
- Playwright Documentation: https://playwright.dev/python/docs/intro
- Docker Playwright Images: https://playwright.dev/python/docs/docker

---

**Story Created:** 2025-11-13
**Last Updated:** 2025-11-13
**Status:** DRAFTED - Ready for implementation
