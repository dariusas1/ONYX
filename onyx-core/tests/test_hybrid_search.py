"""
Unit Tests for Hybrid Search Service

This module contains comprehensive unit tests for the hybrid search functionality,
including result fusion, recency boosting, performance optimization, and error handling.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import time

# Import the services we're testing
from onyx_core.services.hybrid_search_service import HybridSearchService, HybridSearchResult
from onyx_core.services.keyword_search_service import KeywordSearchService, KeywordSearchResult
from onyx_core.rag_service import SearchResult
from onyx_core.config.search_config import SearchConfigManager


class TestHybridSearchResult:
    """Test cases for HybridSearchResult dataclass"""

    def test_hybrid_search_result_creation(self):
        """Test HybridSearchResult object creation"""
        now = datetime.now()
        result = HybridSearchResult(
            doc_id="test-doc-1",
            title="Test Document",
            content="Test content",
            source_type="google_drive",
            source_id="file-123",
            created_at=now,
            updated_at=now,
            permissions=["*"],
            metadata={"key": "value"},
            semantic_score=0.8,
            keyword_score=0.6,
            combined_score=0.74,  # (0.8 * 0.7) + (0.6 * 0.3)
            content_preview="Test content...",
            rank=1
        )

        assert result.doc_id == "test-doc-1"
        assert result.title == "Test Document"
        assert result.semantic_score == 0.8
        assert result.keyword_score == 0.6
        assert result.combined_score == 0.74
        assert result.rank == 1


class TestHybridSearchService:
    """Test cases for HybridSearchService"""

    @pytest.fixture
    def mock_config(self):
        """Mock search configuration"""
        config = Mock()
        config.semantic_weight = 0.7
        config.keyword_weight = 0.3
        config.timeout_ms = 200
        config.recency_boost_days = 30
        config.recency_boost_factor = 1.10
        config.default_limit = 5
        return config

    @pytest.fixture
    def hybrid_service(self, mock_config):
        """Create hybrid search service with mocked configuration"""
        with patch('onyx_core.services.hybrid_search_service.os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_value"
            service = HybridSearchService()
            service.semantic_weight = mock_config.semantic_weight
            service.keyword_weight = mock_config.keyword_weight
            service.timeout_ms = mock_config.timeout_ms
            service.recency_boost_days = mock_config.recency_boost_days
            service.recency_boost_factor = mock_config.recency_boost_factor
            service.default_limit = mock_config.default_limit
            return service

    @pytest.mark.asyncio
    async def test_apply_recency_boost_recent_document(self, hybrid_service):
        """Test recency boost for recent documents"""
        score = 0.5
        created_at = datetime.now() - timedelta(days=15)  # Within 30 days

        boosted_score = hybrid_service._apply_recency_boost(score, created_at)
        expected = 0.5 * 1.10  # 0.55

        assert boosted_score == expected

    @pytest.mark.asyncio
    async def test_apply_recency_boost_old_document(self, hybrid_service):
        """Test no recency boost for old documents"""
        score = 0.6
        created_at = datetime.now() - timedelta(days=60)  # Outside 30 days

        boosted_score = hybrid_service._apply_recency_boost(score, created_at)

        assert boosted_score == score  # No change

    @pytest.mark.asyncio
    async def test_apply_recency_boost_none_date(self, hybrid_service):
        """Test recency boost with None date"""
        score = 0.7
        created_at = None

        boosted_score = hybrid_service._apply_recency_boost(score, created_at)

        assert boosted_score == score  # No change

    def test_classify_query_type_keyword_dominant(self, hybrid_service):
        """Test query classification for keyword-dominant queries"""
        queries = [
            "project-unicorn launch date",
            "ticket-123 status",
            "file:/path/to/document.pdf",
            "user@example.com email",
            "https://example.com website",
            "exact phrase in quotes"
        ]

        for query in queries:
            query_type = hybrid_service.classify_query_type(query)
            assert query_type == "keyword", f"Query '{query}' should be classified as keyword"

    def test_classify_query_type_semantic_dominant(self, hybrid_service):
        """Test query classification for semantic-dominant queries"""
        queries = [
            "what is artificial intelligence",
            "how to improve team productivity",
            "explain the benefits of cloud computing",
            "describe the implementation strategy",
            "summarize the quarterly results"
        ]

        for query in queries:
            query_type = hybrid_service.classify_query_type(query)
            assert query_type == "semantic", f"Query '{query}' should be classified as semantic"

    def test_classify_query_type_mixed(self, hybrid_service):
        """Test query classification for mixed queries"""
        queries = [
            "customer feedback on AI features",
            "project timeline and milestones",
            "best practices for security"
        ]

        for query in queries:
            query_type = hybrid_service.classify_query_type(query)
            assert query_type == "mixed", f"Query '{query}' should be classified as mixed"

    def test_fuse_results_no_duplicates(self, hybrid_service):
        """Test result fusion with no duplicate documents"""
        # Create semantic results
        semantic_results = [
            SearchResult(
                doc_id="doc-1",
                score=0.9,
                text="Semantic content 1",
                title="Document 1",
                source="google_drive",
                metadata={"created_at": datetime.now()}
            ),
            SearchResult(
                doc_id="doc-2",
                score=0.8,
                text="Semantic content 2",
                title="Document 2",
                source="slack",
                metadata={"created_at": datetime.now()}
            )
        ]

        # Create keyword results
        keyword_results = [
            KeywordSearchResult(
                doc_id="doc-3",
                title="Keyword Document 3",
                content="Keyword content 3",
                source_type="upload",
                source_id="file-3",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                permissions=["*"],
                metadata={},
                bm25_score=0.7,
                content_preview="Keyword preview..."
            ),
            KeywordSearchResult(
                doc_id="doc-4",
                title="Keyword Document 4",
                content="Keyword content 4",
                source_type="web",
                source_id="url-4",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                permissions=["*"],
                metadata={},
                bm25_score=0.6,
                content_preview="Keyword preview..."
            )
        ]

        # Fuse results
        fused_results = hybrid_service._fuse_results(semantic_results, keyword_results)

        # Should have 4 unique documents
        assert len(fused_results) == 4

        # Check combined scores
        doc1 = next(r for r in fused_results if r.doc_id == "doc-1")
        assert doc1.semantic_score == 0.9
        assert doc1.keyword_score == 0.0
        assert doc1.combined_score == 0.9 * 0.7  # 0.63

        doc3 = next(r for r in fused_results if r.doc_id == "doc-3")
        assert doc3.semantic_score == 0.0
        assert doc3.keyword_score == 0.7
        assert doc3.combined_score == 0.7 * 0.3  # 0.21

    def test_fuse_results_with_duplicates(self, hybrid_service):
        """Test result fusion with duplicate documents"""
        # Create semantic results
        semantic_results = [
            SearchResult(
                doc_id="doc-1",
                score=0.9,
                text="Content about AI strategy",
                title="AI Strategy Document",
                source="google_drive",
                metadata={"created_at": datetime.now()}
            )
        ]

        # Create keyword results with duplicate
        keyword_results = [
            KeywordSearchResult(
                doc_id="doc-1",  # Same document ID
                title="AI Strategy Document",  # Same title
                content="Detailed content about AI strategy implementation",
                source_type="google_drive",
                source_id="file-1",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                permissions=["*"],
                metadata={"category": "strategy"},
                bm25_score=0.7,
                content_preview="Detailed content..."
            )
        ]

        # Fuse results
        fused_results = hybrid_service._fuse_results(semantic_results, keyword_results)

        # Should have only 1 document (duplicate merged)
        assert len(fused_results) == 1

        # Check merged result has both scores
        merged_doc = fused_results[0]
        assert merged_doc.doc_id == "doc-1"
        assert merged_doc.semantic_score == 0.9
        assert merged_doc.keyword_score == 0.7
        expected_combined = (0.9 * 0.7) + (0.7 * 0.3)  # 0.84
        assert merged_doc.combined_score == expected_combined

    def test_fuse_results_ranking(self, hybrid_service):
        """Test result fusion ranking by combined score"""
        # Create results with different scores
        semantic_results = [
            SearchResult(
                doc_id="doc-high",
                score=0.9,  # High semantic score
                text="High scoring content",
                title="High Score Doc",
                source="google_drive",
                metadata={"created_at": datetime.now()}
            ),
            SearchResult(
                doc_id="doc-low",
                score=0.4,  # Low semantic score
                text="Low scoring content",
                title="Low Score Doc",
                source="slack",
                metadata={"created_at": datetime.now()}
            )
        ]

        keyword_results = [
            KeywordSearchResult(
                doc_id="doc-medium",
                title="Medium Score Doc",
                content="Medium scoring content",
                source_type="upload",
                source_id="file-2",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                permissions=["*"],
                metadata={},
                bm25_score=0.6,  # Medium keyword score
                content_preview="Medium preview..."
            )
        ]

        # Fuse results
        fused_results = hybrid_service._fuse_results(semantic_results, keyword_results)

        # Should be sorted by combined score
        assert len(fused_results) == 3
        assert fused_results[0].doc_id == "doc-high"  # 0.9 * 0.7 = 0.63
        assert fused_results[1].doc_id == "doc-medium"  # 0.6 * 0.3 = 0.18
        assert fused_results[2].doc_id == "doc-low"  # 0.4 * 0.7 = 0.28

        # Verify ranks
        assert fused_results[0].rank == 1
        assert fused_results[1].rank == 2
        assert fused_results[2].rank == 3

    @pytest.mark.asyncio
    async def test_search_with_mock_services(self, hybrid_service):
        """Test hybrid search with mocked semantic and keyword services"""
        # Mock the semantic and keyword services
        mock_semantic_result = SearchResult(
            doc_id="doc-1",
            score=0.8,
            text="Semantic content",
            title="Semantic Doc",
            source="google_drive",
            metadata={"created_at": datetime.now()}
        )

        mock_keyword_result = KeywordSearchResult(
            doc_id="doc-1",
            title="Keyword Doc",
            content="Keyword content",
            source_type="google_drive",
            source_id="file-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            permissions=["*"],
            metadata={},
            bm25_score=0.6,
            content_preview="Keyword preview..."
        )

        # Patch the service methods
        hybrid_service.rag_service = AsyncMock()
        hybrid_service.keyword_search_service = AsyncMock()

        hybrid_service.rag_service.search.return_value = [mock_semantic_result]
        hybrid_service.keyword_search_service.search.return_value = [mock_keyword_result]

        # Execute search
        results = await hybrid_service.search(
            query="test query",
            user_permissions=["*"],
            limit=5
        )

        # Verify results
        assert len(results) == 1
        result = results[0]
        assert result.doc_id == "doc-1"
        assert result.semantic_score == 0.8
        assert result.keyword_score == 0.6
        assert result.combined_score == (0.8 * 0.7) + (0.6 * 0.3)  # 0.74

    @pytest.mark.asyncio
    async def test_search_timeout_handling(self, hybrid_service):
        """Test search timeout handling"""
        # Mock services that take too long
        async def slow_semantic_search(*args, **kwargs):
            await asyncio.sleep(0.3)  # 300ms > 200ms timeout
            return []

        async def slow_keyword_search(*args, **kwargs):
            await asyncio.sleep(0.3)
            return []

        hybrid_service.rag_service = AsyncMock()
        hybrid_service.keyword_search_service = AsyncMock()
        hybrid_service.rag_service.search.side_effect = slow_semantic_search
        hybrid_service.keyword_search_service.search.side_effect = slow_keyword_search

        # Execute search should handle timeout gracefully
        start_time = time.time()
        results = await hybrid_service.search(
            query="test query",
            user_permissions=["*"],
            limit=5
        )
        end_time = time.time()

        # Should complete within timeout
        assert (end_time - start_time) < 0.25  # Should be ~200ms + small overhead

    @pytest.mark.asyncio
    async def test_search_with_semantic_only(self, hybrid_service):
        """Test semantic-only search mode"""
        # Mock semantic service
        mock_result = SearchResult(
            doc_id="doc-1",
            score=0.9,
            text="Semantic only content",
            title="Semantic Only Doc",
            source="google_drive",
            metadata={"created_at": datetime.now()}
        )

        hybrid_service.rag_service = AsyncMock()
        hybrid_service.rag_service.search.return_value = [mock_result]

        # Execute semantic-only search
        results = await hybrid_service.search(
            query="test query",
            user_permissions=["*"],
            search_type="semantic"
        )

        # Verify results
        assert len(results) == 1
        assert results[0].doc_id == "doc-1"
        assert results[0].semantic_score == 0.9
        assert results[0].keyword_score == 0.0

    @pytest.mark.asyncio
    async def test_search_with_keyword_only(self, hybrid_service):
        """Test keyword-only search mode"""
        # Mock keyword service
        mock_result = KeywordSearchResult(
            doc_id="doc-1",
            title="Keyword Only Doc",
            content="Keyword only content",
            source_type="google_drive",
            source_id="file-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            permissions=["*"],
            metadata={},
            bm25_score=0.8,
            content_preview="Keyword preview..."
        )

        hybrid_service.keyword_search_service = AsyncMock()
        hybrid_service.keyword_search_service.search.return_value = [mock_result]

        # Execute keyword-only search
        results = await hybrid_service.search(
            query="test query",
            user_permissions=["*"],
            search_type="keyword"
        )

        # Verify results
        assert len(results) == 1
        assert results[0].doc_id == "doc-1"
        assert results[0].semantic_score == 0.0
        assert results[0].keyword_score == 0.8

    @pytest.mark.asyncio
    async def test_search_error_handling(self, hybrid_service):
        """Test search error handling"""
        # Mock services that raise exceptions
        hybrid_service.rag_service = AsyncMock()
        hybrid_service.keyword_search_service = AsyncMock()
        hybrid_service.rag_service.search.side_effect = Exception("Semantic search failed")
        hybrid_service.keyword_search_service.search.side_effect = Exception("Keyword search failed")

        # Execute search should not raise exceptions
        results = await hybrid_service.search(
            query="test query",
            user_permissions=["*"]
        )

        # Should return empty results instead of raising
        assert results == []

    @pytest.mark.asyncio
    async def test_health_check(self, hybrid_service):
        """Test health check functionality"""
        # Mock services
        hybrid_service.rag_service = AsyncMock()
        hybrid_service.keyword_search_service = AsyncMock()

        hybrid_service.rag_service.health_check.return_value = {
            "status": "healthy",
            "collection_exists": True,
            "document_count": 100
        }

        hybrid_service.keyword_search_service.health_check.return_value = {
            "status": "healthy",
            "document_count": 95,
            "search_functions_available": True
        }

        # Execute health check
        health = await hybrid_service.health_check()

        # Verify health check results
        assert health["status"] == "healthy"
        assert "configuration" in health
        assert "services" in health
        assert "performance" in health
        assert health["services"]["semantic_search"]["status"] == "healthy"
        assert health["services"]["keyword_search"]["status"] == "healthy"

    def test_update_performance_stats(self, hybrid_service):
        """Test performance statistics tracking"""
        # Initial stats
        assert hybrid_service._search_stats["total_searches"] == 0
        assert hybrid_service._search_stats["total_latency_ms"] == 0

        # Update stats
        hybrid_service._update_performance_stats(150.0)
        hybrid_service._update_performance_stats(200.0)

        # Verify updated stats
        assert hybrid_service._search_stats["total_searches"] == 2
        assert hybrid_service._search_stats["total_latency_ms"] == 350.0

    @pytest.mark.asyncio
    async def test_get_performance_stats(self, hybrid_service):
        """Test performance statistics retrieval"""
        # Mock keyword search stats
        hybrid_service.keyword_search_service = AsyncMock()
        hybrid_service.keyword_search_service.get_search_stats.return_value = {
            "total_docs": "100",
            "recent_docs": "25"
        }

        # Update some hybrid search stats
        hybrid_service._update_performance_stats(100.0)
        hybrid_service._update_performance_stats(200.0)

        # Get performance stats
        stats = await hybrid_service.get_performance_stats()

        # Verify stats
        assert "hybrid_search" in stats
        assert "keyword_search" in stats
        assert stats["hybrid_search"]["total_searches"] == 2
        assert stats["hybrid_search"]["average_latency_ms"] == 150.0


class TestSearchConfigManager:
    """Test cases for SearchConfigManager"""

    def test_default_config_loading(self):
        """Test loading default configuration"""
        with patch('onyx_core.config.search_config.os.getenv') as mock_getenv:
            # Mock environment variables
            def mock_getenv_func(key, default=None):
                env_vars = {
                    "SEMANTIC_WEIGHT": "0.7",
                    "KEYWORD_WEIGHT": "0.3",
                    "HYBRID_SEARCH_TIMEOUT_MS": "200"
                }
                return env_vars.get(key, default)

            mock_getenv.side_effect = mock_getenv_func

            config_manager = SearchConfigManager()
            config = config_manager.config

            assert config.semantic_weight == 0.7
            assert config.keyword_weight == 0.3
            assert config.total_timeout_ms == 200

    def test_config_validation(self):
        """Test configuration validation"""
        config_manager = SearchConfigManager()
        config_manager.config.semantic_weight = 0.7
        config_manager.config.keyword_weight = 0.4  # Sum = 1.1 > 1.0

        validation = config_manager.validate_config()

        assert not validation["valid"]
        assert len(validation["issues"]) > 0
        assert "weights sum to 1.1" in validation["issues"][0]

    def test_config_update(self):
        """Test configuration updates"""
        config_manager = SearchConfigManager()

        # Update configuration
        config_manager.update_config(
            semantic_weight=0.8,
            keyword_weight=0.2,
            total_timeout_ms=300
        )

        config = config_manager.config
        assert config.semantic_weight == 0.8
        assert config.keyword_weight == 0.2
        assert config.total_timeout_ms == 300

    def test_invalid_config_key(self):
        """Test invalid configuration key"""
        config_manager = SearchConfigManager()

        # Should raise error for invalid key
        with pytest.raises(ValueError):
            config_manager.update_config(invalid_key=0.5)

    def test_get_config_dict(self):
        """Test configuration dictionary output"""
        config_manager = SearchConfigManager()
        config_dict = config_manager.get_config_dict()

        # Verify structure
        assert "weights" in config_dict
        assert "limits" in config_dict
        assert "performance" in config_dict
        assert "features" in config_dict
        assert "recency_boost" in config_dict
        assert "quality" in config_dict
        assert "monitoring" in config_dict

        # Verify weights structure
        weights = config_dict["weights"]
        assert "semantic" in weights
        assert "keyword" in weights


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])