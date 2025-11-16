"""
Memory Injection Service Tests
Story 4-2: Memory Injection & Agent Integration
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from services.memory_injection_service import (
    MemoryInjectionService,
    MemoryInjection,
    CachedInjection,
    get_memory_injection_service
)


class TestMemoryInjectionService:
    """Test suite for MemoryInjectionService"""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection for testing"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.commit = MagicMock()
        return mock_conn, mock_cursor

    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return MemoryInjectionService()

    @pytest.fixture
    def sample_memories(self):
        """Sample memory data for testing"""
        return [
            {
                'id': 'mem-1',
                'fact': 'User prefers TypeScript over JavaScript',
                'category': 'preference',
                'confidence': 0.9,
                'source_type': 'manual',
                'created_at': datetime.now() - timedelta(days=1),
                'access_count': 5,
                'last_accessed_at': datetime.now() - timedelta(hours=2),
                'memory_score': 0.85
            },
            {
                'id': 'mem-2',
                'fact': 'Working on Q4 financial planning',
                'category': 'goal',
                'confidence': 0.85,
                'source_type': 'extracted_from_chat',
                'created_at': datetime.now() - timedelta(days=3),
                'access_count': 2,
                'last_accessed_at': datetime.now() - timedelta(hours=6),
                'memory_score': 0.78
            }
        ]

    @pytest.fixture
    def sample_instructions(self):
        """Sample standing instructions for testing"""
        return [
            {
                'id': 'inst-1',
                'instruction_text': 'Always provide code examples with TypeScript types',
                'category': 'workflow',
                'priority': 8,
                'context_hints': ['coding', 'typescript'],
                'usage_count': 12,
                'last_used_at': datetime.now() - timedelta(hours=1),
                'priority_score': 0.92
            },
            {
                'id': 'inst-2',
                'instruction_text': 'Consider security implications in all recommendations',
                'category': 'security',
                'priority': 9,
                'context_hints': ['security', 'recommendations'],
                'usage_count': 8,
                'last_used_at': datetime.now() - timedelta(hours=3),
                'priority_score': 0.95
            }
        ]

    @pytest.mark.asyncio
    async def test_prepare_injection_success(self, service, sample_memories, sample_instructions, mock_db_connection):
        """Test successful memory injection preparation"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock database queries
        mock_cursor.fetchall.side_effect = [
            sample_instructions,  # First query for instructions
            sample_memories       # Second query for memories
        ]

        with patch.object(service, '_get_connection', return_value=mock_conn):
            result = await service.prepare_injection(
                user_id='user-123',
                conversation_id='conv-456',
                current_message='Help me with TypeScript setup'
            )

        # Verify result structure
        assert isinstance(result, MemoryInjection)
        assert result.user_id == 'user-123'
        assert result.conversation_id == 'conv-456'
        assert len(result.standing_instructions) == 2
        assert len(result.memories) == 2
        assert result.injection_time >= 0
        assert result.performance_stats['cache_hit'] == False
        assert result.performance_stats['instructions_count'] == 2
        assert result.performance_stats['memories_count'] == 2

        # Verify injection text formatting
        injection_text = result.injection_text
        assert 'STANDING INSTRUCTIONS:' in injection_text
        assert 'USER CONTEXT (Key memories):' in injection_text
        assert 'TypeScript' in injection_text
        assert 'financial planning' in injection_text

    @pytest.mark.asyncio
    async def test_prepare_injection_cache_hit(self, service, sample_memories, sample_instructions):
        """Test memory injection with cache hit"""
        # Prepare injection first time
        with patch.object(service, '_get_connection') as mock_get_conn:
            mock_conn, mock_cursor = MagicMock(), MagicMock()
            mock_cursor.fetchall.side_effect = [sample_instructions, sample_memories]
            mock_get_conn.return_value = mock_conn

            result1 = await service.prepare_injection(
                user_id='user-123',
                conversation_id='conv-456'
            )

        assert result1.performance_stats['cache_hit'] == False

        # Second call should hit cache
        with patch.object(service, '_get_connection') as mock_get_conn:
            result2 = await service.prepare_injection(
                user_id='user-123',
                conversation_id='conv-456'
            )

        assert result2.performance_stats['cache_hit'] == True
        assert result2.standing_instructions == result1.standing_instructions
        assert result2.memories == result1.memories

    @pytest.mark.asyncio
    async def test_prepare_injection_database_error(self, service):
        """Test memory injection with database error"""
        with patch.object(service, '_get_connection', side_effect=Exception("Database error")):
            result = await service.prepare_injection(
                user_id='user-123',
                conversation_id='conv-456'
            )

        # Should return fallback injection
        assert isinstance(result, MemoryInjection)
        assert result.user_id == 'user-123'
        assert result.conversation_id == 'conv-456'
        assert len(result.standing_instructions) == 0
        assert len(result.memories) == 0
        assert result.injection_text == ""
        assert 'error' in result.performance_stats

    def test_format_for_llm(self, service, sample_memories, sample_instructions):
        """Test LLM formatting of memories and instructions"""
        injection_text = service._format_for_llm(sample_instructions, sample_memories)

        # Verify structure
        assert injection_text.startswith('STANDING INSTRUCTIONS:')
        assert 'USER CONTEXT (Key memories):' in injection_text

        # Verify instruction formatting
        assert '1. Always provide code examples with TypeScript types' in injection_text
        assert '2. Consider security implications' in injection_text

        # Verify memory formatting with metadata
        assert '1. User prefers TypeScript over JavaScript' in injection_text
        assert '(preference, 90% confidence' in injection_text
        assert '2. Working on Q4 financial planning' in injection_text
        assert '(goal, 85% confidence' in injection_text

    def test_format_age(self, service):
        """Test age formatting for memories"""
        now = datetime.now()

        # Test recent memory
        recent = now - timedelta(minutes=30)
        assert service._format_age(recent) == 'just now'

        # Test hours ago
        hours_ago = now - timedelta(hours=3)
        assert service._format_age(hours_ago) == '3h'

        # Test days ago
        days_ago = now - timedelta(days=2)
        assert service._format_age(days_ago) == '2d'

        # Test weeks ago
        weeks_ago = now - timedelta(weeks=2)
        assert service._format_age(weeks_ago) == '2w'

    def test_format_source(self, service):
        """Test source type formatting"""
        assert service._format_source('manual') == 'manual'
        assert service._format_source('extracted_from_chat') == 'extracted'
        assert service._format_source('auto_summary') == 'summary'
        assert service._format_source('standing_instruction') == 'instruction'
        assert service._format_source('unknown') == 'unknown'

    def test_cache_operations(self, service):
        """Test caching functionality"""
        # Create test injection
        injection = MemoryInjection(
            user_id='user-123',
            conversation_id='conv-456',
            standing_instructions=[],
            memories=[],
            injection_text='test',
            injection_time=50,
            performance_stats={}
        )

        # Test cache miss
        cached = service._get_cached_injection('user-123:conv-456')
        assert cached is None

        # Test cache store
        service._cache_injection('user-123:conv-456', injection)
        cached = service._get_cached_injection('user-123:conv-456')
        assert cached is not None
        assert cached.injection.user_id == 'user-123'

        # Test cache expiration
        expired_time = time.time() - 400  # Past default TTL of 300 seconds
        service.cache['user-123:conv-456'].timestamp = expired_time
        cached = service._get_cached_injection('user-123:conv-456')
        assert cached is None

    @pytest.mark.asyncio
    async def test_get_context_aware_memories(self, service, mock_db_connection):
        """Test context-aware memory retrieval"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock semantic search results
        mock_cursor.fetchall.return_value = [
            {
                'id': 'mem-1',
                'fact': 'User has TypeScript experience',
                'category': 'context',
                'confidence': 0.9,
                'relevance_score': 0.95
            }
        ]

        with patch.object(service, '_get_connection', return_value=mock_conn):
            results = await service.get_context_aware_memories(
                user_id='user-123',
                conversation_id='conv-456',
                current_message='Help with TypeScript project setup',
                limit=5
            )

        assert len(results) == 1
        assert results[0]['fact'] == 'User has TypeScript experience'
        assert results[0]['relevance_score'] == 0.95

    def test_extract_keywords(self, service):
        """Test keyword extraction for semantic matching"""
        text = "I need help setting up a TypeScript React project with authentication"
        keywords = service._extract_keywords(text)

        # Should extract meaningful keywords
        assert 'help' in keywords
        assert 'setting' in keywords
        assert 'typescript' in keywords
        assert 'react' in keywords
        assert 'project' in keywords
        assert 'authentication' in keywords

        # Should filter out stop words
        assert 'the' not in keywords
        assert 'and' not in keywords
        assert 'with' not in keywords

    @pytest.mark.asyncio
    async def test_get_injection_analytics(self, service, mock_db_connection):
        """Test injection analytics retrieval"""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = {
            'total_injections': 25,
            'avg_performance_ms': 75.5,
            'successful_injections': 24,
            'failed_injections': 1,
            'total_memories_injected': 150
        }

        with patch.object(service, '_get_connection', return_value=mock_conn):
            analytics = await service.get_injection_analytics(
                user_id='user-123',
                days=7
            )

        assert analytics['period_days'] == 7
        assert analytics['total_injections'] == 25
        assert analytics['avg_performance_ms'] == 75.5
        assert analytics['success_rate'] == 96.0  # 24/25 * 100
        assert analytics['total_memories_injected'] == 150
        assert 'cache_hit_rate' in analytics

    def test_get_memory_injection_service_singleton(self):
        """Test global service instance management"""
        service1 = get_memory_injection_service()
        service2 = get_memory_injection_service()

        # Should return the same instance
        assert service1 is service2
        assert isinstance(service1, MemoryInjectionService)


class TestCachedInjection:
    """Test suite for CachedInjection dataclass"""

    def test_cached_injection_creation(self):
        """Test CachedInjection dataclass creation"""
        injection = MemoryInjection(
            user_id='user-123',
            conversation_id='conv-456',
            standing_instructions=[],
            memories=[],
            injection_text='test',
            injection_time=50,
            performance_stats={}
        )

        cached = CachedInjection(
            injection=injection,
            timestamp=time.time()
        )

        assert cached.injection == injection
        assert cached.ttl == 300  # Default TTL
        assert cached.timestamp > 0

    def test_cached_injection_expiration(self):
        """Test cache expiration logic"""
        injection = MemoryInjection(
            user_id='user-123',
            conversation_id='conv-456',
            standing_instructions=[],
            memories=[],
            injection_text='test',
            injection_time=50,
            performance_stats={}
        )

        # Create expired cached injection
        cached = CachedInjection(
            injection=injection,
            timestamp=time.time() - 400  # Past TTL
        )

        # Simulate expiration check
        is_expired = (time.time() - cached.timestamp) > cached.ttl
        assert is_expired is True


if __name__ == '__main__':
    pytest.main([__file__])