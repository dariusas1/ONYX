"""
Memory Service for ONYX

This service provides CRUD operations for user memories with categorization,
confidence scoring, and search functionality.
"""

import os
import re
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for memory CRUD operations and management"""

    def __init__(self):
        """Initialize memory service with database connection"""
        self.connection_string = self._build_connection_string()
        self.conn = None

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "manus")
        user = os.getenv("POSTGRES_USER", "manus")
        password = os.getenv("POSTGRES_PASSWORD", "")

        return f"host={host} port={port} dbname={database} user={user} password={password}"

    def connect(self):
        """Establish database connection"""
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(self.connection_string)
                logger.info("Memory service database connection established")
        except Exception as e:
            logger.error(f"Memory service database connection failed: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Memory service database connection closed")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    # =========================================================================
    # Memory CRUD Operations
    # =========================================================================

    async def create_memory(
        self,
        user_id: str,
        fact: str,
        category: str,
        confidence: float = 0.8,
        source_type: str = "manual",
        source_message_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new memory record

        Args:
            user_id: User UUID
            fact: Memory content/fact
            category: Memory category
            confidence: Confidence score (0.0-1.0)
            source_type: Source of the memory
            source_message_id: Optional source message UUID
            conversation_id: Optional conversation UUID
            metadata: Optional metadata dictionary
            expires_at: Optional expiration timestamp

        Returns:
            Created memory record or None if failed
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                # Validate inputs
                if not fact or not fact.strip():
                    raise ValueError("Memory fact cannot be empty")

                if not self._validate_category(category):
                    raise ValueError(f"Invalid category: {category}")

                if not self._validate_confidence(confidence):
                    raise ValueError(f"Invalid confidence score: {confidence}")

                if not self._validate_source_type(source_type):
                    raise ValueError(f"Invalid source type: {source_type}")

                # Check for duplicates
                duplicate = await self._find_duplicate_memory(user_id, fact)
                if duplicate and duplicate['confidence'] > 0.7:
                    logger.info(f"Duplicate memory found with high confidence: {duplicate['id']}")
                    return duplicate

                # Detect and mask PII if enabled
                masked_fact, pii_detected = self._detect_and_mask_pii(fact)
                if pii_detected:
                    logger.info(f"PII detected and masked in memory for user {user_id}")

                cur.execute(
                    """
                    INSERT INTO user_memories
                    (user_id, fact, category, confidence, source_type,
                     source_message_id, conversation_id, metadata, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, fact, category, confidence, source_type,
                              source_message_id, conversation_id, metadata, expires_at,
                              access_count, last_accessed_at, is_deleted, created_at, updated_at
                    """,
                    (
                        user_id,
                        masked_fact,
                        category,
                        confidence,
                        source_type,
                        source_message_id,
                        conversation_id,
                        Json(metadata or {}),
                        expires_at
                    )
                )

                result = cur.fetchone()
                self.conn.commit()

                # Convert to dict with proper column names
                memory = {
                    'id': result[0],
                    'user_id': result[1],
                    'fact': result[2],
                    'category': result[3],
                    'confidence': result[4],
                    'source_type': result[5],
                    'source_message_id': result[6],
                    'conversation_id': result[7],
                    'metadata': result[8],
                    'expires_at': result[9],
                    'access_count': result[10],
                    'last_accessed_at': result[11],
                    'is_deleted': result[12],
                    'created_at': result[13],
                    'updated_at': result[14]
                }

                logger.info(f"Created memory {memory['id']} for user {user_id}")
                return memory

        except ValueError as e:
            logger.error(f"Validation error creating memory: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    async def get_memory(self, memory_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific memory by ID

        Args:
            memory_id: Memory UUID
            user_id: User UUID for authorization

        Returns:
            Memory record or None if not found
        """
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_id, fact, category, confidence, source_type,
                           source_message_id, conversation_id, metadata, expires_at,
                           access_count, last_accessed_at, is_deleted, created_at, updated_at
                    FROM user_memories
                    WHERE id = %s AND user_id = %s AND is_deleted = FALSE
                    """,
                    (memory_id, user_id)
                )

                result = cur.fetchone()
                if result:
                    # Update access tracking
                    await self._track_access(memory_id)
                    return dict(result)

                return None

        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None

    async def update_memory(
        self,
        memory_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing memory

        Args:
            memory_id: Memory UUID
            user_id: User UUID for authorization
            updates: Dictionary of fields to update

        Returns:
            Updated memory record or None if failed
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                # Build dynamic update query
                valid_fields = ['fact', 'category', 'confidence', 'metadata', 'expires_at']
                update_fields = []
                params = []
                param_index = 1

                for field, value in updates.items():
                    if field not in valid_fields:
                        continue

                    # Validate specific fields
                    if field == 'category' and not self._validate_category(value):
                        raise ValueError(f"Invalid category: {value}")

                    if field == 'confidence' and not self._validate_confidence(value):
                        raise ValueError(f"Invalid confidence score: {value}")

                    if field == 'fact' and not value or not value.strip():
                        raise ValueError("Memory fact cannot be empty")

                    update_fields.append(f"{field} = ${param_index}")
                    params.append(value if field != 'metadata' else Json(value))
                    param_index += 1

                if not update_fields:
                    raise ValueError("No valid fields to update")

                # Add WHERE parameters
                params.extend([memory_id, user_id])

                cur.execute(
                    f"""
                    UPDATE user_memories
                    SET {', '.join(update_fields)}, updated_at = NOW()
                    WHERE id = ${param_index} AND user_id = ${param_index + 1} AND is_deleted = FALSE
                    RETURNING id, user_id, fact, category, confidence, source_type,
                              source_message_id, conversation_id, metadata, expires_at,
                              access_count, last_accessed_at, is_deleted, created_at, updated_at
                    """,
                    params
                )

                result = cur.fetchone()
                if result:
                    self.conn.commit()

                    # Convert to dict
                    memory = {
                        'id': result[0],
                        'user_id': result[1],
                        'fact': result[2],
                        'category': result[3],
                        'confidence': result[4],
                        'source_type': result[5],
                        'source_message_id': result[6],
                        'conversation_id': result[7],
                        'metadata': result[8],
                        'expires_at': result[9],
                        'access_count': result[10],
                        'last_accessed_at': result[11],
                        'is_deleted': result[12],
                        'created_at': result[13],
                        'updated_at': result[14]
                    }

                    logger.info(f"Updated memory {memory_id} for user {user_id}")
                    return memory

                return None

        except ValueError as e:
            logger.error(f"Validation error updating memory: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """
        Soft delete a memory

        Args:
            memory_id: Memory UUID
            user_id: User UUID for authorization

        Returns:
            True if deleted successfully
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_memories
                    SET is_deleted = TRUE, updated_at = NOW()
                    WHERE id = %s AND user_id = %s AND is_deleted = FALSE
                    """,
                    (memory_id, user_id)
                )

                rows_affected = cur.rowcount
                self.conn.commit()

                if rows_affected > 0:
                    logger.info(f"Deleted memory {memory_id} for user {user_id}")
                    return True

                return False

        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    # =========================================================================
    # Memory Search and Filtering
    # =========================================================================

    async def get_user_memories(
        self,
        user_id: str,
        category: Optional[str] = None,
        source_type: Optional[str] = None,
        confidence_min: Optional[float] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "DESC"
    ) -> List[Dict[str, Any]]:
        """
        Get user memories with filtering and pagination

        Args:
            user_id: User UUID
            category: Optional category filter
            source_type: Optional source type filter
            confidence_min: Optional minimum confidence filter
            search: Optional search term
            limit: Maximum number of results
            offset: Pagination offset
            sort_by: Sort field
            sort_order: Sort order (ASC/DESC)

        Returns:
            List of memory records
        """
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query
                query = """
                    SELECT id, user_id, fact, category, confidence, source_type,
                           source_message_id, conversation_id, metadata, expires_at,
                           access_count, last_accessed_at, is_deleted, created_at, updated_at
                    FROM user_memories
                    WHERE user_id = %s AND is_deleted = FALSE
                """
                params = [user_id]
                param_index = 2

                # Add filters
                if category:
                    query += f" AND category = ${param_index}"
                    params.append(category)
                    param_index += 1

                if source_type:
                    query += f" AND source_type = ${param_index}"
                    params.append(source_type)
                    param_index += 1

                if confidence_min is not None:
                    query += f" AND confidence >= ${param_index}"
                    params.append(confidence_min)
                    param_index += 1

                if search:
                    query += f" AND fact ILIKE ${param_index}"
                    params.append(f"%{search}%")
                    param_index += 1

                # Add sorting
                valid_sort_fields = ['created_at', 'updated_at', 'confidence', 'access_count', 'last_accessed_at']
                if sort_by not in valid_sort_fields:
                    sort_by = 'created_at'

                if sort_order.upper() not in ['ASC', 'DESC']:
                    sort_order = 'DESC'

                query += f" ORDER BY {sort_by} {sort_order}"
                query += f" LIMIT ${param_index} OFFSET ${param_index + 1}"
                params.extend([limit, offset])

                cur.execute(query, params)
                results = cur.fetchall()

                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get user memories: {e}")
            return []

    async def search_memories(
        self,
        user_id: str,
        query: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across memory facts

        Args:
            user_id: User UUID
            query: Search query
            category: Optional category filter
            limit: Maximum number of results

        Returns:
            List of matching memories
        """
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                search_query = """
                    SELECT id, user_id, fact, category, confidence, source_type,
                           source_message_id, conversation_id, metadata, expires_at,
                           access_count, last_accessed_at, is_deleted, created_at, updated_at,
                           ts_rank(to_tsvector('english', fact), plainto_tsquery('english', %s)) as rank
                    FROM user_memories
                    WHERE user_id = %s
                      AND is_deleted = FALSE
                      AND to_tsvector('english', fact) @@ plainto_tsquery('english', %s)
                """
                params = [query, user_id, query]
                param_index = 4

                if category:
                    search_query += f" AND category = ${param_index}"
                    params.append(category)
                    param_index += 1

                search_query += " ORDER BY rank DESC, confidence DESC LIMIT $" + str(param_index)
                params.append(limit)

                cur.execute(search_query, params)
                results = cur.fetchall()

                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    # =========================================================================
    # Memory Categories Management
    # =========================================================================

    async def get_memory_categories(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all memory categories for a user"""
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, user_id, name, description, color, icon, is_system_category, created_at, updated_at
                    FROM memory_categories
                    WHERE user_id = %s
                    ORDER BY is_system_category DESC, name ASC
                    """,
                    (user_id,)
                )

                results = cur.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get memory categories: {e}")
            return []

    async def initialize_default_categories(self, user_id: str) -> bool:
        """Initialize default system categories for a user"""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute("SELECT insert_default_categories(%s)", (user_id,))
                self.conn.commit()

                logger.info(f"Initialized default categories for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to initialize default categories: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _validate_category(self, category: str) -> bool:
        """Validate memory category"""
        valid_categories = [
            'priority', 'decision', 'context', 'preference',
            'relationship', 'goal', 'summary'
        ]
        return category in valid_categories

    def _validate_confidence(self, confidence: float) -> bool:
        """Validate confidence score"""
        return isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0

    def _validate_source_type(self, source_type: str) -> bool:
        """Validate source type"""
        valid_types = [
            'manual', 'extracted_from_chat', 'auto_summary', 'standing_instruction'
        ]
        return source_type in valid_types

    async def _find_duplicate_memory(self, user_id: str, fact: str) -> Optional[Dict[str, Any]]:
        """Find potential duplicate memories"""
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Simple similarity check - can be enhanced with more sophisticated algorithms
                cur.execute(
                    """
                    SELECT id, fact, confidence
                    FROM user_memories
                    WHERE user_id = %s
                      AND is_deleted = FALSE
                      AND (fact = %s OR fact ILIKE %s)
                    ORDER BY confidence DESC
                    LIMIT 1
                    """,
                    (user_id, fact, f"%{fact[:50]}%")
                )

                result = cur.fetchone()
                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to find duplicate memory: {e}")
            return None

    async def _track_access(self, memory_id: str) -> None:
        """Track memory access for analytics"""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_memories
                    SET access_count = access_count + 1, last_accessed_at = NOW()
                    WHERE id = %s
                    """,
                    (memory_id,)
                )
                self.conn.commit()

        except Exception as e:
            logger.error(f"Failed to track memory access: {e}")

    def _detect_and_mask_pii(self, text: str) -> tuple[str, bool]:
        """
        Detect and mask personally identifiable information

        Args:
            text: Text to analyze

        Returns:
            Tuple of (masked_text, pii_detected)
        """
        pii_detected = False
        masked_text = text

        # Email detection and masking
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, masked_text):
            masked_text = re.sub(email_pattern, '[EMAIL]', masked_text)
            pii_detected = True

        # Phone number detection (basic pattern)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        if re.search(phone_pattern, masked_text):
            masked_text = re.sub(phone_pattern, '[PHONE]', masked_text)
            pii_detected = True

        # SSN detection
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        if re.search(ssn_pattern, masked_text):
            masked_text = re.sub(ssn_pattern, '[SSN]', masked_text)
            pii_detected = True

        # Credit card detection (basic pattern)
        cc_pattern = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
        if re.search(cc_pattern, masked_text):
            masked_text = re.sub(cc_pattern, '[CARD]', masked_text)
            pii_detected = True

        return masked_text, pii_detected


# Global memory service instance
_memory_service = None


def get_memory_service() -> MemoryService:
    """Get or create memory service instance"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service