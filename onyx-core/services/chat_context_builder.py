"""
Chat Context Builder for ONYX

This service builds LLM context with memory injection for chat conversations.
Integrates with the memory injection system to provide personalized context.

Story 4-3: Memory Injection & Agent Integration
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .memory_injection_service import get_memory_injection_service
from .memory_service import get_memory_service

logger = logging.getLogger(__name__)


class ChatContextBuilder:
    """Service for building LLM context with memory injection"""

    def __init__(self):
        """Initialize chat context builder"""
        self.memory_injection_service = get_memory_injection_service()
        self.memory_service = get_memory_service()

    async def build_context(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        recent_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Build complete LLM context with memory injection

        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            current_message: Current user message
            recent_history: Optional recent conversation history

        Returns:
            Complete context object with system prompt and metadata
        """
        start_time = time.time()

        try:
            # Get memory injection
            memory_injection = await self.memory_injection_service.prepare_injection(
                user_id=user_id,
                conversation_id=conversation_id,
                current_message=current_message
            )

            # Get recent conversation context
            recent_context = await self._get_recent_conversation_context(
                recent_history or []
            )

            # Build complete system prompt
            system_prompt = self._build_system_prompt(
                memory_injection=memory_injection,
                recent_context=recent_context,
                current_message=current_message
            )

            # Track usage analytics
            await self._track_memory_usage(
                user_id=user_id,
                memory_injection=memory_injection
            )

            # Return complete context
            return {
                "system_prompt": system_prompt,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "memory_injection": {
                    "memories_count": len(memory_injection.memories),
                    "instructions_count": len(memory_injection.standing_instructions),
                    "injection_time_ms": memory_injection.injection_time,
                    "performance_stats": memory_injection.performance_stats
                },
                "recent_context": recent_context,
                "context_build_time_ms": int((time.time() - start_time) * 1000),
                "total_tokens_estimate": self._estimate_tokens(system_prompt),
                "context_metadata": {
                    "built_at": datetime.utcnow().isoformat() + "Z",
                    "context_version": "1.0",
                    "injection_enabled": True
                }
            }

        except Exception as e:
            logger.error(f"Failed to build chat context for user {user_id}: {e}")
            # Return fallback context without injection
            return self._build_fallback_context(
                user_id=user_id,
                conversation_id=conversation_id,
                error=str(e),
                build_time=int((time.time() - start_time) * 1000)
            )

    async def update_context(
        self,
        user_id: str,
        conversation_id: str,
        new_message: str,
        new_memory_suggestions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update context during ongoing conversation

        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            new_message: New message in conversation
            new_memory_suggestions: Optional suggested memories to extract

        Returns:
            Updated context with any new insights
        """
        try:
            # Get context-aware memories for current conversation topic
            context_memories = await self.memory_injection_service.get_context_aware_memories(
                user_id=user_id,
                conversation_id=conversation_id,
                current_message=new_message,
                limit=8
            )

            # Format context update
            context_update = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "current_message": new_message,
                "context_memories": context_memories,
                "suggested_memories": new_memory_suggestions or [],
                "update_timestamp": datetime.utcnow().isoformat() + "Z"
            }

            # If there are memory suggestions, they can be processed by the memory extraction service
            if new_memory_suggestions:
                context_update["memory_extraction_needed"] = True

            return {
                "success": True,
                "context_update": context_update,
                "context_memories_count": len(context_memories)
            }

        except Exception as e:
            logger.error(f"Failed to update chat context: {e}")
            return {
                "success": False,
                "error": str(e),
                "context_update": None
            }

    def _build_system_prompt(
        self,
        memory_injection,
        recent_context: str,
        current_message: str
    ) -> str:
        """Build complete system prompt with memory injection"""
        prompt_parts = []

        # Base system prompt
        prompt_parts.append(
            "You are Manus, M3rcury's strategic intelligence advisor."
        )

        # Add memory injection if available
        if memory_injection.injection_text.strip():
            prompt_parts.append("")
            prompt_parts.append(memory_injection.injection_text)

        # Add recent conversation context if available
        if recent_context.strip():
            prompt_parts.append("")
            prompt_parts.append("RECENT CONVERSATION CONTEXT:")
            prompt_parts.append(recent_context)

        # Add response guidelines
        prompt_parts.append("")
        prompt_parts.append("RESPONSE GUIDELINES:")
        prompt_parts.append("- Use the standing instructions and memories above to provide personalized advice")
        prompt_parts.append("- Reference the user's priorities and current focus areas when relevant")
        prompt_parts.append("- Consider recent decisions when making recommendations")
        prompt_parts.append("- Always cite sources and provide evidence-based insights")
        prompt_parts.append("- Be concise but thorough in your analysis")
        prompt_parts.append("- Focus on strategic implications and actionable recommendations")
        prompt_parts.append("- Maintain a professional and supportive tone")

        # Add continuation marker
        prompt_parts.append("")
        prompt_parts.append("Current conversation continues below:")

        return "\n".join(prompt_parts)

    async def _get_recent_conversation_context(
        self,
        recent_history: List[Dict[str, Any]]
    ) -> str:
        """Format recent conversation context"""
        if not recent_history:
            return ""

        context_lines = []
        for message in recent_history[-5:]:  # Last 5 messages
            role = message.get('role', 'unknown')
            content = message.get('content', '')
            timestamp = message.get('timestamp')

            if role == 'user':
                role_label = "User"
            elif role == 'assistant':
                role_label = "Manus"
            else:
                role_label = role.title()

            # Format timestamp if available
            time_str = ""
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    time_str = f" [{dt.strftime('%H:%M')}]"
                except:
                    time_str = ""

            # Format message
            if content:
                context_lines.append(f"{time_str} {role_label}: {content}")

        return "\n".join(context_lines)

    async def _track_memory_usage(
        self,
        user_id: str,
        memory_injection
    ):
        """Track memory usage for analytics"""
        try:
            # Update usage counts for injected memories
            memory_ids = [memory['id'] for memory in memory_injection.memories]
            if memory_ids:
                conn = self.memory_injection_service._get_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE user_memories
                        SET access_count = access_count + 1,
                            last_accessed_at = NOW()
                        WHERE id = ANY(%s)
                        """,
                        (memory_ids,)
                    )
                    conn.commit()

            # Update instruction usage
            instruction_ids = [inst['id'] for inst in memory_injection.standing_instructions]
            if instruction_ids:
                conn = self.memory_injection_service._get_connection()
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE standing_instructions
                        SET usage_count = usage_count + 1,
                            last_used_at = NOW()
                        WHERE id = ANY(%s)
                        """,
                        (instruction_ids,)
                    )
                    conn.commit()

        except Exception as e:
            logger.error(f"Failed to track memory usage: {e}")

    def _build_fallback_context(
        self,
        user_id: str,
        conversation_id: str,
        error: str,
        build_time: int
    ) -> Dict[str, Any]:
        """Build fallback context when injection fails"""
        fallback_prompt = """You are Manus, M3rcury's strategic intelligence advisor.

RESPONSE GUIDELINES:
- Provide clear, evidence-based insights
- Focus on strategic implications and actionable recommendations
- Be concise but thorough in your analysis
- Maintain a professional and supportive tone
- Always cite sources when referencing specific information

Current conversation continues below:"""

        return {
            "system_prompt": fallback_prompt,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "memory_injection": {
                "memories_count": 0,
                "instructions_count": 0,
                "injection_time_ms": 0,
                "performance_stats": {"error": error}
            },
            "recent_context": "",
            "context_build_time_ms": build_time,
            "total_tokens_estimate": self._estimate_tokens(fallback_prompt),
            "context_metadata": {
                "built_at": datetime.utcnow().isoformat() + "Z",
                "context_version": "1.0",
                "injection_enabled": False,
                "fallback_used": True,
                "error": error
            }
        }

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if not text:
            return 0

        # Simple token estimation (approximately 4 characters per token)
        # This is a rough estimate - can be enhanced with actual tokenizer
        estimated_tokens = len(text) // 4

        # Add buffer for safety
        return int(estimated_tokens * 1.2)

    # =========================================================================
    # Advanced Context Building Features
    # =========================================================================

    async def build_context_with_constraints(
        self,
        user_id: str,
        conversation_id: str,
        current_message: str,
        max_tokens: int = 4000,
        priority_categories: Optional[List[str]] = None,
        exclude_categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build context with specific constraints

        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            current_message: Current message
            max_tokens: Maximum tokens for context
            priority_categories: Categories to prioritize
            exclude_categories: Categories to exclude

        Returns:
            Constrained context object
        """
        try:
            # Get base context
            base_context = await self.build_context(
                user_id=user_id,
                conversation_id=conversation_id,
                current_message=current_message
            )

            # Apply constraints
            if base_context["total_tokens_estimate"] > max_tokens:
                # Truncate context to fit token limit
                truncated_context = self._truncate_context(
                    base_context["system_prompt"],
                    max_tokens
                )
                base_context["system_prompt"] = truncated_context
                base_context["total_tokens_estimate"] = self._estimate_tokens(truncated_context)
                base_context["context_metadata"]["truncated"] = True

            # Apply category filters if specified
            if priority_categories or exclude_categories:
                filtered_context = self._filter_context_by_categories(
                    base_context["system_prompt"],
                    priority_categories or [],
                    exclude_categories or []
                )
                base_context["system_prompt"] = filtered_context
                base_context["context_metadata"]["category_filtered"] = True
                base_context["context_metadata"]["priority_categories"] = priority_categories
                base_context["context_metadata"]["exclude_categories"] = exclude_categories

            return base_context

        except Exception as e:
            logger.error(f"Failed to build constrained context: {e}")
            return await self.build_context(user_id, conversation_id, current_message)

    def _truncate_context(self, context: str, max_tokens: int) -> str:
        """Truncate context to fit within token limit"""
        lines = context.split('\n')
        truncated_lines = []
        current_tokens = 0

        # Always keep the first part (system prompt intro)
        intro_lines = []
        for line in lines:
            if line.strip() and not line.startswith("STANDING INSTRUCTIONS") and not line.startswith("USER CONTEXT"):
                intro_lines.append(line)
            elif line.startswith("STANDING INSTRUCTIONS") or line.startswith("USER CONTEXT"):
                break

        current_tokens = self._estimate_tokens('\n'.join(intro_lines))
        truncated_lines.extend(intro_lines)

        # Add remaining lines until we hit the token limit
        for line in lines[len(intro_lines):]:
            line_tokens = self._estimate_tokens(line)
            if current_tokens + line_tokens > max_tokens:
                break
            truncated_lines.append(line)
            current_tokens += line_tokens

        return '\n'.join(truncated_lines)

    def _filter_context_by_categories(
        self,
        context: str,
        priority_categories: List[str],
        exclude_categories: List[str]
    ) -> str:
        """Filter context by memory categories"""
        lines = context.split('\n')
        filtered_lines = []
        current_section = None

        for line in lines:
            # Track current section
            if line.startswith("USER CONTEXT"):
                current_section = "memories"
            elif line.startswith("STANDING INSTRUCTIONS"):
                current_section = "instructions"
            elif line.strip() == "" or line.startswith("RECENT CONVERSATION") or line.startswith("RESPONSE GUIDELINES"):
                current_section = None

            # Filter memories by category
            if current_section == "memories" and line.strip().startswith(tuple(f"{i}." for i in range(1, 10))):
                # This is a memory line - check category
                if exclude_categories and any(cat in line for cat in exclude_categories):
                    continue
                if priority_categories and not any(cat in line for cat in priority_categories):
                    continue

            filtered_lines.append(line)

        return '\n'.join(filtered_lines)


# Global chat context builder instance
_chat_context_builder = None


def get_chat_context_builder() -> ChatContextBuilder:
    """Get or create chat context builder instance"""
    global _chat_context_builder
    if _chat_context_builder is None:
        _chat_context_builder = ChatContextBuilder()
    return _chat_context_builder