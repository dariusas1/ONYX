"""
Summarization API Endpoints
Story 4-4: Auto-Summarization Pipeline

REST API endpoints for managing conversation summaries and monitoring
the auto-summarization pipeline.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field
import asyncpg
import redis
import json

from ..services.summarization.trigger_service import create_summarization_trigger_service
from ..services.summarization.storage import create_summary_memory_storage
from ..workers.summarization_worker import create_summarization_worker

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class SummaryResponse(BaseModel):
    id: str
    conversation_id: str
    summary: str
    key_topics: List[str]
    sentiment: float
    confidence: float
    message_range: Dict[str, int]
    processing_time: int
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SummaryStatistics(BaseModel):
    total_summaries: int
    sentiment_distribution: Dict[str, int]
    avg_processing_time_ms: int
    recent_summaries_7d: int
    updated_at: datetime

class PipelineMetrics(BaseModel):
    trigger_service: Dict[str, Any]
    worker: Dict[str, Any]
    storage: Dict[str, Any]
    updated_at: datetime

class TriggerSummaryRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID to trigger summarization for")

# Create router
router = APIRouter(prefix="/summarization", tags=["summarization"])

# Dependency to get database pool
async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool."""
    # This should be implemented based on your app's dependency injection
    # For now, we'll return a placeholder
    raise NotImplementedError("Database pool dependency not implemented")

# Dependency to get Redis client
async def get_redis_client() -> redis.Redis:
    """Get Redis client."""
    # This should be implemented based on your app's dependency injection
    # For now, we'll return a placeholder
    raise NotImplementedError("Redis client dependency not implemented")

@router.post("/trigger", response_model=Dict[str, Any])
async def trigger_summarization(
    request: TriggerSummaryRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Manually trigger summarization for a conversation.

    This endpoint allows manual triggering of the summarization process
    for testing or on-demand summarization.
    """
    try:
        # Initialize trigger service
        trigger_service = await create_summarization_trigger_service(db_pool, redis_client)

        # Check if trigger should occur
        trigger = await trigger_service.should_trigger(request.conversation_id)

        if not trigger:
            return {
                "success": False,
                "message": "No summarization trigger needed for this conversation",
                "conversation_id": request.conversation_id
            }

        # Process the trigger
        success = await trigger_service.process_trigger(trigger)

        await trigger_service.close()

        return {
            "success": success,
            "message": "Summarization job queued successfully" if success else "Failed to queue summarization job",
            "conversation_id": request.conversation_id,
            "trigger": {
                "message_count": trigger.message_count,
                "created_at": trigger.created_at.isoformat()
            }
        }

    except Exception as error:
        logger.error(f"Error triggering summarization: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@router.get("/conversations/{conversation_id}/summaries", response_model=List[SummaryResponse])
async def get_conversation_summaries(
    conversation_id: str = Path(..., description="Conversation ID"),
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of summaries to return"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get all summaries for a specific conversation.
    """
    try:
        # Initialize storage service
        storage = create_summary_memory_storage(db_pool)

        # Get summaries
        summaries = await storage.get_conversation_summaries(conversation_id, user_id, limit)

        # Convert to response models
        response_summaries = []
        for summary in summaries:
            response_summary = SummaryResponse(
                id=summary.id,
                conversation_id=summary.conversation_id,
                summary=summary.summary,
                key_topics=summary.key_topics,
                sentiment=summary.sentiment,
                confidence=summary.confidence,
                message_range=summary.message_range,
                processing_time=summary.processing_time,
                created_at=summary.created_at
            )
            response_summaries.append(response_summary)

        return response_summaries

    except Exception as error:
        logger.error(f"Error getting conversation summaries: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@router.get("/users/{user_id}/summaries", response_model=List[SummaryResponse])
async def get_user_summaries(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of summaries to return"),
    offset: int = Query(0, ge=0, description="Number of summaries to skip"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get summaries for a user across all conversations.
    """
    try:
        # Initialize storage service
        storage = create_summary_memory_storage(db_pool)

        # Get summaries
        summaries = await storage.get_user_summaries(user_id, limit, offset)

        # Convert to response models
        response_summaries = []
        for summary in summaries:
            response_summary = SummaryResponse(
                id=summary.id,
                conversation_id=summary.conversation_id,
                summary=summary.summary,
                key_topics=summary.key_topics,
                sentiment=summary.sentiment,
                confidence=summary.confidence,
                message_range=summary.message_range,
                processing_time=summary.processing_time,
                created_at=summary.created_at
            )
            response_summaries.append(response_summary)

        return response_summaries

    except Exception as error:
        logger.error(f"Error getting user summaries: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@router.get("/users/{user_id}/statistics", response_model=SummaryStatistics)
async def get_user_summary_statistics(
    user_id: str = Path(..., description="User ID"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get statistics about summaries for a user.
    """
    try:
        # Initialize storage service
        storage = create_summary_memory_storage(db_pool)

        # Get statistics
        stats = await storage.get_summary_statistics(user_id)

        return SummaryStatistics(**stats)

    except Exception as error:
        logger.error(f"Error getting summary statistics: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@router.delete("/summaries/{summary_id}")
async def delete_summary(
    summary_id: str = Path(..., description="Summary ID"),
    user_id: str = Query(..., description="User ID for authorization"),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Soft delete a summary.
    """
    try:
        # Initialize storage service
        storage = create_summary_memory_storage(db_pool)

        # Delete summary
        success = await storage.delete_summary(summary_id, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Summary not found or access denied")

        return {"message": "Summary deleted successfully"}

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error deleting summary: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@router.get("/metrics", response_model=PipelineMetrics)
async def get_pipeline_metrics(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Get comprehensive metrics for the summarization pipeline.
    """
    try:
        # Initialize services
        trigger_service = await create_summarization_trigger_service(db_pool, redis_client)
        storage = create_summary_memory_storage(db_pool)

        # Get worker metrics (if worker is running)
        worker_metrics = {}
        try:
            # Note: In a real implementation, you'd have a way to access the running worker
            # For now, we'll return basic queue metrics
            worker_metrics = {
                "status": "not_running",
                "message": "Worker metrics not available - worker not initialized in API context"
            }
        except Exception as error:
            logger.warning(f"Could not get worker metrics: {error}")
            worker_metrics = {"error": str(error)}

        # Get metrics from all services
        trigger_metrics = await trigger_service.get_metrics()
        storage_metrics = await storage.get_metrics()

        await trigger_service.close()

        return PipelineMetrics(
            trigger_service=trigger_metrics,
            worker=worker_metrics,
            storage=storage_metrics,
            updated_at=datetime.utcnow()
        )

    except Exception as error:
        logger.error(f"Error getting pipeline metrics: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@router.post("/test-connection")
async def test_connections(
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    redis_client: redis.Redis = Depends(get_redis_client)
):
    """
    Test connections to all required services.
    """
    try:
        # Test database connection
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_status = "connected"
        except Exception as error:
            db_status = f"error: {error}"

        # Test Redis connection
        try:
            redis_client.ping()
            redis_status = "connected"
        except Exception as error:
            redis_status = f"error: {error}"

        # Test LiteLLM connection (optional)
        litellm_status = "not_tested"
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get("http://litellm-proxy:4000/health")
                if response.status_code == 200:
                    litellm_status = "connected"
                else:
                    litellm_status = f"error: {response.status_code}"
        except Exception as error:
            litellm_status = f"error: {error}"

        return {
            "database": db_status,
            "redis": redis_status,
            "litellm": litellm_status,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as error:
        logger.error(f"Error testing connections: {error}")
        raise HTTPException(status_code=500, detail=str(error))

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "summarization-api",
        "timestamp": datetime.utcnow().isoformat()
    }