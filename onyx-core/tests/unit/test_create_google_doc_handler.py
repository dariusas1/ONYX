"""
Unit tests for Google Docs creation agent handler

Tests the handler that processes agent tool invocations for document creation,
including validation, error handling, and audit trail creation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from agents.handlers.create_google_doc_handler import (
    CreateGoogleDocHandler,
    create_google_doc_tool,
    get_handler,
    TOOL_DEFINITION,
)


class TestCreateGoogleDocHandler:
    """Test suite for CreateGoogleDocHandler"""

    @pytest.fixture
    def handler(self):
        """Create handler instance"""
        return CreateGoogleDocHandler()

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID"""
        return "test-user-123"

    @pytest.fixture
    def mock_credentials(self):
        """Mock Google credentials"""
        creds = MagicMock()
        creds.token = "test-token"
        return creds

    @pytest.mark.asyncio
    async def test_handler_initialization(self, handler):
        """Test handler initializes correctly"""
        assert handler is not None
        assert handler.docs_service is not None
        assert handler.oauth_service is not None

    @pytest.mark.asyncio
    async def test_create_document_success(
        self, handler, sample_user_id, mock_credentials
    ):
        """Test successful document creation"""
        with patch.object(
            handler.oauth_service, "get_credentials", return_value=mock_credentials
        ):
            with patch.object(handler.docs_service, "create_document") as mock_create:
                mock_create.return_value = {
                    "doc_id": "doc-123",
                    "url": "https://docs.google.com/document/d/doc-123/edit",
                    "created_at": "2024-01-15T10:00:00Z",
                    "title": "Test Doc",
                    "performance_ms": 1200,
                    "metadata_stored": True,
                }

                result = await handler.handle(
                    user_id=sample_user_id,
                    title="Test Doc",
                    content="# Test\n\nContent",
                )

                assert result["success"] is True
                assert result["data"]["doc_id"] == "doc-123"
                assert "url" in result["data"]

    @pytest.mark.asyncio
    async def test_empty_title_validation(self, handler, sample_user_id):
        """Test validation of empty title"""
        result = await handler.handle(
            user_id=sample_user_id, title="", content="Content"
        )

        assert result["success"] is False
        assert result["error_code"] == "INVALID_TITLE"

    @pytest.mark.asyncio
    async def test_empty_content_validation(self, handler, sample_user_id):
        """Test validation of empty content"""
        result = await handler.handle(user_id=sample_user_id, title="Title", content="")

        assert result["success"] is False
        assert result["error_code"] == "INVALID_CONTENT"

    @pytest.mark.asyncio
    async def test_title_too_long_validation(self, handler, sample_user_id):
        """Test validation of title length"""
        long_title = "x" * 1025
        result = await handler.handle(
            user_id=sample_user_id, title=long_title, content="Content"
        )

        assert result["success"] is False
        assert result["error_code"] == "TITLE_TOO_LONG"

    @pytest.mark.asyncio
    async def test_user_not_authorized(self, handler, sample_user_id):
        """Test error when user not authorized"""
        with patch.object(handler.oauth_service, "get_credentials", return_value=None):
            result = await handler.handle(
                user_id=sample_user_id, title="Title", content="Content"
            )

            assert result["success"] is False
            assert result["error_code"] == "NOT_AUTHORIZED"
            assert "authorize_google_drive" in result.get("action_required", "")

    @pytest.mark.asyncio
    async def test_agent_context_captured(
        self, handler, sample_user_id, mock_credentials
    ):
        """Test that agent context is properly captured"""
        with patch.object(
            handler.oauth_service, "get_credentials", return_value=mock_credentials
        ):
            with patch.object(handler.docs_service, "create_document") as mock_create:
                mock_create.return_value = {
                    "doc_id": "doc-456",
                    "url": "https://docs.google.com/document/d/doc-456/edit",
                    "created_at": "2024-01-15T10:00:00Z",
                    "title": "Context Test",
                    "performance_ms": 900,
                    "metadata_stored": True,
                }

                result = await handler.handle(
                    user_id=sample_user_id,
                    title="Context Test",
                    content="Content",
                    agent_name="TestAgent",
                    task_id="task-789",
                )

                # Verify create_document was called with context
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["agent_context"] is not None
                assert call_kwargs["agent_context"]["agent"] == "TestAgent"
                assert call_kwargs["agent_context"]["task_id"] == "task-789"

    @pytest.mark.asyncio
    async def test_folder_placement(self, handler, sample_user_id, mock_credentials):
        """Test folder placement parameter"""
        with patch.object(
            handler.oauth_service, "get_credentials", return_value=mock_credentials
        ):
            with patch.object(handler.docs_service, "create_document") as mock_create:
                mock_create.return_value = {
                    "doc_id": "doc-789",
                    "url": "https://docs.google.com/document/d/doc-789/edit",
                    "created_at": "2024-01-15T10:00:00Z",
                    "title": "Folder Test",
                    "performance_ms": 1100,
                    "metadata_stored": True,
                }

                folder_id = "folder-xyz"
                result = await handler.handle(
                    user_id=sample_user_id,
                    title="Folder Test",
                    content="Content",
                    folder_id=folder_id,
                )

                # Verify folder_id was passed
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args.kwargs
                assert call_kwargs["folder_id"] == folder_id

    @pytest.mark.asyncio
    async def test_permission_error_handling(
        self, handler, sample_user_id, mock_credentials
    ):
        """Test handling of permission errors"""
        with patch.object(
            handler.oauth_service, "get_credentials", return_value=mock_credentials
        ):
            with patch.object(handler.docs_service, "create_document") as mock_create:
                mock_create.side_effect = PermissionError("Insufficient permissions")

                result = await handler.handle(
                    user_id=sample_user_id, title="Title", content="Content"
                )

                assert result["success"] is False
                assert result["error_code"] == "PERMISSION_DENIED"

    @pytest.mark.asyncio
    async def test_quota_error_handling(
        self, handler, sample_user_id, mock_credentials
    ):
        """Test handling of quota exceeded errors"""
        with patch.object(
            handler.oauth_service, "get_credentials", return_value=mock_credentials
        ):
            with patch.object(handler.docs_service, "create_document") as mock_create:
                mock_create.side_effect = Exception("Quota exceeded")

                result = await handler.handle(
                    user_id=sample_user_id, title="Title", content="Content"
                )

                assert result["success"] is False
                assert result["error_code"] == "QUOTA_EXCEEDED"

    @pytest.mark.asyncio
    async def test_generic_error_handling(
        self, handler, sample_user_id, mock_credentials
    ):
        """Test handling of generic API errors"""
        with patch.object(
            handler.oauth_service, "get_credentials", return_value=mock_credentials
        ):
            with patch.object(handler.docs_service, "create_document") as mock_create:
                mock_create.side_effect = Exception("API error")

                result = await handler.handle(
                    user_id=sample_user_id, title="Title", content="Content"
                )

                assert result["success"] is False
                assert result["error_code"] == "API_ERROR"


class TestCreateGoogleDocTool:
    """Test the tool function for agents"""

    @pytest.mark.asyncio
    async def test_tool_function_execution(self):
        """Test the tool function executes correctly"""
        with patch("agents.handlers.create_google_doc_handler.get_handler") as mock_get:
            handler = MagicMock()
            handler.handle = AsyncMock(return_value={"success": True, "data": {}})
            mock_get.return_value = handler

            result = await create_google_doc_tool(
                user_id="user-123", title="Test", content="Content"
            )

            assert result["success"] is True
            handler.handle.assert_called_once()


class TestToolDefinition:
    """Test the tool definition structure"""

    def test_tool_definition_structure(self):
        """Test that tool definition is properly structured"""
        assert "name" in TOOL_DEFINITION
        assert TOOL_DEFINITION["name"] == "create_google_doc"
        assert "description" in TOOL_DEFINITION
        assert "parameters" in TOOL_DEFINITION
        assert "returns" in TOOL_DEFINITION

    def test_tool_parameters_schema(self):
        """Test parameter schema is complete"""
        params = TOOL_DEFINITION["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params

        # Check required parameters
        assert "title" in params["required"]
        assert "content" in params["required"]

        # Check property definitions
        props = params["properties"]
        assert "title" in props
        assert "content" in props
        assert "folder_id" in props

    def test_tool_return_schema(self):
        """Test return value schema is complete"""
        returns = TOOL_DEFINITION["returns"]
        assert returns["type"] == "object"
        assert "properties" in returns

        props = returns["properties"]
        assert "success" in props
        assert "data" in props
        assert "error" in props
        assert "error_code" in props

    def test_tool_examples_provided(self):
        """Test that examples are provided"""
        assert "examples" in TOOL_DEFINITION
        assert len(TOOL_DEFINITION["examples"]) > 0

        example = TOOL_DEFINITION["examples"][0]
        assert "name" in example
        assert "request" in example
        assert "response" in example


class TestHandlerSingleton:
    """Test handler singleton pattern"""

    def test_get_handler_singleton(self):
        """Test that get_handler returns same instance"""
        handler1 = get_handler()
        handler2 = get_handler()

        assert handler1 is handler2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
