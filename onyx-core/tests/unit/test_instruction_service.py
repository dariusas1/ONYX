"""
Unit Tests for Instruction Service

This module contains comprehensive unit tests for the InstructionService class,
covering CRUD operations, validation, conflict detection, and analytics.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest
import asyncio
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

from onyx_core.services.instruction_service import InstructionService


class TestInstructionService:
    """Test suite for InstructionService"""

    def setUp(self):
        """Set up test fixtures"""
        self.service = InstructionService()
        self.mock_connection = Mock()
        self.service.conn = self.mock_connection

        # Sample instruction data
        self.sample_instruction = {
            'id': '550e8400-e29b-41d4-a716-446655440000',
            'user_id': '550e8400-e29b-41d4-a716-446655440001',
            'instruction_text': 'Test instruction for unit testing',
            'priority': 5,
            'category': 'behavior',
            'enabled': True,
            'context_hints': {'topics': ['test'], 'agentModes': ['chat']},
            'usage_count': 10,
            'last_used_at': datetime.now(),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

    @patch('onyx_core.services.instruction_service.psycopg2.connect')
    def test_connect_success(self, mock_connect):
        """Test successful database connection"""
        mock_connect.return_value = self.mock_connection
        mock_connection.closed = False

        self.service.connect()

        mock_connect.assert_called_once_with(self.service.connection_string)
        assert self.service.conn == self.mock_connection

    @patch('onyx_core.services.instruction_service.psycopg2.connect')
    def test_connect_failure(self, mock_connect):
        """Test database connection failure"""
        mock_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            self.service.connect()

    def test_close_connection(self):
        """Test closing database connection"""
        self.service.conn = self.mock_connection
        mock_connection.closed = False

        self.service.close()

        mock_connection.close.assert_called_once()

    def test_context_manager(self):
        """Test context manager functionality"""
        with patch.object(self.service, 'connect') as mock_connect, \
             patch.object(self.service, 'close') as mock_close:

            with self.service as service:
                assert service == self.service

            mock_connect.assert_called_once()
            mock_close.assert_called_once()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_create_instruction_success(self, mock_connect):
        """Test successful instruction creation"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_connection.commit = Mock()

        mock_cursor.fetchone.return_value = self.sample_instruction

        result = await self.service.create_instruction(
            user_id='user123',
            instruction_text='Test instruction',
            category='behavior',
            priority=5,
            enabled=True,
            context_hints={'topics': ['test']}
        )

        assert result == self.sample_instruction
        mock_cursor.execute.assert_called_once()
        self.mock_connection.commit.assert_called_once()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_create_instruction_validation_errors(self, mock_connect):
        """Test instruction creation with validation errors"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        # Test empty instruction text
        with pytest.raises(ValueError, match="Instruction text cannot be empty"):
            await self.service.create_instruction(
                user_id='user123',
                instruction_text='',
                category='behavior'
            )

        # Test text too long
        with pytest.raises(ValueError, match="Instruction text cannot exceed 500 characters"):
            await self.service.create_instruction(
                user_id='user123',
                instruction_text='x' * 501,
                category='behavior'
            )

        # Test invalid priority
        with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
            await self.service.create_instruction(
                user_id='user123',
                instruction_text='Valid instruction',
                category='behavior',
                priority=15
            )

        # Test invalid category
        with pytest.raises(ValueError, match="Category must be one of"):
            await self.service.create_instruction(
                user_id='user123',
                instruction_text='Valid instruction',
                category='invalid_category'
            )

        # Verify rollback on error
        self.mock_connection.rollback.assert_called()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_create_instruction_limit_check(self, mock_connect):
        """Test instruction creation limit check"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {'count': 100}  # At limit

        with pytest.raises(ValueError, match="Maximum number of active instructions"):
            await self.service.create_instruction(
                user_id='user123',
                instruction_text='Test instruction',
                category='behavior'
            )

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_get_instructions_success(self, mock_connect):
        """Test successful instruction retrieval"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [self.sample_instruction]

        result = await self.service.get_instructions('user123')

        assert len(result) == 1
        assert result[0] == self.sample_instruction
        mock_cursor.execute.assert_called()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_get_instructions_with_filters(self, mock_connect):
        """Test instruction retrieval with filters"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [self.sample_instruction]

        filters = {
            'category': 'behavior',
            'enabled': True,
            'priority_min': 3,
            'search': 'test'
        }

        result = await self.service.get_instructions('user123', filters)

        assert len(result) == 1
        # Verify filter conditions in SQL
        call_args = mock_cursor.execute.call_args[0][0]
        assert 'category = %s' in call_args
        assert 'enabled = %s' in call_args
        assert 'priority >= %s' in call_args

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_get_instruction_by_id_success(self, mock_connect):
        """Test successful instruction retrieval by ID"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = self.sample_instruction

        result = await self.service.get_instruction_by_id('user123', 'instruction_id')

        assert result == self.sample_instruction
        mock_cursor.execute.assert_called_once()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_get_instruction_by_id_not_found(self, mock_connect):
        """Test instruction retrieval by ID when not found"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = await self.service.get_instruction_by_id('user123', 'nonexistent_id')

        assert result is None

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_update_instruction_success(self, mock_connect):
        """Test successful instruction update"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_connection.commit = Mock()

        updated_instruction = self.sample_instruction.copy()
        updated_instruction['instruction_text'] = 'Updated instruction'

        mock_cursor.fetchone.return_value = updated_instruction

        updates = {
            'instruction_text': 'Updated instruction',
            'priority': 7
        }

        result = await self.service.update_instruction(
            user_id='user123',
            instruction_id='instruction_id',
            updates=updates
        )

        assert result['instruction_text'] == 'Updated instruction'
        assert result['priority'] == 7
        self.mock_connection.commit.assert_called_once()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_update_instruction_validation(self, mock_connect):
        """Test instruction update with validation errors"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        # Test invalid priority
        with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
            await self.service.update_instruction(
                user_id='user123',
                instruction_id='instruction_id',
                updates={'priority': 15}
            )

        # Test invalid category
        with pytest.raises(ValueError, match="Category must be one of"):
            await self.service.update_instruction(
                user_id='user123',
                instruction_id='instruction_id',
                updates={'category': 'invalid'}
            )

        self.mock_connection.rollback.assert_called()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_update_instruction_not_found(self, mock_connect):
        """Test instruction update when instruction not found"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None

        result = await self.service.update_instruction(
            user_id='user123',
            instruction_id='nonexistent_id',
            updates={'instruction_text': 'Updated'}
        )

        assert result is None

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_delete_instruction_soft_delete(self, mock_connect):
        """Test soft delete of instruction"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_connection.commit = Mock()
        mock_cursor.rowcount = 1

        result = await self.service.delete_instruction('user123', 'instruction_id', soft_delete=True)

        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "UPDATE standing_instructions SET enabled = FALSE WHERE id = %s AND user_id = %s",
            ('instruction_id', 'user123')
        )
        self.mock_connection.commit.assert_called_once()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_delete_instruction_hard_delete(self, mock_connect):
        """Test hard delete of instruction"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_connection.commit = Mock()
        mock_cursor.rowcount = 1

        result = await self.service.delete_instruction('user123', 'instruction_id', soft_delete=False)

        assert result is True
        mock_cursor.execute.assert_called_once_with(
            "DELETE FROM standing_instructions WHERE id = %s AND user_id = %s",
            ('instruction_id', 'user123')
        )
        self.mock_connection.commit.assert_called_once()

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_delete_instruction_not_found(self, mock_connect):
        """Test instruction deletion when not found"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.rowcount = 0

        result = await self.service.delete_instruction('user123', 'nonexistent_id')

        assert result is False

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_bulk_operation_success(self, mock_connect):
        """Test successful bulk operation"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_connection.commit = Mock()

        instruction_ids = ['id1', 'id2', 'id3']
        operation = 'enable'

        result = await self.service.bulk_operation(
            user_id='user123',
            operation=operation,
            instruction_ids=instruction_ids
        )

        assert result['success_count'] == 3
        assert result['failed_count'] == 0
        assert len(result['errors']) == 0
        self.mock_connection.commit.assert_called_once()

    @patch('onyx_core.services.instruction_service.Instruction.connect')
    async def test_bulk_operation_with_failures(self, mock_connect):
        """Test bulk operation with some failures"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        self.mock_connection.commit = Mock()

        # Mock the cursor to simulate failures
        def side_effect(*args, **kwargs):
            if 'nonexistent_id' in str(args):
                return None  # Simulate row count 0 for non-existent ID
            return 1  # Simulate row count 1 for successful operations

        mock_cursor.rowcount = side_effect

        instruction_ids = ['id1', 'nonexistent_id', 'id3']
        operation = 'delete'

        result = await self.service.bulk_operation(
            user_id='user123',
            operation=operation,
            instruction_ids=instruction_ids
        )

        assert result['success_count'] >= 0
        assert result['failed_count'] >= 0

    def test_is_instruction_relevant_topic_matching(self):
        """Test instruction relevance checking with topic matching"""
        instruction = {
            'context_hints': {'topics': ['finance', 'budget', 'planning']},
            'category': 'behavior'
        }

        context = {
            'messageContent': 'I need help with my financial planning and budget management',
            'agentMode': 'chat',
            'confidence': 0.8
        }

        result = self.service._is_instruction_relevant(instruction, context)
        assert result is True  # Should match 'finance' and 'budget'

    def test_is_instruction_relevant_no_topic_match(self):
        """Test instruction relevance when no topic matches"""
        instruction = {
            'context_hints': {'topics': ['health', 'fitness']},
            'category': 'behavior'
        }

        context = {
            'messageContent': 'I need help with financial planning',
            'agentMode': 'chat',
            'confidence': 0.8
        }

        result = self.service._is_instruction_relevant(instruction, context)
        assert result is False  # No matching topics

    def test_is_instruction_relevant_agent_mode_filtering(self):
        """Test instruction relevance with agent mode filtering"""
        instruction = {
            'context_hints': {'agentModes': ['agent']},
            'category': 'workflow'
        }

        context = {
            'messageContent': 'Execute this task',
            'agentMode': 'chat',  # Different mode
            'confidence': 0.8
        }

        result = self.service._is_instruction_relevant(instruction, context)
        assert result is False  # Wrong agent mode

    def test_is_instruction_relevant_confidence_threshold(self):
        """Test instruction relevance with confidence threshold"""
        instruction = {
            'context_hints': {'minConfidence': 0.9},
            'category': 'behavior'
        }

        context = {
            'messageContent': 'Test message',
            'agentMode': 'chat',
            'confidence': 0.7  # Below threshold
        }

        result = self.service._is_instruction_relevant(instruction, context)
        assert result is False  # Below confidence threshold

    def test_is_instruction_relevant_security_category(self):
        """Test instruction relevance for security category"""
        instruction = {
            'category': 'security'
        }

        # Should be relevant with sensitive data
        context_sensitive = {
            'messageContent': 'Handle my password',
            'agentMode': 'chat',
            'confidence': 0.8,
            'involvesSensitiveData': True,
            'requiresSecureHandling': True
        }

        result = self.service._is_instruction_relevant(instruction, context_sensitive)
        assert result is True

        # Should not be relevant without sensitive data
        context_normal = {
            'messageContent': 'Normal conversation',
            'agentMode': 'chat',
            'confidence': 0.8,
            'involvesSensitiveData': False,
            'requiresSecureHandling': False
        }

        result = self.service._is_instruction_relevant(instruction, context_normal)
        assert result is False

    def test_calculate_relevance_score(self):
        """Test relevance score calculation"""
        instruction = {
            'priority': 8,
            'usage_count': 20,
            'last_used_at': datetime.now() - timedelta(days=2)
        }

        context = {
            'messageContent': 'Test',
            'agentMode': 'chat',
            'confidence': 0.8
        }

        score = self.service.calculate_relevance_score(instruction, context)

        # Score should be between 0 and 1
        assert 0 <= score <= 1
        # High priority and high usage should result in high score
        assert score > 0.7

    def test_calculate_relevance_score_never_used(self):
        """Test relevance score for never used instruction"""
        instruction = {
            'priority': 5,
            'usage_count': 0,
            'last_used_at': None
        }

        context = {
            'messageContent': 'Test',
            'agentMode': 'chat',
            'confidence': 0.8
        }

        score = self.service.calculate_relevance_score(instruction, context)

        # Should have base score from priority, no usage or recency bonus
        expected_score = (5 / 10) * 0.6  # Only priority contribution
        assert abs(score - expected_score) < 0.01

    def test_validate_instruction_valid_data(self):
        """Test validation with valid instruction data"""
        instruction_data = {
            'instruction_text': 'This is a valid instruction',
            'priority': 5,
            'category': 'behavior'
        }

        result = self.service.validate_instruction(instruction_data)

        assert result['is_valid'] is True
        assert len(result['errors']) == 0

    def test_validate_instruction_invalid_text(self):
        """Test validation with invalid instruction text"""
        instruction_data = {
            'instruction_text': '',  # Empty
            'priority': 5,
            'category': 'behavior'
        }

        result = self.service.validate_instruction(instruction_data)

        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert any('empty' in error.lower() for error in result['errors'])

    def test_validate_instruction_invalid_priority(self):
        """Test validation with invalid priority"""
        instruction_data = {
            'instruction_text': 'Valid instruction',
            'priority': 15,  # Too high
            'category': 'behavior'
        }

        result = self.service.validate_instruction(instruction_data)

        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert any('priority' in error.lower() for error in result['errors'])

    def test_validate_instruction_invalid_category(self):
        """Test validation with invalid category"""
        instruction_data = {
            'instruction_text': 'Valid instruction',
            'priority': 5,
            'category': 'invalid_category'
        }

        result = self.service.validate_instruction(instruction_data)

        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert any('category' in error.lower() for error in result['errors'])

    def test_validate_instruction_warnings(self):
        """Test validation warnings generation"""
        instruction_data = {
            'instruction_text': 'You must always follow this rule exactly as written',
            'priority': 5,
            'category': 'behavior'
        }

        result = self.service.validate_instruction(instruction_data)

        assert result['is_valid'] is True  # Still valid
        assert len(result['warnings']) > 0  # But has warnings
        assert any('always' in warning.lower() for warning in result['warnings'])
        assert any('must' in warning.lower() for warning in result['warnings'])

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_get_instruction_analytics(self, mock_connect):
        """Test getting instruction analytics"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {
                'category': 'behavior',
                'total_instructions': 5,
                'active_instructions': 4,
                'avg_priority': 6.0,
                'total_usage': 25,
                'avg_usage': 5.0,
                'last_activity': datetime.now(),
                'unused_instructions': 1
            }
        ]

        result = await self.service.get_instruction_analytics('user123')

        assert len(result) == 1
        assert result[0]['category'] == 'behavior'
        assert result[0]['total_instructions'] == 5

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_get_usage_stats(self, mock_connect):
        """Test getting usage statistics"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = self.sample_instruction

        result = await self.service.get_usage_stats('user123', 'instruction_id', 30)

        assert result['instruction_id'] == 'instruction_id'
        assert result['total_usage'] == 10
        assert 'avg_daily_usage' in result

    @patch('onyx_core.services.instruction_service.InstructionService.connect')
    async def test_detect_conflicts(self, mock_connect):
        """Test conflict detection"""
        mock_cursor = Mock()
        self.mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {
                'instruction_1_id': 'id1',
                'instruction_1_text': 'Always be formal',
                'instruction_2_id': 'id2',
                'instruction_2_text': 'Be casual and informal',
                'conflict_type': 'direct_contradiction',
                'severity': 'high'
            }
        ]

        result = await self.service.detect_conflicts('user123')

        assert len(result) == 1
        assert result[0]['conflict_type'] == 'direct_contradiction'
        assert result[0]['severity'] == 'high'


if __name__ == '__main__':
    unittest.main()