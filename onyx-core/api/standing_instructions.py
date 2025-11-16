"""
Standing Instructions API for ONYX

REST API endpoints for standing instructions CRUD operations,
analytics, and management.

Story 4-2: Standing Instructions Management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from .auth import require_authenticated_user
from ..services.standing_instructions_service import StandingInstructionsService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/instructions", tags=["standing-instructions"])

# Initialize service
instructions_service = StandingInstructionsService()


# Pydantic models for request/response
class StandingInstructionCreate(BaseModel):
    """Model for creating a standing instruction"""
    instruction_text: str = Field(..., min_length=1, max_length=500, description="The instruction text")
    category: str = Field(..., description="Instruction category")
    priority: int = Field(default=5, ge=1, le=10, description="Priority level (1-10)")
    context_hints: Optional[List[str]] = Field(default=None, max_items=10, description="Context hints for filtering")
    enabled: bool = Field(default=True, description="Whether instruction is enabled")

    @validator('category')
    def validate_category(cls, v):
        valid_categories = ['workflow', 'decision', 'communication', 'security', 'general']
        if v not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {valid_categories}")
        return v

    @validator('instruction_text')
    def validate_instruction_text(cls, v):
        if not v or not v.strip():
            raise ValueError("Instruction text cannot be empty")
        return v.strip()


class StandingInstructionUpdate(BaseModel):
    """Model for updating a standing instruction"""
    instruction_text: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    context_hints: Optional[List[str]] = Field(None, max_items=10)
    enabled: Optional[bool] = None

    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            valid_categories = ['workflow', 'decision', 'communication', 'security', 'general']
            if v not in valid_categories:
                raise ValueError(f"Invalid category. Must be one of: {valid_categories}")
        return v


class StandingInstructionResponse(BaseModel):
    """Model for standing instruction response"""
    id: str
    user_id: str
    instruction_text: str
    category: str
    priority: int
    context_hints: Optional[List[str]]
    enabled: bool
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class BulkStatusUpdate(BaseModel):
    """Model for bulk status update"""
    instruction_ids: List[str] = Field(..., min_items=1, description="List of instruction IDs")
    enabled: bool = Field(..., description="New enabled status")


class InstructionAnalytics(BaseModel):
    """Model for instruction analytics response"""
    overall_stats: Dict[str, Any]
    category_breakdown: List[Dict[str, Any]]
    top_instructions: List[Dict[str, Any]]
    generated_at: datetime


# API Endpoints

@router.post("/", response_model=StandingInstructionResponse)
async def create_instruction(
    instruction: StandingInstructionCreate,
    user_id: str = Depends(require_authenticated_user)
):
    """
    Create a new standing instruction

    Args:
        instruction: Instruction data
        user_id: Authenticated user ID

    Returns:
        Created instruction
    """
    try:
        result = await instructions_service.create_instruction(
            user_id=user_id,
            instruction_text=instruction.instruction_text,
            category=instruction.category,
            priority=instruction.priority,
            context_hints=instruction.context_hints,
            enabled=instruction.enabled
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create instruction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[StandingInstructionResponse])
async def get_instructions(
    category: Optional[str] = Query(None, description="Filter by category"),
    enabled_only: bool = Query(True, description="Return only enabled instructions"),
    sort_by: str = Query("priority", description="Sort order: priority, usage, category, created"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Limit number of results"),
    user_id: str = Depends(require_authenticated_user)
):
    """
    Get user's standing instructions with filtering and sorting

    Args:
        category: Optional category filter
        enabled_only: Whether to return only enabled instructions
        sort_by: Sort order
        limit: Optional limit
        user_id: Authenticated user ID

    Returns:
        List of instructions
    """
    try:
        if sort_by not in ["priority", "usage", "category", "created"]:
            raise HTTPException(status_code=400, detail="Invalid sort_by parameter")

        results = await instructions_service.get_user_instructions(
            user_id=user_id,
            category=category,
            enabled_only=enabled_only,
            sort_by=sort_by,
            limit=limit
        )
        return results
    except Exception as e:
        logger.error(f"Failed to get instructions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{instruction_id}", response_model=StandingInstructionResponse)
async def get_instruction(
    instruction_id: str,
    user_id: str = Depends(require_authenticated_user)
):
    """
    Get a specific standing instruction

    Args:
        instruction_id: Instruction ID
        user_id: Authenticated user ID

    Returns:
        Instruction data
    """
    try:
        instructions = await instructions_service.get_user_instructions(user_id=user_id)
        for instruction in instructions:
            if instruction['id'] == instruction_id:
                return instruction

        raise HTTPException(status_code=404, detail="Instruction not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get instruction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{instruction_id}", response_model=StandingInstructionResponse)
async def update_instruction(
    instruction_id: str,
    updates: StandingInstructionUpdate,
    user_id: str = Depends(require_authenticated_user)
):
    """
    Update a standing instruction

    Args:
        instruction_id: Instruction ID
        updates: Update data
        user_id: Authenticated user ID

    Returns:
        Updated instruction
    """
    try:
        update_data = updates.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = await instructions_service.update_instruction(
            instruction_id=instruction_id,
            user_id=user_id,
            updates=update_data
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update instruction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{instruction_id}")
async def delete_instruction(
    instruction_id: str,
    user_id: str = Depends(require_authenticated_user)
):
    """
    Delete a standing instruction (soft delete)

    Args:
        instruction_id: Instruction ID
        user_id: Authenticated user ID

    Returns:
        Success message
    """
    try:
        deleted = await instructions_service.delete_instruction(
            instruction_id=instruction_id,
            user_id=user_id
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Instruction not found")

        return {"message": "Instruction deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete instruction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/bulk-status", response_model=Dict[str, Any])
async def bulk_update_status(
    bulk_update: BulkStatusUpdate,
    user_id: str = Depends(require_authenticated_user)
):
    """
    Bulk update enabled status for multiple instructions

    Args:
        bulk_update: Bulk update data
        user_id: Authenticated user ID

    Returns:
        Update results
    """
    try:
        updated_count = await instructions_service.bulk_update_status(
            instruction_ids=bulk_update.instruction_ids,
            user_id=user_id,
            enabled=bulk_update.enabled
        )

        return {
            "message": f"Updated {updated_count} instructions",
            "updated_count": updated_count
        }
    except Exception as e:
        logger.error(f"Failed to bulk update instructions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/usage", response_model=InstructionAnalytics)
async def get_instruction_analytics(
    user_id: str = Depends(require_authenticated_user)
):
    """
    Get usage analytics for user's standing instructions

    Args:
        user_id: Authenticated user ID

    Returns:
        Analytics data
    """
    try:
        analytics = await instructions_service.get_instruction_analytics(user_id=user_id)
        return analytics
    except Exception as e:
        logger.error(f"Failed to get instruction analytics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/test-injection")
async def test_instruction_injection(
    background_tasks: BackgroundTasks,
    limit: int = Query(5, ge=1, le=20, description="Number of instructions to test"),
    user_id: str = Depends(require_authenticated_user)
):
    """
    Test instruction injection with current user context

    Args:
        background_tasks: FastAPI background tasks
        limit: Number of instructions to include
        user_id: Authenticated user ID

    Returns:
        Injection test results
    """
    try:
        from ..services.memory_injection_service import MemoryInjectionService

        injection_service = MemoryInjectionService()
        conversation_id = "test-conversation"

        # Prepare injection with instructions
        injection = await injection_service.prepare_injection(
            user_id=user_id,
            conversation_id=conversation_id,
            current_message="Test injection"
        )

        return {
            "message": "Instruction injection test completed",
            "injection": {
                "user_id": injection.user_id,
                "conversation_id": injection.conversation_id,
                "instructions_count": len(injection.standing_instructions),
                "memories_count": len(injection.memories),
                "injection_time_ms": injection.injection_time,
                "performance_stats": injection.performance_stats,
                "instructions": injection.standing_instructions[:limit]  # Limit response size
            }
        }
    except Exception as e:
        logger.error(f"Failed to test instruction injection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for standing instructions service

    Returns:
        Service health status
    """
    try:
        # Test database connection
        conn = instructions_service._get_connection()
        if conn and not conn.closed:
            return {"status": "healthy", "database": "connected"}
        else:
            return {"status": "unhealthy", "database": "disconnected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}