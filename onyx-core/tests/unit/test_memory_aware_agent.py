"""
Unit Tests for Memory-Aware Agent

Tests memory-aware agent execution, task processing, and memory extraction.

Story 4-3: Memory Injection & Agent Integration
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.memory_aware_agent import MemoryAwareAgent, AgentTask, AgentResult


class TestMemoryAwareAgent:
    """Test cases for MemoryAwareAgent"""

    @pytest.fixture
    def mock_memory_injection_service(self):
        """Mock memory injection service"""
        service = AsyncMock(spec=MemoryAwareAgent)
        return service

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service"""
        service = AsyncMock(spec=MemoryAwareAgent)
        return service

    @pytest.fixture
    def agent(self, mock_memory_injection_service, mock_memory_service):
        """Create memory-aware agent with mocked dependencies"""
        agent = MemoryAwareAgent()
        agent.memory_injection_service = mock_memory_injection_service
        agent.memory_service = mock_memory_service
        return agent

    @pytest.fixture
    def sample_task(self):
        """Sample agent task for testing"""
        return AgentTask(
            task_id="task-123",
            description="Research aerospace defense contracts",
            task_type="research",
            parameters={
                "topic": "defense contracts",
                "industry": "aerospace"
            },
            conversation_id="conv-456",
            priority="high",
            metadata={"request_source": "chat"}
        )

    @pytest.fixture
    def sample_task_memories(self):
        """Sample task-relevant memories"""
        return [
            {
                "id": "memory-1",
                "fact": "User prefers defense contracts",
                "category": "priority",
                "confidence": 0.95,
                "source_type": "manual",
                "created_at": datetime.utcnow()
            },
            {
                "id": "memory-2",
                "fact": "Current focus on aerospace projects",
                "category": "goal",
                "confidence": 0.9,
                "source_type": "extracted_from_chat",
                "created_at": datetime.utcnow() - timedelta(days=1)
            },
            {
                "id": "memory-3",
                "fact": "Recently decided to prioritize Onyx platform",
                "category": "decision",
                "confidence": 0.88,
                "source_type": "manual",
                "created_at": datetime.utcnow() - timedelta(days=3)
            }
        ]

    @pytest.fixture
    def sample_agent_instructions(self):
        """Sample agent standing instructions"""
        return [
            {
                "id": "instruction-1",
                "instruction_text": "Always provide evidence-based recommendations",
                "category": "workflow",
                "priority": 9,
                "context_hints": ["research", "analysis"],
                "usage_count": 12
            },
            {
                "id": "instruction-2",
                "instruction_text": "Consider user preferences when making suggestions",
                "category": "communication",
                "priority": 8,
                "context_hints": ["preferences", "personalization"],
                "usage_count": 8
            }
        ]

    @pytest.mark.asyncio
    async def test_execute_task_success(self, agent, sample_task, sample_task_memories, sample_agent_instructions):
        """Test successful agent task execution"""
        # Mock service methods
        agent._get_task_relevant_memories = AsyncMock(return_value=sample_task_memories)
        agent._get_agent_instructions = AsyncMock(return_value=sample_agent_instructions)
        agent._extract_memories_from_execution = AsyncMock(return_value=[])

        result = await agent.execute_task(sample_task, "test-user-123")

        # Verify success
        assert result.success is True
        assert result.task_id == "task-123"
        assert result.execution_time_ms > 0
        assert result.errors == []

        # Verify result data structure
        assert "task_id" in result.result_data
        assert "task_type" in result.result_data
        assert "execution_status" in result.result_data
        assert "result_summary" in result.result_data
        assert "actions_taken" in result.result_data

        # Verify method calls
        agent._get_task_relevant_memories.assert_called_once_with(sample_task, "test-user-123", limit=10)
        agent._get_agent_instructions.assert_called_once_with("test-user-123", "research")
        agent._extract_memories_from_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_with_memory_extraction(self, agent, sample_task, sample_task_memories):
        """Test agent task execution with memory extraction"""
        # Mock memory extraction to return new memories
        extracted_memories = [
            {
                "id": "new-memory-1",
                "fact": "Successfully executed research agent task",
                "category": "goal",
                "confidence": 0.9
            }
        ]
        agent._get_task_relevant_memories = AsyncMock(return_value=sample_task_memories)
        agent._get_agent_instructions = AsyncMock(return_value=[])
        agent._extract_memories_from_execution = AsyncMock(return_value=extracted_memories)

        result = await agent.execute_task(sample_task, "test-user-123")

        assert result.success is True
        assert len(result.memories_extracted) == 1
        assert result.memories_extracted[0]["fact"] == "Successfully executed research agent task"

    @pytest.asyncio
    async def test_execute_task_error_handling(self, agent, sample_task):
        """Test agent task execution with error handling"""
        # Mock service to raise exception
        agent._get_task_relevant_memories = AsyncMock(side_effect=Exception("Service error"))

        result = await agent.execute_task(sample_task, "test-user-123")

        # Verify error handling
        assert result.success is False
        assert result.task_id == "task-123"
        assert result.execution_time_ms > 0
        assert result.result_data == {}
        assert len(result.errors) == 1
        assert "Service error" in result.errors[0]
        assert result.memories_extracted == []

    @pytest.mark.asyncio
    async def test_get_task_relevant_memories(self, agent, sample_task, sample_task_memories):
        """Test getting task-relevant memories"""
        # Mock memory service
        mock_memories = sample_task_memories + [
            {"id": "other-memory", "fact": "Other memory", "category": "context", "confidence": 0.7}
        ]
        agent.memory_service.get_user_memories = AsyncMock(return_value=mock_memories)

        result = await agent._get_task_relevant_memories(sample_task, "test-user-123", limit=8)

        # Should filter by priority categories
        priority_categories = ['priority', 'decision', 'goal', 'preference', 'context']
        filtered_memories = [
            mem for mem in mock_memories
            if mem.get('category') in priority_categories
        ]

        assert len(result) == len(filtered_memories)  # Should only return priority categories

        # Should respect limit
        assert len(result) <= 8

    @pytest.mark.asyncio
    async def test_get_agent_instructions(self, agent, sample_agent_instructions):
        """Test getting agent standing instructions"""
        # Mock database connection and query
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        conn.cursor.return_value.__exit__.return_value = None
        cursor.fetchall.return_value = [
            (
                "instruction-1", "Always provide evidence-based recommendations",
                "workflow", 9, ["research", "analysis"], 12
            ),
            (
                "instruction-2", "Consider user preferences",
                "communication", 8, ["preferences", "personalization"], 8
            )
        ]

        with patch.object(agent.memory_injection_service, '_get_connection', return_value=conn):
            result = await agent._get_agent_instructions("test-user-123", "research")

        assert len(result) == 2
        assert result[0]["instruction_text"] == "Always provide evidence-based recommendations"
        assert result[0]["category"] == "workflow"
        assert result[0]["priority"] == 9

    def test_build_agent_prompt(self, agent, sample_task, sample_task_memories, sample_agent_instructions):
        """Test agent prompt building"""
        prompt = agent._build_agent_prompt(sample_task, sample_task_memories, sample_agent_instructions)

        # Verify prompt structure
        assert "You are executing a task as Manus, M3rcury's strategic intelligence advisor." in prompt
        assert "AGENT INSTRUCTIONS:" in prompt
        assert "RELEVANT CONTEXT:" in prompt
        assert "TASK TYPE: research" in prompt
        assert "TASK DESCRIPTION: Research aerospace defense contracts" in prompt
        assert "TASK PARAMETERS:" in prompt

        # Verify content inclusion
        assert "Always provide evidence-based recommendations" in prompt
        assert "User prefers defense contracts" in prompt
        assert "Current focus on aerospace projects" in prompt

        # Verify parameter inclusion
        assert "topic: defense contracts" in prompt
        assert "industry: aerospace" in prompt

        # Verify execution guidelines
        assert "Execute this task considering the instructions and context above" in prompt

    @pytest.mark.asyncio
    async def test_execute_with_memory(self, agent, sample_task):
        """Test task execution with memory context"""
        result = await agent._execute_with_memory(sample_task, "test-prompt", "test-user")

        assert result["task_id"] == "task-123"
        assert result["task_type"] == "research"
        assert result["execution_status"] == "completed"
        assert "result_summary" in result
        assert "actions_taken" in result
        assert "execution_timestamp" in result
        assert "agent_performance" in result

        # Verify agent performance metrics
        performance = result["agent_performance"]
        assert "prompt_tokens_estimate" in performance
        assert "execution_steps" in performance
        assert "memory_integration_applied" in performance

    @pytest.mark.asyncio
    async def test_extract_memories_from_execution(self, agent):
        """Test memory extraction from execution"""
        # Test with successful execution result
        execution_result = {
            "task_id": "task-123",
            "task_type": "research",
            "execution_status": "completed",
            "result_summary": "Research completed successfully",
            "actions_taken": ["Analyzed requirements", "Found relevant data", "Generated report"],
            "research_findings": "Found 5 key defense contract opportunities"
        }

        # Mock memory service create_memory method
        agent.memory_service.create_memory = AsyncMock(side_effect=[
            {"id": "memory-1", "fact": "Successfully executed research agent task", "category": "goal"},
            {"id": "memory-2", "fact": "Agent task actions: Analyzed requirements, Found relevant data, Generated report", "category": "context"},
            {"id": "memory-3", "fact": "Research completed: Found 5 key defense contract opportunities", "category": "summary"}
        ])

        result = await agent._extract_memories_from_execution(
            execution_result, "test-user-123", "conv-456"
        )

        assert len(result) == 3
        assert result[0]["fact"] == "Successfully executed research agent task"
        assert result[0]["category"] == "goal"
        assert result[1]["fact"] == "Agent task actions: Analyzed requirements, Found relevant data, Generated report"
        assert result[2]["fact"] == "Research completed: Found 5 key defense contract opportunities"
        assert result[2]["category"] == "summary"

    def test_deduplicate_memories(self, agent):
        """Test memory deduplication"""
        memories_with_duplicates = [
            {"id": "mem-1", "fact": "User prefers defense contracts", "category": "priority"},
            {"id": "mem-2", "fact": "User prefers defense contracts", "category": "priority"},  # Duplicate
            {"id": "mem-3", "fact": "user prefers defense contracts", "category": "priority"},  # Case-insensitive duplicate
            {"id": "mem-4", "fact": "User focuses on aerospace", "category": "goal"},
            {"id": "mem-5", "fact": "User prefers defense contracts and aerospace", "category": "priority"}
        ]

        unique_memories = agent._deduplicate_memories(memories_with_duplicates)

        # Should remove duplicates
        assert len(unique_memories) == 3
        facts = [mem["fact"].lower() for mem in unique_memories]
        assert "user prefers defense contracts" in facts
        assert "user focuses on aerospace" in facts
        assert "user prefers defense contracts and aerospace" in facts

    @pytest.mark.asyncio
    async def test_log_agent_execution(self, agent, sample_task):
        """Test agent execution logging"""
        result = AgentResult(
            task_id="task-123",
            success=True,
            result_data={"status": "completed"},
            execution_time_ms=150,
            memories_extracted=[],
            errors=[]
        )

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            await agent._log_agent_execution("test-user-123", sample_task, result, True)

        # Verify the file would be opened (logging occurred)
            mock_open.assert_called()

    def test_get_most_recent_memory(self, agent):
        """Test getting most recent memory"""
        memories_by_category = {
            "priority": [
                {"created_at": datetime.utcnow() - timedelta(days=5), "fact": "Old priority memory"}
            ],
            "goal": [
                {"created_at": datetime.utcnow() - timedelta(days=1), "fact": "Recent goal memory"}
            ],
            "decision": [
                {"created_at": datetime.utcnow() - timedelta(hours=6), "fact": "Recent decision memory"}
            ]
        }

        most_recent = agent._get_most_recent_memory(memories_by_category)

        # Should return the most recent memory (6 hours ago)
        assert most_recent is not None
        assert most_recent["fact"] == "Recent decision memory"
        assert most_recent["category"] == "decision"

    @pytest.mark.asyncio
    async def test_get_agent_memory_summary(self, agent):
        """Test getting agent memory summary"""
        # Mock service methods
        mock_memories_by_category = {
            "priority": [{"id": "mem-1", "fact": "Priority memory"}],
            "decision": [{"id": "mem-2", "fact": "Decision memory"}],
            "goal": [{"id": "mem-3", "fact": "Goal memory"}],
            "preference": [{"id": "mem-4", "fact": "Preference memory"}],
            "context": [{"id": "mem-5", "fact": "Context memory"}],
            "summary": []
        }
        agent.get_memory_service.get_user_memories = AsyncMock()
        agent._get_agent_instructions = AsyncMock(return_value=[])

        # Mock the service to return different memories for each category
        def mock_get_user_memories(user_id, category=None, **kwargs):
            if category:
                return mock_memories_by_category.get(category, [])
            return []  # Return empty for no category

        agent.get_memory_service.get_user_memories.side_effect = mock_get_user_memories

        result = await agent.get_agent_memory_summary("test-user-123", "research")

        assert result["user_id"] == "test-user-123"
        assert result["total_memories"] == 5  # 5 categories with memories
        assert len(result["memories_by_category"]) == 6  # All 6 categories
        assert result["standing_instructions_count"] == 0
        assert result["memory_coverage"]["priority"] == 1
        assert result["memory_coverage"]["decision"] == 1
        assert result["memory_coverage"]["goal"] == 1
        assert result["memory_coverage"]["preference"] == 1
        assert result["memory_coverage"]["context"] == 1
        assert result["memory_coverage"]["summary"] == 0

    @pytest.mark.asyncio
    async def test_suggest_memory_extractions(self, agent, sample_task):
        """Test memory extraction suggestions"""
        execution_result = {
            "task_type": "research",
            "result_summary": "Research completed successfully",
            "research_findings": "Key aerospace market opportunities identified",
            "analysis_results": "Strategic recommendations developed"
        }

        suggestions = await agent.suggest_memory_extractions(sample_task, execution_result)

        assert len(suggestions) > 0
        assert any("Research aerospace defense contracts" in s for s in suggestions)
        assert any("Research completed" in s for s in suggestions)
        assert any("Research findings" in s for s in suggestions)
        assert any("Analysis results" in s for s in suggestions)

        # Test with task parameters
        task_with_params = AgentTask(
            task_id="task-456",
            description="Create document with preferences",
            task_type="document_creation",
            parameters={"style": "professional", "tone": "formal"},
            conversation_id="conv-789"
        )

        execution_result_with_params = {
            "result_summary": "Document created successfully"
        }

        suggestions_with_params = await agent.suggest_memory_extractions(task_with_params, execution_result_with_params)

        assert any("Parameter preference: style = professional" in s for s in suggestions_with_params)
        assert any("Parameter preference: tone = formal" in s for s in suggestions_with_params)


if __name__ == "__main__":
    pytest.main([__file__])