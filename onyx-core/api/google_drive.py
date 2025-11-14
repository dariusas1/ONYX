"""
Google Drive API Router

This module provides FastAPI endpoints for Google Drive OAuth and sync operations.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from services.google_oauth import get_oauth_service
from services.sync_scheduler import get_scheduler
from utils.database import get_db_service
from utils.auth import get_current_user, require_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-drive", tags=["Google Drive"])


# Request/Response models
class OAuthCallbackRequest(BaseModel):
    """OAuth callback request"""

    code: str
    state: Optional[str] = None


class SyncRequest(BaseModel):
    """Sync request"""

    full_sync: bool = False
    max_files: Optional[int] = None


class ScheduleSyncRequest(BaseModel):
    """Schedule sync request"""

    interval_minutes: int = 10
    immediate: bool = False


# =============================================================================
# OAuth Endpoints
# =============================================================================


@router.get("/auth/authorize")
async def get_authorization_url(
    current_user: dict = Depends(require_authenticated_user),
    state: Optional[str] = None
):
    """
    Get Google OAuth authorization URL

    Args:
        current_user: Authenticated user from JWT token
        state: Optional state parameter for CSRF protection

    Returns:
        Authorization URL to redirect user to
    """
    try:
        oauth_service = get_oauth_service()
        user_id = current_user["user_id"]

        # Generate state if not provided (include user_id for tracking)
        if not state:
            state = f"user_{user_id}"

        auth_url = oauth_service.get_authorization_url(state=state)

        return {
            "success": True,
            "data": {
                "auth_url": auth_url,
                "state": state,
                "user_id": user_id,
                "message": "Redirect user to this URL to authorize Google Drive access",
            },
        }

    except Exception as e:
        logger.error(f"Failed to generate authorization URL: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to generate authorization URL"
        )


@router.post("/auth/callback")
async def oauth_callback(
    callback_data: OAuthCallbackRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Handle OAuth callback after user authorizes

    Args:
        callback_data: Authorization code and state
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation
    """
    try:
        oauth_service = get_oauth_service()
        user_id = current_user["user_id"]

        # TODO: Validate state parameter matches user session (CSRF protection)
        # if callback_data.state and not validate_state(callback_data.state, user_id):
        #     raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Exchange authorization code for tokens
        access_token, refresh_token, expiry, scopes = oauth_service.exchange_code_for_tokens(
            callback_data.code
        )

        # Store encrypted tokens
        success = oauth_service.store_tokens(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expiry=expiry,
            scopes=scopes,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to store OAuth tokens")

        return {
            "success": True,
            "data": {
                "message": "Google Drive connected successfully",
                "user_id": user_id,
                "scopes": scopes,
            },
        }

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@router.post("/auth/disconnect")
async def disconnect_google_drive(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Disconnect Google Drive for a user (revoke tokens)

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation
    """
    try:
        oauth_service = get_oauth_service()
        user_id = current_user["user_id"]

        # Revoke tokens
        success = oauth_service.revoke_tokens(user_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to revoke tokens")

        # Also unschedule sync jobs
        scheduler = get_scheduler()
        scheduler.unschedule_user_sync(user_id)

        return {
            "success": True,
            "data": {
                "message": "Google Drive disconnected successfully",
                "user_id": user_id,
            },
        }

    except Exception as e:
        logger.error(f"Failed to disconnect Google Drive: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to disconnect: {str(e)}"
        )


@router.get("/auth/status")
async def get_auth_status(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Check if user has authenticated Google Drive

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Authentication status
    """
    try:
        oauth_service = get_oauth_service()
        user_id = current_user["user_id"]
        is_authenticated = oauth_service.is_authenticated(user_id)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "is_authenticated": is_authenticated,
                "provider": "google_drive",
            },
        }

    except Exception as e:
        logger.error(f"Failed to check auth status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to check authentication status"
        )


# =============================================================================
# Sync Endpoints
# =============================================================================


@router.post("/sync")
async def trigger_sync(
    sync_request: SyncRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Trigger a manual Google Drive sync

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
        job_id = await scheduler.trigger_manual_sync(
            user_id=user_id, full_sync=sync_request.full_sync
        )

        if not job_id:
            raise HTTPException(status_code=500, detail="Failed to trigger sync")

        return {
            "success": True,
            "data": {
                "job_id": job_id,
                "user_id": user_id,
                "status": "running",
                "full_sync": sync_request.full_sync,
                "message": "Sync job started successfully",
            },
        }

    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger sync: {str(e)}")


@router.get("/sync/status/{job_id}")
async def get_sync_status(
    job_id: str,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get sync job status

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
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync status: {str(e)}"
        )


@router.get("/sync/history")
async def get_sync_history(
    current_user: dict = Depends(require_authenticated_user),
    limit: int = Query(10, le=50)
):
    """
    Get sync job history for a user

    Args:
        current_user: Authenticated user from JWT token
        limit: Maximum number of jobs to return (max 50)

    Returns:
        List of recent sync jobs
    """
    try:
        db_service = get_db_service()
        user_id = current_user["user_id"]
        jobs = db_service.get_latest_sync_jobs(user_id, limit=limit)

        # Convert to response format
        job_list = [
            {
                "job_id": str(job["id"]),
                "source_type": job["source_type"],
                "status": job["status"],
                "started_at": job["started_at"].isoformat() if job["started_at"] else None,
                "completed_at": job["completed_at"].isoformat() if job["completed_at"] else None,
                "documents_synced": job["documents_synced"],
                "documents_failed": job["documents_failed"],
                "error_message": job.get("error_message"),
            }
            for job in jobs
        ]

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "jobs_count": len(job_list),
                "jobs": job_list,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get sync history: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sync history: {str(e)}"
        )


@router.post("/sync/schedule")
async def schedule_sync(
    schedule_request: ScheduleSyncRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Schedule periodic sync for a user

    Args:
        schedule_request: Scheduling parameters
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation
    """
    try:
        scheduler = get_scheduler()
        user_id = current_user["user_id"]

        # Schedule user sync
        scheduler.schedule_user_sync(
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
                "message": f"Sync scheduled every {schedule_request.interval_minutes} minutes",
            },
        }

    except Exception as e:
        logger.error(f"Failed to schedule sync: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to schedule sync: {str(e)}"
        )


@router.delete("/sync/schedule")
async def unschedule_sync(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Unschedule periodic sync for a user

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Success confirmation
    """
    try:
        scheduler = get_scheduler()
        user_id = current_user["user_id"]
        scheduler.unschedule_user_sync(user_id)

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "message": "Sync unscheduled successfully",
            },
        }

    except Exception as e:
        logger.error(f"Failed to unschedule sync: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to unschedule sync: {str(e)}"
        )


@router.get("/sync/dashboard")
async def get_sync_dashboard(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get comprehensive sync status for dashboard display

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Dashboard data with sync status, statistics, and recent jobs
    """
    try:
        db_service = get_db_service()
        user_id = current_user["user_id"]

        # Get sync state
        sync_state = db_service.get_sync_state(user_id)

        # Get latest sync job
        recent_jobs = db_service.get_latest_sync_jobs(user_id, limit=1)
        latest_job = recent_jobs[0] if recent_jobs else None

        # Get auth status
        oauth_service = get_oauth_service()
        is_authenticated = oauth_service.is_authenticated(user_id)

        # Calculate next sync time (if scheduled)
        scheduler = get_scheduler()
        scheduled_jobs = [
            job for job in scheduler.get_scheduled_jobs() if job["job_id"] == f"sync-{user_id}"
        ]
        next_sync = scheduled_jobs[0]["next_run"] if scheduled_jobs else None

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "is_authenticated": is_authenticated,
                "last_sync_at": sync_state["last_sync_at"].isoformat() if sync_state and sync_state.get("last_sync_at") else None,
                "files_synced": sync_state["files_synced"] if sync_state else 0,
                "files_failed": sync_state["files_failed"] if sync_state else 0,
                "last_error": sync_state.get("last_error") if sync_state else None,
                "latest_job": {
                    "status": latest_job["status"],
                    "started_at": latest_job["started_at"].isoformat() if latest_job["started_at"] else None,
                    "completed_at": latest_job["completed_at"].isoformat() if latest_job["completed_at"] else None,
                    "documents_synced": latest_job["documents_synced"],
                    "documents_failed": latest_job["documents_failed"],
                } if latest_job else None,
                "next_sync_at": next_sync,
                "is_scheduled": len(scheduled_jobs) > 0,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get sync dashboard: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard data: {str(e)}"
        )
