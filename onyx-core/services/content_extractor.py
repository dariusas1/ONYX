"""
Content Extraction Service

This module handles content extraction from various file types:
- Google Docs (export to Markdown/HTML)
- Google Sheets (export to CSV)
- PDFs (text extraction)
- Plain text files
"""

import io
from typing import Optional
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import PyPDF2

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Service for extracting text content from various file types"""

    # MIME type mappings
    MIME_GOOGLE_DOC = "application/vnd.google-apps.document"
    MIME_GOOGLE_SHEET = "application/vnd.google-apps.spreadsheet"
    MIME_GOOGLE_PRESENTATION = "application/vnd.google-apps.presentation"
    MIME_PDF = "application/pdf"
    MIME_PLAIN_TEXT = "text/plain"
    MIME_MARKDOWN = "text/markdown"
    MIME_HTML = "text/html"

    # Supported MIME types
    SUPPORTED_MIME_TYPES = {
        MIME_GOOGLE_DOC,
        MIME_GOOGLE_SHEET,
        MIME_PDF,
        MIME_PLAIN_TEXT,
        MIME_MARKDOWN,
        MIME_HTML,
    }

    def __init__(self, drive_service):
        """
        Initialize content extractor

        Args:
            drive_service: Authenticated Google Drive API service
        """
        self.drive_service = drive_service

    def is_supported(self, mime_type: str) -> bool:
        """Check if MIME type is supported for extraction"""
        return mime_type in self.SUPPORTED_MIME_TYPES

    def extract_content(self, file_id: str, mime_type: str, file_name: str) -> Optional[str]:
        """
        Extract text content from a file

        Args:
            file_id: Google Drive file ID
            mime_type: File MIME type
            file_name: File name (for logging)

        Returns:
            Extracted text content or None if extraction fails
        """
        try:
            if not self.is_supported(mime_type):
                logger.warning(f"Unsupported MIME type {mime_type} for file {file_name}")
                return None

            # Route to appropriate extractor
            if mime_type == self.MIME_GOOGLE_DOC:
                return self._extract_google_doc(file_id, file_name)
            elif mime_type == self.MIME_GOOGLE_SHEET:
                return self._extract_google_sheet(file_id, file_name)
            elif mime_type == self.MIME_PDF:
                return self._extract_pdf(file_id, file_name)
            elif mime_type in [self.MIME_PLAIN_TEXT, self.MIME_MARKDOWN, self.MIME_HTML]:
                return self._extract_text_file(file_id, file_name)
            else:
                logger.warning(f"No extractor implemented for {mime_type}")
                return None

        except Exception as e:
            logger.error(f"Content extraction failed for {file_name} ({file_id}): {e}")
            return None

    def _extract_google_doc(self, file_id: str, file_name: str) -> Optional[str]:
        """
        Extract content from Google Doc as plain text

        We try multiple export formats in order of preference:
        1. Plain text (simplest, no formatting)
        2. HTML (can be parsed if needed)
        """
        try:
            # Try exporting as plain text first
            try:
                request = self.drive_service.files().export_media(
                    fileId=file_id, mimeType="text/plain"
                )
                content = request.execute().decode("utf-8")
                logger.info(f"Extracted Google Doc as plain text: {file_name}")
                return content
            except Exception as e:
                logger.warning(f"Plain text export failed for {file_name}, trying HTML: {e}")

            # Fallback to HTML export
            request = self.drive_service.files().export_media(
                fileId=file_id, mimeType="text/html"
            )
            html_content = request.execute().decode("utf-8")

            # Basic HTML to text conversion (strip tags)
            # In production, consider using BeautifulSoup or html2text
            import re

            text_content = re.sub(r"<[^>]+>", "", html_content)
            text_content = re.sub(r"\s+", " ", text_content).strip()

            logger.info(f"Extracted Google Doc as HTML (converted to text): {file_name}")
            return text_content

        except Exception as e:
            logger.error(f"Google Doc extraction failed for {file_name}: {e}")
            return None

    def _extract_google_sheet(self, file_id: str, file_name: str) -> Optional[str]:
        """
        Extract content from Google Sheet as CSV

        Args:
            file_id: Google Drive file ID
            file_name: File name

        Returns:
            CSV content as text
        """
        try:
            # Export as CSV
            request = self.drive_service.files().export_media(
                fileId=file_id, mimeType="text/csv"
            )
            csv_content = request.execute().decode("utf-8")

            logger.info(f"Extracted Google Sheet as CSV: {file_name}")
            return csv_content

        except Exception as e:
            logger.error(f"Google Sheet extraction failed for {file_name}: {e}")
            return None

    def _extract_pdf(self, file_id: str, file_name: str) -> Optional[str]:
        """
        Extract text content from PDF

        Args:
            file_id: Google Drive file ID
            file_name: File name

        Returns:
            Extracted text or None
        """
        try:
            # Download PDF
            request = self.drive_service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            file_buffer.seek(0)

            # Extract text using PyPDF2
            pdf_reader = PyPDF2.PdfReader(file_buffer)
            text_content = []

            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())

            extracted_text = "\n\n".join(text_content).strip()

            if not extracted_text:
                logger.warning(f"No text extracted from PDF: {file_name}")
                return None

            logger.info(f"Extracted PDF text ({len(pdf_reader.pages)} pages): {file_name}")
            return extracted_text

        except Exception as e:
            logger.error(f"PDF extraction failed for {file_name}: {e}")
            return None

    def _extract_text_file(self, file_id: str, file_name: str) -> Optional[str]:
        """
        Extract content from plain text file

        Args:
            file_id: Google Drive file ID
            file_name: File name

        Returns:
            File content as text
        """
        try:
            # Download file
            request = self.drive_service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            file_buffer.seek(0)
            content = file_buffer.read().decode("utf-8")

            logger.info(f"Extracted text file: {file_name}")
            return content

        except Exception as e:
            logger.error(f"Text file extraction failed for {file_name}: {e}")
            return None


def create_content_extractor(drive_service) -> ContentExtractor:
    """
    Factory function to create a content extractor

    Args:
        drive_service: Authenticated Google Drive API service

    Returns:
        ContentExtractor instance
    """
    return ContentExtractor(drive_service)
