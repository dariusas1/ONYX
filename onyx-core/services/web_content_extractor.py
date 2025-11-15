"""
Web Content Extractor Service

This module provides intelligent content extraction from web pages using Playwright
browser automation and advanced HTML processing algorithms.

Key Features:
- Intelligent content type detection (article, product, documentation, academic)
- Readability algorithm for clean content extraction
- Structured data extraction (titles, authors, dates, pricing, specifications)
- Content quality scoring and duplicate detection
- Image and link extraction with metadata
- Performance optimization with <3s extraction targets

Content Types Supported:
- Article: News articles, blog posts, publications
- Product: E-commerce pages with pricing and specifications
- Documentation: Technical docs, API documentation, tutorials
- Academic: Research papers, citations, references
- Generic: Fallback for unknown content types

Performance Targets:
- Content extraction: <2s for typical pages
- Structured data extraction: <3s for complex pages
- Quality scoring: <500ms
- Browser cleanup: <500ms
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Literal, Union
from urllib.parse import urlparse
import re
import hashlib
from datetime import datetime
import time

# HTML processing libraries
from bs4 import BeautifulSoup, Comment
import html2text
from readability import Document

# Playwright browser automation
from playwright.async_api import Page

# Import browser manager
from .browser_manager import BrowserManager

# Configure logging
logger = logging.getLogger(__name__)


class WebContentExtractor:
    """
    Intelligent web content extraction service.

    Provides comprehensive content extraction from web pages with support for
    multiple content types, quality assessment, and structured data extraction.
    """

    def __init__(self, browser_manager: BrowserManager):
        """
        Initialize the web content extractor.

        Args:
            browser_manager: Instance of BrowserManager for browser automation
        """
        self.browser_manager = browser_manager

        # Configure HTML to text converter
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0  # No line wrapping
        self.html2text.unicode_snob = True
        self.html2text.skip_internal_links = False

        # Content type detection patterns
        self.type_patterns = {
            'article': [
                r'/article/', r'/news/', r'/blog/', r'/post/', r'/story/',
                r'.*/news\.', r'.*/blog\.', r'.*/article\.', r'.*/post\.',
                r'medium\.com', r'substack\.com', r'wordpress\.com',
                r'github\.com/.*issues/', r'github\.com/.*discussions/'
            ],
            'product': [
                r'/product/', r'/item/', r'/p/', r'/buy/', r'/shop/',
                r'amazon\.com/', r'amazon\.', r'etsy\.com', r'shopify\.com',
                r'ebay\.com', r'aliexpress\.com', r'target\.com',
                r'walmart\.com', r'bestbuy\.com'
            ],
            'documentation': [
                r'/docs/', r'/api/', r'/guide/', r'/tutorial/', r'/reference/',
                r'readthedocs\.io', r'github\.io/docs', r'gitbook\.com',
                r'docs\.python\.org', r'developer\.mozilla\.org',
                r'stackoverflow\.com', r'dev\.docs\.io'
            ],
            'academic': [
                r'/paper/', r'/research/', r'/publication/', r'/scholar/',
                r'arxiv\.org', r'scholar\.google\.com', r'pubmed\.ncbi\.nlm\.nih\.gov',
                r'ieee\.org', r'acm\.org', r'springer\.com', r'sciencedirect\.com'
            ]
        }

        # Product price patterns
        self.price_patterns = [
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 1,234.56 USD
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*\$',     # 1,234.56$
            r'USD\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',     # USD 1,234.56
            r'€\s*(\d+(?:\.\d{3})*(?:,\d{2})?)',       # €1.234,56
            r'(\d+(?:\.\d{3})*(?:,\d{2})?)\s*€',       # 1.234,56€
            r'£\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',       # £1,234.56
        ]

    async def extract_content(
        self,
        url: str,
        content_type: Optional[Literal["article", "product", "documentation", "academic"]] = None,
        extract_images: bool = True,
        extract_links: bool = True,
        extract_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Extract structured content from a URL.

        Args:
            url: URL to extract content from
            content_type: Optional content type hint (auto-detected if not provided)
            extract_images: Whether to extract images
            extract_links: Whether to extract links
            extract_metadata: Whether to extract detailed metadata

        Returns:
            Dictionary containing extracted content and metadata
        """
        start_time = time.time()
        logger.info(f"Starting content extraction for {url}")

        try:
            # Auto-detect content type if not provided
            if content_type is None:
                content_type = self._detect_content_type(url)
                logger.info(f"Auto-detected content type: {content_type}")

            # Navigate to page
            page = await self.browser_manager.navigate(url)

            try:
                # Get page HTML after JavaScript rendering
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
                extraction_time = (time.time() - start_time) * 1000
                common_metadata = {
                    'url': url,
                    'content_type': content_type,
                    'extracted_at': datetime.utcnow().isoformat(),
                    'extraction_time_ms': round(extraction_time, 2),
                    'quality_score': self._calculate_quality_score(result),
                    'content_hash': hashlib.md5(result.get('content', '').encode()).hexdigest()
                }

                result.update(common_metadata)

                # Extract optional content
                if extract_images:
                    result['images'] = await self._extract_images(page)

                if extract_links:
                    result['links'] = await self._extract_links(page)

                if extract_metadata:
                    result['metadata'] = await self._extract_page_metadata(page, html)

                logger.info(f"Content extraction complete: {len(result.get('content', ''))} characters in {extraction_time:.0f}ms")
                return result

            finally:
                # Ensure page cleanup
                await self.browser_manager.close_page(page)

        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            extraction_time = (time.time() - start_time) * 1000
            return {
                'url': url,
                'content_type': content_type or 'unknown',
                'error': str(e),
                'content': '',
                'extracted_at': datetime.utcnow().isoformat(),
                'extraction_time_ms': round(extraction_time, 2),
                'quality_score': 0.0,
                'success': False
            }

    def _detect_content_type(self, url: str) -> str:
        """
        Auto-detect content type from URL patterns and domain analysis.

        Args:
            url: URL to analyze

        Returns:
            Detected content type
        """
        url_lower = url.lower()

        # Check against known patterns
        for content_type, patterns in self.type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return content_type

        return 'generic'

    async def _extract_article(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract article content with readability algorithm.

        Args:
            html: HTML content of the page
            url: Source URL

        Returns:
            Dictionary containing article content and metadata
        """
        # Apply readability algorithm for main content
        doc = Document(html)

        # Extract main content and title
        summary = doc.summary()
        title = doc.title()

        # Parse with BeautifulSoup for detailed extraction
        soup = BeautifulSoup(summary, 'html.parser')

        # Convert to clean markdown
        content = self.html2text.handle(summary)

        # Extract structured metadata
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup, html)
        summary_text = self._extract_summary(soup)

        return {
            'title': title or '',
            'author': author or '',
            'publish_date': publish_date,
            'summary': summary_text,
            'content': content.strip(),
            'word_count': len(content.split()),
            'reading_time_minutes': max(1, round(len(content.split()) / 200)),  # 200 words/min
            'content_type': 'article'
        }

    async def _extract_product(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract product information from e-commerce pages.

        Args:
            html: HTML content of the page
            url: Source URL

        Returns:
            Dictionary containing product information
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Extract product name with multiple selectors
        name_selectors = [
            'h1.product-title', '.product-name', '#productTitle',
            'h1', '[data-product-title]', '.product-title h1',
            '.pdp-title', '.item-title', '.product-page-title'
        ]
        name = self._extract_by_selectors(soup, name_selectors)

        # Extract price with currency normalization
        price_info = self._extract_price_with_currency(soup)

        # Extract description
        desc_selectors = [
            '.product-description', '#feature-bullets',
            '.product-details', '[data-product-description]',
            '.item-description', '.description', '.summary'
        ]
        description_raw = self._extract_by_selectors(soup, desc_selectors)
        description = self.html2text.handle(description_raw or '').strip() if description_raw else ''

        # Extract specifications
        specs = self._extract_specifications(soup)

        # Extract images with product-specific attributes
        images = self._extract_product_images(soup)

        # Extract availability and reviews
        availability = self._extract_availability(soup)
        reviews = self._extract_review_count(soup)

        return {
            'name': name or '',
            'price': price_info['price'],
            'currency': price_info['currency'],
            'price_formatted': price_info['formatted'],
            'description': description,
            'images': images,
            'specifications': specs,
            'availability': availability,
            'review_count': reviews,
            'content_type': 'product'
        }

    async def _extract_documentation(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract structured documentation content.

        Args:
            html: HTML content of the page
            url: Source URL

        Returns:
            Dictionary containing documentation structure and content
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title_selectors = ['h1', '.page-title', 'title', '.documentation-title']
        title = self._extract_by_selectors(soup, title_selectors)

        # Extract table of contents
        toc = self._extract_table_of_contents(soup)

        # Extract sections with hierarchy
        sections = self._extract_sections(soup)

        # Extract code examples
        code_examples = self._extract_code_examples(soup)

        # Extract main content (fallback)
        main_content = self._extract_main_content(soup)

        return {
            'title': title or '',
            'table_of_contents': toc,
            'sections': sections,
            'code_examples': code_examples,
            'content': main_content,
            'section_count': len(sections),
            'code_example_count': len(code_examples),
            'content_type': 'documentation'
        }

    async def _extract_academic(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract academic paper content.

        Args:
            html: HTML content of the page
            url: Source URL

        Returns:
            Dictionary containing academic paper structure and content
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title_selectors = [
            '.paper-title', '.article-title', 'h1',
            '.abstract h1', '.paper h1'
        ]
        title = self._extract_by_selectors(soup, title_selectors)

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
            'citation_count': len(citations),
            'content': content,
            'author_count': len(authors),
            'content_type': 'academic'
        }

    async def _extract_generic(self, html: str, url: str) -> Dict[str, Any]:
        """
        Generic content extraction fallback.

        Args:
            html: HTML content of the page
            url: Source URL

        Returns:
            Dictionary containing basic content extraction
        """
        # Use readability as fallback
        doc = Document(html)
        content = self.html2text.handle(doc.summary()).strip()

        return {
            'title': doc.title() or '',
            'content': content,
            'word_count': len(content.split()),
            'reading_time_minutes': max(1, round(len(content.split()) / 200)),
            'content_type': 'generic'
        }

    async def _extract_images(self, page: Page) -> List[Dict[str, Any]]:
        """Extract images with metadata."""
        images = []
        try:
            img_elements = await page.query_selector_all('img')

            for img in img_elements:
                try:
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt')
                    title = await img.get_attribute('title')
                    width = await img.get_attribute('width')
                    height = await img.get_attribute('height')

                    if src and src.strip():
                        images.append({
                            'src': src.strip(),
                            'alt': alt or '',
                            'title': title or '',
                            'width': width,
                            'height': height,
                            'is_product_image': self._is_product_image(src, alt or '')
                        })
                except Exception as e:
                    logger.debug(f"Error extracting image: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error extracting images: {e}")

        return images

    async def _extract_links(self, page: Page) -> List[Dict[str, Any]]:
        """Extract links with categorization."""
        links = []
        try:
            link_elements = await page.query_selector_all('a[href]')

            for link in link_elements:
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()

                    if href and text.strip():
                        parsed_url = urlparse(href)
                        links.append({
                            'href': href,
                            'text': text.strip(),
                            'is_external': href.startswith(('http://', 'https://')),
                            'domain': parsed_url.netloc if href.startswith(('http://', 'https://')) else '',
                            'is_navigation': self._is_navigation_link(href, text),
                            'is_download': self._is_download_link(href)
                        })
                except Exception as e:
                    logger.debug(f"Error extracting link: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error extracting links: {e}")

        return links

    async def _extract_page_metadata(self, page: Page, html: str) -> Dict[str, Any]:
        """Extract comprehensive page metadata."""
        metadata = {}

        try:
            # Extract meta tags
            meta_tags = await page.query_selector_all('meta')
            for meta in meta_tags:
                name = await meta.get_attribute('name') or await meta.get_attribute('property')
                content = await meta.get_attribute('content')
                if name and content:
                    metadata[name] = content

            # Extract structured data
            metadata['language'] = await self._extract_language(page)
            metadata['author'] = metadata.get('author', '') or self._extract_author_from_meta(html)
            metadata['publish_date'] = metadata.get('publish_date') or self._extract_publish_date_from_meta(metadata)
            metadata['description'] = metadata.get('description', '') or self._extract_description_from_meta(metadata)

        except Exception as e:
            logger.debug(f"Error extracting metadata: {e}")

        return metadata

    def _calculate_quality_score(self, content: Dict[str, Any]) -> float:
        """
        Calculate content quality score (0-1).

        Args:
            content: Extracted content dictionary

        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0

        # Content length score (0-0.3)
        content_length = len(content.get('content', ''))
        if content_length > 2000:
            score += 0.3
        elif content_length > 1000:
            score += 0.25
        elif content_length > 500:
            score += 0.2
        elif content_length > 100:
            score += 0.1

        # Structure score (0-0.25)
        if content.get('title'):
            score += 0.1
        if content.get('content_type') != 'generic':
            score += 0.1
        if any(key in content for key in ['sections', 'specifications', 'authors']):
            score += 0.05

        # Metadata completeness (0-0.25)
        metadata_fields = ['author', 'publish_date', 'summary', 'description']
        complete_fields = sum(1 for field in metadata_fields if field in content and content[field])
        score += (complete_fields / len(metadata_fields)) * 0.25

        # Readability score (0-0.2)
        text = content.get('content', '')
        if text:
            sentences = max(1, text.count('.') + text.count('!') + text.count('?'))
            words = len(text.split())
            avg_words_per_sentence = words / sentences

            if 10 <= avg_words_per_sentence <= 20:
                score += 0.2
            elif 5 <= avg_words_per_sentence <= 30:
                score += 0.15
            elif 3 <= avg_words_per_sentence <= 40:
                score += 0.1

        return min(score, 1.0)

    # Helper methods for specific extraction tasks
    def _extract_by_selectors(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract content using multiple CSS selectors."""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text:
                        return text
            except Exception:
                continue
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author information."""
        author_selectors = [
            '[rel="author"]', '.author', '.byline',
            '.article-author', '[itemprop="author"]',
            '.post-author', '.writer', '.contributor'
        ]
        return self._extract_by_selectors(soup, author_selectors)

    def _extract_publish_date(self, soup: BeautifulSoup, html: str) -> Optional[str]:
        """Extract publication date."""
        date_selectors = [
            '[itemprop="datePublished"]', '.publish-date',
            '.date', '[datetime]', '.timestamp',
            '.publication-date', '.post-date'
        ]
        date_text = self._extract_by_selectors(soup, date_selectors)

        if date_text:
            # Extract date from datetime attribute if available
            for selector in date_selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        datetime_attr = element.get('datetime')
                        if datetime_attr:
                            return datetime_attr
                except Exception:
                    continue

        return date_text

    def _extract_summary(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article summary."""
        summary_selectors = [
            '.summary', '.excerpt', '.lead',
            '.abstract', '.description',
            'meta[name="description"]'
        ]

        # Try meta description first
        meta_desc = soup.select_one('meta[name="description"]')
        if meta_desc:
            content = meta_desc.get('content')
            if content and len(content) > 20:  # Filter out very short descriptions
                return content

        return self._extract_by_selectors(soup, summary_selectors)

    def _extract_price_with_currency(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract price with currency information."""
        price_info = {'price': '', 'currency': '', 'formatted': ''}

        # Try structured data first
        price_elements = soup.select('[itemprop="price"], .price, .product-price')

        for element in price_elements:
            price_text = element.get_text(strip=True)
            if price_text:
                # Extract using patterns
                for pattern in self.price_patterns:
                    match = re.search(pattern, price_text)
                    if match:
                        price_value = match.group(1).replace(',', '')
                        price_info['price'] = price_value

                        # Detect currency
                        if '$' in price_text or 'USD' in price_text:
                            price_info['currency'] = 'USD'
                        elif '€' in price_text or 'EUR' in price_text:
                            price_info['currency'] = 'EUR'
                        elif '£' in price_text or 'GBP' in price_text:
                            price_info['currency'] = 'GBP'

                        price_info['formatted'] = match.group(0)
                        return price_info

        return price_info

    def _extract_specifications(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract product specifications."""
        specs = []

        # Try structured specifications
        spec_selectors = [
            '.specifications table', '.specs table',
            '.product-specs table', '.details table'
        ]

        for selector in spec_selectors:
            table = soup.select_one(selector)
            if table:
                rows = table.select('tr')
                for row in rows:
                    cells = row.select('td, th')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            specs.append({'key': key, 'value': value})

        return specs

    def _extract_product_images(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract product images with special handling."""
        images = []

        # Try product image galleries
        img_selectors = [
            '.product-image img', '.product-photo img',
            '.gallery img', '.carousel img', '.main-image img'
        ]

        for selector in img_selectors:
            img_elements = soup.select(selector)
            for img in img_elements:
                src = img.get('src') or img.get('data-src')
                alt = img.get('alt', '')
                if src:
                    images.append({
                        'src': src,
                        'alt': alt,
                        'is_primary': 'main' in selector or 'primary' in selector
                    })

        return images

    def _extract_availability(self, soup: BeautifulSoup) -> str:
        """Extract product availability."""
        availability_selectors = [
            '.availability', '.stock-status', '.in-stock',
            '.out-of-stock', '.availability-status'
        ]

        availability = self._extract_by_selectors(soup, availability_selectors)

        if availability:
            availability_lower = availability.lower()
            if any(word in availability_lower for word in ['in stock', 'available', 'ready to ship']):
                return 'in_stock'
            elif any(word in availability_lower for word in ['out of stock', 'unavailable', 'sold out']):
                return 'out_of_stock'
            else:
                return availability

        return 'unknown'

    def _extract_review_count(self, soup: BeautifulSoup) -> int:
        """Extract review count."""
        review_selectors = [
            '.reviews-count', '.review-count', '.ratings-count',
            '[itemprop="reviewCount"]'
        ]

        for selector in review_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                # Extract number from text
                match = re.search(r'(\d+(?:,\d+)*)', text)
                if match:
                    return int(match.group(1).replace(',', ''))

        return 0

    def _extract_table_of_contents(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract table of contents."""
        toc = []

        # Try common TOC selectors
        toc_selectors = [
            '.toc', '.table-of-contents', '.contents',
            '.navigation', '.menu', '.sidebar nav'
        ]

        for selector in toc_selectors:
            toc_element = soup.select_one(selector)
            if toc_element:
                links = toc_element.select('a[href]')
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if text and href:
                        # Determine heading level
                        parent_tag = link.parent.name if link.parent else ''
                        level = 1
                        if parent_tag in ['h2', 'h3', 'h4', 'h5', 'h6']:
                            level = int(parent_tag[1])
                        elif parent_tag in ['li']:
                            # Try to infer level from nesting
                            level = 2

                        toc.append({
                            'text': text,
                            'href': href,
                            'level': level
                        })
                break

        return toc

    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract document sections."""
        sections = []

        # Extract heading-based sections
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

        for i, heading in enumerate(headings):
            level = int(heading.name[1])
            title = heading.get_text(strip=True)

            # Find content between this heading and the next heading of same or higher level
            content_elements = []
            next_element = heading.next_sibling

            while next_element:
                # Stop if we hit a heading of same or higher level
                if (next_element.name and
                    next_element.name.startswith('h') and
                    int(next_element.name[1]) <= level):
                    break

                content_elements.append(next_element)
                next_element = next_element.next_sibling

            # Convert content elements to text
            content = ''
            for element in content_elements:
                content += element.get_text() + '\n'

            if title.strip():
                sections.append({
                    'title': title.strip(),
                    'level': level,
                    'content': content.strip()
                })

        return sections

    def _extract_code_examples(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract code examples."""
        code_examples = []

        # Find code blocks
        code_selectors = [
            'pre code', '.highlight code', '.codehilite code',
            'pre', '.code-block', 'code[class*="language-"]'
        ]

        for selector in code_selectors:
            code_elements = soup.select(selector)
            for code_element in code_elements:
                code_text = code_element.get_text()
                class_attr = code_element.get('class', [])

                # Try to detect language
                language = 'unknown'
                for cls in class_attr:
                    if cls.startswith('language-'):
                        language = cls.replace('language-', '')
                        break
                    elif cls in ['python', 'javascript', 'java', 'cpp', 'c', 'go', 'rust']:
                        language = cls
                        break

                if code_text.strip():
                    code_examples.append({
                        'code': code_text.strip(),
                        'language': language,
                        'lines': len(code_text.split('\n'))
                    })

        return code_examples

    def _extract_authors(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract academic paper authors."""
        authors = []

        # Try various author selectors
        author_selectors = [
            '.author', '.paper-author', '[itemprop="author"]',
            '.contributor', '.writer', '.researcher'
        ]

        for selector in author_selectors:
            author_elements = soup.select(selector)
            for element in author_elements:
                name = element.get_text(strip=True)
                if name and name not in [a['name'] for a in authors]:
                    # Extract affiliation if available
                    affiliation = ''
                    affil_element = element.find_next(class_='affiliation')
                    if affil_element:
                        affiliation = affil_element.get_text(strip=True)

                    authors.append({
                        'name': name,
                        'affiliation': affiliation,
                        'email': element.get('href', '') if element.get('href', '').startswith('mailto:') else ''
                    })

        return authors

    def _extract_abstract(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract academic paper abstract."""
        abstract_selectors = [
            '.abstract', '.summary', '[itemprop="abstract"]',
            '.paper-abstract', '.research-summary'
        ]

        return self._extract_by_selectors(soup, abstract_selectors)

    def _extract_citations(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract academic paper citations."""
        citations = []

        # Try citation selectors
        citation_selectors = [
            '.citation', '.reference', '.bibliography',
            '.works-cited', '.cited-work'
        ]

        for selector in citation_selectors:
            citation_elements = soup.select(selector)
            for element in citation_elements:
                citation_text = element.get_text(strip=True)
                if citation_text and len(citation_text) > 10:  # Filter out very short citations
                    citations.append({
                        'text': citation_text,
                        'type': selector.replace('.', '')
                    })

        return citations

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content fallback."""
        # Try content area selectors
        content_selectors = [
            '.content', '.main-content', '.article-content',
            '.post-content', '#content', 'main', 'article'
        ]

        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                return self.html2text.handle(str(content_element)).strip()

        # Fallback to readability
        doc = Document(str(soup))
        return self.html2text.handle(doc.summary()).strip()

    def _is_product_image(self, src: str, alt: str) -> bool:
        """Determine if an image is a product image."""
        product_indicators = [
            'product', 'item', 'model', 'photo', 'image',
            'main', 'primary', 'featured', 'thumbnail'
        ]

        src_lower = src.lower()
        alt_lower = alt.lower()

        return any(indicator in src_lower or indicator in alt_lower for indicator in product_indicators)

    def _is_navigation_link(self, href: str, text: str) -> bool:
        """Determine if a link is a navigation link."""
        nav_indicators = [
            'menu', 'nav', 'sidebar', 'footer', 'header',
            'home', 'about', 'contact', 'login', 'register'
        ]

        href_lower = href.lower()
        text_lower = text.lower()

        return (any(indicator in href_lower for indicator in nav_indicators) or
                any(indicator in text_lower for indicator in nav_indicators))

    def _is_download_link(self, href: str) -> bool:
        """Determine if a link is a download link."""
        download_indicators = ['.pdf', '.zip', '.doc', '.docx', '.xls', '.xlsx']
        return any(href.lower().endswith(indicator) for indicator in download_indicators)

    async def _extract_language(self, page: Page) -> str:
        """Extract page language."""
        try:
            # Try lang attribute from html element
            lang = await page.get_attribute('lang')
            if lang:
                return lang[:2]  # Return ISO 639-1 code
        except Exception:
            pass

        try:
            # Try meta language tag
            meta_lang = await page.query_selector('meta[http-equiv="content-language"]')
            if meta_lang:
                content = await meta_lang.get_attribute('content')
                if content:
                    return content[:2]
        except Exception:
            pass

        return 'en'  # Default to English

    def _extract_author_from_meta(self, html: str) -> Optional[str]:
        """Extract author from HTML meta tags."""
        meta_patterns = [
            r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*property=["\']article:author["\'][^>]*content=["\']([^"\']+)["\']'
        ]

        for pattern in meta_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_publish_date_from_meta(self, metadata: Dict[str, str]) -> Optional[str]:
        """Extract publish date from metadata."""
        date_fields = [
            'article:published_time', 'published_time', 'datePublished',
            'publish_date', 'publication_date', 'date'
        ]

        for field in date_fields:
            if field in metadata:
                return metadata[field]

        return None

    def _extract_description_from_meta(self, metadata: Dict[str, str]) -> Optional[str]:
        """Extract description from metadata."""
        desc_fields = [
            'description', 'og:description', 'twitter:description',
            'summary', 'abstract'
        ]

        for field in desc_fields:
            if field in metadata:
                return metadata[field]

        return None


# Factory function
def create_web_content_extractor(browser_manager: BrowserManager) -> WebContentExtractor:
    """
    Factory function to create a web content extractor.

    Args:
        browser_manager: Instance of BrowserManager for browser automation

    Returns:
        WebContentExtractor instance
    """
    return WebContentExtractor(browser_manager)