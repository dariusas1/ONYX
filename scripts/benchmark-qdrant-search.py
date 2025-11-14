#!/usr/bin/env python3
"""
Qdrant Performance Benchmark Script

Measures search latency and throughput for the Qdrant vector database.
Tests various scenarios to ensure performance meets requirements.

Requirements (AC3.1.3):
- Search query (top-10 results) completes in <100ms (95th percentile)
- All upserts complete successfully
- API responds correctly for all CRUD operations

Usage:
    python scripts/benchmark-qdrant-search.py

Environment Variables:
    QDRANT_URL: Qdrant service URL (default: http://localhost:6333)
    QDRANT_API_KEY: Optional API key for Qdrant authentication
"""

import os
import sys
import time
import logging
import statistics
from typing import List, Dict, Any
import uuid

try:
    import numpy as np
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
except ImportError as e:
    print(f"Error: Missing required package. Run: pip install qdrant-client numpy")
    print(f"Import error: {e}")
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
VECTOR_SIZE = 1536  # OpenAI text-embedding-3-small

# Benchmark parameters
NUM_VECTORS_TO_INSERT = 1000
NUM_SEARCH_QUERIES = 100
TOP_K = 10
LATENCY_TARGET_MS = 100  # 95th percentile


class BenchmarkResults:
    """Container for benchmark results"""

    def __init__(self):
        self.upsert_times: List[float] = []
        self.search_times: List[float] = []
        self.errors: List[str] = []

    def add_upsert_time(self, time_ms: float):
        """Add an upsert time measurement"""
        self.upsert_times.append(time_ms)

    def add_search_time(self, time_ms: float):
        """Add a search time measurement"""
        self.search_times.append(time_ms)

    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)

    def calculate_percentiles(self, times: List[float]) -> Dict[str, float]:
        """Calculate percentiles for a list of times"""
        if not times:
            return {}

        return {
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "p50": np.percentile(times, 50),
            "p90": np.percentile(times, 90),
            "p95": np.percentile(times, 95),
            "p99": np.percentile(times, 99),
        }

    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        if self.upsert_times:
            upsert_stats = self.calculate_percentiles(self.upsert_times)
            print(f"\nUpsert Performance ({len(self.upsert_times)} operations):")
            print(f"  Min:    {upsert_stats['min']:.2f} ms")
            print(f"  Mean:   {upsert_stats['mean']:.2f} ms")
            print(f"  Median: {upsert_stats['median']:.2f} ms")
            print(f"  P95:    {upsert_stats['p95']:.2f} ms")
            print(f"  Max:    {upsert_stats['max']:.2f} ms")

        if self.search_times:
            search_stats = self.calculate_percentiles(self.search_times)
            print(f"\nSearch Performance ({len(self.search_times)} queries, top-{TOP_K} results):")
            print(f"  Min:    {search_stats['min']:.2f} ms")
            print(f"  Mean:   {search_stats['mean']:.2f} ms")
            print(f"  Median: {search_stats['median']:.2f} ms")
            print(f"  P90:    {search_stats['p90']:.2f} ms")
            print(f"  P95:    {search_stats['p95']:.2f} ms")
            print(f"  P99:    {search_stats['p99']:.2f} ms")
            print(f"  Max:    {search_stats['max']:.2f} ms")

            # Check if meets requirements
            p95_latency = search_stats['p95']
            if p95_latency < LATENCY_TARGET_MS:
                print(f"\n✅ PASS: P95 latency ({p95_latency:.2f} ms) is under target ({LATENCY_TARGET_MS} ms)")
            else:
                print(f"\n❌ FAIL: P95 latency ({p95_latency:.2f} ms) exceeds target ({LATENCY_TARGET_MS} ms)")

        if self.errors:
            print(f"\nErrors encountered: {len(self.errors)}")
            for i, error in enumerate(self.errors[:5], 1):  # Show first 5 errors
                print(f"  {i}. {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")

        print("\n" + "=" * 80)


def get_qdrant_client() -> QdrantClient:
    """Initialize and return Qdrant client"""
    try:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            timeout=30.0
        )
        logger.info(f"Connected to Qdrant at {QDRANT_URL}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise


def generate_random_vector() -> List[float]:
    """Generate a random vector for testing"""
    return np.random.rand(VECTOR_SIZE).tolist()


def create_test_payload(index: int) -> Dict[str, Any]:
    """Create a test payload for a document"""
    return {
        "doc_id": f"benchmark-doc-{index}",
        "title": f"Benchmark Document {index}",
        "text": f"This is a test document for performance benchmarking. Document number: {index}",
        "source": "benchmark",
        "source_type": "test",
        "chunk_index": index,
        "metadata": {
            "benchmark_run": True,
            "timestamp": time.time(),
        }
    }


def benchmark_upsert(client: QdrantClient, results: BenchmarkResults, num_vectors: int):
    """Benchmark vector upsert operations"""
    logger.info(f"Benchmarking upsert of {num_vectors} vectors...")

    # Prepare points in batches
    batch_size = 100
    total_batches = (num_vectors + batch_size - 1) // batch_size

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, num_vectors)
        batch_points = []

        for i in range(start_idx, end_idx):
            point = PointStruct(
                id=f"benchmark-{uuid.uuid4()}",
                vector=generate_random_vector(),
                payload=create_test_payload(i)
            )
            batch_points.append(point)

        # Measure upsert time
        try:
            start_time = time.time()
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch_points
            )
            elapsed_ms = (time.time() - start_time) * 1000
            results.add_upsert_time(elapsed_ms)

            if (batch_num + 1) % 5 == 0:
                logger.info(f"  Upserted batch {batch_num + 1}/{total_batches} ({end_idx}/{num_vectors} vectors)")

        except Exception as e:
            error_msg = f"Upsert batch {batch_num} failed: {e}"
            logger.error(error_msg)
            results.add_error(error_msg)

    logger.info(f"Upsert benchmark completed: {len(results.upsert_times)} batches")


def benchmark_search(client: QdrantClient, results: BenchmarkResults, num_queries: int):
    """Benchmark vector search operations"""
    logger.info(f"Benchmarking {num_queries} search queries (top-{TOP_K} results)...")

    for i in range(num_queries):
        query_vector = generate_random_vector()

        try:
            start_time = time.time()
            search_results = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                limit=TOP_K
            )
            elapsed_ms = (time.time() - start_time) * 1000
            results.add_search_time(elapsed_ms)

            if (i + 1) % 20 == 0:
                logger.info(f"  Completed {i + 1}/{num_queries} search queries")

        except Exception as e:
            error_msg = f"Search query {i} failed: {e}"
            logger.error(error_msg)
            results.add_error(error_msg)

    logger.info(f"Search benchmark completed: {len(results.search_times)} queries")


def verify_collection_exists(client: QdrantClient) -> bool:
    """Verify that the documents collection exists"""
    try:
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME in collection_names:
            logger.info(f"Collection '{COLLECTION_NAME}' exists")
            return True
        else:
            logger.error(f"Collection '{COLLECTION_NAME}' not found")
            return False

    except Exception as e:
        logger.error(f"Failed to verify collection: {e}")
        return False


def get_collection_stats(client: QdrantClient):
    """Get and display collection statistics"""
    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        logger.info(f"\nCollection Statistics:")
        logger.info(f"  Points count: {collection_info.points_count}")
        logger.info(f"  Segments count: {collection_info.segments_count}")
        logger.info(f"  Indexed vectors: {collection_info.indexed_vectors_count}")
        logger.info(f"  Vector size: {collection_info.config.params.vectors.size}")
        logger.info(f"  Distance metric: {collection_info.config.params.vectors.distance}")

    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")


def cleanup_benchmark_data(client: QdrantClient):
    """Clean up benchmark test data by deleting points with benchmark source"""
    logger.info("Cleaning up benchmark data...")

    try:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # Delete all points with source="benchmark"
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value="benchmark")
                    )
                ]
            )
        )
        logger.info("Successfully cleaned up benchmark data")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def main():
    """Main benchmark execution"""
    print("=" * 80)
    print("Qdrant Performance Benchmark")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Qdrant URL: {QDRANT_URL}")
    print(f"  Collection: {COLLECTION_NAME}")
    print(f"  Vector size: {VECTOR_SIZE} dimensions")
    print(f"  Vectors to insert: {NUM_VECTORS_TO_INSERT}")
    print(f"  Search queries: {NUM_SEARCH_QUERIES}")
    print(f"  Top-K results: {TOP_K}")
    print(f"  P95 latency target: {LATENCY_TARGET_MS} ms")
    print("")

    try:
        # Initialize client
        client = get_qdrant_client()

        # Verify collection exists
        if not verify_collection_exists(client):
            logger.error("Collection not found. Run 'python scripts/init-qdrant.py' first.")
            return 1

        # Get initial collection stats
        get_collection_stats(client)

        # Initialize results
        results = BenchmarkResults()

        # Run benchmarks
        print("\n" + "-" * 80)
        benchmark_upsert(client, results, NUM_VECTORS_TO_INSERT)

        print("\n" + "-" * 80)
        benchmark_search(client, results, NUM_SEARCH_QUERIES)

        # Get final collection stats
        print("\n" + "-" * 80)
        get_collection_stats(client)

        # Print summary
        results.print_summary()

        # Determine exit code
        if results.search_times:
            p95_latency = np.percentile(results.search_times, 95)
            if p95_latency >= LATENCY_TARGET_MS:
                logger.warning(f"Performance target not met (P95: {p95_latency:.2f} ms)")
                return 1

        if results.errors:
            logger.warning(f"Benchmark completed with {len(results.errors)} errors")
            return 1

        logger.info("Benchmark completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
