"""
Standing Instructions Service for ONYX

This service provides CRUD operations for standing instructions with context-aware
evaluation, conflict detection, and usage analytics.
"""

import os
import re
import uuid
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging

logger = logging.getLogger(__name__)


class InstructionService:
    """Service for standing instructions CRUD operations and management"""

    def __init__(self):
        """Initialize instruction service with database connection"""
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
                logger.info("Instruction service database connection established")
        except Exception as e:
            logger.error(f"Instruction service database connection failed: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Instruction service database connection closed")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    # =========================================================================
    # Standing Instructions CRUD Operations
    # =========================================================================

    async def create_instruction(
        self,
        user_id: str,
        instruction_text: str,
        category: str,
        priority: int = 5,
        enabled: bool = True,
        context_hints: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new standing instruction

        Args:
            user_id: User UUID
            instruction_text: Instruction content (1-500 characters)
            category: Instruction category
            priority: Priority level (1-10)
            enabled: Whether instruction is active
            context_hints: Optional context metadata

        Returns:
            Created instruction record or None if failed
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                # Validate inputs
                if not instruction_text or not instruction_text.strip():
                    raise ValueError("Instruction text cannot be empty")

                if len(instruction_text) > 500:
                    raise ValueError("Instruction text cannot exceed 500 characters")

                if not 1 <= priority <= 10:
                    raise ValueError("Priority must be between 1 and 10")

                valid_categories = ['behavior', 'communication', 'decision', 'security', 'workflow']
                if category not in valid_categories:
                    raise ValueError(f"Category must be one of: {valid_categories}")

                # Check user's instruction limit
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM standing_instructions
                    WHERE user_id = %s AND enabled = TRUE
                """, (user_id,))
                result = cur.fetchone()
                if result and result['count'] >= 100:  # Limit to 100 active instructions per user
                    raise ValueError("Maximum number of active instructions (100) reached")

                # Create instruction
                cur.execute("""
                    INSERT INTO standing_instructions
                    (user_id, instruction_text, priority, category, enabled, context_hints)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, instruction_text, priority, category, enabled,
                             context_hints, usage_count, created_at, updated_at
                """, (
                    user_id,
                    instruction_text.strip(),
                    priority,
                    category,
                    enabled,
                    Json(context_hints or {})
                ))

                instruction = cur.fetchone()
                self.conn.commit()

                logger.info(f"Created instruction {instruction['id']} for user {user_id}")
                return dict(instruction)

        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"Failed to create instruction: {e}")
            raise

    async def get_instructions(
        self,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get instructions for a user with optional filtering

        Args:
            user_id: User UUID
            filters: Optional filter parameters

        Returns:
            List of instruction records
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                # Build query with filters
                query = """
                    SELECT id, user_id, instruction_text, priority, category, enabled,
                           context_hints, usage_count, last_used_at, created_at, updated_at
                    FROM standing_instructions
                    WHERE user_id = %s
                """
                params = [user_id]

                if filters:
                    if 'enabled' in filters:
                        query += " AND enabled = %s"
                        params.append(filters['enabled'])

                    if 'category' in filters:
                        query += " AND category = %s"
                        params.append(filters['category'])

                    if 'priority_min' in filters:
                        query += " AND priority >= %s"
                        params.append(filters['priority_min'])

                    if 'priority_max' in filters:
                        query += " AND priority <= %s"
                        params.append(filters['priority_max'])

                    if 'search' in filters:
                        query += " AND instruction_text ILIKE %s"
                        params.append(f"%{filters['search']}%")

                # Add ordering
                sort_by = filters.get('sort_by', 'priority')
                sort_order = filters.get('sort_order', 'DESC')

                valid_sort_fields = ['priority', 'usage_count', 'last_used_at', 'created_at', 'updated_at']
                if sort_by in valid_sort_fields:
                    query += f" ORDER BY {sort_by} {sort_order}"
                else:
                    query += " ORDER BY priority DESC, usage_count DESC"

                # Add limit and offset
                if 'limit' in filters:
                    query += " LIMIT %s"
                    params.append(filters['limit'])

                if 'offset' in filters:
                    query += " OFFSET %s"
                    params.append(filters['offset'])

                cur.execute(query, params)
                instructions = cur.fetchall()

                return [dict(instruction) for instruction in instructions]

        except Exception as e:
            logger.error(f"Failed to get instructions: {e}")
            raise

    async def get_instruction_by_id(
        self,
        user_id: str,
        instruction_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific instruction by ID

        Args:
            user_id: User UUID
            instruction_id: Instruction UUID

        Returns:
            Instruction record or None if not found
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, instruction_text, priority, category, enabled,
                           context_hints, usage_count, last_used_at, created_at, updated_at
                    FROM standing_instructions
                    WHERE id = %s AND user_id = %s
                """, (instruction_id, user_id))

                instruction = cur.fetchone()
                return dict(instruction) if instruction else None

        except Exception as e:
            logger.error(f"Failed to get instruction {instruction_id}: {e}")
            raise

    async def update_instruction(
        self,
        user_id: str,
        instruction_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing instruction

        Args:
            user_id: User UUID
            instruction_id: Instruction UUID
            updates: Fields to update

        Returns:
            Updated instruction record or None if failed
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                # Validate updates
                if 'instruction_text' in updates:
                    text = updates['instruction_text']
                    if not text or not text.strip():
                        raise ValueError("Instruction text cannot be empty")
                    if len(text) > 500:
                        raise ValueError("Instruction text cannot exceed 500 characters")
                    updates['instruction_text'] = text.strip()

                if 'priority' in updates:
                    priority = updates['priority']
                    if not 1 <= priority <= 10:
                        raise ValueError("Priority must be between 1 and 10")

                if 'category' in updates:
                    valid_categories = ['behavior', 'communication', 'decision', 'security', 'workflow']
                    if updates['category'] not in valid_categories:
                        raise ValueError(f"Category must be one of: {valid_categories}")

                if 'context_hints' in updates:
                    updates['context_hints'] = Json(updates['context_hints'])

                # Build dynamic update query
                set_clauses = []
                params = []

                for field, value in updates.items():
                    set_clauses.append(f"{field} = %s")
                    params.append(value)

                if not set_clauses:
                    raise ValueError("No valid fields to update")

                params.extend([instruction_id, user_id])

                cur.execute(f"""
                    UPDATE standing_instructions
                    SET {', '.join(set_clauses)}
                    WHERE id = %s AND user_id = %s
                    RETURNING id, user_id, instruction_text, priority, category, enabled,
                             context_hints, usage_count, last_used_at, created_at, updated_at
                """, params)

                instruction = cur.fetchone()
                self.conn.commit()

                if instruction:
                    logger.info(f"Updated instruction {instruction_id} for user {user_id}")
                    return dict(instruction)
                else:
                    logger.warning(f"Instruction {instruction_id} not found for user {user_id}")
                    return None

        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"Failed to update instruction {instruction_id}: {e}")
            raise

    async def delete_instruction(
        self,
        user_id: str,
        instruction_id: str,
        soft_delete: bool = True
    ) -> bool:
        """
        Delete an instruction

        Args:
            user_id: User UUID
            instruction_id: Instruction UUID
            soft_delete: Whether to soft delete (disable) or hard delete

        Returns:
            True if deleted, False if not found
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                if soft_delete:
                    cur.execute("""
                        UPDATE standing_instructions
                        SET enabled = FALSE
                        WHERE id = %s AND user_id = %s
                    """, (instruction_id, user_id))
                else:
                    cur.execute("""
                        DELETE FROM standing_instructions
                        WHERE id = %s AND user_id = %s
                    """, (instruction_id, user_id))

                self.conn.commit()
                deleted = cur.rowcount > 0

                if deleted:
                    logger.info(f"Deleted instruction {instruction_id} for user {user_id}")
                else:
                    logger.warning(f"Instruction {instruction_id} not found for user {user_id}")

                return deleted

        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"Failed to delete instruction {instruction_id}: {e}")
            raise

    async def bulk_operation(
        self,
        user_id: str,
        operation: str,
        instruction_ids: List[str],
        value: Any = None
    ) -> Dict[str, Any]:
        """
        Perform bulk operations on instructions

        Args:
            user_id: User UUID
            operation: Operation type (enable, disable, delete, update_priority)
            instruction_ids: List of instruction UUIDs
            value: Value for update_priority operation

        Returns:
            Result with success count and errors
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                results = {
                    'success_count': 0,
                    'failed_count': 0,
                    'errors': []
                }

                for instruction_id in instruction_ids:
                    try:
                        if operation == 'enable':
                            cur.execute("""
                                UPDATE standing_instructions
                                SET enabled = TRUE
                                WHERE id = %s AND user_id = %s
                            """, (instruction_id, user_id))

                        elif operation == 'disable':
                            cur.execute("""
                                UPDATE standing_instructions
                                SET enabled = FALSE
                                WHERE id = %s AND user_id = %s
                            """, (instruction_id, user_id))

                        elif operation == 'delete':
                            cur.execute("""
                                DELETE FROM standing_instructions
                                WHERE id = %s AND user_id = %s
                            """, (instruction_id, user_id))

                        elif operation == 'update_priority':
                            if not isinstance(value, int) or not 1 <= value <= 10:
                                raise ValueError("Priority must be between 1 and 10")
                            cur.execute("""
                                UPDATE standing_instructions
                                SET priority = %s
                                WHERE id = %s AND user_id = %s
                            """, (value, instruction_id, user_id))

                        else:
                            raise ValueError(f"Invalid operation: {operation}")

                        if cur.rowcount > 0:
                            results['success_count'] += 1
                        else:
                            results['failed_count'] += 1
                            results['errors'].append({
                                'instruction_id': instruction_id,
                                'error': 'Instruction not found'
                            })

                    except Exception as e:
                        results['failed_count'] += 1
                        results['errors'].append({
                            'instruction_id': instruction_id,
                            'error': str(e)
                        })

                self.conn.commit()
                logger.info(f"Bulk {operation} completed for user {user_id}: {results['success_count']} success, {results['failed_count']} failed")
                return results

        except Exception as e:
            if self.conn:
                self.conn.rollback()
            logger.error(f"Failed bulk operation {operation}: {e}")
            raise

    # =========================================================================
    # Instruction Evaluation and Processing
    # =========================================================================

    async def evaluate_instructions(
        self,
        user_id: str,
        conversation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate and rank relevant instructions for conversation context

        Args:
            user_id: User UUID
            conversation_context: Context information for evaluation

        Returns:
            Dictionary with active instructions and metadata
        """
        start_time = datetime.now()

        try:
            self.connect()
            with self.conn.cursor() as cur:
                # Get active instructions using the optimized function
                cur.execute("""
                    SELECT * FROM get_active_instructions(%s, TRUE, NULL, NULL)
                """, (user_id,))

                all_instructions = cur.fetchall()

                # Filter based on context relevance
                relevant_instructions = []
                applied_instruction_ids = []

                for instruction in all_instructions:
                    if self._is_instruction_relevant(dict(instruction), conversation_context):
                        relevant_instructions.append(dict(instruction))
                        applied_instruction_ids.append(instruction['id'])

                # Sort by relevance score (already calculated in the function)
                relevant_instructions.sort(key=lambda x: x['relevance_score'], reverse=True)

                # Update usage statistics
                if applied_instruction_ids:
                    await self._update_usage_stats(applied_instruction_ids)

                # Detect conflicts
                conflicts = await self.detect_conflicts(user_id)

                evaluation_time = (datetime.now() - start_time).total_seconds() * 1000

                result = {
                    'active_instructions': relevant_instructions,
                    'evaluation_time_ms': evaluation_time,
                    'total_evaluated': len(all_instructions),
                    'conflicts_detected': conflicts,
                    'applied_count': len(relevant_instructions)
                }

                logger.info(f"Instruction evaluation completed for user {user_id}: {len(relevant_instructions)} applied in {evaluation_time:.2f}ms")
                return result

        except Exception as e:
            logger.error(f"Failed to evaluate instructions for user {user_id}: {e}")
            raise

    def _is_instruction_relevant(
        self,
        instruction: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if instruction applies to current conversation context

        Args:
            instruction: Instruction record
            context: Conversation context

        Returns:
            True if instruction is relevant
        """
        try:
            context_hints = instruction.get('context_hints', {})

            # Check topic relevance
            if 'topics' in context_hints and context_hints['topics']:
                message_content = context.get('messageContent', '').lower()
                has_matching_topic = any(
                    topic.lower() in message_content
                    for topic in context_hints['topics']
                )
                if not has_matching_topic:
                    return False

            # Check agent mode relevance
            if 'agentModes' in context_hints and context_hints['agentModes']:
                agent_mode = context.get('agentMode')
                if agent_mode not in context_hints['agentModes']:
                    return False

            # Check confidence threshold
            if 'minConfidence' in context_hints:
                confidence = context.get('confidence', 0)
                if confidence < context_hints['minConfidence']:
                    return False

            # Check keywords
            if 'keywords' in context_hints and context_hints['keywords']:
                message_content = context.get('messageContent', '').lower()
                has_matching_keyword = any(
                    keyword.lower() in message_content
                    for keyword in context_hints['keywords']
                )
                if not has_matching_keyword:
                    return False

            # Check exclude topics
            if 'excludeTopics' in context_hints and context_hints['excludeTopics']:
                message_content = context.get('messageContent', '').lower()
                has_excluded_topic = any(
                    topic.lower() in message_content
                    for topic in context_hints['excludeTopics']
                )
                if has_excluded_topic:
                    return False

            # Check category-specific conditions
            category = instruction.get('category')
            if category == 'security':
                return (context.get('involvesSensitiveData', False) or
                       context.get('requiresSecureHandling', False))
            elif category == 'workflow':
                return (context.get('isAgentMode', False) or
                       context.get('isTaskExecution', False))
            elif category == 'communication':
                return True  # Communication instructions always relevant
            else:
                return True

        except Exception as e:
            logger.warning(f"Error checking instruction relevance: {e}")
            return True  # Default to relevant if there's an error

    async def _update_usage_stats(self, instruction_ids: List[str]):
        """Update usage statistics for applied instructions"""
        try:
            with self.conn.cursor() as cur:
                for instruction_id in instruction_ids:
                    cur.execute("""
                        UPDATE standing_instructions
                        SET usage_count = usage_count + 1,
                            last_used_at = NOW()
                        WHERE id = %s
                    """, (instruction_id,))

                self.conn.commit()
                logger.debug(f"Updated usage stats for {len(instruction_ids)} instructions")

        except Exception as e:
            logger.error(f"Failed to update usage stats: {e}")
            # Don't raise - this is non-critical

    async def detect_conflicts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Detect conflicts between instructions

        Args:
            user_id: User UUID

        Returns:
            List of conflict records
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM detect_instruction_conflicts(%s)", (user_id,))
                conflicts = cur.fetchall()

                return [dict(conflict) for conflict in conflicts]

        except Exception as e:
            logger.error(f"Failed to detect conflicts for user {user_id}: {e}")
            return []

    # =========================================================================
    # Analytics and Statistics
    # =========================================================================

    async def get_instruction_analytics(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get analytics data for user's instructions

        Args:
            user_id: User UUID

        Returns:
            Analytics data by category
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute("SELECT * FROM instruction_analytics WHERE user_id = %s", (user_id,))
                analytics = cur.fetchall()

                return [dict(analytic) for analytic in analytics]

        except Exception as e:
            logger.error(f"Failed to get instruction analytics for user {user_id}: {e}")
            raise

    async def get_usage_stats(
        self,
        user_id: str,
        instruction_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a specific instruction

        Args:
            user_id: User UUID
            instruction_id: Instruction UUID
            days: Number of days to analyze

        Returns:
            Usage statistics
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                # Get instruction details
                cur.execute("""
                    SELECT usage_count, last_used_at, created_at
                    FROM standing_instructions
                    WHERE id = %s AND user_id = %s
                """, (instruction_id, user_id))

                instruction = cur.fetchone()
                if not instruction:
                    return {}

                # Calculate basic stats
                days_since_creation = (datetime.now() - instruction['created_at']).days
                avg_daily_usage = instruction['usage_count'] / max(days_since_creation, 1)

                return {
                    'instruction_id': instruction_id,
                    'total_usage': instruction['usage_count'],
                    'last_used_at': instruction['last_used_at'],
                    'created_at': instruction['created_at'],
                    'days_since_creation': days_since_creation,
                    'avg_daily_usage': avg_daily_usage
                }

        except Exception as e:
            logger.error(f"Failed to get usage stats for instruction {instruction_id}: {e}")
            raise

    # =========================================================================
    # Validation and Testing
    # =========================================================================

    def validate_instruction(self, instruction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate instruction data

        Args:
            instruction_data: Instruction data to validate

        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []

        # Validate instruction_text
        instruction_text = instruction_data.get('instruction_text', '')
        if not instruction_text or not instruction_text.strip():
            errors.append({
                'field': 'instruction_text',
                'message': 'Instruction text cannot be empty',
                'code': 'REQUIRED_FIELD'
            })
        elif len(instruction_text) > 500:
            errors.append({
                'field': 'instruction_text',
                'message': 'Instruction text cannot exceed 500 characters',
                'code': 'MAX_LENGTH_EXCEEDED'
            })

        # Validate priority
        priority = instruction_data.get('priority')
        if priority is not None:
            if not isinstance(priority, int) or not 1 <= priority <= 10:
                errors.append({
                    'field': 'priority',
                    'message': 'Priority must be an integer between 1 and 10',
                    'code': 'INVALID_RANGE'
                })

        # Validate category
        category = instruction_data.get('category')
        valid_categories = ['behavior', 'communication', 'decision', 'security', 'workflow']
        if category not in valid_categories:
            errors.append({
                'field': 'category',
                'message': f'Category must be one of: {valid_categories}',
                'code': 'INVALID_VALUE'
            })

        # Check for potentially problematic instruction text
        instruction_lower = instruction_text.lower()
        problematic_patterns = [
            ('always', 'Consider using "typically" or "generally" instead of "always" for more flexibility'),
            ('never', 'Consider using "avoid" or "rarely" instead of "never" for more flexibility'),
            ('must', 'Consider using "should" or "preferably" instead of "must" for less rigidity')
        ]

        for pattern, suggestion in problematic_patterns:
            if pattern in instruction_lower:
                warnings.append(suggestion)

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }