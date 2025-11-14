"""
Web Scraping API Router

Provides endpoints for web page scraping and content extraction.
Integrates with BrowserManager for headless browser automation.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import asyncio
import logging
import time
from datetime import datetime
import re
import html2text
from bs4 import BeautifulSoup
import readability
from readability import Document

from services.browser_manager import BrowserManager

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class ScrapeUrlRequest(BaseModel):
    """Request model for URL scraping."""
    url: HttpUrl
    wait_for_javascript: bool = True
    timeout_seconds: int = 10
    extract_metadata: bool = True


class ScrapeUrlResponse(BaseModel):
    """Response model for URL scraping results."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, str]] = None


class ContentExtractor:
    """
    Content extraction and cleaning utility.

    Uses readability-lxml for main content extraction and BeautifulSoup
    for HTML cleaning and metadata extraction.
    """

    def __init__(self):
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0  # No line wrapping
        self.html2text.protect_links = True
        self.html2text.unicode_snob = True

    def extract_content(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Extract clean content from HTML.

        Args:
            html_content: Raw HTML content
            url: Source URL for metadata

        Returns:
            Dictionary with extracted content and metadata
        """
        try:
            # Use readability for main content extraction
            doc = Document(html_content)

            # Extract main content
            summary_html = doc.summary()

            # Convert to markdown
            markdown_content = self.html2text.handle(summary_html)

            # Clean up markdown
            markdown_content = self._clean_markdown(markdown_content)

            # Extract metadata
            metadata = self._extract_metadata(html_content, url, doc)

            return {
                "text_content": markdown_content,
                "metadata": metadata,
                "raw_html_length": len(html_content),
                "content_length": len(markdown_content)
            }

        except Exception as e:
            logger.error(f"Content extraction failed: {e}")
            # Fallback to basic text extraction
            return self._fallback_extraction(html_content, url)

    def _clean_markdown(self, markdown: str) -> str:
        """Clean up markdown content."""
        # Remove excessive whitespace
        markdown = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown)
        # Remove leading/trailing whitespace from each line
        markdown = '\n'.join(line.strip() for line in markdown.split('\n'))
        # Remove empty lines at start and end
        markdown = markdown.strip()
        return markdown

    def _extract_metadata(self, html_content: str, url: str, doc: Document) -> Dict[str, Any]:
        """Extract metadata from HTML content."""
        metadata = {
            "title": doc.title(),
            "url": url,
            "extracted_at": datetime.utcnow().isoformat() + "Z"
        }

        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # Extract author
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta:
                metadata['author'] = author_meta.get('content', '').strip()

            # Extract publication date
            for attr in ['article:published_time', 'publication_date', 'date', 'created']:
                date_meta = soup.find('meta', attrs={'property': attr}) or \
                          soup.find('meta', attrs={'name': attr})
                if date_meta and date_meta.get('content'):
                    metadata['publish_date'] = date_meta.get('content').strip()
                    break

            # Extract description
            desc_meta = soup.find('meta', attrs={'name': 'description'}) or \
                       soup.find('meta', attrs={'property': 'og:description'})
            if desc_meta:
                metadata['description'] = desc_meta.get('content', '').strip()

            # Extract site name
            site_meta = soup.find('meta', attrs={'property': 'og:site_name'})
            if site_meta:
                metadata['site_name'] = site_meta.get('content', '').strip()

        except Exception as e:
            logger.warning(f"Metadata extraction partially failed: {e}")

        return metadata

    def _fallback_extraction(self, html_content: str, url: str) -> Dict[str, Any]:
        """Fallback extraction using basic BeautifulSoup parsing."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            # Extract text content
            text_content = soup.get_text()
            text_content = self._clean_markdown(text_content)

            # Basic metadata
            title = soup.title.string if soup.title else url
            metadata = {
                "title": title.strip(),
                "url": url,
                "extracted_at": datetime.utcnow().isoformat() + "Z",
                "extraction_method": "fallback"
            }

            return {
                "text_content": text_content,
                "metadata": metadata,
                "raw_html_length": len(html_content),
                "content_length": len(text_content)
            }

        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            raise


# Global content extractor instance
content_extractor = ContentExtractor()


@router.post("/tools/scrape_url", response_model=ScrapeUrlResponse)
async def scrape_url(request: ScrapeUrlRequest):
    """
    Scrape web page and extract clean content.

    Args:
        request: Scraping request with URL and options

    Returns:
        Extracted content in markdown format with metadata
    """
    start_time = time.time()

    try:
        # Validate and normalize URL
        url = str(request.url).strip()
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_URL", "message": "URL must start with http:// or https://"}
            )

        logger.info(f"Starting URL scrape: {url}")

        # Get browser manager instance
        browser_manager = await BrowserManager.get_instance()

        # Navigate to page
        wait_strategy = "load" if request.wait_for_javascript else "domcontentloaded"
        page = await browser_manager.navigate(url, wait_until=wait_strategy)

        try:
            # Wait for JavaScript to render if requested
            if request.wait_for_javascript:
                # Wait a moment for dynamic content to load
                await asyncio.sleep(2)

                # Check if page has meaningful content
                content_check = await page.evaluate("""
                    () => {
                        const body = document.body;
                        const text = body ? body.innerText || body.textContent || '' : '';
                        return {
                            has_content: text.length > 100,
                            content_length: text.length,
                            has_dynamic_elements: document.querySelectorAll('script, [data-src], [onclick]').length > 0
                        };
                    }
                """)

                if not content_check['has_content']:
                    logger.warning(f"Page may have insufficient content: {content_check}")

            # Extract page HTML
            html_content = await page.content()
            logger.info(f"Page loaded successfully: {len(html_content)} bytes")

            # Extract clean content
            extraction_result = content_extractor.extract_content(html_content, url)

            # Add performance metrics
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            extraction_result["performance"] = {
                "execution_time_ms": round(execution_time, 2),
                "navigation_time_ms": execution_time,  # For now, same as total
                "content_extraction_ms": 0  # Would need more detailed timing
            }

            # Validate 5-second performance requirement (AC7.3.5)
            if execution_time > 5000:
                logger.warning(f"Scraping exceeded 5s limit: {execution_time:.2f}ms")

            logger.info(f"Content extracted successfully in {execution_time:.2f}ms")

            return ScrapeUrlResponse(
                success=True,
                data=extraction_result
            )

        finally:
            # Always clean up page resources
            await browser_manager.close_page(page)

    except HTTPException:
        raise
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_message = str(e)

        # Categorize error types
        if "timeout" in error_message.lower():
            error_code = "NAVIGATION_FAILED"
            error_detail = f"Page navigation timed out after {request.timeout_seconds} seconds"
        elif "404" in error_message or "not found" in error_message.lower():
            error_code = "NAVIGATION_FAILED"
            error_detail = "Page not found (404 error)"
        elif "blocked" in error_message.lower() or "forbidden" in error_message.lower():
            error_code = "NAVIGATION_FAILED"
            error_detail = "Access to page blocked or forbidden"
        elif "content extraction" in error_message.lower():
            error_code = "CONTENT_EXTRACTION_FAILED"
            error_detail = "Failed to extract clean content from page"
        else:
            error_code = "BROWSER_ERROR"
            error_detail = "Browser automation error occurred"

        logger.error(f"URL scraping failed for {url}: {error_message}")

        return ScrapeUrlResponse(
            success=False,
            error={
                "code": error_code,
                "message": error_detail,
                "details": error_message,
                "execution_time_ms": round(execution_time, 2)
            }
        )


@router.get("/tools/scrape_url/health")
async def scrape_url_health():
    """Health check endpoint for scraping service."""
    try:
        browser_manager = await BrowserManager.get_instance()
        is_healthy = await browser_manager.is_healthy()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "scrape_url",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "browser_connected": is_healthy
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "scrape_url",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )