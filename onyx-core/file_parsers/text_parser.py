"""
Text File Parser

This module handles parsing of plain text (.txt) files with content
extraction and metadata for vector indexing.
"""

import os
import re
from typing import Dict, Any, Optional
from datetime import datetime
from .base_parser import BaseParser, ParseResult, ValidationResult


class TextParser(BaseParser):
    """Parser for plain text (.txt) files"""

    SUPPORTED_EXTENSIONS = ['.txt', '.text', '.log']
    MAGIC_NUMBERS = {
        '.txt': b'',  # Text files don't have reliable magic numbers
        '.log': b'',  # Log files are text files
    }

    def extract_content(self, file_path: str) -> ParseResult:
        """
        Extract text content from text file with analysis

        Args:
            file_path: Path to the text file

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

            # Detect encoding and read file
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding) as file:
                content = file.read()

            if not content.strip():
                return ParseResult(
                    success=False,
                    error_message="Text file appears to be empty"
                )

            # Extract metadata
            metadata = self._extract_text_metadata(content, file_path)

            # Process content for better vector search
            processed_content = self._process_text_content(content)

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

        except UnicodeDecodeError as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to decode text file with detected encoding: {str(e)}"
            )
        except Exception as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to parse text file: {str(e)}"
            )

    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding with fallback options

        Args:
            file_path: Path to the file

        Returns:
            Detected encoding string
        """
        encodings_to_try = [
            'utf-8', 'utf-8-sig',  # UTF-8 with and without BOM
            'latin-1', 'cp1252',     # Common Western encodings
            'iso-8859-1',           # ISO standard
            'ascii',                 # ASCII fallback
        ]

        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)  # Try to read a small chunk
                return encoding
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        # Fallback to utf-8 with error handling
        return 'utf-8'

    def _extract_text_metadata(self, content: str, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from text content

        Args:
            content: Raw text content
            file_path: Path to the file

        Returns:
            Dictionary of metadata
        """
        metadata = {
            'file_type': 'text',
            'encoding': self._detect_encoding(file_path),
            'line_count': len(content.split('\n')),
            'word_count': len(content.split()),
            'char_count': len(content),
            'char_count_no_spaces': len(content.replace(' ', '')),
            'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
            'has_urls': bool(re.search(r'https?://[^\s]+', content)),
            'has_email_addresses': bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)),
            'has_numbers': bool(re.search(r'\b\d+\b', content)),
            'language_indicators': self._detect_language(content),
            'content_type': self._detect_content_type(file_path, content),
            'average_line_length': 0,
            'max_line_length': 0
        }

        # Calculate line length statistics
        lines = content.split('\n')
        if lines:
            lengths = [len(line) for line in lines]
            metadata['average_line_length'] = sum(lengths) / len(lengths)
            metadata['max_line_length'] = max(lengths)

        # Extract URLs and email addresses if present
        if metadata['has_urls']:
            urls = re.findall(r'https?://[^\s\)]+', content)
            metadata['urls'] = urls[:10]  # First 10 URLs

        if metadata['has_email_addresses']:
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
            metadata['email_addresses'] = emails[:10]  # First 10 emails

        # Extract numbers if present
        if metadata['has_numbers']:
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', content)
            metadata['numbers'] = numbers[:20]  # First 20 numbers

        # Detect if it might be code, log, or other specialized content
        file_name = os.path.basename(file_path).lower()
        if any(indicator in file_name for indicator in ['.log', 'debug', 'error', 'output']):
            metadata['content_subtype'] = 'log'
        elif any(indicator in file_name for indicator in ['.py', '.js', '.html', '.css', '.java']):
            metadata['content_subtype'] = 'code'
        elif metadata['has_urls'] and metadata['has_email_addresses']:
            metadata['content_subtype'] = 'communication'
        else:
            metadata['content_subtype'] = 'general'

        return metadata

    def _detect_language(self, content: str) -> Dict[str, float]:
        """
        Simple language detection based on character patterns

        Args:
            content: Text content to analyze

        Returns:
            Dictionary with language indicators
        """
        content_lower = content.lower()
        total_chars = len([c for c in content if c.isalpha()])

        if total_chars == 0:
            return {'unknown': 1.0}

        language_indicators = {
            'english': 0,
            'numeric': 0,
            'punctuation': 0,
            'other': 0
        }

        for char in content_lower:
            if char.isalpha():
                language_indicators['english'] += 1
            elif char.isdigit():
                language_indicators['numeric'] += 1
            elif char in '.,!?;:"\'()-[]{}':
                language_indicators['punctuation'] += 1
            else:
                language_indicators['other'] += 1

        # Normalize to percentages
        for key in language_indicators:
            language_indicators[key] = language_indicators[key] / total_chars

        return language_indicators

    def _detect_content_type(self, file_path: str, content: str) -> str:
        """
        Detect the type of text content

        Args:
            file_path: Path to file
            content: File content

        Returns:
            Detected content type
        """
        file_name = os.path.basename(file_path).lower()

        # Check filename first
        if 'log' in file_name or file_name.endswith('.log'):
            return 'log'
        elif file_name.endswith('.md'):
            return 'markdown'  # Even though extension is .txt, content might be markdown
        elif file_name.endswith('.json') or file_name.endswith('.xml'):
            return 'structured_data'

        # Check content patterns
        if re.search(r'^\d{4}-\d{2}-\d{2', content):  # Date patterns suggest logs
            return 'log'
        elif re.search(r'stacktrace|exception|error', content, re.IGNORECASE):
            return 'error_log'
        elif re.search(r'import\s+\w+|function\s+\w+|class\s+\w+', content):
            return 'code'
        elif re.search(r'https?://[^\s]+', content) and re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
            return 'communication'
        elif len(content.split('\n')) > 1000:  # Many lines suggest structured data
            return 'structured_data'
        else:
            return 'general_text'

    def _process_text_content(self, content: str) -> str:
        """
        Process text content for better vector search

        Args:
            content: Raw text content

        Returns:
            Processed text content
        """
        if not content:
            return ""

        # Normalize whitespace
        processed = re.sub(r'\r\n', '\n', content)  # Normalize line endings
        processed = re.sub(r'[ \t]+', ' ', processed)  # Replace multiple spaces/tabs with single space

        # Clean up excessive newlines but preserve paragraph structure
        processed = re.sub(r'\n{4,}', '\n\n\n', processed)  # Reduce very long runs of newlines
        processed = re.sub(r'\n{3}', '\n\n', processed)  # Triple newlines to double

        # Fix common formatting issues
        processed = re.sub(r'([.!?])\s*\n\s*([A-Z])', r'\1 \2', processed)  # Fix sentence splits
        processed = re.sub(r'(\d)\s*\n\s*([a-zA-Z])', r'\1 \2', processed)  # Fix number-letter splits

        # Preserve important patterns
        # Keep URLs intact
        url_pattern = r'https?://[^\s\)]+'
        urls = re.findall(url_pattern, processed)
        for i, url in enumerate(urls):
            processed = processed.replace(url, f'URL_{i}_PLACEHOLDER', 1)

        # Keep email addresses intact
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, processed)
        for i, email in enumerate(emails):
            processed = processed.replace(email, f'EMAIL_{i}_PLACEHOLDER', 1)

        # Clean up punctuation spacing
        processed = re.sub(r'\s*([,.!?;:])\s*', r'\1 ', processed)  # Ensure space after punctuation
        processed = re.sub(r'\s+([,.!?;:])', r'\1', processed)  # Remove space before punctuation

        # Restore URLs and emails
        for i, url in enumerate(urls):
            processed = processed.replace(f'URL_{i}_PLACEHOLDER', url)

        for i, email in enumerate(emails):
            processed = processed.replace(f'EMAIL_{i}_PLACEHOLDER', email)

        # Final cleanup
        processed = processed.strip()
        processed = re.sub(r'\n{3,}', '\n\n', processed)  # Final cleanup of excessive newlines

        return processed

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Enhanced text file validation

        Args:
            file_path: Path to text file

        Returns:
            ValidationResult with text-specific validation
        """
        base_validation = super().validate_file(file_path)

        if not base_validation.is_valid:
            return base_validation

        try:
            # Additional text-specific validation
            encoding = self._detect_encoding(file_path)

            # Try to read and validate content
            with open(file_path, 'r', encoding=encoding) as file:
                sample = file.read(1024)

            # Check if file contains readable text (high text-to-binary ratio)
            if sample:
                text_chars = len([c for c in sample if c.isprintable()])
                total_chars = len(sample)
                text_ratio = text_chars / total_chars

                if text_ratio < 0.7:  # Less than 70% printable characters
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"File appears to be binary data (text ratio: {text_ratio:.2%})",
                        file_size=base_validation.file_size
                    )

            # Check for obvious binary file signatures
            binary_signatures = [
                b'\x00\x00\x00',  # Common binary start
                b'\xff\xfe',      # UTF-16 LE BOM
                b'\xfe\xff',      # UTF-16 BE BOM
            ]

            with open(file_path, 'rb') as file:
                header = file.read(16)
                for signature in binary_signatures:
                    if header.startswith(signature):
                        return ValidationResult(
                            is_valid=False,
                            error_message="File appears to be binary data, not text",
                            file_size=base_validation.file_size
                        )

            return base_validation

        except UnicodeDecodeError:
            return ValidationResult(
                is_valid=False,
                error_message="File contains non-text characters or unsupported encoding",
                file_size=base_validation.file_size
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Text file validation failed: {str(e)}"
            )