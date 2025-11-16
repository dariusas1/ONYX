"""
Memory-Aware Agent Service for ONYX

This service provides memory-aware task execution for Agent Mode.
Integrates memory injection and standing instructions into agent workflows.

Story 4-3: Memory Injection & Agent Integration
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass

from .memory_injection_service import get_memory_injection_service
from .memory_service import get_memory_service

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    """Agent task definition"""
    task_id: str
    description: str
    task_type: str
    parameters: Dict[str, Any]
    conversation_id: str
    priority: str = "medium"
    metadata: Dict[str, Any] = None


@dataclass
class AgentResult:
    """Agent execution result"""
    task_id: str
    success: bool
    result_data: Dict[str, Any]
    execution_time_ms: int
    memories_extracted: List[Dict[str, Any]]
    errors: List[str] = None


class MemoryAwareAgent:
    """Memory-aware agent execution service"""

    def __init__(self):
        """Initialize memory-aware agent"""
        self.memory_injection_service = get_memory_injection_service()
        self.memory_service = get_memory_service()

    async def execute_task(
        self,
        task: AgentTask,
        user_id: str
    ) -> AgentResult:
        """
        Execute agent task with memory context

        Args:
            task: Agent task to execute
            user_id: User UUID

        Returns:
            Agent execution result with memory extraction
        """
        start_time = time.time()

        try:
            # 1. Load task-relevant memories
            task_memories = await self._get_task_relevant_memories(task, user_id)

            # 2. Load agent-specific standing instructions
            agent_instructions = await self._get_agent_instructions(user_id, task.task_type)

            # 3. Build memory-enhanced system prompt
            enhanced_prompt = self._build_agent_prompt(task, task_memories, agent_instructions)

            # 4. Execute task with memory context
            execution_result = await self._execute_with_memory(task, enhanced_prompt, user_id)

            # 5. Extract new memories from execution
            extracted_memories = await self._extract_memories_from_execution(
                execution_result, user_id, task.conversation_id
            )

            execution_time = int((time.time() - start_time) * 1000)

            result = AgentResult(
                task_id=task.task_id,
                success=True,
                result_data=execution_result,
                execution_time_ms=execution_time,
                memories_extracted=extracted_memories,
                errors=[]
            )

            # Log successful execution for analytics
            await self._log_agent_execution(user_id, task, result, True)

            return result

        except Exception as e:
            logger.error(f"Failed to execute agent task {task.task_id}: {e}")
            execution_time = int((time.time() - start_time) * 1000)

            result = AgentResult(
                task_id=task.task_id,
                success=False,
                result_data={},
                execution_time_ms=execution_time,
                memories_extracted=[],
                errors=[str(e)]
            )

            # Log failed execution for analytics
            await self._log_agent_execution(user_id, task, result, False)

            return result

    async def _get_task_relevant_memories(
        self,
        task: AgentTask,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get memories relevant to the specific task"""
        try:
            # Get category-specific memories for agent tasks
            priority_categories = ['priority', 'decision', 'goal', 'preference', 'context']

            # Get memories by priority categories
            category_memories = await self.memory_service.get_user_memories(
                user_id=user_id,
                category=None,  # We'll filter in the query
                limit=limit
            )

            # Filter for relevant categories
            relevant_memories = [
                memory for memory in category_memories
                if memory.get('category') in priority_categories
            ]

            # Also get context-aware memories for the task description
            context_memories = await self.memory_injection_service.get_context_aware_memories(
                user_id=user_id,
                conversation_id=task.conversation_id,
                current_message=task.description,
                limit=8
            )

            # Merge and deduplicate, keeping top memories
            all_memories = relevant_memories + context_memories
            unique_memories = self._deduplicate_memories(all_memories)

            return unique_memories[:limit]

        except Exception as e:
            logger.error(f"Failed to get task-relevant memories: {e}")
            return []

    async def _get_agent_instructions(
        self,
        user_id: str,
        task_type: str
    ) -> List[Dict[str, Any]]:
        """Get standing instructions relevant to agent execution"""
        try:
            conn = self.memory_injection_service._get_connection()
            with conn.cursor() as cur:
                # Get instructions for agent-relevant categories
                cur.execute(
                    """
                    SELECT id, instruction_text, category, priority, context_hints, usage_count
                    FROM standing_instructions
                    WHERE user_id = %s
                        AND enabled = TRUE
                        AND category IN ('workflow', 'decision', 'security', 'general')
                    ORDER BY priority DESC, usage_count DESC
                    LIMIT 8
                    """,
                    (user_id,)
                )
                results = cur.fetchall()

                instructions = []
                for row in results:
                    instructions.append({
                        'id': row[0],
                        'instruction_text': row[1],
                        'category': row[2],
                        'priority': row[3],
                        'context_hints': row[4] or [],
                        'usage_count': row[5]
                    })

                return instructions

        except Exception as e:
            logger.error(f"Failed to get agent instructions: {e}")
            return []

    def _build_agent_prompt(
        self,
        task: AgentTask,
        memories: List[Dict[str, Any]],
        instructions: List[Dict[str, Any]]
    ) -> str:
        """Build memory-enhanced system prompt for agent execution"""
        prompt_parts = []

        # Base agent prompt
        prompt_parts.append(
            f"You are executing a task as Manus, M3rcury's strategic intelligence advisor."
        )
        prompt_parts.append("")

        # Add standing instructions
        if instructions:
            prompt_parts.append("AGENT INSTRUCTIONS:")
            for i, instruction in enumerate(instructions, 1):
                instruction_text = instruction.get('instruction_text', '')
                if instruction_text:
                    prompt_parts.append(f"{i}. {instruction_text}")
            prompt_parts.append("")

        # Add relevant context/memories
        if memories:
            prompt_parts.append("RELEVANT CONTEXT:")
            for i, memory in enumerate(memories, 1):
                fact = memory.get('fact', '')
                category = memory.get('category', 'unknown')
                prompt_parts.append(f"{i}. {fact} ({category})")
            prompt_parts.append("")

        # Add task details
        prompt_parts.append(f"TASK TYPE: {task.task_type}")
        prompt_parts.append(f"TASK DESCRIPTION: {task.description}")

        if task.parameters:
            prompt_parts.append(f"TASK PARAMETERS:")
            for key, value in task.parameters.items():
                prompt_parts.append(f"  - {key}: {value}")
            prompt_parts.append("")

        # Add execution guidelines
        prompt_parts.append(
            "Execute this task considering the instructions and context above. "
            "Provide specific, actionable results and track any decisions made or information learned. "
            "Be thorough but efficient in your execution."
        )

        return "\n".join(prompt_parts)

    async def _execute_with_memory(
        self,
        task: AgentTask,
        enhanced_prompt: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute task with memory context
        This is a placeholder for actual agent execution logic
        """
        try:
            # This would integrate with the actual agent execution system
            # For now, we'll simulate execution with task analysis

            execution_result = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "execution_status": "completed",
                "result_summary": f"Executed {task.task_type} task: {task.description}",
                "actions_taken": [
                    "Analyzed task requirements",
                    "Applied memory context",
                    "Executed with standing instructions"
                ],
                "memory_references_used": len([m for m in enhanced_prompt.split('\n') if 'CONTEXT:' in m]),
                "execution_timestamp": datetime.utcnow().isoformat() + "Z",
                "agent_performance": {
                    "prompt_tokens_estimate": len(enhanced_prompt) // 4,
                    "execution_steps": 3,
                    "memory_integration_applied": True
                }
            }

            # Add task-specific execution details
            if task.task_type == "research":
                execution_result["research_findings"] = "Task research completed with memory context"
            elif task.task_type == "analysis":
                execution_result["analysis_results"] = "Task analysis completed with relevant context"
            elif task.task_type == "document_creation":
                execution_result["document_created"] = True
                execution_result["document_content"] = "Document created with user preferences applied"

            return execution_result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "task_id": task.task_id,
                "execution_status": "failed",
                "error": str(e),
                "execution_timestamp": datetime.utcnow().isoformat() + "Z"
            }

    async def _extract_memories_from_execution(
        self,
        execution_result: Dict[str, Any],
        user_id: str,
        conversation_id: str
    ) -> List[Dict[str, Any]]:
        """Extract new memories from agent execution"""
        extracted_memories = []

        try:
            # Extract memories from execution results
            if execution_result.get("execution_status") == "completed":
                # Memory 1: Task execution success
                task_type = execution_result.get("task_type", "unknown")
                memory_1 = await self.memory_service.create_memory(
                    user_id=user_id,
                    fact=f"Successfully executed {task_type} agent task",
                    category="goal",
                    confidence=0.9,
                    source_type="extracted_from_chat",
                    conversation_id=conversation_id,
                    metadata={
                        "task_id": execution_result.get("task_id"),
                        "task_type": task_type,
                        "extraction_source": "agent_execution"
                    }
                )
                if memory_1:
                    extracted_memories.append(memory_1)

                # Memory 2: Actions taken during execution
                actions = execution_result.get("actions_taken", [])
                if actions:
                    memory_2 = await self.memory_service.create_memory(
                        user_id=user_id,
                        fact=f"Agent task actions: {', '.join(actions[:3])}",
                        category="context",
                        confidence=0.8,
                        source_type="extracted_from_chat",
                        conversation_id=conversation_id,
                        metadata={
                            "actions_count": len(actions),
                            "task_id": execution_result.get("task_id"),
                            "extraction_source": "agent_execution"
                        }
                    )
                    if memory_2:
                        extracted_memories.append(memory_2)

                # Memory 3: Performance or outcome if available
                if task_type == "research" and "research_findings" in execution_result:
                    memory_3 = await self.memory_service.create_memory(
                        user_id=user_id,
                        fact=f"Research completed: {execution_result['research_findings']}",
                        category="summary",
                        confidence=0.85,
                        source_type="auto_summary",
                        conversation_id=conversation_id,
                        metadata={
                            "task_id": execution_result.get("task_id"),
                            "extraction_source": "agent_research"
                        }
                    )
                    if memory_3:
                        extracted_memories.append(memory_3)

        except Exception as e:
            logger.error(f"Failed to extract memories from execution: {e}")

        return extracted_memories

    def _deduplicate_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate memories based on content similarity"""
        seen_facts = set()
        unique_memories = []

        for memory in memories:
            fact = memory.get('fact', '').strip().lower()
            if fact and fact not in seen_facts:
                seen_facts.add(fact)
                unique_memories.append(memory)

        return unique_memories

    async def _log_agent_execution(
        self,
        user_id: str,
        task: AgentTask,
        result: AgentResult,
        success: bool
    ):
        """Log agent execution for analytics"""
        try:
            # This could be enhanced with proper analytics tables
            log_entry = {
                "user_id": user_id,
                "task_id": task.task_id,
                "task_type": task.task_type,
                "success": success,
                "execution_time_ms": result.execution_time_ms,
                "memories_extracted": len(result.memories_extracted),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            # For now, just log to file - could be stored in database
            logger.info(f"Agent execution logged: {json.dumps(log_entry)}")

        except Exception as e:
            logger.error(f"Failed to log agent execution: {e}")

    # =========================================================================
    # Advanced Agent Features
    # =========================================================================

    async def get_agent_memory_summary(
        self,
        user_id: str,
        task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get summary of memories relevant to agent execution"""
        try:
            # Get recent agent-related memories
            agent_categories = ['priority', 'decision', 'goal', 'preference', 'context']

            memories_by_category = {}
            total_memories = 0

            for category in agent_categories:
                memories = await self.memory_service.get_user_memories(
                    user_id=user_id,
                    category=category,
                    limit=10
                )
                memories_by_category[category] = memories
                total_memories += len(memories)

            # Get standing instructions
            instructions = await self._get_agent_instructions(user_id, task_type or "general")

            return {
                "user_id": user_id,
                "total_memories": total_memories,
                "memories_by_category": memories_by_category,
                "standing_instructions_count": len(instructions),
                "most_recent_memory": self._get_most_recent_memory(memories_by_category),
                "memory_coverage": {
                    category: len(memories_by_category.get(category, []))
                    for category in agent_categories
                }
            }

        except Exception as e:
            logger.error(f"Failed to get agent memory summary: {e}")
            return {"error": str(e)}

    def _get_most_recent_memory(self, memories_by_category: Dict[str, List]) -> Optional[Dict[str, Any]]:
        """Get the most recent memory across all categories"""
        most_recent = None
        latest_timestamp = None

        for category, memories in memories_by_category.items():
            for memory in memories:
                created_at = memory.get('created_at')
                if created_at:
                    if latest_timestamp is None or created_at > latest_timestamp:
                        latest_timestamp = created_at
                        most_recent = memory

        return most_recent

    async def suggest_memory_extractions(
        self,
        task: AgentTask,
        execution_result: Dict[str, Any]
    ) -> List[str]:
        """Suggest potential memory extractions from execution"""
        suggestions = []

        try:
            task_type = task.task_type
            result_summary = execution_result.get("result_summary", "")

            # Suggest task completion memory
            suggestions.append(f"Completed {task_type} task: {task.description}")

            # Suggest outcome-based memories
            if "research_findings" in execution_result:
                suggestions.append(f"Research findings: {execution_result['research_findings']}")

            if "analysis_results" in execution_result:
                suggestions.append(f"Analysis results: {execution_result['analysis_results']}")

            # Suggest preference memories from task parameters
            if task.parameters:
                for param, value in task.parameters.items():
                    if isinstance(value, str) and len(value) < 200:
                        suggestions.append(f"Parameter preference: {param} = {value}")

        except Exception as e:
            logger.error(f"Failed to suggest memory extractions: {e}")

        return suggestions[:5]  # Return top 5 suggestions


# Global memory-aware agent instance
_memory_aware_agent = None


def get_memory_aware_agent() -> MemoryAwareAgent:
    """Get or create memory-aware agent instance"""
    global _memory_aware_agent
    if _memory_aware_agent is None:
        _memory_aware_agent = MemoryAwareAgent()
    return _memory_aware_agent