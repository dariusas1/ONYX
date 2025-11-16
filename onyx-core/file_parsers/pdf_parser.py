"""
PDF File Parser

This module handles parsing of PDF (.pdf) files using multiple libraries
for reliable text extraction with fallback options.
"""

import os
import re
from typing import Dict, Any, Optional
from datetime import datetime
from .base_parser import BaseParser, ParseResult, ValidationResult


class PDFParser(BaseParser):
    """Parser for PDF (.pdf) files"""

    SUPPORTED_EXTENSIONS = ['.pdf']
    MAGIC_NUMBERS = {
        '.pdf': b'%PDF-',  # PDF files start with %PDF-
    }

    def extract_content(self, file_path: str) -> ParseResult:
        """
        Extract text content from PDF file with multiple extraction methods

        Args:
            file_path: Path to the PDF file

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

            # Try different extraction methods in order of preference
            text_content = None
            metadata = None
            extraction_method = None

            # Method 1: Try pdfminer.six (most reliable for text-based PDFs)
            try:
                text_content, metadata = self._extract_with_pdfminer(file_path)
                extraction_method = 'pdfminer'
            except Exception as e:
                print(f"PDFMiner extraction failed: {e}")

            # Method 2: Try PyPDF2 as fallback
            if not text_content:
                try:
                    text_content, metadata = self._extract_with_pypdf2(file_path)
                    extraction_method = 'pypdf2'
                except Exception as e:
                    print(f"PyPDF2 extraction failed: {e}")

            # Method 3: Last resort - try to read as plain text (rare case)
            if not text_content:
                try:
                    text_content = self._extract_as_text(file_path)
                    extraction_method = 'text'
                except Exception as e:
                    print(f"Text extraction failed: {e}")

            if not text_content or not text_content.strip():
                return ParseResult(
                    success=False,
                    error_message="PDF appears to be empty, image-based, or corrupted. No text could be extracted."
                )

            # Clean and process the extracted text
            processed_content = self._process_pdf_text(text_content)

            # Create chunks for vector indexing
            chunks = self.chunk_text(processed_content)

            # Add extraction method to metadata
            metadata['extraction_method'] = extraction_method
            metadata['file_type'] = 'pdf'

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

        except Exception as e:
            return ParseResult(
                success=False,
                error_message=f"Failed to parse PDF file: {str(e)}"
            )

    def _extract_with_pdfminer(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """
        Extract text using pdfminer.six library

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (extracted_text, metadata)
        """
        try:
            from pdfminer.high_level import extract_text
            from pdfminer.layout import LAParams
            from pdfminer.pdfparser import PDFParser
            from pdfminer.pdfdocument import PDFDocument
            from pdfminer.pdfpage import PDFPage

            # Extract text with optimized parameters
            text = extract_text(
                file_path,
                laparams=LAParams(
                    detect_vertical=True,  # Better text flow detection
                    all_texts=True,  # Extract all text including small fonts
                    char_margin=1.0,  # Tighter character grouping
                    line_margin=0.5,  # Better line detection
                    word_margin=0.1,  # Better word detection
                )
            )

            # Extract additional metadata
            metadata = self._extract_pdf_metadata(file_path)

            return text, metadata

        except ImportError:
            raise ImportError("pdfminer.six not available. Install with: pip install pdfminer.six")
        except Exception as e:
            raise Exception(f"PDFMiner extraction failed: {str(e)}")

    def _extract_with_pypdf2(self, file_path: str) -> tuple[str, Dict[str, Any]]:
        """
        Extract text using PyPDF2 library as fallback

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (extracted_text, metadata)
        """
        try:
            from PyPDF2 import PdfReader

            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                text_content = []
                page_count = len(reader.pages)

                for page_num, page in enumerate(reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(f"PAGE {page_num}:\n{page_text}")
                    except Exception as e:
                        print(f"Failed to extract text from page {page_num}: {e}")
                        continue

                text = "\n\n".join(text_content)

                # Extract metadata
                metadata = {
                    'page_count': page_count,
                    'has_text': len(text.strip()) > 0,
                    'extraction_quality': 'pypdf2'
                }

                # Try to get PDF metadata
                if hasattr(reader, 'metadata') and reader.metadata:
                    for key, value in reader.metadata.items():
                        if key and value:
                            metadata[f'pdf_{key.lower()}'] = str(value)

                return text, metadata

        except ImportError:
            raise ImportError("PyPDF2 not available. Install with: pip install PyPDF2")
        except Exception as e:
            raise Exception(f"PyPDF2 extraction failed: {str(e)}")

    def _extract_as_text(self, file_path: str) -> str:
        """
        Last resort: try to read PDF as plain text (rare edge case)

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Look for text patterns in PDF content
            text_lines = []
            for line in content.split('\n'):
                # Skip PDF-specific syntax and binary content
                if not re.match(r'^\s*(%|/|obj|endobj|stream|endstream)', line):
                    # Extract printable ASCII characters
                    clean_line = re.sub(r'[^\x20-\x7E\n\r\t]', '', line)
                    if clean_line.strip():
                        text_lines.append(clean_line)

            return '\n'.join(text_lines)

        except Exception as e:
            raise Exception(f"Text extraction failed: {str(e)}")

    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive PDF metadata

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary of PDF metadata
        """
        metadata = {
            'file_type': 'pdf',
            'has_images': False,
            'is_encrypted': False,
            'pdf_version': None,
        }

        try:
            # Try to extract metadata using pdfminer
            from pdfminer.pdfparser import PDFParser
            from pdfminer.pdfdocument import PDFDocument

            with open(file_path, 'rb') as file:
                parser = PDFParser(file)
                document = PDFDocument(parser)

                # Get PDF version
                if hasattr(parser, 'header') and parser.header:
                    metadata['pdf_version'] = parser.header.decode('utf-8', errors='ignore')

                # Check if encrypted
                metadata['is_encrypted'] = document.is_encrypted

                # Get document info
                if hasattr(document, 'info') and document.info:
                    for key, value in document.info[0].items():
                        if key and value:
                            metadata[f'pdf_{key.lower()}'] = str(value)

        except Exception:
            pass  # Metadata extraction failures should not stop processing

        # Try to get page count using PyPDF2
        try:
            from PyPDF2 import PdfReader
            with open(file_path, 'rb') as file:
                reader = PdfReader(file)
                metadata['page_count'] = len(reader.pages)
        except Exception:
            pass

        return metadata

    def _process_pdf_text(self, text: str) -> str:
        """
        Process extracted PDF text for better vector search

        Args:
            text: Raw extracted text

        Returns:
            Processed text
        """
        if not text:
            return ""

        # Remove PDF artifacts and common extraction errors
        text = re.sub(r'\f', '\n\n', text)  # Form feeds to paragraph breaks
        text = re.sub(r'\x00', '', text)  # Remove null characters
        text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)  # Keep only ASCII printable chars

        # Fix common spacing issues
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between lower->upper case
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)  # Add space after punctuation
        text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)  # Add space between numbers and letters

        # Remove excessive whitespace
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r' +\n', '\n', text)  # Remove trailing spaces
        text = re.sub(r'\n +', '\n', text)  # Remove leading spaces

        # Fix common PDF extraction artifacts
        artifacts = [
            r'\b\d+\s*of\s*\d+\b',  # Page numbers like "1 of 10"
            r'^Page\s*\d+\s*$',  # Page headers
            r'^\s*[-\.]\s*$',  # Separator lines
            r'\s{2,}',  # Multiple spaces (redundant with above but catches edge cases)
        ]

        for artifact in artifacts:
            text = re.sub(artifact, ' ', text, flags=re.MULTILINE)

        # Preserve paragraph structure but clean up
        paragraphs = text.split('\n\n')
        cleaned_paragraphs = []

        for para in paragraphs:
            para = para.strip()
            if len(para) > 10:  # Keep substantial paragraphs
                cleaned_paragraphs.append(para)

        return '\n\n'.join(cleaned_paragraphs)

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Enhanced PDF file validation

        Args:
            file_path: Path to PDF file

        Returns:
            ValidationResult with PDF-specific validation
        """
        base_validation = super().validate_file(file_path)

        if not base_validation.is_valid:
            return base_validation

        try:
            # Additional PDF-specific validation
            with open(file_path, 'rb') as f:
                header = f.read(16)

            # Check PDF signature
            if not header.startswith(b'%PDF-'):
                return ValidationResult(
                    is_valid=False,
                    error_message="File does not have valid PDF signature (should start with %PDF-)",
                    file_size=base_validation.file_size
                )

            # Try to read basic PDF structure
            try:
                from PyPDF2 import PdfReader
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    if len(reader.pages) == 0:
                        return ValidationResult(
                            is_valid=False,
                            error_message="PDF appears to have no pages",
                            file_size=base_validation.file_size
                        )
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"PDF structure validation failed: {str(e)}",
                    file_size=base_validation.file_size
                )

            return base_validation

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"PDF validation failed: {str(e)}"
            )