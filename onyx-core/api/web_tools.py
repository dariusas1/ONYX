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
from typing import Optional, List, Dict, Any
import logging
import asyncio
from datetime import datetime

from services.scraper_service import ScraperService, ScrapedContent
from services.cache_manager import CacheManager
from services.browser_manager import BrowserManager
from services.auth import require_authenticated_user  # Assuming auth exists

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/tools", tags=["web-tools"])

# Global service instances (initialized on startup)
scraper_service: Optional[ScraperService] = None
cache_manager: Optional[CacheManager] = None


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


# Service Initialization

async def initialize_services():
    """Initialize global service instances."""
    global scraper_service, cache_manager

    try:
        # Initialize cache manager
        cache_manager = CacheManager()

        # Initialize scraper service
        scraper_service = ScraperService(cache_manager=cache_manager)

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