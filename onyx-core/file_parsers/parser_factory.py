"""
Parser Factory

This module provides a factory for creating appropriate file parsers
based on file extensions and format detection.
"""

import os
from typing import Dict, Any, Optional
from .base_parser import BaseParser, ParseResult, ValidationResult
from .markdown_parser import MarkdownParser
from .pdf_parser import PDFParser
from .csv_parser import CSVParser
from .json_parser import JSONParser
from .text_parser import TextParser
from .image_parser import ImageParser


class ParserFactory:
    """
    Factory class for creating appropriate file parsers
    """

    # Mapping of file extensions to parser classes
    PARSER_MAPPING = {
        # Documents
        '.md': MarkdownParser,
        '.markdown': MarkdownParser,
        '.pdf': PDFParser,

        # Structured Data
        '.csv': CSVParser,
        '.json': JSONParser,
        '.jsonl': JSONParser,

        # Text
        '.txt': TextParser,
        '.text': TextParser,
        '.log': TextParser,

        # Images
        '.png': ImageParser,
        '.jpg': ImageParser,
        '.jpeg': ImageParser,
        '.webp': ImageParser,
    }

    # All supported extensions for quick lookup
    SUPPORTED_EXTENSIONS = set(PARSER_MAPPING.keys())

    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        """
        Get appropriate parser for file based on extension

        Args:
            file_path: Path to the file

        Returns:
            Parser instance for the file type

        Raises:
            ValueError: If file type is not supported
        """
        extension = cls._get_file_extension(file_path)

        if extension not in cls.PARSER_MAPPING:
            raise ValueError(f"Unsupported file type: {extension}. Supported types: {', '.join(cls.SUPPORTED_EXTENSIONS)}")

        parser_class = cls.PARSER_MAPPING[extension]
        return parser_class()

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """
        Get list of all supported file extensions

        Returns:
            List of supported extensions
        """
        return sorted(cls.SUPPORTED_EXTENSIONS)

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        Check if file type is supported

        Args:
            file_path: Path to the file

        Returns:
            True if file type is supported
        """
        extension = cls._get_file_extension(file_path)
        return extension in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def _get_file_extension(cls, file_path: str) -> str:
        """
        Get file extension in lowercase

        Args:
            file_path: Path to the file

        Returns:
            File extension with dot (e.g., '.pdf')
        """
        return os.path.splitext(file_path)[1].lower()

    @classmethod
    def detect_file_type(cls, file_path: str) -> Optional[str]:
        """
        Detect file type by examining file content and extension

        Args:
            file_path: Path to the file

        Returns:
            Detected file extension or None if unknown
        """
        extension = cls._get_file_extension(file_path)

        # If extension is known, use it
        if extension in cls.SUPPORTED_EXTENSIONS:
            return extension

        # Try to detect by magic number
        try:
            with open(file_path, 'rb') as file:
                header = file.read(32)  # Read first 32 bytes

            # Check magic numbers for each supported type
            for ext, parser_class in cls.PARSER_MAPPING.items():
                parser = parser_class()
                magic_number = parser._get_magic_number(file_path)
                if magic_number:
                    detected_format = parser._detect_format_by_magic_number(magic_number)
                    if detected_format:
                        return detected_format

        except Exception:
            pass

        return None

    @classmethod
    def validate_file(cls, file_path: str) -> ValidationResult:
        """
        Validate file and check if it's supported

        Args:
            file_path: Path to the file

        Returns:
            ValidationResult with validation status
        """
        try:
            # Check file existence
            if not os.path.exists(file_path):
                return ValidationResult(
                    is_valid=False,
                    error_message="File does not exist"
                )

            # Detect file type
            detected_extension = cls.detect_file_type(file_path)

            if not detected_extension:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsupported file type. Supported formats: {', '.join(cls.get_supported_extensions())}"
                )

            # Get parser and validate file
            parser = cls.get_parser(file_path)
            return parser.validate_file(file_path)

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"File validation failed: {str(e)}"
            )

    @classmethod
    def parse_file(cls, file_path: str, user_id: str) -> ParseResult:
        """
        Parse file using appropriate parser

        Args:
            file_path: Path to the file
            user_id: User ID for permission metadata

        Returns:
            ParseResult with extracted content
        """
        try:
            # Validate file first
            validation = cls.validate_file(file_path)
            if not validation.is_valid:
                return ParseResult(
                    success=False,
                    error_message=validation.error_message
                )

            # Get parser and parse file
            parser = cls.get_parser(file_path)
            result = parser.extract_content(file_path)

            if result.success and result.metadata:
                # Add file metadata to result metadata
                file_metadata = parser.get_file_metadata(file_path, user_id)
                result.metadata.update({
                    'file_metadata': file_metadata.__dict__
                })

            return result

        except ValueError as e:
            return ParseResult(
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            return ParseResult(
                success=False,
                error_message=f"File parsing failed: {str(e)}"
            )

    @classmethod
    def get_parser_info(cls, file_path: str) -> Dict[str, Any]:
        """
        Get information about parser that would be used for file

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with parser information
        """
        info = {
            'file_path': file_path,
            'file_exists': os.path.exists(file_path),
            'file_extension': cls._get_file_extension(file_path),
            'is_supported': False,
            'parser_class': None,
            'supported_extensions': cls.get_supported_extensions(),
        }

        if info['file_exists']:
            detected_extension = cls.detect_file_type(file_path)
            if detected_extension:
                info.update({
                    'detected_extension': detected_extension,
                    'is_supported': True,
                    'parser_class': cls.PARSER_MAPPING[detected_extension].__name__
                })

            # Get file size
            try:
                info['file_size'] = os.path.getsize(file_path)
            except Exception:
                info['file_size'] = None

        return info


# Convenience function for quick parsing
def parse_file(file_path: str, user_id: str) -> ParseResult:
    """
    Convenience function to parse a file

    Args:
        file_path: Path to the file
        user_id: User ID for permission metadata

    Returns:
        ParseResult with extracted content
    """
    return ParserFactory.parse_file(file_path, user_id)


# Convenience function to check file support
def is_file_supported(file_path: str) -> bool:
    """
    Convenience function to check if file type is supported

    Args:
        file_path: Path to the file

    Returns:
        True if file type is supported
    """
    return ParserFactory.is_supported(file_path)