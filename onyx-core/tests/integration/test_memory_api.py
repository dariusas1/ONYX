"""
Integration tests for Memory API endpoints

This test suite tests the full API endpoints including request validation,
response formatting, and error handling.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from services.memory_service import MemoryCategory, SourceType, Memory

class TestMemoryAPI:
    """Integration tests for memory API endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def sample_user_token(self):
        """Sample authentication token for testing"""
        # This would normally be a valid JWT token
        return "Bearer valid_token_here"

    @pytest.fixture
    def auth_headers(self, sample_user_token):
        """Authentication headers for requests"""
        return {"Authorization": sample_user_token}

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_memory_id(self):
        """Sample memory ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_memory_data(self, sample_memory_id, sample_user_id):
        """Sample memory data for API responses"""
        return {
            "id": sample_memory_id,
            "user_id": sample_user_id,
            "fact": "I prefer to receive updates via email rather than chat notifications",
            "category": MemoryCategory.PREFERENCE.value,
            "confidence": 0.85,
            "source_type": SourceType.MANUAL.value,
            "source_message_id": None,
            "conversation_id": None,
            "metadata": {},
            "expires_at": None,
            "access_count": 0,
            "last_accessed_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

    def test_get_memory_categories(self, client):
        """Test getting memory categories endpoint"""
        response = client.get("/api/memories/categories/list")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]) == 7  # 7 standard categories

        categories = data["data"]
        category_values = [cat["value"] for cat in categories]
        assert MemoryCategory.PRIORITY.value in category_values
        assert MemoryCategory.PREFERENCE.value in category_values

    def test_memory_health_check(self, client):
        """Test memory service health check"""
        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.pool = True  # Simulate healthy service
            mock_get_service.return_value = mock_service

            response = client.get("/api/memories/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["status"] == "healthy"

    @patch('api.memories.require_authenticated_user')
    def test_get_memories_success(self, mock_auth, client, auth_headers, sample_memory_data):
        """Test successful memory retrieval"""
        # Mock authentication
        mock_auth.return_value = {"id": sample_memory_data["user_id"]}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_memories.return_value = [Memory(**sample_memory_data)]
            mock_get_service.return_value = mock_service

            response = client.get("/api/memories/", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "memories" in data["data"]
            assert len(data["data"]["memories"]) == 1

    @patch('api.memories.require_authenticated_user')
    def test_get_memories_with_filters(self, mock_auth, client, auth_headers, sample_user_id):
        """Test memory retrieval with filters"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_memories.return_value = []
            mock_get_service.return_value = mock_service

            response = client.get(
                "/api/memories/?category=preference&confidence_min=0.7&limit=10",
                headers=auth_headers
            )

            assert response.status_code == 200
            mock_service.get_user_memories.assert_called_once()

            # Check that filters were passed correctly
            call_args = mock_service.get_user_memories.call_args
            filters = call_args[0][1]  # Second argument
            assert filters.category == MemoryCategory.PREFERENCE
            assert filters.confidence_min == 0.7
            assert filters.limit == 10

    @patch('api.memories.require_authenticated_user')
    def test_get_memory_by_id_success(self, mock_auth, client, auth_headers, sample_memory_data):
        """Test getting a specific memory by ID"""
        mock_auth.return_value = {"id": sample_memory_data["user_id"]}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_memory.return_value = Memory(**sample_memory_data)
            mock_get_service.return_value = mock_service

            memory_id = sample_memory_data["id"]
            response = client.get(f"/api/memories/{memory_id}", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["id"] == memory_id

    @patch('api.memories.require_authenticated_user')
    def test_get_memory_by_id_not_found(self, mock_auth, client, auth_headers, sample_user_id):
        """Test getting a non-existent memory"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_memory.return_value = None
            mock_get_service.return_value = mock_service

            memory_id = str(uuid.uuid4())
            response = client.get(f"/api/memories/{memory_id}", headers=auth_headers)

            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False

    def test_get_memory_invalid_id(self, client, auth_headers):
        """Test getting memory with invalid ID format"""
        response = client.get("/api/memories/invalid-id", headers=auth_headers)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "Invalid memory ID format" in data["error"]["message"]

    @patch('api.memories.require_authenticated_user')
    def test_create_memory_success(self, mock_auth, client, auth_headers, sample_memory_data, sample_user_id):
        """Test successful memory creation"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_memory.return_value = Memory(**sample_memory_data)
            mock_get_service.return_value = mock_service

            create_data = {
                "fact": "I prefer to receive updates via email rather than chat notifications",
                "category": MemoryCategory.PREFERENCE.value,
                "confidence": 0.85,
                "source_type": SourceType.MANUAL.value
            }

            response = client.post("/api/memories/", json=create_data, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["fact"] == create_data["fact"]
            assert data["data"]["category"] == create_data["category"]

    @patch('api.memories.require_authenticated_user')
    def test_create_memory_validation_error(self, mock_auth, client, auth_headers, sample_user_id):
        """Test memory creation with invalid data"""
        mock_auth.return_value = {"id": sample_user_id}

        create_data = {
            "fact": "",  # Empty fact should fail validation
            "category": MemoryCategory.PREFERENCE.value,
            "confidence": 0.85
        }

        response = client.post("/api/memories/", json=create_data, headers=auth_headers)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_create_memory_missing_auth(self, client):
        """Test memory creation without authentication"""
        create_data = {
            "fact": "Test memory",
            "category": MemoryCategory.PREFERENCE.value,
            "confidence": 0.8
        }

        response = client.post("/api/memories/", json=create_data)

        assert response.status_code == 401  # Unauthorized

    @patch('api.memories.require_authenticated_user')
    def test_create_memory_duplicate_error(self, mock_auth, client, auth_headers, sample_user_id):
        """Test memory creation with duplicate content"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.create_memory.side_effect = ValueError("Similar memory already exists")
            mock_get_service.return_value = mock_service

            create_data = {
                "fact": "I prefer email updates",
                "category": MemoryCategory.PREFERENCE.value,
                "confidence": 0.8
            }

            response = client.post("/api/memories/", json=create_data, headers=auth_headers)

            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "Similar memory already exists" in data["error"]["message"]

    @patch('api.memories.require_authenticated_user')
    def test_update_memory_success(self, mock_auth, client, auth_headers, sample_memory_data, sample_user_id):
        """Test successful memory update"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()

            # Return updated memory
            updated_memory_data = sample_memory_data.copy()
            updated_memory_data["fact"] = "Updated memory fact"
            updated_memory_data["confidence"] = 0.9

            mock_service.update_memory.return_value = Memory(**updated_memory_data)
            mock_get_service.return_value = mock_service

            update_data = {
                "fact": "Updated memory fact",
                "confidence": 0.9
            }

            memory_id = sample_memory_data["id"]
            response = client.put(f"/api/memories/{memory_id}", json=update_data, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["fact"] == "Updated memory fact"
            assert data["data"]["confidence"] == 0.9

    @patch('api.memories.require_authenticated_user')
    def test_update_memory_not_found(self, mock_auth, client, auth_headers, sample_user_id):
        """Test updating a non-existent memory"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.update_memory.side_effect = ValueError("Memory not found or cannot be updated")
            mock_get_service.return_value = mock_service

            update_data = {
                "fact": "Updated memory fact"
            }

            memory_id = str(uuid.uuid4())
            response = client.put(f"/api/memories/{memory_id}", json=update_data, headers=auth_headers)

            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False

    @patch('api.memories.require_authenticated_user')
    def test_delete_memory_success(self, mock_auth, client, auth_headers, sample_memory_data, sample_user_id):
        """Test successful memory deletion"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_memory.return_value = True
            mock_get_service.return_value = mock_service

            memory_id = sample_memory_data["id"]
            response = client.delete(f"/api/memories/{memory_id}", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["deleted"] is True

    @patch('api.memories.require_authenticated_user')
    def test_delete_memory_not_found(self, mock_auth, client, auth_headers, sample_user_id):
        """Test deleting a non-existent memory"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.delete_memory.return_value = False
            mock_get_service.return_value = mock_service

            memory_id = str(uuid.uuid4())
            response = client.delete(f"/api/memories/{memory_id}", headers=auth_headers)

            assert response.status_code == 404
            data = response.json()
            assert data["success"] is False

    @patch('api.memories.require_authenticated_user')
    def test_search_memories_success(self, mock_auth, client, auth_headers, sample_memory_data, sample_user_id):
        """Test successful memory search"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search_memories.return_value = [Memory(**sample_memory_data)]
            mock_get_service.return_value = mock_service

            query = "email"
            response = client.get(f"/api/memories/search/{query}", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["query"] == query
            assert len(data["data"]["memories"]) == 1

    @patch('api.memories.require_authenticated_user')
    def test_search_memories_empty_query(self, mock_auth, client, auth_headers, sample_user_id):
        """Test memory search with empty query"""
        mock_auth.return_value = {"id": sample_user_id}

        response = client.get("/api/memories/search/", headers=auth_headers)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    @patch('api.memories.require_authenticated_user')
    def test_get_memory_statistics(self, mock_auth, client, auth_headers, sample_user_id):
        """Test getting memory statistics"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_memory_statistics.return_value = {
                "total_memories": 15,
                "preferences": 5,
                "decisions": 3,
                "avg_confidence": 0.82
            }
            mock_get_service.return_value = mock_service

            response = client.get("/api/memories/statistics/summary", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_memories"] == 15
            assert data["data"]["preferences"] == 5

    @patch('api.memories.require_authenticated_user')
    def test_bulk_create_memories_success(self, mock_auth, client, auth_headers, sample_user_id):
        """Test successful bulk memory creation"""
        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()

            # Mock created memories
            created_memories = []
            for i in range(3):
                memory_data = {
                    "id": str(uuid.uuid4()),
                    "user_id": sample_user_id,
                    "fact": f"Bulk memory {i}",
                    "category": MemoryCategory.PREFERENCE.value,
                    "confidence": 0.8,
                    "source_type": SourceType.MANUAL.value,
                    "source_message_id": None,
                    "conversation_id": None,
                    "metadata": {},
                    "expires_at": None,
                    "access_count": 0,
                    "last_accessed_at": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                created_memories.append(Memory(**memory_data))

            mock_service.bulk_create_memories.return_value = created_memories
            mock_get_service.return_value = mock_service

            bulk_data = [
                {
                    "fact": f"Bulk memory {i}",
                    "category": MemoryCategory.PREFERENCE.value,
                    "confidence": 0.8
                }
                for i in range(3)
            ]

            response = client.post("/api/memories/bulk", json=bulk_data, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["created"] == 3
            assert data["data"]["requested"] == 3
            assert len(data["data"]["memories"]) == 3

    @patch('api.memories.require_authenticated_user')
    def test_bulk_create_memories_too_many(self, mock_auth, client, auth_headers, sample_user_id):
        """Test bulk memory creation with too many memories"""
        mock_auth.return_value = {"id": sample_user_id}

        # Create 60 memories (exceeds limit of 50)
        bulk_data = [
            {
                "fact": f"Bulk memory {i}",
                "category": MemoryCategory.PREFERENCE.value,
                "confidence": 0.8
            }
            for i in range(60)
        ]

        response = client.post("/api/memories/bulk", json=bulk_data, headers=auth_headers)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "Maximum 50 memories" in data["error"]["message"]

    def test_bulk_create_memories_empty(self, client, auth_headers):
        """Test bulk memory creation with empty list"""
        response = client.post("/api/memories/bulk", json=[], headers=auth_headers)

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "No memories provided" in data["error"]["message"]

    def test_error_handling_invalid_json(self, client, auth_headers):
        """Test error handling for invalid JSON"""
        response = client.post(
            "/api/memories/",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )

        assert response.status_code == 422  # Validation error

    @patch('api.memories.require_authenticated_user')
    def test_cleanup_expired_memories_admin_only(self, mock_auth, client, auth_headers, sample_user_id):
        """Test cleanup endpoint requires admin access"""
        # Mock non-admin user
        mock_auth.return_value = {"id": sample_user_id, "is_admin": False}

        response = client.post("/api/memories/cleanup/expired", headers=auth_headers)

        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False
        assert "Admin access required" in data["error"]["message"]

class TestMemoryAPIPerformance:
    """Performance tests for memory API endpoints"""

    @patch('api.memories.require_authenticated_user')
    def test_api_response_time(self, mock_auth, client, auth_headers, sample_user_id):
        """Test API response time is within acceptable limits"""
        import time

        mock_auth.return_value = {"id": sample_user_id}

        with patch('api.memories.get_memory_service') as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_memories.return_value = []
            mock_get_service.return_value = mock_service

            start_time = time.time()
            response = client.get("/api/memories/", headers=auth_headers)
            end_time = time.time()

            assert response.status_code == 200
            # Should respond within 1 second (adjust threshold as needed)
            assert end_time - start_time < 1.0

if __name__ == '__main__':
    pytest.main([__file__])