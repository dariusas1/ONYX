"""
Memory API Endpoints for ONYX

REST API endpoints for memory CRUD operations, search, and categorization.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from services.memory_service import get_memory_service
from utils.auth import require_authenticated_user

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# Pydantic Models for API Requests/Responses

class MemoryCreateRequest(BaseModel):
    """Request model for creating a memory"""
    fact: str = Field(..., min_length=1, max_length=2000, description="Memory content/fact")
    category: str = Field(..., description="Memory category")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    source_type: str = Field(default="manual", description="Source of the memory")
    source_message_id: Optional[str] = Field(None, description="Optional source message ID")
    conversation_id: Optional[str] = Field(None, description="Optional conversation ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional metadata")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration timestamp")

    @validator('category')
    def validate_category(cls, v):
        valid_categories = [
            'priority', 'decision', 'context', 'preference',
            'relationship', 'goal', 'summary'
        ]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return v

    @validator('source_type')
    def validate_source_type(cls, v):
        valid_types = [
            'manual', 'extracted_from_chat', 'auto_summary', 'standing_instruction'
        ]
        if v not in valid_types:
            raise ValueError(f"Source type must be one of: {', '.join(valid_types)}")
        return v


class MemoryUpdateRequest(BaseModel):
    """Request model for updating a memory"""
    fact: Optional[str] = Field(None, min_length=1, max_length=2000, description="Memory content/fact")
    category: Optional[str] = Field(None, description="Memory category")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration timestamp")

    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            valid_categories = [
                'priority', 'decision', 'context', 'preference',
                'relationship', 'goal', 'summary'
            ]
            if v not in valid_categories:
                raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return v


class MemoryResponse(BaseModel):
    """Response model for memory data"""
    id: str
    user_id: str
    fact: str
    category: str
    confidence: float
    source_type: str
    source_message_id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """Response model for memory lists"""
    memories: List[MemoryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class CategoryResponse(BaseModel):
    """Response model for memory categories"""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    color: str = "#6366f1"
    icon: str = "folder"
    is_system_category: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# API Endpoints

@router.post("/memories", response_model=Dict[str, Any])
async def create_memory(
    request: MemoryCreateRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Create a new memory

    Args:
        request: Memory creation request
        current_user: Authenticated user from JWT token

    Returns:
        Created memory data
    """
    try:
        user_id = current_user["sub"]  # Extract user ID from JWT

        memory_service = get_memory_service()
        memory = await memory_service.create_memory(
            user_id=user_id,
            fact=request.fact,
            category=request.category,
            confidence=request.confidence,
            source_type=request.source_type,
            source_message_id=request.source_message_id,
            conversation_id=request.conversation_id,
            metadata=request.metadata,
            expires_at=request.expires_at
        )

        if memory:
            return {
                "success": True,
                "data": memory
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create memory"
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Create memory failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


@router.get("/memories/{memory_id}", response_model=Dict[str, Any])
async def get_memory(
    memory_id: str,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Retrieve a specific memory by ID

    Args:
        memory_id: Memory UUID
        current_user: Authenticated user from JWT token

    Returns:
        Memory data
    """
    try:
        user_id = current_user["sub"]

        memory_service = get_memory_service()
        memory = await memory_service.get_memory(memory_id, user_id)

        if memory:
            return {
                "success": True,
                "data": memory
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Memory not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get memory failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


@router.put("/memories/{memory_id}", response_model=Dict[str, Any])
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Update an existing memory

    Args:
        memory_id: Memory UUID
        request: Memory update request
        current_user: Authenticated user from JWT token

    Returns:
        Updated memory data
    """
    try:
        user_id = current_user["sub"]

        # Build updates dictionary, only include non-None values
        updates = {}
        if request.fact is not None:
            updates['fact'] = request.fact
        if request.category is not None:
            updates['category'] = request.category
        if request.confidence is not None:
            updates['confidence'] = request.confidence
        if request.metadata is not None:
            updates['metadata'] = request.metadata
        if request.expires_at is not None:
            updates['expires_at'] = request.expires_at

        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No fields to update"
            )

        memory_service = get_memory_service()
        memory = await memory_service.update_memory(memory_id, user_id, updates)

        if memory:
            return {
                "success": True,
                "data": memory
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Memory not found"
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update memory failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


@router.delete("/memories/{memory_id}", response_model=Dict[str, Any])
async def delete_memory(
    memory_id: str,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Soft delete a memory

    Args:
        memory_id: Memory UUID
        current_user: Authenticated user from JWT token

    Returns:
        Deletion status
    """
    try:
        user_id = current_user["sub"]

        memory_service = get_memory_service()
        success = await memory_service.delete_memory(memory_id, user_id)

        if success:
            return {
                "success": True,
                "data": {
                    "message": "Memory deleted successfully",
                    "id": memory_id
                }
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="Memory not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete memory failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


@router.get("/memories", response_model=Dict[str, Any])
async def get_memories(
    category: Optional[str] = Query(None, description="Filter by category"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    confidence_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    search: Optional[str] = Query(None, description="Search term"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("DESC", regex="^(ASC|DESC)$", description="Sort order"),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get user memories with filtering and pagination

    Args:
        category: Optional category filter
        source_type: Optional source type filter
        confidence_min: Optional minimum confidence filter
        search: Optional search term
        limit: Maximum number of results
        offset: Pagination offset
        sort_by: Sort field
        sort_order: Sort order
        current_user: Authenticated user from JWT token

    Returns:
        List of memories with pagination info
    """
    try:
        user_id = current_user["sub"]

        memory_service = get_memory_service()
        memories = await memory_service.get_user_memories(
            user_id=user_id,
            category=category,
            source_type=source_type,
            confidence_min=confidence_min,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # For now, we don't have total count, so we'll estimate
        has_more = len(memories) == limit

        return {
            "success": True,
            "data": {
                "memories": memories,
                "total": len(memories),
                "limit": limit,
                "offset": offset,
                "has_more": has_more
            }
        }

    except Exception as e:
        logger.error(f"Get memories failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


@router.get("/memories/search", response_model=Dict[str, Any])
async def search_memories(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results"),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Full-text search across memory facts

    Args:
        q: Search query
        category: Optional category filter
        limit: Maximum number of results
        current_user: Authenticated user from JWT token

    Returns:
        List of matching memories
    """
    try:
        user_id = current_user["sub"]

        memory_service = get_memory_service()
        memories = await memory_service.search_memories(
            user_id=user_id,
            query=q,
            category=category,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "memories": memories,
                "query": q,
                "category": category,
                "total": len(memories)
            }
        }

    except Exception as e:
        logger.error(f"Search memories failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


@router.get("/memories/categories", response_model=Dict[str, Any])
async def get_memory_categories(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Get all memory categories for the user

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        List of memory categories
    """
    try:
        user_id = current_user["sub"]

        memory_service = get_memory_service()
        categories = await memory_service.get_memory_categories(user_id)

        # Initialize default categories if none exist
        if not categories:
            await memory_service.initialize_default_categories(user_id)
            categories = await memory_service.get_memory_categories(user_id)

        return {
            "success": True,
            "data": {
                "categories": categories,
                "total": len(categories)
            }
        }

    except Exception as e:
        logger.error(f"Get memory categories failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


@router.post("/memories/categories/initialize", response_model=Dict[str, Any])
async def initialize_memory_categories(
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Initialize default memory categories for the user

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        Initialization status
    """
    try:
        user_id = current_user["sub"]

        memory_service = get_memory_service()
        success = await memory_service.initialize_default_categories(user_id)

        if success:
            return {
                "success": True,
                "data": {
                    "message": "Default categories initialized successfully"
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize default categories"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Initialize memory categories failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Memory service temporarily unavailable"
        )


# Health check endpoint for memory service
@router.get("/memories/health", response_model=Dict[str, Any])
async def memory_health_check():
    """Health check for memory service"""
    try:
        memory_service = get_memory_service()
        # Test database connection
        memory_service.connect()
        memory_service.close()

        return {
            "success": True,
            "data": {
                "status": "healthy",
                "service": "memory",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

    except Exception as e:
        logger.error(f"Memory health check failed: {e}")
        return {
            "success": False,
            "error": {
                "code": "MEMORY_SERVICE_UNHEALTHY",
                "message": "Memory service is unhealthy",
                "details": str(e)
            }
        }