"""
Unit Tests for Memory Injection Service

Tests memory injection functionality, scoring algorithms, and performance.

Story 4-3: Memory Injection & Agent Integration
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from services.memory_injection_service import (
    MemoryInjectionService,
    MemoryInjection,
    CachedInjection
)
from services.memory_service import MemoryService


class TestMemoryInjectionService:
    """Test cases for MemoryInjectionService"""

    @pytest.fixture
    def mock_connection(self):
        """Mock database connection"""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        conn.cursor.return_value.__exit__.return_value = None
        conn.commit = MagicMock()
        return conn, cursor

    @pytest.fixture
    def injection_service(self):
        """Create memory injection service instance"""
        service = MemoryInjectionService()
        service.cache = {}  # Start with empty cache
        return service

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing"""
        return {
            "user_id": "test-user-123",
            "conversation_id": "test-conversation-456"
        }

    @pytest.fixture
    def sample_memories(self):
        """Sample memories for testing"""
        return [
            {
                "id": "memory-1",
                "fact": "User prefers defense contracts and aerospace projects",
                "category": "priority",
                "confidence": 0.95,
                "source_type": "manual",
                "created_at": datetime.utcnow() - timedelta(days=2),
                "access_count": 5,
                "memory_score": 0.92
            },
            {
                "id": "memory-2",
                "fact": "Recently decided to prioritize Onyx platform development",
                "category": "decision",
                "confidence": 0.9,
                "source_type": "manual",
                "created_at": datetime.utcnow() - timedelta(days=5),
                "access_count": 3,
                "memory_score": 0.85
            },
            {
                "id": "memory-3",
                "fact": "Current focus on AI infrastructure projects",
                "category": "goal",
                "confidence": 0.88,
                "source_type": "extracted_from_chat",
                "created_at": datetime.utcnow() - timedelta(days=1),
                "access_count": 8,
                "memory_score": 0.90
            }
        ]

    @pytest.fixture
    def sample_instructions(self):
        """Sample standing instructions for testing"""
        return [
            {
                "id": "instruction-1",
                "instruction_text": "Always cite sources when referencing specific documents",
                "category": "workflow",
                "priority": 9,
                "context_hints": ["research", "documents"],
                "usage_count": 15,
                "priority_score": 0.95
            },
            {
                "id": "instruction-2",
                "instruction_text": "Focus on strategic implications and actionable recommendations",
                "category": "communication",
                "priority": 8,
                "context_hints": ["strategy", "planning"],
                "usage_count": 12,
                "priority_score": 0.88
            }
        ]

    @pytest.mark.asyncio
    async def test_prepare_injection_success(self, injection_service, mock_connection, sample_user_data, sample_memories, sample_instructions):
        """Test successful memory injection preparation"""
        conn, cursor = mock_connection

        # Mock database queries
        cursor.fetchall.side_effect = [
            sample_instructions,  # First call for instructions
            sample_memories     # Second call for memories
        ]

        with patch.object(injection_service, '_get_connection', return_value=conn):
            result = await injection_service.prepare_injection(
                user_id=sample_user_data["user_id"],
                conversation_id=sample_user_data["conversation_id"],
                current_message="I need help with defense contracts"
            )

        # Verify injection result
        assert isinstance(result, MemoryInjection)
        assert result.user_id == sample_user_data["user_id"]
        assert result.conversation_id == sample_user_data["conversation_id"]
        assert len(result.standing_instructions) == 2
        assert len(result.memories) == 3
        assert result.injection_text != ""
        assert result.injection_time > 0
        assert result.performance_stats["cache_hit"] is False

    @pytest.mark.asyncio
    async def test_prepare_injection_cache_hit(self, injection_service, sample_user_data, sample_memories, sample_instructions):
        """Test memory injection cache hit"""
        # Pre-populate cache
        cache_key = f"{sample_user_data['user_id']}:{sample_user_data['conversation_id']}"
        cached_injection = MemoryInjection(
            user_id=sample_user_data["user_id"],
            conversation_id=sample_user_data["conversation_id"],
            standing_instructions=sample_instructions,
            memories=sample_memories,
            injection_text="Cached injection text",
            injection_time=25,
            performance_stats={"cache_hit": True}
        )
        injection_service.cache[cache_key] = CachedInjection(
            injection=cached_injection,
            timestamp=time.time(),
            ttl=300
        )

        result = await injection_service.prepare_injection(
            user_id=sample_user_data["user_id"],
            conversation_id=sample_user_data["conversation_id"]
        )

        # Should return cached result
        assert result.injection_text == "Cached injection text"
        assert result.performance_stats["cache_hit"] is True
        assert result.injection_time == 25  # Preserved from cached injection

    @pytest.mark.asyncio
    async def test_prepare_injection_database_error(self, injection_service, sample_user_data):
        """Test memory injection with database error"""
        with patch.object(injection_service, '_get_connection', side_effect=Exception("Database connection failed")):
            result = await injection_service.prepare_injection(
                user_id=sample_user_data["user_id"],
                conversation_id=sample_user_data["conversation_id"]
            )

        # Should return fallback injection
        assert isinstance(result, MemoryInjection)
        assert result.user_id == sample_user_data["user_id"]
        assert result.conversation_id == sample_user_data["conversation_id"]
        assert len(result.standing_instructions) == 0
        assert len(result.memories) == 0
        assert result.injection_text == ""
        assert "error" in result.performance_stats

    @pytest.mark.asyncio
    async def test_get_top_standing_instructions(self, injection_service, mock_connection, sample_instructions):
        """Test getting top standing instructions"""
        conn, cursor = mock_connection
        cursor.fetchall.return_value = sample_instructions

        with patch.object(injection_service, '_get_connection', return_value=conn):
            result = await injection_service._get_top_standing_instructions(cursor, "test-user", 10)

        assert len(result) == 2
        assert result[0]["instruction_text"] == "Always cite sources when referencing specific documents"
        assert result[0]["category"] == "workflow"

    @pytest.mark.asyncio
    async def test_get_top_memories_scoring_algorithm(self, injection_service, mock_connection, sample_memories):
        """Test memory scoring algorithm"""
        conn, cursor = mock_connection
        cursor.fetchall.return_value = sample_memories

        with patch.object(injection_service, '_get_connection', return_value=conn):
            result = await injection_service._get_top_memories(cursor, "test-user")

        assert len(result) == 3
        # Verify memories are ordered by memory_score
        assert result[0]["memory_score"] >= result[1]["memory_score"]
        assert result[1]["memory_score"] >= result[2]["memory_score"]

        # Verify scoring components
        memory = result[0]  # Highest scored memory
        assert memory["confidence"] == 0.95  # High confidence contributes to score
        assert memory["category"] == "priority"  # Priority category gets bonus

    def test_format_for_llm(self, injection_service, sample_instructions, sample_memories):
        """Test LLM formatting"""
        injection_text = injection_service._format_for_llm(sample_instructions, sample_memories)

        # Check that all sections are present
        assert "STANDING INSTRUCTIONS:" in injection_text
        assert "USER CONTEXT (Key memories):" in injection_text

        # Check that all instructions are included
        assert "Always cite sources when referencing specific documents" in injection_text
        assert "Focus on strategic implications" in injection_text

        # Check that all memories are included with proper formatting
        assert "User prefers defense contracts" in injection_text
        assert "priority, 95% confidence" in injection_text
        assert "decision, 90% confidence" in injection_text

    def test_format_age(self, injection_service):
        """Test age formatting"""
        # Test different age scenarios
        now = datetime.utcnow()

        # Just now
        assert injection_service._format_age(now - timedelta(minutes=30)) == "just now"

        # Hours
        assert injection_service._format_age(now - timedelta(hours=3)) == "3h"
        assert injection_service._format_age(now - timedelta(hours=23)) == "23h"

        # Days
        assert injection_service._format_age(now - timedelta(days=2)) == "2d"
        assert injection_service._format_age(now - timedelta(days=6)) == "6d"

        # Weeks
        assert injection_service._format_age(now - timedelta(weeks=2)) == "2w"

        # None/invalid
        assert injection_service._format_age(None) == "unknown"

    def test_format_source(self, injection_service):
        """Test source type formatting"""
        assert injection_service._format_source("manual") == "manual"
        assert injection_service._format_source("extracted_from_chat") == "extracted"
        assert injection_service._format_source("auto_summary") == "summary"
        assert injection_service._format_source("standing_instruction") == "instruction"
        assert injection_service._format_source("unknown") == "unknown"

    def test_cache_operations(self, injection_service, sample_user_data):
        """Test cache operations"""
        cache_key = f"{sample_user_data['user_id']}:{sample_user_data['conversation_id']}"

        # Test cache miss
        cached = injection_service._get_cached_injection(cache_key)
        assert cached is None

        # Test cache set
        injection = MemoryInjection(
            user_id=sample_user_data["user_id"],
            conversation_id=sample_user_data["conversation_id"],
            standing_instructions=[],
            memories=[],
            injection_text="Test",
            injection_time=10,
            performance_stats={}
        )
        injection_service._cache_injection(cache_key, injection)

        # Test cache hit
        cached = injection_service._get_cached_injection(cache_key)
        assert cached is not None
        assert cached.injection.injection_text == "Test"

        # Test cache TTL expiration
        injection_service.cache_ttl = 0.001  # Very short TTL
        time.sleep(0.002)  # Wait for TTL to expire
        cached = injection_service._get_cached_injection(cache_key)
        assert cached is None

    @pytest.mark.asyncio
    async def test_get_context_aware_memories(self, injection_service, sample_user_data):
        """Test context-aware memory retrieval"""
        # Mock database response
        mock_memories = [
            {
                "id": "context-memory-1",
                "fact": "User is working on aerospace defense project",
                "category": "priority",
                "confidence": 0.9,
                "relevance_score": 0.85
            }
        ]

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        conn.cursor.return_value.__exit__.return_value = None
        cursor.fetchall.return_value = mock_memories

        with patch.object(injection_service, '_get_connection', return_value=conn):
            result = await injection_service.get_context_aware_memories(
                user_id=sample_user_data["user_id"],
                conversation_id=sample_user_data["conversation_id"],
                current_message="I need help with aerospace defense contracts",
                limit=8
            )

        assert len(result) == 1
        assert "aerospace" in result[0]["fact"]

    def test_extract_keywords(self, injection_service):
        """Test keyword extraction"""
        # Test with normal text
        text = "I need help with aerospace defense contracts and project management"
        keywords = injection_service._extract_keywords(text)
        assert len(keywords) > 0
        assert "help" in keywords
        assert "aerospace" in keywords
        assert "defense" in keywords

        # Test with empty text
        assert injection_service._extract_keywords("") == []

        # Test with None
        assert injection_service._extract_keywords(None) == []

    @pytest.mark.asyncio
    async def test_get_injection_analytics(self, injection_service, sample_user_data):
        """Test injection analytics retrieval"""
        # Mock database response
        mock_analytics = {
            "total_injections": 15,
            "avg_performance_ms": 35.5,
            "successful_injections": 14,
            "failed_injections": 1,
            "total_memories_injected": 45
        }

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        conn.cursor.return_value.__exit__.return_value = None
        cursor.fetchone.return_value = mock_analytics

        with patch.object(injection_service, '_get_connection', return_value=conn):
            result = await injection_service.get_injection_analytics(
                user_id=sample_user_data["user_id"],
                days=7
            )

        assert result["period_days"] == 7
        assert result["total_injections"] == 15
        assert result["avg_performance_ms"] == 35.5
        assert result["success_rate"] == (14 / 15) * 100  # ~93.33%
        assert result["total_memories_injected"] == 45

    @pytest.mark.asyncio
    async def test_performance_targets(self, injection_service, mock_connection, sample_user_data, sample_memories, sample_instructions):
        """Test that performance targets are met"""
        conn, cursor = mock_connection
        cursor.fetchall.side_effect = [
            sample_instructions,
            sample_memories
        ]

        with patch.object(injection_service, '_get_connection', return_value=conn):
            start_time = time.time()
            result = await injection_service.prepare_injection(
                user_id=sample_user_data["user_id"],
                conversation_id=sample_user_data["conversation_id"]
            )
            end_time = time.time()

        # Performance assertions
        assert result.injection_time < 50  # Should be under 50ms
        assert result.performance_stats["cache_hit"] is False  # First call, no cache hit

        # Test cache performance
        cache_key = f"{sample_user_data['user_id']}:{sample_user_data['conversation_id']}"
        start_time = time.time()
        cached_result = await injection_service.prepare_injection(
            user_id=sample_user_data["user_id"],
            conversation_id=sample_user_data["conversation_id"]
        )
        end_time = time.time()

        # Cache should be much faster
        assert cached_result.injection_time < 5  # Cached should be under 5ms
        assert cached_result.performance_stats["cache_hit"] is True


if __name__ == "__main__":
    pytest.main([__file__])