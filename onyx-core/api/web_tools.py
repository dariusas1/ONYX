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