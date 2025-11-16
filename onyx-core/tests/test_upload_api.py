"""
File Upload API Tests

Tests for the file upload functionality including validation,
processing, and integration with the RAG system.
"""

import pytest
import asyncio
import tempfile
import os
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from io import BytesIO

from main import app
from api.upload import FileUploadResponse, FileProcessingResult
from file_parsers.parser_factory import ParserFactory

client = TestClient(app)


class TestFileUploadAPI:
    """Test suite for file upload API endpoints"""

    def test_upload_endpoint_exists(self):
        """Test that the upload endpoint is accessible"""
        response = client.get("/api/upload/formats")
        assert response.status_code == 200
        data = response.json()
        assert "supported_extensions" in data
        assert "max_file_size_mb" in data

    def test_supported_formats(self):
        """Test supported formats endpoint"""
        response = client.get("/api/upload/formats")
        assert response.status_code == 200

        data = response.json()
        supported_formats = data["supported_extensions"]

        # Check that all required formats are supported
        required_formats = ['.md', '.pdf', '.csv', '.json', '.txt', '.png', '.jpg', '.jpeg']
        for fmt in required_formats:
            assert fmt in supported_formats

    def test_upload_status(self):
        """Test upload status endpoint"""
        response = client.get("/api/upload/status")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "supported_formats" in data
        assert "limits" in data

    @pytest.mark.asyncio
    async def test_file_validation(self):
        """Test file validation functionality"""
        from api.upload import validate_upload_file

        # Test valid markdown file
        valid_md_content = b"# Test Document\n\nThis is a test markdown file."

        class MockFile:
            def __init__(self, content, filename):
                self.file = BytesIO(content)
                self.filename = filename

        mock_file = MockFile(valid_md_content, "test.md")
        validation = validate_upload_file(mock_file)

        assert validation.is_valid == True
        assert validation.filename == "test.md"
        assert validation.detected_format == "markdown"

    @patch('api.upload.process_uploaded_file')
    @patch('api.upload.require_authenticated_user')
    def test_upload_files_success(self, mock_auth, mock_process):
        """Test successful file upload"""
        # Mock authentication
        mock_auth.return_value = {"email": "test@example.com"}

        # Mock successful file processing
        mock_result = FileProcessingResult(
            filename="test.md",
            status="success",
            chunks_count=5,
            doc_id="test_doc_123",
            processing_time=1.5
        )
        mock_process.return_value = mock_result

        # Create test file
        test_content = b"# Test Document\n\nThis is a test markdown file."

        response = client.post(
            "/api/upload/files",
            files={"files": ("test.md", test_content, "text/markdown")},
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["total_files"] == 1
        assert data["successful_files"] == 1
        assert len(data["results"]) == 1

    def test_upload_files_no_auth(self):
        """Test file upload without authentication"""
        test_content = b"# Test Document"

        response = client.post(
            "/api/upload/files",
            files={"files": ("test.md", test_content, "text/markdown")}
        )

        # Should require authentication
        assert response.status_code == 401 or response.status_code == 403

    def test_upload_files_too_many(self):
        """Test uploading too many files"""
        @patch('api.upload.require_authenticated_user')
        def test_with_auth(mock_auth):
            mock_auth.return_value = {"email": "test@example.com"}

            # Create 15 test files (exceeding MAX_FILES_PER_REQUEST = 10)
            files = []
            for i in range(15):
                files.append(("files", (f"test_{i}.md", b"# Test {i}", "text/markdown")))

            response = client.post(
                "/api/upload/files",
                files=files,
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 400
            data = response.json()
            assert "Maximum" in data["detail"] and "files allowed" in data["detail"]

        test_with_auth()

    def test_upload_large_file(self):
        """Test uploading file that exceeds size limit"""
        # Create a file larger than 50MB (simulated)
        large_content = b"x" * (60 * 1024 * 1024)  # 60MB

        @patch('api.upload.require_authenticated_user')
        def test_with_auth(mock_auth):
            mock_auth.return_value = {"email": "test@example.com"}

            response = client.post(
                "/api/upload/files",
                files={"files": ("large.txt", large_content, "text/plain")},
                headers={"Authorization": "Bearer test_token"}
            )

            # Should be rejected due to size
            assert response.status_code == 413 or response.status_code == 400

        test_with_auth()


class TestParserFactory:
    """Test suite for parser factory"""

    def test_get_supported_extensions(self):
        """Test getting supported extensions"""
        extensions = ParserFactory.get_supported_extensions()

        required_extensions = ['.md', '.pdf', '.csv', '.json', '.txt', '.png', '.jpg', '.jpeg']
        for ext in required_extensions:
            assert ext in extensions

    def test_file_format_detection(self):
        """Test file format detection by extension"""
        # Test markdown detection
        parser = ParserFactory.get_parser("test.md")
        assert parser is not None
        assert parser.__class__.__name__ == "MarkdownParser"

        # Test PDF detection
        parser = ParserFactory.get_parser("test.pdf")
        assert parser is not None
        assert parser.__class__.__name__ == "PDFParser"

        # Test CSV detection
        parser = ParserFactory.get_parser("test.csv")
        assert parser is not None
        assert parser.__class__.__name__ == "CSVParser"

        # Test JSON detection
        parser = ParserFactory.get_parser("test.json")
        assert parser is not None
        assert parser.__class__.__name__ == "JSONParser"

        # Test unsupported format
        parser = ParserFactory.get_parser("test.xyz")
        assert parser is None


class TestFileUploadIntegration:
    """Integration tests for file upload system"""

    @pytest.mark.asyncio
    async def test_end_to_end_markdown_upload(self):
        """Test complete markdown upload flow"""
        # Create temporary markdown file
        test_content = """# Test Document

## Introduction
This is a test markdown document for file upload testing.

## Features
- **Bold text**
- *Italic text*
- `Code blocks`

### Code Example
```python
def hello_world():
    print("Hello, World!")
    return True
```

## Conclusion
This document should be properly parsed and indexed.
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(test_content)
            temp_file_path = f.name

        try:
            # Test validation
            from api.upload import validate_upload_file

            class MockFile:
                def __init__(self, file_path):
                    self.file = open(file_path, 'rb')
                    self.filename = os.path.basename(file_path)

                def __del__(self):
                    self.file.close()

            mock_file = MockFile(temp_file_path)
            validation = validate_upload_file(mock_file)

            assert validation.is_valid == True
            assert validation.detected_format == "markdown"
            assert validation.file_size > 0

            # Test parsing
            parser = ParserFactory.get_parser(temp_file_path)
            assert parser is not None

            parse_result = parser.parse_file(temp_file_path, "test_user")
            assert parse_result.success == True
            assert len(parse_result.content) > 0
            assert "Test Document" in parse_result.content
            assert "hello_world" in parse_result.content

        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_csv_parsing_and_chunking(self):
        """Test CSV parsing and content chunking"""
        csv_content = """Name,Age,City
John Doe,30,New York
Jane Smith,25,San Francisco
Bob Johnson,35,Chicago
Alice Brown,28,Boston
Charlie Wilson,32,Seattle"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file_path = f.name

        try:
            parser = ParserFactory.get_parser(temp_file_path)
            parse_result = parser.parse_file(temp_file_path, "test_user")

            assert parse_result.success == True
            assert len(parse_result.content) > 0
            assert "John Doe" in parse_result.content
            assert "New York" in parse_result.content

            # Verify metadata
            if parse_result.metadata:
                assert 'row_count' in parse_result.metadata
                assert parse_result.metadata['row_count'] >= 5  # At least 5 data rows

        finally:
            os.unlink(temp_file_path)

    @pytest.mark.asyncio
    async def test_json_parsing_structure(self):
        """Test JSON parsing and structure extraction"""
        json_content = {
            "title": "Test Document",
            "description": "A test JSON document",
            "data": {
                "users": [
                    {"name": "John", "age": 30, "active": True},
                    {"name": "Jane", "age": 25, "active": False}
                ],
                "settings": {
                    "theme": "dark",
                    "notifications": True,
                    "max_items": 100
                }
            },
            "version": "1.0.0"
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_content, f, indent=2)
            temp_file_path = f.name

        try:
            parser = ParserFactory.get_parser(temp_file_path)
            parse_result = parser.parse_file(temp_file_path, "test_user")

            assert parse_result.success == True
            assert len(parse_result.content) > 0
            assert "Test Document" in parse_result.content
            assert "John" in parse_result.content
            assert "dark" in parse_result.content

        finally:
            os.unlink(temp_file_path)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])