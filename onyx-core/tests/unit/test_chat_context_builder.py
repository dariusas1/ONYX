"""
Unit Tests for Chat Context Builder

Tests chat context building with memory injection and LLM formatting.

Story 4-3: Memory Injection & Agent Integration
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.chat_context_builder import ChatContextBuilder
from services.memory_injection_service import MemoryInjection


class TestChatContextBuilder:
    """Test cases for ChatContextBuilder"""

    @pytest.fixture
    def mock_memory_injection_service(self):
        """Mock memory injection service"""
        service = AsyncMock(spec=ChatContextBuilder)
        return service

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service"""
        service = AsyncMock(spec=ChatContextBuilder)
        return service

    @pytest.fixture
    def context_builder(self, mock_memory_injection_service, mock_memory_service):
        """Create chat context builder with mocked dependencies"""
        builder = ChatContextBuilder()
        builder.memory_injection_service = mock_memory_injection_service
        builder.memory_service = mock_memory_service
        return builder

    @pytest.fixture
    def sample_memory_injection(self):
        """Sample memory injection for testing"""
        return MemoryInjection(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            standing_instructions=[
                {
                    "id": "instruction-1",
                    "instruction_text": "Always cite sources when referencing documents"
                }
            ],
            memories=[
                {
                    "id": "memory-1",
                    "fact": "User prefers defense contracts",
                    "category": "priority",
                    "confidence": 0.95,
                    "source_type": "manual",
                    "created_at": datetime.utcnow()
                }
            ],
            injection_text="STANDING INSTRUCTIONS:\n1. Always cite sources when referencing documents\n\nUSER CONTEXT (Key memories):\n1. User prefers defense contracts (priority, 95% confidence, 0d ago, manual)\n\n",
            injection_time=25,
            performance_stats={"instructions_count": 1, "memories_count": 1}
        )

    @pytest.fixture
    def sample_conversation_history(self):
        """Sample conversation history"""
        return [
            {
                "role": "user",
                "content": "I need help with defense contracts",
                "timestamp": "2025-01-15T10:00:00Z"
            },
            {
                "role": "assistant",
                "content": "I can help you with defense contracts",
                "timestamp": "2025-01-15T10:01:00Z"
            }
        ]

    @pytest.mark.asyncio
    async def test_build_context_success(self, context_builder, mock_memory_injection_service, sample_memory_injection, sample_conversation_history):
        """Test successful context building"""
        # Mock memory injection service
        mock_memory_injection_service.prepare_injection.return_value = sample_memory_injection

        result = await context_builder.build_context(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            current_message="Help me with defense contracts",
            recent_history=sample_conversation_history
        )

        # Verify context structure
        assert result["user_id"] == "test-user-123"
        assert result["conversation_id"] == "test-conversation-456"
        assert "system_prompt" in result
        assert "memory_injection" in result
        assert "recent_context" in result
        assert "context_build_time_ms" in result
        assert "total_tokens_estimate" in result
        assert "context_metadata" in result

        # Verify system prompt contains memory injection
        system_prompt = result["system_prompt"]
        assert "STANDING INSTRUCTIONS" in system_prompt
        assert "USER CONTEXT (Key memories)" in system_prompt
        assert "User prefers defense contracts" in system_prompt
        assert "Always cite sources" in system_prompt

        # Verify recent context is included
        assert "I need help with defense contracts" in result["recent_context"]
        assert "I can help you with defense contracts" in result["recent_context"]

        # Verify metadata
        metadata = result["context_metadata"]
        assert metadata["injection_enabled"] is True
        assert metadata["context_version"] == "1.0"
        assert "built_at" in metadata

    @pytest.mark.asyncio
    async def test_build_context_without_history(self, context_builder, mock_memory_injection_service, sample_memory_injection):
        """Test context building without recent history"""
        mock_memory_injection_service.prepare_injection.return_value = sample_memory_injection

        result = await context_builder.build_context(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            current_message="Help me with defense contracts",
            recent_history=None
        )

        # Should still build context
        assert result["system_prompt"] != ""
        assert result["recent_context"] == ""  # Empty when no history

    @pytest.mark.asyncio
    async def test_build_context_with_empty_injection(self, context_builder, mock_memory_injection_service):
        """Test context building with empty memory injection"""
        empty_injection = MemoryInjection(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            standing_instructions=[],
            memories=[],
            injection_text="",
            injection_time=10,
            performance_stats={"instructions_count": 0, "memories_count": 0}
        )
        mock_memory_injection_service.prepare_injection.return_value = empty_injection

        result = await context_builder.build_context(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            current_message="Help me with defense contracts"
        )

        # Should build fallback context
        assert result["system_prompt"] != ""
        assert "You are Manus, M3rcury's strategic intelligence advisor" in result["system_prompt"]
        assert result["memory_injection"]["memories_count"] == 0
        assert result["memory_injection"]["instructions_count"] == 0

    @pytest.mark.asyncio
    async def test_build_context_error_handling(self, context_builder, mock_memory_injection_service):
        """Test context building with error handling"""
        # Mock service to raise exception
        mock_memory_injection_service.prepare_injection.side_effect = Exception("Service error")

        result = await context_builder.build_context(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            current_message="Help me with defense contracts"
        )

        # Should return fallback context
        assert result["system_prompt"] != ""
        assert result["context_metadata"]["injection_enabled"] is False
        assert result["context_metadata"]["fallback_used"] is True
        assert "error" in result["context_metadata"]

    @pytest.mark.asyncio
    async def test_update_context_success(self, context_builder):
        """Test successful context update"""
        # Mock context-aware memories
        context_memories = [
            {
                "id": "context-memory-1",
                "fact": "User is interested in aerospace projects",
                "category": "preference",
                "confidence": 0.9
            }
        ]

        with patch.object(context_builder.memory_injection_service, 'get_context_aware_memories', return_value=context_memories):
            result = await context_builder.update_context(
                user_id="test-user-123",
                conversation_id="test-conversation-456",
                new_message="Tell me about aerospace contracts",
                new_memory_suggestions=["User prefers aerospace projects"]
            )

        assert result["success"] is True
        assert result["context_update"]["user_id"] == "test-user-123"
        assert result["context_update"]["conversation_id"] == "test-conversation-456"
        assert result["context_update"]["current_message"] == "Tell me about aerospace contracts"
        assert result["context_update"]["suggested_memories"] == ["User prefers aerospace projects"]
        assert result["context_update"]["context_memories_count"] == 1
        assert "update_timestamp" in result["context_update"]

    @pytest.mark.asyncio
    async def test_update_context_with_memory_suggestions(self, context_builder):
        """Test context update with memory suggestions"""
        with patch.object(context_builder.memory_injection_service, 'get_context_aware_memories', return_value=[]):
            result = await context_builder.update_context(
                user_id="test-user-123",
                conversation_id="test-conversation-456",
                new_message="I just completed a project",
                new_memory_suggestions=["User completed aerospace project", "User is satisfied with results"]
            )

        assert result["success"] is True
        assert result["context_update"]["memory_extraction_needed"] is True
        assert result["context_update"]["suggested_memories"] == [
            "User completed aerospace project",
            "User is satisfied with results"
        ]

    @pytest.mark.asyncio
    async def test_update_context_error_handling(self, context_builder):
        """Test context update error handling"""
        with patch.object(context_builder.memory_injection_service, 'get_context_aware_memories', side_effect=Exception("Context error")):
            result = await context_builder.update_context(
                user_id="test-user-123",
                conversation_id="test-conversation-456",
                new_message="Test message"
            )

        assert result["success"] is False
        assert "error" in result
        assert result["context_update"] is None

    def test_get_recent_conversation_context(self, context_builder, sample_conversation_history):
        """Test recent conversation context formatting"""
        context = context_builder._get_recent_conversation_context(sample_conversation_history)

        assert "User: I need help with defense contracts" in context
        assert "Manus: I can help you with defense contracts" in context
        assert "[10:00] User:" in context  # Timestamp formatting

        # Test with empty history
        empty_context = context_builder._get_recent_conversation_context([])
        assert empty_context == ""

        # Test with None history
        none_context = context_builder._get_recent_conversation_context(None)
        assert none_context == ""

    def test_build_system_prompt(self, context_builder, sample_memory_injection):
        """Test system prompt building"""
        recent_context = "User: I need help\nManus: I can help"

        prompt = context_builder._build_system_prompt(
            memory_injection=sample_memory_injection,
            recent_context=recent_context,
            current_message="Help with defense contracts"
        )

        # Verify prompt structure
        assert "You are Manus, M3rcury's strategic intelligence advisor." in prompt
        assert "STANDING INSTRUCTIONS:" in prompt
        assert "USER CONTEXT (Key memories):" in prompt
        assert "RECENT CONVERSATION CONTEXT:" in prompt
        assert "RESPONSE GUIDELINES:" in prompt
        assert "Current conversation continues below:" in prompt

        # Verify content inclusion
        assert "Always cite sources when referencing documents" in prompt
        assert "User prefers defense contracts" in prompt
        assert "I need help" in prompt
        assert "I can help" in prompt

    def test_build_fallback_context(self, context_builder):
        """Test fallback context building"""
        result = context_builder._build_fallback_context(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            error="Service unavailable",
            build_time=15
        )

        assert result["user_id"] == "test-user-123"
        assert result["conversation_id"] == "test-conversation-456"
        assert result["context_build_time_ms"] == 15
        assert result["context_metadata"]["injection_enabled"] is False
        assert result["context_metadata"]["fallback_used"] is True
        assert result["context_metadata"]["error"] == "Service unavailable"

        # Verify fallback prompt
        assert "You are Manus, M3rcury's strategic intelligence advisor." in result["system_prompt"]
        assert "RESPONSE GUIDELINES:" in result["system_prompt"]

    def test_estimate_tokens(self, context_builder):
        """Test token estimation"""
        # Test with normal text
        text = "This is a test message with some content"
        tokens = context_builder._estimate_tokens(text)
        assert tokens > 0

        # Test with empty text
        assert context_builder._estimate_tokens("") == 0

        # Test with None
        assert context_builder._estimate_tokens(None) == 0

        # Test with long text
        long_text = "word " * 100
        tokens = context_builder._estimate_tokens(long_text)
        assert tokens > 200  # Should be ~500 characters / 4 = 125 tokens, plus buffer

    @pytest.mark.asyncio
    async def test_build_context_with_constraints(self, context_builder, mock_memory_injection_service, sample_memory_injection):
        """Test context building with constraints"""
        mock_memory_injection_service.prepare_injection.return_value = sample_memory_injection

        result = await context_builder.build_context_with_constraints(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            current_message="Help me with defense contracts",
            max_tokens=1000,  # Small limit to trigger truncation
            priority_categories=["priority", "decision"],
            exclude_categories=["summary"]
        )

        assert result["user_id"] == "test-user-123"
        assert result["context_metadata"]["truncated"] is True  # Should be truncated due to token limit
        assert result["context_metadata"]["category_filtered"] is True
        assert result["context_metadata"]["priority_categories"] == ["priority", "decision"]
        assert result["context_metadata"]["exclude_categories"] == ["summary"]

    def test_truncate_context(self, context_builder):
        """Test context truncation"""
        # Create a long context
        long_prompt = "You are Manus.\n\n" + "STANDING INSTRUCTIONS:\n"
        for i in range(20):
            long_prompt += f"{i}. This is instruction {i}.\n"
        long_prompt += "\nUSER CONTEXT:\n"
        for i in range(20):
            long_prompt += f"{i}. This is memory {i}.\n"

        # Truncate to 100 tokens
        truncated = context_builder._truncate_context(long_prompt, 100)

        # Should be much shorter
        assert len(truncated) < len(long_prompt)
        assert "You are Manus." in truncated
        assert truncated.endswith("Current conversation continues below:")

    def test_filter_context_by_categories(self, context_builder):
        """Test context filtering by categories"""
        # Create context with different memory categories
        context_with_categories = """You are Manus.

STANDING INSTRUCTIONS:
1. General instruction

USER CONTEXT (Key memories):
1. User priority item (priority, 95% confidence)
2. User decision item (decision, 90% confidence)
3. User summary item (summary, 85% confidence)
4. User preference item (preference, 80% confidence)

RECENT CONVERSATION CONTEXT:
User: Test message
Manus: Test response"""

        # Test with priority categories only
        filtered = context_builder._filter_context_by_categories(
            context_with_categories,
            ["priority", "decision"],
            []
        )
        assert "User priority item" in filtered
        assert "User decision item" in filtered
        assert "User summary item" not in filtered  # Excluded
        assert "User preference item" not in filtered  # Not prioritized

        # Test with excluded categories
        filtered = context_builder._filter_context_by_categories(
            context_with_categories,
            [],
            ["summary"]
        )
        assert "User priority item" in filtered
        assert "User decision item" in filtered
        assert "User preference item" in filtered
        assert "User summary item" not in filtered  # Excluded

        # Test with both priority and excluded
        filtered = context_builder._filter_context_by_categories(
            context_with_categories,
            ["priority"],
            ["summary", "preference"]
        )
        assert "User priority item" in filtered
        assert "User decision item" not in filtered  # Not prioritized
        assert "User summary item" not in filtered  # Excluded
        assert "User preference item" not in filtered  # Excluded

    @pytest.mark.asyncio
    async def test_track_memory_usage(self, context_builder):
        """Test memory usage tracking"""
        # Create mock memory injection with specific IDs
        injection = MemoryInjection(
            user_id="test-user-123",
            conversation_id="test-conversation-456",
            standing_instructions=[
                {"id": "instruction-1", "instruction_text": "Test instruction"}
            ],
            memories=[
                {"id": "memory-1", "fact": "Test memory"},
                {"id": "memory-2", "fact": "Another test memory"}
            ],
            injection_text="",
            injection_time=20,
            performance_stats={}
        )

        # Mock database connection
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        conn.cursor.return_value.__exit__.return_value = None
        conn.commit = MagicMock()

        with patch.object(context_builder.memory_injection_service, '_get_connection', return_value=conn):
            await context_builder._track_memory_usage("test-user-123", injection)

        # Verify database calls were made
        assert cursor.execute.call_count == 2  # Once for memories, once for instructions
        conn.commit.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])