"""
Form Tools API for ONYX Core

REST API endpoints for form interaction and web automation tools.
Provides fill_form and detect_form endpoints for automated form handling.

Author: ONYX Core Team
Story: 7-4-form-filling-web-interaction
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from services.form_interaction_service import (
    FormInteractionService,
    FormFillRequest,
    FormFillResponse
)
from services.browser_manager import BrowserManager
from utils.auth import require_authenticated_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
_form_service: Optional[FormInteractionService] = None


async def get_form_service() -> FormInteractionService:
    """Get or initialize form interaction service."""
    global _form_service
    if _form_service is None:
        _form_service = FormInteractionService()
    return _form_service


@router.post("/fill_form", response_model=FormFillResponse)
async def fill_form(
    request: FormFillRequest,
    user_id: str = Depends(require_authenticated_user)
) -> FormFillResponse:
    """
    Fill a web form with specified data.

    Args:
        request: Form filling request with URL and field data
        user_id: Authenticated user ID

    Returns:
        FormFillResponse: Operation results with field status and screenshots

    Raises:
        HTTPException: For validation errors or operation failures
    """
    logger.info(f"Fill form request from user {user_id}: {request.url}")

    try:
        # Validate request
        if not request.url or not request.form_data:
            raise HTTPException(status_code=400, detail="URL and form_data are required")

        # Validate form data structure
        if not isinstance(request.form_data, dict):
            raise HTTPException(status_code=400, detail="form_data must be a dictionary")

        # Execute form filling
        form_service = await get_form_service()
        response = await form_service.fill_form(request)

        # Log results
        if response.success:
            logger.info(f"Form filled successfully: {len(response.fields_filled)} fields, "
                       f"{len(response.fields_failed)} failed, {response.execution_time:.2f}s")
        else:
            logger.warning(f"Form fill partially successful: {len(response.fields_filled)} filled, "
                          f"{len(response.fields_failed)} failed")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in fill_form: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/detect_form")
async def detect_form(
    url: str,
    user_id: str = Depends(require_authenticated_user)
) -> Dict[str, Any]:
    """
    Analyze a web page and detect form fields.

    Args:
        url: URL of the page to analyze
        user_id: Authenticated user ID

    Returns:
        Dictionary with detected form metadata and field information

    Raises:
        HTTPException: For validation errors or analysis failures
    """
    logger.info(f"Detect forms request from user {user_id}: {url}")

    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        # Get browser manager and navigate to page
        browser_manager = await BrowserManager.get_instance()
        page = await browser_manager.navigate(url)

        try:
            # Detect forms and fields
            form_service = await get_form_service()
            forms = await form_service.detect_forms(page)

            # Extract page metadata
            page_title = await page.title()
            page_url = page.url

            # Prepare response
            response = {
                "url": page_url,
                "title": page_title,
                "forms_detected": len(forms),
                "forms": forms,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

            logger.info(f"Form detection completed: {len(forms)} form(s) found")
            return response

        finally:
            # Cleanup page
            await browser_manager.close_page(page)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in detect_form: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/form_health")
async def form_health(
    user_id: str = Depends(require_authenticated_user)
) -> Dict[str, Any]:
    """
    Health check for form interaction services.

    Args:
        user_id: Authenticated user ID

    Returns:
        Dictionary with service health status
    """
    try:
        # Check browser manager health
        browser_manager = await BrowserManager.get_instance()
        browser_healthy = await browser_manager.is_healthy()

        # Check form service
        form_service = await get_form_service()

        # Get browser memory usage
        memory_mb = await browser_manager.check_memory()

        response = {
            "status": "healthy" if browser_healthy else "unhealthy",
            "browser_connected": browser_healthy,
            "memory_usage_mb": memory_mb,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": "1.0.0"
        }

        return response

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "browser_connected": False,
            "memory_usage_mb": 0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
            "version": "1.0.0"
        }


@router.get("/form_capabilities")
async def form_capabilities(
    user_id: str = Depends(require_authenticated_user)
) -> Dict[str, Any]:
    """
    Return the capabilities of the form interaction service.

    Args:
        user_id: Authenticated user ID

    Returns:
        Dictionary with supported field types and features
    """
    return {
        "supported_field_types": [
            "input_text",
            "input_email",
            "input_password",
            "input_number",
            "input_tel",
            "input_url",
            "input_search",
            "input_date",
            "input_datetime-local",
            "input_time",
            "textarea",
            "select",
            "checkbox",
            "radio"
        ],
        "features": [
            "form_detection",
            "field_filling",
            "form_submission",
            "screenshot_audit",
            "error_handling",
            "timeout_management",
            "field_validation"
        ],
        "performance_targets": {
            "execution_time_seconds": 5.0,
            "page_load_timeout_seconds": 10,
            "field_detection_timeout_seconds": 1,
            "screenshot_timeout_seconds": 0.5
        },
        "security_features": [
            "url_validation",
            "input_sanitization",
            "blocklist_enforcement",
            "audit_trail"
        ],
        "version": "1.0.0"
    }