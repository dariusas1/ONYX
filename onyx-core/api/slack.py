"""
Slack API Router

This module provides FastAPI endpoints for Slack authentication, sync operations,
and status monitoring.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from services.slack_client import get_slack_client
from services.slack_sync_service import get_slack_sync_service
from services.sync_scheduler import get_scheduler
from services.google_oauth import get_oauth_service  # Reuse encryption utilities
from utils.database import get_db_service
from utils.auth import get_current_user, require_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/slack", tags=["Slack"])


# Request/Response models
class SlackAuthRequest(BaseModel):
    """Slack authentication request"""
    bot_token: str


class SlackSyncRequest(BaseModel):
    """Slack sync request"""
    full_sync: bool = False
    channel_ids: Optional[List[str]] = None


class SlackScheduleRequest(BaseModel):
    """Slack schedule sync request"""
    interval_minutes: int = 10
    immediate: bool = False


class SlackChannelResponse(BaseModel):
    """Slack channel information"""
    id: str
    name: Optional[str]
    type: str
    is_private: bool
    is_member: bool
    last_sync_at: Optional[str]
    messages_count: int
    sync_status: str


# =============================================================================
# Authentication Endpoints
# =============================================================================


@router.post("/auth/connect")
async def connect_slack(
    auth_data: SlackAuthRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Connect Slack workspace with bot token

    Args:
        auth_data: Bot token for Slack workspace
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation with workspace information
    """
    try:
        slack_client = get_slack_client()
        user_id = current_user["user_id"]

        # Validate bot token
        validation_result = await slack_client.validate_token(auth_data.bot_token)

        if not validation_result.get("ok"):
            raise HTTPException(
                status_code=400, detail=f"Invalid Slack token: {validation_result.get('error', 'Unknown error')}"
            )

        # Encrypt and store token using existing OAuth infrastructure
        oauth_service = get_oauth_service()

        # Note: Slack doesn't use refresh tokens, but we store access token
        success = oauth_service.store_tokens(
            user_id=user_id,
            access_token=auth_data.bot_token,
            refresh_token="",  # Slack doesn't use refresh tokens for bots
            expiry=None,  # Bot tokens don't expire unless revoked
            scopes=validation_result.get("bot_scopes", []),
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to store Slack token")

        # Update sync state with team information
        db_service = get_db_service()
        await db_service.update_slack_sync_state(
            user_id=user_id,
            team_id=validation_result["team_id"],
            team_name=validation_result["team_name"],
            bot_user_id=validation_result["bot_user_id"]
        )

        return {
            "success": True,
            "data": {
                "message": "Slack workspace connected successfully",
                "team_id": validation_result["team_id"],
                "team_name": validation_result["team_name"],
                "bot_user_id": validation_result["bot_user_id"],
                "bot_name": validation_result["bot_name"],
                "scopes": validation_result["bot_scopes"],
                "user_id": user_id,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Slack connection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Slack connection failed: {str(e)}")


@router.post("/auth/disconnect")
async def disconnect_slack(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Disconnect Slack workspace for a user

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation
    """
    try:
        user_id = current_user["user_id"]
        oauth_service = get_oauth_service()

        # Delete OAuth tokens
        success = oauth_service.delete_tokens(user_id, "slack")

        if not success:
            raise HTTPException(status_code=500, detail="Failed to disconnect Slack workspace")

        # Unschedule sync jobs
        scheduler = get_scheduler()
        scheduler.unschedule_slack_sync(user_id)

        return {
            "success": True,
            "data": {
                "message": "Slack workspace disconnected successfully",
                "user_id": user_id,
            },
        }

    except Exception as e:
        logger.error(f"Failed to disconnect Slack: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to disconnect: {str(e)}"
        )


@router.get("/auth/status")
async def get_slack_auth_status(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Check if user has authenticated Slack workspace

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Authentication status and workspace information
    """
    try:
        user_id = current_user["user_id"]
        db_service = get_db_service()
        oauth_service = get_oauth_service()

        # Check OAuth token exists
        oauth_tokens = oauth_service.get_tokens(user_id, "slack")
        has_token = bool(oauth_tokens)

        # Get sync state for additional info
        sync_state = db_service.get_slack_sync_state(user_id)

        auth_info = {
            "user_id": user_id,
            "is_authenticated": has_token,
            "provider": "slack",
            "has_sync_data": sync_state is not None,
        }

        if sync_state:
            auth_info.update({
                "team_id": sync_state.get("team_id"),
                "team_name": sync_state.get("team_name"),
                "bot_user_id": sync_state.get("bot_user_id"),
                "last_sync_at": sync_state.get("last_sync_at").isoformat() if sync_state.get("last_sync_at") else None,
                "channels_synced": sync_state.get("channels_synced", 0),
                "messages_synced": sync_state.get("messages_synced", 0),
                "last_error": sync_state.get("last_error"),
            })

        return {
            "success": True,
            "data": auth_info,
        }

    except Exception as e:
        logger.error(f"Failed to check Slack auth status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to check authentication status"
        )


# =============================================================================
# Sync Endpoints
# =============================================================================


@router.post("/sync")
async def trigger_slack_sync(
    sync_request: SlackSyncRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Trigger a manual Slack sync

    Args:
        sync_request: Sync parameters
        current_user: Authenticated user from JWT token

    Returns:
        Sync job ID and status
    """
    try:
        scheduler = get_scheduler()
        user_id = current_user["user_id"]

        # Trigger manual sync
        job_id = await scheduler.trigger_slack_sync(
            user_id=user_id,
            full_sync=sync_request.full_sync,
            channel_ids=sync_request.channel_ids
        )

        if not job_id:
            raise HTTPException(status_code=500, detail="Failed to trigger Slack sync")

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "user_id": user_id,
                "status": "running",
                "full_sync": sync_request.full_sync,
                "channel_ids": sync_request.channel_ids,
                "message": "Slack sync job started successfully",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger Slack sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger sync: {str(e)}")


@router.get("/sync/status/{job_id}")
async def get_slack_sync_status(
    job_id: str,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get Slack sync job status

    Args:
        job_id: Sync job UUID
        current_user: Authenticated user from JWT token

    Returns:
        Job status and details
    """
    try:
        db_service = get_db_service()
        job = db_service.get_sync_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Sync job not found")

        # Verify the job belongs to the authenticated user
        if str(job["user_id"]) != current_user["user_id"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: This sync job belongs to another user"
            )

        # Filter for Slack jobs
        if job["source_type"] != "slack":
            raise HTTPException(status_code=404, detail="Slack sync job not found")

        return {
            "success": True,
            "data": {
                "job_id": job["id"],
                "user_id": str(job["user_id"]),
                "source_type": job["source_type"],
                "status": job["status"],
                "started_at": job["started_at"].isoformat() if job["started_at"] else None,
                "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
                "documents_synced": job["documents_synced"],
                "documents_failed": job["documents_failed"],
                "error_message": job["error_message"],
                "error_details": job.get("error_details"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Slack sync status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync status: {str(e)}"
        )


@router.get("/sync/dashboard")
async def get_slack_sync_dashboard(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get comprehensive Slack sync status for dashboard display

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Dashboard data with sync status, statistics, and recent jobs
    """
    try:
        user_id = current_user["user_id"]
        slack_service = get_slack_sync_service()

        # Get sync status
        sync_status = await slack_service.get_sync_status(user_id)

        # Get latest sync job
        db_service = get_db_service()
        recent_jobs = db_service.get_latest_sync_jobs(user_id, limit=5)
        latest_slack_job = None
        for job in recent_jobs:
            if job["source_type"] == "slack":
                latest_slack_job = job
                break

        # Get scheduled jobs
        scheduler = get_scheduler()
        scheduled_jobs = scheduler.get_slack_scheduled_jobs()
        user_scheduled_job = next(
            (job for job in scheduled_jobs if job["user_id"] == user_id), None
        )

        # Get channels status
        channels = db_service.get_slack_channels(user_id)
        channels_summary = {
            "total": len(channels),
            "synced": len([c for c in channels if c["sync_status"] == "completed"]),
            "failed": len([c for c in channels if c["sync_status"] == "failed"]),
            "pending": len([c for c in channels if c["sync_status"] == "pending"]),
            "syncing": len([c for c in channels if c["sync_status"] == "syncing"]),
        }

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "sync_status": sync_status,
                "channels": channels_summary,
                "latest_job": {
                    "status": latest_slack_job["status"],
                    "started_at": latest_slack_job["started_at"].isoformat() if latest_slack_job["started_at"] else None,
                    "completed_at": latest_slack_job["completed_at"].isoformat() if latest_slack_job["completed_at"] else None,
                    "documents_synced": latest_slack_job["documents_synced"],
                    "documents_failed": latest_slack_job["documents_failed"],
                    "error_message": latest_slack_job.get("error_message"),
                } if latest_slack_job else None,
                "next_sync_at": user_scheduled_job["next_run"] if user_scheduled_job else None,
                "is_scheduled": user_scheduled_job is not None,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get Slack sync dashboard: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard data: {str(e)}"
        )


@router.post("/sync/schedule")
async def schedule_slack_sync(
    schedule_request: SlackScheduleRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Schedule periodic Slack sync for a user

    Args:
        schedule_request: Scheduling parameters
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation
    """
    try:
        scheduler = get_scheduler()
        user_id = current_user["user_id"]

        # Schedule Slack sync
        scheduler.schedule_slack_sync(
            user_id=user_id,
            interval_minutes=schedule_request.interval_minutes,
            immediate=schedule_request.immediate,
        )

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "interval_minutes": schedule_request.interval_minutes,
                "immediate": schedule_request.immediate,
                "message": f"Slack sync scheduled every {schedule_request.interval_minutes} minutes",
            },
        }

    except Exception as e:
        logger.error(f"Failed to schedule Slack sync: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule sync: {str(e)}"
        )


@router.delete("/sync/schedule")
async def unschedule_slack_sync(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Unschedule periodic Slack sync for a user

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation
    """
    try:
        scheduler = get_scheduler()
        user_id = current_user["user_id"]
        scheduler.unschedule_slack_sync(user_id)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "message": "Slack sync unscheduled successfully",
            },
        }

    except Exception as e:
        logger.error(f"Failed to unschedule Slack sync: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to unschedule sync: {str(e)}"
        )


# =============================================================================
# Channels Endpoints
# =============================================================================


@router.get("/channels")
async def get_slack_channels(
    current_user: dict = Depends(require_authenticated_user),
    include_archived: bool = Query(False, description="Include archived channels"),
    sync_status: Optional[str] = Query(None, description="Filter by sync status"),
):
    """
    Get Slack channels accessible to the bot

    Args:
        current_user: Authenticated user from JWT token
        include_archived: Whether to include archived channels
        sync_status: Filter channels by sync status

    Returns:
        List of channels with sync status
    """
    try:
        user_id = current_user["user_id"]
        db_service = get_db_service()

        # Get channels from database
        channels = db_service.get_slack_channels(
            user_id=user_id,
            include_archived=include_archived,
            sync_status=sync_status
        )

        # Format response
        channel_list = []
        for channel in channels:
            channel_list.append({
                "id": channel["channel_id"],
                "name": channel["channel_name"],
                "type": channel["channel_type"],
                "is_private": channel["channel_type"] in ["private_channel", "im", "mpim"],
                "is_archived": channel["is_archived"],
                "is_member": channel["is_member"],
                "last_sync_at": channel["last_sync_at"].isoformat() if channel["last_sync_at"] else None,
                "messages_count": channel["messages_count"],
                "sync_status": channel["sync_status"],
                "error_message": channel.get("error_message"),
            })

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "channels_count": len(channel_list),
                "channels": channel_list,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get Slack channels: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get channels: {str(e)}"
        )


# =============================================================================
# Health Check Endpoints
# =============================================================================


@router.get("/health")
async def health_check():
    """Health check for Slack service"""
    return {
        "success": True,
        "data": {
            "service": "slack",
            "status": "healthy",
            "timestamp": "2025-11-15T00:00:00Z",  # Would use actual timestamp
        },
    }