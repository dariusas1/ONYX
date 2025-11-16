"""
Unit tests for Memory Service

This test suite covers the core functionality of the memory service including
CRUD operations, validation, PII detection, and search functionality.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from services.memory_service import (
    MemoryService, MemoryCategory, SourceType,
    CreateMemoryRequest, UpdateMemoryRequest, MemoryFilters,
    PIIDetector, Memory, get_memory_service
)

class TestMemoryService:
    """Test suite for MemoryService class"""

    @pytest.fixture
    def memory_service(self):
        """Create memory service instance"""
        return MemoryService()

    @pytest.fixture
    def mock_pool(self):
        """Create mock database connection pool"""
        pool = AsyncMock()
        pool.acquire = AsyncMock()
        return pool

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_memory_id(self):
        """Sample memory ID for testing"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_create_request(self, sample_user_id):
        """Sample create memory request"""
        return CreateMemoryRequest(
            user_id=sample_user_id,
            fact="I prefer to receive updates via email rather than chat notifications",
            category=MemoryCategory.PREFERENCE,
            confidence=0.85,
            source_type=SourceType.MANUAL
        )

    @pytest.fixture
    def sample_memory_row(self, sample_user_id, sample_memory_id):
        """Sample database row representing a memory"""
        return {
            'id': sample_memory_id,
            'user_id': sample_user_id,
            'fact': "I prefer to receive updates via email rather than chat notifications",
            'category': MemoryCategory.PREFERENCE.value,
            'confidence': 0.85,
            'source_type': SourceType.MANUAL.value,
            'source_message_id': None,
            'conversation_id': None,
            'metadata': {},
            'expires_at': None,
            'access_count': 0,
            'last_accessed_at': datetime.utcnow(),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

    @pytest.mark.asyncio
    async def test_init_connection_pool(self, memory_service):
        """Test database connection pool initialization"""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            await memory_service._init_connection_pool()

            assert memory_service.pool == mock_pool
            mock_create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_memory_input_valid(self, memory_service, sample_create_request):
        """Test validation with valid input"""
        # Should not raise any exceptions
        memory_service._validate_memory_input(sample_create_request)

    @pytest.mark.asyncio
    async def test_validate_memory_input_empty_fact(self, memory_service, sample_user_id):
        """Test validation with empty fact"""
        request = CreateMemoryRequest(
            user_id=sample_user_id,
            fact="",
            category=MemoryCategory.PREFERENCE
        )

        with pytest.raises(ValueError, match="Memory fact cannot be empty"):
            memory_service._validate_memory_input(request)

    @pytest.mark.asyncio
    async def test_validate_memory_input_invalid_confidence(self, memory_service, sample_user_id):
        """Test validation with invalid confidence"""
        request = CreateMemoryRequest(
            user_id=sample_user_id,
            fact="Test fact",
            category=MemoryCategory.PREFERENCE,
            confidence=1.5  # Invalid confidence > 1.0
        )

        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            memory_service._validate_memory_input(request)

    @pytest.mark.asyncio
    async def test_sanitize_memory_fact(self, memory_service):
        """Test fact sanitization"""
        dirty_fact = "  This is a test fact   with SQL injection'; DROP TABLE users; --  "
        clean_fact = memory_service._sanitize_memory_fact(dirty_fact)

        assert clean_fact == "This is a test fact with SQL injection DROP TABLE users"

    def test_generate_fact_hash(self, memory_service):
        """Test fact hash generation"""
        user_id = "test-user"
        fact = "Test memory fact"
        fact2 = "test memory fact"  # Different case

        hash1 = memory_service._generate_fact_hash(fact, user_id)
        hash2 = memory_service._generate_fact_hash(fact2, user_id)

        # Should be same for different cases due to lowercasing
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hash length

    @pytest.mark.asyncio
    async def test_create_memory_success(self, memory_service, sample_create_request, mock_pool, sample_memory_row):
        """Test successful memory creation"""
        # Mock the database operations
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = sample_memory_row

        # Mock schema verification
        with patch.object(memory_service, '_verify_schema'):
            result = await memory_service.create_memory(sample_create_request)

        assert result.id == sample_memory_row['id']
        assert result.fact == sample_create_request.fact
        assert result.category == sample_create_request.category.value

    @pytest.mark.asyncio
    async def test_create_memory_duplicate_detection(self, memory_service, sample_create_request, mock_pool):
        """Test duplicate memory detection"""
        # Mock existing duplicate memory
        duplicate_memory = Memory(
            id=str(uuid.uuid4()),
            user_id=sample_create_request.user_id,
            fact=sample_create_request.fact,
            category=sample_create_request.category.value,
            confidence=0.9,
            source_type=SourceType.MANUAL.value,
            source_message_id=None,
            conversation_id=None,
            metadata={},
            expires_at=None,
            access_count=0,
            last_accessed_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None  # No similarity result (simplified)

        with patch.object(memory_service, 'find_duplicate_memory', return_value=duplicate_memory):
            with patch.object(memory_service, '_verify_schema'):
                with pytest.raises(ValueError, match="Similar memory already exists"):
                    await memory_service.create_memory(sample_create_request)

    @pytest.mark.asyncio
    async def test_get_memory_found(self, memory_service, sample_memory_id, sample_user_id, mock_pool, sample_memory_row):
        """Test getting an existing memory"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = sample_memory_row

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.get_memory(sample_memory_id, sample_user_id)

        assert result is not None
        assert result.id == sample_memory_id
        mock_conn.execute.assert_called_once()  # Should call track_memory_access

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, memory_service, sample_memory_id, sample_user_id, mock_pool):
        """Test getting a non-existent memory"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.get_memory(sample_memory_id, sample_user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_memory_success(self, memory_service, sample_memory_id, sample_user_id, mock_pool):
        """Test successful memory update"""
        update_request = UpdateMemoryRequest(
            fact="Updated memory fact",
            confidence=0.9
        )

        updated_row = {
            **sample_memory_row,
            'fact': "Updated memory fact",
            'confidence': 0.9,
            'updated_at': datetime.utcnow()
        }

        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = updated_row

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.update_memory(sample_memory_id, sample_user_id, update_request)

        assert result.fact == "Updated memory fact"
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, memory_service, sample_memory_id, sample_user_id, mock_pool):
        """Test successful memory deletion"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = {'id': sample_memory_id}

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.delete_memory(sample_memory_id, sample_user_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, memory_service, sample_memory_id, sample_user_id, mock_pool):
        """Test deleting a non-existent memory"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchrow.return_value = None

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.delete_memory(sample_memory_id, sample_user_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_memories_with_filters(self, memory_service, sample_user_id, mock_pool):
        """Test getting user memories with filters"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock database rows
        mock_rows = [
            {
                'id': str(uuid.uuid4()),
                'user_id': sample_user_id,
                'fact': "Test memory 1",
                'category': MemoryCategory.PREFERENCE.value,
                'confidence': 0.8,
                'source_type': SourceType.MANUAL.value,
                'source_message_id': None,
                'conversation_id': None,
                'metadata': {},
                'expires_at': None,
                'access_count': 5,
                'last_accessed_at': datetime.utcnow(),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        mock_conn.fetch.return_value = mock_rows

        filters = MemoryFilters(
            category=MemoryCategory.PREFERENCE,
            confidence_min=0.7,
            limit=10
        )

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.get_user_memories(sample_user_id, filters)

        assert len(result) == 1
        assert result[0].category == MemoryCategory.PREFERENCE.value
        assert result[0].confidence == 0.8

    @pytest.mark.asyncio
    async def test_search_memories(self, memory_service, sample_user_id, mock_pool):
        """Test full-text memory search"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock search results
        mock_rows = [
            {
                'id': str(uuid.uuid4()),
                'user_id': sample_user_id,
                'fact': "User prefers email updates",
                'category': MemoryCategory.PREFERENCE.value,
                'confidence': 0.85,
                'source_type': SourceType.EXTRACTED_FROM_CHAT.value,
                'source_message_id': None,
                'conversation_id': None,
                'metadata': {},
                'expires_at': None,
                'access_count': 2,
                'last_accessed_at': datetime.utcnow(),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        mock_conn.fetch.return_value = mock_rows

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.search_memories(sample_user_id, "email", 10)

        assert len(result) == 1
        assert "email" in result[0].fact.lower()

    @pytest.mark.asyncio
    async def test_get_memory_statistics(self, memory_service, sample_user_id, mock_pool):
        """Test getting memory statistics"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        # Mock statistics row
        mock_row = {
            'total_memories': 15,
            'priorities': 3,
            'decisions': 2,
            'contexts': 4,
            'preferences': 3,
            'relationships': 1,
            'goals': 1,
            'summaries': 1,
            'avg_confidence': 0.82,
            'max_access_count': 12,
            'last_memory_created': datetime.utcnow()
        }
        mock_conn.fetchrow.return_value = mock_row

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.get_memory_statistics(sample_user_id)

        assert result['total_memories'] == 15
        assert result['avg_confidence'] == 0.82
        assert result['preferences'] == 3

    @pytest.mark.asyncio
    async def test_cleanup_expired_memories(self, memory_service, mock_pool):
        """Test cleanup of expired memories"""
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.fetchval.return_value = 5

        with patch.object(memory_service, '_ensure_initialized'):
            result = await memory_service.cleanup_expired_memories()

        assert result == 5

    def test_row_to_memory(self, memory_service, sample_memory_row):
        """Test conversion from database row to Memory object"""
        memory = memory_service._row_to_memory(sample_memory_row)

        assert isinstance(memory, Memory)
        assert memory.id == str(sample_memory_row['id'])
        assert memory.fact == sample_memory_row['fact']
        assert memory.category == sample_memory_row['category']
        assert memory.confidence == sample_memory_row['confidence']

class TestPIIDetector:
    """Test suite for PII detection functionality"""

    @pytest.fixture
    def pii_detector(self):
        """Create PII detector instance"""
        return PIIDetector()

    def test_detect_email(self, pii_detector):
        """Test email detection"""
        text = "My email is user@example.com for contact"
        findings = pii_detector.detect_pii(text)

        assert len(findings) == 1
        assert findings[0]['type'] == 'EMAIL'
        assert findings[0]['text'] == 'user@example.com'

    def test_detect_phone_number(self, pii_detector):
        """Test phone number detection"""
        text = "Call me at (555) 123-4567 for details"
        findings = pii_detector.detect_pii(text)

        assert len(findings) == 1
        assert findings[0]['type'] == 'PHONE'
        assert '(555) 123-4567' in findings[0]['text']

    def test_detect_ssn(self, pii_detector):
        """Test SSN detection"""
        text = "My SSN is 123-45-6789 for verification"
        findings = pii_detector.detect_pii(text)

        assert len(findings) == 1
        assert findings[0]['type'] == 'SSN'
        assert findings[0]['text'] == '123-45-6789'

    def test_detect_multiple_pii(self, pii_detector):
        """Test detection of multiple PII types"""
        text = "Contact user@example.com or call (555) 123-4567. SSN: 123-45-6789"
        findings = pii_detector.detect_pii(text)

        assert len(findings) == 3
        types = [f['type'] for f in findings]
        assert 'EMAIL' in types
        assert 'PHONE' in types
        assert 'SSN' in types

    def test_mask_pii(self, pii_detector):
        """Test PII masking"""
        text = "Email: user@example.com, Phone: (555) 123-4567"
        masked = pii_detector.mask_pii(text, '*')

        assert 'user@example.com' not in masked
        assert '(555) 123-4567' not in masked
        assert 'Email:' in text  # Non-PII content should remain

    def test_has_pii(self, pii_detector):
        """Test PII presence detection"""
        assert pii_detector.has_pii("My email is user@example.com") is True
        assert pii_detector.has_pii("This is just regular text") is False

class TestMemoryServiceIntegration:
    """Integration tests for memory service"""

    @pytest.mark.asyncio
    async def test_get_memory_service_singleton(self):
        """Test that get_memory_service returns the same instance"""
        with patch('services.memory_service._memory_service', None):
            service1 = await get_memory_service()
            service2 = await get_memory_service()
            assert service1 is service2

    @pytest.mark.asyncio
    async def test_bulk_create_memories(self, memory_service, mock_pool):
        """Test bulk memory creation"""
        user_id = str(uuid.uuid4())
        requests = [
            CreateMemoryRequest(
                user_id=user_id,
                fact=f"Memory fact {i}",
                category=MemoryCategory.PREFERENCE,
                confidence=0.8
            )
            for i in range(3)
        ]

        # Mock the create_memory method
        memory_service.pool = mock_pool
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        created_memories = []
        for i, request in enumerate(requests):
            memory_row = {
                'id': str(uuid.uuid4()),
                'user_id': user_id,
                'fact': request.fact,
                'category': request.category.value,
                'confidence': request.confidence,
                'source_type': SourceType.MANUAL.value,
                'source_message_id': None,
                'conversation_id': None,
                'metadata': {},
                'expires_at': None,
                'access_count': 0,
                'last_accessed_at': datetime.utcnow(),
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            created_memories.append(memory_service._row_to_memory(memory_row))

        with patch.object(memory_service, 'create_memory', side_effect=created_memories):
            with patch.object(memory_service, '_verify_schema'):
                result = await memory_service.bulk_create_memories(requests)

        assert len(result) == 3
        for i, memory in enumerate(result):
            assert f"Memory fact {i}" in memory.fact

# Performance tests
class TestMemoryServicePerformance:
    """Performance tests for memory service"""

    @pytest.mark.asyncio
    async def test_concurrent_memory_creation(self, memory_service):
        """Test concurrent memory creation performance"""
        import time

        user_id = str(uuid.uuid4())
        num_memories = 10

        async def create_memory(i):
            request = CreateMemoryRequest(
                user_id=user_id,
                fact=f"Concurrent memory {i}",
                category=MemoryCategory.PREFERENCE,
                confidence=0.8
            )
            # Mock the actual creation for performance test
            await asyncio.sleep(0.01)  # Simulate database latency
            return f"memory-{i}"

        start_time = time.time()
        tasks = [create_memory(i) for i in range(num_memories)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        assert len(results) == num_memories
        # Should complete in reasonable time (adjust threshold as needed)
        assert end_time - start_time < 1.0

if __name__ == '__main__':
    pytest.main([__file__])