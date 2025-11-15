"""
Unit Tests for Web Content Extractor

This module contains comprehensive unit tests for the WebContentExtractor service,
testing content type detection, extraction algorithms, quality scoring, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import hashlib
import time

from services.web_content_extractor import WebContentExtractor
from services.browser_manager import BrowserManager


class TestWebContentExtractor:
    """Test suite for WebContentExtractor service."""

    @pytest.fixture
    def mock_browser_manager(self):
        """Create a mock BrowserManager instance."""
        browser_manager = Mock(spec=BrowserManager)
        return browser_manager

    @pytest.fixture
    def web_content_extractor(self, mock_browser_manager):
        """Create WebContentExtractor instance with mocked dependencies."""
        return WebContentExtractor(mock_browser_manager)

    # =============================================================================
    # Content Type Detection Tests
    # =============================================================================

    def test_detect_content_type_article(self, web_content_extractor):
        """Test article content type detection."""
        article_urls = [
            "https://example.com/article/test-article",
            "https://news.cnn.com/world/story",
            "https://blog.example.com/post/123",
            "https://medium.com/@author/article-title",
            "https://github.com/user/repo/issues/123"
        ]

        for url in article_urls:
            result = web_content_extractor._detect_content_type(url)
            assert result == "article", f"Failed to detect article for URL: {url}"

    def test_detect_content_type_product(self, web_content_extractor):
        """Test product content type detection."""
        product_urls = [
            "https://amazon.com/dp/B123456789",
            "https://etsy.com/listing/123456789",
            "https://shop.example.com/product/item123",
            "https://example.com/p/12345"
        ]

        for url in product_urls:
            result = web_content_extractor._detect_content_type(url)
            assert result == "product", f"Failed to detect product for URL: {url}"

    def test_detect_content_type_documentation(self, web_content_extractor):
        """Test documentation content type detection."""
        doc_urls = [
            "https://docs.example.com/api/v1",
            "https://readthedocs.io/en/latest/",
            "https://developer.mozilla.org/en-US/docs/Web/API",
            "https://github.io/docs/",
            "https://stackoverflow.com/questions/12345"
        ]

        for url in doc_urls:
            result = web_content_extractor._detect_content_type(url)
            assert result == "documentation", f"Failed to detect documentation for URL: {url}"

    def test_detect_content_type_academic(self, web_content_extractor):
        """Test academic content type detection."""
        academic_urls = [
            "https://arxiv.org/abs/1234.56789",
            "https://scholar.google.com/citations",
            "https://pubmed.ncbi.nlm.nih.gov/12345",
            "https://ieeexplore.ieee.org/document/12345"
        ]

        for url in academic_urls:
            result = web_content_extractor._detect_content_type(url)
            assert result == "academic", f"Failed to detect academic for URL: {url}"

    def test_detect_content_type_generic_fallback(self, web_content_extractor):
        """Test generic content type fallback."""
        generic_urls = [
            "https://example.com/page",
            "https://unknown-site.com/content",
            "https://example.com/random/path"
        ]

        for url in generic_urls:
            result = web_content_extractor._detect_content_type(url)
            assert result == "generic", f"Should fallback to generic for URL: {url}"

    # =============================================================================
    # Quality Scoring Tests
    # =============================================================================

    def test_calculate_quality_score_high_quality(self, web_content_extractor):
        """Test quality scoring for high-quality content."""
        content = {
            'content': 'This is a long and well-structured article. ' * 200,  # 2000+ words
            'title': 'A Quality Article Title',
            'content_type': 'article',
            'author': 'John Doe',
            'publish_date': '2024-01-01',
            'summary': 'This is a comprehensive summary.'
        }

        score = web_content_extractor._calculate_quality_score(content)
        assert score >= 0.8, f"Expected high quality score, got {score}"

    def test_calculate_quality_score_low_quality(self, web_content_extractor):
        """Test quality scoring for low-quality content."""
        content = {
            'content': 'Short content.',
            'title': '',
            'content_type': 'generic',
            'author': '',
            'publish_date': None
        }

        score = web_content_extractor._calculate_quality_score(content)
        assert score <= 0.4, f"Expected low quality score, got {score}"

    def test_calculate_quality_score_medium_quality(self, web_content_extractor):
        """Test quality scoring for medium-quality content."""
        content = {
            'content': 'This is a medium length article with some structure. ' * 50,  # ~500 words
            'title': 'Medium Quality Article',
            'content_type': 'article',
            'author': 'Jane Smith',
            'publish_date': '2024-01-01'
        }

        score = web_content_extractor._calculate_quality_score(content)
        assert 0.4 <= score <= 0.8, f"Expected medium quality score, got {score}"

    # =============================================================================
    # Article Extraction Tests
    # =============================================================================

    def test_extract_article_basic(self, web_content_extractor):
        """Test basic article content extraction."""
        html = """
        <html>
        <head>
            <title>Test Article</title>
            <meta name="author" content="John Doe">
            <meta property="article:published_time" content="2024-01-01T12:00:00Z">
        </head>
        <body>
            <article>
                <h1>Test Article Title</h1>
                <div class="article-content">
                    <p>This is the main article content. It contains multiple sentences that are
                    reasonably sized for readability. The content should be properly formatted
                    when extracted using the readability algorithm.</p>
                    <p>This is the second paragraph with more content to ensure we have
                    enough text for quality scoring.</p>
                </div>
            </article>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_article(html, "https://example.com/article"))

        assert result['title'] == 'Test Article Title'
        assert result['content_type'] == 'article'
        assert len(result['content']) > 100
        assert 'main article content' in result['content']
        assert result['word_count'] > 20
        assert result['reading_time_minutes'] >= 1

    def test_extract_article_with_author(self, web_content_extractor):
        """Test article extraction with author information."""
        html = """
        <html>
        <body>
            <article>
                <h1>Article Title</h1>
                <div class="author">By Jane Smith</div>
                <div class="article-content">
                    <p>This is article content with proper author attribution.</p>
                </div>
            </article>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_article(html, "https://example.com/article"))

        assert result['author'] == 'By Jane Smith'
        assert result['title'] == 'Article Title'

    # =============================================================================
    # Product Extraction Tests
    # =============================================================================

    def test_extract_product_basic(self, web_content_extractor):
        """Test basic product information extraction."""
        html = """
        <html>
        <body>
            <div class="product-page">
                <h1 class="product-title">Test Product Name</h1>
                <div class="price">$29.99</div>
                <div class="product-description">
                    This is a high-quality product with excellent features.
                </div>
                <div class="product-specs">
                    <table>
                        <tr><td>Color</td><td>Red</td></tr>
                        <tr><td>Size</td><td>Large</td></tr>
                    </table>
                </div>
                <div class="availability">In Stock</div>
                <div class="reviews-count">42 reviews</div>
            </div>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_product(html, "https://example.com/product"))

        assert result['name'] == 'Test Product Name'
        assert result['price'] == '29.99'
        assert result['currency'] == 'USD'
        assert 'high-quality product' in result['description']
        assert len(result['specifications']) == 2
        assert result['specifications'][0]['key'] == 'Color'
        assert result['specifications'][0]['value'] == 'Red'
        assert result['availability'] == 'in_stock'
        assert result['review_count'] == 42
        assert result['content_type'] == 'product'

    def test_extract_product_with_multiple_prices(self, web_content_extractor):
        """Test product extraction with multiple price formats."""
        html = """
        <html>
        <body>
            <div class="product-page">
                <h1>Expensive Product</h1>
                <div class="price">€1,234.56</div>
            </div>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_product(html, "https://example.com/product"))

        assert result['price'] == '1.234.56'
        assert result['currency'] == 'EUR'
        assert '€1,234.56' in result['price_formatted']

    # =============================================================================
    # Documentation Extraction Tests
    # =============================================================================

    def test_extract_documentation_with_sections(self, web_content_extractor):
        """Test documentation extraction with sections."""
        html = """
        <html>
        <body>
            <div class="documentation">
                <h1>API Documentation</h1>
                <nav class="toc">
                    <a href="#introduction">Introduction</a>
                    <a href="#getting-started">Getting Started</a>
                </nav>
                <div class="content">
                    <h2>Introduction</h2>
                    <p>This is the introduction section.</p>

                    <h2>Getting Started</h2>
                    <p>This section explains how to get started.</p>

                    <h3>Installation</h3>
                    <pre><code>npm install package</code></pre>
                </div>
            </div>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_documentation(html, "https://example.com/docs"))

        assert result['title'] == 'API Documentation'
        assert len(result['sections']) >= 2
        assert result['sections'][0]['title'] == 'Introduction'
        assert result['sections'][0]['level'] == 2
        assert len(result['code_examples']) >= 1
        assert result['code_examples'][0]['code'] == 'npm install package'
        assert len(result['table_of_contents']) >= 2
        assert result['content_type'] == 'documentation'

    # =============================================================================
    # Academic Extraction Tests
    # =============================================================================

    def test_extract_academic_with_citations(self, web_content_extractor):
        """Test academic paper extraction."""
        html = """
        <html>
        <body>
            <div class="paper">
                <h1 class="paper-title">Research Paper Title</h1>
                <div class="author">Dr. John Smith</div>
                <div class="abstract">
                    This is the abstract of the research paper. It provides a brief summary
                    of the research methodology, findings, and conclusions.
                </div>
                <div class="content">
                    <h2>Introduction</h2>
                    <p>This is the main content of the paper.</p>
                </div>
                <div class="references">
                    <div class="citation">[1] Smith, J. et al. (2024). "Previous Research". Journal Name.</div>
                    <div class="citation">[2] Doe, J. (2023). "Related Study". Another Journal.</div>
                </div>
            </div>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_academic(html, "https://example.com/paper"))

        assert result['title'] == 'Research Paper Title'
        assert len(result['authors']) >= 1
        assert result['authors'][0]['name'] == 'Dr. John Smith'
        assert 'abstract of the research paper' in result['abstract']
        assert len(result['citations']) >= 2
        assert result['citation_count'] >= 2
        assert result['content_type'] == 'academic'

    # =============================================================================
    # Generic Extraction Tests
    # =============================================================================

    def test_extract_generic_fallback(self, web_content_extractor):
        """Test generic content extraction fallback."""
        html = """
        <html>
        <head>
            <title>Generic Page</title>
        </head>
        <body>
            <div>
                <h1>Page Title</h1>
                <p>This is some generic content that doesn't fit into any specific category.
                It should still be extracted properly using the readability algorithm as a
                fallback method.</p>
                <p>Additional content to ensure sufficient length.</p>
            </div>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_generic(html, "https://example.com/page"))

        assert result['title'] == 'Generic Page'
        assert len(result['content']) > 50
        assert 'generic content' in result['content']
        assert result['content_type'] == 'generic'
        assert result['word_count'] > 10

    # =============================================================================
    # Integration Tests with Mocked Browser
    # =============================================================================

    @pytest.mark.asyncio
    async def test_extract_content_with_browser_integration(self, web_content_extractor, mock_browser_manager):
        """Test full content extraction with browser integration."""
        # Mock browser manager methods
        mock_page = AsyncMock()
        mock_page.content.return_value = """
        <html>
        <head>
            <title>Integration Test Article</title>
            <meta name="author" content="Test Author">
        </head>
        <body>
            <article>
                <h1>Integration Test Title</h1>
                <p>This is integration test content that should be extracted properly.
                It includes multiple sentences to test the readability algorithm.</p>
                <p>Second paragraph with more content for comprehensive testing.</p>
            </article>
        </body>
        </html>
        """
        mock_page.query_selector_all.return_value = []  # No images or links
        mock_page.query_selector.return_value = None

        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page.return_value = None

        # Test article extraction
        result = await web_content_extractor.extract_content(
            url="https://example.com/article/test",
            content_type="article",
            extract_images=False,
            extract_links=False
        )

        assert result['success'] is True
        assert result['title'] == 'Integration Test Title'
        assert result['content_type'] == 'article'
        assert 'integration test content' in result['content']
        assert result['quality_score'] > 0.5
        assert result['extraction_time_ms'] > 0
        assert result['content_hash'] is not None

    @pytest.mark.asyncio
    async def test_extract_content_error_handling(self, web_content_extractor, mock_browser_manager):
        """Test error handling during content extraction."""
        # Mock browser manager to raise exception
        mock_browser_manager.navigate.side_effect = Exception("Browser error")

        result = await web_content_extractor.extract_content(
            url="https://example.com/error",
            content_type="article"
        )

        assert result['success'] is False
        assert 'error' in result
        assert result['quality_score'] == 0.0
        assert result['content_type'] == 'article'

    @pytest.mark.asyncio
    async def test_auto_content_type_detection(self, web_content_extractor, mock_browser_manager):
        """Test automatic content type detection."""
        # Mock browser setup
        mock_page = AsyncMock()
        mock_page.content.return_value = "<html><body><h1>Test</h1></body></html>"
        mock_page.query_selector_all.return_value = []
        mock_page.query_selector.return_value = None
        mock_browser_manager.navigate.return_value = mock_page
        mock_browser_manager.close_page.return_value = None

        # Test auto-detection for article URL
        result = await web_content_extractor.extract_content(
            url="https://news.example.com/article/123"
        )

        assert result['content_type'] == 'article'

    # =============================================================================
    # Helper Method Tests
    # =============================================================================

    def test_extract_price_patterns(self, web_content_extractor):
        """Test price extraction patterns."""
        test_cases = [
            ("$29.99", "29.99", "USD"),
            ("€1,234.56", "1.234.56", "EUR"),
            ("£499.00", "499.00", "GBP"),
            ("1234.56 USD", "1234.56", "USD"),
            ("USD 1234.56", "1234.56", "USD"),
            ("€ 1.234,56", "1.234,56", "EUR")
        ]

        for price_text, expected_price, expected_currency in test_cases:
            price_info = web_content_extractor._extract_price_with_currency(
                BeautifulSoup(f'<div class="price">{price_text}</div>', 'html.parser')
            )
            assert price_info['price'] == expected_price, f"Failed for {price_text}"
            assert price_info['currency'] == expected_currency, f"Failed for {price_text}"

    def test_extract_specifications(self, web_content_extractor):
        """Test specification extraction."""
        html = """
        <div class="specifications">
            <table>
                <tr><td>Brand</td><td>TestBrand</td></tr>
                <tr><td>Model</td><td>123X</td></tr>
                <tr><td>Weight</td><td>2.5 kg</td></tr>
            </table>
        </div>
        """

        soup = BeautifulSoup(html, 'html.parser')
        specs = web_content_extractor._extract_specifications(soup)

        assert len(specs) == 3
        assert specs[0]['key'] == 'Brand'
        assert specs[0]['value'] == 'TestBrand'
        assert specs[1]['key'] == 'Model'
        assert specs[1]['value'] == '123X'

    def test_extract_table_of_contents(self, web_content_extractor):
        """Test table of contents extraction."""
        html = """
        <nav class="toc">
            <ul>
                <li><a href="#introduction">Introduction</a></li>
                <li><a href="#getting-started">Getting Started</a></li>
                <li><a href="#advanced">Advanced Topics</a></li>
            </ul>
        </nav>
        """

        soup = BeautifulSoup(html, 'html.parser')
        toc = web_content_extractor._extract_table_of_contents(soup)

        assert len(toc) == 3
        assert toc[0]['text'] == 'Introduction'
        assert toc[0]['href'] == '#introduction'
        assert toc[0]['level'] == 1

    def test_extract_sections(self, web_content_extractor):
        """Test section extraction."""
        html = """
        <div>
            <h1>Main Title</h1>
            <p>Main content.</p>

            <h2>Section 1</h2>
            <p>Section 1 content.</p>

            <h3>Subsection 1.1</h3>
            <p>Subsection content.</p>

            <h2>Section 2</h2>
            <p>Section 2 content.</p>
        </div>
        """

        soup = BeautifulSoup(html, 'html.parser')
        sections = web_content_extractor._extract_sections(soup)

        assert len(sections) >= 3
        assert sections[0]['title'] == 'Main Title'
        assert sections[0]['level'] == 1
        assert sections[1]['title'] == 'Section 1'
        assert sections[1]['level'] == 2

    def test_extract_code_examples(self, web_content_extractor):
        """Test code example extraction."""
        html = """
        <div>
            <pre><code class="language-python">
def hello_world():
    print("Hello, World!")
            </code></pre>

            <pre><code>
def generic_function():
    pass
            </code></pre>

            <div class="highlight">
                <pre><code class="javascript">
console.log("JavaScript code");
                </code></pre>
            </div>
        </div>
        """

        soup = BeautifulSoup(html, 'html.parser')
        code_examples = web_content_extractor._extract_code_examples(soup)

        assert len(code_examples) == 3
        assert code_examples[0]['language'] == 'python'
        assert 'def hello_world():' in code_examples[0]['code']
        assert code_examples[1]['language'] == 'unknown'
        assert code_examples[2]['language'] == 'javascript'

    # =============================================================================
    # Performance Tests
    # =============================================================================

    def test_performance_large_content(self, web_content_extractor):
        """Test performance with large content."""
        # Create large content (5000 words)
        large_content = "This is a sentence. " * 1000  # ~5000 words

        content = {
            'content': large_content,
            'title': 'Large Article Title',
            'content_type': 'article'
        }

        start_time = time.time()
        score = web_content_extractor._calculate_quality_score(content)
        end_time = time.time()

        processing_time = (end_time - start_time) * 1000

        assert score > 0.8  # Should be high quality due to length
        assert processing_time < 100  # Should process in under 100ms

    # =============================================================================
    # Edge Cases and Validation Tests
    # =============================================================================

    def test_extract_content_empty_html(self, web_content_extractor):
        """Test content extraction with empty HTML."""
        result = asyncio.run(web_content_extractor._extract_article("", "https://example.com"))
        assert result['content_type'] == 'article'
        assert result['title'] == ''
        assert result['content'] == ''

    def test_extract_content_malformed_html(self, web_content_extractor):
        """Test content extraction with malformed HTML."""
        malformed_html = "<div>Unclosed tag<p>Paragraph"

        # Should not crash and should extract something
        result = asyncio.run(web_content_extractor._extract_generic(malformed_html, "https://example.com"))
        assert 'content_type' in result

    def test_unicode_content_extraction(self, web_content_extractor):
        """Test extraction with Unicode content."""
        unicode_content = """
        <html>
        <body>
            <h1>Título con acentos</h1>
            <p>Contenido con caracteres especiales: ñ, ü, 中文, العربية</p>
            <p>Testing emoji: 🚀, 🎉, 💻</p>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_article(unicode_content, "https://example.com"))
        assert 'acentos' in result['content']
        assert 'ñ' in result['content'] or '中文' in result['content']

    def test_very_long_title(self, web_content_extractor):
        """Test handling of very long titles."""
        long_title = "This is a very long title that extends beyond normal limits " * 10
        html = f"<html><head><title>{long_title}</title></head><body><p>Content</p></body></html>"

        result = asyncio.run(web_content_extractor._extract_article(html, "https://example.com"))
        assert len(result['title']) > 0  # Should handle long titles without crashing

    def test_nested_content_extraction(self, web_content_extractor):
        """Test extraction from deeply nested content."""
        nested_html = """
        <html>
        <body>
            <div class="wrapper">
                <div class="container">
                    <div class="content">
                        <div class="article">
                            <h1>Nested Content Title</h1>
                            <div class="text">
                                <p>This content is deeply nested.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        result = asyncio.run(web_content_extractor._extract_article(nested_html, "https://example.com"))
        assert result['title'] == 'Nested Content Title'
        assert 'deeply nested' in result['content']


# =============================================================================
# Integration Test Helper Classes
# =============================================================================

class MockBrowserPage:
    """Mock browser page for testing."""

    def __init__(self, html_content="", images=[], links=[]):
        self.html_content = html_content
        self.images = images
        self.links = links

    async def content(self):
        return self.html_content

    async def query_selector_all(self, selector):
        if selector == 'img':
            return [MockElement(attrs=img) for img in self.images]
        elif selector == 'a[href]':
            return [MockElement(attrs=link) for link in self.links]
        return []

    async def query_selector(self, selector):
        return None

    async def get_attribute(self, attr):
        return None

    async def inner_text(self):
        return ""

    async def get_text(self):
        return ""


class MockElement:
    """Mock DOM element for testing."""

    def __init__(self, attrs=None):
        self.attrs = attrs or {}

    async def get_attribute(self, attr):
        return self.attrs.get(attr)

    async def inner_text(self):
        return self.attrs.get('text', '')

    async def get_text(self):
        return self.attrs.get('text', '')


if __name__ == "__main__":
    pytest.main([__file__])