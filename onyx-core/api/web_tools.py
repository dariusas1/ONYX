"""
Web Tools API Router

Provides API endpoints for web automation tools including:
- URL scraping and content extraction
- Web search integration
- Screenshot capture
- Form filling

Author: ONYX Core Team
Story: 7-3-url-scraping-content-extraction
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List, Dict, Any, Union, Literal
import logging
import asyncio
from datetime import datetime

from services.scraper_service import ScraperService, ScrapedContent
from services.cache_manager import CacheManager
from services.browser_manager import BrowserManager
from services.form_fill_service import FormFillService, FormFieldInput
from utils.auth import require_authenticated_user

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/tools", tags=["web-tools"])

# Global service instances (initialized on startup)
scraper_service: Optional[ScraperService] = None
cache_manager: Optional[CacheManager] = None
form_fill_service: Optional[FormFillService] = None


# Pydantic Models for API

class ScrapeUrlRequest(BaseModel):
    """Request model for URL scraping."""

    url: HttpUrl = Field(
        ...,
        description="URL to scrape and extract content from"
    )

    force_refresh: bool = Field(
        False,
        description="Skip cache and force fresh scraping"
    )

    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "force_refresh": False
            }
        }


class ScrapeUrlResponse(BaseModel):
    """Response model for URL scraping."""

    success: bool = Field(..., description="Whether scraping was successful")

    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Scraped content data if successful"
    )

    error: Optional[Dict[str, str]] = Field(
        None,
        description="Error details if scraping failed"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Response metadata"
    )

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "url": "https://example.com/article",
                    "title": "Example Article",
                    "text_content": "Article content...",
                    "markdown_content": "# Article Title\n\nArticle content...",
                    "author": "John Doe",
                    "publish_date": "2024-01-15T10:00:00Z",
                    "excerpt": "Article excerpt...",
                    "word_count": 1500,
                    "scraped_at": "2024-01-16T14:30:00Z"
                },
                "metadata": {
                    "execution_time_ms": 3200,
                    "cached": False
                }
            }
        }


class BatchScrapeRequest(BaseModel):
    """Request model for batch URL scraping."""

    urls: List[HttpUrl] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="List of URLs to scrape (max 10)"
    )

    force_refresh: bool = Field(
        False,
        description="Skip cache and force fresh scraping"
    )

    class Config:
        schema_extra = {
            "example": {
                "urls": [
                    "https://example.com/article1",
                    "https://example.com/article2"
                ],
                "force_refresh": False
            }
        }


class BatchScrapeResponse(BaseModel):
    """Response model for batch URL scraping."""

    success: bool = Field(..., description="Whether batch scraping completed")

    results: List[Dict[str, Any]] = Field(
        ...,
        description="List of scraping results for each URL"
    )

    summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Summary statistics"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Response metadata"
    )


SelectorStrategy = Literal["name", "id", "label", "placeholder", "css_class", "aria_label"]


class FormFieldPayload(BaseModel):
    """Field descriptor for form filling."""

    name: str = Field(..., min_length=1, description="Human-readable field name or label")
    value: Any = Field(..., description="Value to inject into the control")
    selector: Optional[str] = Field(
        None,
        description="Optional CSS selector override when automatic detection is insufficient"
    )
    field_type: Optional[str] = Field(
        None,
        description="Optional field type hint (text, select, checkbox, radio, textarea)"
    )
    required: bool = Field(
        False,
        description="Whether this field is required for success calculation"
    )


class FormFillRequest(BaseModel):
    """Request payload for fill_form operations."""

    url: HttpUrl = Field(..., description="URL containing the target form")
    fields: List[FormFieldPayload] = Field(..., description="List of fields to populate")
    submit: bool = Field(False, description="Whether to submit the form after filling")
    selector_strategy: Optional[SelectorStrategy] = Field(
        None,
        description="Optional selector strategy hint for FieldDetector"
    )
    wait_after_submit_ms: Optional[int] = Field(
        1500,
        ge=0,
        le=10000,
        description="Wait duration after submission for DOM updates"
    )
    capture_screenshots: bool = Field(
        True,
        description="Capture before/after screenshots for audit"
    )

    @validator("fields", pre=True)
    def normalize_fields(cls, value):
        if isinstance(value, dict):
            return [{"name": field_name, "value": field_value} for field_name, field_value in value.items()]
        return value

    @validator("fields")
    def ensure_fields_not_empty(cls, value):
        if not value:
            raise ValueError("fields must contain at least one entry")
        return value


class FieldResultModel(BaseModel):
    """Response model for individual field interactions."""

    name: str
    success: bool
    selector: Optional[str]
    selector_strategy: Optional[str]
    field_type: Optional[str]
    message: Optional[str]
    value_preview: Optional[str]


class FormFillResponseData(BaseModel):
    """Structured response data for fill_form."""

    url: HttpUrl
    result_url: HttpUrl
    submitted: bool
    submission_message: Optional[str]
    execution_time_ms: int
    fields_filled: List[str]
    fields_failed: List[str]
    field_results: List[FieldResultModel]
    warnings: List[str]
    before_screenshot: Optional[str]
    after_screenshot: Optional[str]


class FormFillResponse(BaseModel):
    """Response wrapper for fill_form requests."""

    success: bool
    data: FormFillResponseData
    error: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]


class ScreenshotRequest(BaseModel):
    """Request model for screenshot capture."""

    url: HttpUrl = Field(
        ...,
        description="URL to capture screenshot from"
    )

    full_page: bool = Field(
        True,
        description="Capture full page or viewport only"
    )

    format: Literal["png", "jpeg"] = Field(
        "png",
        description="Image format: PNG (lossless) or JPEG (compressed)"
    )

    quality: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="JPEG quality (1-100), only used for JPEG format"
    )

    selector: Optional[str] = Field(
        None,
        min_length=1,
        description="CSS selector to capture specific element instead of full page"
    )

    width: Optional[int] = Field(
        None,
        ge=100,
        le=4000,
        description="Optional viewport width override"
    )

    height: Optional[int] = Field(
        None,
        ge=100,
        le=4000,
        description="Optional viewport height override"
    )

    wait_strategy: Literal["load", "domcontentloaded", "networkidle"] = Field(
        "load",
        description="Navigation wait strategy"
    )

    @validator('quality')
    def validate_jpeg_quality(cls, v, values):
        """Validate quality parameter only applies to JPEG format."""
        if v is not None and values.get('format') == 'png':
            raise ValueError('quality parameter only applies to JPEG format')
        return v

    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com",
                "full_page": True,
                "format": "png",
                "quality": None,
                "selector": None,
                "width": 1920,
                "height": 1080,
                "wait_strategy": "load"
            }
        }


class ScreenshotResponseData(BaseModel):
    """Screenshot response data."""

    url: HttpUrl = Field(..., description="URL that was captured")
    format: Literal["png", "jpeg"] = Field(..., description="Image format used")
    full_page: bool = Field(..., description="Whether full page was captured")
    data_url: str = Field(..., description="Base64 data URL for the image")
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")
    file_size_bytes: int = Field(..., description="Size of the image file in bytes")
    selector: Optional[str] = Field(None, description="CSS selector if element capture")
    execution_time_ms: int = Field(..., description="Time taken to capture screenshot")


class ScreenshotResponse(BaseModel):
    """Response model for screenshot capture."""

    success: bool = Field(..., description="Whether screenshot was captured successfully")

    data: Optional[ScreenshotResponseData] = Field(
        None,
        description="Screenshot data if successful"
    )

    error: Optional[Dict[str, Any]] = Field(
        None,
        description="Error details if screenshot failed"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Response metadata"
    )


# Service Initialization

async def initialize_services():
    """Initialize global service instances."""
    global scraper_service, cache_manager, form_fill_service

    try:
        # Initialize cache manager
        cache_manager = CacheManager()

        # Initialize scraper service
        scraper_service = ScraperService(cache_manager=cache_manager)

        # Initialize form fill service
        if not form_fill_service:
            form_fill_service = FormFillService()

        logger.info("Web tools services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize web tools services: {e}")
        raise


# API Endpoints

@router.post("/scrape_url", response_model=ScrapeUrlResponse)
async def scrape_url(
    request: ScrapeUrlRequest,
    current_user: dict = Depends(require_authenticated_user),
    background_tasks: BackgroundTasks = None
) -> ScrapeUrlResponse:
    """
    Scrape and extract clean content from a URL.

    Uses Mozilla Readability algorithm to clean HTML, converts to Markdown,
    extracts metadata, and returns structured content with caching.

    Args:
        request: Scrape URL request with URL and options
        current_user: Authenticated user (from auth dependency)
        background_tasks: FastAPI background tasks for async operations

    Returns:
        ScrapeUrlResponse with scraped content or error details

    Raises:
        HTTPException: For authentication or server errors
    """
    if not scraper_service:
        await initialize_services()

    start_time = asyncio.get_event_loop().time()

    try:
        logger.info(f"User {current_user.get('user_id')} scraping URL: {request.url}")

        # Perform scraping
        result: ScrapedContent = await scraper_service.scrape_url(
            str(request.url),
            force_refresh=request.force_refresh
        )

        execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        # Determine if result was from cache
        cached = False
        if not request.force_refresh and cache_manager:
            cache_key = scraper_service._generate_cache_key(str(request.url))
            cached = await cache_manager.exists(cache_key)

        if result.error:
            # Return successful response with error in data
            response_data = {
                "success": False,
                "data": result.to_dict(),
                "error": {
                    "code": "CONTENT_EXTRACTION_WARNING" if "too short" in result.error else "CONTENT_EXTRACTION_ERROR",
                    "message": result.error
                },
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "cached": cached,
                    "user_id": current_user.get('user_id')
                }
            }
        else:
            # Return successful response with scraped content
            response_data = {
                "success": True,
                "data": result.to_dict(),
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "cached": cached,
                    "user_id": current_user.get('user_id'),
                    "word_count": result.word_count,
                    "has_author": bool(result.author),
                    "has_publish_date": bool(result.publish_date)
                }
            }

        logger.info(f"Scraping completed for {request.url}: {result.error and 'WARNING' or 'SUCCESS'}")
        return ScrapeUrlResponse(**response_data)

    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error for URL {request.url}: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_URL",
                "message": str(e),
                "url": str(request.url)
            }
        )

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error scraping URL {request.url}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during scraping",
                "details": str(e)
            }
        )


@router.post("/batch_scrape", response_model=BatchScrapeResponse)
async def batch_scrape_urls(
    request: BatchScrapeRequest,
    current_user: dict = Depends(require_authenticated_user)
) -> BatchScrapeResponse:
    """
    Scrape multiple URLs in sequence (respects rate limiting).

    Processes up to 10 URLs sequentially, applying rate limiting per domain.
    Returns individual results for each URL along with summary statistics.

    Args:
        request: Batch scrape request with list of URLs
        current_user: Authenticated user

    Returns:
        BatchScrapeResponse with individual results and summary

    Raises:
        HTTPException: For authentication or server errors
    """
    if not scraper_service:
        await initialize_services()

    if len(request.urls) > 10:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "TOO_MANY_URLS",
                "message": "Maximum 10 URLs allowed per batch request"
            }
        )

    start_time = asyncio.get_event_loop().time()

    try:
        logger.info(f"User {current_user.get('user_id')} batch scraping {len(request.urls)} URLs")

        # Convert URLs to strings and scrape
        url_strings = [str(url) for url in request.urls]
        results: List[ScrapedContent] = await scraper_service.batch_scrape(
            url_strings,
            force_refresh=request.force_refresh
        )

        # Convert results to dictionaries
        result_dicts = [result.to_dict() for result in results]

        # Calculate summary statistics
        successful = sum(1 for result in results if not result.error)
        failed = len(results) - successful
        total_words = sum(result.word_count or 0 for result in results)
        avg_time = sum(result.execution_time_ms or 0 for result in results) / len(results) if results else 0

        summary = {
            "total_urls": len(request.urls),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(request.urls) if request.urls else 0,
            "total_words": total_words,
            "average_time_ms": int(avg_time),
            "has_content": successful > 0
        }

        execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        response_data = {
            "success": successful > 0,
            "results": result_dicts,
            "summary": summary,
            "metadata": {
                "execution_time_ms": execution_time_ms,
                "user_id": current_user.get('user_id'),
                "urls_processed": len(url_strings)
            }
        }

        logger.info(f"Batch scraping completed: {successful}/{len(request.urls)} successful")
        return BatchScrapeResponse(**response_data)

    except Exception as e:
        logger.error(f"Unexpected error in batch scraping: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during batch scraping",
                "details": str(e)
            }
        )


@router.post("/fill_form", response_model=FormFillResponse)
async def fill_form(
    request: FormFillRequest,
    current_user: dict = Depends(require_authenticated_user)
) -> FormFillResponse:
    """
    Fill target form fields using Playwright automation and return audit data.
    """
    try:
        if not form_fill_service:
            await initialize_services()

        normalized_fields = [
            FormFieldInput(
                name=field.name,
                value=field.value,
                selector=field.selector,
                field_type=field.field_type,
                required=field.required,
            )
            for field in request.fields
        ]

        result = await form_fill_service.fill_form(
            str(request.url),
            normalized_fields,
            submit=request.submit,
            selector_strategy=request.selector_strategy,
            wait_after_submit_ms=request.wait_after_submit_ms,
            capture_screenshots=request.capture_screenshots,
        )

        response_data = FormFillResponseData(**result.to_dict())
        metadata = {
            "execution_time_ms": result.execution_time_ms,
            "user_id": current_user.get("user_id"),
            "warnings": result.warnings,
        }

        error_block = None
        if not result.success:
            error_block = {
                "code": "FORM_FILL_PARTIAL_FAILURE",
                "message": "One or more fields failed to fill",
                "fields_failed": result.fields_failed,
            }

        return FormFillResponse(
            success=result.success,
            data=response_data,
            error=error_block,
            metadata=metadata,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "FORM_FILL_VALIDATION_ERROR",
                "message": str(e),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"fill_form failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "FORM_FILL_ERROR",
                "message": "An unexpected error occurred during form filling",
                "details": str(e),
            },
        )


@router.post("/screenshot", response_model=ScreenshotResponse)
async def capture_screenshot(
    request: ScreenshotRequest,
    current_user: dict = Depends(require_authenticated_user)
) -> ScreenshotResponse:
    """
    Capture screenshot of a web page with configurable options.

    Supports full-page or viewport capture, PNG/JPEG formats, quality settings,
    CSS selector targeting, and custom viewport dimensions.

    Args:
        request: Screenshot request with URL and capture options
        current_user: Authenticated user

    Returns:
        ScreenshotResponse with base64 image data and metadata

    Raises:
        HTTPException: For authentication, validation, or capture errors
    """
    start_time = asyncio.get_event_loop().time()

    try:
        logger.info(f"User {current_user.get('user_id')} capturing screenshot of {request.url}")

        # Get browser manager instance
        browser_manager = await BrowserManager.get_instance()

        # Navigate to URL with specified wait strategy
        page = await browser_manager.navigate(
            str(request.url),
            wait_until=request.wait_strategy
        )

        try:
            # Capture screenshot with all options
            data_url = await browser_manager.screenshot_base64(
                page=page,
                full_page=request.full_page,
                format=request.format,
                quality=request.quality,
                selector=request.selector,
                width=request.width,
                height=request.height
            )

            # Extract base64 data (remove data URL prefix)
            base64_data = data_url.split(',')[1]
            file_size_bytes = len(base64_data) * 3 // 4  # Approximate size from base64

            execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            # Get viewport dimensions for response
            viewport = page.viewport_size or {"width": 1280, "height": 720}

            # Create success response
            response_data = ScreenshotResponseData(
                url=request.url,
                format=request.format,
                full_page=request.full_page,
                data_url=data_url,
                width=viewport["width"],
                height=viewport["height"],
                file_size_bytes=file_size_bytes,
                selector=request.selector,
                execution_time_ms=execution_time_ms
            )

            response = ScreenshotResponse(
                success=True,
                data=response_data,
                metadata={
                    "execution_time_ms": execution_time_ms,
                    "user_id": current_user.get('user_id'),
                    "capture_method": "element" if request.selector else "full_page" if request.full_page else "viewport",
                    "wait_strategy": request.wait_strategy
                }
            )

            logger.info(f"Screenshot captured successfully: {request.url} ({execution_time_ms}ms, {file_size_bytes} bytes)")
            return response

        finally:
            # Always clean up the page
            await browser_manager.close_page(page)

    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error for screenshot {request.url}: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "code": "SCREENSHOT_VALIDATION_ERROR",
                "message": str(e),
                "url": str(request.url)
            }
        )

    except Exception as e:
        # Screenshot capture errors
        execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        error_message = str(e).lower()

        # Categorize error types
        if "timeout" in error_message:
            error_code = "SCREENSHOT_TIMEOUT"
            status_code = 408
        elif "navigation" in error_message or "goto" in error_message:
            error_code = "SCREENSHOT_NAVIGATION_ERROR"
            status_code = 422
        elif "element not found" in error_message:
            error_code = "SCREENSHOT_ELEMENT_NOT_FOUND"
            status_code = 400
        else:
            error_code = "SCREENSHOT_CAPTURE_ERROR"
            status_code = 500

        logger.error(f"Screenshot capture failed for {request.url}: {e}")

        raise HTTPException(
            status_code=status_code,
            detail={
                "code": error_code,
                "message": f"Screenshot capture failed: {str(e)}",
                "url": str(request.url),
                "execution_time_ms": execution_time_ms
            }
        )


@router.get("/scrape_health")
async def scrape_health_check(
    current_user: dict = Depends(require_authenticated_user)
) -> Dict[str, Any]:
    """
    Health check for scraping services.

    Returns status of browser manager, cache, and overall system health.

    Args:
        current_user: Authenticated user

    Returns:
        Health check response with service status
    """
    try:
        health_status = {
            "healthy": True,
            "services": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Check browser manager
        try:
            browser_manager = await BrowserManager.get_instance()
            browser_healthy = await browser_manager.is_healthy()
            health_status["services"]["browser_manager"] = {
                "status": "healthy" if browser_healthy else "unhealthy",
                "memory_usage_mb": await browser_manager.check_memory()
            }
        except Exception as e:
            health_status["services"]["browser_manager"] = {
                "status": "error",
                "error": str(e)
            }

        # Check cache manager
        try:
            if cache_manager:
                # Simple cache test
                test_key = "health_check_test"
                await cache_manager.set(test_key, {"test": True}, ttl=1)
                test_result = await cache_manager.get(test_key)
                await cache_manager.delete(test_key)

                cache_healthy = test_result is not None
                health_status["services"]["cache_manager"] = {
                    "status": "healthy" if cache_healthy else "unhealthy"
                }
            else:
                health_status["services"]["cache_manager"] = {
                    "status": "not_initialized"
                }
        except Exception as e:
            health_status["services"]["cache_manager"] = {
                "status": "error",
                "error": str(e)
            }

        # Check scraper service
        try:
            if scraper_service:
                health_status["services"]["scraper_service"] = {
                    "status": "initialized"
                }
            else:
                health_status["services"]["scraper_service"] = {
                    "status": "not_initialized"
                }
        except Exception as e:
            health_status["services"]["scraper_service"] = {
                "status": "error",
                "error": str(e)
            }

        # Overall health determination
        all_healthy = all(
            service.get("status") == "healthy"
            for service in health_status["services"].values()
        )
        health_status["healthy"] = all_healthy

        return health_status

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Tool Registry Integration
# This would be called during application startup to register the tool

async def register_scrape_url_tool(tool_registry):
    """
    Register scrape_url tool in the tool registry.

    This function should be called during application startup to make the
    scrape_url tool available to the agent system.

    Args:
        tool_registry: Tool registry instance
    """
    try:
        tool_definition = {
            "name": "scrape_url",
            "description": "Scrape and extract clean content from web pages using Mozilla Readability",
            "parameters": {
                "url": {
                    "type": "string",
                    "description": "URL to scrape and extract content from",
                    "required": True
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Skip cache and force fresh scraping",
                    "default": False
                }
            },
            "returns": {
                "type": "object",
                "description": "Scraped content with metadata including title, author, publish_date, text_content, and markdown_content"
            },
            "endpoint": "/tools/scrape_url",
            "method": "POST",
            "auth_required": True
        }

        # Register the tool (implementation depends on tool_registry interface)
        await tool_registry.register_tool("scrape_url", tool_definition)

        logger.info("scrape_url tool registered successfully")

    except Exception as e:
        logger.error(f"Failed to register scrape_url tool: {e}")
        raise


async def register_fill_form_tool(tool_registry):
    """
    Register fill_form tool in the tool registry.

    Args:
        tool_registry: Tool registry instance
    """
    try:
        tool_definition = {
            "name": "fill_form",
            "description": "Populate web forms using Playwright automation with before/after audit artifacts",
            "parameters": {
                "url": {
                    "type": "string",
                    "description": "Target page containing the form",
                    "required": True,
                },
                "fields": {
                    "type": "object",
                    "description": "Map of field names to values (supports select/checkbox/radio metadata)",
                    "required": True,
                },
                "submit": {
                    "type": "boolean",
                    "description": "Submit the form after filling",
                    "default": False,
                },
            },
            "returns": {
                "type": "object",
                "description": "Audit payload containing filled/failed fields and screenshot artifacts",
            },
            "endpoint": "/tools/fill_form",
            "method": "POST",
            "auth_required": True,
            "category": "web_automation",
        }

        await tool_registry.register_tool("fill_form", tool_definition)
        logger.info("fill_form tool registered successfully")

    except Exception as e:
        logger.error(f"Failed to register fill_form tool: {e}")
        raise


async def register_screenshot_tool(tool_registry):
    """
    Register screenshot tool in the tool registry.

    Args:
        tool_registry: Tool registry instance
    """
    try:
        tool_definition = {
            "name": "screenshot",
            "description": "Capture screenshots of web pages with configurable format, quality, and targeting options",
            "parameters": {
                "url": {
                    "type": "string",
                    "description": "URL to capture screenshot from",
                    "required": True
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Capture full page or viewport only",
                    "default": True
                },
                "format": {
                    "type": "string",
                    "description": "Image format: PNG (lossless) or JPEG (compressed)",
                    "enum": ["png", "jpeg"],
                    "default": "png"
                },
                "quality": {
                    "type": "integer",
                    "description": "JPEG quality (1-100), only used for JPEG format",
                    "minimum": 1,
                    "maximum": 100
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to capture specific element instead of full page"
                },
                "width": {
                    "type": "integer",
                    "description": "Optional viewport width override (100-4000px)",
                    "minimum": 100,
                    "maximum": 4000
                },
                "height": {
                    "type": "integer",
                    "description": "Optional viewport height override (100-4000px)",
                    "minimum": 100,
                    "maximum": 4000
                },
                "wait_strategy": {
                    "type": "string",
                    "description": "Navigation wait strategy",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "default": "load"
                }
            },
            "returns": {
                "type": "object",
                "description": "Screenshot data including base64 image, dimensions, file size, and execution time"
            },
            "endpoint": "/tools/screenshot",
            "method": "POST",
            "auth_required": True,
            "category": "web_automation",
            "performance_target": "<5 seconds for typical pages"
        }

        await tool_registry.register_tool("screenshot", tool_definition)
        logger.info("screenshot tool registered successfully")

    except Exception as e:
        logger.error(f"Failed to register screenshot tool: {e}")
        raise


# Startup event to initialize services
async def startup_event():
    """Initialize services on application startup."""
    await initialize_services()


# Shutdown event to cleanup services
async def shutdown_event():
    """Cleanup services on application shutdown."""
    try:
        if scraper_service:
            logger.info("Cleaning up scraper service")
        if cache_manager:
            await cache_manager.close()
        browser_manager = await BrowserManager.get_instance()
        await browser_manager.cleanup()
        logger.info("Web tools services cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
