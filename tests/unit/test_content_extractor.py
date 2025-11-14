"""
Unit Tests for Content Extractor

Tests for content extraction from various file types.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import io


class TestContentExtractor:
    """Tests for ContentExtractor class"""

    @pytest.fixture
    def mock_drive_service(self):
        """Create a mock Google Drive service"""
        return Mock()

    @pytest.fixture
    def content_extractor(self, mock_drive_service):
        """Create a ContentExtractor instance with mock service"""
        from services.content_extractor import ContentExtractor

        return ContentExtractor(mock_drive_service)

    def test_is_supported(self, content_extractor):
        """Test MIME type support detection"""
        # Supported types
        assert content_extractor.is_supported("application/vnd.google-apps.document")
        assert content_extractor.is_supported("application/vnd.google-apps.spreadsheet")
        assert content_extractor.is_supported("application/pdf")
        assert content_extractor.is_supported("text/plain")
        assert content_extractor.is_supported("text/markdown")

        # Unsupported types
        assert not content_extractor.is_supported("image/jpeg")
        assert not content_extractor.is_supported("video/mp4")
        assert not content_extractor.is_supported("application/vnd.google-apps.folder")

    def test_extract_google_doc_plain_text(self, content_extractor, mock_drive_service):
        """Test Google Doc extraction (plain text export)"""
        # Mock the export response
        mock_export = Mock()
        mock_export.execute.return_value = b"# Test Document\n\nThis is test content."

        mock_drive_service.files.return_value.export_media.return_value = mock_export

        # Extract content
        content = content_extractor._extract_google_doc("file-123", "Test Doc")

        assert content is not None
        assert "Test Document" in content
        assert "test content" in content

    def test_extract_google_doc_html_fallback(
        self, content_extractor, mock_drive_service
    ):
        """Test Google Doc extraction with HTML fallback"""
        # Mock plain text export to fail
        mock_export_text = Mock()
        mock_export_text.execute.side_effect = Exception("Plain text export failed")

        # Mock HTML export to succeed
        mock_export_html = Mock()
        mock_export_html.execute.return_value = b"<html><body><h1>Test</h1><p>Content</p></body></html>"

        # Configure mock to return different exports
        def export_side_effect(fileId, mimeType):
            if mimeType == "text/plain":
                return mock_export_text
            elif mimeType == "text/html":
                return mock_export_html
            raise ValueError(f"Unexpected mime type: {mimeType}")

        mock_drive_service.files.return_value.export_media.side_effect = export_side_effect

        # Extract content
        content = content_extractor._extract_google_doc("file-123", "Test Doc")

        assert content is not None
        assert "Test" in content
        assert "Content" in content

    def test_extract_google_sheet(self, content_extractor, mock_drive_service):
        """Test Google Sheet extraction"""
        # Mock CSV export
        mock_export = Mock()
        mock_export.execute.return_value = b"Name,Value\nItem1,100\nItem2,200"

        mock_drive_service.files.return_value.export_media.return_value = mock_export

        # Extract content
        content = content_extractor._extract_google_sheet("file-123", "Test Sheet")

        assert content is not None
        assert "Name,Value" in content
        assert "Item1,100" in content

    @patch("services.content_extractor.PyPDF2")
    def test_extract_pdf(
        self, mock_pypdf2, content_extractor, mock_drive_service
    ):
        """Test PDF extraction"""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "PDF page content"

        mock_pdf_reader = Mock()
        mock_pdf_reader.pages = [mock_page, mock_page]

        mock_pypdf2.PdfReader.return_value = mock_pdf_reader

        # Mock file download
        mock_media = Mock()

        def download_side_effect(file_buffer, media):
            # Simulate download progress
            return (Mock(progress=lambda: 1.0), True)

        with patch(
            "services.content_extractor.MediaIoBaseDownload",
            return_value=Mock(next_chunk=Mock(return_value=(Mock(), True))),
        ):
            # Extract content
            content = content_extractor._extract_pdf("file-123", "Test PDF")

            assert content is not None
            assert "PDF page content" in content

    def test_extract_text_file(self, content_extractor, mock_drive_service):
        """Test plain text file extraction"""
        # Mock file download
        with patch(
            "services.content_extractor.MediaIoBaseDownload"
        ) as mock_downloader:
            mock_downloader.return_value.next_chunk.return_value = (Mock(), True)

            # Mock get_media
            mock_media = Mock()
            mock_drive_service.files.return_value.get_media.return_value = mock_media

            # Mock the file buffer reading
            with patch("services.content_extractor.io.BytesIO") as mock_bytesio:
                mock_buffer = Mock()
                mock_buffer.read.return_value = b"Plain text file content"
                mock_bytesio.return_value = mock_buffer

                content = content_extractor._extract_text_file("file-123", "Test.txt")

                assert content is not None
                assert "Plain text file content" in content

    def test_extract_unsupported_mime_type(self, content_extractor):
        """Test extraction of unsupported MIME type"""
        content = content_extractor.extract_content(
            "file-123", "image/jpeg", "image.jpg"
        )

        assert content is None

    def test_extract_content_error_handling(
        self, content_extractor, mock_drive_service
    ):
        """Test error handling during content extraction"""
        # Mock export to raise an error
        mock_export = Mock()
        mock_export.execute.side_effect = Exception("API error")

        mock_drive_service.files.return_value.export_media.return_value = mock_export

        # Should return None on error, not raise
        content = content_extractor.extract_content(
            "file-123", "application/vnd.google-apps.document", "Test Doc"
        )

        assert content is None


def test_create_content_extractor():
    """Test content extractor factory function"""
    from services.content_extractor import create_content_extractor

    mock_service = Mock()
    extractor = create_content_extractor(mock_service)

    assert extractor is not None
    assert extractor.drive_service is mock_service
