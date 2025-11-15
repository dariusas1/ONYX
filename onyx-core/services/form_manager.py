"""
Form Manager Service for Web Form Automation

This module provides comprehensive form filling and interaction capabilities for web automation.
It integrates with the existing FieldDetector and BrowserManager services to deliver reliable
form automation with intelligent field detection and error handling.

Key Features:
- Intelligent form field detection using multiple selector strategies
- Support for all common input types (text, email, select, checkbox, radio, textarea)
- Form validation and error handling
- Screenshot capture for audit trails
- Performance optimization with <5s execution target
- CAPTCHA detection and security compliance

Performance Targets:
- Form fill time: <5s for typical forms (5-10 fields)
- Screenshot capture: <1s for before/after images
- Field detection: <500ms for form analysis
- Browser navigation: <3s page load time

Security Features:
- Input sanitization for safe form filling
- CAPTCHA detection and manual intervention requests
- URL validation against known malicious domains
- Audit trail with screenshot documentation
"""

import asyncio
import base64
import io
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

# Import FieldDetector and BrowserManager first
try:
    from .field_detector import FieldDetector, FieldInfo, FormInfo
    from .browser_manager import BrowserManager
except ImportError:
    # Fallback for direct import when running from tests
    from services.field_detector import FieldDetector, FieldInfo, FormInfo
    from services.browser_manager import BrowserManager

# Import RateLimiter with fallback
try:
    from .rate_limiter import RateLimiter
except (ImportError, ModuleNotFoundError):
    # Simple fallback RateLimiter when redis is not available
    class RateLimiter:
        async def check_limit(self, key: str, limit: int, window: int):
            """Simple rate limiter that always allows requests (for testing)"""
            pass

logger = logging.getLogger(__name__)


@dataclass
class FormFillRequest:
    """Request model for form filling operations."""

    url: str
    fields: Dict[str, Any]  # Field name -> value mapping
    submit: bool = False  # Whether to submit the form after filling
    selector_strategy: str = "label"  # Default strategy for field matching
    timeout: int = 30  # Timeout in seconds
    screenshots: bool = True  # Capture before/after screenshots


@dataclass
class FieldResult:
    """Result for a single field operation."""

    field_name: str
    success: bool
    value: Any
    error: Optional[str] = None
    field_info: Optional[FieldInfo] = None
    execution_time_ms: Optional[float] = None


@dataclass
class FormFillResult:
    """Result for a complete form filling operation."""

    success: bool
    url: str
    total_fields: int
    successful_fields: int
    failed_fields: int
    field_results: List[FieldResult]
    execution_time_ms: float
    executed_at: str
    screenshots: Dict[str, str] = None  # Base64 encoded images
    submit_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    captcha_detected: bool = False


class FormManager:
    """
    Comprehensive form manager for web form automation.

    Provides intelligent form filling with error handling, screenshot capture,
    and performance optimization. Integrates with existing browser automation
    infrastructure.
    """

    def __init__(self):
        """Initialize form manager with dependencies."""
        self.field_detector = FieldDetector()
        self.browser_manager = None
        self.rate_limiter = RateLimiter()

        # Form security patterns
        self.blocked_domains = [
            'malware-example.com',
            'phishing-site.com',
            # Add more blocked domains as needed
        ]

        # Performance tracking
        self.performance_stats = {
            'total_forms_processed': 0,
            'average_fill_time_ms': 0.0,
            'success_rate': 0.0
        }

        logger.info("FormManager initialized")

    async def get_instance(self) -> 'FormManager':
        """Get or create FormManager singleton."""
        if self.browser_manager is None:
            self.browser_manager = await BrowserManager.get_instance()
        return self

    async def fill_form(self, request: FormFillRequest) -> FormFillResult:
        """
        Fill a web form with provided field values.

        Args:
            request: Form fill request with URL and field data

        Returns:
            FormFillResult: Comprehensive result with field-level details
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Validate request
            await self._validate_request(request)

            logger.info(f"Starting form fill for URL: {request.url}")

            # Rate limiting check
            await self.rate_limiter.check_limit("form_fill", limit=20, window=3600)

            # Get browser page
            page = await self._get_browser_page(request.url)

            # Take "before" screenshot
            screenshots = {}
            if request.screenshots:
                screenshots['before'] = await self._capture_screenshot(page, 'before')

            # Analyze form
            form_info = await self.field_detector.analyze_form(page)

            # Check for CAPTCHA
            if form_info.has_captcha:
                logger.warning(f"CAPTCHA detected on {request.url}")
                return FormFillResult(
                    success=False,
                    url=request.url,
                    total_fields=0,
                    successful_fields=0,
                    failed_fields=0,
                    field_results=[],
                    screenshots=screenshots,
                    execution_time_ms=self._calculate_execution_time(start_time),
                    captcha_detected=True,
                    executed_at=datetime.utcnow().isoformat(),
                    error="CAPTCHA detected - manual intervention required"
                )

            # Fill form fields
            field_results = await self._fill_fields(page, form_info, request)

            # Take "after" screenshot
            if request.screenshots:
                screenshots['after'] = await self._capture_screenshot(page, 'after')

            # Submit form if requested
            submit_result = None
            if request.submit and all(r.success for r in field_results):
                submit_result = await self._submit_form(page, form_info)

            # Calculate results
            successful_fields = sum(1 for r in field_results if r.success)
            failed_fields = len(field_results) - successful_fields
            execution_time_ms = self._calculate_execution_time(start_time)

            result = FormFillResult(
                success=failed_fields == 0,
                url=request.url,
                total_fields=len(field_results),
                successful_fields=successful_fields,
                failed_fields=failed_fields,
                field_results=field_results,
                screenshots=screenshots,
                submit_result=submit_result,
                execution_time_ms=execution_time_ms,
                captcha_detected=False,
                executed_at=datetime.utcnow().isoformat()
            )

            # Update performance stats
            self._update_performance_stats(result)

            logger.info(f"Form fill complete: {successful_fields}/{len(field_results)} fields "
                       f"in {execution_time_ms:.0f}ms")

            return result

        except Exception as e:
            logger.error(f"Form fill failed for {request.url}: {e}")
            return FormFillResult(
                success=False,
                url=request.url,
                total_fields=0,
                successful_fields=0,
                failed_fields=0,
                field_results=[],
                execution_time_ms=self._calculate_execution_time(start_time),
                error=str(e),
                executed_at=datetime.utcnow().isoformat()
            )
        finally:
            # Cleanup browser resources
            if 'page' in locals():
                await self._cleanup_page(page)

    async def _validate_request(self, request: FormFillRequest) -> None:
        """Validate form fill request for security and constraints."""
        # URL validation
        parsed_url = urlparse(request.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {request.url}")

        # Check against blocked domains
        domain = parsed_url.netloc.lower()
        if any(blocked in domain for blocked in self.blocked_domains):
            raise ValueError(f"Blocked domain: {domain}")

        # Field validation
        if not request.fields:
            raise ValueError("No fields provided for form filling")

        # Timeout validation
        if request.timeout > 60:
            raise ValueError("Timeout cannot exceed 60 seconds")

        # Sanitize field values
        for field_name, value in request.fields.items():
            if isinstance(value, str):
                # Basic XSS prevention
                request.fields[field_name] = self._sanitize_input(value)

    def _sanitize_input(self, value: str) -> str:
        """Sanitize input value for safe form filling."""
        # Remove potential script injections
        value = value.replace('<script', '').replace('</script>', '')
        value = value.replace('javascript:', '')
        value = value.replace('vbscript:', '')
        # Limit length to prevent buffer overflow
        return value[:10000]

    async def _get_browser_page(self, url: str):
        """Get browser page and navigate to URL."""
        browser_manager = await BrowserManager.get_instance()
        page = await browser_manager.get_page()

        try:
            # Navigate to URL
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Wait for page to be ready
            await page.wait_for_load_state('networkidle', timeout=10000)

            return page

        except Exception as e:
            await browser_manager.release_page(page)
            raise RuntimeError(f"Failed to navigate to {url}: {e}") from e

    async def _capture_screenshot(self, page, step: str) -> str:
        """Capture screenshot and return as base64 encoded string."""
        try:
            screenshot = await page.screenshot(
                type='png',
                full_page=True,
                timeout=5000
            )

            # Convert to base64
            buffer = io.BytesIO(screenshot)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()

            logger.debug(f"Screenshot captured for step: {step}")
            return image_base64

        except Exception as e:
            logger.warning(f"Failed to capture screenshot for step {step}: {e}")
            return ""

    async def _fill_fields(self, page, form_info: FormInfo, request: FormFillRequest) -> List[FieldResult]:
        """Fill all form fields with provided values."""
        field_results = []

        for field_name, field_value in request.fields.items():
            field_result = await self._fill_single_field(page, field_name, field_value, form_info, request)
            field_results.append(field_result)

        return field_results

    async def _fill_single_field(self, page, field_name: str, field_value: Any,
                                form_info: FormInfo, request: FormFillRequest) -> FieldResult:
        """Fill a single form field."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Find field using field detector
            field_info = await self.field_detector.find_field(
                page, field_name, form_info.form_selector
            )

            if not field_info:
                return FieldResult(
                    field_name=field_name,
                    success=False,
                    value=field_value,
                    error=f"Field not found: {field_name}",
                    execution_time_ms=self._calculate_execution_time(start_time)
                )

            # Fill field based on type
            await self._fill_field_by_type(page, field_info, field_value)

            return FieldResult(
                field_name=field_name,
                success=True,
                value=field_value,
                field_info=field_info,
                execution_time_ms=self._calculate_execution_time(start_time)
            )

        except Exception as e:
            return FieldResult(
                field_name=field_name,
                success=False,
                value=field_value,
                error=str(e),
                execution_time_ms=self._calculate_execution_time(start_time)
            )

    async def _fill_field_by_type(self, page, field_info: FieldInfo, value: Any) -> None:
        """Fill field based on its type."""
        if field_info.disabled:
            raise ValueError(f"Field is disabled: {field_info.name}")

        if field_info.field_type in ['text', 'email', 'password']:
            await page.fill(field_info.selector, str(value))

        elif field_info.field_type == 'textarea':
            await page.fill(field_info.selector, str(value))

        elif field_info.field_type == 'select':
            if field_info.options:
                # Handle select with options
                option_value = str(value).lower()
                for option in field_info.options:
                    if option.get('text', '').lower() == option_value or \
                       option.get('value', '').lower() == option_value:
                        await page.select_option(field_info.selector, option['value'])
                        return
            # Fallback to value-based selection
            await page.select_option(field_info.selector, str(value))

        elif field_info.field_type == 'checkbox':
            should_check = bool(value)
            if should_check != await page.is_checked(field_info.selector):
                if should_check:
                    await page.check(field_info.selector)
                else:
                    await page.uncheck(field_info.selector)

        elif field_info.field_type == 'radio':
            # For radio buttons, we need to click the correct option
            radio_value = str(value)
            await page.click(field_info.selector)

        else:
            # Default fill for unknown types
            await page.fill(field_info.selector, str(value))

    async def _submit_form(self, page, form_info: FormInfo) -> Dict[str, Any]:
        """Submit the form and capture the result."""
        try:
            # Look for submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                f'{form_info.form_selector} button[type="submit"]',
                f'{form_info.form_selector} input[type="submit"]',
                f'{form_info.form_selector} button:not([type])',
                'button:contains("Submit")',
                'button:contains("Send")',
                'button:contains("Save")',
                'button:contains("Continue")'
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    if await page.query_selector(selector):
                        submit_button = selector
                        break
                except:
                    continue

            if not submit_button:
                return {
                    'success': False,
                    'error': 'No submit button found'
                }

            # Capture current URL for comparison
            initial_url = page.url

            # Click submit button
            await page.click(submit_button)

            # Wait for navigation or response
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)

                # Check if navigation occurred
                final_url = page.url
                navigated = final_url != initial_url

                return {
                    'success': True,
                    'initial_url': initial_url,
                    'final_url': final_url,
                    'navigated': navigated,
                    'submit_button': submit_button
                }

            except Exception as e:
                # Check if page still loaded
                current_url = page.url
                return {
                    'success': True,
                    'initial_url': initial_url,
                    'final_url': current_url,
                    'navigated': False,
                    'submit_button': submit_button,
                    'note': 'Form submitted but no navigation detected'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Form submission failed: {str(e)}'
            }

    async def _cleanup_page(self, page) -> None:
        """Clean up browser page resources."""
        try:
            if page and not page.is_closed():
                await page.close()
        except Exception as e:
            logger.warning(f"Error cleaning up page: {e}")

    def _calculate_execution_time(self, start_time: float) -> float:
        """Calculate execution time in milliseconds."""
        return (asyncio.get_event_loop().time() - start_time) * 1000

    def _update_performance_stats(self, result: FormFillResult) -> None:
        """Update performance statistics."""
        self.performance_stats['total_forms_processed'] += 1

        # Update average fill time
        total = self.performance_stats['total_forms_processed']
        current_avg = self.performance_stats['average_fill_time_ms']
        self.performance_stats['average_fill_time_ms'] = (
            (current_avg * (total - 1) + result.execution_time_ms) / total
        )

        # Update success rate
        if result.success:
            current_success_rate = self.performance_stats['success_rate']
            self.performance_stats['success_rate'] = (
                (current_success_rate * (total - 1) + 1.0) / total
            )

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        return self.performance_stats.copy()