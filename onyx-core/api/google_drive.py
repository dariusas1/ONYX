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
from services.google_docs_edit import get_google_docs_edit_service
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
# Google Docs Editing Request/Response Models
# =============================================================================


class InsertContentRequest(BaseModel):
    """Request to insert content into Google Doc"""

    document_id: str = ...
    content_markdown: str = ...
    position: str = "end"  # beginning, end, after_heading, before_heading, offset
    heading_text: Optional[str] = None
    offset: Optional[int] = None

    class Config:
        schema_extra = {
            "example": {
                "document_id": "1abc123...",
                "content_markdown": "# New Section\n\nThis is new content.",
                "position": "end",
            }
        }


class ReplaceContentRequest(BaseModel):
    """Request to replace content in Google Doc"""

    document_id: str = ...
    search_text: str = ...
    replacement_markdown: str = ...
    use_regex: bool = False
    replace_all: bool = True

    class Config:
        schema_extra = {
            "example": {
                "document_id": "1abc123...",
                "search_text": "TODO",
                "replacement_markdown": "✓ DONE",
                "use_regex": False,
                "replace_all": True,
            }
        }


class UpdateFormattingRequest(BaseModel):
    """Request to update formatting in Google Doc"""

    document_id: str = ...
    start_index: int = ...
    end_index: int = ...
    formatting: Dict[str, Any] = {}

    class Config:
        schema_extra = {
            "example": {
                "document_id": "1abc123...",
                "start_index": 50,
                "end_index": 100,
                "formatting": {
                    "bold": True,
                    "fontSize": 14,
                },
            }
        }


class EditGoogleDocResponse(BaseModel):
    """Response from Google Docs edit operation"""

    success: bool = ...
    message: str = ...
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = 0

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Successfully inserted 245 characters",
                "data": {
                    "content_id_ranges": [],
                    "character_inserted": 245,
                },
                "execution_time_ms": 450,
            }
        }


# =============================================================================
# OAuth Endpoints
# =============================================================================


@router.get("/auth/authorize")
async def get_authorization_url(
    current_user: dict = Depends(require_authenticated_user),
    state: Optional[str] = None,
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
    current_user: dict = Depends(require_authenticated_user),
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
        access_token, refresh_token, expiry, scopes = (
            oauth_service.exchange_code_for_tokens(callback_data.code)
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
    current_user: dict = Depends(require_authenticated_user),
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
        raise HTTPException(status_code=500, detail=f"Failed to disconnect: {str(e)}")


@router.get("/auth/status")
async def get_auth_status(current_user: dict = Depends(require_authenticated_user)):
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
    sync_request: SyncRequest, current_user: dict = Depends(require_authenticated_user)
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
    job_id: str, current_user: dict = Depends(require_authenticated_user)
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
                detail="Access denied: This sync job belongs to another user",
            )

        return {
            "success": True,
            "data": {
                "job_id": job["id"],
                "user_id": str(job["user_id"]),
                "source_type": job["source_type"],
                "status": job["status"],
                "started_at": job["started_at"].isoformat()
                if job["started_at"]
                else None,
                "completed_at": job["completed_at"].isoformat()
                if job["completed_at"]
                else None,
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
    limit: int = Query(10, le=50),
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
                "started_at": job["started_at"].isoformat()
                if job["started_at"]
                else None,
                "completed_at": job["completed_at"].isoformat()
                if job["completed_at"]
                else None,
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
    current_user: dict = Depends(require_authenticated_user),
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
async def unschedule_sync(current_user: dict = Depends(require_authenticated_user)):
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
async def get_sync_dashboard(current_user: dict = Depends(require_authenticated_user)):
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
            job
            for job in scheduler.get_scheduled_jobs()
            if job["job_id"] == f"sync-{user_id}"
        ]
        next_sync = scheduled_jobs[0]["next_run"] if scheduled_jobs else None

        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "is_authenticated": is_authenticated,
                "last_sync_at": sync_state["last_sync_at"].isoformat()
                if sync_state and sync_state.get("last_sync_at")
                else None,
                "files_synced": sync_state["files_synced"] if sync_state else 0,
                "files_failed": sync_state["files_failed"] if sync_state else 0,
                "last_error": sync_state.get("last_error") if sync_state else None,
                "latest_job": {
                    "status": latest_job["status"],
                    "started_at": latest_job["started_at"].isoformat()
                    if latest_job["started_at"]
                    else None,
                    "completed_at": latest_job["completed_at"].isoformat()
                    if latest_job["completed_at"]
                    else None,
                    "documents_synced": latest_job["documents_synced"],
                    "documents_failed": latest_job["documents_failed"],
                }
                if latest_job
                else None,
                "next_sync_at": next_sync,
                "is_scheduled": len(scheduled_jobs) > 0,
            },
        }

    except Exception as e:
        logger.error(f"Failed to get sync dashboard: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get dashboard data: {str(e)}"
        )


# =============================================================================
# Google Docs Editing Endpoints (Story 6-3)
# =============================================================================


@router.post("/docs/insert", response_model=EditGoogleDocResponse)
async def insert_content(
    request: InsertContentRequest,
    current_user: dict = Depends(require_authenticated_user),
) -> EditGoogleDocResponse:
    """
    Insert content at specified position in a Google Doc

    AC6.3.1: Agent can invoke edit_google_doc tool with document_id and action parameters
    AC6.3.2: Content insertion works at specified positions (beginning, middle, end)
    AC6.3.9: Markdown input properly converted to Google Docs format during editing
    AC6.3.10: Document metadata updated with edit timestamp and agent context

    Args:
        request: Insert content request
        current_user: Authenticated user from JWT token

    Returns:
        EditGoogleDocResponse with operation results
    """
    try:
        user_id = current_user["user_id"]

        # Get edit service for user
        edit_service = get_google_docs_edit_service(user_id)

        # Insert content
        result = edit_service.insert_content(
            document_id=request.document_id,
            content_markdown=request.content_markdown,
            position=request.position,
            heading_text=request.heading_text,
            offset=request.offset,
        )

        if result["success"]:
            return EditGoogleDocResponse(
                success=True,
                message=result["message"],
                data={
                    "content_id_ranges": result.get("content_id_ranges", []),
                    "character_inserted": result.get("character_inserted", 0),
                },
                execution_time_ms=result.get("execution_time_ms", 0),
            )
        else:
            return EditGoogleDocResponse(
                success=False,
                message="Insert operation failed",
                error=result.get("error", "Unknown error"),
                execution_time_ms=result.get("execution_time_ms", 0),
            )

    except ValueError as e:
        logger.error(f"Invalid input for insert operation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Insert content operation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Insert operation failed: {str(e)}"
        )


@router.post("/docs/replace", response_model=EditGoogleDocResponse)
async def replace_content(
    request: ReplaceContentRequest,
    current_user: dict = Depends(require_authenticated_user),
) -> EditGoogleDocResponse:
    """
    Replace text in a Google Doc

    AC6.3.3: Text replacement functionality updates existing content within specified ranges
    AC6.3.4: Formatting updates preserve Google Docs structure
    AC6.3.9: Markdown input properly converted to Google Docs format during editing

    Args:
        request: Replace content request
        current_user: Authenticated user from JWT token

    Returns:
        EditGoogleDocResponse with operation results
    """
    try:
        user_id = current_user["user_id"]

        # Get edit service for user
        edit_service = get_google_docs_edit_service(user_id)

        # Replace content
        result = edit_service.replace_content(
            document_id=request.document_id,
            search_text=request.search_text,
            replacement_markdown=request.replacement_markdown,
            use_regex=request.use_regex,
            replace_all=request.replace_all,
        )

        if result["success"]:
            return EditGoogleDocResponse(
                success=True,
                message=result["message"],
                data={
                    "replacements_count": result.get("replacements_count", 0),
                    "character_changes": result.get("character_changes", 0),
                },
                execution_time_ms=result.get("execution_time_ms", 0),
            )
        else:
            return EditGoogleDocResponse(
                success=False,
                message="Replace operation failed",
                error=result.get("error", "Unknown error"),
                execution_time_ms=result.get("execution_time_ms", 0),
            )

    except ValueError as e:
        logger.error(f"Invalid input for replace operation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Replace content operation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Replace operation failed: {str(e)}"
        )


@router.post("/docs/format", response_model=EditGoogleDocResponse)
async def update_formatting(
    request: UpdateFormattingRequest,
    current_user: dict = Depends(require_authenticated_user),
) -> EditGoogleDocResponse:
    """
    Update formatting for a text range in a Google Doc

    AC6.3.4: Formatting updates preserve Google Docs structure (headings, lists, bold, italics)
    AC6.3.10: Document metadata updated with edit timestamp and agent context

    Args:
        request: Update formatting request
        current_user: Authenticated user from JWT token

    Returns:
        EditGoogleDocResponse with operation results
    """
    try:
        user_id = current_user["user_id"]

        # Get edit service for user
        edit_service = get_google_docs_edit_service(user_id)

        # Update formatting
        result = edit_service.update_formatting(
            document_id=request.document_id,
            start_index=request.start_index,
            end_index=request.end_index,
            formatting=request.formatting,
        )

        if result["success"]:
            return EditGoogleDocResponse(
                success=True,
                message=result["message"],
                data={
                    "formatting_applied": len(request.formatting),
                },
                execution_time_ms=result.get("execution_time_ms", 0),
            )
        else:
            return EditGoogleDocResponse(
                success=False,
                message="Format operation failed",
                error=result.get("error", "Unknown error"),
                execution_time_ms=result.get("execution_time_ms", 0),
            )

    except ValueError as e:
        logger.error(f"Invalid input for format operation: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Format operation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Format operation failed: {str(e)}"
        )
