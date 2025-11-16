"""
Markdown File Parser

This module handles parsing of Markdown (.md) files with preservation
of structure, formatting, and metadata extraction.
"""

import re
import os
from typing import Dict, Any, Optional
from datetime import datetime
from .base_parser import BaseParser, ParseResult, ValidationResult


class MarkdownParser(BaseParser):
    """Parser for Markdown (.md) files"""

    SUPPORTED_EXTENSIONS = ['.md', '.markdown']
    MAGIC_NUMBERS = {
        '.md': b'',  # Text files don't have reliable magic numbers
    }

    def extract_content(self, file_path: str) -> ParseResult:
        """
        Extract text content from Markdown file with structure preservation

        Args:
            file_path: Path to the Markdown file

        Returns:
            ParseResult with extracted content and metadata
        """
        import time
        start_time = time.time()

        try:
            # Validate file first
            validation = self.validate_file(file_path)
            if not validation.is_valid:
                return ParseResult(
                    success=False,
                    error_message=validation.error_message
                )

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                return ParseResult(
                    success=False,
                    error_message="Markdown file appears to be empty"
                )

            # Extract metadata
            metadata = self._extract_markdown_metadata(content, file_path)

            # Process content while preserving structure
            processed_content = self._process_markdown_content(content)

            # Create chunks for vector indexing
            chunks = self.chunk_text(processed_content)

            processing_time = time.time() - start_time

            return ParseResult(
                success=True,
                content=processed_content,
                metadata=metadata,
                chunks=chunks,
                total_chunks=len(chunks),
                file_size=validation.file_size,
                processing_time=processing_time
            )

        except UnicodeDecodeError:
            return ParseResult(
                success=False,
                error_message="Failed to decode Markdown file as UTF-8 text"
            )
        except Exception as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to parse Markdown file: {str(e)}"
            )

    def _extract_markdown_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from Markdown content

        Args:
            content: Raw Markdown content
            file_path: Path to the file

        Returns:
            Dictionary of metadata
        """
        metadata = {
            'file_type': 'markdown',
            'extraction_method': 'markdown_parser',
            'has_frontmatter': False,
            'header_count': 0,
            'code_block_count': 0,
            'link_count': 0,
            'image_count': 0
        }

        # Extract frontmatter (YAML metadata at top)
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            metadata['has_frontmatter'] = True
            frontmatter = frontmatter_match.group(1)

            # Parse basic YAML frontmatter
            try:
                yaml_lines = frontmatter.split('\n')
                for line in yaml_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[f'frontmatter_{key.strip().lower()}'] = value.strip()
            except Exception:
                pass  # Frontmatter parsing failures should not stop processing

        # Count structural elements
        metadata['header_count'] = len(re.findall(r'^#{1,6}\s+', content, re.MULTILINE))
        metadata['code_block_count'] = len(re.findall(r'```', content)) // 2
        metadata['link_count'] = len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content))
        metadata['image_count'] = len(re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content))

        # Extract title from first H1 or filename
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        else:
            metadata['title'] = os.path.splitext(os.path.basename(file_path))[0]

        return metadata

    def _process_markdown_content(self, content: str) -> str:
        """
        Process Markdown content to optimize for vector search while preserving structure

        Args:
            content: Raw Markdown content

        Returns:
            Processed text content
        """
        # Remove frontmatter for content processing
        content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

        # Preserve header structure
        content = re.sub(r'^#{1,6}\s+(.+)$', r'HEADER: \1', content, flags=re.MULTILINE)

        # Process code blocks - preserve as CODE: label
        content = re.sub(r'```[^`\n]*\n(.*?)\n```', r'CODE_BLOCK: \1', content, flags=re.DOTALL)

        # Process inline code
        content = re.sub(r'`([^`]+)`', r'INLINE_CODE: \1', content)

        # Process links - preserve both text and URL
        content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'LINK: \1 (URL: \2)', content)

        # Process images
        content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'IMAGE: \1 (URL: \2)', content)

        # Preserve list structure
        content = re.sub(r'^\s*[-*+]\s+(.+)$', r'LIST_ITEM: \1', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*\d+\.\s+(.+)$', r'NUMBERED_ITEM: \1', content, flags=re.MULTILINE)

        # Preserve blockquotes
        content = re.sub(r'^>\s+(.+)$', r'QUOTE: \1', content, flags=re.MULTILINE)

        # Preserve emphasis (bold and italic)
        content = re.sub(r'\*\*([^*]+)\*\*', r'BOLD: \1', content)
        content = re.sub(r'\*([^*]+)\*', r'ITALIC: \1', content)
        content = re.sub(r'__([^_]+)__', r'BOLD: \1', content)
        content = re.sub(r'_([^_]+)_', r'ITALIC: \1', content)

        # Clean up excessive whitespace while preserving structure
        content = re.sub(r'\n{3,}', '\n\n', content)  # Reduce multiple newlines
        content = re.sub(r'[ \t]+', ' ', content)  # Replace multiple spaces with single

        return content.strip()

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Validate Markdown file with additional checks

        Args:
            file_path: Path to the file

        Returns:
            ValidationResult with enhanced validation
        """
        base_validation = super().validate_file(file_path)

        if not base_validation.is_valid:
            return base_validation

        try:
            # Additional Markdown-specific validation
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # Read first 1KB for validation

            # Check if file looks like Markdown by looking for common Markdown patterns
            markdown_indicators = [
                r'^#{1,6}\s+',  # Headers
                r'\*\*.*?\*\*',  # Bold text
                r'\[.*\]\(.*\)',  # Links
                r'^\s*[-*+]\s+',  # Lists
                r'```',  # Code blocks
            ]

            has_markdown_patterns = any(re.search(pattern, content, re.MULTILINE)
                                      for pattern in markdown_indicators)

            if not has_markdown_patterns and len(content.strip()) > 0:
                # File doesn't look like Markdown but is text - still valid but with warning
                base_validation.error_message = "File does not contain obvious Markdown patterns, but will be processed as text"

            return base_validation

        except UnicodeDecodeError:
            return ValidationResult(
                is_valid=False,
                error_message="File contains non-UTF-8 characters, cannot be processed as Markdown"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation failed: {str(e)}"
            )