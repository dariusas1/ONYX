"""
Standing Instructions Service for ONYX

This service provides CRUD operations for standing instructions with
categorization, priority-based ordering, and context-aware evaluation.

Story 4-2: Standing Instructions Management
"""

import os
import uuid
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging

logger = logging.getLogger(__name__)


class StandingInstructionsService:
    """Service for standing instructions CRUD operations and management"""

    def __init__(self):
        """Initialize standing instructions service"""
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

    def _get_connection(self):
        """Get database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.connection_string)
        return self.conn

    def _detect_and_mask_pii(self, text: str) -> Tuple[str, bool]:
        """
        Detect and mask PII in instruction text

        Args:
            text: Text to check for PII

        Returns:
            Tuple of (masked_text, has_pii)
        """
        has_pii = False
        masked_text = text

        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, text):
            has_pii = True
            masked_text = re.sub(email_pattern, '[EMAIL_REDACTED]', masked_text)

        # Phone pattern (basic)
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        if re.search(phone_pattern, text):
            has_pii = True
            masked_text = re.sub(phone_pattern, '[PHONE_REDACTED]', masked_text)

        # SSN pattern
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        if re.search(ssn_pattern, text):
            has_pii = True
            masked_text = re.sub(ssn_pattern, '[SSN_REDACTED]', masked_text)

        return masked_text, has_pii

    def _validate_instruction_data(self, instruction_text: str, category: str, priority: int, context_hints: List[str]) -> None:
        """
        Validate instruction data

        Args:
            instruction_text: The instruction text
            category: Instruction category
            priority: Priority level (1-10)
            context_hints: List of context hints

        Raises:
            ValueError: If validation fails
        """
        # Validate instruction text
        if not instruction_text or not instruction_text.strip():
            raise ValueError("Instruction text cannot be empty")

        if len(instruction_text.strip()) > 500:
            raise ValueError("Instruction text cannot exceed 500 characters")

        # Check for PII
        masked_text, has_pii = self._detect_and_mask_pii(instruction_text)
        if has_pii:
            logger.warning(f"PII detected in instruction text: {masked_text[:100]}...")

        # Validate category
        valid_categories = ['workflow', 'decision', 'communication', 'security', 'general']
        if category not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {valid_categories}")

        # Validate priority
        if not isinstance(priority, int) or priority < 1 or priority > 10:
            raise ValueError("Priority must be an integer between 1 and 10")

        # Validate context hints
        if context_hints and len(context_hints) > 10:
            raise ValueError("Cannot have more than 10 context hints")

    async def create_instruction(
        self,
        user_id: str,
        instruction_text: str,
        category: str,
        priority: int = 5,
        context_hints: Optional[List[str]] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new standing instruction

        Args:
            user_id: User UUID
            instruction_text: The instruction text (1-500 characters)
            category: Instruction category
            priority: Priority level (1-10)
            context_hints: Optional context hints for filtering
            enabled: Whether instruction is enabled

        Returns:
            Created instruction data
        """
        # Validate input
        context_hints = context_hints or []
        self._validate_instruction_data(instruction_text, category, priority, context_hints)

        # Generate instruction ID
        instruction_id = str(uuid.uuid4())

        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Insert instruction
                query = """
                INSERT INTO standing_instructions
                (id, user_id, instruction_text, category, priority, context_hints, enabled, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id, user_id, instruction_text, category, priority, context_hints, enabled,
                         usage_count, last_used_at, created_at, updated_at
                """
                cur.execute(query, (
                    instruction_id, user_id, instruction_text.strip(),
                    category, priority, context_hints, enabled
                ))

                result = dict(cur.fetchone())
                logger.info(f"Created standing instruction {instruction_id} for user {user_id}")
                return result

        except Exception as e:
            logger.error(f"Failed to create standing instruction: {e}")
            raise

    async def get_user_instructions(
        self,
        user_id: str,
        category: Optional[str] = None,
        enabled_only: bool = True,
        sort_by: str = "priority",
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user's standing instructions with filtering and sorting

        Args:
            user_id: User UUID
            category: Optional category filter
            enabled_only: Whether to return only enabled instructions
            sort_by: Sort order ('priority', 'usage', 'category', 'created')
            limit: Optional limit on number of results

        Returns:
            List of instructions
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query
                query = "SELECT * FROM standing_instructions WHERE user_id = %s"
                params = [user_id]

                # Add filters
                if enabled_only:
                    query += " AND enabled = TRUE"

                if category:
                    query += " AND category = %s"
                    params.append(category)

                # Add sorting
                if sort_by == "priority":
                    query += " ORDER BY priority DESC, usage_count DESC, created_at DESC"
                elif sort_by == "usage":
                    query += " ORDER BY usage_count DESC, last_used_at DESC"
                elif sort_by == "category":
                    query += " ORDER BY category, priority DESC"
                elif sort_by == "created":
                    query += " ORDER BY created_at DESC"
                else:
                    query += " ORDER BY priority DESC, usage_count DESC"

                # Add limit
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)

                cur.execute(query, params)
                results = [dict(row) for row in cur.fetchall()]

                logger.debug(f"Retrieved {len(results)} instructions for user {user_id}")
                return results

        except Exception as e:
            logger.error(f"Failed to get user instructions: {e}")
            raise

    async def update_instruction(
        self,
        instruction_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing standing instruction

        Args:
            instruction_id: Instruction UUID
            user_id: User UUID (for authorization)
            updates: Dictionary of fields to update

        Returns:
            Updated instruction data
        """
        # Validate updates
        valid_fields = ['instruction_text', 'category', 'priority', 'context_hints', 'enabled']
        update_fields = []
        params = []

        for field, value in updates.items():
            if field not in valid_fields:
                raise ValueError(f"Invalid field: {field}")

            if field == 'instruction_text':
                if 'category' in updates:
                    self._validate_instruction_data(
                        value, updates['category'],
                        updates.get('priority', 5),
                        updates.get('context_hints', [])
                    )

            update_fields.append(f"{field} = %s")
            params.append(value)

        if not update_fields:
            raise ValueError("No valid fields to update")

        params.extend([instruction_id, user_id])

        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = f"""
                UPDATE standing_instructions
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                RETURNING id, user_id, instruction_text, category, priority, context_hints, enabled,
                         usage_count, last_used_at, created_at, updated_at
                """
                cur.execute(query, params)
                result = cur.fetchone()

                if not result:
                    raise ValueError("Instruction not found or access denied")

                updated_instruction = dict(result)
                logger.info(f"Updated standing instruction {instruction_id}")
                return updated_instruction

        except Exception as e:
            logger.error(f"Failed to update standing instruction: {e}")
            raise

    async def delete_instruction(self, instruction_id: str, user_id: str) -> bool:
        """
        Delete a standing instruction (soft delete)

        Args:
            instruction_id: Instruction UUID
            user_id: User UUID (for authorization)

        Returns:
            True if deleted successfully
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                query = """
                UPDATE standing_instructions
                SET enabled = FALSE, updated_at = NOW()
                WHERE id = %s AND user_id = %s
                """
                cur.execute(query, (instruction_id, user_id))

                deleted = cur.rowcount > 0
                if deleted:
                    logger.info(f"Deleted standing instruction {instruction_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete standing instruction: {e}")
            raise

    async def get_instruction_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage analytics for user's standing instructions

        Args:
            user_id: User UUID

        Returns:
            Analytics data
        """
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get overall stats
                stats_query = """
                SELECT
                    COUNT(*) as total_instructions,
                    COUNT(CASE WHEN enabled = TRUE THEN 1 END) as enabled_instructions,
                    COUNT(CASE WHEN enabled = FALSE THEN 1 END) as disabled_instructions,
                    SUM(usage_count) as total_usage,
                    AVG(usage_count) as avg_usage,
                    MAX(usage_count) as max_usage,
                    MAX(last_used_at) as last_used
                FROM standing_instructions
                WHERE user_id = %s
                """
                cur.execute(stats_query, (user_id,))
                overall_stats = dict(cur.fetchone())

                # Get category breakdown
                category_query = """
                SELECT
                    category,
                    COUNT(*) as count,
                    SUM(usage_count) as total_usage,
                    AVG(priority) as avg_priority
                FROM standing_instructions
                WHERE user_id = %s AND enabled = TRUE
                GROUP BY category
                ORDER BY count DESC
                """
                cur.execute(category_query, (user_id,))
                category_stats = [dict(row) for row in cur.fetchall()]

                # Get top used instructions
                top_query = """
                SELECT id, instruction_text, category, priority, usage_count, last_used_at
                FROM standing_instructions
                WHERE user_id = %s AND enabled = TRUE
                ORDER BY usage_count DESC, last_used_at DESC
                LIMIT 5
                """
                cur.execute(top_query, (user_id,))
                top_instructions = [dict(row) for row in cur.fetchall()]

                analytics = {
                    "overall_stats": overall_stats,
                    "category_breakdown": category_stats,
                    "top_instructions": top_instructions,
                    "generated_at": datetime.utcnow().isoformat()
                }

                return analytics

        except Exception as e:
            logger.error(f"Failed to get instruction analytics: {e}")
            raise

    async def bulk_update_status(
        self,
        instruction_ids: List[str],
        user_id: str,
        enabled: bool
    ) -> int:
        """
        Bulk update enabled status for multiple instructions

        Args:
            instruction_ids: List of instruction UUIDs
            user_id: User UUID (for authorization)
            enabled: New enabled status

        Returns:
            Number of instructions updated
        """
        if not instruction_ids:
            return 0

        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                # Create placeholders for IN clause
                placeholders = ','.join(['%s'] * len(instruction_ids))
                params = [enabled, user_id] + instruction_ids

                query = f"""
                UPDATE standing_instructions
                SET enabled = %s, updated_at = NOW()
                WHERE user_id = %s AND id IN ({placeholders})
                """
                cur.execute(query, params)

                updated_count = cur.rowcount
                logger.info(f"Bulk updated {updated_count} instructions for user {user_id}")
                return updated_count

        except Exception as e:
            logger.error(f"Failed to bulk update instructions: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Standing instructions service database connection closed")