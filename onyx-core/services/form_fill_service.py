"""
Form Filling Service for ONYX Core

Implements Playwright-backed automation for populating web forms on behalf of
agents. Uses BrowserManager for navigation, FieldDetector for selector
resolution, and captures audit artifacts (before/after screenshots) to satisfy
Epic 7 Story 7.4 requirements.

Key responsibilities:
- Normalize incoming field payloads and enforce safety limits
- Navigate to requested URL through BrowserManager (serial execution)
- Resolve form controls via FieldDetector with selector strategy hints
- Interact with text/select/checkbox/radio controls and optionally submit
- Capture audit data including screenshots and per-field interaction logs

Author: ONYX Core Team
Story: 7-4-form-filling-web-interaction
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from services.browser_manager import BrowserManager
from services.field_detector import FieldDetector, FieldInfo, FormInfo

logger = logging.getLogger(__name__)


@dataclass
class FormFieldInput:
    """Normalized request payload for a single form field."""

    name: str
    value: Any
    selector: Optional[str] = None
    field_type: Optional[str] = None
    required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldInteractionResult:
    """Represents the outcome of interacting with a field."""

    name: str
    success: bool
    selector: Optional[str] = None
    selector_strategy: Optional[str] = None
    field_type: Optional[str] = None
    message: Optional[str] = None
    value_preview: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "selector": self.selector,
            "selector_strategy": self.selector_strategy,
            "field_type": self.field_type,
            "message": self.message,
            "value_preview": self.value_preview,
        }


@dataclass
class FormFillResult:
    """Aggregate result for a form filling invocation."""

    url: str
    result_url: str
    execution_time_ms: int
    submitted: bool
    submission_message: Optional[str]
    fields_filled: List[str]
    fields_failed: List[str]
    field_results: List[FieldInteractionResult]
    warnings: List[str]
    before_screenshot: Optional[str] = None
    after_screenshot: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "result_url": self.result_url,
            "submitted": self.submitted,
            "submission_message": self.submission_message,
            "execution_time_ms": self.execution_time_ms,
            "fields_filled": self.fields_filled,
            "fields_failed": self.fields_failed,
            "field_results": [result.to_dict() for result in self.field_results],
            "warnings": self.warnings,
            "before_screenshot": self.before_screenshot,
            "after_screenshot": self.after_screenshot,
        }

    @property
    def success(self) -> bool:
        return len(self.fields_failed) == 0


class FormFillService:
    """High-level orchestration for the fill_form tool."""

    def __init__(self):
        self.field_detector = FieldDetector()
        self.max_fields = int(os.getenv("FORM_FILL_MAX_FIELDS", "25"))
        self.default_submit_wait_ms = int(os.getenv("FORM_FILL_SUBMIT_WAIT_MS", "1500"))

    async def fill_form(
        self,
        url: str,
        fields: Sequence[FormFieldInput],
        *,
        submit: bool = False,
        selector_strategy: Optional[str] = None,
        wait_after_submit_ms: Optional[int] = None,
        capture_screenshots: bool = True,
    ) -> FormFillResult:
        """Fill a web form using Playwright and return audit data."""

        if not fields:
            raise ValueError("fields payload cannot be empty")
        if len(fields) > self.max_fields:
            raise ValueError(
                f"Field limit exceeded: received {len(fields)} fields (max {self.max_fields})"
            )

        start_time = asyncio.get_event_loop().time()
        browser_manager = await BrowserManager.get_instance()
        page = await browser_manager.navigate(url, wait_until="networkidle")

        before_screenshot = None
        after_screenshot = None
        warnings: List[str] = []
        submitted = False
        submission_message: Optional[str] = None
        field_results: List[FieldInteractionResult] = []
        form_selector = "form"
        form_info: Optional[FormInfo] = None

        try:
            # Analyze form up front to gather selectors, metadata, CAPTCHA status
            try:
                form_info = await self.field_detector.analyze_form(page)
                form_selector = form_info.form_selector or form_selector
                if form_info.has_captcha:
                    warnings.append("CAPTCHA detected on form; auto submission disabled")
                    submit = False
            except Exception as e:  # pragma: no cover - diagnostic warning path
                warnings.append(f"Form analysis failed: {e}")

            if capture_screenshots:
                before_screenshot = await self._capture_base64(browser_manager, page)

            for field in fields:
                result = await self._fill_single_field(
                    page,
                    field,
                    form_selector=form_selector,
                    selector_strategy=selector_strategy,
                    form_info=form_info,
                )
                field_results.append(result)

            if submit:
                submitted, submission_message = await self._submit_form(
                    page, form_selector=form_selector
                )
                wait_ms = self.default_submit_wait_ms if wait_after_submit_ms is None else wait_after_submit_ms
                if wait_ms:
                    await page.wait_for_timeout(wait_ms)

            if capture_screenshots:
                after_screenshot = await self._capture_base64(browser_manager, page)

            exec_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            fields_filled = [result.name for result in field_results if result.success]
            fields_failed = [result.name for result in field_results if not result.success]

            return FormFillResult(
                url=url,
                result_url=page.url,
                execution_time_ms=exec_ms,
                submitted=submitted,
                submission_message=submission_message,
                fields_filled=fields_filled,
                fields_failed=fields_failed,
                field_results=field_results,
                warnings=warnings,
                before_screenshot=before_screenshot,
                after_screenshot=after_screenshot,
            )

        finally:
            await browser_manager.close_page(page)

    async def _fill_single_field(
        self,
        page,
        field: FormFieldInput,
        *,
        form_selector: str,
        selector_strategy: Optional[str],
        form_info: Optional[FormInfo],
    ) -> FieldInteractionResult:
        """Attempt to fill an individual field and capture result."""

        preview_value = self._preview_value(field.value)
        result = FieldInteractionResult(
            name=field.name,
            success=False,
            value_preview=preview_value,
            field_type=field.field_type,
        )

        try:
            field_info = self._match_field_from_form(field, form_info)
            if not field_info:
                field_info = await self._find_field(
                    field.name,
                    page,
                    form_selector=form_selector,
                    strategy_hint=selector_strategy,
                )

            if not field_info:
                result.message = "Field not found"
                return result

            locator = page.locator(field_info.selector).first
            await self._apply_value(page, locator, field_info, field.value)

            result.success = True
            result.selector = field_info.selector
            result.selector_strategy = field_info.selector_strategy
            result.field_type = field_info.field_type or field.field_type
            result.message = "filled"
            return result

        except Exception as e:  # pragma: no cover - failure path
            logger.warning(f"Failed to fill field '{field.name}': {e}")
            result.success = False
            result.message = str(e)
            return result

    def _match_field_from_form(
        self, field: FormFieldInput, form_info: Optional[FormInfo]
    ) -> Optional[FieldInfo]:
        if not form_info or not form_info.fields:
            return None

        normalized = field.name.lower()
        for candidate in form_info.fields:
            for attr in filter(None, [candidate.name, candidate.label_text, candidate.placeholder]):
                if attr.lower() == normalized:
                    return candidate
        return None

    async def _find_field(
        self,
        field_name: str,
        page,
        *,
        form_selector: str,
        strategy_hint: Optional[str],
    ) -> Optional[FieldInfo]:
        """Use FieldDetector with optional selector strategy hint."""

        original = list(self.field_detector.selector_strategies)
        try:
            if strategy_hint and strategy_hint in self.field_detector.selector_strategies:
                ordered = [strategy_hint] + [
                    strategy
                    for strategy in self.field_detector.selector_strategies
                    if strategy != strategy_hint
                ]
                self.field_detector.selector_strategies = ordered

            return await self.field_detector.find_field(page, field_name, form_selector=form_selector)
        finally:
            self.field_detector.selector_strategies = original

    async def _apply_value(self, page, locator, field_info: FieldInfo, raw_value: Any) -> None:
        """Apply a value to a Playwright locator based on field type."""

        field_type = (field_info.field_type or "text").lower()
        value = raw_value
        if isinstance(raw_value, dict):
            value = raw_value.get("value") or raw_value.get("text") or raw_value.get("label")

        if field_type in {"text", "email", "password", "textarea"}:
            await locator.fill("" if value is None else str(value))
        elif field_type == "select":
            await locator.select_option(self._normalize_select_value(value))
        elif field_type == "checkbox":
            desired_state = bool(value)
            current_state = await locator.is_checked()
            if desired_state != current_state:
                await locator.click()
        elif field_type == "radio":
            await self._select_radio_option(page, field_info, value)
        else:
            # Default to typing/filling for unrecognized types
            await locator.fill("" if value is None else str(value))

    async def _select_radio_option(self, page, field_info: FieldInfo, value: Any) -> None:
        if value is None:
            raise ValueError("Radio field requires a value to select")

        selector = field_info.selector
        if field_info.name:
            radio_selector = f"input[type='radio'][name='{field_info.name}'][value='{value}']"
            candidate = page.locator(radio_selector)
            if await candidate.count():
                await candidate.first.check()
                return

        await page.locator(selector).first.check()

    def _normalize_select_value(self, value: Any) -> Any:
        if value is None:
            raise ValueError("Select field requires a value")
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        return str(value)

    async def _submit_form(self, page, *, form_selector: str) -> Tuple[bool, Optional[str]]:
        """Attempt to submit the form by clicking a submit button."""

        buttons = page.locator(
            f"{form_selector} button[type='submit'], {form_selector} input[type='submit'], {form_selector} button:not([type])"
        )

        if not await buttons.count():
            return False, "No submit button detected"

        try:
            await buttons.first.click()
            return True, "Form submitted"
        except Exception as e:
            return False, f"Submit failed: {e}"

    async def _capture_base64(self, browser_manager: BrowserManager, page) -> str:
        screenshot_bytes = await browser_manager.screenshot(page, full_page=True)
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    def _preview_value(self, value: Any, max_len: int = 64) -> Optional[str]:
        if value is None:
            return None
        text = str(value)
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text
