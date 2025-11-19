"""
Unit tests for Form Interaction Service

Tests form field detection, filling logic, and error handling
without requiring actual browser automation.

Author: ONYX Core Team
Story: 7-4-form-filling-web-interaction
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.form_interaction_service import (
    FormInteractionService,
    FormField,
    FormFillRequest,
    FormFillResponse,
    FieldResult
)


class TestFormInteractionService:
    """Test suite for FormInteractionService"""

    @pytest.fixture
    def service(self):
        """Create form interaction service instance."""
        return FormInteractionService()

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = AsyncMock()
        page.url = "https://example.com/test"
        page.title = AsyncMock(return_value="Test Page")
        page.query_selector_all = AsyncMock(return_value=[])
        page.wait_for_selector = AsyncMock()
        return page

    @pytest.fixture
    def mock_element(self):
        """Create mock form element."""
        element = AsyncMock()
        element.get_attribute = AsyncMock()
        element.is_visible = AsyncMock(return_value=True)
        element.is_enabled = AsyncMock(return_value=True)
        element.is_checked = AsyncMock(return_value=False)
        element.inner_text = AsyncMock(return_value="Test Label")
        element.input_value = AsyncMock(return_value="")
        element.clear = AsyncMock()
        element.fill = AsyncMock()
        element.select_option = AsyncMock()
        element.click = AsyncMock()
        element.evaluate = AsyncMock()
        return element

    @pytest.fixture
    def sample_form_request(self):
        """Create sample form fill request."""
        return FormFillRequest(
            url="https://example.com/contact",
            form_data={
                "name": "John Doe",
                "email": "john@example.com",
                "message": "Hello World",
                "newsletter": True,
                "contact_method": "email"
            },
            submit_form=False,
            screenshot_before=True,
            screenshot_after=True
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert service.browser_manager is None

    @pytest.mark.asyncio
    async def test_detect_text_input_field(self, service, mock_element):
        """Test detection of text input fields."""
        # Setup mock element attributes
        mock_element.get_attribute.side_effect = lambda attr, default=None: {
            'name': 'full_name',
            'id': 'name-input',
            'type': 'text',
            'placeholder': 'Enter your name',
            'required': 'required',
            'value': ''
        }.get(attr)

        mock_element.evaluate.return_value = 'input'
        mock_element.query_selector_all.return_value = []
        mock_element.is_visible.return_value = True
        mock_element.is_enabled.return_value = True

        with patch.object(service, '_generate_selector', return_value='#name-input'):
            with patch.object(service, '_extract_field_label', return_value='Full Name'):
                field = await service._analyze_input_field(mock_element)

        assert field is not None
        assert field.name == 'full_name'
        assert field.field_type == 'input_text'
        assert field.selector == '#name-input'
        assert field.label == 'Full Name'
        assert field.placeholder == 'Enter your name'
        assert field.required == True
        assert field.visible == True
        assert field.enabled == True

    @pytest.mark.asyncio
    async def test_detect_select_field(self, service, mock_element):
        """Test detection of select dropdown fields."""
        # Setup mock for select element
        mock_element.get_attribute.side_effect = lambda attr, default=None: {
            'name': 'country',
            'id': 'country-select',
            'required': None
        }.get(attr)

        mock_element.input_value.return_value = 'us'
        mock_element.is_visible.return_value = True
        mock_element.is_enabled.return_value = True

        # Mock option elements
        mock_option = AsyncMock()
        mock_option.get_attribute.return_value = 'us'
        mock_option.inner_text.return_value = 'United States'

        mock_element.query_selector_all.return_value = [mock_option]

        with patch.object(service, '_generate_selector', return_value='#country-select'):
            with patch.object(service, '_extract_field_label', return_value='Country'):
                field = await service._analyze_select_field(mock_element)

        assert field is not None
        assert field.name == 'country'
        assert field.field_type == 'select'
        assert field.options == ['us']
        assert field.value == 'us'

    @pytest.mark.asyncio
    async def test_detect_checkbox_field(self, service, mock_element):
        """Test detection of checkbox fields."""
        mock_element.get_attribute.side_effect = lambda attr, default=None: {
            'name': 'agree_terms',
            'id': 'agree-checkbox',
            'required': 'required'
        }.get(attr)

        mock_element.is_checked.return_value = False
        mock_element.is_visible.return_value = True
        mock_element.is_enabled.return_value = True

        with patch.object(service, '_generate_selector', return_value='#agree-checkbox'):
            with patch.object(service, '_extract_field_label', return_value='Agree to Terms'):
                field = await service._analyze_checkbox_field(mock_element)

        assert field is not None
        assert field.name == 'agree_terms'
        assert field.field_type == 'checkbox'
        assert field.options == ['true', 'false']
        assert field.value == 'false'

    @pytest.mark.asyncio
    async def test_generate_selector_with_id(self, service, mock_element):
        """Test CSS selector generation for element with ID."""
        mock_element.get_attribute.return_value = 'test-input'
        selector = await service._generate_selector(mock_element)
        assert selector == '#test-input'

    @pytest.mark.asyncio
    async def test_generate_selector_with_name(self, service, mock_element):
        """Test CSS selector generation for element with name."""
        mock_element.get_attribute.side_effect = lambda attr: None if attr == 'id' else 'test-name'
        mock_element.evaluate.return_value = 'input'
        selector = await service._generate_selector(mock_element)
        assert selector == 'input[name="test-name"]'

    @pytest.mark.asyncio
    async def test_fill_text_field(self, service, mock_element):
        """Test filling a text field."""
        field = {
            'field_type': 'input_text',
            'selector': '#test-input'
        }

        await service._fill_field(mock_element, field, "Test Value")

        mock_element.clear.assert_called_once()
        mock_element.fill.assert_called_once_with("Test Value")

    @pytest.mark.asyncio
    async def test_fill_checkbox_field_true(self, service, mock_element):
        """Test filling a checkbox field with True value."""
        field = {
            'field_type': 'checkbox',
            'selector': '#test-checkbox'
        }

        mock_element.is_checked.return_value = False

        await service._fill_field(mock_element, field, True)

        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_checkbox_field_false(self, service, mock_element):
        """Test filling a checkbox field with False value."""
        field = {
            'field_type': 'checkbox',
            'selector': '#test-checkbox'
        }

        mock_element.is_checked.return_value = True

        await service._fill_field(mock_element, field, False)

        mock_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_fill_select_field_single(self, service, mock_element):
        """Test filling a select field with single value."""
        field = {
            'field_type': 'select',
            'selector': '#test-select'
        }

        await service._fill_field(mock_element, field, "option1")

        mock_element.select_option.assert_called_once_with(['option1'])

    @pytest.mark.asyncio
    async def test_fill_select_field_multiple(self, service, mock_element):
        """Test filling a select field with multiple values."""
        field = {
            'field_type': 'select',
            'selector': '#test-select'
        }

        await service._fill_field(mock_element, field, ["option1", "option2"])

        mock_element.select_option.assert_called_once_with(["option1", "option2"])

    @pytest.mark.asyncio
    async def test_fill_radio_field(self, service, mock_element):
        """Test filling a radio field."""
        mock_page = AsyncMock()
        mock_element.page = mock_page

        field = {
            'field_type': 'radio',
            'selector': 'input[type="radio"][name="gender"]'
        }

        radio_element = AsyncMock()
        radio_element.is_visible.return_value = True
        mock_page.locator.return_value = radio_element

        await service._fill_field(mock_element, field, "male")

        mock_page.locator.assert_called_once_with('input[type="radio"][name="gender"][value="male"]')
        radio_element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_field_by_name_exact_match(self, service):
        """Test finding field by exact name match."""
        fields = [
            {'name': 'email', 'selector': '#email'},
            {'name': 'name', 'selector': '#name'}
        ]

        field = await service._find_field_by_name(fields, 'email')
        assert field is not None
        assert field['name'] == 'email'

    @pytest.mark.asyncio
    async def test_find_field_by_name_case_insensitive(self, service):
        """Test finding field by case-insensitive name match."""
        fields = [
            {'name': 'EMAIL', 'selector': '#email'},
            {'name': 'name', 'selector': '#name'}
        ]

        field = await service._find_field_by_name(fields, 'email')
        assert field is not None
        assert field['name'] == 'EMAIL'

    @pytest.mark.asyncio
    async def test_find_field_by_name_partial_match(self, service):
        """Test finding field by partial name match."""
        fields = [
            {'name': 'user_email', 'selector': '#email'},
            {'name': 'name', 'selector': '#name'}
        ]

        field = await service._find_field_by_name(fields, 'email')
        assert field is not None
        assert field['name'] == 'user_email'

    @pytest.mark.asyncio
    async def test_find_field_by_label_match(self, service):
        """Test finding field by label match."""
        fields = [
            {'name': 'email_input', 'label': 'Email Address', 'selector': '#email'},
            {'name': 'name', 'selector': '#name'}
        ]

        field = await service._find_field_by_name(fields, 'Email Address')
        assert field is not None
        assert field['name'] == 'email_input'

    @pytest.mark.asyncio
    async def test_find_field_not_found(self, service):
        """Test field not found scenario."""
        fields = [
            {'name': 'email', 'selector': '#email'},
            {'name': 'name', 'selector': '#name'}
        ]

        field = await service._find_field_by_name(fields, 'phone')
        assert field is None

    @pytest.mark.asyncio
    async def test_fill_field_unsupported_type(self, service, mock_element):
        """Test error handling for unsupported field types."""
        field = {
            'field_type': 'unsupported_type',
            'selector': '#test-field'
        }

        with pytest.raises(Exception, match="Unsupported field type: unsupported_type"):
            await service._fill_field(mock_element, field, "value")

    @pytest.mark.asyncio
    async def test_detect_forms_empty_page(self, service, mock_page):
        """Test form detection on page with no forms."""
        mock_page.query_selector_all.return_value = []

        forms = await service.detect_forms(mock_page)

        assert forms == []
        mock_page.query_selector_all.assert_called_once_with('form')

    @pytest.mark.asyncio
    async def test_detect_forms_with_fields(self, service, mock_page):
        """Test form detection with fields."""
        # Mock form element
        mock_form = AsyncMock()
        mock_form.get_attribute.side_effect = lambda attr, default=None: {
            'action': '/submit',
            'method': 'POST',
            'id': 'contact-form',
            'class': 'form'
        }.get(attr)

        mock_page.query_selector_all.return_value = [mock_form]

        with patch.object(service, '_detect_form_fields', return_value=[
            FormField(name='email', field_type='input_text', selector='#email'),
            FormField(name='name', field_type='input_text', selector='#name')
        ]):
            forms = await service.detect_forms(mock_page)

        assert len(forms) == 1
        assert forms[0]['action'] == '/submit'
        assert forms[0]['method'] == 'POST'
        assert forms[0]['id'] == 'contact-form'
        assert forms[0]['field_count'] == 2
        assert len(forms[0]['fields']) == 2


class TestFormFillRequestValidation:
    """Test suite for form fill request validation."""

    def test_valid_request(self, sample_form_request):
        """Test validation of valid request."""
        assert sample_form_request.url == "https://example.com/contact"
        assert sample_form_request.form_data["name"] == "John Doe"
        assert sample_form_request.submit_form == False

    def test_invalid_url(self):
        """Test validation of invalid URL."""
        with pytest.raises(Exception):
            FormFillRequest(
                url="not-a-valid-url",
                form_data={"name": "test"}
            )

    def test_empty_form_data(self):
        """Test validation of empty form data."""
        with pytest.raises(Exception):
            FormFillRequest(
                url="https://example.com",
                form_data={}
            )

    def test_default_values(self):
        """Test default request values."""
        request = FormFillRequest(
            url="https://example.com",
            form_data={"name": "test"}
        )
        assert request.submit_form == False
        assert request.screenshot_before == True
        assert request.screenshot_after == True
        assert request.timeout == 5000


class TestFormFillResponse:
    """Test suite for form fill response."""

    def test_successful_response(self):
        """Test creation of successful response."""
        response = FormFillResponse(
            success=True,
            fields_filled=["name", "email"],
            fields_failed=[],
            execution_time=2.5,
            form_submitted=False,
            screenshots={"before": "base64image"},
            form_metadata={"forms_detected": 1}
        )

        assert response.success == True
        assert len(response.fields_filled) == 2
        assert len(response.fields_failed) == 0
        assert response.execution_time == 2.5

    def test_failed_field_result(self):
        """Test creation of failed field result."""
        field_result = FieldResult(
            field_name="email",
            success=False,
            error_message="Field not found"
        )

        assert field_result.field_name == "email"
        assert field_result.success == False
        assert "Field not found" in field_result.error_message


class TestIntegrationScenarios:
    """Integration test scenarios with complex mocking."""

    @pytest.mark.asyncio
    async def test_form_fill_complete_workflow(self, service, sample_form_request):
        """Test complete form fill workflow with mocked dependencies."""
        # Mock browser manager
        mock_browser_manager = AsyncMock()
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/contact"
        mock_page.title = AsyncMock(return_value="Contact Form")
        mock_page.wait_for_selector = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])

        # Mock form detection
        mock_form = AsyncMock()
        mock_form.get_attribute.side_effect = lambda attr, default=None: {
            'action': '/submit',
            'method': 'POST'
        }.get(attr)

        mock_page.query_selector_all.return_value = [mock_form]

        # Mock screenshot
        mock_browser_manager.screenshot.return_value = b'fake_screenshot_data'

        # Mock field detection
        detected_fields = [
            FormField(name='name', field_type='input_text', selector='#name'),
            FormField(name='email', field_type='input_email', selector='#email'),
            FormField(name='message', field_type='textarea', selector='#message')
        ]

        with patch.object(service, '_get_browser_manager', return_value=mock_browser_manager):
            with patch.object(service, 'detect_forms') as mock_detect:
                mock_detect.return_value = [{
                    'action': '/submit',
                    'method': 'POST',
                    'field_count': 3,
                    'fields': [field.dict() for field in detected_fields]
                }]

                with patch.object(service, '_find_field_by_name') as mock_find:
                    # Return fields for each lookup
                    mock_find.side_effect = detected_fields

                    with patch.object(service, '_fill_field') as mock_fill:
                        response = await service.fill_form(sample_form_request)

        # Verify response
        assert response.success == True
        assert len(response.fields_filled) == 3
        assert len(response.fields_failed) == 0
        assert 'before' in response.screenshots
        assert 'after' in response.screenshots
        assert response.form_metadata is not None
        assert response.execution_time > 0