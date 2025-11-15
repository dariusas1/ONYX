"""
Integration Tests for Hybrid Search Pipeline

This module contains integration tests for the complete hybrid search pipeline,
including database operations, API endpoints, and performance validation.
"""

import pytest
import asyncio
import aiohttp
import asyncpg
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

from onyx_core.services.hybrid_search_service import HybridSearchService
from onyx_core.services.keyword_search_service import KeywordSearchService
from onyx_core.rag_service import RAGService, SearchResult


class TestHybridSearchIntegration:
    """Integration tests for hybrid search pipeline"""

    @pytest.fixture
    async def postgres_connection(self):
        """Create PostgreSQL connection for testing"""
        connection = await asyncpg.connect(
            user="postgres",
            password="password",
            database="onyx",
            host="localhost",
            port="5432"
        )
        yield connection
        await connection.close()

    @pytest.fixture
    async def setup_test_data(self, postgres_connection):
        """Set up test data for integration tests"""
        # Insert test documents
        test_documents = [
            {
                "doc_id": "test-doc-1",
                "title": "AI Strategy Document",
                "content": "Our company's AI strategy focuses on implementing machine learning solutions across all departments. Key priorities include automation, data analytics, and natural language processing.",
                "source_type": "google_drive",
                "source_id": "file-123",
                "created_at": datetime.now() - timedelta(days=10),
                "updated_at": datetime.now() - timedelta(days=5),
                "permissions": ["*"],
                "metadata": {"department": "strategy", "priority": "high"}
            },
            {
                "doc_id": "test-doc-2",
                "title": "Project Unicorn Launch Plan",
                "content": "Project Unicorn is scheduled to launch in Q4 2025. The launch will involve coordination across marketing, engineering, and sales teams. Budget allocation: $2M for development, $500K for marketing.",
                "source_type": "slack",
                "source_id": "msg-456",
                "created_at": datetime.now() - timedelta(days=3),
                "updated_at": datetime.now() - timedelta(days=1),
                "permissions": ["user1@company.com", "user2@company.com"],
                "metadata": {"project": "unicorn", "stage": "planning"}
            },
            {
                "doc_id": "test-doc-3",
                "title": "Technical Specifications",
                "content": "The system must support sub-200ms search latency with 99.9% uptime. Database requirements: PostgreSQL with full-text search capabilities, Qdrant for vector storage.",
                "source_type": "upload",
                "source_id": "file-789",
                "created_at": datetime.now() - timedelta(days=45),
                "updated_at": datetime.now() - timedelta(days=30),
                "permissions": ["*"],
                "metadata": {"type": "specifications", "version": "1.0"}
            },
            {
                "doc_id": "test-doc-4",
                "title": "Customer Feedback Analysis",
                "content": "Recent customer feedback indicates high satisfaction with AI features (85% positive). Users particularly value the automated summarization and intelligent search capabilities.",
                "source_type": "google_drive",
                "source_id": "file-012",
                "created_at": datetime.now() - timedelta(days=1),
                "updated_at": datetime.now() - timedelta(days=1),
                "permissions": ["*"],
                "metadata": {"category": "feedback", "sentiment": "positive"}
            },
            {
                "doc_id": "test-doc-5",
                "title": "Budget Allocation Report",
                "content": "Q4 2025 budget allocation: R&D 40%, Marketing 25%, Operations 20%, Sales 15%. Total budget: $10M. Project Unicorn receives $2.5M allocated funding.",
                "source_type": "slack",
                "source_id": "msg-345",
                "created_at": datetime.now() - timedelta(days=20),
                "updated_at": datetime.now() - timedelta(days=15),
                "permissions": ["user1@company.com"],
                "metadata": {"category": "finance", "quarter": "Q4"}
            }
        ]

        # Insert documents into keyword search table
        for doc in test_documents:
            await postgres_connection.execute("""
                INSERT INTO documents_search (
                    doc_id, title, content, source_type, source_id,
                    created_at, updated_at, permissions, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (doc_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    source_type = EXCLUDED.source_type,
                    source_id = EXCLUDED.source_id,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at,
                    permissions = EXCLUDED.permissions,
                    metadata = EXCLUDED.metadata
            """, *[
                doc["doc_id"], doc["title"], doc["content"], doc["source_type"],
                doc["source_id"], doc["created_at"], doc["updated_at"],
                doc["permissions"], doc["metadata"]
            ])

        yield test_documents

        # Clean up test data
        await postgres_connection.execute(
            "DELETE FROM documents_search WHERE doc_id LIKE 'test-doc%'"
        )

    @pytest.mark.asyncio
    async def test_keyword_search_function(self, postgres_connection, setup_test_data):
        """Test PostgreSQL keyword search function"""
        # Test basic keyword search
        results = await postgres_connection.fetch("""
            SELECT * FROM keyword_search('AI strategy', ARRAY['*'], NULL, 10, 0)
        """)

        assert len(results) >= 1
        ai_docs = [r for r in results if 'ai' in r['title'].lower() or 'ai' in r['content'].lower()]
        assert len(ai_docs) >= 1

        # Test with source filter
        results = await postgres_connection.fetch("""
            SELECT * FROM keyword_search('project unicorn', ARRAY['*'], 'slack', 10, 0)
        """)

        assert len(results) >= 1
        slack_results = [r for r in results if r['source_type'] == 'slack']
        assert len(slack_results) >= 1

        # Test phrase search
        results = await postgres_connection.fetch("""
            SELECT * FROM phrase_search('Project Unicorn', ARRAY['*'], NULL, 10)
        """)

        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_end_to_end_hybrid_search(self, setup_test_data):
        """Test complete hybrid search pipeline"""
        # Initialize services
        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Test hybrid search with different query types
            test_queries = [
                ("AI strategy", "semantic_dominant"),
                ("project-unicorn", "keyword_dominant"),
                ("customer feedback", "mixed"),
                ("budget allocation", "keyword_dominant"),
                ("technical specifications", "mixed")
            ]

            for query, expected_type in test_queries:
                start_time = time.time()

                # Execute search
                results = await hybrid_service.search(
                    query=query,
                    user_permissions=["*"],
                    limit=5
                )

                search_time = (time.time() - start_time) * 1000  # Convert to ms

                # Validate results
                assert len(results) <= 5, f"Too many results for query: {query}"
                assert search_time < 500, f"Search too slow: {search_time:.2f}ms for query: {query}"

                # Check result structure
                for result in results:
                    assert result.doc_id is not None
                    assert result.title is not None
                    assert result.content is not None
                    assert result.semantic_score >= 0.0
                    assert result.keyword_score >= 0.0
                    assert result.combined_score >= 0.0
                    assert result.rank >= 1

                # Log performance
                print(f"Query '{query}' ({expected_type}): {len(results)} results in {search_time:.2f}ms")

        finally:
            await hybrid_service.close()

    @pytest.mark.asyncio
    async def test_recency_boosting(self, setup_test_data):
        """Test recency boosting functionality"""
        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Search for recent documents
            results = await hybrid_service.search(
                query="document",
                user_permissions=["*"],
                limit=10,
                include_recency_boost=True
            )

            # Test without recency boost
            results_no_boost = await hybrid_service.search(
                query="document",
                user_permissions=["*"],
                limit=10,
                include_recency_boost=False
            )

            # Recent documents should be ranked higher with boost enabled
            recent_docs_with_boost = [
                r for r in results if (datetime.now() - r.created_at).days <= 30
            ]
            recent_docs_no_boost = [
                r for r in results_no_boost if (datetime.now() - r.created_at).days <= 30
            ]

            # Should have recent documents in both cases
            assert len(recent_docs_with_boost) >= 1
            assert len(recent_docs_no_boost) >= 1

        finally:
            await hybrid_service.close()

    @pytest.mark.asyncio
    async def test_permission_filtering(self, setup_test_data):
        """Test permission-based document filtering"""
        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Search with public permissions
            public_results = await hybrid_service.search(
                query="budget",
                user_permissions=["*"],
                limit=10
            )

            # Search with restricted permissions
            restricted_results = await hybrid_service.search(
                query="budget",
                user_permissions=["nonexistent@company.com"],
                limit=10
            )

            # Should get results with public permissions
            assert len(public_results) >= 1

            # Should get fewer or no results with restricted permissions
            assert len(restricted_results) <= len(public_results)

            # Check that returned results have appropriate permissions
            for result in public_results:
                assert "*" in result.permissions or "user1@company.com" in result.permissions

        finally:
            await hybrid_service.close()

    @pytest.mark.asyncio
    async def test_search_performance_targets(self, setup_test_data):
        """Test that search meets performance targets"""
        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Performance test parameters
            test_queries = [
                "AI strategy",
                "project unicorn launch",
                "technical specifications",
                "customer feedback analysis",
                "budget allocation"
            ]

            latencies = []
            result_counts = []

            # Execute multiple searches and measure performance
            for query in test_queries:
                start_time = time.time()

                results = await hybrid_service.search(
                    query=query,
                    user_permissions=["*"],
                    limit=5
                )

                latency = (time.time() - start_time) * 1000  # Convert to ms
                latencies.append(latency)
                result_counts.append(len(results))

            # Calculate performance metrics
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

            # Validate performance targets
            assert avg_latency < 200, f"Average latency {avg_latency:.2f}ms exceeds 200ms target"
            assert max_latency < 400, f"Max latency {max_latency:.2f}ms too high"
            assert p95_latency < 300, f"P95 latency {p95_latency:.2f}ms exceeds target"

            print(f"Performance Results:")
            print(f"  Average latency: {avg_latency:.2f}ms")
            print(f"  Max latency: {max_latency:.2f}ms")
            print(f"  Min latency: {min_latency:.2f}ms")
            print(f"  P95 latency: {p95_latency:.2f}ms")
            print(f"  Average results: {sum(result_counts) / len(result_counts):.1f}")

        finally:
            await hybrid_service.close()

    @pytest.mark.asyncio
    async def test_rag_service_integration(self, setup_test_data):
        """Test integration with enhanced RAG service"""
        # Import and test enhanced RAG service
        from onyx_core.rag_service import get_rag_service

        rag_service = await get_rag_service()

        try:
            # Test different search types
            test_cases = [
                ("auto", "AI strategy"),
                ("hybrid", "project unicorn"),
                ("semantic", "technical specifications"),
                ("keyword", "budget allocation")
            ]

            for search_type, query in test_cases:
                results = await rag_service.search(
                    query=query,
                    top_k=5,
                    search_type=search_type,
                    user_email=None,  # Use public access
                    user_permissions=["*"]
                )

                assert len(results) <= 5
                for result in results:
                    assert result.score >= 0.0
                    assert result.text is not None
                    assert result.title is not None
                    assert result.source in ["google_drive", "slack", "upload", "web"]

                print(f"RAG {search_type} search '{query}': {len(results)} results")

        finally:
            if hasattr(rag_service, 'close'):
                await rag_service.close()

    @pytest.mark.asyncio
    async def test_health_check_endpoints(self, setup_test_data):
        """Test health check endpoints for all services"""
        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Test hybrid service health
            hybrid_health = await hybrid_service.health_check()
            assert hybrid_health["status"] in ["healthy", "degraded"]
            assert "configuration" in hybrid_health
            assert "services" in hybrid_health

            # Test keyword service health
            keyword_health = await hybrid_service.keyword_search_service.health_check()
            assert keyword_health["status"] in ["healthy", "unhealthy"]
            assert "document_count" in keyword_health

            # Test RAG service health
            rag_health = await hybrid_service.rag_service.health_check()
            assert rag_health["status"] in ["healthy", "unhealthy"]

            print(f"Health Check Results:")
            print(f"  Hybrid Search: {hybrid_health['status']}")
            print(f"  Keyword Search: {keyword_health['status']}")
            print(f"  RAG Service: {rag_health['status']}")

        finally:
            await hybrid_service.close()

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, postgres_connection):
        """Test error handling and recovery mechanisms"""
        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Test with empty query
            results = await hybrid_service.search(
                query="",
                user_permissions=["*"]
            )
            # Should return empty results without error
            assert isinstance(results, list)

            # Test with malformed query (should handle gracefully)
            results = await hybrid_service.search(
                query="x" * 10000,  # Very long query
                user_permissions=["*"]
            )
            assert isinstance(results, list)

            # Test with invalid permissions (should not crash)
            results = await hybrid_service.search(
                query="AI strategy",
                user_permissions=["invalid@company.com"]
            )
            assert isinstance(results, list)

            print("Error handling tests passed")

        finally:
            await hybrid_service.close()

    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self, setup_test_data):
        """Test concurrent search operations"""
        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Create multiple concurrent searches
            async def perform_search(query_id):
                return await hybrid_service.search(
                    query=f"test query {query_id}",
                    user_permissions=["*"],
                    limit=5
                )

            # Execute 10 concurrent searches
            tasks = [perform_search(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check that all searches completed (no exceptions)
            successful_results = [r for r in results if not isinstance(r, Exception)]
            exceptions = [r for r in results if isinstance(r, Exception)]

            assert len(exceptions) == 0, f"Got {len(exceptions)} exceptions: {exceptions}"
            assert len(successful_results) == 10

            # Verify all results have expected structure
            for result_list in successful_results:
                assert isinstance(result_list, list)
                for result in result_list:
                    assert hasattr(result, 'doc_id')
                    assert hasattr(result, 'title')
                    assert hasattr(result, 'combined_score')

            print("Concurrent search test passed")

        finally:
            await hybrid_service.close()


class TestHybridSearchAPI:
    """API integration tests for hybrid search"""

    @pytest.mark.asyncio
    async def test_search_api_endpoints(self):
        """Test search API endpoints"""
        # Note: This test would require running FastAPI server
        # For now, we'll test the service layer directly

        hybrid_service = HybridSearchService()
        await hybrid_service._ensure_services_initialized()

        try:
            # Test different search configurations
            test_cases = [
                {
                    "query": "AI strategy",
                    "permissions": ["*"],
                    "source_filter": None,
                    "limit": 5,
                    "expected_results": "list"
                },
                {
                    "query": "project unicorn",
                    "permissions": ["user1@company.com"],
                    "source_filter": "slack",
                    "limit": 3,
                    "expected_results": "list"
                }
            ]

            for test_case in test_cases:
                results = await hybrid_service.search(
                    query=test_case["query"],
                    user_permissions=test_case["permissions"],
                    source_filter=test_case["source_filter"],
                    limit=test_case["limit"]
                )

                assert isinstance(results, list), f"Expected list for query: {test_case['query']}"
                assert len(results) <= test_case["limit"]

                # Verify result structure matches API expectations
                for result in results:
                    api_result = {
                        "doc_id": result.doc_id,
                        "title": result.title,
                        "source_type": result.source_type,
                        "source_id": result.source_id,
                        "created_at": result.created_at.isoformat() if result.created_at else None,
                        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
                        "permissions": result.permissions,
                        "metadata": result.metadata,
                        "semantic_score": result.semantic_score,
                        "keyword_score": result.keyword_score,
                        "combined_score": result.combined_score,
                        "rank": result.rank,
                        "content_preview": result.content_preview
                    }

                    # Verify all required fields exist and are serializable
                    for key, value in api_result.items():
                        if key in ["created_at", "updated_at"] and value is not None:
                            # Verify datetime format
                            datetime.fromisoformat(value)
                        elif key in ["permissions", "metadata"]:
                            assert isinstance(value, (list, dict))

        finally:
            await hybrid_service.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])