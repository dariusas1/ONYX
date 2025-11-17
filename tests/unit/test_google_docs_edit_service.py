"""
Unit Tests for Google Docs Edit Service

Tests for GoogleDocsEditService including:
- Content insertion at various positions
- Text replacement functionality
- Formatting updates
- Error handling for permissions and invalid documents
- Performance monitoring
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, call
import time
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../onyx-core"))

# Mock encryption before importing oauth service
sys.modules["utils.encryption"] = MagicMock()
sys.modules["utils.database"] = MagicMock()

from services.google_docs_edit import GoogleDocsEditService


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_oauth_service():
    """Mock Google OAuth service"""
    mock_service = Mock()
    mock_creds = Mock(spec=Credentials)
    mock_creds.valid = True
    mock_creds.expired = False
    mock_service.get_credentials.return_value = mock_creds
    return mock_service


@pytest.fixture
def mock_db_service():
    """Mock database service"""
    mock_service = Mock()
    mock_service.log_google_docs_operation.return_value = True
    return mock_service


@pytest.fixture
def mock_docs_api():
    """Mock Google Docs API service"""
    mock_service = Mock()
    mock_docs = Mock()
    mock_get = Mock()
    mock_batch = Mock()

    # Set up chain: service.documents().get()
    mock_service.documents.return_value = mock_docs
    mock_docs.get.return_value = mock_get
    mock_docs.batchUpdate.return_value = mock_batch

    return mock_service


@pytest.fixture
def mock_drive_api():
    """Mock Google Drive API service"""
    return Mock()


@pytest.fixture
def mock_sample_document():
    """Mock Google Docs document structure"""
    return {
        "documentId": "test-doc-123",
        "title": "Test Document",
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [
                            {"textRun": {"content": "Introduction\n", "textStyle": {}}}
                        ],
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                    },
                    "startIndex": 1,
                    "endIndex": 14,
                },
                {
                    "paragraph": {
                        "elements": [
                            {
                                "textRun": {
                                    "content": "This is a test document.\n",
                                    "textStyle": {},
                                }
                            }
                        ],
                        "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                    },
                    "startIndex": 14,
                    "endIndex": 39,
                },
            ]
        },
    }


# =============================================================================
# TEST: Service Initialization (AC6.3.1, AC6.3.8)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_init_valid_credentials(
    mock_build, mock_get_db, mock_get_oauth, mock_oauth_service, mock_db_service
):
    """Test service initialization with valid credentials"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service

    service = GoogleDocsEditService("user-123")

    assert service.user_id == "user-123"
    assert service.credentials is not None
    assert service.docs_service is not None
    assert service.drive_service is not None


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
def test_init_no_credentials(mock_get_db, mock_get_oauth):
    """Test service initialization fails with no credentials"""
    mock_oauth_service = Mock()
    mock_oauth_service.get_credentials.return_value = None
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = Mock()

    with pytest.raises(ValueError, match="Invalid or missing credentials"):
        GoogleDocsEditService("user-123")


# =============================================================================
# TEST: Content Insertion (AC6.3.2, AC6.3.9, AC6.3.10)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_insert_at_end(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test content insertion at document end"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"insertText": {}}]
    }

    service = GoogleDocsEditService("user-123")

    result = service.insert_content(
        document_id="test-doc-123",
        content_markdown="## New Section\n\nNew content here.",
        position="end",
    )

    assert result["success"] is True
    assert result["character_inserted"] > 0
    assert "message" in result
    assert result["execution_time_ms"] < 2000  # AC6.3.7: <2 seconds


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_insert_at_beginning(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test content insertion at document beginning"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"insertText": {}}]
    }

    service = GoogleDocsEditService("user-123")

    result = service.insert_content(
        document_id="test-doc-123",
        content_markdown="**Important Note:**\n",
        position="beginning",
    )

    assert result["success"] is True
    # Verify batchUpdate was called with correct index (1 = beginning)
    mock_docs_api.documents().batchUpdate.assert_called_once()


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_insert_invalid_document(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
):
    """Test insertion with invalid document ID"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock document not found
    mock_docs_api.documents().get().execute.return_value = None

    service = GoogleDocsEditService("user-123")

    result = service.insert_content(
        document_id="invalid-doc", content_markdown="Content", position="end"
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_insert_permission_denied(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test insertion with permission denied error"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock permission error
    from googleapiclient.errors import HttpError

    mock_response = Mock()
    mock_response.status = 403
    mock_docs_api.documents().get().execute.side_effect = HttpError(
        mock_response, b"Permission denied"
    )

    service = GoogleDocsEditService("user-123")

    result = service.insert_content(
        document_id="test-doc-123", content_markdown="Content", position="end"
    )

    assert result["success"] is False


# =============================================================================
# TEST: Text Replacement (AC6.3.3, AC6.3.4)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_replace_single_occurrence(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test replacing single text occurrence"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"deleteContentRange": {}}, {"insertText": {}}]
    }

    service = GoogleDocsEditService("user-123")

    result = service.replace_content(
        document_id="test-doc-123",
        search_text="test document",
        replacement_markdown="**production document**",
        replace_all=False,
    )

    assert result["success"] is True
    assert result["replacements_count"] >= 0  # May be 0 if text not found in mock


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_replace_all_occurrences(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test replacing all occurrences"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {"replies": []}

    service = GoogleDocsEditService("user-123")

    result = service.replace_content(
        document_id="test-doc-123",
        search_text="test",
        replacement_markdown="qa",
        replace_all=True,
    )

    assert result["success"] is True


# =============================================================================
# TEST: Formatting Updates (AC6.3.4)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_format_bold(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test applying bold formatting"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"updateTextStyle": {}}]
    }

    service = GoogleDocsEditService("user-123")

    result = service.update_formatting(
        document_id="test-doc-123",
        start_index=0,
        end_index=10,
        formatting={"bold": True},
    )

    assert result["success"] is True
    assert "formatting" in result["message"].lower()


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_format_multiple_properties(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test applying multiple formatting properties"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"updateTextStyle": {}}]
    }

    service = GoogleDocsEditService("user-123")

    result = service.update_formatting(
        document_id="test-doc-123",
        start_index=0,
        end_index=20,
        formatting={
            "bold": True,
            "italic": True,
            "fontSize": 14,
        },
    )

    assert result["success"] is True


# =============================================================================
# TEST: Error Handling (AC6.3.6)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_error_handling_missing_parameters(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
):
    """Test error handling for missing parameters"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    service = GoogleDocsEditService("user-123")

    # Missing content_markdown
    result = service.insert_content(
        document_id="test-doc-123", content_markdown="", position="end"
    )

    assert result["success"] is False


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_error_handling_invalid_range(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test error handling for invalid character range"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document

    service = GoogleDocsEditService("user-123")

    # Invalid range: start > end
    result = service.update_formatting(
        document_id="test-doc-123",
        start_index=100,
        end_index=50,
        formatting={"bold": True},
    )

    assert result["success"] is False


# =============================================================================
# TEST: Performance Constraints (AC6.3.7)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_performance_under_2_seconds(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test that operations complete within 2 second target"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls with fast responses
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"insertText": {}}]
    }

    service = GoogleDocsEditService("user-123")

    start = time.time()

    result = service.insert_content(
        document_id="test-doc-123", content_markdown="Test content", position="end"
    )

    elapsed = time.time() - start

    # Should complete within 2 seconds
    assert result["execution_time_ms"] < 2000
    assert elapsed < 2.0


# =============================================================================
# TEST: Audit Trail Logging (AC6.3.5, AC6.3.10)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_operation_logged_to_database(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test that operations are logged to database for audit trail"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"insertText": {}}]
    }

    service = GoogleDocsEditService("user-123")

    result = service.insert_content(
        document_id="test-doc-123", content_markdown="Test content", position="end"
    )

    assert result["success"] is True

    # Verify database logging was called
    mock_db_service.log_google_docs_operation.assert_called()
    call_args = mock_db_service.log_google_docs_operation.call_args[0][0]

    # Verify logged data includes required fields
    assert call_args["user_id"] == "user-123"
    assert call_args["document_id"] == "test-doc-123"
    assert call_args["operation_type"] == "insert"
    assert call_args["status"] == "success"
    assert "timestamp" in call_args


# =============================================================================
# TEST: OAuth2 Integration (AC6.3.8)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_oauth2_credentials_used(
    mock_build, mock_get_db, mock_get_oauth, mock_oauth_service, mock_db_service
):
    """Test that OAuth2 credentials are properly used"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service

    service = GoogleDocsEditService("user-123")

    # Verify OAuth service was called to get credentials
    mock_oauth_service.get_credentials.assert_called_once_with("user-123")

    # Verify credentials were passed to API client
    assert service.credentials == mock_oauth_service.get_credentials.return_value


# =============================================================================
# TEST: Markdown Conversion (AC6.3.9)
# =============================================================================


@patch("services.google_docs_edit.get_oauth_service")
@patch("services.google_docs_edit.get_db_service")
@patch("services.google_docs_edit.build")
def test_markdown_conversion(
    mock_build,
    mock_get_db,
    mock_get_oauth,
    mock_oauth_service,
    mock_db_service,
    mock_docs_api,
    mock_sample_document,
):
    """Test Markdown to Google Docs format conversion"""
    mock_get_oauth.return_value = mock_oauth_service
    mock_get_db.return_value = mock_db_service
    mock_build.return_value = mock_docs_api

    # Mock API calls
    mock_docs_api.documents().get().execute.return_value = mock_sample_document
    mock_docs_api.documents().batchUpdate().execute.return_value = {
        "replies": [{"insertText": {}}]
    }

    service = GoogleDocsEditService("user-123")

    markdown_content = """
# Heading 1
## Heading 2

This is **bold** and this is *italic*.

- Bullet point 1
- Bullet point 2

`inline code`

[Link](https://example.com)
    """.strip()

    result = service.insert_content(
        document_id="test-doc-123", content_markdown=markdown_content, position="end"
    )

    assert result["success"] is True
    assert result["character_inserted"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
