"""
Unit Tests for Summarization Trigger Service
Story 4-4: Auto-Summarization Pipeline
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid
import redis
import asyncpg

from onyx_core.services.summarization.trigger_service import (
    SummarizationTriggerService,
    SummarizationTrigger,
    create_summarization_trigger_service
)


class TestSummarizationTriggerService:
    """Test cases for SummarizationTriggerService."""

    @pytest.fixture
    def mock_db_pool(self):
        """Create a mock database pool."""
        pool = AsyncMock()
        return pool

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        redis_client = Mock()
        redis_client.connection_pool.connection_kwargs = {
            'host': 'localhost',
            'port': 6379
        }
        return redis_client

    @pytest.fixture
    async def trigger_service(self, mock_db_pool, mock_redis_client):
        """Create a SummarizationTriggerService instance."""
        with patch('bullmq.Queue'):
            service = SummarizationTriggerService(mock_db_pool, mock_redis_client)
            yield service
            await service.close()

    @pytest.mark.asyncio
    async def test_should_trigger_at_interval(self, trigger_service, mock_db_pool):
        """Test that trigger is detected at correct message intervals."""
        conversation_id = str(uuid.uuid4())

        # Mock database response for message count
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 10  # Exactly at trigger interval
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock latest message
        mock_conn.fetchrow.return_value = {
            'id': str(uuid.uuid4()),
            'user_id': str(uuid.uuid4()),
            'content': 'Test message',
            'created_at': datetime.utcnow()
        }

        # Mock duplicate check
        mock_conn.fetchval.return_value = 0

        # Test trigger detection
        trigger = await trigger_service.should_trigger(conversation_id)

        assert trigger is not None
        assert trigger.conversation_id == conversation_id
        assert trigger.message_count == 10
        assert isinstance(trigger, SummarizationTrigger)

    @pytest.mark.asyncio
    async def test_should_not_trigger_off_interval(self, trigger_service, mock_db_pool):
        """Test that no trigger is detected when not at interval."""
        conversation_id = str(uuid.uuid4())

        # Mock database response for message count
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 7  # Not at trigger interval
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Test trigger detection
        trigger = await trigger_service.should_trigger(conversation_id)

        assert trigger is None

    @pytest.mark.asyncio
    async def test_should_not_trigger_duplicate(self, trigger_service, mock_db_pool):
        """Test that duplicate triggers are prevented."""
        conversation_id = str(uuid.uuid4())

        # Mock message count
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 10
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock latest message
        mock_conn.fetchrow.return_value = {
            'id': str(uuid.uuid4()),
            'user_id': str(uuid.uuid4()),
            'content': 'Test message',
            'created_at': datetime.utcnow()
        }

        # Mock duplicate check returning True (duplicate exists)
        mock_conn.fetchval.return_value = 1

        # Test trigger detection
        trigger = await trigger_service.should_trigger(conversation_id)

        assert trigger is None

    @pytest.mark.asyncio
    async def test_process_trigger_success(self, trigger_service, mock_db_pool):
        """Test successful trigger processing."""
        trigger = SummarizationTrigger(
            conversation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            message_count=10,
            user_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )

        # Mock database job tracking
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock BullMQ queue
        mock_job = Mock()
        mock_job.id = str(uuid.uuid4())
        trigger_service.summarization_queue.add = AsyncMock(return_value=mock_job)

        # Test trigger processing
        result = await trigger_service.process_trigger(trigger)

        assert result is True
        trigger_service.summarization_queue.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_trigger_failure(self, trigger_service):
        """Test trigger processing failure handling."""
        trigger = SummarizationTrigger(
            conversation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            message_count=10,
            user_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )

        # Mock BullMQ queue to raise exception
        trigger_service.summarization_queue.add = AsyncMock(side_effect=Exception("Queue error"))

        # Test trigger processing
        result = await trigger_service.process_trigger(trigger)

        assert result is False

    def test_calculate_priority_recent(self, trigger_service):
        """Test priority calculation for recent conversations."""
        trigger = SummarizationTrigger(
            conversation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            message_count=10,
            user_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()  # Very recent
        )

        priority = trigger_service._calculate_priority(trigger)

        assert priority >= 5  # Should have high priority for recent conversations

    def test_calculate_priority_old(self, trigger_service):
        """Test priority calculation for old conversations."""
        trigger = SummarizationTrigger(
            conversation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            message_count=10,
            user_id=str(uuid.uuid4()),
            created_at=datetime.utcnow() - timedelta(hours=10)  # 10 hours old
        )

        priority = trigger_service._calculate_priority(trigger)

        assert priority <= 5  # Should have lower priority for old conversations

    @pytest.mark.asyncio
    async def test_get_metrics(self, trigger_service, mock_db_pool):
        """Test metrics retrieval."""
        # Mock database metrics queries
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = [85.5, 1200, 5]  # success_rate, avg_time, queue_depth
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock queue metrics
        trigger_service.summarization_queue.getWaiting = AsyncMock(return_value=5)

        # Set some internal metrics
        trigger_service.metrics = {
            'triggers_detected': 100,
            'jobs_queued': 95,
            'duplicate_prevented': 5,
            'errors': 2
        }

        metrics = await trigger_service.get_metrics()

        assert 'triggers_detected' in metrics
        assert 'success_rate_24h' in metrics
        assert 'avg_processing_time_24h' in metrics
        assert 'queue_depth' in metrics
        assert 'updated_at' in metrics

    @pytest.mark.asyncio
    async def test_cleanup_old_records(self, trigger_service, mock_db_pool):
        """Test cleanup of old records."""
        # Mock database cleanup
        mock_conn = AsyncMock()
        mock_conn.execute.return_value = "DELETE 25"
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        deleted_count = await trigger_service.cleanup_old_records(30)

        assert deleted_count == 25

    @pytest.mark.asyncio
    async def test_create_service(self, mock_db_pool, mock_redis_client):
        """Test service factory function."""
        with patch('bullmq.Queue'):
            service = await create_summarization_trigger_service(mock_db_pool, mock_redis_client)

            assert service is not None
            assert isinstance(service, SummarizationTriggerService)

            await service.close()

    @pytest.mark.asyncio
    async def test_error_handling_in_should_trigger(self, trigger_service, mock_db_pool):
        """Test error handling in should_trigger method."""
        conversation_id = str(uuid.uuid4())

        # Mock database to raise exception
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = Exception("Database error")
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Test trigger detection with error
        trigger = await trigger_service.should_trigger(conversation_id)

        assert trigger is None
        assert trigger_service.metrics['errors'] == 1

    @pytest.mark.asyncio
    async def test_get_message_count_error(self, trigger_service, mock_db_pool):
        """Test error handling in message count retrieval."""
        conversation_id = str(uuid.uuid4())

        # Mock database to raise exception
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = Exception("Database error")
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Test message count retrieval
        count = await trigger_service._get_message_count(conversation_id)

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_latest_message_error(self, trigger_service, mock_db_pool):
        """Test error handling in latest message retrieval."""
        conversation_id = str(uuid.uuid4())

        # Mock database to raise exception
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = Exception("Database error")
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Test latest message retrieval
        message = await trigger_service._get_latest_message(conversation_id)

        assert message is None

    @pytest.mark.asyncio
    async def test_track_job_error(self, trigger_service, mock_db_pool):
        """Test error handling in job tracking."""
        trigger = SummarizationTrigger(
            conversation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            message_count=10,
            user_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        job_id = str(uuid.uuid4())

        # Mock database to raise exception
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = Exception("Database error")
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # This should not raise an exception, just log the error
        await trigger_service._track_job(trigger, job_id, 'queued')

        # No assertion needed - just verify it doesn't crash

    def test_priority_bounds(self, trigger_service):
        """Test that priority calculation stays within bounds."""
        # Test very recent conversation
        recent_trigger = SummarizationTrigger(
            conversation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            message_count=10,
            user_id=str(uuid.uuid4()),
            created_at=datetime.utcnow()
        )
        recent_priority = trigger_service._calculate_priority(recent_trigger)
        assert 1 <= recent_priority <= 10

        # Test very old conversation
        old_trigger = SummarizationTrigger(
            conversation_id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            message_count=10,
            user_id=str(uuid.uuid4()),
            created_at=datetime.utcnow() - timedelta(hours=100)
        )
        old_priority = trigger_service._calculate_priority(old_trigger)
        assert 1 <= old_priority <= 10