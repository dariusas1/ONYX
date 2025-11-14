#!/usr/bin/env python3
"""
Qdrant Collection Initialization Script

This script initializes the 'documents' collection in Qdrant with the correct configuration.
It is idempotent and safe to run multiple times.

Usage:
    python scripts/init-qdrant.py

Environment Variables:
    QDRANT_URL: Qdrant service URL (default: http://localhost:6333)
    QDRANT_API_KEY: Optional API key for Qdrant authentication
"""

import os
import sys
import logging
from typing import Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, OptimizersConfigDiff
except ImportError:
    print("Error: qdrant-client not installed. Run: pip install qdrant-client")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "documents"
VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small dimension
DISTANCE_METRIC = Distance.COSINE


def get_qdrant_client() -> QdrantClient:
    """Initialize and return Qdrant client"""
    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=10.0
        )
        logger.info(f"Connected to Qdrant at {QDRANT_URL}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    """Check if a collection exists"""
    try:
        collections = client.get_collections().collections
        return collection_name in [c.name for c in collections]
    except Exception as e:
        logger.error(f"Failed to check if collection exists: {e}")
        raise


def create_documents_collection(client: QdrantClient) -> None:
    """
    Create the documents collection with the correct configuration.
    This function is idempotent - safe to run multiple times.
    """
    try:
        if collection_exists(client, COLLECTION_NAME):
            logger.info(f"Collection '{COLLECTION_NAME}' already exists - skipping creation")

            # Verify collection configuration
            collection_info = client.get_collection(COLLECTION_NAME)
            vector_size = collection_info.config.params.vectors.size
            distance = collection_info.config.params.vectors.distance

            logger.info(f"  Vector size: {vector_size} dimensions")
            logger.info(f"  Distance metric: {distance}")

            if vector_size != VECTOR_SIZE:
                logger.warning(
                    f"  WARNING: Collection has {vector_size} dimensions but expected {VECTOR_SIZE}. "
                    f"This may cause issues with embeddings."
                )

            return

        # Create collection with optimized configuration
        logger.info(f"Creating collection '{COLLECTION_NAME}'...")

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=DISTANCE_METRIC,
                on_disk=True  # Enable on-disk storage for large corpus support
            ),
            optimizers_config=OptimizersConfigDiff(
                default_segment_number=2,  # Balance between indexing speed and search performance
                indexing_threshold=20000   # Rebuild index after this many updates
            )
        )

        logger.info(f"Successfully created collection '{COLLECTION_NAME}'")
        logger.info(f"  Vector size: {VECTOR_SIZE} dimensions (OpenAI text-embedding-3-small)")
        logger.info(f"  Distance metric: {DISTANCE_METRIC}")
        logger.info(f"  On-disk storage: Enabled")
        logger.info(f"  Optimizer config: 2 segments, 20000 indexing threshold")

    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise


def verify_collection_health(client: QdrantClient) -> None:
    """Verify the collection is healthy and ready for use"""
    try:
        collection_info = client.get_collection(COLLECTION_NAME)

        logger.info("\nCollection Health Check:")
        logger.info(f"  Status: OK")
        logger.info(f"  Points count: {collection_info.points_count}")
        logger.info(f"  Segments count: {collection_info.segments_count}")
        logger.info(f"  Indexed vectors: {collection_info.indexed_vectors_count}")

    except Exception as e:
        logger.error(f"Collection health check failed: {e}")
        raise


def main():
    """Main initialization function"""
    try:
        logger.info("=" * 60)
        logger.info("Qdrant Collection Initialization")
        logger.info("=" * 60)

        # Initialize Qdrant client
        client = get_qdrant_client()

        # Create collection (idempotent)
        create_documents_collection(client)

        # Verify collection health
        verify_collection_health(client)

        logger.info("\n" + "=" * 60)
        logger.info("Initialization completed successfully!")
        logger.info("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"\nInitialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
