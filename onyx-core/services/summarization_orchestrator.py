"""
Summarization Orchestrator for ONYX

This service orchestrates the auto-summarization pipeline by integrating
trigger detection, LLM processing, and memory storage with the existing
memory injection system.

Story 4-4: Auto-Summarization Pipeline
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from services.summarization_trigger_service import get_summarization_trigger_service
from services.conversation_summarizer import get_conversation_summarizer
from services.summary_memory_storage import get_summary_memory_storage
from services.memory_injection_service import get_memory_injection_service
from services.memory_service import get_memory_service

logger = logging.getLogger(__name__)


class SummarizationOrchestrator:
    """Orchestrator for the auto-summarization pipeline"""

    def __init__(self):
        """Initialize summarization orchestrator"""
        self.trigger_service = get_summarization_trigger_service()
        self.summarizer = get_conversation_summarizer()
        self.storage_service = get_summary_memory_storage()
        self.injection_service = get_memory_injection_service()
        self.memory_service = get_memory_service()

        # Configuration
        self.enabled = os.getenv("SUMMARIZATION_ENABLED", "true").lower() == "true"
        self.auto_inject_summaries = os.getenv("SUMMARIZATION_AUTO_INJECT", "true").lower() == "true"

    async def process_message(
        self,
        conversation_id: str,
        message_id: str,
        user_id: str,
        message_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a new message and trigger summarization if needed

        This method should be called after each message is stored to determine
        if auto-summarization should be triggered.

        Args:
            conversation_id: Conversation UUID
            message_id: Current message UUID
            user_id: User UUID
            message_content: Optional current message content for context

        Returns:
            Result of the processing including whether summarization was triggered
        """
        if not self.enabled:
            return {"enabled": False, "reason": "Summarization is disabled"}

        try:
            # Check if summarization should be triggered
            trigger = await self.trigger_service.should_trigger_summarization(
                conversation_id=conversation_id,
                message_id=message_id,
                user_id=user_id
            )

            if not trigger:
                return {
                    "triggered": False,
                    "reason": "Trigger conditions not met",
                    "enabled": True
                }

            # Process the trigger (queues background job)
            job_queued = await self.trigger_service.process_trigger(trigger)

            result = {
                "triggered": True,
                "job_queued": job_queued,
                "conversation_id": conversation_id,
                "message_count": trigger.message_count,
                "trigger_interval": trigger.trigger_interval,
                "enabled": True
            }

            if job_queued:
                logger.info(
                    f"Summarization triggered for conversation {conversation_id} "
                    f"at message count {trigger.message_count}"
                )
            else:
                logger.warning(
                    f"Failed to queue summarization job for conversation {conversation_id}"
                )
                result["error"] = "Failed to queue background job"

            return result

        except Exception as e:
            logger.error(f"Error processing message for summarization: {e}")
            return {
                "triggered": False,
                "error": str(e),
                "enabled": True
            }

    async def get_conversation_context_with_summaries(
        self,
        user_id: str,
        conversation_id: str,
        current_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get conversation context including relevant summaries

        This integrates with the existing memory injection system to include
        auto-generated summaries along with other memories and standing instructions.

        Args:
            user_id: User UUID
            conversation_id: Conversation UUID
            current_message: Optional current message for context filtering

        Returns:
            Enhanced injection context including summaries
        """
        try:
            # Get standard memory injection
            injection = await self.injection_service.prepare_injection(
                user_id=user_id,
                conversation_id=conversation_id,
                current_message=current_message
            )

            if self.auto_inject_summaries:
                # Get recent summaries for this conversation
                conversation_summaries = await self.storage_service.get_conversation_summaries(
                    conversation_id=conversation_id,
                    limit=3  # Get last 3 summaries
                )

                # Get general summary memories for context
                user_summary_memories = await self.storage_service.get_user_summary_memories(
                    user_id=user_id,
                    limit=2,  # Get 2 recent summary memories from other conversations
                    days=7
                )

                # Enhance injection with summaries
                enhanced_injection = self._enhance_injection_with_summaries(
                    injection,
                    conversation_summaries,
                    user_summary_memories
                )

                return enhanced_injection

            return {
                "injection": injection,
                "summaries_integrated": False,
                "auto_inject_enabled": False
            }

        except Exception as e:
            logger.error(f"Error getting conversation context with summaries: {e}")
            # Return basic injection on error
            return {
                "error": str(e),
                "injection": None,
                "summaries_integrated": False
            }

    def _enhance_injection_with_summaries(
        self,
        injection: Any,
        conversation_summaries: List[Dict[str, Any]],
        user_summary_memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enhance memory injection with summaries"""
        try:
            # Extract current injection text
            injection_text = injection.injection_text if injection else ""
            enhanced_parts = [injection_text] if injection_text else []

            # Add conversation summaries section
            if conversation_summaries:
                enhanced_parts.append("RECENT CONVERSATION SUMMARIES:")
                for i, summary in enumerate(conversation_summaries, 1):
                    created_at = summary.get('created_at')
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                    # Format age
                    now = datetime.utcnow()
                    if isinstance(created_at, datetime):
                        delta = now - created_at
                        hours_ago = int(delta.total_seconds() / 3600)
                        age_str = f"{hours_io}h ago" if hours_ago > 0 else "just now"
                    else:
                        age_str = "unknown"

                    summary_text = summary.get('summary_text', '')
                    topics = summary.get('key_topics', [])
                    confidence = summary.get('confidence_score', 0.8)

                    topics_str = f" (topics: {', '.join(topics)})" if topics else ""

                    enhanced_parts.append(
                        f"{i}. {summary_text}{topics_str} "
                        f"({int(confidence * 100)}% confidence, {age_str})"
                    )
                enhanced_parts.append("")  # Empty line for separation

            # Add general summary memories section
            if user_summary_memories:
                enhanced_parts.append("RELEVANT SUMMARY MEMORIES:")
                for i, memory in enumerate(user_summary_memories, 1):
                    fact = memory.get('fact', '')
                    metadata = memory.get('metadata', {})
                    conversation_id = metadata.get('conversation_id', 'unknown')
                    created_at = metadata.get('generated_at', memory.get('created_at'))

                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                    # Format age
                    now = datetime.utcnow()
                    if isinstance(created_at, datetime):
                        delta = now - created_at
                        days_ago = int(delta.total_seconds() / 86400)
                        age_str = f"{days_ago}d ago" if days_ago > 0 else "just now"
                    else:
                        age_str = "unknown"

                    confidence = memory.get('confidence', 0.8)

                    enhanced_parts.append(
                        f"{i}. {fact} (conversation {conversation_id[:8]}..., "
                        f"{int(confidence * 100)}% confidence, {age_str})"
                    )
                enhanced_parts.append("")  # Empty line for separation

            # Create enhanced injection text
            enhanced_injection_text = "\n".join(enhanced_parts)

            # Create enhanced injection object
            enhanced_injection = injection  # This will have all the original fields
            enhanced_injection.injection_text = enhanced_injection_text
            enhanced_injection.summaries_included = {
                "conversation_summaries": len(conversation_summaries),
                "user_summary_memories": len(user_summary_memories)
            }

            return {
                "injection": enhanced_injection,
                "summaries_integrated": True,
                "auto_inject_enabled": True,
                "summaries_count": len(conversation_summaries) + len(user_summary_memories)
            }

        except Exception as e:
            logger.error(f"Error enhancing injection with summaries: {e}")
            return {
                "injection": injection,
                "summaries_integrated": False,
                "error": str(e)
            }

    async def get_user_summarization_stats(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get summarization statistics for a user

        Args:
            user_id: User UUID
            days: Number of days to analyze

        Returns:
            Comprehensive summarization statistics
        """
        try:
            # Get summary memories for the user
            summary_memories = await self.storage_service.get_user_summary_memories(
                user_id=user_id,
                limit=1000,  # Get all recent summaries
                days=days
            )

            # Get injection analytics
            injection_analytics = await self.injection_service.get_injection_analytics(
                user_id=user_id,
                days=days
            )

            # Calculate additional statistics
            total_summaries = len(summary_memories)
            conversations_with_summaries = len(set(
                mem.get('conversation_id') for mem in summary_memories
                if mem.get('conversation_id')
            ))

            # Calculate confidence distribution
            confidence_ranges = {"high": 0, "medium": 0, "low": 0}
            for memory in summary_memories:
                confidence = memory.get('confidence', 0.8)
                if confidence >= 0.9:
                    confidence_ranges["high"] += 1
                elif confidence >= 0.7:
                    confidence_ranges["medium"] += 1
                else:
                    confidence_ranges["low"] += 1

            # Calculate sentiment distribution
            sentiment_ranges = {"positive": 0, "neutral": 0, "negative": 0}
            for memory in summary_memmaries:
                metadata = memory.get('metadata', {})
                sentiment = metadata.get('sentiment', 0.0)
                if sentiment > 0.2:
                    sentiment_ranges["positive"] += 1
                elif sentiment < -0.2:
                    sentiment_ranges["negative"] += 1
                else:
                    sentiment_ranges["neutral"] += 1

            return {
                "user_id": user_id,
                "period_days": days,
                "summary_memories": {
                    "total_count": total_summaries,
                    "conversations_with_summaries": conversations_with_summaries,
                    "confidence_distribution": confidence_ranges,
                    "sentiment_distribution": sentiment_ranges
                },
                "injection_analytics": injection_analytics,
                "enabled": self.enabled,
                "auto_inject_enabled": self.auto_inject_summaries
            }

        except Exception as e:
            logger.error(f"Error getting user summarization stats: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "period_days": days
            }

    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get overall orchestrator status and health"""
        try:
            # Get status from all services
            queue_status = await self.trigger_service.get_queue_status()
            summarizer_metrics = await self.summarizer.get_service_metrics()
            storage_metrics = await self.storage_service.get_service_metrics()

            return {
                "orchestrator": {
                    "enabled": self.enabled,
                    "auto_inject_summaries": self.auto_inject_summaries,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "services": {
                    "trigger_service": "ok",
                    "summarizer_service": "ok",
                    "storage_service": "ok",
                    "injection_service": "ok",
                    "memory_service": "ok"
                },
                "queue_status": queue_status,
                "summarizer_metrics": summarizer_metrics,
                "storage_metrics": storage_metrics
            }

        except Exception as e:
            return {
                "orchestrator": {
                    "enabled": self.enabled,
                    "auto_inject_summaries": self.auto_inject_summaries,
                    "status": "error",
                    "error": str(e)
                },
                "timestamp": datetime.utcnow().isoformat()
            }


# Global orchestrator instance
_orchestrator = None


def get_summarization_orchestrator() -> SummarizationOrchestrator:
    """Get or create summarization orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SummarizationOrchestrator()
    return _orchestrator