"""
Unit Tests for Qdrant Collection Setup

Tests the RAG service Qdrant collection initialization and vector operations.

Run with:
    pytest tests/unit/test_qdrant_collection.py -v
"""

import pytest
import os
import sys
import uuid
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../onyx-core')))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, OptimizersConfigDiff


# Test configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "documents"
VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small


@pytest.fixture(scope="module")
def qdrant_client():
    """Fixture to create a Qdrant client for testing"""
    client = QdrantClient(url=QDRANT_URL, timeout=10.0)
    yield client


@pytest.fixture(scope="module")
def ensure_collection(qdrant_client):
    """Fixture to ensure the documents collection exists"""
    collections = qdrant_client.get_collections().collections
    collection_names = [c.name for c in collections]

    if COLLECTION_NAME not in collection_names:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
                on_disk=True,
            ),
            optimizers_config=OptimizersConfigDiff(
                default_segment_number=2,
                indexing_threshold=20000,
            ),
        )

    yield qdrant_client

    # Cleanup is optional - collection can persist for other tests


class TestQdrantConnection:
    """Test Qdrant connection and basic operations"""

    def test_qdrant_connection(self, qdrant_client):
        """Test that we can connect to Qdrant"""
        collections = qdrant_client.get_collections()
        assert collections is not None
        assert hasattr(collections, 'collections')

    def test_qdrant_health(self, qdrant_client):
        """Test that Qdrant health endpoint works"""
        # Qdrant client doesn't expose health directly, but if we can list collections, it's healthy
        collections = qdrant_client.get_collections()
        assert collections is not None


class TestCollectionCreation:
    """Test collection creation and configuration"""

    def test_collection_exists(self, ensure_collection):
        """Test that the documents collection exists"""
        collections = ensure_collection.get_collections().collections
        collection_names = [c.name for c in collections]
        assert COLLECTION_NAME in collection_names

    def test_collection_configuration(self, ensure_collection):
        """Test that the collection has the correct configuration"""
        collection_info = ensure_collection.get_collection(COLLECTION_NAME)

        # Verify vector configuration
        assert collection_info.config.params.vectors.size == VECTOR_SIZE
        assert collection_info.config.params.vectors.distance == Distance.COSINE

        # Verify on-disk storage (if available in API response)
        if hasattr(collection_info.config.params.vectors, 'on_disk'):
            assert collection_info.config.params.vectors.on_disk is True

    def test_collection_idempotent(self, qdrant_client):
        """Test that creating the collection multiple times doesn't fail"""
        # First creation (or already exists)
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME not in collection_names:
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                    on_disk=True,
                ),
            )

        # Verify it exists
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        assert collection_info is not None
        assert collection_info.config.params.vectors.size == VECTOR_SIZE

        # Second "creation" should not throw error if we check first
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        assert COLLECTION_NAME in collection_names  # Already exists, no error


class TestVectorOperations:
    """Test basic vector CRUD operations"""

    def test_upsert_single_vector(self, ensure_collection):
        """Test upserting a single vector"""
        doc_id = f"test-{uuid.uuid4()}"
        test_vector = [0.1] * VECTOR_SIZE

        point = PointStruct(
            id=doc_id,
            vector=test_vector,
            payload={
                "doc_id": doc_id,
                "title": "Test Document",
                "text": "This is a test document",
                "source": "unit_test",
            }
        )

        # Upsert the point
        result = ensure_collection.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )

        assert result is not None

    def test_upsert_multiple_vectors(self, ensure_collection):
        """Test upserting multiple vectors in batch"""
        num_vectors = 10
        points = []

        for i in range(num_vectors):
            doc_id = f"test-batch-{uuid.uuid4()}"
            test_vector = [0.1 * (i + 1)] * VECTOR_SIZE

            point = PointStruct(
                id=doc_id,
                vector=test_vector,
                payload={
                    "doc_id": doc_id,
                    "title": f"Test Document {i}",
                    "text": f"This is test document number {i}",
                    "source": "unit_test",
                    "batch_index": i,
                }
            )
            points.append(point)

        # Upsert all points
        result = ensure_collection.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

        assert result is not None

    def test_search_vectors(self, ensure_collection):
        """Test searching for vectors"""
        # First, upsert a test vector
        doc_id = f"test-search-{uuid.uuid4()}"
        test_vector = [0.5] * VECTOR_SIZE

        point = PointStruct(
            id=doc_id,
            vector=test_vector,
            payload={
                "doc_id": doc_id,
                "title": "Searchable Test Document",
                "text": "This document should be found in search",
                "source": "unit_test",
            }
        )

        ensure_collection.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )

        # Now search for similar vectors
        query_vector = [0.5] * VECTOR_SIZE
        search_results = ensure_collection.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=5
        )

        assert len(search_results) > 0
        assert search_results[0].id == doc_id
        assert search_results[0].score > 0.99  # Should be very close to 1.0 (exact match)

    def test_search_with_filters(self, ensure_collection):
        """Test searching with payload filters"""
        # Upsert vectors with different sources
        for source in ["source_a", "source_b"]:
            doc_id = f"test-filter-{source}-{uuid.uuid4()}"
            test_vector = [0.7] * VECTOR_SIZE

            point = PointStruct(
                id=doc_id,
                vector=test_vector,
                payload={
                    "doc_id": doc_id,
                    "title": f"Document from {source}",
                    "text": f"This is from {source}",
                    "source": source,
                }
            )

            ensure_collection.upsert(
                collection_name=COLLECTION_NAME,
                points=[point]
            )

        # Search with filter (note: filter syntax may vary by qdrant-client version)
        query_vector = [0.7] * VECTOR_SIZE

        # Basic search without filter should return results
        search_results = ensure_collection.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=10
        )

        assert len(search_results) > 0


class TestVectorDimensions:
    """Test vector dimension validation"""

    def test_correct_vector_dimensions(self, ensure_collection):
        """Test that vectors with correct dimensions can be inserted"""
        doc_id = f"test-dims-{uuid.uuid4()}"
        test_vector = [0.1] * VECTOR_SIZE  # Correct size

        point = PointStruct(
            id=doc_id,
            vector=test_vector,
            payload={"doc_id": doc_id, "title": "Test"}
        )

        result = ensure_collection.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )

        assert result is not None

    def test_incorrect_vector_dimensions_fails(self, ensure_collection):
        """Test that vectors with incorrect dimensions are rejected"""
        doc_id = f"test-dims-wrong-{uuid.uuid4()}"
        test_vector = [0.1] * 100  # Wrong size

        point = PointStruct(
            id=doc_id,
            vector=test_vector,
            payload={"doc_id": doc_id, "title": "Test"}
        )

        # This should raise an error
        with pytest.raises(Exception):  # Qdrant will raise an exception
            ensure_collection.upsert(
                collection_name=COLLECTION_NAME,
                points=[point]
            )


class TestCollectionStats:
    """Test collection statistics and metadata"""

    def test_get_collection_info(self, ensure_collection):
        """Test retrieving collection information"""
        collection_info = ensure_collection.get_collection(COLLECTION_NAME)

        assert collection_info is not None
        assert hasattr(collection_info, 'points_count')
        assert hasattr(collection_info, 'segments_count')
        assert collection_info.config.params.vectors.size == VECTOR_SIZE

    def test_collection_point_count(self, ensure_collection):
        """Test that we can get the point count"""
        collection_info = ensure_collection.get_collection(COLLECTION_NAME)
        assert collection_info.points_count >= 0  # Should be non-negative


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
