"""
Embedding Service

This module handles content chunking and vector generation using OpenAI embeddings
for indexing in the vector database.
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio

from openai import OpenAI
import tiktoken

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MAX_TOKENS_PER_CHUNK = 500
CHUNK_OVERLAP_TOKENS = 50
BATCH_SIZE = 10  # Process chunks in batches for efficiency
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # Base retry delay in seconds


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk"""
    chunk_index: int
    total_chunks: int
    token_count: int
    start_char: int
    end_char: int
    chunk_hash: str


@dataclass
class ProcessedChunk:
    """Processed chunk with embeddings"""
    text: str
    embedding: List[float]
    metadata: ChunkMetadata


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    success: bool
    chunks: List[ProcessedChunk]
    total_chunks: int
    processing_time: float
    error_message: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None


class EmbeddingService:
    """Service for generating embeddings from text content"""

    def __init__(self):
        """Initialize embedding service with OpenAI client"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model = EMBEDDING_MODEL
        self.dimensions = EMBEDDING_DIMENSIONS

        # Initialize OpenAI client
        try:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            logger.info(f"Embedding service initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

        # Initialize tokenizer for accurate token counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except Exception as e:
            logger.warning(f"Failed to initialize tokenizer for {self.model}: {e}")
            self.tokenizer = None

    async def generate_embeddings(self, content: str, doc_metadata: Dict[str, Any]) -> EmbeddingResult:
        """
        Generate embeddings for text content with chunking

        Args:
            content: Text content to embed
            doc_metadata: Document metadata

        Returns:
            EmbeddingResult with processed chunks and embeddings
        """
        start_time = time.time()

        try:
            # Step 1: Chunk the content
            chunks = self._chunk_content(content)
            total_chunks = len(chunks)

            if total_chunks == 0:
                return EmbeddingResult(
                    success=False,
                    chunks=[],
                    total_chunks=0,
                    processing_time=time.time() - start_time,
                    error_message="No content chunks generated"
                )

            logger.info(f"Generated {total_chunks} chunks from content")

            # Step 2: Generate embeddings for chunks
            processed_chunks = await self._generate_chunk_embeddings(chunks, doc_metadata)

            processing_time = time.time() - start_time

            # Generate statistics
            stats = self._generate_stats(processed_chunks, processing_time)

            logger.info(f"Generated embeddings for {len(processed_chunks)} chunks in {processing_time:.2f}s")

            return EmbeddingResult(
                success=True,
                chunks=processed_chunks,
                total_chunks=total_chunks,
                processing_time=processing_time,
                stats=stats
            )

        except Exception as e:
            error_msg = f"Embedding generation failed: {str(e)}"
            logger.error(error_msg)
            return EmbeddingResult(
                success=False,
                chunks=[],
                total_chunks=0,
                processing_time=time.time() - start_time,
                error_message=error_msg
            )

    def _chunk_content(self, content: str) -> List[str]:
        """
        Split content into overlapping chunks optimized for semantic search

        Args:
            content: Text content to chunk

        Returns:
            List of text chunks
        """
        if not content or not content.strip():
            return []

        # Use tiktoken for accurate token counting if available
        if self.tokenizer:
            return self._chunk_with_tokenizer(content)
        else:
            # Fallback to word-based chunking
            return self._chunk_by_words(content)

    def _chunk_with_tokenizer(self, content: str) -> List[str]:
        """
        Chunk content using tiktoken for accurate token counting

        Args:
            content: Text content to chunk

        Returns:
            List of text chunks
        """
        # Tokenize content
        tokens = self.tokenizer.encode(content)
        total_tokens = len(tokens)

        if total_tokens <= MAX_TOKENS_PER_CHUNK:
            return [content]

        chunks = []
        start_idx = 0
        chunk_index = 0

        while start_idx < total_tokens:
            # Calculate end index
            end_idx = min(start_idx + MAX_TOKENS_PER_CHUNK, total_tokens)

            # Extract tokens for this chunk
            chunk_tokens = tokens[start_idx:end_idx]

            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens)

            # Clean up chunk text
            chunk_text = chunk_text.strip()

            if chunk_text:
                # Add chunk with metadata
                chunks.append(chunk_text)

            # Move start position with overlap
            start_idx = max(0, end_idx - CHUNK_OVERLAP_TOKENS)
            chunk_index += 1

        return chunks

    def _chunk_by_words(self, content: str) -> List[str]:
        """
        Fallback word-based chunking method

        Args:
            content: Text content to chunk

        Returns:
            List of text chunks
        """
        # Split into words and estimate tokens (rough approximation: 1 token ≈ 0.75 words)
        words = content.split()
        target_words_per_chunk = int(MAX_TOKENS_PER_CHUNK * 0.75)
        overlap_words = int(CHUNK_OVERLAP_TOKENS * 0.75)

        if len(words) <= target_words_per_chunk:
            return [content]

        chunks = []
        start_idx = 0

        while start_idx < len(words):
            end_idx = min(start_idx + target_words_per_chunk, len(words))
            chunk_words = words[start_idx:end_idx]
            chunk_text = ' '.join(chunk_words).strip()

            if chunk_text:
                chunks.append(chunk_text)

            # Move start position with overlap
            start_idx = max(0, end_idx - overlap_words)

        return chunks

    async def _generate_chunk_embeddings(self, chunks: List[str], doc_metadata: Dict[str, Any]) -> List[ProcessedChunk]:
        """
        Generate embeddings for chunks with batching and retry logic

        Args:
            chunks: List of text chunks
            doc_metadata: Document metadata

        Returns:
            List of processed chunks with embeddings
        """
        processed_chunks = []
        total_chunks = len(chunks)

        # Process chunks in batches
        for batch_start in range(0, total_chunks, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total_chunks)
            batch_chunks = chunks[batch_start:batch_end]
            batch_indices = list(range(batch_start, batch_end))

            # Generate embeddings for this batch with retry logic
            batch_embeddings = await self._generate_batch_embeddings_with_retry(batch_chunks)

            # Create processed chunks
            for i, (chunk_text, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
                chunk_metadata = self._create_chunk_metadata(
                    chunk_text=chunk_text,
                    chunk_index=batch_indices[i],
                    total_chunks=total_chunks,
                    doc_metadata=doc_metadata
                )

                processed_chunk = ProcessedChunk(
                    text=chunk_text,
                    embedding=embedding,
                    metadata=chunk_metadata
                )
                processed_chunks.append(processed_chunk)

        return processed_chunks

    async def _generate_batch_embeddings_with_retry(self, chunks: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of chunks with retry logic

        Args:
            chunks: List of text chunks

        Returns:
            List of embeddings
        """
        for attempt in range(MAX_RETRIES):
            try:
                response = self.openai_client.embeddings.create(
                    model=self.model,
                    input=chunks
                )

                embeddings = [data.embedding for data in response.data]

                # Validate embeddings
                if len(embeddings) != len(chunks):
                    raise ValueError(f"Embedding count mismatch: expected {len(chunks)}, got {len(embeddings)}")

                for embedding in embeddings:
                    if len(embedding) != self.dimensions:
                        raise ValueError(f"Embedding dimension mismatch: expected {self.dimensions}, got {len(embedding)}")

                return embeddings

            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    # Last attempt failed, raise the exception
                    raise Exception(f"Embedding generation failed after {MAX_RETRIES} attempts: {str(e)}")

                # Exponential backoff
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Embedding generation attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)

        # This should never be reached
        raise Exception("Embedding generation failed: unexpected error")

    def _create_chunk_metadata(self, chunk_text: str, chunk_index: int, total_chunks: int, doc_metadata: Dict[str, Any]) -> ChunkMetadata:
        """
        Create metadata for a chunk

        Args:
            chunk_text: The chunk text
            chunk_index: Index of this chunk
            total_chunks: Total number of chunks
            doc_metadata: Document metadata

        Returns:
            ChunkMetadata object
        """
        # Calculate token count for this chunk
        if self.tokenizer:
            token_count = len(self.tokenizer.encode(chunk_text))
        else:
            # Rough approximation
            token_count = len(chunk_text.split()) * 1.3

        # Calculate character positions (rough approximation)
        if chunk_index == 0:
            start_char = 0
        else:
            # Estimate start position (this is approximate since we don't track exact positions)
            avg_chunk_length = len(chunk_text)
            start_char = chunk_index * (avg_chunk_length - 100)  # Approximate with overlap

        end_char = start_char + len(chunk_text)

        # Calculate chunk hash
        chunk_hash = self._calculate_chunk_hash(chunk_text)

        return ChunkMetadata(
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            token_count=token_count,
            start_char=start_char,
            end_char=end_char,
            chunk_hash=chunk_hash
        )

    def _calculate_chunk_hash(self, chunk_text: str) -> str:
        """
        Calculate hash for chunk deduplication

        Args:
            chunk_text: Chunk text content

        Returns:
            SHA-256 hash as hexadecimal string
        """
        import hashlib
        return hashlib.sha256(chunk_text.encode('utf-8')).hexdigest()

    def _generate_stats(self, chunks: List[ProcessedChunk], processing_time: float) -> Dict[str, Any]:
        """
        Generate statistics about the embedding process

        Args:
            chunks: List of processed chunks
            processing_time: Total processing time

        Returns:
            Statistics dictionary
        """
        if not chunks:
            return {}

        token_counts = [chunk.metadata.token_count for chunk in chunks]
        embedding_lengths = [len(chunk.embedding) for chunk in chunks]

        return {
            'total_chunks': len(chunks),
            'total_tokens': sum(token_counts),
            'average_tokens_per_chunk': sum(token_counts) / len(token_counts) if token_counts else 0,
            'min_tokens_per_chunk': min(token_counts) if token_counts else 0,
            'max_tokens_per_chunk': max(token_counts) if token_counts else 0,
            'total_processing_time': processing_time,
            'chunks_per_second': len(chunks) / processing_time if processing_time > 0 else 0,
            'tokens_per_second': sum(token_counts) / processing_time if processing_time > 0 else 0,
            'embedding_dimensions': self.dimensions,
            'model_used': self.model,
            'average_embedding_length': sum(embedding_lengths) / len(embedding_lengths) if embedding_lengths else 0,
            'embedding_validation_passed': all(length == self.dimensions for length in embedding_lengths),
        }

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the embedding model

        Returns:
            Model information dictionary
        """
        return {
            'model': self.model,
            'dimensions': self.dimensions,
            'max_tokens_per_chunk': MAX_TOKENS_PER_CHUNK,
            'chunk_overlap_tokens': CHUNK_OVERLAP_TOKENS,
            'batch_size': BATCH_SIZE,
            'max_retries': MAX_RETRIES,
            'retry_delay': RETRY_DELAY,
            'tokenizer_available': self.tokenizer is not None,
        }


# Global embedding service instance
embedding_service = None


async def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service instance"""
    global embedding_service
    if embedding_service is None:
        embedding_service = EmbeddingService()
    return embedding_service