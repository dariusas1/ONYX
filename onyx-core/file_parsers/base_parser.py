"""
Base Parser Interface and Data Classes

This module defines the abstract base class for all file parsers and
common data structures used across different file format parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class ValidationResult:
    """Result of file validation"""
    is_valid: bool
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    detected_format: Optional[str] = None
    magic_number: Optional[str] = None


@dataclass
class ParseResult:
    """Result of file parsing"""
    success: bool
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    chunks: Optional[List[str]] = None
    total_chunks: Optional[int] = None
    file_size: Optional[int] = None
    processing_time: Optional[float] = None


@dataclass
class FileMetadata:
    """Metadata for uploaded files"""
    filename: str
    file_type: str
    file_size: int
    upload_timestamp: datetime
    user_id: str
    content_hash: Optional[str] = None
    permissions: Optional[List[str]] = None


class BaseParser(ABC):
    """Abstract base class for file parsers"""

    # Supported file extensions for this parser
    SUPPORTED_EXTENSIONS: List[str] = []

    # Maximum file size in bytes (default 50MB)
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Magic number signatures for file type validation
    MAGIC_NUMBERS: Dict[str, bytes] = {}

    def __init__(self):
        """Initialize parser with common settings"""
        self.max_file_size = self.MAX_FILE_SIZE

    @abstractmethod
    def extract_content(self, file_path: str) -> ParseResult:
        """
        Extract text content and metadata from file

        Args:
            file_path: Path to the file to parse

        Returns:
            ParseResult with content and metadata
        """
        pass

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Validate file format and integrity

        Args:
            file_path: Path to the file to validate

        Returns:
            ValidationResult with validation status
        """
        import os
        import hashlib

        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return ValidationResult(
                    is_valid=False,
                    error_message="File does not exist"
                )

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File size {file_size} bytes exceeds maximum {self.max_file_size} bytes",
                    file_size=file_size
                )

            # Check file extension
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension not in self.SUPPORTED_EXTENSIONS:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"File extension '{file_extension}' not supported. Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}",
                    file_size=file_size
                )

            # Check magic number if available
            magic_number = self._get_magic_number(file_path)
            detected_format = self._detect_format_by_magic_number(magic_number)

            # Validate magic number matches expected format
            if detected_format and detected_format not in self.SUPPORTED_EXTENSIONS:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Magic number indicates '{detected_format}' but parser expects one of: {', '.join(self.SUPPORTED_EXTENSIONS)}",
                    file_size=file_size,
                    magic_number=magic_number.hex() if magic_number else None
                )

            return ValidationResult(
                is_valid=True,
                file_size=file_size,
                detected_format=file_extension,
                magic_number=magic_number.hex() if magic_number else None
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Validation failed: {str(e)}"
            )

    def _get_magic_number(self, file_path: str, bytes_to_read: int = 16) -> Optional[bytes]:
        """
        Read magic number bytes from file start

        Args:
            file_path: Path to file
            bytes_to_read: Number of bytes to read from start

        Returns:
            Magic number bytes or None if file cannot be read
        """
        try:
            with open(file_path, 'rb') as f:
                return f.read(bytes_to_read)
        except Exception:
            return None

    def _detect_format_by_magic_number(self, magic_number: Optional[bytes]) -> Optional[str]:
        """
        Detect file format by magic number

        Args:
            magic_number: First bytes of file

        Returns:
            File extension or None if unknown
        """
        if not magic_number:
            return None

        for ext, signature in self.MAGIC_NUMBERS.items():
            if magic_number.startswith(signature):
                return ext

        return None

    def _calculate_content_hash(self, content: str) -> str:
        """
        Calculate SHA-256 hash of content for deduplication

        Args:
            content: Text content to hash

        Returns:
            SHA-256 hash as hexadecimal string
        """
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks for better vector indexing

        Args:
            text: Text to chunk
            chunk_size: Target chunk size in tokens (approximately 375 words)
            overlap: Overlap between chunks in tokens

        Returns:
            List of text chunks
        """
        import tiktoken

        try:
            # Use tiktoken for accurate token counting
            encoding = tiktoken.encoding_for_model("text-embedding-3-small")
            tokens = encoding.encode(text)

            if len(tokens) <= chunk_size:
                return [text]

            chunks = []
            start_idx = 0

            while start_idx < len(tokens):
                # Calculate end index with overlap
                end_idx = min(start_idx + chunk_size, len(tokens))

                # Decode tokens back to text
                chunk_tokens = tokens[start_idx:end_idx]
                chunk_text = encoding.decode(chunk_tokens)

                # Clean up chunk text (remove leading/trailing whitespace)
                chunk_text = chunk_text.strip()

                if chunk_text:
                    chunks.append(chunk_text)

                # Move start position with overlap
                start_idx = max(0, end_idx - overlap)

            return chunks

        except Exception:
            # Fallback to simple word-based chunking if tiktoken fails
            words = text.split()
            if len(words) <= chunk_size * 0.75:  # Approximate token to word ratio
                return [text]

            chunks = []
            start_idx = 0

            while start_idx < len(words):
                end_idx = min(start_idx + int(chunk_size * 0.75), len(words))
                chunk_words = words[start_idx:end_idx]
                chunk_text = ' '.join(chunk_words).strip()

                if chunk_text:
                    chunks.append(chunk_text)

                # Move start position with overlap
                start_idx = max(0, end_idx - int(overlap * 0.75))

            return chunks

    def get_file_metadata(self, file_path: str, user_id: str) -> FileMetadata:
        """
        Get comprehensive metadata for uploaded file

        Args:
            file_path: Path to file
            user_id: User ID who uploaded the file

        Returns:
            FileMetadata object
        """
        import os
        from datetime import datetime

        filename = os.path.basename(file_path)
        file_type = os.path.splitext(filename)[1].lower()
        file_size = os.path.getsize(file_path)
        upload_timestamp = datetime.utcnow()

        return FileMetadata(
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            upload_timestamp=upload_timestamp,
            user_id=user_id,
            permissions=[f"user:{user_id}", "team:*"]  # User + team access
        )