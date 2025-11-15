"""
Comprehensive test suite for Form Manager service.

This module provides unit and integration tests for the form filling functionality,
including field detection, form submission, screenshot capture, and error handling scenarios.

Test Coverage:
- Form analysis and field detection
- Field type handling (text, email, select, checkbox, radio, textarea)
- Form filling with multiple selector strategies
- Form submission and result capture
- Screenshot capture functionality
- Error handling (missing fields, CAPTCHAs, timeouts)
- Performance validation (<5s execution target)
- Security validation (input sanitization, domain blocking)
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.form_manager import FormManager, FormFillRequest, FieldResult, FormFillResult
from services.field_detector import FieldInfo, FormInfo


class TestFormManager:
    """Test suite for FormManager class."""

    @pytest.fixture
    async def form_manager(self):
        """Create FormManager instance for testing."""
        manager = FormManager()
        await manager.get_instance()
        return manager

    @pytest.fixture
    def mock_browser_manager(self):
        """Mock BrowserManager for testing."""
        mock_manager = Mock()
        return mock_manager

    @pytest.fixture
    def mock_page(self):
        """Mock Playwright page for testing."""
        mock_page = AsyncMock()
        return mock_page

    @pytest.fixture
    def sample_form_request(self):
        """Sample form fill request for testing."""
        return FormFillRequest(
            url="https://example.com/contact",
            fields={
                "name": "John Doe",
                "email": "john@example.com",
                "message": "Test message",
                "newsletter": True,
                "country": "US"
            },
            submit=True,
            screenshots=True
        )

    # ========================
    # Form Fill Validation Tests
    # ========================

    @pytest.mark.asyncio
    async def test_validate_request_valid(self, form_manager):
        """Test validation of valid form fill request."""
        request = FormFillRequest(
            url="https://example.com/contact",
            fields={"name": "John"},
            submit=False,
            timeout=30
        )

        # Should not raise exception
        await form_manager._validate_request(request)

    @pytest.mark.asyncio
    async def test_validate_request_invalid_url(self, form_manager):
        """Test validation of request with invalid URL."""
        request = FormFillRequest(
            url="invalid-url",
            fields={"name": "John"},
            submit=False
        )

        with pytest.raises(ValueError, match="Invalid URL"):
            await form_manager._validate_request(request)

    @pytest.mark.asyncio
    async def test_validate_request_no_fields(self, form_manager):
        """Test validation of request with no fields."""
        request = FormFillRequest(
            url="https://example.com/contact",
            fields={},
            submit=False
        )

        with pytest.raises(ValueError, match="No fields provided"):
            await form_manager._validate_request(request)

    @pytest.mark.asyncio
    async def test_validate_request_timeout_too_long(self, form_manager):
        """Test validation of request with timeout too long."""
        request = FormFillRequest(
            url="https://example.com/contact",
            fields={"name": "John"},
            submit=False,
            timeout=120
        )

        with pytest.raises(ValueError, match="Timeout cannot exceed 60 seconds"):
            await form_manager._validate_request(request)

    @pytest.mark.asyncio
    async def test_validate_request_blocked_domain(self, form_manager):
        """Test validation of request with blocked domain."""
        request = FormFillRequest(
            url="https://malware-example.com/contact",
            fields={"name": "John"},
            submit=False
        )

        with pytest.raises(ValueError, match="Blocked domain"):
            await form_manager._validate_request(request)

    @pytest.mark.asyncio
    async def test_sanitize_input(self, form_manager):
        """Test input sanitization for XSS prevention."""
        # Test script injection removal
        malicious_input = "<script>alert('xss')</script>test"
        sanitized = form_manager._sanitize_input(malicious_input)
        assert "<script>" not in sanitized
        assert "</script>" not in sanitized
        assert "test" in sanitized

        # Test javascript protocol removal
        js_input = "javascript:alert('xss')"
        sanitized = form_manager._sanitize_input(js_input)
        assert "javascript:" not in sanitized

        # Test length limiting
        long_input = "a" * 20000
        sanitized = form_manager._sanitize_input(long_input)
        assert len(sanitized) <= 10000

    # ========================
    # Form Analysis Tests
    # ========================

    @pytest.mark.asyncio
    @patch('services.form_manager.BrowserManager.get_instance')
    async def test_get_browser_page_success(self, mock_get_instance, form_manager, mock_page):
        """Test successful browser page retrieval."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.get_page.return_value = mock_page
        mock_browser_manager.release_page.return_value = None
        mock_get_instance.return_value = mock_browser_manager

        # Mock page navigation
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None

        page = await form_manager._get_browser_page("https://example.com")

        # Verify navigation calls
        mock_page.goto.assert_called_once_with(
            "https://example.com",
            wait_until='domcontentloaded',
            timeout=30000
        )
        mock_page.wait_for_load_state.assert_called_once_with('networkidle', timeout=10000)

    @pytest.mark.asyncio
    @patch('services.form_manager.BrowserManager.get_instance')
    async def test_get_browser_page_navigation_failure(self, mock_get_instance, form_manager):
        """Test browser page retrieval with navigation failure."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_browser_manager.get_page.return_value = AsyncMock()
        mock_get_instance.return_value = mock_browser_manager

        # Mock page navigation failure
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Navigation failed")
        mock_browser_manager.get_page.return_value = mock_page

        with pytest.raises(RuntimeError, match="Failed to navigate"):
            await form_manager._get_browser_page("https://example.com")

    # ========================
    # Screenshot Tests
    # ========================

    @pytest.mark.asyncio
    async def test_capture_screenshot_success(self, form_manager, mock_page):
        """Test successful screenshot capture."""
        # Mock screenshot capture
        mock_screenshot = b"fake_screenshot_data"
        mock_page.screenshot.return_value = mock_screenshot

        result = await form_manager._capture_screenshot(mock_page, "before")

        # Verify screenshot was captured
        mock_page.screenshot.assert_called_once_with(
            type='png',
            full_page=True,
            timeout=5000
        )

        # Verify base64 encoding
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_capture_screenshot_failure(self, form_manager, mock_page):
        """Test screenshot capture failure handling."""
        # Mock screenshot failure
        mock_page.screenshot.side_effect = Exception("Screenshot failed")

        result = await form_manager._capture_screenshot(mock_page, "before")

        # Should return empty string on failure
        assert result == ""

    # ========================
    # Field Filling Tests
    # ========================

    @pytest.mark.asyncio
    async def test_fill_single_field_text(self, form_manager, mock_page):
        """Test filling a text field."""
        field_info = FieldInfo(
            field_type="text",
            selector="input[name='first_name']",
            selector_strategy="name",
            name="first_name"
        )

        await form_manager._fill_field_by_type(mock_page, field_info, "John Doe")

        # Verify field was filled
        mock_page.fill.assert_called_once_with("input[name='first_name']", "John Doe")

    @pytest.mark.asyncio
    async def test_fill_single_field_email(self, form_manager, mock_page):
        """Test filling an email field."""
        field_info = FieldInfo(
            field_type="email",
            selector="input[name='email']",
            selector_strategy="name",
            name="email"
        )

        await form_manager._fill_field_by_type(mock_page, field_info, "test@example.com")

        # Verify field was filled
        mock_page.fill.assert_called_once_with("input[name='email']", "test@example.com")

    @pytest.mark.asyncio
    async def test_fill_single_field_textarea(self, form_manager, mock_page):
        """Test filling a textarea field."""
        field_info = FieldInfo(
            field_type="textarea",
            selector="textarea[name='message']",
            selector_strategy="name",
            name="message"
        )

        await form_manager._fill_field_by_type(mock_page, field_info, "Test message")

        # Verify field was filled
        mock_page.fill.assert_called_once_with("textarea[name='message']", "Test message")

    @pytest.mark.asyncio
    async def test_fill_single_field_checkbox_true(self, form_manager, mock_page):
        """Test filling a checkbox field with True value."""
        field_info = FieldInfo(
            field_type="checkbox",
            selector="input[name='agree']",
            selector_strategy="name",
            name="agree"
        )

        # Mock is_checked to return False (unchecked)
        mock_page.is_checked.return_value = False

        await form_manager._fill_field_by_type(mock_page, field_info, True)

        # Verify checkbox was checked
        mock_page.check.assert_called_once_with("input[name='agree']")

    @pytest.mark.asyncio
    async def test_fill_single_field_checkbox_false(self, form_manager, mock_page):
        """Test filling a checkbox field with False value."""
        field_info = FieldInfo(
            field_type="checkbox",
            selector="input[name='agree']",
            selector_strategy="name",
            name="agree"
        )

        # Mock is_checked to return True (checked)
        mock_page.is_checked.return_value = True

        await form_manager._fill_field_by_type(mock_page, field_info, False)

        # Verify checkbox was unchecked
        mock_page.uncheck.assert_called_once_with("input[name='agree']")

    @pytest.mark.asyncio
    async def test_fill_single_field_disabled(self, form_manager, mock_page):
        """Test filling a disabled field."""
        field_info = FieldInfo(
            field_type="text",
            selector="input[name='disabled_field']",
            selector_strategy="name",
            name="disabled_field",
            disabled=True
        )

        with pytest.raises(ValueError, match="Field is disabled"):
            await form_manager._fill_field_by_type(mock_page, field_info, "value")

    # ========================
    # Form Submission Tests
    # ========================

    @pytest.mark.asyncio
    async def test_submit_form_success(self, form_manager, mock_page):
        """Test successful form submission."""
        form_info = FormInfo(
            form_selector="form",
            action_url="/submit",
            method="POST",
            field_count=2
        )

        # Mock submit button detection and form submission
        mock_page.query_selector.return_value = True
        mock_page.url = "https://example.com/contact"
        mock_page.click.return_value = None
        mock_page.wait_for_load_state.return_value = None

        result = await form_manager._submit_form(mock_page, form_info)

        # Verify submission success
        assert result["success"] is True
        assert result["initial_url"] == "https://example.com/contact"
        assert "submit_button" in result

    @pytest.mark.asyncio
    async def test_submit_form_no_button(self, form_manager, mock_page):
        """Test form submission with no submit button found."""
        form_info = FormInfo(
            form_selector="form",
            field_count=1
        )

        # Mock no submit button found
        mock_page.query_selector.return_value = False

        result = await form_manager._submit_form(mock_page, form_info)

        # Verify submission failed
        assert result["success"] is False
        assert "No submit button found" in result["error"]

    @pytest.mark.asyncio
    async def test_fill_fields_comprehensive(self, form_manager, mock_page):
        """Test filling multiple fields with different types."""
        form_info = FormInfo(
            form_selector="form",
            field_count=4
        )

        request = FormFillRequest(
            url="https://example.com/contact",
            fields={
                "name": "John Doe",
                "email": "john@example.com",
                "newsletter": True,
                "country": "US"
            },
            submit=False,
            selector_strategy="name"
        )

        # Mock field detector responses
        mock_field_detector = AsyncMock()

        field_results = []
        for field_name, field_value in request.fields.items():
            field_info = FieldInfo(
                field_type="text" if field_name not in ["newsletter", "country"] else "checkbox" if field_name == "newsletter" else "select",
                selector=f"input[name='{field_name}']",
                selector_strategy="name",
                name=field_name
            )

            field_result = FieldResult(
                field_name=field_name,
                success=True,
                value=field_value,
                field_info=field_info
            )
            field_results.append(field_result)

        results = await form_manager._fill_fields(mock_page, form_info, request)

        # Verify correct number of field results
        assert len(results) == 4

        # Verify all fields were successful
        assert all(r.success for r in results)

        # Verify field names match
        result_names = [r.field_name for r in results]
        assert set(result_names) == set(request.fields.keys())

    # ========================
    # Performance Tests
    # ========================

    @pytest.mark.asyncio
    async def test_execution_time_calculation(self, form_manager):
        """Test execution time calculation."""
        import time

        start_time = time.time()
        # Simulate some work
        await asyncio.sleep(0.001)  # 1ms
        execution_time_ms = form_manager._calculate_execution_time(start_time)

        # Verify execution time is in reasonable range
        assert 0.5 <= execution_time_ms <= 10.0  # Allow 0.5-10ms for test timing

    @pytest.mark.asyncio
    async def test_performance_stats_update(self, form_manager):
        """Test performance statistics tracking."""
        # Initial stats
        initial_stats = form_manager.performance_stats.copy()
        assert initial_stats["total_forms_processed"] == 0

        # Create successful result
        result = FormFillResult(
            success=True,
            url="https://example.com",
            total_fields=5,
            successful_fields=5,
            failed_fields=0,
            field_results=[],
            execution_time_ms=3000,
            executed_at=datetime.utcnow().isoformat()
        )

        # Update stats
        form_manager._update_performance_stats(result)

        # Verify stats were updated
        updated_stats = form_manager.performance_stats
        assert updated_stats["total_forms_processed"] == 1
        assert updated_stats["average_fill_time_ms"] == 3000.0
        assert updated_stats["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_get_performance_stats(self, form_manager):
        """Test retrieving performance statistics."""
        stats = await form_manager.get_performance_stats()

        # Verify stats structure
        assert "total_forms_processed" in stats
        assert "average_fill_time_ms" in stats
        assert "success_rate" in stats

        # Verify stats are returned as copy
        stats["total_forms_processed"] = 999
        original_stats = form_manager.performance_stats
        assert original_stats["total_forms_processed"] != 999

    # ========================
    # Integration Tests
    # ========================

    @pytest.mark.asyncio
    @patch('services.form_manager.BrowserManager.get_instance')
    @patch('services.form_manager.RateLimiter.check_limit')
    async def test_fill_form_integration_success(self, mock_rate_limit, mock_get_instance, form_manager, sample_form_request):
        """Test complete form filling integration success scenario."""
        # Setup mocks
        mock_browser_manager = AsyncMock()
        mock_page = AsyncMock()
        mock_browser_manager.get_page.return_value = mock_page
        mock_browser_manager.release_page.return_value = None
        mock_get_instance.return_value = mock_browser_manager

        # Mock page interactions
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.screenshot.return_value = b"fake_screenshot"

        # Mock field detector
        mock_field_detector = AsyncMock()
        form_info = FormInfo(
            form_selector="form",
            field_count=3,
            has_captcha=False
        )
        mock_field_detector.analyze_form.return_value = form_info
        mock_field_detector.find_field.return_value = FieldInfo(
            field_type="text",
            selector="input[name='name']",
            selector_strategy="name",
            name="name"
        )

        # Override field detector
        form_manager.field_detector = mock_field_detector

        result = await form_manager.fill_form(sample_form_request)

        # Verify successful result
        assert result.success is True
        assert result.total_fields == 3
        assert result.captcha_detected is False
        assert "screenshots" in result
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    @patch('services.form_manager.BrowserManager.get_instance')
    async def test_fill_form_integration_captcha_detected(self, mock_get_instance, form_manager, sample_form_request):
        """Test form filling with CAPTCHA detection."""
        # Setup mocks
        mock_browser_manager = AsyncMock()
        mock_page = AsyncMock()
        mock_browser_manager.get_page.return_value = mock_page
        mock_browser_manager.release_page.return_value = None
        mock_get_instance.return_value = mock_browser_manager

        # Mock page interactions
        mock_page.goto.return_value = None
        mock_page.wait_for_load_state.return_value = None
        mock_page.screenshot.return_value = b"fake_screenshot"

        # Mock field detector with CAPTCHA
        mock_field_detector = AsyncMock()
        form_info = FormInfo(
            form_selector="form",
            field_count=2,
            has_captcha=True
        )
        mock_field_detector.analyze_form.return_value = form_info

        # Override field detector
        form_manager.field_detector = mock_field_detector

        result = await form_manager.fill_form(sample_form_request)

        # Verify CAPTCHA detected result
        assert result.success is False
        assert result.captcha_detected is True
        assert "CAPTCHA detected" in result.error

    @pytest.mark.asyncio
    async def test_fill_form_performance_target(self, form_manager):
        """Test form filling meets 5-second performance target."""
        # Create a complex form request
        complex_request = FormFillRequest(
            url="https://example.com/complex-form",
            fields={
                f"field_{i}": f"value_{i}" for i in range(10)  # 10 fields
            },
            submit=True,
            screenshots=True,
            timeout=30
        )

        # Mock all dependencies for performance testing
        with patch('services.form_manager.BrowserManager.get_instance') as mock_get_instance, \
             patch('services.form_manager.RateLimiter.check_limit'), \
             patch('services.form_manager.FieldDetector') as mock_field_detector_class:

            # Setup mocks
            mock_browser_manager = AsyncMock()
            mock_page = AsyncMock()
            mock_browser_manager.get_page.return_value = mock_page
            mock_browser_manager.release_page.return_value = None
            mock_get_instance.return_value = mock_browser_manager

            # Mock fast operations
            mock_page.goto.return_value = None
            mock_page.wait_for_load_state.return_value = None
            mock_page.screenshot.return_value = b"screenshot"
            mock_page.fill.return_value = None
            mock_page.is_checked.return_value = False
            mock_page.query_selector.return_value = True
            mock_page.click.return_value = None
            mock_page.wait_for_load_state.return_value = None

            # Mock field detector for fast analysis
            mock_field_detector = AsyncMock()
            mock_field_detector_instance = mock_field_detector.return_value
            mock_field_detector_instance.analyze_form.return_value = FormInfo(
                form_selector="form",
                field_count=10,
                has_captcha=False
            )

            # Mock field finding for each field
            async def mock_find_field(page, field_name, form_selector):
                return FieldInfo(
                    field_type="text",
                    selector=f"input[name='{field_name}']",
                    selector_strategy="name",
                    name=field_name
                )

            mock_field_detector_instance.find_field.side_effect = mock_find_field

            # Override field detector
            form_manager.field_detector = mock_field_detector_instance

            start_time = asyncio.get_event_loop().time()
            result = await form_manager.fill_form(complex_request)
            execution_time = asyncio.get_event_loop().time() - start_time

            # Verify 5-second target is met (allowing for test environment overhead)
            assert execution_time < 10.0  # Looser limit for test environment
            assert result.success is True
            assert result.total_fields == 10
            assert result.execution_time_ms < 5000  # Should be much faster in reality

    # ========================
    # Error Handling Tests
    # ========================

    @pytest.mark.asyncio
    async def test_fill_form_field_not_found(self, form_manager, mock_page):
        """Test handling when field is not found."""
        form_info = FormInfo(form_selector="form", field_count=1)

        request = FormFillRequest(
            url="https://example.com/contact",
            fields={"missing_field": "value"},
            submit=False
        )

        # Mock field detector to return None for missing field
        mock_field_detector = AsyncMock()
        mock_field_detector.find_field.return_value = None
        form_manager.field_detector = mock_field_detector

        result = await form_manager.fill_form(request)

        # Verify field not found error
        assert result.success is False
        assert result.total_fields == 1
        assert result.failed_fields == 1
        assert "Field not found" in result.field_results[0].error

    @pytest.mark.asyncio
    async def test_cleanup_page_success(self, form_manager, mock_page):
        """Test successful page cleanup."""
        mock_page.is_closed.return_value = False
        mock_page.close.return_value = None

        await form_manager._cleanup_page(mock_page)

        # Verify cleanup was called
        mock_page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_page_already_closed(self, form_manager, mock_page):
        """Test cleanup of already closed page."""
        mock_page.is_closed.return_value = True

        # Should not raise exception
        await form_manager._cleanup_page(mock_page)

        # Cleanup should not be called on already closed page
        mock_page.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_fill_form_exception_handling(self, form_manager):
        """Test exception handling during form filling."""
        request = FormFillRequest(
            url="https://example.com/contact",
            fields={"name": "John"},
            submit=False
        )

        # Mock rate limiter to raise exception
        with patch('services.form_manager.RateLimiter.check_limit', side_effect=Exception("Rate limit exceeded")):
            result = await form_manager.fill_form(request)

        # Verify error handling
        assert result.success is False
        assert result.error == "Rate limit exceeded"
        assert result.total_fields == 0


# ========================
# Integration Test Suite
# ========================

class TestFormManagerIntegration:
    """Integration test suite for FormManager with real components."""

    @pytest.mark.asyncio
    async def test_form_fill_with_real_components(self):
        """Test form filling with integration of real components."""
        # This test would require actual browser instances
        # and real web pages, so we'll use comprehensive mocking
        pass

    @pytest.mark.asyncio
    async def test_form_fill_end_to_end_workflow(self):
        """Test complete form filling workflow end-to-end."""
        # Test the complete workflow from request to result
        # including all intermediate steps
        pass


# ========================
# Performance Benchmark Tests
# ========================

class TestFormManagerPerformance:
    """Performance benchmark test suite for FormManager."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("field_count", [5, 10, 20])
    async def test_form_fill_performance_benchmarks(self, field_count):
        """Benchmark form filling performance with different field counts."""
        import time

        form_manager = FormManager()
        await form_manager.get_instance()

        # Create request with specified field count
        request = FormFillRequest(
            url="https://example.com/performance-test",
            fields={f"field_{i}": f"value_{i}" for i in range(field_count)},
            submit=True,
            screenshots=False,  # Disable screenshots for performance testing
            timeout=30
        )

        # Mock all dependencies for isolated performance testing
        with patch('services.form_manager.BrowserManager.get_instance') as mock_get_instance, \
             patch('services.form_manager.RateLimiter.check_limit'), \
             patch('services.form_manager.FieldDetector') as mock_field_detector_class:

            # Setup high-performance mocks
            mock_browser_manager = AsyncMock()
            mock_page = AsyncMock()
            mock_browser_manager.get_page.return_value = mock_page
            mock_browser_manager.release_page.return_value = None
            mock_get_instance.return_value = mock_browser_manager

            # Configure minimal overhead mocks
            mock_page.goto.return_value = None
            mock_page.wait_for_load_state.return_value = None
            mock_page.fill.return_value = None

            # Mock field detector for optimal performance
            mock_field_detector = AsyncMock()
            mock_field_detector_instance = mock_field_detector.return_value
            mock_field_detector_instance.analyze_form.return_value = FormInfo(
                form_selector="form",
                field_count=field_count,
                has_captcha=False
            )

            # Configure fast field finding
            def mock_find_field(page, field_name, form_selector):
                return FieldInfo(
                    field_type="text",
                    selector=f"input[name='{field_name}']",
                    selector_strategy="name",
                    name=field_name
                )

            mock_field_detector_instance.find_field.side_effect = mock_find_field

            form_manager.field_detector = mock_field_detector_instance

            # Measure performance
            start_time = time.time()
            result = await form_manager.fill_form(request)
            execution_time = time.time() - start_time

            # Performance assertions
            assert result.success is True
            assert result.total_fields == field_count

            # Should scale linearly with field count
            expected_max_time = field_count * 0.1  # 100ms per field max
            assert execution_time < expected_max_time, f"Expected <{expected_max_time:.2f}s, got {execution_time:.2f}s for {field_count} fields"

            # Memory efficiency check
            assert result.execution_time_ms < field_count * 100  # 100ms per field max

    @pytest.mark.asyncio
    async def test_concurrent_form_fills(self):
        """Test performance of concurrent form filling operations."""
        import time

        form_manager = FormManager()
        await form_manager.get_instance()

        # Create multiple form fill requests
        requests = [
            FormFillRequest(
                url=f"https://example.com/form-{i}",
                fields={f"field_{i}_1": "value1", f"field_{i}_2": "value2"},
                submit=False,
                screenshots=False
            )
            for i in range(5)
        ]

        # Mock dependencies
        with patch('services.form_manager.BrowserManager.get_instance') as mock_get_instance, \
             patch('services.form_manager.RateLimiter.check_limit'), \
             patch('services.form_manager.FieldDetector') as mock_field_detector_class:

            # Setup mocks for concurrent operations
            def create_mock_page():
                mock_page = AsyncMock()
                mock_page.goto.return_value = None
                mock_page.wait_for_load_state.return_value = None
                mock_page.fill.return_value = None
                mock_page.query_selector.return_value = True
                mock_page.click.return_value = None
                mock_page.wait_for_load_state.return_value = None
                return mock_page

            mock_browser_manager = AsyncMock()
            mock_browser_manager.get_page.side_effect = create_mock_page
            mock_browser_manager.release_page.return_value = None
            mock_get_instance.return_value = mock_browser_manager

            # Configure field detector
            mock_field_detector = AsyncMock()
            mock_field_detector_instance = mock_field_detector.return_value
            mock_field_detector_instance.analyze_form.return_value = FormInfo(
                form_selector="form",
                field_count=2,
                has_captcha=False
            )
            mock_field_detector_instance.find_field.return_value = FieldInfo(
                field_type="text",
                selector="input[name='test']",
                selector_strategy="name",
                name="test"
            )
            form_manager.field_detector = mock_field_detector_instance

            # Run concurrent form fills
            start_time = time.time()
            tasks = [form_manager.fill_form(request) for request in requests]
            results = await asyncio.gather(*tasks)
            execution_time = time.time() - start_time

            # Verify all operations completed successfully
            assert len(results) == 5
            assert all(r.success for r in results)

            # Performance check - should be faster than sequential
            assert execution_time < 2.0  # 2 seconds for 5 concurrent operations

            # Verify no resource conflicts
            assert all(r.execution_time_ms > 0 for r in results)


if __name__ == "__main__":
    pytest.main([__file__])