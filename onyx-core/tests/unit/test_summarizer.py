"""
Unit Tests for Conversation Summarizer
Story 4-4: Auto-Summarization Pipeline
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from datetime import datetime
import httpx

from onyx_core.services.summarization.summarizer import (
    ConversationSummarizer,
    SummarizationRequest,
    SummarizationResult,
    create_conversation_summarizer
)


class TestConversationSummarizer:
    """Test cases for ConversationSummarizer."""

    @pytest.fixture
    def summarizer(self):
        """Create a ConversationSummarizer instance."""
        return ConversationSummarizer()

    @pytest.fixture
    def sample_messages(self):
        """Create sample messages for testing."""
        return [
            {
                'id': '1',
                'role': 'user',
                'content': 'I need help planning my project timeline',
                'created_at': datetime.utcnow()
            },
            {
                'id': '2',
                'role': 'assistant',
                'content': 'I can help you create a project timeline. Let me break it down into phases.',
                'created_at': datetime.utcnow()
            },
            {
                'id': '3',
                'role': 'user',
                'content': 'Great! I want to focus on design first, then development.',
                'created_at': datetime.utcnow()
            }
        ]

    def test_initialization(self):
        """Test summarizer initialization."""
        summarizer = ConversationSummarizer("http://custom-proxy:4000")

        assert summarizer.litellm_base_url == "http://custom-proxy:4000"
        assert summarizer.model == "deepseek-main"
        assert summarizer.temperature == 0.3
        assert summarizer.max_tokens == 150
        assert summarizer.timeout == 30

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, summarizer, sample_messages):
        """Test successful summary generation."""
        request = SummarizationRequest(
            conversation_id="conv-123",
            message_range={'start': 1, 'end': 3},
            user_id="user-123"
        )

        # Mock message retrieval
        with patch.object(summarizer, '_get_messages_in_range', return_value=sample_messages):
            # Mock LLM call
            mock_response = {
                'choices': [{
                    'message': {
                        'content': 'User needs help with project planning, focusing on design and development phases.'
                    }
                }]
            }
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response

                # Mock topic extraction
                with patch.object(summarizer, '_extract_topics', return_value=['project planning', 'design', 'development']):
                    # Mock sentiment analysis
                    with patch.object(summarizer, '_analyze_sentiment', return_value=0.5):
                        result = await summarizer.generate_summary(request)

        assert isinstance(result, SummarizationResult)
        assert result.summary == 'User needs help with project planning, focusing on design and development phases.'
        assert result.key_topics == ['project planning', 'design', 'development']
        assert result.sentiment == 0.5
        assert result.confidence == 0.9
        assert result.processing_time > 0
        assert result.message_count == 3

    @pytest.mark.asyncio
    async def test_generate_summary_no_messages(self, summarizer):
        """Test summary generation with no messages."""
        request = SummarizationRequest(
            conversation_id="conv-123",
            message_range={'start': 1, 'end': 3},
            user_id="user-123"
        )

        with patch.object(summarizer, '_get_messages_in_range', return_value=[]):
            with pytest.raises(ValueError, match="No messages found for summarization"):
                await summarizer.generate_summary(request)

    @pytest.mark.asyncio
    async def test_generate_summary_llm_error(self, summarizer, sample_messages):
        """Test summary generation with LLM error."""
        request = SummarizationRequest(
            conversation_id="conv-123",
            message_range={'start': 1, 'end': 3},
            user_id="user-123"
        )

        with patch.object(summarizer, '_get_messages_in_range', return_value=sample_messages):
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.status_code = 500
                mock_post.return_value.json.return_value = {'error': 'Internal server error'}

                with pytest.raises(ValueError, match="LLM API error"):
                    await summarizer.generate_summary(request)

    @pytest.mark.asyncio
    async def test_generate_summary_invalid_length(self, summarizer, sample_messages):
        """Test summary generation with invalid summary length."""
        request = SummarizationRequest(
            conversation_id="conv-123",
            message_range={'start': 1, 'end': 3},
            user_id="user-123",
            max_length=20  # Very short max length
        )

        with patch.object(summarizer, '_get_messages_in_range', return_value=sample_messages):
            # Mock LLM to return too long summary
            mock_response = {
                'choices': [{
                    'message': {
                        'content': 'This is a very long summary that exceeds the maximum allowed length and should fail validation.'
                    }
                }]
            }
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.json.return_value = mock_response

                with patch.object(summarizer, '_extract_topics', return_value=['topic']):
                    with patch.object(summarizer, '_analyze_sentiment', return_value=0.0):
                        with pytest.raises(ValueError, match="Summary length invalid"):
                            await summarizer.generate_summary(request)

    def test_format_conversation(self, summarizer, sample_messages):
        """Test conversation formatting."""
        formatted = summarizer._format_conversation(sample_messages)

        assert 'User:' in formatted
        assert 'Assistant:' in formatted
        assert 'project timeline' in formatted
        assert formatted.count('\n\n') == len(sample_messages) - 1

    def test_validate_summary_length_valid(self, summarizer):
        """Test valid summary length validation."""
        request = SummarizationRequest(
            conversation_id="conv-123",
            message_range={'start': 1, 'end': 3},
            user_id="user-123"
        )

        # Valid length
        valid_summary = "This is a valid summary length."
        assert summarizer._validate_summary_length(valid_summary, request) is True

    def test_validate_summary_length_too_short(self, summarizer):
        """Test too short summary length validation."""
        request = SummarizationRequest(
            conversation_id="conv-123",
            message_range={'start': 1, 'end': 3},
            user_id="user-123",
            min_length=20
        )

        # Too short
        short_summary = "Too short."
        assert summarizer._validate_summary_length(short_summary, request) is False

    def test_validate_summary_length_too_long(self, summarizer):
        """Test too long summary length validation."""
        request = SummarizationRequest(
            conversation_id="conv-123",
            message_range={'start': 1, 'end': 3},
            user_id="user-123",
            max_length=50
        )

        # Too long
        long_summary = "This is a very long summary that exceeds the maximum allowed length for validation purposes."
        assert summarizer._validate_summary_length(long_summary, request) is False

    @pytest.mark.asyncio
    async def test_extract_topics_llm_success(self, summarizer):
        """Test successful topic extraction using LLM."""
        summary = "User discussed project planning and design phases for development."

        # Mock successful LLM response
        mock_response = {
            'choices': [{
                'message': {
                    'content': '["project planning", "design", "development"]'
                }
            }]
        }
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            topics = await summarizer._extract_topics(summary)

        assert topics == ['project planning', 'design', 'development']
        assert len(topics) == 3

    @pytest.mark.asyncio
    async def test_extract_topics_llm_json_error(self, summarizer):
        """Test topic extraction with JSON parsing error."""
        summary = "User discussed project planning."

        # Mock LLM response with invalid JSON
        mock_response = {
            'choices': [{
                'message': {
                    'content': 'project planning, development'  # Not JSON
                }
            }]
        }
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response

            topics = await summarizer._extract_topics(summary)

        # Should fall back to keyword extraction
        assert isinstance(topics, list)
        assert len(topics) > 0

    @pytest.mark.asyncio
    async def test_extract_topics_llm_error(self, summarizer):
        """Test topic extraction with LLM error."""
        summary = "User discussed project planning."

        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 500

            topics = await summarizer._extract_topics(summary)

            # Should fall back to keyword extraction
            assert isinstance(topics, list)

    def test_extract_topics_keyword_fallback(self, summarizer):
        """Test keyword extraction fallback."""
        summary = "User discussed project planning, design phases, and development timeline with team collaboration."

        topics = summarizer._simple_keyword_extraction(summary)

        assert isinstance(topics, list)
        assert len(topics) > 0
        # Should not include stop words
        assert 'the' not in topics
        assert 'and' not in topics
        # Should include meaningful words
        assert any('project' in topic.lower() for topic in topics)

    def test_normalize_topic(self, summarizer):
        """Test topic normalization."""
        # Test basic normalization
        assert summarizer._normalize_topic("PROJECT PLANNING") == "Project Planning"
        assert summarizer._normalize_topic("  design-phase  ") == "Design Phase"
        assert summarizer._normalize_topic("dev@lopment!") == "Devlopment"  # Special chars removed

        # Test stop word removal
        assert summarizer._normalize_topic("The design process") == "Design Process"
        assert summarizer._normalize_topic("Project planning and timeline") == "Project Planning Timeline"

        # Test short topic filtering
        assert summarizer._normalize_topic("It") == ""
        assert summarizer._normalize_topic("A") == ""

    def test_analyze_sentiment_positive(self, summarizer, sample_messages):
        """Test positive sentiment analysis."""
        # Add positive sentiment words to user messages
        sample_messages[0]['content'] = "This is great! I love the project, it's excellent and perfect."
        sample_messages[2]['content'] = "Thanks for the awesome help, this is fantastic!"

        sentiment = await summarizer._analyze_sentiment(sample_messages)

        assert sentiment > 0.5  # Should be positive

    def test_analyze_sentiment_negative(self, summarizer, sample_messages):
        """Test negative sentiment analysis."""
        # Add negative sentiment words to user messages
        sample_messages[0]['content'] = "This is terrible, I hate the problems, it's awful and bad."
        sample_messages[2]['content'] = "This is wrong, the issue is frustrating and disappointing."

        sentiment = await summarizer._analyze_sentiment(sample_messages)

        assert sentiment < -0.5  # Should be negative

    def test_analyze_sentiment_neutral(self, summarizer, sample_messages):
        """Test neutral sentiment analysis."""
        sentiment = await summarizer._analyze_sentiment(sample_messages)

        # Should be close to neutral (around 0)
        assert -0.3 <= sentiment <= 0.3

    def test_analyze_sentiment_empty_messages(self, summarizer):
        """Test sentiment analysis with no messages."""
        sentiment = await summarizer._analyze_sentiment([])

        assert sentiment == 0.0

    def test_analyze_sentiment_no_user_messages(self, summarizer):
        """Test sentiment analysis with no user messages."""
        messages = [
            {
                'role': 'assistant',
                'content': 'I can help you with that.',
                'created_at': datetime.utcnow()
            }
        ]

        sentiment = await summarizer._analyze_sentiment(messages)

        assert sentiment == 0.0

    def test_update_avg_processing_time(self, summarizer):
        """Test average processing time calculation."""
        # First update
        summarizer._update_avg_processing_time(1000)
        assert summarizer.metrics['avg_processing_time'] == 1000

        # Second update with exponential moving average
        summarizer.metrics['summaries_generated'] = 2
        summarizer.metrics['avg_processing_time'] = 1000
        summarizer._update_avg_processing_time(2000)
        # EMA: alpha * new + (1 - alpha) * old
        # 0.1 * 2000 + 0.9 * 1000 = 200 + 900 = 1100
        assert summarizer.metrics['avg_processing_time'] == 1100

    @pytest.mark.asyncio
    async def test_get_metrics(self, summarizer):
        """Test metrics retrieval."""
        # Set some metrics
        summarizer.metrics = {
            'summaries_generated': 100,
            'topics_extracted': 95,
            'sentiment_analyzed': 95,
            'errors': 5,
            'avg_processing_time': 1500
        }

        metrics = await summarizer.get_metrics()

        assert metrics['summaries_generated'] == 100
        assert metrics['topics_extracted'] == 95
        assert metrics['sentiment_analyzed'] == 95
        assert metrics['errors'] == 5
        assert metrics['avg_processing_time'] == 1500
        assert 'updated_at' in metrics

    @pytest.mark.asyncio
    async def test_test_connection_success(self, summarizer):
        """Test successful connection test."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 200

            result = await summarizer.test_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, summarizer):
        """Test failed connection test."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_get.return_value.status_code = 500

            result = await summarizer.test_connection()

            assert result is False

    def test_create_summarizer(self):
        """Test summarizer factory function."""
        summarizer = create_conversation_summarizer("http://test-proxy:4000")

        assert isinstance(summarizer, ConversationSummarizer)
        assert summarizer.litellm_base_url == "http://test-proxy:4000"