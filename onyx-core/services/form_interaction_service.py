"""
Form Interaction Service for ONYX Core

Intelligent form detection, field analysis, and automated form filling
using Playwright browser automation. Supports multiple field types with
comprehensive error handling and audit trails.

Author: ONYX Core Team
Story: 7-4-form-filling-web-interaction
"""

from typing import Dict, List, Optional, Union, Any, Literal
from playwright.async_api import Page, Locator, Browser
from pydantic import BaseModel, Field
import asyncio
import time
import logging
import base64
import hashlib
from datetime import datetime
from urllib.parse import urljoin, urlparse

from .browser_manager import BrowserManager

logger = logging.getLogger(__name__)


class FormField(BaseModel):
    """Represents a detected form field with metadata."""
    name: str = Field(..., description="Field name/id")
    field_type: str = Field(..., description="Field type (input, select, checkbox, radio, textarea)")
    selector: str = Field(..., description="CSS selector for the field")
    label: Optional[str] = Field(None, description="Human-readable label")
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    required: bool = Field(False, description="Whether field is required")
    options: Optional[List[str]] = Field(None, description="Available options for select/radio")
    value: Optional[str] = Field(None, description="Current value")
    visible: bool = Field(True, description="Whether field is visible")
    enabled: bool = Field(True, description="Whether field is enabled")


class FormFillRequest(BaseModel):
    """Request model for form filling operations."""
    url: str = Field(..., description="Target URL containing the form")
    form_data: Dict[str, Union[str, bool, int, List[str]]] = Field(..., description="Form field values")
    submit_form: bool = Field(False, description="Whether to submit the form after filling")
    wait_for_selector: Optional[str] = Field(None, description="CSS selector to wait for before filling")
    screenshot_before: bool = Field(True, description="Capture screenshot before filling")
    screenshot_after: bool = Field(True, description="Capture screenshot after filling")
    timeout: int = Field(5000, description="Operation timeout in milliseconds")


class FieldResult(BaseModel):
    """Result for individual field filling operation."""
    field_name: str = Field(..., description="Field name")
    success: bool = Field(..., description="Whether field was filled successfully")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    value_filled: Optional[str] = Field(None, description="Value that was filled")


class FormFillResponse(BaseModel):
    """Response model for form filling operations."""
    success: bool = Field(..., description="Form filling operation success status")
    fields_filled: List[str] = Field(..., description="List of successfully filled field names")
    fields_failed: List[FieldResult] = Field(..., description="Failed fields with error messages")
    execution_time: float = Field(..., description="Total execution time in seconds")
    form_submitted: bool = Field(..., description="Whether form was submitted")
    submission_result: Optional[Dict[str, Any]] = Field(None, description="Form submission response")
    screenshots: Dict[str, str] = Field(..., description="Screenshot file paths (base64)")
    form_metadata: Optional[Dict[str, Any]] = Field(None, description="Detected form metadata")


class FormInteractionService:
    """
    Intelligent form detection and filling service.

    Provides automated form interaction with comprehensive field type support,
    screenshot audit trails, and robust error handling.
    """

    def __init__(self):
        """Initialize form interaction service."""
        self.browser_manager: Optional[BrowserManager] = None
        logger.info("FormInteractionService initialized")

    async def _get_browser_manager(self) -> BrowserManager:
        """Get or initialize browser manager."""
        if not self.browser_manager:
            self.browser_manager = await BrowserManager.get_instance()
        return self.browser_manager

    async def detect_forms(self, page: Page) -> List[Dict[str, Any]]:
        """
        Detect all forms on the current page.

        Args:
            page: Playwright page object

        Returns:
            List of form metadata dictionaries
        """
        logger.info("Detecting forms on page")

        forms = []
        try:
            # Find all form elements
            form_elements = await page.query_selector_all('form')

            for i, form in enumerate(form_elements):
                form_info = {
                    'index': i,
                    'action': await form.get_attribute('action'),
                    'method': await form.get_attribute('method') or 'GET',
                    'id': await form.get_attribute('id'),
                    'class': await form.get_attribute('class'),
                    'field_count': 0,
                    'fields': []
                }

                # Detect fields within this form
                fields = await self._detect_form_fields(form)
                form_info['fields'] = [field.dict() for field in fields]
                form_info['field_count'] = len(fields)

                forms.append(form_info)

            logger.info(f"Detected {len(forms)} form(s) on page")
            return forms

        except Exception as e:
            logger.error(f"Error detecting forms: {e}")
            return []

    async def _detect_form_fields(self, form_element: Locator) -> List[FormField]:
        """
        Detect all form fields within a form element.

        Args:
            form_element: Playwright locator for the form

        Returns:
            List of FormField objects
        """
        fields = []

        try:
            # Text inputs and various types
            input_selectors = [
                'input[type="text"]',
                'input[type="email"]',
                'input[type="password"]',
                'input[type="number"]',
                'input[type="tel"]',
                'input[type="url"]',
                'input[type="search"]',
                'input[type="date"]',
                'input[type="datetime-local"]',
                'input[type="time"]',
                'input:not([type])',  # inputs without type attribute
            ]

            for selector in input_selectors:
                elements = await form_element.query_selector_all(selector)
                for element in elements:
                    field = await self._analyze_input_field(element)
                    if field:
                        fields.append(field)

            # Textareas
            textareas = await form_element.query_selector_all('textarea')
            for textarea in textareas:
                field = await self._analyze_textarea_field(textarea)
                if field:
                    fields.append(field)

            # Select dropdowns
            selects = await form_element.query_selector_all('select')
            for select in selects:
                field = await self._analyze_select_field(select)
                if field:
                    fields.append(field)

            # Checkboxes
            checkboxes = await form_element.query_selector_all('input[type="checkbox"]')
            for checkbox in checkboxes:
                field = await self._analyze_checkbox_field(checkbox)
                if field:
                    fields.append(field)

            # Radio buttons (grouped by name)
            radio_groups = {}
            radios = await form_element.query_selector_all('input[type="radio"]')
            for radio in radios:
                name = await radio.get_attribute('name') or 'unnamed'
                if name not in radio_groups:
                    radio_groups[name] = []
                radio_groups[name].append(radio)

            for name, radio_elements in radio_groups.items():
                field = await self._analyze_radio_group(radio_elements, name)
                if field:
                    fields.append(field)

        except Exception as e:
            logger.error(f"Error detecting form fields: {e}")

        return fields

    async def _analyze_input_field(self, element: Locator) -> Optional[FormField]:
        """Analyze an input field and extract metadata."""
        try:
            name = await element.get_attribute('name') or await element.get_attribute('id') or ''
            field_type = await element.get_attribute('type') or 'text'

            # Generate unique selector
            selector = await self._generate_selector(element)

            # Extract other attributes
            label = await self._extract_field_label(element)
            placeholder = await element.get_attribute('placeholder')
            required = await element.get_attribute('required') is not None
            visible = await element.is_visible()
            enabled = await element.is_enabled()
            value = await element.get_attribute('value')

            return FormField(
                name=name,
                field_type=f"input_{field_type}",
                selector=selector,
                label=label,
                placeholder=placeholder,
                required=required,
                options=None,
                value=value,
                visible=visible,
                enabled=enabled
            )
        except Exception as e:
            logger.warning(f"Error analyzing input field: {e}")
            return None

    async def _analyze_textarea_field(self, element: Locator) -> Optional[FormField]:
        """Analyze a textarea field and extract metadata."""
        try:
            name = await element.get_attribute('name') or await element.get_attribute('id') or ''
            selector = await self._generate_selector(element)
            label = await self._extract_field_label(element)
            placeholder = await element.get_attribute('placeholder')
            required = await element.get_attribute('required') is not None
            visible = await element.is_visible()
            enabled = await element.is_enabled()
            value = await element.input_value()

            return FormField(
                name=name,
                field_type="textarea",
                selector=selector,
                label=label,
                placeholder=placeholder,
                required=required,
                options=None,
                value=value,
                visible=visible,
                enabled=enabled
            )
        except Exception as e:
            logger.warning(f"Error analyzing textarea field: {e}")
            return None

    async def _analyze_select_field(self, element: Locator) -> Optional[FormField]:
        """Analyze a select dropdown field and extract metadata."""
        try:
            name = await element.get_attribute('name') or await element.get_attribute('id') or ''
            selector = await self._generate_selector(element)
            label = await self._extract_field_label(element)
            required = await element.get_attribute('required') is not None
            visible = await element.is_visible()
            enabled = await element.is_enabled()

            # Extract options
            options = []
            option_elements = await element.query_selector_all('option')
            for opt in option_elements:
                option_value = await opt.get_attribute('value')
                option_text = await opt.inner_text()
                if option_value:
                    options.append(option_value)

            # Get selected value
            selected_value = await element.input_value()

            return FormField(
                name=name,
                field_type="select",
                selector=selector,
                label=label,
                placeholder=None,
                required=required,
                options=options,
                value=selected_value,
                visible=visible,
                enabled=enabled
            )
        except Exception as e:
            logger.warning(f"Error analyzing select field: {e}")
            return None

    async def _analyze_checkbox_field(self, element: Locator) -> Optional[FormField]:
        """Analyze a checkbox field and extract metadata."""
        try:
            name = await element.get_attribute('name') or await element.get_attribute('id') or ''
            selector = await self._generate_selector(element)
            label = await self._extract_field_label(element)
            required = await element.get_attribute('required') is not None
            visible = await element.is_visible()
            enabled = await element.is_enabled()
            checked = await element.is_checked()

            return FormField(
                name=name,
                field_type="checkbox",
                selector=selector,
                label=label,
                placeholder=None,
                required=required,
                options=["true", "false"],
                value=str(checked).lower(),
                visible=visible,
                enabled=enabled
            )
        except Exception as e:
            logger.warning(f"Error analyzing checkbox field: {e}")
            return None

    async def _analyze_radio_group(self, radio_elements: List[Locator], group_name: str) -> Optional[FormField]:
        """Analyze a radio button group and extract metadata."""
        try:
            if not radio_elements:
                return None

            # Use the first radio element for base attributes
            first_radio = radio_elements[0]
            selector = f'input[type="radio"][name="{group_name}"]'
            label = await self._extract_field_label(first_radio)

            # Check if any radio in the group is required
            required = False
            visible = False
            enabled = False
            selected_value = None
            options = []

            for radio in radio_elements:
                if await radio.get_attribute('required') is not None:
                    required = True
                if await radio.is_visible():
                    visible = True
                if await radio.is_enabled():
                    enabled = True

                value = await radio.get_attribute('value')
                if value:
                    options.append(value)
                if await radio.is_checked():
                    selected_value = value

            return FormField(
                name=group_name,
                field_type="radio",
                selector=selector,
                label=label,
                placeholder=None,
                required=required,
                options=options,
                value=selected_value,
                visible=visible,
                enabled=enabled
            )
        except Exception as e:
            logger.warning(f"Error analyzing radio group: {e}")
            return None

    async def _generate_selector(self, element: Locator) -> str:
        """Generate a reliable CSS selector for an element."""
        try:
            # Try ID first
            element_id = await element.get_attribute('id')
            if element_id:
                return f"#{element_id}"

            # Try name attribute
            name = await element.get_attribute('name')
            if name:
                tag = await element.evaluate('el => el.tagName.toLowerCase()')
                return f'{tag}[name="{name}"]'

            # Fall back to a more complex selector
            tag = await element.evaluate('el => el.tagName.toLowerCase()')
            class_name = await element.get_attribute('class')
            if class_name:
                first_class = class_name.split()[0]
                return f'{tag}.{first_class}'

            return tag
        except Exception:
            return "element"

    async def _extract_field_label(self, element: Locator) -> Optional[str]:
        """Extract the human-readable label for a form field."""
        try:
            # Check for explicit label association
            element_id = await element.get_attribute('id')
            if element_id:
                label = await element.page.query_selector(f'label[for="{element_id}"]')
                if label:
                    return await label.inner_text()

            # Check for parent label
            parent = await element.query_selector('xpath=..')
            if parent:
                parent_tag = await parent.evaluate('el => el.tagName.toLowerCase()')
                if parent_tag == 'label':
                    return await parent.inner_text()

            # Look for preceding text or nearby label
            siblings = await element.query_selector_all('xpath=./preceding-sibling::*')
            for sibling in siblings[:3]:  # Check first 3 preceding siblings
                sibling_tag = await sibling.evaluate('el => el.tagName.toLowerCase()')
                if sibling_tag == 'label':
                    return await sibling.inner_text()

            return None
        except Exception:
            return None

    async def fill_form(self, request: FormFillRequest) -> FormFillResponse:
        """
        Fill a web form with specified data.

        Args:
            request: Form filling request with URL and field data

        Returns:
            FormFillResponse with operation results
        """
        start_time = time.time()

        logger.info(f"Starting form fill for URL: {request.url}")

        # Initialize response
        response = FormFillResponse(
            success=False,
            fields_filled=[],
            fields_failed=[],
            execution_time=0.0,
            form_submitted=False,
            screenshots={}
        )

        try:
            # Get browser manager
            browser_manager = await self._get_browser_manager()

            # Navigate to page
            page = await browser_manager.navigate(request.url)

            # Wait for optional selector
            if request.wait_for_selector:
                await page.wait_for_selector(request.wait_for_selector, timeout=request.timeout)

            # Screenshot before filling
            if request.screenshot_before:
                screenshot_bytes = await browser_manager.screenshot(page)
                response.screenshots['before'] = base64.b64encode(screenshot_bytes).decode()

            # Detect and analyze forms
            forms = await self.detect_forms(page)
            if not forms:
                raise ValueError("No forms detected on page")

            # Use the first form (or could be made configurable)
            target_form = forms[0]
            response.form_metadata = {
                'forms_detected': len(forms),
                'selected_form': target_form,
                'total_fields': target_form['field_count']
            }

            # Fill form fields
            fields_filled = []
            fields_failed = []

            for field_name, field_value in request.form_data.items():
                try:
                    # Find matching field
                    field = await self._find_field_by_name(target_form['fields'], field_name)
                    if not field:
                        fields_failed.append(FieldResult(
                            field_name=field_name,
                            success=False,
                            error_message=f"Field '{field_name}' not found in form"
                        ))
                        continue

                    # Fill the field
                    element = page.locator(field['selector'])
                    if not await element.is_visible():
                        fields_failed.append(FieldResult(
                            field_name=field_name,
                            success=False,
                            error_message=f"Field '{field_name}' is not visible"
                        ))
                        continue

                    await self._fill_field(element, field, field_value)
                    fields_filled.append(field_name)

                    logger.info(f"Successfully filled field: {field_name}")

                except Exception as e:
                    error_msg = f"Error filling field '{field_name}': {str(e)}"
                    logger.error(error_msg)
                    fields_failed.append(FieldResult(
                        field_name=field_name,
                        success=False,
                        error_message=error_msg
                    ))

            # Update response
            response.fields_filled = fields_filled
            response.fields_failed = fields_failed

            # Submit form if requested
            if request.submit_form:
                submission_result = await self._submit_form(page, target_form)
                response.form_submitted = submission_result['success']
                response.submission_result = submission_result.get('data')

            # Screenshot after filling
            if request.screenshot_after:
                screenshot_bytes = await browser_manager.screenshot(page)
                response.screenshots['after'] = base64.b64encode(screenshot_bytes).decode()

            # Determine overall success
            response.success = len(fields_filled) > 0 and len(fields_failed) == 0

            logger.info(f"Form fill completed: {len(fields_filled)} fields filled, {len(fields_failed)} failed")

        except Exception as e:
            logger.error(f"Form fill operation failed: {e}")
            # Add a generic failure if no specific field failures
            if not response.fields_failed:
                response.fields_failed.append(FieldResult(
                    field_name="general",
                    success=False,
                    error_message=str(e)
                ))

        finally:
            # Calculate execution time
            response.execution_time = time.time() - start_time

            # Cleanup page
            try:
                if 'page' in locals():
                    await self._get_browser_manager().close_page(page)
            except Exception as e:
                logger.warning(f"Error cleaning up page: {e}")

        return response

    async def _find_field_by_name(self, fields: List[Dict], target_name: str) -> Optional[Dict]:
        """Find a field in the form by name or partial match."""
        target_name_lower = target_name.lower()

        for field in fields:
            field_name = field.get('name', '').lower()
            field_label = (field.get('label') or '').lower()

            # Exact name match
            if field_name == target_name_lower:
                return field

            # Label match
            if field_label == target_name_lower:
                return field

            # Partial matches
            if target_name_lower in field_name or field_name in target_name_lower:
                return field
            if target_name_lower in field_label or field_label in target_name_lower:
                return field

        return None

    async def _fill_field(self, element: Locator, field: Dict, value: Union[str, bool, int, List[str]]) -> None:
        """Fill a specific form field with the given value."""
        field_type = field.get('field_type', '')

        try:
            if field_type.startswith('input_') or field_type == 'textarea':
                # Text-based input
                await element.clear()
                await element.fill(str(value))

            elif field_type == 'select':
                # Dropdown selection
                if isinstance(value, list):
                    # Multiple selections
                    await element.select_option(value)
                else:
                    # Single selection
                    await element.select_option([str(value)])

            elif field_type == 'checkbox':
                # Checkbox
                if isinstance(value, bool):
                    if value != await element.is_checked():
                        await element.click()
                else:
                    # Convert string to boolean
                    should_check = str(value).lower() in ['true', '1', 'yes', 'on']
                    if should_check != await element.is_checked():
                        await element.click()

            elif field_type == 'radio':
                # Radio button selection
                # Find the specific radio button by value
                radio_selector = f'{field["selector"]}[value="{value}"]'
                radio_element = element.page.locator(radio_selector)
                if await radio_element.is_visible():
                    await radio_element.click()

            else:
                raise ValueError(f"Unsupported field type: {field_type}")

        except Exception as e:
            raise Exception(f"Failed to fill {field_type} field: {e}")

    async def _submit_form(self, page: Page, form: Dict) -> Dict:
        """Submit the form and capture the result."""
        try:
            # Look for submit button
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Send")',
                'button:has-text("Save")',
                'button:has-text("Continue")',
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = page.locator(selector).first
                    if await submit_button.is_visible():
                        break
                except:
                    continue

            if submit_button and await submit_button.is_visible():
                await submit_button.click()
                logger.info("Form submitted via submit button")
            else:
                # Try form.submit() method
                await page.evaluate('document.querySelector("form").submit()')
                logger.info("Form submitted via form.submit()")

            # Wait for navigation or response
            await page.wait_for_load_state('networkidle', timeout=3000)

            return {'success': True, 'data': {'message': 'Form submitted successfully'}}

        except Exception as e:
            logger.error(f"Form submission failed: {e}")
            return {'success': False, 'error': str(e)}