"""
Memory Injection API Endpoints for ONYX

REST API endpoints for memory injection, context building, and agent integration.

Story 4-3: Memory Injection & Agent Integration
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.memory_injection_service import get_memory_injection_service
from services.chat_context_builder import get_chat_context_builder
from services.memory_aware_agent import get_memory_aware_agent, AgentTask
from utils.auth import require_authenticated_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Pydantic Models for API Requests/Responses

class ContextRequest(BaseModel):
    """Request model for building chat context"""
    conversation_id: str = Field(..., description="Conversation UUID")
    current_message: str = Field(..., min_length=1, max_length=5000, description="Current user message")
    recent_history: Optional[List[Dict[str, Any]]] = Field(default=None, description="Recent conversation history")
    max_tokens: Optional[int] = Field(default=4000, ge=1000, le=8000, description="Maximum tokens for context")
    priority_categories: Optional[List[str]] = Field(default=None, description="Categories to prioritize")
    exclude_categories: Optional[List[str]] = Field(default=None, description="Categories to exclude")

    @validator('priority_categories')
    def validate_priority_categories(cls, v):
        if v is not None:
            valid_categories = [
                'priority', 'decision', 'context', 'preference',
                'relationship', 'goal', 'summary'
            ]
            for cat in v:
                if cat not in valid_categories:
                    raise ValueError(f"Invalid category in priority_categories: {cat}")
        return v

    @validator('exclude_categories')
    def validate_exclude_categories(cls, v):
        if v is not None:
            valid_categories = [
                'priority', 'decision', 'context', 'preference',
                'relationship', 'goal', 'summary'
            ]
            for cat in v:
                if cat not in valid_categories:
                    raise ValueError(f"Invalid category in exclude_categories: {cat}")
        return v


class AgentTaskRequest(BaseModel):
    """Request model for agent task execution"""
    task_id: str = Field(..., description="Task UUID")
    description: str = Field(..., min_length=1, max_length=2000, description="Task description")
    task_type: str = Field(..., description="Type of task to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    conversation_id: str = Field(..., description="Conversation UUID")
    priority: str = Field(default="medium", regex="^(low|medium|high|critical)$", description="Task priority")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional task metadata")


class ContextUpdateRequest(BaseModel):
    """Request model for updating conversation context"""
    conversation_id: str = Field(..., description="Conversation UUID")
    new_message: str = Field(..., min_length=1, max_length=5000, description="New message in conversation")
    memory_suggestions: Optional[List[str]] = Field(default=None, description="Suggested memories to extract")


class MemoryAnalyticsRequest(BaseModel):
    """Request model for memory analytics"""
    days: int = Field(default=7, ge=1, le=90, description="Number of days for analytics")


class ContextResponse(BaseModel):
    """Response model for chat context"""
    system_prompt: str
    user_id: str
    conversation_id: str
    memory_injection: Dict[str, Any]
    recent_context: str
    context_build_time_ms: int
    total_tokens_estimate: int
    context_metadata: Dict[str, Any]


class AgentTaskResponse(BaseModel):
    """Response model for agent task execution"""
    task_id: str
    success: bool
    result_data: Dict[str, Any]
    execution_time_ms: int
    memories_extracted: List[Dict[str, Any]]
    errors: List[str] = []


class MemoryAnalyticsResponse(BaseModel):
    """Response model for memory analytics"""
    period_days: int
    total_injections: int
    avg_performance_ms: float
    success_rate: float
    total_memories_injected: int
    cache_hit_rate: float


# API Endpoints

@router.post("/context/build", response_model=Dict[str, Any])
async def build_chat_context(
    request: ContextRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Build LLM context with memory injection for chat

    Args:
        request: Context building request
        background_tasks: FastAPI background tasks
        current_user: Authenticated user from JWT token

    Returns:
        Complete context object with memory injection
    """
    try:
        user_id = current_user["sub"]

        context_builder = get_chat_context_builder()

        # Build context with or without constraints
        if request.priority_categories or request.exclude_categories or request.max_tokens != 4000:
            context = await context_builder.build_context_with_constraints(
                user_id=user_id,
                conversation_id=request.conversation_id,
                current_message=request.current_message,
                max_tokens=request.max_tokens,
                priority_categories=request.priority_categories,
                exclude_categories=request.exclude_categories
            )
        else:
            context = await context_builder.build_context(
                user_id=user_id,
                conversation_id=request.conversation_id,
                current_message=request.current_message,
                recent_history=request.recent_history
            )

        return {
            "success": True,
            "data": context
        }

    except Exception as e:
        logger.error(f"Failed to build chat context: {e}")
        raise HTTPException(
            status_code=500,
            detail="Context building service temporarily unavailable"
        )


@router.post("/context/update", response_model=Dict[str, Any])
async def update_chat_context(
    request: ContextUpdateRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Update conversation context with new message

    Args:
        request: Context update request
        current_user: Authenticated user from JWT token

    Returns:
        Updated context information
    """
    try:
        user_id = current_user["sub"]

        context_builder = get_chat_context_builder()
        update_result = await context_builder.update_context(
            user_id=user_id,
            conversation_id=request.conversation_id,
            new_message=request.new_message,
            new_memory_suggestions=request.memory_suggestions
        )

        return {
            "success": True,
            "data": update_result
        }

    except Exception as e:
        logger.error(f"Failed to update chat context: {e}")
        raise HTTPException(
            status_code=500,
            detail="Context update service temporarily unavailable"
        )


@router.post("/agent/execute", response_model=Dict[str, Any])
async def execute_agent_task(
    request: AgentTaskRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Execute agent task with memory-aware context

    Args:
        request: Agent task request
        background_tasks: FastAPI background tasks
        current_user: Authenticated user from JWT token

    Returns:
        Agent execution result with memory extraction
    """
    try:
        user_id = current_user["sub"]

        # Create agent task
        task = AgentTask(
            task_id=request.task_id,
            description=request.description,
            task_type=request.task_type,
            parameters=request.parameters,
            conversation_id=request.conversation_id,
            priority=request.priority,
            metadata=request.metadata
        )

        # Execute task with memory awareness
        agent = get_memory_aware_agent()
        result = await agent.execute_task(task, user_id)

        return {
            "success": True,
            "data": {
                "task_id": result.task_id,
                "success": result.success,
                "result_data": result.result_data,
                "execution_time_ms": result.execution_time_ms,
                "memories_extracted": result.memories_extracted,
                "errors": result.errors or []
            }
        }

    except Exception as e:
        logger.error(f"Failed to execute agent task: {e}")
        raise HTTPException(
            status_code=500,
            detail="Agent execution service temporarily unavailable"
        )


@router.get("/agent/memory-summary", response_model=Dict[str, Any])
async def get_agent_memory_summary(
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get memory summary relevant to agent execution

    Args:
        task_type: Optional task type filter
        current_user: Authenticated user from JWT token

    Returns:
        Agent memory summary with categorization
    """
    try:
        user_id = current_user["sub"]

        agent = get_memory_aware_agent()
        summary = await agent.get_agent_memory_summary(user_id, task_type)

        return {
            "success": True,
            "data": summary
        }

    except Exception as e:
        logger.error(f"Failed to get agent memory summary: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory summary service temporarily unavailable"
        )


@router.get("/injection/analytics", response_model=Dict[str, Any])
async def get_injection_analytics(
    request: MemoryAnalyticsRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get memory injection analytics

    Args:
        request: Analytics request parameters
        current_user: Authenticated user from JWT token

    Returns:
        Injection analytics and performance metrics
    """
    try:
        user_id = current_user["sub"]

        injection_service = get_memory_injection_service()
        analytics = await injection_service.get_injection_analytics(
            user_id=user_id,
            days=request.days
        )

        return {
            "success": True,
            "data": analytics
        }

    except Exception as e:
        logger.error(f"Failed to get injection analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Analytics service temporarily unavailable"
        )


@router.post("/injection/prepare", response_model=Dict[str, Any])
async def prepare_memory_injection(
    conversation_id: str = Query(..., description="Conversation UUID"),
    current_message: Optional[str] = Query(None, description="Current message for context filtering"),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Prepare memory injection for testing and debugging

    Args:
        conversation_id: Conversation UUID
        current_message: Optional current message
        current_user: Authenticated user from JWT token

    Returns:
        Memory injection details without full context building
    """
    try:
        user_id = current_user["sub"]

        injection_service = get_memory_injection_service()
        injection = await injection_service.prepare_injection(
            user_id=user_id,
            conversation_id=conversation_id,
            current_message=current_message
        )

        return {
            "success": True,
            "data": {
                "user_id": injection.user_id,
                "conversation_id": injection.conversation_id,
                "standing_instructions": injection.standing_instructions,
                "memories": injection.memories,
                "injection_text": injection.injection_text,
                "injection_time_ms": injection.injection_time,
                "performance_stats": injection.performance_stats
            }
        }

    except Exception as e:
        logger.error(f"Failed to prepare memory injection: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory injection service temporarily unavailable"
        )


@router.get("/injection/health", response_model=Dict[str, Any])
async def injection_health_check():
    """Health check for memory injection services"""
    try:
        # Test memory injection service
        injection_service = get_memory_injection_service()
        context_builder = get_chat_context_builder()
        agent = get_memory_aware_agent()

        services_status = {
            "memory_injection_service": "healthy",
            "chat_context_builder": "healthy",
            "memory_aware_agent": "healthy"
        }

        return {
            "success": True,
            "data": {
                "status": "healthy",
                "services": services_status,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

    except Exception as e:
        logger.error(f"Memory injection health check failed: {e}")
        return {
            "success": False,
            "error": {
                "code": "INJECTION_SERVICES_UNHEALTHY",
                "message": "Memory injection services are unhealthy",
                "details": str(e)
            }
        }


@router.post("/injection/clear-cache", response_model=Dict[str, Any])
async def clear_injection_cache(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Clear memory injection cache for user

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Cache clearing status
    """
    try:
        user_id = current_user["sub"]

        injection_service = get_memory_injection_service()

        # Clear cache entries for this user
        cache_keys_to_remove = [
            key for key in injection_service.cache.keys()
            if key.startswith(f"{user_id}:")
        ]

        for key in cache_keys_to_remove:
            del injection_service.cache[key]

        return {
            "success": True,
            "data": {
                "cache_entries_cleared": len(cache_keys_to_remove),
                "user_id": user_id,
                "message": "Cache cleared successfully"
            }
        }

    except Exception as e:
        logger.error(f"Failed to clear injection cache: {e}")
        raise HTTPException(
            status_code=500,
            detail="Cache clearing service temporarily unavailable"
        )