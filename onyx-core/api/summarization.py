"""
Summarization API Endpoints for ONYX

REST API endpoints for managing and monitoring the auto-summarization pipeline.

Story 4-4: Auto-Summarization Pipeline
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from services.summarization_trigger_service import get_summarization_trigger_service
from services.conversation_summarizer import get_conversation_summarizer, SummarizationRequest
from services.summary_memory_storage import get_summary_memory_storage
from config.summarization_config import get_summarization_config

router = APIRouter(prefix="/summarization", tags=["summarization"])


# Pydantic models for API
class SummarizationTriggerRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID to check for triggers")
    message_id: str = Field(..., description="Current message ID")
    user_id: str = Field(..., description="User ID")


class SummarizationStatusResponse(BaseModel):
    triggered: bool
    message_count: Optional[int] = None
    trigger_interval: int
    cooldown_remaining: Optional[int] = None


class ConversationSummaryResponse(BaseModel):
    id: str
    conversation_id: str
    summary_text: str
    message_range_start: int
    message_range_end: int
    key_topics: List[str]
    sentiment_score: float
    confidence_score: float
    processing_time_ms: Optional[int]
    model_used: str
    created_at: datetime


class QueueStatusResponse(BaseModel):
    queue_length: int
    processing_count: int
    trigger_interval: int
    cooldown_period: int
    last_24_hours: Dict[str, Any]


class WorkerMetricsResponse(BaseModel):
    worker_id: str
    uptime_seconds: float
    jobs_processed: int
    jobs_successful: int
    jobs_failed: int
    success_rate_percent: float
    avg_processing_time_ms: float


class ServiceHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    config: Dict[str, Any]
    queue_status: QueueStatusResponse
    summarizer_metrics: Dict[str, Any]
    storage_metrics: Dict[str, Any]


# Dependencies
def get_trigger_service():
    """Get summarization trigger service instance"""
    return get_summarization_trigger_service()


def get_summarizer_service():
    """Get conversation summarizer service instance"""
    return get_conversation_summarizer()


def get_storage_service():
    """Get summary memory storage service instance"""
    return get_summary_memory_storage()


def get_config():
    """Get summarization configuration"""
    return get_summarization_config()


# =========================================================================
# Core Summarization Endpoints
# =========================================================================

@router.post("/trigger", response_model=SummarizationStatusResponse)
async def trigger_summarization_check(
    request: SummarizationTriggerRequest,
    trigger_service = Depends(get_trigger_service),
    config = Depends(get_config)
):
    """
    Check if summarization should be triggered for a conversation

    This endpoint is called after each message to determine if auto-summarization
    should be triggered based on message count and cooldown period.
    """
    try:
        # Check if summarization should be triggered
        trigger = await trigger_service.should_trigger_summarization(
            conversation_id=request.conversation_id,
            message_id=request.message_id,
            user_id=request.user_id
        )

        if trigger:
            # Process the trigger
            success = await trigger_service.process_trigger(trigger)

            return SummarizationStatusResponse(
                triggered=success,
                message_count=trigger.message_count,
                trigger_interval=config.TRIGGER_INTERVAL,
                cooldown_remaining=None
            )
        else:
            return SummarizationStatusResponse(
                triggered=False,
                trigger_interval=config.TRIGGER_INTERVAL,
                cooldown_remaining=None
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking summarization trigger: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/summaries", response_model=List[ConversationSummaryResponse])
async def get_conversation_summaries(
    conversation_id: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of summaries to return"),
    storage_service = Depends(get_storage_service)
):
    """Get all summaries for a specific conversation"""
    try:
        summaries = await storage_service.get_conversation_summaries(conversation_id, limit)

        return [
            ConversationSummaryResponse(**summary)
            for summary in summaries
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversation summaries: {str(e)}"
        )


@router.get("/users/{user_id}/summary-memories")
async def get_user_summary_memories(
    user_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of memories to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    storage_service = Depends(get_storage_service)
):
    """Get summary memories for a user"""
    try:
        memories = await storage_service.get_user_summary_memories(user_id, limit, days)

        return {
            "user_id": user_id,
            "memories": memories,
            "total_count": len(memories),
            "days": days,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user summary memories: {str(e)}"
        )


# =========================================================================
# Monitoring and Analytics Endpoints
# =========================================================================

@router.get("/status/queue", response_model=QueueStatusResponse)
async def get_queue_status(
    trigger_service = Depends(get_trigger_service)
):
    """Get current queue status and processing metrics"""
    try:
        status = await trigger_service.get_queue_status()

        if "error" in status:
            raise HTTPException(status_code=500, detail=status["error"])

        return QueueStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting queue status: {str(e)}"
        )


@router.get("/status/service", response_model=ServiceHealthResponse)
async def get_service_health(
    trigger_service = Depends(get_trigger_service),
    summarizer_service = Depends(get_summarizer_service),
    storage_service = Depends(get_storage_service),
    config = Depends(get_config)
):
    """Get comprehensive service health and metrics"""
    try:
        # Get status from all services
        queue_status = await trigger_service.get_queue_status()
        summarizer_metrics = await summarizer_service.get_service_metrics()
        storage_metrics = await storage_service.get_service_metrics()

        return ServiceHealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            config=config.to_dict(),
            queue_status=QueueStatusResponse(**queue_status),
            summarizer_metrics=summarizer_metrics,
            storage_metrics=storage_metrics
        )

    except Exception as e:
        return ServiceHealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            config=config.to_dict(),
            queue_status=QueueStatusResponse(queue_length=0, processing_count=0, trigger_interval=0, cooldown_period=0, last_24_hours={}),
            summarizer_metrics={"error": str(e)},
            storage_metrics={"error": str(e)}
        )


@router.get("/metrics/performance")
async def get_performance_metrics(
    hours: int = Query(24, ge=1, le=168, description="Hours of data to analyze"),
    trigger_service = Depends(get_trigger_service)
):
    """Get detailed performance metrics for the specified time period"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        # Get database connection
        config = get_config()
        conn = psycopg2.connect(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD
        )

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get performance stats using the database function
                cur.execute(
                    "SELECT * FROM get_summarization_performance_stats(%s)",
                    (hours,)
                )
                perf_stats = cur.fetchone()

                # Get trigger analytics
                cur.execute(
                    "SELECT * FROM get_trigger_analytics(%s)",
                    (hours,)
                )
                trigger_stats = cur.fetchone()

                return {
                    "period_hours": hours,
                    "performance_stats": dict(perf_stats) if perf_stats else {},
                    "trigger_stats": dict(trigger_stats) if trigger_stats else {},
                    "timestamp": datetime.utcnow().isoformat()
                }

        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving performance metrics: {str(e)}"
        )


@router.get("/metrics/recent-failures")
async def get_recent_failures(
    hours: int = Query(24, ge=1, le=168, description="Hours of failure data to retrieve"),
    trigger_service = Depends(get_trigger_service)
):
    """Get recent summarization failures for debugging"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        config = get_config()
        conn = psycopg2.connect(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DB,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD
        )

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM recent_summarization_failures
                    WHERE created_at > NOW() - INTERVAL '%s hours'
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    (hours,)
                )
                failures = cur.fetchall()

                return {
                    "period_hours": hours,
                    "total_failures": len(failures),
                    "failures": [dict(failure) for failure in failures],
                    "timestamp": datetime.utcnow().isoformat()
                }

        finally:
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving recent failures: {str(e)}"
        )


# =========================================================================
# Management Endpoints
# =========================================================================

@router.post("/admin/cleanup/metrics")
async def cleanup_old_metrics(
    background_tasks: BackgroundTasks,
    days_to_keep: int = Query(90, ge=7, le=365, description="Days of metrics to keep"),
    trigger_service = Depends(get_trigger_service)
):
    """Clean up old metrics data (admin only)"""
    try:
        # Run cleanup in background
        background_tasks.add_task(
            storage_service.cleanup_old_summaries,
            days_to_keep
        )

        return {
            "message": f"Cleanup task started for data older than {days_to_keep} days",
            "task_queued": True
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting cleanup task: {str(e)}"
        )


@router.post("/admin/queue/clear-processing-flags")
async def clear_processing_flags(
    trigger_service = Depends(get_trigger_service)
):
    """Clear all processing flags (admin only - use for recovery)"""
    try:
        cleared_count = await trigger_service.clear_processing_flags()

        return {
            "message": f"Processing flags cleared successfully",
            "flags_cleared": cleared_count
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing processing flags: {str(e)}"
        )


@router.get("/admin/config", response_model=Dict[str, Any])
async def get_configuration(config = Depends(get_config)):
    """Get current summarization configuration (admin only)"""
    return {
        "configuration": config.to_dict(),
        "validation_errors": config.validate(),
        "is_production": config.is_production()
    }


@router.post("/admin/config/reload", response_model=Dict[str, Any])
async def reload_configuration():
    """Reload configuration from environment (admin only)"""
    try:
        from config.summarization_config import reload_summarization_config
        new_config = reload_summarization_config()

        validation_errors = new_config.validate()

        return {
            "message": "Configuration reloaded successfully",
            "new_config": new_config.to_dict(),
            "validation_errors": validation_errors,
            "is_production": new_config.is_production()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reloading configuration: {str(e)}"
        )


# =========================================================================
# Health Check Endpoint
# =========================================================================

@router.get("/health")
async def health_check(
    trigger_service = Depends(get_trigger_service),
    summarizer_service = Depends(get_summarizer_service),
    storage_service = Depends(get_storage_service)
):
    """Simple health check endpoint"""
    try:
        # Basic connectivity check
        queue_status = await trigger_service.get_queue_status()

        if "error" in queue_status:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": queue_status["error"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "trigger_service": "ok",
                "summarizer_service": "ok",
                "storage_service": "ok"
            }
        }

    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )