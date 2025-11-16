"""
Comprehensive test suite for Slack connector integration

Tests cover:
- API endpoints
- Database operations
- Slack client service
- Message processing
- Sync scheduling
- Error handling
- Integration workflows
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import tempfile
import os

from fastapi.testclient import TestClient
from httpx import AsyncClient

from onyx_core.main import app
from onyx_core.services.slack_client import get_slack_client, SlackClientService
from onyx_core.services.slack_sync_service import get_slack_sync_service
from onyx_core.services.message_processor import MessageProcessor
from onyx_core.services.sync_scheduler import get_scheduler
from onyx_core.utils.database import get_db_service
from onyx_core.utils.auth import create_access_token


class TestSlackAPIEndpoints:
    """Test Slack API endpoints"""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Create authentication headers"""
        token = create_access_token(data={"sub": "test-user-id", "email": "test@example.com"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def mock_slack_client(self):
        """Mock Slack client service"""
        with patch('onyx_core.api.slack.get_slack_client') as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client

    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/api/v1/slack/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["service"] == "slack"

    @patch('onyx_core.api.slack.get_oauth_service')
    @patch('onyx_core.api.slack.get_slack_client')
    @patch('onyx_core.api.slack.get_db_service')
    def test_auth_connect_success(self, mock_db, mock_slack, mock_oauth, client: TestClient, auth_headers: Dict[str, str]):
        """Test successful Slack authentication"""
        # Setup mocks
        mock_client = AsyncMock()
        mock_slack.return_value = mock_client
        mock_client.validate_token.return_value = {
            "ok": True,
            "team_id": "T123456",
            "team_name": "Test Workspace",
            "bot_user_id": "U123456",
            "bot_name": "Test Bot",
            "bot_scopes": ["channels:read", "messages:read"]
        }

        mock_oauth_service = AsyncMock()
        mock_oauth.return_value = mock_oauth_service
        mock_oauth_service.store_tokens.return_value = True

        mock_db_service = AsyncMock()
        mock_db.return_value = mock_db_service
        mock_db_service.update_slack_sync_state.return_value = True

        response = client.post(
            "/api/v1/slack/auth/connect",
            json={"bot_token": "xoxb-test-token"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "team_id" in data["data"]
        assert data["data"]["team_name"] == "Test Workspace"

    def test_auth_connect_invalid_token(self, client: TestClient, auth_headers: Dict[str, str], mock_slack_client):
        """Test authentication with invalid token"""
        mock_slack_client.return_value.validate_token.return_value = {
            "ok": False,
            "error": "invalid_auth"
        }

        response = client.post(
            "/api/v1/slack/auth/connect",
            json={"bot_token": "invalid-token"},
            headers=auth_headers
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid Slack token" in data["detail"]

    def test_auth_status_not_connected(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test authentication status when not connected"""
        with patch('onyx_core.api.slack.get_oauth_service') as mock_oauth, \
             patch('onyx_core.api.slack.get_db_service') as mock_db:

            mock_oauth.return_value.get_tokens.return_value = None
            mock_db.return_value.get_slack_sync_state.return_value = None

            response = client.get("/api/v1/slack/auth/status", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["is_authenticated"] is False

    @patch('onyx_core.api.slack.get_scheduler')
    def test_sync_schedule(self, mock_scheduler, client: TestClient, auth_headers: Dict[str, str]):
        """Test scheduling Slack sync"""
        mock_sched = AsyncMock()
        mock_scheduler.return_value = mock_sched

        response = client.post(
            "/api/v1/slack/sync/schedule",
            json={"interval_minutes": 15, "immediate": False},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["interval_minutes"] == 15
        mock_sched.schedule_slack_sync.assert_called_once()


class TestSlackClientService:
    """Test Slack client service"""

    @pytest.fixture
    def slack_service(self) -> SlackClientService:
        """Create Slack client service instance"""
        return SlackClientService()

    @pytest.fixture
    def mock_web_client(self):
        """Mock AsyncWebClient"""
        with patch('slack_sdk.web.async_client.AsyncWebClient') as mock:
            client = AsyncMock()
            mock.return_value = client
            yield client

    @pytest.mark.asyncio
    async def test_create_client_success(self, slack_service: SlackClientService, mock_web_client):
        """Test successful client creation"""
        mock_web_client.auth_test.return_value = {
            "ok": True,
            "team": "test-team",
            "user": "test-bot"
        }

        client = await slack_service.create_client("xoxb-test-token")

        assert client is not None
        mock_web_client.auth_test.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_client_invalid_token(self, slack_service: SlackClientService, mock_web_client):
        """Test client creation with invalid token"""
        from slack_sdk.errors import SlackApiError

        mock_web_client.auth_test.side_effect = SlackApiError(
            message="Invalid auth",
            response={"ok": False, "error": "invalid_auth"}
        )

        with pytest.raises(ValueError, match="Invalid Slack token"):
            await slack_service.create_client("invalid-token")

    @pytest.mark.asyncio
    async def test_get_channels_success(self, slack_service: SlackClientService, mock_web_client):
        """Test successful channel retrieval"""
        mock_web_client.conversations_list.return_value = {
            "ok": True,
            "channels": [
                {"id": "C123", "name": "general", "is_private": False},
                {"id": "C456", "name": "random", "is_private": False}
            ],
            "response_metadata": {"next_cursor": None}
        }

        channels = await slack_service.get_channels(mock_web_client)

        assert len(channels) == 2
        assert channels[0]["id"] == "C123"
        assert channels[0]["name"] == "general"

    @pytest.mark.asyncio
    async def test_get_messages_pagination(self, slack_service: SlackClientService, mock_web_client):
        """Test message retrieval with pagination"""
        # First page
        mock_web_client.conversations_history.return_value = {
            "ok": True,
            "messages": [
                {"ts": "1234567890.000001", "text": "Hello world", "user": "U123"},
                {"ts": "1234567890.000002", "text": "Another message", "user": "U456"}
            ],
            "has_more": True,
            "response_metadata": {"next_cursor": "cursor123"}
        }

        # Second page
        mock_web_client.conversations_history.side_effect = [
            {
                "ok": True,
                "messages": [
                    {"ts": "1234567890.000001", "text": "Hello world", "user": "U123"},
                    {"ts": "1234567890.000002", "text": "Another message", "user": "U456"}
                ],
                "has_more": True,
                "response_metadata": {"next_cursor": "cursor123"}
            },
            {
                "ok": True,
                "messages": [
                    {"ts": "1234567890.000003", "text": "Third message", "user": "U789"}
                ],
                "has_more": False,
                "response_metadata": {"next_cursor": None}
            }
        ]

        messages = await slack_service.get_messages(mock_web_client, "C123", limit=100)

        assert len(messages) == 3
        assert messages[2]["text"] == "Third message"


class TestMessageProcessor:
    """Test message processing service"""

    @pytest.fixture
    def processor(self) -> MessageProcessor:
        """Create message processor instance"""
        return MessageProcessor()

    def test_process_simple_message(self, processor: MessageProcessor):
        """Test processing a simple message"""
        message = {
            "ts": "1234567890.000001",
            "text": "Hello world",
            "user": "U123",
            "username": "testuser",
            "channel": "C123",
            "channel_name": "general"
        }

        result = processor.process_message(message)

        assert result["source_id"] == "1234567890.000001"
        assert result["text"] == "Hello world"
        assert result["message_type"] == "message"
        assert result["thread_id"] is None

    def test_process_thread_parent(self, processor: MessageProcessor):
        """Test processing a thread parent message"""
        message = {
            "ts": "1234567890.000001",
            "text": "Starting a thread",
            "user": "U123",
            "username": "testuser",
            "channel": "C123",
            "channel_name": "general",
            "thread_ts": "1234567890.000001"  # Same as message ts indicates thread parent
        }

        result = processor.process_message(message)

        assert result["message_type"] == "thread_parent"
        assert result["thread_id"] == "1234567890.000001"

    def test_process_thread_reply(self, processor: MessageProcessor):
        """Test processing a thread reply"""
        message = {
            "ts": "1234567890.000002",
            "text": "Replying to thread",
            "user": "U456",
            "username": "anotheruser",
            "channel": "C123",
            "channel_name": "general",
            "thread_ts": "1234567890.000001"  # Different ts indicates reply
        }

        result = processor.process_message(message)

        assert result["message_type"] == "thread_reply"
        assert result["thread_id"] == "1234567890.000001"

    def test_extract_file_content_pdf(self, processor: MessageProcessor):
        """Test PDF content extraction"""
        # Create a temporary PDF-like file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
            f.write("Sample PDF content for testing")
            temp_path = f.name

        try:
            content = processor.extract_file_content(temp_path, "application/pdf")
            # Note: In real implementation, this would use PyPDF2
            # For testing, we'll get the raw content
            assert "Sample PDF content" in content
        finally:
            os.unlink(temp_path)

    def test_extract_file_content_text(self, processor: MessageProcessor):
        """Test text file content extraction"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Sample text content\nWith multiple lines")
            temp_path = f.name

        try:
            content = processor.extract_file_content(temp_path, "text/plain")
            assert "Sample text content" in content
            assert "With multiple lines" in content
        finally:
            os.unlink(temp_path)

    def test_extract_file_content_unsupported(self, processor: MessageProcessor):
        """Test handling of unsupported file types"""
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            f.write(b"binary content")
            temp_path = f.name

        try:
            content = processor.extract_file_content(temp_path, "application/octet-stream")
            assert content == ""  # Unsupported types return empty string
        finally:
            os.unlink(temp_path)

    def test_create_content_chunks(self, processor: MessageProcessor):
        """Test content chunking"""
        long_text = "This is a very long message that should be split into multiple chunks. " * 20

        chunks = processor.create_content_chunks(long_text, "msg123", "general")

        assert len(chunks) > 1
        assert all(chunk["text"] for chunk in chunks)
        assert all("msg123" in chunk["source_id"] for chunk in chunks)

    def test_create_content_chunks_short_text(self, processor: MessageProcessor):
        """Test content chunking with short text"""
        short_text = "This is a short message"

        chunks = processor.create_content_chunks(short_text, "msg123", "general")

        assert len(chunks) == 1
        assert chunks[0]["text"] == short_text


class TestDatabaseOperations:
    """Test database operations for Slack"""

    @pytest.fixture
    def db_service(self):
        """Create database service instance"""
        with patch('onyx_core.utils.database.psycopg2.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            yield get_db_service()

    @pytest.mark.asyncio
    async def test_upsert_slack_document_new(self, db_service):
        """Test upserting a new Slack document"""
        db_service.connect = MagicMock()

        with patch.object(db_service, '_execute_query') as mock_execute:
            mock_execute.return_value = [{"id": "doc123"}]

            doc_id = await db_service.upsert_slack_document(
                source_id="1234567890.000001",
                channel_id="C123",
                channel_name="general",
                user_id="U123",
                user_name="testuser",
                text="Hello world",
                timestamp=datetime.now()
            )

            assert doc_id == "doc123"
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_slack_document_by_source_id(self, db_service):
        """Test retrieving Slack document by source ID"""
        db_service.connect = MagicMock()

        with patch.object(db_service, '_execute_query') as mock_execute:
            mock_execute.return_value = [{
                "id": "doc123",
                "source_id": "1234567890.000001",
                "text": "Hello world",
                "channel_name": "general"
            }]

            doc = await db_service.get_slack_document("1234567890.000001")

            assert doc is not None
            assert doc["source_id"] == "1234567890.000001"
            assert doc["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_upsert_slack_channel(self, db_service):
        """Test upserting Slack channel information"""
        db_service.connect = MagicMock()

        with patch.object(db_service, '_execute_query') as mock_execute:
            await db_service.upsert_slack_channel(
                user_id="test-user",
                channel_id="C123",
                channel_name="general",
                channel_type="public_channel",
                is_private=False,
                is_member=True
            )

            mock_execute.assert_called_once()


class TestSyncScheduler:
    """Test sync scheduler for Slack"""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance"""
        with patch('onyx_core.services.sync_scheduler.AsyncIOScheduler') as mock:
            sched = AsyncMock()
            mock.return_value = sched
            from onyx_core.services.sync_scheduler import SyncScheduler
            return SyncScheduler()

    def test_schedule_slack_sync(self, scheduler):
        """Test scheduling Slack sync"""
        scheduler.schedule_slack_sync("user123", interval_minutes=15, immediate=False)

        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args
        assert "user123" in call_args[1]["id"]

    @pytest.mark.asyncio
    async def test_trigger_manual_sync(self, scheduler):
        """Test triggering manual sync"""
        with patch.object(scheduler, 'db_service') as mock_db:
            mock_db.create_sync_job.return_value = "job123"

            with patch('onyx_core.services.sync_scheduler.asyncio.create_task'):
                job_id = await scheduler.trigger_slack_sync("user123", full_sync=True)

                assert job_id == "job123"
                mock_db.create_sync_job.assert_called_once_with("user123", source_type="slack")


class TestIntegrationWorkflows:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_complete_sync_workflow(self):
        """Test complete Slack sync workflow"""
        # This test would integrate multiple services
        # In a real implementation, you'd use test containers or mock external services

        with patch('onyx_core.services.slack_sync_service.get_slack_client') as mock_client, \
             patch('onyx_core.services.slack_sync_service.get_db_service') as mock_db, \
             patch('onyx_core.services.slack_sync_service.get_rag_service') as mock_rag:

            # Setup mocks
            mock_slack_client = AsyncMock()
            mock_client.return_value = mock_slack_client
            mock_slack_client.validate_token.return_value = {"ok": True, "team": "test"}

            mock_db_service = AsyncMock()
            mock_db.return_value = mock_db_service
            mock_db_service.get_oauth_tokens.return_value = {
                "encrypted_access_token": "encrypted_token"
            }

            mock_rag_service = AsyncMock()
            mock_rag.return_value = mock_rag_service

            # Mock channel and message responses
            mock_slack_client.get_channels.return_value = [
                {"id": "C123", "name": "general", "is_private": False}
            ]
            mock_slack_client.get_messages.return_value = [
                {
                    "ts": "1234567890.000001",
                    "text": "Hello world",
                    "user": "U123",
                    "username": "testuser"
                }
            ]

            # Execute sync
            from onyx_core.services.slack_sync_service import get_slack_sync_service
            sync_service = get_slack_sync_service()

            # Mock decryption
            with patch.object(sync_service, '_decrypt_token'):
                stats = await sync_service.sync_slack_workspace("user123")

                assert stats["channels_processed"] == 1
                assert stats["messages_processed"] == 1
                assert stats["documents_indexed"] > 0

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling in sync workflow"""
        with patch('onyx_core.services.slack_sync_service.get_slack_client') as mock_client, \
             patch('onyx_core.services.slack_sync_service.get_db_service') as mock_db:

            # Setup mock to raise exception
            mock_client.return_value.validate_token.side_effect = Exception("Slack API error")

            from onyx_core.services.slack_sync_service import get_slack_sync_service
            sync_service = get_slack_sync_service()

            stats = await sync_service.sync_slack_workspace("user123")

            assert stats["errors"] > 0
            assert "Slack API error" in str(stats["error_details"])


class TestPerformanceAndScalability:
    """Performance and scalability tests"""

    @pytest.mark.asyncio
    async def test_large_message_processing(self):
        """Test processing large volumes of messages"""
        processor = MessageProcessor()

        # Generate test messages
        messages = []
        for i in range(1000):
            messages.append({
                "ts": f"1234567890.{i:06d}",
                "text": f"Test message {i} with some content to process",
                "user": f"U{i % 10}",
                "username": f"user{i % 10}",
                "channel": "C123",
                "channel_name": "general"
            })

        # Process all messages
        start_time = datetime.now()
        processed = [processor.process_message(msg) for msg in messages]
        end_time = datetime.now()

        processing_time = (end_time - start_time).total_seconds()

        assert len(processed) == 1000
        assert processing_time < 10.0  # Should process 1000 messages in under 10 seconds

    @pytest.mark.asyncio
    async def test_concurrent_channel_processing(self):
        """Test processing multiple channels concurrently"""
        with patch('onyx_core.services.slack_sync_service.get_slack_client') as mock_client:
            mock_slack_client = AsyncMock()
            mock_client.return_value = mock_slack_client

            # Mock multiple channels
            channels = [{"id": f"C{i}", "name": f"channel{i}"} for i in range(10)]
            mock_slack_client.get_channels.return_value = channels

            from onyx_core.services.slack_sync_service import get_slack_sync_service
            sync_service = get_slack_sync_service()

            # Mock token decryption
            with patch.object(sync_service, '_decrypt_token'), \
                 patch.object(sync_service, '_process_channel_messages'):

                start_time = datetime.now()
                stats = await sync_service.sync_slack_workspace("user123")
                end_time = datetime.now()

                processing_time = (end_time - start_time).total_seconds()

                assert stats["channels_processed"] == 10
                # Concurrent processing should be faster than sequential
                assert processing_time < 30.0  # Reasonable threshold


if __name__ == "__main__":
    # Run specific test class
    pytest.main([__file__, "-v", "TestSlackAPIEndpoints"])
    pytest.main([__file__, "-v", "TestSlackClientService"])
    pytest.main([__file__, "-v", "TestMessageProcessor"])
    pytest.main([__file__, "-v", "TestDatabaseOperations"])
    pytest.main([__file__, "-v", "TestSyncScheduler"])
    pytest.main([__file__, "-v", "TestIntegrationWorkflows"])
    pytest.main([__file__, "-v", "TestPerformanceAndScalability"])