# Story 7-3: URL Scraping & Content Extraction

**Story ID:** 7-3-url-scraping-content-extraction
**Epic:** Epic 7 - Web Automation & Search
**Status:** completed
**Priority:** P0 (Foundation - Blocking)
**Estimated Effort:** 6 Story Points
**Sprint:** Sprint 7
**Owner:** TBD
**Created:** 2025-11-14

---

## User Story

**As a** Manus Internal system
**I want** intelligent URL content scraping and extraction capabilities
**So that** I can automatically extract clean article content, product information, and structured data from websites for knowledge ingestion and research tasks

---

## Context

This story implements the core content extraction functionality for Epic 7 (Web Automation & Search). Building on the Playwright browser automation from Story 7-1, this feature provides intelligent content scraping that can extract meaningful data from web pages while filtering out navigation, ads, and irrelevant content.

The content extraction system must handle diverse website structures including news articles, blog posts, product pages, documentation sites, and academic papers. Performance is critical: content extraction should complete in <3s for typical pages to maintain responsive user experience during research tasks.

### Why This Matters

Without intelligent content extraction, Manus cannot:
- Extract clean article text from news sites and blogs for knowledge ingestion
- Pull product information from e-commerce sites for market research
- Gather structured data from documentation sites for technical analysis
- Create searchable knowledge bases from web content
- Provide accurate citations for web-based research findings

This capability transforms Manus from a basic web browser into an intelligent research assistant that can understand and organize web content at scale.

---

## Technical Context

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Onyx Core (Python) - Content Extraction Layer         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  ContentExtractor: extract_content()             │ │
│  │  → clean_html() → extract_structured_data()      │ │
│  │  → detect_content_type() → format_output()       │ │
│  └───────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────┘
                         │ Browser API calls
                         ↓
┌─────────────────────────────────────────────────────────┐
│  Playwright Browser (Story 7-1)                       │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Browser Manager: navigate() → page.content()    │ │
│  │  Screenshot capture for visual verification       │ │
│  │  JavaScript rendering for dynamic content          │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Key Components

1. **Content Extractor** (`onyx-core/services/content_extractor.py`):
   - Main service for intelligent content extraction
   - Content type detection (article, product, documentation, etc.)
   - HTML cleaning and content extraction algorithms
   - Structured data extraction (titles, authors, dates, etc.)
   - Output formatting (JSON, markdown, plain text)

2. **HTML Processing Engine**:
   - Readability algorithm for content detection
   - Boilerplate removal (ads, navigation, footers)
   - Image and media extraction with alt-text
   - Link extraction and categorization
   - Metadata extraction (Open Graph, JSON-LD, microformats)

3. **Content Type Handlers**:
   - Article extractor (news, blogs, publications)
   - Product extractor (e-commerce, pricing)
   - Documentation extractor (technical docs, APIs)
   - Academic extractor (papers, research)
   - Generic extractor (fallback for unknown types)

4. **Quality Assurance**:
   - Content quality scoring
   - Duplicate content detection
   - Language detection
   - Spam and low-quality content filtering

### Performance Targets

| Operation | Target | Timeout | Notes |
|-----------|--------|---------|-------|
| Content extraction | <2s | 5s | Typical article page |
| Structured data extraction | <3s | 8s | Complex pages with multiple data types |
| Image extraction | <1s | 3s | Per image processing |
| Quality scoring | <500ms | 2s | Content assessment |

### Content Types Supported

| Type | Detection Method | Data Extracted |
|------|------------------|----------------|
| Article | URL patterns, content density | Title, author, date, body, summary |
| Product | Structured data, price patterns | Name, price, description, images, specs |
| Documentation | URL patterns, TOC detection | Title, sections, code examples |
| Academic | Citation patterns, abstracts | Title, authors, abstract, citations |
| Social Media | URL patterns, metadata | Post content, author, timestamp |

---

## Acceptance Criteria

### AC7.3.1: Extract Clean Article Content from News/Blog Sites
**Given** a URL points to a news article or blog post
**When** the system calls `extract_content(url, type="article")`
**Then** it returns clean article content with title, author, date, and body text
**And** navigation, ads, and boilerplate content are removed
**And** the content is formatted as structured JSON with metadata

**Verification:**
- Test with URLs from news sites (CNN, BBC, etc.)
- Test with blog posts from various platforms
- Verify boilerplate removal (no navigation menus, ads)
- Verify structured output with title/author/date fields
- Test content quality scoring >0.7 for legitimate articles

---

### AC7.3.2: Extract Product Information from E-commerce Pages
**Given** a URL points to an e-commerce product page
**When** the system calls `extract_content(url, type="product")`
**Then** it returns product details including name, price, description, images, and specifications
**And** structured data includes availability, variants, and reviews count
**And** currency and pricing information are normalized

**Verification:**
- Test with Amazon product pages
- Test with Shopify stores
- Verify price extraction with currency normalization
- Test image extraction with alt-text descriptions
- Verify specification parsing (technical specs, dimensions)

---

### AC7.3.3: Extract Structured Data from Documentation Sites
**Given** a URL points to technical documentation
**When** the system calls `extract_content(url, type="documentation")`
**Then** it returns document structure with sections, subsections, and code examples
**And** code blocks are extracted with language detection
**And** navigation menus are preserved as document structure

**Verification:**
- Test with API documentation (Swagger, OpenAPI)
- Test with technical docs (GitHub Pages, GitBook)
- Verify code block extraction with syntax highlighting hints
- Test TOC generation and section hierarchy
- Verify link extraction for internal navigation

---

### AC7.3.4: Extract Academic Content with Citations
**Given** a URL points to an academic paper or research article
**When** the system calls `extract_content(url, type="academic")`
**Then** it returns structured content with title, authors, abstract, and citations
**And** citation formatting is preserved (APA, MLA, etc.)
**And** references section is extracted and categorized

**Verification:**
- Test with arXiv papers
- Test with university research pages
- Verify author extraction and affiliation detection
- Test abstract identification and extraction
- Verify citation parsing and reference extraction

---

### AC7.3.5: Automatic Content Type Detection
**Given** a URL without explicit content type
**When** the system calls `extract_content(url)` without type parameter
**Then** it automatically detects the content type based on URL patterns and page analysis
**And** applies the appropriate extraction strategy
**And** returns the detected type in the response metadata

**Verification:**
- Test detection accuracy across 50 different URL types
- Verify news site detection (>90% accuracy)
- Verify e-commerce detection (>85% accuracy)
- Verify documentation detection (>90% accuracy)
- Test fallback to generic extraction for unknown types

---

### AC7.3.6: Content Quality Assessment and Filtering
**Given** extracted content from any URL
**When** the content extraction completes
**Then** a quality score (0-1) is calculated based on content length, readability, and structure
**And** low-quality content (<0.3) is flagged for manual review
**And** duplicate content is detected across multiple extractions

**Verification:**
- Test quality scoring on known good vs. bad content
- Verify spam content detection and flagging
- Test duplicate detection across similar articles
- Verify readability scoring (Flesch-Kincaid, etc.)
- Test content length validation (minimum requirements)

---

## Implementation Details

### Step 1: Content Extractor Service

**File:** `onyx-core/services/content_extractor.py`

```python
import asyncio
import logging
from typing import Dict, List, Optional, Any, Literal
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup, Comment
import html2text
from readability import Document
from datetime import datetime
import hashlib

from .browser_manager import BrowserManager

logger = logging.getLogger(__name__)

class ContentExtractor:
    """Intelligent content extraction from web pages."""

    def __init__(self, browser_manager: BrowserManager):
        self.browser_manager = browser_manager
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0  # No line wrapping

        # Content type patterns
        self.type_patterns = {
            'article': [
                r'/article/', r'/news/', r'/blog/', r'/post/',
                r'.*/news\.', r'.*/blog\.', r'.*/article\.',
                r'medium\.com', r'substack\.com'
            ],
            'product': [
                r'/product/', r'/item/', r'/p/', r'/buy/',
                r'amazon\.com', r'etsy\.com', r'shopify\.com'
            ],
            'documentation': [
                r'/docs/', r'/api/', r'/guide/', r'/tutorial/',
                r'readthedocs\.io', r'github\.io/docs'
            ],
            'academic': [
                r'/paper/', r'/research/', r'/publication/',
                r'arxiv\.org', r'scholar\.google\.com'
            ]
        }

    async def extract_content(
        self,
        url: str,
        content_type: Optional[Literal["article", "product", "documentation", "academic"]] = None,
        extract_images: bool = True,
        extract_links: bool = True
    ) -> Dict[str, Any]:
        """Extract structured content from a URL."""
        logger.info(f"Extracting content from {url}")

        # Auto-detect content type if not provided
        if content_type is None:
            content_type = self._detect_content_type(url)
            logger.info(f"Auto-detected content type: {content_type}")

        # Navigate to page
        page = await self.browser_manager.navigate(url)

        try:
            # Get page HTML
            html = await page.content()

            # Extract content based on type
            if content_type == "article":
                result = await self._extract_article(html, url)
            elif content_type == "product":
                result = await self._extract_product(html, url)
            elif content_type == "documentation":
                result = await self._extract_documentation(html, url)
            elif content_type == "academic":
                result = await self._extract_academic(html, url)
            else:
                result = await self._extract_generic(html, url)

            # Add common metadata
            result.update({
                'url': url,
                'content_type': content_type,
                'extracted_at': datetime.utcnow().isoformat(),
                'quality_score': self._calculate_quality_score(result),
                'content_hash': hashlib.md5(result.get('content', '').encode()).hexdigest()
            })

            # Extract images and links if requested
            if extract_images:
                result['images'] = await self._extract_images(page)

            if extract_links:
                result['links'] = await self._extract_links(page)

            logger.info(f"Content extraction complete: {len(result.get('content', ''))} characters")
            return result

        finally:
            await self.browser_manager.close_page(page)

    def _detect_content_type(self, url: str) -> str:
        """Auto-detect content type from URL patterns."""
        url_lower = url.lower()

        for content_type, patterns in self.type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return content_type

        return 'generic'

    async def _extract_article(self, html: str, url: str) -> Dict[str, Any]:
        """Extract article content with readability algorithm."""
        doc = Document(html)

        # Use readability for main content
        summary = doc.summary()
        title = doc.title()

        # Parse with BeautifulSoup for detailed extraction
        soup = BeautifulSoup(summary, 'html.parser')

        # Extract structured data
        content = self.html2text.handle(summary)

        # Try to extract metadata
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup)

        return {
            'title': title,
            'author': author,
            'publish_date': publish_date,
            'content': content.strip(),
            'word_count': len(content.split()),
            'reading_time': self._estimate_reading_time(content)
        }

    async def _extract_product(self, html: str, url: str) -> Dict[str, Any]:
        """Extract product information from e-commerce pages."""
        soup = BeautifulSoup(html, 'html.parser')

        # Extract product name (try multiple selectors)
        name = (self._extract_by_selectors(soup, [
            'h1.product-title', '.product-name', '#productTitle',
            'h1', '[data-product-title]'
        ]) or '').strip()

        # Extract price
        price = self._extract_price(soup)

        # Extract description
        description = self._extract_by_selectors(soup, [
            '.product-description', '#feature-bullets',
            '.product-details', '[data-product-description]'
        ])

        # Extract images
        images = self._extract_product_images(soup)

        # Extract specifications
        specs = self._extract_specifications(soup)

        return {
            'name': name,
            'price': price,
            'description': self.html2text.handle(description or '').strip() if description else '',
            'images': images,
            'specifications': specs,
            'availability': self._extract_availability(soup)
        }

    async def _extract_documentation(self, html: str, url: str) -> Dict[str, Any]:
        """Extract structured documentation content."""
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title = self._extract_by_selectors(soup, ['h1', '.page-title', 'title'])

        # Extract table of contents
        toc = self._extract_table_of_contents(soup)

        # Extract sections
        sections = self._extract_sections(soup)

        # Extract code examples
        code_examples = self._extract_code_examples(soup)

        return {
            'title': title or '',
            'table_of_contents': toc,
            'sections': sections,
            'code_examples': code_examples,
            'content': self._extract_main_content(soup)
        }

    async def _extract_academic(self, html: str, url: str) -> Dict[str, Any]:
        """Extract academic paper content."""
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title = self._extract_by_selectors(soup, [
            '.paper-title', '.article-title', 'h1'
        ])

        # Extract authors
        authors = self._extract_authors(soup)

        # Extract abstract
        abstract = self._extract_abstract(soup)

        # Extract citations
        citations = self._extract_citations(soup)

        # Extract main content
        content = self._extract_main_content(soup)

        return {
            'title': title or '',
            'authors': authors,
            'abstract': abstract,
            'citations': citations,
            'content': content,
            'citation_count': len(citations)
        }

    async def _extract_generic(self, html: str, url: str) -> Dict[str, Any]:
        """Generic content extraction fallback."""
        soup = BeautifulSoup(html, 'html.parser')

        # Use readability as fallback
        doc = Document(html)

        return {
            'title': doc.title(),
            'content': self.html2text.handle(doc.summary()).strip(),
            'word_count': len(doc.summary().split())
        }

    async def _extract_images(self, page) -> List[Dict[str, Any]]:
        """Extract images with metadata."""
        images = []
        img_elements = await page.query_selector_all('img')

        for img in img_elements:
            src = await img.get_attribute('src')
            alt = await img.get_attribute('alt')
            title = await img.get_attribute('title')

            if src:
                images.append({
                    'src': src,
                    'alt': alt or '',
                    'title': title or '',
                    'width': await img.get_attribute('width'),
                    'height': await img.get_attribute('height')
                })

        return images

    async def _extract_links(self, page) -> List[Dict[str, Any]]:
        """Extract links with categorization."""
        links = []
        link_elements = await page.query_selector_all('a[href]')

        for link in link_elements:
            href = await link.get_attribute('href')
            text = await link.inner_text()

            if href and text.strip():
                links.append({
                    'href': href,
                    'text': text.strip(),
                    'is_external': href.startswith(('http://', 'https://')),
                    'domain': urlparse(href).netloc if href.startswith(('http://', 'https://')) else ''
                })

        return links

    def _calculate_quality_score(self, content: Dict[str, Any]) -> float:
        """Calculate content quality score (0-1)."""
        score = 0.0

        # Content length score (0-0.3)
        content_length = len(content.get('content', ''))
        if content_length > 1000:
            score += 0.3
        elif content_length > 500:
            score += 0.2
        elif content_length > 100:
            score += 0.1

        # Structure score (0-0.3)
        if content.get('title'):
            score += 0.1
        if content.get('content_type') != 'generic':
            score += 0.1
        if 'sections' in content or 'specifications' in content:
            score += 0.1

        # Readability score (0-0.2)
        text = content.get('content', '')
        if text:
            # Simple readability metrics
            sentences = text.count('.') + text.count('!') + text.count('?')
            words = len(text.split())
            if sentences > 0:
                avg_words_per_sentence = words / sentences
                if 10 <= avg_words_per_sentence <= 20:
                    score += 0.2
                elif 5 <= avg_words_per_sentence <= 30:
                    score += 0.1

        # Metadata completeness (0-0.2)
        metadata_fields = ['author', 'publish_date', 'word_count']
        complete_fields = sum(1 for field in metadata_fields if field in content and content[field])
        score += (complete_fields / len(metadata_fields)) * 0.2

        return min(score, 1.0)

    def _estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes."""
        words = len(content.split())
        return max(1, round(words / 200))  # Average 200 words per minute
```

### Step 2: Integration Tests

**File:** `onyx-core/tests/integration/test_content_extractor.py`

```python
import pytest
from services.content_extractor import ContentExtractor
from services.browser_manager import BrowserManager

@pytest.mark.asyncio
async def test_article_extraction():
    """Test article content extraction."""
    browser_manager = await BrowserManager.get_instance()
    extractor = ContentExtractor(browser_manager)

    result = await extractor.extract_content(
        'https://example.com/article',  # Use test URL
        content_type='article'
    )

    assert result['content_type'] == 'article'
    assert 'title' in result
    assert 'content' in result
    assert len(result['content']) > 100
    assert result['quality_score'] > 0.0
    assert 'extracted_at' in result

@pytest.mark.asyncio
async def test_product_extraction():
    """Test product information extraction."""
    browser_manager = await BrowserManager.get_instance()
    extractor = ContentExtractor(browser_manager)

    result = await extractor.extract_content(
        'https://example.com/product',
        content_type='product'
    )

    assert result['content_type'] == 'product'
    assert 'name' in result
    assert 'price' in result or 'description' in result
    assert 'images' in result

@pytest.mark.asyncio
async def test_auto_content_type_detection():
    """Test automatic content type detection."""
    browser_manager = await BrowserManager.get_instance()
    extractor = ContentExtractor(browser_manager)

    # Test news article detection
    result = await extractor.extract_content(
        'https://example.com/news/article-test'
    )

    assert result['content_type'] in ['article', 'generic']
    assert 'quality_score' in result

@pytest.mark.asyncio
async def test_content_quality_scoring():
    """Test content quality assessment."""
    browser_manager = await BrowserManager.get_instance()
    extractor = ContentExtractor(browser_manager)

    result = await extractor.extract_content(
        'https://example.com/article',
        content_type='article'
    )

    # Quality score should be between 0 and 1
    assert 0.0 <= result['quality_score'] <= 1.0

@pytest.mark.asyncio
async def test_image_and_link_extraction():
    """Test image and link extraction."""
    browser_manager = await BrowserManager.get_instance()
    extractor = ContentExtractor(browser_manager)

    result = await extractor.extract_content(
        'https://example.com/article',
        extract_images=True,
        extract_links=True
    )

    assert 'images' in result
    assert 'links' in result
    assert isinstance(result['images'], list)
    assert isinstance(result['links'], list)

@pytest.mark.asyncio
async def test_performance_targets():
    """Test content extraction performance."""
    import time

    browser_manager = await BrowserManager.get_instance()
    extractor = ContentExtractor(browser_manager)

    start_time = time.time()
    result = await extractor.extract_content(
        'https://example.com/article',
        content_type='article'
    )
    extraction_time = time.time() - start_time

    # Should complete within 3 seconds for typical content
    assert extraction_time < 3.0
    assert len(result['content']) > 0
```

### Step 3: HTML Processing Dependencies

**File:** `onyx-core/requirements.txt` (additions)

```python
# HTML processing and content extraction
beautifulsoup4==4.12.0
html2text==2020.1.16
readability-lxml==0.8.1
lxml==4.9.0
python-dateutil==2.8.2
```

---

## Dependencies

### Blocking Dependencies
- **Story 7-1**: Playwright Browser Setup - Must be completed and approved
- **Environment**: Python libraries for HTML processing (BeautifulSoup, readability)

### External Dependencies
- **BeautifulSoup4**: HTML parsing and content extraction
- **html2text**: HTML to text conversion
- **readability-lxml**: Content extraction algorithm
- **lxml**: XML/HTML parsing performance

### Package Dependencies

```python
# requirements.txt additions
beautifulsoup4==4.12.0
html2text==2020.1.16
readability-lxml==0.8.1
lxml==4.9.0
python-dateutil==2.8.2
```

---

## Testing Strategy

### Unit Tests
- Content type detection accuracy
- HTML parsing and cleaning
- Metadata extraction (titles, authors, dates)
- Price parsing and currency normalization
- Quality scoring algorithm
- Duplicate content detection

### Integration Tests
- End-to-end content extraction with real URLs
- Integration with Browser Manager from Story 7-1
- Content type auto-detection accuracy
- Performance benchmarks (<3s extraction time)
- Image and link extraction functionality

### Manual Verification
- Test with real news sites (CNN, BBC, etc.)
- Test with e-commerce sites (Amazon, Etsy, etc.)
- Test with documentation sites (GitHub Pages, etc.)
- Verify content quality assessment
- Test edge cases (broken pages, missing content)

### Performance Tests
- Content extraction latency measurement
- Memory usage during extraction
- Concurrent extraction handling
- Large document processing performance

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Anti-bot detection** | Medium | Rotate user agents, rate limiting, respectful crawling |
| **Complex JavaScript sites** | Medium | Ensure Playwright renders JS before extraction |
| **Paywall content** | Low | Detect paywalls and handle gracefully |
| **Broken HTML structures** | Medium | Robust HTML parsing with fallback strategies |
| **Performance degradation** | Medium | Set timeouts, implement caching for repeated extractions |

---

## Definition of Done

- [ ] Content Extractor service implemented with all extraction methods
- [ ] HTML processing dependencies installed and configured
- [ ] All 6 acceptance criteria verified and passing
- [ ] Unit tests: >90% coverage of content_extractor.py
- [ ] Integration tests: Content extraction workflows passing
- [ ] Performance tests: <3s extraction time for typical pages
- [ ] Quality scoring: Algorithm validates known good vs. bad content
- [ ] Documentation: Content Extractor API documented in code
- [ ] Code review: Approved by senior engineer
- [ ] Merged to main branch and deployed to staging

---

## Notes

### Content Type Detection Strategy
- Primary: URL pattern matching (fast, accurate for common sites)
- Secondary: HTML structure analysis (headings, content density)
- Tertiary: Machine learning classification (future enhancement)

### Extraction Algorithm Priority
1. **Readability Algorithm** (primary): Proven content extraction
2. **Structured Data**: JSON-LD, microformats, Open Graph
3. **Heuristic Methods**: CSS selectors, content density analysis
4. **Fallback**: Basic text extraction with cleaning

### Performance Optimization
- Cache extracted content for repeated URLs
- Parallel image processing (independent of text extraction)
- Incremental quality scoring (early exit for obviously bad content)
- Browser page reuse when possible

### Security Considerations
- No execution of JavaScript from extracted content
- Sanitization of extracted HTML
- Rate limiting for domain-specific extractions
- Input validation for URLs and parameters

---

## Related Stories

- **Story 7-1**: Playwright Browser Setup - **DEPENDENCY** (must be completed first)
- **Story 7-2**: Web Search Tool (SerpAPI or Exa) - Independent
- **Story 7-4**: Form Filling & Web Interaction - Independent
- **Story 7-5**: Screenshot & Page Capture - Independent

---

## References

- Epic 7 Technical Specification: `/docs/epics/epic-7-tech-spec.md`
- PRD Section F6: Web Automation & Search
- Readability.js Algorithm: Mozilla's content extraction approach
- BeautifulSoup Documentation: HTML parsing best practices

---

## Development Notes

### Implementation Start

This story is ready for development once Story 7-1 (Playwright Browser Setup) is approved and merged. The ContentExtractor service builds directly on the BrowserManager foundation and requires stable browser automation capabilities.

### Next Steps After Implementation

1. **Integration with Knowledge Base**: Feed extracted content into Qdrant vector database
2. **Content Classification**: Use extracted metadata for automatic categorization
3. **Citation System**: Link extracted content back to source URLs for reference
4. **Batch Processing**: Process multiple URLs efficiently for research tasks

### Testing URLs for Development

**Article Sites:**
- https://example.com/article
- Medium articles
- News sites for testing

**Product Sites:**
- Amazon product pages
- Shopify stores
- Product documentation

**Documentation Sites:**
- GitHub Pages sites
- API documentation
- Technical tutorials

---

**Story Created:** 2025-11-14
**Status:** Drafted - Ready for Context Generation
**Next Step:** Execute story-context workflow to generate project context