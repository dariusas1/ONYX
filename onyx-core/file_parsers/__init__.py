"""
File Parsers Package

This package provides parsers for multiple file formats with a unified interface
for text extraction, metadata generation, and content processing.
"""

from .base_parser import BaseParser, ParseResult, ValidationResult, FileMetadata
from .markdown_parser import MarkdownParser
from .pdf_parser import PDFParser
from .csv_parser import CSVParser
from .json_parser import JSONParser
from .text_parser import TextParser
from .image_parser import ImageParser

__all__ = [
    'BaseParser',
    'ParseResult',
    'ValidationResult',
    'FileMetadata',
    'MarkdownParser',
    'PDFParser',
    'CSVParser',
    'JSONParser',
    'TextParser',
    'ImageParser'
]