"""
RAG (Retrieval-Augmented Generation) Service Module

This module provides document search and retrieval functionality using Qdrant vector database
and sentence transformers for embedding generation.
"""

import os
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

from qdrant_client import QdrantClient # pyright: ignore[reportMissingImports]
from qdrant_client.models import ( # pyright: ignore[reportMissingImports]
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    OptimizersConfigDiff,
)
from openai import OpenAI

# Import hybrid search components
try:
    from .services.hybrid_search_service import HybridSearchService, HybridSearchResult
    from .services.keyword_search_service import KeywordSearchService
    HYBRID_SEARCH_AVAILABLE = True
except ImportError:
    HYBRID_SEARCH_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Hybrid search components not available - falling back to semantic search only")

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
VECTOR_SIZE = 1536
COLLECTION_NAME = "documents"


@dataclass
class SearchResult:
    """Data class for search results"""

    doc_id: str
    score: float
    text: str
    title: str
    source: str
    metadata: Dict[str, Any]


class RAGService:
    """RAG Service for document search and retrieval with hybrid search capabilities"""

    def __init__(self):
        """Initialize RAG service with Qdrant and OpenAI embeddings"""
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.collection_name = COLLECTION_NAME

        # Hybrid search configuration
        self.enable_hybrid_search = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
        self.hybrid_search_service = None

        # Initialize clients
        self._init_clients()
        self._init_hybrid_search()

    def _init_clients(self):
        """Initialize Qdrant client and OpenAI client"""
        try:
            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(
                url=self.qdrant_url, api_key=self.qdrant_api_key
            )

            # Initialize OpenAI client for embeddings
            if not self.openai_api_key:
                logger.warning("OPENAI_API_KEY not set. Embedding generation will fail.")
            self.openai_client = OpenAI(api_key=self.openai_api_key)

            logger.info(f"RAG service initialized with Qdrant at {self.qdrant_url}")
            logger.info(f"Using OpenAI embedding model: {EMBEDDING_MODEL_NAME}")

        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise

    def _init_hybrid_search(self):
        """Initialize hybrid search service if enabled"""
        if not self.enable_hybrid_search:
            logger.info("Hybrid search disabled - using semantic search only")
            return

        if not HYBRID_SEARCH_AVAILABLE:
            logger.warning("Hybrid search requested but components not available")
            self.enable_hybrid_search = False
            return

        try:
            # Note: Hybrid search service is initialized lazily when needed
            # to avoid circular import issues
            logger.info("Hybrid search enabled - will initialize on first search")
        except Exception as e:
            logger.error(f"Failed to initialize hybrid search: {e}")
            self.enable_hybrid_search = False

    async def ensure_collection_exists(self):
        """Ensure the Qdrant collection exists"""
        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                # Create collection with optimized configuration
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE,
                        on_disk=True,  # Enable on-disk storage for large corpus support
                    ),
                    optimizers_config=OptimizersConfigDiff(
                        default_segment_number=2,  # Balance between indexing speed and search performance
                        indexing_threshold=20000,  # Rebuild index after this many updates
                    ),
                )
                logger.info(
                    f"Created Qdrant collection: {self.collection_name} "
                    f"({VECTOR_SIZE} dimensions, on-disk storage enabled)"
                )
            else:
                logger.info(f"Qdrant collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise

    def embed_query(self, query: str) -> List[float]:
        """Embed a query string using OpenAI text-embedding-3-small"""
        try:
            response = self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL_NAME,
                input=query
            )
            embedding = response.data[0].embedding
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise

    async def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: Optional[str] = None,
        score_threshold: float = 0.5,
        user_email: Optional[str] = None,
        search_type: str = "auto",  # auto, hybrid, semantic, keyword
        user_permissions: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """
        Search for documents using hybrid, semantic, or keyword search with permission filtering

        Args:
            query: Search query string
            top_k: Number of top results to return
            source_filter: Optional filter for document source
            score_threshold: Minimum similarity score threshold (for semantic search)
            user_email: User email for permission filtering (REQUIRED for secure search)
            search_type: Type of search to perform ("auto", "hybrid", "semantic", "keyword")
            user_permissions: List of user permissions/email addresses for keyword search

        Returns:
            List of search results filtered by user permissions
        """
        try:
            # Ensure collection exists
            await self.ensure_collection_exists()

            # Use hybrid search if enabled and requested
            if (self.enable_hybrid_search and
                HYBRID_SEARCH_AVAILABLE and
                search_type in ["auto", "hybrid"]):
                return await self._search_with_hybrid(
                    query, top_k, source_filter, user_email, user_permissions
                )
            elif search_type == "keyword" and HYBRID_SEARCH_AVAILABLE:
                return await self._search_with_keyword_only(
                    query, top_k, source_filter, user_email, user_permissions
                )

            # Fallback to semantic search
            # Embed the query
            query_embedding = self.embed_query(query)

            # Build filter conditions
            filter_conditions = []

            # Add source filter if provided
            if source_filter:
                filter_conditions.append(
                    FieldCondition(
                        key="source", match=MatchValue(value=source_filter)
                    )
                )

            # Add permission filter if user_email is provided (CRITICAL for security)
            if user_email:
                # Permission filter: user must have access OR document is public (permissions contains "*")
                # This uses MatchAny to check if the permissions array contains either the user's email or "*"
                filter_conditions.append(
                    FieldCondition(
                        key="metadata.permissions",
                        match=MatchAny(any=[user_email, "*"])
                    )
                )
                logger.debug(f"Applying permission filter for user: {user_email}")
            else:
                # WARNING: No permission filtering applied - only use for public/unauthenticated searches
                logger.warning("Search performed without permission filtering - this may expose private documents!")

            # Build final filter
            search_filter = None
            if filter_conditions:
                search_filter = Filter(must=filter_conditions)

            # Search in Qdrant
            search_result = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=top_k,
                score_threshold=score_threshold,
            )

            # Convert to SearchResult objects
            results = []
            for hit in search_result:
                if hasattr(hit, "payload") and hit.payload:
                    result = SearchResult(
                        doc_id=hit.id,
                        score=hit.score,
                        text=hit.payload.get("text", ""),
                        title=hit.payload.get("title", ""),
                        source=hit.payload.get("source", "unknown"),
                        metadata=hit.payload.get("metadata", {}),
                    )
                    results.append(result)

            logger.info(
                f"Search completed: {len(results)} results for query: '{query}' "
                f"(user: {user_email or 'unauthenticated'})"
            )
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            # Return empty results instead of raising to maintain service availability
            return []

    async def add_document(
        self,
        doc_id: str,
        text: str,
        title: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a document to the vector database

        Args:
            doc_id: Unique document identifier
            text: Document text content
            title: Document title
            source: Document source (e.g., 'google_drive', 'slack', 'local')
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure collection exists
            await self.ensure_collection_exists()

            # Embed the document text
            doc_embedding = self.embed_query(text)

            # Create point structure
            point = PointStruct(
                id=doc_id,
                vector=doc_embedding,
                payload={
                    "text": text,
                    "title": title,
                    "source": source,
                    "metadata": metadata or {},
                },
            )

            # Upsert to Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name, points=[point]
            )

            logger.info(f"Added document {doc_id} from {source}")
            return True

        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            return False

    async def get_document_count(self) -> int:
        """Get total number of documents in the collection"""
        try:
            await self.ensure_collection_exists()
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Failed to get document count: {e}")
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on RAG service"""
        try:
            # Check Qdrant connection
            collections = self.qdrant_client.get_collections()
            collection_exists = self.collection_name in [c.name for c in collections.collections]

            health_info = {
                "status": "healthy",
                "qdrant_url": self.qdrant_url,
                "collection_exists": collection_exists,
                "embedding_model": EMBEDDING_MODEL_NAME,
            }

            # If collection exists, get detailed info
            if collection_exists:
                try:
                    doc_count = await self.get_document_count()
                    collection_info = self.qdrant_client.get_collection(self.collection_name)

                    health_info.update({
                        "document_count": doc_count,
                        "vector_size": getattr(collection_info.config.params.vectors, 'size', 'unknown'),
                        "distance_metric": str(getattr(collection_info.config.params.vectors, 'distance', 'unknown')),
                        "on_disk_storage": getattr(collection_info.config.params.vectors, 'on_disk', False),
                        "segments_count": getattr(collection_info, 'segments_count', 0),
                        "indexed_vectors": getattr(collection_info, 'indexed_vectors_count', 0),
                    })
                except Exception as e:
                    logger.warning(f"Could not retrieve collection details: {e}")

            return health_info

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def _get_hybrid_search_service(self) -> HybridSearchService:
        """Get or create hybrid search service instance"""
        if self.hybrid_search_service is None:
            from .services.hybrid_search_service import get_hybrid_search_service
            self.hybrid_search_service = await get_hybrid_search_service()
        return self.hybrid_search_service

    async def _search_with_hybrid(
        self,
        query: str,
        top_k: int,
        source_filter: Optional[str],
        user_email: Optional[str],
        user_permissions: Optional[List[str]]
    ) -> List[SearchResult]:
        """Execute hybrid search combining semantic and keyword approaches"""
        try:
            # Convert user_email to user_permissions format
            if user_permissions is None:
                user_permissions = [user_email] if user_email else ['*']

            # Get hybrid search service
            hybrid_service = await self._get_hybrid_search_service()

            # Execute hybrid search
            hybrid_results = await hybrid_service.search(
                query=query,
                user_permissions=user_permissions,
                source_filter=source_filter,
                limit=top_k,
                include_recency_boost=True,
                query_type="hybrid"
            )

            # Convert HybridSearchResult to SearchResult format
            search_results = []
            for result in hybrid_results:
                search_result = SearchResult(
                    doc_id=result.doc_id,
                    score=result.combined_score,
                    text=result.content,
                    title=result.title,
                    source=result.source_type,
                    metadata={
                        **result.metadata,
                        'source_id': result.source_id,
                        'permissions': result.permissions,
                        'created_at': result.created_at,
                        'updated_at': result.updated_at,
                        'semantic_score': result.semantic_score,
                        'keyword_score': result.keyword_score,
                        'combined_score': result.combined_score,
                        'rank': result.rank
                    }
                )
                search_results.append(search_result)

            logger.info(f"Hybrid search returned {len(search_results)} results for query: '{query}'")
            return search_results

        except Exception as e:
            logger.error(f"Hybrid search failed, falling back to semantic: {e}")
            # Fallback to semantic search
            return await self._search_with_semantic_only(query, top_k, source_filter, user_email)

    async def _search_with_keyword_only(
        self,
        query: str,
        top_k: int,
        source_filter: Optional[str],
        user_email: Optional[str],
        user_permissions: Optional[List[str]]
    ) -> List[SearchResult]:
        """Execute keyword search only"""
        try:
            # Convert user_email to user_permissions format
            if user_permissions is None:
                user_permissions = [user_email] if user_email else ['*']

            # Get keyword search service
            from .services.keyword_search_service import get_keyword_search_service
            keyword_service = await get_keyword_search_service()

            # Execute keyword search
            keyword_results = await keyword_service.search(
                query=query,
                user_permissions=user_permissions,
                source_filter=source_filter,
                limit=top_k,
                include_recency_boost=True
            )

            # Convert KeywordSearchResult to SearchResult format
            search_results = []
            for result in keyword_results:
                search_result = SearchResult(
                    doc_id=result.doc_id,
                    score=result.bm25_score,
                    text=result.content,
                    title=result.title,
                    source=result.source_type,
                    metadata={
                        **result.metadata,
                        'source_id': result.source_id,
                        'permissions': result.permissions,
                        'created_at': result.created_at,
                        'updated_at': result.updated_at,
                        'bm25_score': result.bm25_score,
                        'search_type': 'keyword'
                    }
                )
                search_results.append(search_result)

            logger.info(f"Keyword search returned {len(search_results)} results for query: '{query}'")
            return search_results

        except Exception as e:
            logger.error(f"Keyword search failed, falling back to semantic: {e}")
            # Fallback to semantic search
            return await self._search_with_semantic_only(query, top_k, source_filter, user_email)

    async def _search_with_semantic_only(
        self,
        query: str,
        top_k: int,
        source_filter: Optional[str],
        user_email: Optional[str],
        score_threshold: float = 0.3
    ) -> List[SearchResult]:
        """Execute semantic search only with enhanced filtering"""
        # Embed the query
        query_embedding = self.embed_query(query)

        # Build filter conditions
        filter_conditions = []

        # Add source filter if provided
        if source_filter:
            filter_conditions.append(
                FieldCondition(
                    key="source", match=MatchValue(value=source_filter)
                )
            )

        # Add permission filter if user_email is provided
        if user_email:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.permissions",
                    match=MatchAny(any=[user_email, "*"])
                )
            )
            logger.debug(f"Applying permission filter for user: {user_email}")
        else:
            logger.warning("Search performed without permission filtering")

        # Build final filter
        search_filter = None
        if filter_conditions:
            search_filter = Filter(must=filter_conditions)

        # Search in Qdrant
        search_result = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k,
            score_threshold=score_threshold,
        )

        # Convert to SearchResult objects
        results = []
        for hit in search_result:
            if hasattr(hit, "payload") and hit.payload:
                result = SearchResult(
                    doc_id=hit.id,
                    score=hit.score,
                    text=hit.payload.get("text", ""),
                    title=hit.payload.get("title", ""),
                    source=hit.payload.get("source", "unknown"),
                    metadata={
                        **hit.payload.get("metadata", {}),
                        'semantic_score': hit.score,
                        'search_type': 'semantic'
                    }
                )
                results.append(result)

        return results


# Global RAG service instance
rag_service = None


async def get_rag_service() -> RAGService:
    """Get or create RAG service instance"""
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service
