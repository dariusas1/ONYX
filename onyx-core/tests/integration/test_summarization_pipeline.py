"""
Integration Tests for Auto-Summarization Pipeline
Story 4-4: Auto-Summarization Pipeline
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid
import json
import asyncpg
import redis
import httpx

from onyx_core.services.summarization.trigger_service import create_summarization_trigger_service
from onyx_core.services.summarization.summarizer import create_conversation_summarizer
from onyx_core.services.summarization.storage import create_summary_memory_storage
from onyx_core.workers.summarization_worker import create_summarization_worker, WorkerConfig


class TestSummarizationPipelineIntegration:
    """Integration tests for the complete summarization pipeline."""

    @pytest.fixture
    async def mock_services(self):
        """Create mock services for testing."""
        # Mock database pool
        mock_db_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock Redis client
        mock_redis = Mock()
        mock_redis.connection_pool.connection_kwargs = {
            'host': 'localhost',
            'port': 6379
        }

        # Mock message data
        conversation_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        return {
            'db_pool': mock_db_pool,
            'redis': mock_redis,
            'conversation_id': conversation_id,
            'user_id': user_id,
            'message_id': message_id,
            'mock_conn': mock_conn
        }

    @pytest.mark.asyncio
    async def test_end_to_end_summarization(self, mock_services):
        """Test complete end-to-end summarization flow."""
        db_pool = mock_services['db_pool']
        redis_client = mock_services['redis']
        conversation_id = mock_services['conversation_id']
        user_id = mock_services['user_id']
        mock_conn = mock_services['mock_conn']

        # Mock message count check (exactly at trigger interval)
        mock_conn.fetchval.return_value = 10

        # Mock latest message
        mock_conn.fetchrow.return_value = {
            'id': mock_services['message_id'],
            'user_id': user_id,
            'content': 'Test message for summarization',
            'created_at': datetime.utcnow()
        }

        # Mock duplicate check
        mock_conn.fetchval.return_value = 0

        # Mock database operations for storage
        mock_conn.execute.return_value = "INSERT 1"
        mock_conn.fetchrow.return_value = {'id': str(uuid.uuid4()), 'created_at': datetime.utcnow()}

        # Initialize services
        with patch('bullmq.Queue'):
            trigger_service = await create_summarization_trigger_service(db_pool, redis_client)
            storage = create_summary_memory_storage(db_pool)

            # Step 1: Check for trigger
            trigger = await trigger_service.should_trigger(conversation_id)
            assert trigger is not None
            assert trigger.message_count == 10

            # Step 2: Process trigger (queue job)
            with patch.object(trigger_service.summarization_queue, 'add') as mock_add:
                mock_job = Mock()
                mock_job.id = str(uuid.uuid4())
                mock_add.return_value = mock_job

                success = await trigger_service.process_trigger(trigger)
                assert success is True

            await trigger_service.close()

    @pytest.mark.asyncio
    async def test_summarizer_with_real_llm_mock(self, mock_services):
        """Test summarizer with mocked LLM responses."""
        # Mock messages
        messages = [
            {
                'id': str(uuid.uuid4()),
                'role': 'user',
                'content': 'I need to plan a software project with design and development phases.',
                'created_at': datetime.utcnow()
            },
            {
                'id': str(uuid.uuid4()),
                'role': 'assistant',
                'content': 'I can help you create a comprehensive project plan with clear phases.',
                'created_at': datetime.utcnow()
            },
            {
                'id': str(uuid.uuid4()),
                'role': 'user',
                'content': 'Great! Let\'s start with design, then move to development.',
                'created_at': datetime.utcnow()
            }
        ]

        # Create summarizer
        summarizer = create_conversation_summarizer()

        # Mock message retrieval
        with patch.object(summarizer, '_get_messages_in_range', return_value=messages):
            # Mock LLM responses
            with patch('httpx.AsyncClient.post') as mock_post:
                # Mock summary generation
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.side_effect = [
                    {
                        'choices': [{
                            'message': {
                                'content': 'User is planning a software project with design and development phases, focusing on design first.'
                            }
                        }]
                    },
                    {
                        'choices': [{
                            'message': {
                                'content': '["project planning", "software design", "development"]'
                            }
                        }]
                    }
                ]

                # Create request
                from onyx_core.services.summarization.summarizer import SummarizationRequest
                request = SummarizationRequest(
                    conversation_id=mock_services['conversation_id'],
                    message_range={'start': 1, 'end': 3},
                    user_id=mock_services['user_id']
                )

                # Generate summary
                result = await summarizer.generate_summary(request)

                assert result.summary is not None
                assert len(result.summary) >= 20
                assert len(result.summary) <= 300
                assert len(result.key_topics) >= 1
                assert len(result.key_topics) <= 5
                assert -1 <= result.sentiment <= 1
                assert result.confidence == 0.9
                assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_storage_integration(self, mock_services):
        """Test memory storage integration."""
        db_pool = mock_services['db_pool']
        mock_conn = mock_services['mock_conn']
        user_id = mock_services['user_id']
        conversation_id = mock_services['conversation_id']

        # Mock storage operations
        mock_conn.fetchrow.return_value = None  # No duplicate found
        mock_conn.execute.return_value = "INSERT 1"
        mock_conn.fetchrow.return_value = {'id': str(uuid.uuid4()), 'created_at': datetime.utcnow()}

        # Create storage service
        storage = create_summary_memory_storage(db_pool)

        # Create mock summary result
        from onyx_core.services.summarization.summarizer import SummarizationResult
        summary_result = SummarizationResult(
            summary="User discussed software project planning with design and development phases.",
            key_topics=["project planning", "software design", "development"],
            sentiment=0.3,
            confidence=0.9,
            processing_time=1500,
            message_count=3
        )

        # Store summary
        memory_id = await storage.store_summary(
            user_id=user_id,
            conversation_id=conversation_id,
            summary_result=summary_result,
            message_range={'start': 1, 'end': 3}
        )

        assert memory_id is not None
        assert isinstance(memory_id, str)

        # Verify storage was called
        assert mock_conn.execute.call_count >= 2  # Should have stored in both tables

    @pytest.mark.asyncio
    async def test_duplicate_prevention(self, mock_services):
        """Test duplicate summary prevention."""
        db_pool = mock_services['db_pool']
        mock_conn = mock_services['mock_conn']
        user_id = mock_services['user_id']
        conversation_id = mock_services['conversation_id']

        # Mock duplicate found
        existing_summary_id = str(uuid.uuid4())
        mock_conn.fetchrow.return_value = {
            'id': existing_summary_id,
            'summary': 'Similar summary content',
            'created_at': datetime.utcnow()
        }

        # Create storage service
        storage = create_summary_memory_storage(db_pool)

        # Create mock summary result
        from onyx_core.services.summarization.summarizer import SummarizationResult
        summary_result = SummarizationResult(
            summary="Similar summary content",  # Same as existing
            key_topics=["topic"],
            sentiment=0.0,
            confidence=0.9,
            processing_time=1000,
            message_count=3
        )

        # Store summary - should return existing ID
        memory_id = await storage.store_summary(
            user_id=user_id,
            conversation_id=conversation_id,
            summary_result=summary_result,
            message_range={'start': 1, 'end': 3}
        )

        assert memory_id == existing_summary_id
        # Should not have inserted new records
        mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_worker_job_processing(self, mock_services):
        """Test worker job processing with mocked services."""
        db_pool = mock_services['db_pool']
        redis_client = mock_services['redis']
        mock_conn = mock_services['mock_conn']

        # Mock worker configuration
        config = WorkerConfig(concurrency=1, max_retries=3)

        # Mock database operations
        mock_conn.fetchrow.return_value = {'id': str(uuid.uuid4()), 'created_at': datetime.utcnow()}
        mock_conn.execute.return_value = "INSERT 1"

        # Create worker
        with patch('bullmq.Queue'), patch('bullmq.Worker'):
            worker = create_summarization_worker(db_pool, redis_client, config)

            # Mock job data
            job_data = {
                'conversation_id': mock_services['conversation_id'],
                'user_id': mock_services['user_id'],
                'message_id': mock_services['message_id'],
                'message_count': 10,
                'message_range': {'start': 1, 'end': 3}
            }

            # Mock job
            mock_job = Mock()
            mock_job.id = str(uuid.uuid4())
            mock_job.data = job_data
            mock_job.opts.attemptsMade = 0
            mock_job.opts.attempts = 3

            # Mock summarizer
            with patch.object(worker.summarizer, 'generate_summary') as mock_summarize:
                from onyx_core.services.summarization.summarizer import SummarizationResult
                mock_summarize.return_value = SummarizationResult(
                    summary="Test summary",
                    key_topics=["test"],
                    sentiment=0.0,
                    confidence=0.9,
                    processing_time=1000,
                    message_count=3
                )

                # Mock storage
                with patch.object(worker.storage, 'store_summary', return_value=str(uuid.uuid4())):
                    # Process job
                    result = await worker._process_job(mock_job)

                    assert result is not None
                    assert result['memory_id'] is not None
                    assert result['summary_length'] == len("Test summary")
                    assert result['topics_count'] == 1

            await worker.stop()

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, mock_services):
        """Test pipeline error handling and recovery."""
        db_pool = mock_services['db_pool']
        redis_client = mock_services['redis']
        mock_conn = mock_services['mock_conn']

        # Test trigger service error handling
        with patch('bullmq.Queue'):
            trigger_service = await create_summarization_trigger_service(db_pool, redis_client)

            # Mock database error
            mock_conn.fetchval.side_effect = Exception("Database connection failed")

            # Should handle error gracefully
            trigger = await trigger_service.should_trigger(mock_services['conversation_id'])
            assert trigger is None

            # Check metrics show error
            metrics = await trigger_service.get_metrics()
            assert metrics['errors'] > 0

            await trigger_service.close()

    @pytest.mark.asyncio
    async def test_pipeline_metrics_collection(self, mock_services):
        """Test comprehensive metrics collection across pipeline."""
        db_pool = mock_services['db_pool']
        redis_client = mock_services['redis']
        mock_conn = mock_services['mock_conn']

        # Mock metrics queries
        mock_conn.fetchval.side_effect = [95.5, 1200, 3]  # success_rate, avg_time, queue_depth

        # Initialize services
        with patch('bullmq.Queue'):
            trigger_service = await create_summarization_trigger_service(db_pool, redis_client)
            storage = create_summary_memory_storage(db_pool)

            # Set some internal metrics
            trigger_service.metrics = {
                'triggers_detected': 50,
                'jobs_queued': 48,
                'duplicate_prevented': 2,
                'errors': 1
            }

            storage.metrics = {
                'summaries_stored': 45,
                'duplicates_prevented': 3,
                'errors': 2,
                'avg_storage_time': 800
            }

            # Get metrics
            trigger_metrics = await trigger_service.get_metrics()
            storage_metrics = await storage.get_metrics()

            # Verify metrics structure
            assert 'triggers_detected' in trigger_metrics
            assert 'success_rate_24h' in trigger_metrics
            assert 'avg_processing_time_24h' in trigger_metrics
            assert 'summaries_stored' in storage_metrics
            assert 'avg_storage_time' in storage_metrics
            assert 'updated_at' in trigger_metrics
            assert 'updated_at' in storage_metrics

            await trigger_service.close()

    @pytest.mark.asyncio
    async def test_concurrent_trigger_handling(self, mock_services):
        """Test handling of concurrent triggers for same conversation."""
        db_pool = mock_services['db_pool']
        redis_client = mock_services['redis']
        conversation_id = mock_services['conversation_id']
        mock_conn = mock_services['mock_conn']

        # Mock message count and latest message
        mock_conn.fetchval.return_value = 10
        mock_conn.fetchrow.return_value = {
            'id': mock_services['message_id'],
            'user_id': mock_services['user_id'],
            'content': 'Test message',
            'created_at': datetime.utcnow()
        }

        # Initialize trigger service
        with patch('bullmq.Queue'):
            trigger_service = await create_summarization_trigger_service(db_pool, redis_client)

            # First trigger should succeed
            mock_conn.fetchval.return_value = 0  # No duplicate
            trigger1 = await trigger_service.should_trigger(conversation_id)
            assert trigger1 is not None

            # Second trigger should be prevented (duplicate)
            mock_conn.fetchval.return_value = 1  # Duplicate exists
            trigger2 = await trigger_service.should_trigger(conversation_id)
            assert trigger2 is None

            # Verify metrics
            metrics = await trigger_service.get_metrics()
            assert metrics['duplicate_prevented'] > 0

            await trigger_service.close()

    @pytest.mark.asyncio
    async def test_topic_extraction_variability(self, mock_services):
        """Test topic extraction with various summary types."""
        summarizer = create_conversation_summarizer()

        # Test different types of summaries
        test_cases = [
            "User discussed budget planning for Q4 2024 marketing campaign.",
            "Development team completed API integration testing and deployment.",
            "Meeting notes cover product roadmap, technical decisions, and team assignments.",
            "Customer feedback indicated satisfaction with support response times and issue resolution."
        ]

        with patch('httpx.AsyncClient.post') as mock_post:
            # Mock LLM to return different topic formats
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {
                'choices': [{
                    'message': {
                        'content': '["topic1", "topic2", "topic3"]'
                    }
                }]
            }

            for summary in test_cases:
                topics = await summarizer._extract_topics(summary)
                assert isinstance(topics, list)
                assert len(topics) >= 1
                assert len(topics) <= 5
                # Verify topics are strings
                assert all(isinstance(topic, str) for topic in topics)

    @pytest.mark.asyncio
    async def test_sentiment_analysis_edge_cases(self, mock_services):
        """Test sentiment analysis with edge cases."""
        summarizer = create_conversation_summarizer()

        # Test case 1: Strong positive sentiment
        positive_messages = [
            {'role': 'user', 'content': 'This is absolutely fantastic! I love it!', 'created_at': datetime.utcnow()},
            {'role': 'assistant', 'content': 'Great to hear!', 'created_at': datetime.utcnow()},
            {'role': 'user', 'content': 'Perfect! Excellent work, thank you!', 'created_at': datetime.utcnow()}
        ]

        positive_sentiment = await summarizer._analyze_sentiment(positive_messages)
        assert positive_sentiment > 0.5

        # Test case 2: Strong negative sentiment
        negative_messages = [
            {'role': 'user', 'content': 'This is terrible, I hate it!', 'created_at': datetime.utcnow()},
            {'role': 'assistant', 'content': 'I understand your frustration.', 'created_at': datetime.utcnow()},
            {'role': 'user', 'content': 'Awful experience, very disappointing!', 'created_at': datetime.utcnow()}
        ]

        negative_sentiment = await summarizer._analyze_sentiment(negative_messages)
        assert negative_sentiment < -0.5

        # Test case 3: Mixed sentiment
        mixed_messages = [
            {'role': 'user', 'content': 'I love the design but hate the performance!', 'created_at': datetime.utcnow()},
            {'role': 'assistant', 'content': 'Let me help with both aspects.', 'created_at': datetime.utcnow()},
            {'role': 'user', 'content': 'Great! The fix is wonderful, thanks!', 'created_at': datetime.utcnow()}
        ]

        mixed_sentiment = await summarizer._analyze_sentiment(mixed_messages)
        assert -0.5 <= mixed_sentiment <= 0.5

        # Test case 4: No sentiment words
        neutral_messages = [
            {'role': 'user', 'content': 'The system processes data according to specifications.', 'created_at': datetime.utcnow()},
            {'role': 'assistant', 'content': 'Understood. How can I assist?', 'created_at': datetime.utcnow()}
        ]

        neutral_sentiment = await summarizer._analyze_sentiment(neutral_messages)
        assert neutral_sentiment == 0.0