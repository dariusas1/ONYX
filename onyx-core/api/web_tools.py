"""
Web Tools API Router

This module provides FastAPI endpoints for web automation and content extraction
tools including URL scraping, content analysis, and browser automation.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, HttpUrl
import logging

from services.web_content_extractor import WebContentExtractor
from services.browser_manager import BrowserManager
from services.form_manager import FormManager, FormFillRequest, FormFillResult
from services.screenshot_service import ScreenshotService, ScreenshotOptions, ScreenshotResult
from services.google_drive_sync import GoogleDriveService
from utils.auth import require_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Web Tools"])


# Request/Response models
class ScrapeUrlRequest(BaseModel):
    """Request model for URL scraping"""

    url: HttpUrl
    content_type: Optional[Literal["article", "product", "documentation", "academic"]] = None
    extract_images: bool = True
    extract_links: bool = True
    extract_metadata: bool = True


class ScrapeUrlResponse(BaseModel):
    """Response model for URL scraping"""

    success: bool
    url: str
    content_type: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    extraction_time_ms: Optional[float] = None
    quality_score: Optional[float] = None
    extracted_at: Optional[str] = None


class FillFormRequest(BaseModel):
    """Request model for form filling"""

    url: HttpUrl
    fields: Dict[str, Any]
    submit: bool = False
    selector_strategy: str = "label"
    timeout: int = 30
    screenshots: bool = True


class FillFormResponse(BaseModel):
    """Response model for form filling"""

    success: bool
    url: str
    total_fields: int
    successful_fields: int
    failed_fields: int
    field_results: List[Dict[str, Any]] = []
    screenshots: Optional[Dict[str, str]] = None
    submit_result: Optional[Dict[str, Any]] = None
    execution_time_ms: float
    error: Optional[str] = None
    captcha_detected: bool = False
    executed_at: str


class ScreenshotPageRequest(BaseModel):
    """Request model for screenshot capture"""

    url: HttpUrl
    format: Optional[Literal["png", "jpeg"]] = "png"
    quality: Optional[int] = 85
    width: Optional[int] = 1920
    height: Optional[int] = 1080
    device_preset: Optional[Literal["desktop", "laptop", "tablet", "mobile", "mobile_large"]] = None
    full_page: Optional[bool] = True
    store_in_drive: Optional[bool] = False
    drive_folder: Optional[str] = "Screenshots"
    timeout: Optional[int] = 30


class ScreenshotPageResponse(BaseModel):
    """Response model for screenshot capture"""

    success: bool
    url: str
    image_data: Optional[str] = None  # Base64 encoded image
    drive_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    captured_at: Optional[str] = None


# =============================================================================
# Content Extraction Endpoints
# =============================================================================

@router.post("/scrape_url", response_model=ScrapeUrlResponse)
async def scrape_url(
    request: ScrapeUrlRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Extract structured content from a URL.

    This endpoint provides intelligent content extraction from web pages with support for
    multiple content types (articles, products, documentation, academic papers).

    Args:
        request: Scrape request with URL and options
        current_user: Authenticated user from JWT token

    Returns:
        Extracted content with metadata and quality score
    """
    try:
        logger.info(f"User {current_user.get('email')} scraping URL: {request.url}")

        # Get browser manager instance
        browser_manager = await BrowserManager.get_instance()

        # Create web content extractor
        extractor = WebContentExtractor(browser_manager)

        # Extract content
        result = await extractor.extract_content(
            url=str(request.url),
            content_type=request.content_type,
            extract_images=request.extract_images,
            extract_links=request.extract_links,
            extract_metadata=request.extract_metadata
        )

        # Check if extraction was successful
        if 'error' in result:
            logger.warning(f"Content extraction failed: {result['error']}")
            return ScrapeUrlResponse(
                success=False,
                url=str(request.url),
                content_type=result.get('content_type', 'unknown'),
                error=result['error'],
                extraction_time_ms=result.get('extraction_time_ms'),
                quality_score=result.get('quality_score', 0.0),
                extracted_at=result.get('extracted_at')
            )

        logger.info(f"Content extraction successful: {result.get('word_count', 0)} words, "
                   f"quality_score: {result.get('quality_score', 0.0):.2f}")

        return ScrapeUrlResponse(
            success=True,
            url=str(request.url),
            content_type=result.get('content_type', 'unknown'),
            data=result,
            extraction_time_ms=result.get('extraction_time_ms'),
            quality_score=result.get('quality_score'),
            extracted_at=result.get('extracted_at')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during content extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail="Content extraction service temporarily unavailable"
        )


@router.get("/scrape_url", response_model=ScrapeUrlResponse)
async def scrape_url_get(
    url: HttpUrl = Query(..., description="URL to scrape content from"),
    content_type: Optional[Literal["article", "product", "documentation", "academic"]] = Query(
        None, description="Content type hint (auto-detected if not provided)"
    ),
    extract_images: bool = Query(True, description="Extract images from the page"),
    extract_links: bool = Query(True, description="Extract links from the page"),
    extract_metadata: bool = Query(True, description="Extract detailed metadata"),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Extract structured content from a URL (GET method).

    This endpoint provides the same functionality as POST /scrape_url but using
    query parameters for convenience in testing and simple integrations.

    Args:
        url: URL to extract content from
        content_type: Optional content type hint
        extract_images: Whether to extract images
        extract_links: Whether to extract links
        extract_metadata: Whether to extract detailed metadata
        current_user: Authenticated user from JWT token

    Returns:
        Extracted content with metadata and quality score
    """
    try:
        logger.info(f"User {current_user.get('email')} scraping URL via GET: {url}")

        # Get browser manager instance
        browser_manager = await BrowserManager.get_instance()

        # Create web content extractor
        extractor = WebContentExtractor(browser_manager)

        # Extract content
        result = await extractor.extract_content(
            url=str(url),
            content_type=content_type,
            extract_images=extract_images,
            extract_links=extract_links,
            extract_metadata=extract_metadata
        )

        # Check if extraction was successful
        if 'error' in result:
            logger.warning(f"Content extraction failed: {result['error']}")
            return ScrapeUrlResponse(
                success=False,
                url=str(url),
                content_type=result.get('content_type', 'unknown'),
                error=result['error'],
                extraction_time_ms=result.get('extraction_time_ms'),
                quality_score=result.get('quality_score', 0.0),
                extracted_at=result.get('extracted_at')
            )

        logger.info(f"Content extraction successful: {result.get('word_count', 0)} words, "
                   f"quality_score: {result.get('quality_score', 0.0):.2f}")

        return ScrapeUrlResponse(
            success=True,
            url=str(url),
            content_type=result.get('content_type', 'unknown'),
            data=result,
            extraction_time_ms=result.get('extraction_time_ms'),
            quality_score=result.get('quality_score'),
            extracted_at=result.get('extracted_at')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during content extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail="Content extraction service temporarily unavailable"
        )


# =============================================================================
# Browser Automation Endpoints
# =============================================================================

@router.get("/browser/status")
async def get_browser_status(current_user: dict = Depends(require_authenticated_user)):
    """
    Get current browser automation status.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Browser status information
    """
    try:
        browser_manager = await BrowserManager.get_instance()
        status = await browser_manager.get_status()

        return {
            "success": True,
            "data": status,
            "message": "Browser status retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting browser status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve browser status"
        )


@router.post("/browser/cleanup")
async def cleanup_browser(current_user: dict = Depends(require_authenticated_user)):
    """
    Force cleanup of browser resources.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Cleanup operation result
    """
    try:
        browser_manager = await BrowserManager.get_instance()
        await browser_manager.cleanup()

        return {
            "success": True,
            "message": "Browser cleanup completed successfully"
        }

    except Exception as e:
        logger.error(f"Error during browser cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail="Browser cleanup failed"
        )


# =============================================================================
# Form Automation Endpoints
# =============================================================================

@router.post("/fill_form", response_model=FillFormResponse)
async def fill_form(
    request: FillFormRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Fill a web form with provided field values.

    This endpoint provides intelligent form filling with support for multiple field types,
    automatic field detection, screenshot capture for audit trails, and form submission.

    Args:
        request: Form fill request with URL and field values
        current_user: Authenticated user from JWT token

    Returns:
        Comprehensive form fill result with field-level details and audit information
    """
    try:
        logger.info(f"User {current_user.get('email')} filling form at: {request.url}")

        # Create form manager
        form_manager = FormManager()
        await form_manager.get_instance()

        # Convert request to internal format
        form_request = FormFillRequest(
            url=str(request.url),
            fields=request.fields,
            submit=request.submit,
            selector_strategy=request.selector_strategy,
            timeout=request.timeout,
            screenshots=request.screenshots
        )

        # Fill form
        result = await form_manager.fill_form(form_request)

        # Convert result to response format
        field_results = []
        for field_result in result.field_results:
            field_data = {
                "field_name": field_result.field_name,
                "success": field_result.success,
                "value": field_result.value,
                "error": field_result.error,
                "execution_time_ms": field_result.execution_time_ms
            }
            if field_result.field_info:
                field_data["field_info"] = {
                    "field_type": field_result.field_info.field_type,
                    "selector": field_result.field_info.selector,
                    "selector_strategy": field_result.field_info.selector_strategy,
                    "name": field_result.field_info.name,
                    "id": field_result.field_info.id,
                    "label_text": field_result.field_info.label_text
                }
            field_results.append(field_data)

        if result.success:
            logger.info(f"Form fill successful: {result.successful_fields}/{result.total_fields} fields "
                       f"in {result.execution_time_ms:.0f}ms")
        else:
            logger.warning(f"Form fill failed: {result.error}")

        return FillFormResponse(
            success=result.success,
            url=result.url,
            total_fields=result.total_fields,
            successful_fields=result.successful_fields,
            failed_fields=result.failed_fields,
            field_results=field_results,
            screenshots=result.screenshots,
            submit_result=result.submit_result,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
            captcha_detected=result.captcha_detected,
            executed_at=result.executed_at
        )

    except Exception as e:
        logger.error(f"Unexpected error during form filling: {e}")
        raise HTTPException(
            status_code=500,
            detail="Form filling service temporarily unavailable"
        )


@router.get("/fill_form", response_model=FillFormResponse)
async def fill_form_get(
    url: HttpUrl = Query(..., description="URL of the page containing the form"),
    fields: str = Query(..., description="JSON-encoded field values (e.g., '{\"name\":\"John\",\"email\":\"john@example.com\"}')"),
    submit: bool = Query(False, description="Whether to submit the form after filling"),
    selector_strategy: str = Query("label", description="Field matching strategy"),
    timeout: int = Query(30, description="Timeout in seconds"),
    screenshots: bool = Query(True, description="Capture before/after screenshots"),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Fill a web form with provided field values (GET method).

    This endpoint provides the same functionality as POST /fill_form but using
    query parameters for convenience in testing and simple integrations.

    Args:
        url: URL of the page containing the form
        fields: JSON-encoded field values
        submit: Whether to submit the form after filling
        selector_strategy: Field matching strategy
        timeout: Timeout in seconds
        screenshots: Capture before/after screenshots
        current_user: Authenticated user from JWT token

    Returns:
        Comprehensive form fill result with field-level details and audit information
    """
    try:
        import json

        logger.info(f"User {current_user.get('email')} filling form via GET: {url}")

        # Parse fields from JSON string
        try:
            fields_data = json.loads(fields)
            if not isinstance(fields_data, dict):
                raise ValueError("Fields must be a JSON object")
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON format for fields parameter"
            )

        # Create form manager
        form_manager = FormManager()
        await form_manager.get_instance()

        # Convert request to internal format
        form_request = FormFillRequest(
            url=str(url),
            fields=fields_data,
            submit=submit,
            selector_strategy=selector_strategy,
            timeout=timeout,
            screenshots=screenshots
        )

        # Fill form
        result = await form_manager.fill_form(form_request)

        # Convert result to response format
        field_results = []
        for field_result in result.field_results:
            field_data = {
                "field_name": field_result.field_name,
                "success": field_result.success,
                "value": field_result.value,
                "error": field_result.error,
                "execution_time_ms": field_result.execution_time_ms
            }
            if field_result.field_info:
                field_data["field_info"] = {
                    "field_type": field_result.field_info.field_type,
                    "selector": field_result.field_info.selector,
                    "selector_strategy": field_result.field_info.selector_strategy,
                    "name": field_result.field_info.name,
                    "id": field_result.field_info.id,
                    "label_text": field_result.field_info.label_text
                }
            field_results.append(field_data)

        if result.success:
            logger.info(f"Form fill successful: {result.successful_fields}/{result.total_fields} fields "
                       f"in {result.execution_time_ms:.0f}ms")
        else:
            logger.warning(f"Form fill failed: {result.error}")

        return FillFormResponse(
            success=result.success,
            url=result.url,
            total_fields=result.total_fields,
            successful_fields=result.successful_fields,
            failed_fields=result.failed_fields,
            field_results=field_results,
            screenshots=result.screenshots,
            submit_result=result.submit_result,
            execution_time_ms=result.execution_time_ms,
            error=result.error,
            captcha_detected=result.captcha_detected,
            executed_at=result.executed_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during form filling: {e}")
        raise HTTPException(
            status_code=500,
            detail="Form filling service temporarily unavailable"
        )


@router.get("/form-field-types")
async def get_supported_field_types(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get list of supported form field types for form filling.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        List of supported field types with descriptions and examples
    """
    try:
        field_types = {
            "text": {
                "name": "Text Input",
                "description": "Standard text input fields",
                "examples": ["name", "address", "company", "phone", "search"],
                "html_tags": ["<input type='text'>", "<input type='search'>", "<input type='tel'>", "<input type='url'>"],
                "validation": "Basic string validation, XSS prevention"
            },
            "email": {
                "name": "Email Input",
                "description": "Email address input fields",
                "examples": ["email", "email_address", "contact_email"],
                "html_tags": ["<input type='email'>"],
                "validation": "Email format validation"
            },
            "password": {
                "name": "Password Input",
                "description": "Password input fields",
                "examples": ["password", "pass", "pwd"],
                "html_tags": ["<input type='password'>"],
                "validation": "Standard password field handling"
            },
            "textarea": {
                "name": "Text Area",
                "description": "Multi-line text input fields",
                "examples": ["message", "comments", "description", "feedback"],
                "html_tags": ["<textarea>"],
                "validation": "Multi-line text support"
            },
            "select": {
                "name": "Select Dropdown",
                "description": "Dropdown selection fields",
                "examples": ["country", "state", "category", "language"],
                "html_tags": ["<select>"],
                "validation": "Option matching by text or value"
            },
            "checkbox": {
                "name": "Checkbox",
                "description": "Checkbox fields for boolean values",
                "examples": ["agree", "subscribe", "remember_me", "terms"],
                "html_tags": ["<input type='checkbox'>"],
                "validation": "Boolean value handling"
            },
            "radio": {
                "name": "Radio Button",
                "description": "Radio button groups for single selection",
                "examples": ["gender", "payment_method", "plan"],
                "html_tags": ["<input type='radio'>"],
                "validation": "Single option selection"
            }
        }

        selector_strategies = {
            "name": {
                "name": "Name Attribute",
                "description": "Match by the field's name attribute (most reliable)",
                "example": "name='first_name' matches field with name='first_name'"
            },
            "id": {
                "name": "ID Attribute",
                "description": "Match by the field's id attribute (very reliable)",
                "example": "id='email-input' matches field with id='email-input'"
            },
            "label": {
                "name": "Label Text",
                "description": "Match by associated label text (good for accessibility)",
                "example": "label 'Email Address:' matches field with that label"
            },
            "placeholder": {
                "name": "Placeholder Text",
                "description": "Match by placeholder text (moderate reliability)",
                "example": "placeholder='Enter your email' matches field with that placeholder"
            },
            "css_class": {
                "name": "CSS Class",
                "description": "Match by CSS class names (fallback for styled forms)",
                "example": "class='form-control' matches field with that class"
            },
            "aria_label": {
                "name": "ARIA Label",
                "description": "Match by ARIA label attributes (accessibility fallback)",
                "example": "aria-label='Search query' matches field with that ARIA label"
            }
        }

        return {
            "success": True,
            "data": {
                "field_types": field_types,
                "selector_strategies": selector_strategies,
                "performance_targets": {
                    "form_fill_time": "<5 seconds for typical forms (5-10 fields)",
                    "screenshot_capture": "<1 second for before/after images",
                    "field_detection": "<500ms for form analysis",
                    "browser_navigation": "<3 seconds page load time"
                },
                "security_features": [
                    "Input sanitization for XSS prevention",
                    "CAPTCHA detection and manual intervention",
                    "URL validation against blocked domains",
                    "Audit trail with screenshot documentation",
                    "Rate limiting to prevent abuse"
                ]
            },
            "message": "Form field types information retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting field types: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve field types information"
        )


# =============================================================================
# Screenshot Capture Endpoints
# =============================================================================

@router.post("/screenshot_page", response_model=ScreenshotPageResponse)
async def screenshot_page(
    request: ScreenshotPageRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Capture a full-page screenshot of a web page.

    This endpoint provides high-quality screenshot capture with support for
    multiple image formats, configurable resolutions, and optional Google Drive storage.

    Args:
        request: Screenshot request with URL and options
        current_user: Authenticated user from JWT token

    Returns:
        Screenshot capture result with image data and metadata
    """
    try:
        logger.info(f"User {current_user.get('email')} capturing screenshot of: {request.url}")

        # Initialize Google Drive service if needed
        drive_service = None
        if request.store_in_drive:
            try:
                drive_service = GoogleDriveService()
                logger.info("Google Drive service initialized for screenshot storage")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Drive service: {e}")
                # Continue without Drive storage

        # Create screenshot service
        screenshot_service = ScreenshotService(drive_service)

        # Create screenshot options
        options = ScreenshotOptions(
            url=str(request.url),
            format=request.format or "png",
            quality=request.quality or 85,
            width=request.width,
            height=request.height,
            device_preset=request.device_preset,
            full_page=request.full_page,
            store_in_drive=request.store_in_drive,
            drive_folder=request.drive_folder,
            timeout=request.timeout * 1000  # Convert to milliseconds
        )

        # Capture screenshot
        result = await screenshot_service.capture_screenshot(options)

        if not result.success:
            logger.warning(f"Screenshot capture failed: {result.error}")
            return ScreenshotPageResponse(
                success=False,
                url=str(request.url),
                error=result.error,
                execution_time_ms=result.execution_time_ms,
                captured_at=result.captured_at
            )

        logger.info(f"Screenshot captured successfully in {result.execution_time_ms:.0f}ms, "
                   f"format: {result.metadata.get('format', 'unknown')}, "
                   f"size: {result.metadata.get('file_size', 0)} bytes")

        return ScreenshotPageResponse(
            success=True,
            url=str(request.url),
            image_data=result.base64_data,
            drive_url=result.drive_url,
            metadata=result.metadata,
            execution_time_ms=result.execution_time_ms,
            captured_at=result.captured_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during screenshot capture: {e}")
        raise HTTPException(
            status_code=500,
            detail="Screenshot capture service temporarily unavailable"
        )


@router.get("/screenshot_page", response_model=ScreenshotPageResponse)
async def screenshot_page_get(
    url: HttpUrl = Query(..., description="URL to capture screenshot from"),
    format: Optional[Literal["png", "jpeg"]] = Query("png", description="Image format (png or jpeg)"),
    quality: Optional[int] = Query(85, description="JPEG quality (1-100, for JPEG only)"),
    width: Optional[int] = Query(1920, description="Viewport width in pixels"),
    height: Optional[int] = Query(1080, description="Viewport height in pixels"),
    device_preset: Optional[Literal["desktop", "laptop", "tablet", "mobile", "mobile_large"]] = Query(
        None, description="Device preset for viewport (overrides width/height)"
    ),
    full_page: Optional[bool] = Query(True, description="Capture full page or just viewport"),
    store_in_drive: Optional[bool] = Query(False, description="Store screenshot in Google Drive"),
    drive_folder: Optional[str] = Query("Screenshots", description="Drive folder for screenshots"),
    timeout: Optional[int] = Query(30, description="Capture timeout in seconds"),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Capture a full-page screenshot of a web page (GET method).

    This endpoint provides the same functionality as POST /screenshot_page but using
    query parameters for convenience in testing and simple integrations.

    Args:
        url: URL to capture screenshot from
        format: Image format (png or jpeg)
        quality: JPEG quality (1-100, for JPEG only)
        width: Viewport width in pixels
        height: Viewport height in pixels
        device_preset: Device preset for viewport (overrides width/height)
        full_page: Capture full page or just viewport
        store_in_drive: Store screenshot in Google Drive
        drive_folder: Drive folder for screenshots
        timeout: Capture timeout in seconds
        current_user: Authenticated user from JWT token

    Returns:
        Screenshot capture result with image data and metadata
    """
    try:
        logger.info(f"User {current_user.get('email')} capturing screenshot via GET: {url}")

        # Initialize Google Drive service if needed
        drive_service = None
        if store_in_drive:
            try:
                drive_service = GoogleDriveService()
                logger.info("Google Drive service initialized for screenshot storage")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Drive service: {e}")
                # Continue without Drive storage

        # Create screenshot service
        screenshot_service = ScreenshotService(drive_service)

        # Create screenshot options
        options = ScreenshotOptions(
            url=str(url),
            format=format or "png",
            quality=quality or 85,
            width=width,
            height=height,
            device_preset=device_preset,
            full_page=full_page,
            store_in_drive=store_in_drive,
            drive_folder=drive_folder,
            timeout=timeout * 1000  # Convert to milliseconds
        )

        # Capture screenshot
        result = await screenshot_service.capture_screenshot(options)

        if not result.success:
            logger.warning(f"Screenshot capture failed: {result.error}")
            return ScreenshotPageResponse(
                success=False,
                url=str(url),
                error=result.error,
                execution_time_ms=result.execution_time_ms,
                captured_at=result.captured_at
            )

        logger.info(f"Screenshot captured successfully in {result.execution_time_ms:.0f}ms, "
                   f"format: {result.metadata.get('format', 'unknown')}, "
                   f"size: {result.metadata.get('file_size', 0)} bytes")

        return ScreenshotPageResponse(
            success=True,
            url=str(url),
            image_data=result.base64_data,
            drive_url=result.drive_url,
            metadata=result.metadata,
            execution_time_ms=result.execution_time_ms,
            captured_at=result.captured_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during screenshot capture: {e}")
        raise HTTPException(
            status_code=500,
            detail="Screenshot capture service temporarily unavailable"
        )


@router.get("/screenshot/presets")
async def get_screenshot_presets(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get available device presets for screenshot capture.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        List of available device presets with their dimensions
    """
    try:
        presets = ScreenshotOptions.DEVICE_PRESETS

        return {
            "success": True,
            "data": presets,
            "message": "Screenshot device presets retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting screenshot presets: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve screenshot presets"
        )


# =============================================================================
# Content Analysis Endpoints
# =============================================================================

@router.get("/content-types")
async def get_supported_content_types(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get list of supported content types for extraction.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        List of supported content types with descriptions
    """
    try:
        content_types = {
            "article": {
                "name": "Article",
                "description": "News articles, blog posts, publications",
                "examples": ["news websites", "medium articles", "blog posts"],
                "extraction_fields": ["title", "author", "publish_date", "content", "summary"]
            },
            "product": {
                "name": "Product",
                "description": "E-commerce product pages with pricing",
                "examples": ["Amazon products", "Shopify stores", "product listings"],
                "extraction_fields": ["name", "price", "currency", "description", "images", "specifications"]
            },
            "documentation": {
                "name": "Documentation",
                "description": "Technical documentation and API docs",
                "examples": ["API docs", "tutorials", "technical guides", "GitHub Pages"],
                "extraction_fields": ["title", "table_of_contents", "sections", "code_examples"]
            },
            "academic": {
                "name": "Academic",
                "description": "Research papers and academic publications",
                "examples": ["arXiv papers", "research articles", "scholarly publications"],
                "extraction_fields": ["title", "authors", "abstract", "citations", "content"]
            },
            "generic": {
                "name": "Generic",
                "description": "Fallback extraction for unknown content types",
                "examples": ["General web pages", "unknown content types"],
                "extraction_fields": ["title", "content", "quality_score"]
            }
        }

        return {
            "success": True,
            "data": {
                "content_types": content_types,
                "auto_detection": True,
                "quality_scoring": True
            },
            "message": "Content types information retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting content types: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve content types information"
        )


@router.get("/quality-thresholds")
async def get_quality_thresholds(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get content quality scoring thresholds and criteria.

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Quality scoring thresholds and explanation
    """
    try:
        thresholds = {
            "score_ranges": {
                "excellent": {"min": 0.8, "max": 1.0, "description": "High-quality content with comprehensive metadata"},
                "good": {"min": 0.6, "max": 0.8, "description": "Good content with some metadata"},
                "fair": {"min": 0.4, "max": 0.6, "description": "Acceptable content with minimal metadata"},
                "poor": {"min": 0.2, "max": 0.4, "description": "Low-quality content or extraction issues"},
                "very_poor": {"min": 0.0, "max": 0.2, "description": "Very low quality, likely errors or empty content"}
            },
            "scoring_factors": {
                "content_length": {
                    "weight": 0.3,
                    "criteria": {
                        "2000+ words": 0.3,
                        "1000-2000 words": 0.25,
                        "500-1000 words": 0.2,
                        "100-500 words": 0.1
                    }
                },
                "structure": {
                    "weight": 0.25,
                    "criteria": {
                        "has_title": 0.1,
                        "known_content_type": 0.1,
                        "has_sections_or_specs": 0.05
                    }
                },
                "metadata": {
                    "weight": 0.25,
                    "criteria": "Completeness of author, date, summary fields"
                },
                "readability": {
                    "weight": 0.2,
                    "criteria": {
                        "10-20 words/sentence": 0.2,
                        "5-30 words/sentence": 0.15,
                        "3-40 words/sentence": 0.1
                    }
                }
            }
        }

        return {
            "success": True,
            "data": thresholds,
            "message": "Quality thresholds information retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting quality thresholds: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve quality thresholds information"
        )