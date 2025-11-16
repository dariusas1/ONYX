from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from health import router as health_router
from api.google_drive import router as google_drive_router
from api.memories import router as memories_router
from api.web_tools import router as web_tools_router, startup_event as web_tools_startup, shutdown_event as web_tools_shutdown
from contextlib import asynccontextmanager
from rag_service import get_rag_service
from services.sync_scheduler import start_scheduler, stop_scheduler
from services.memory_service import get_memory_service
from utils.auth import require_authenticated_user
import logging

# Import summarization services
try:
    from services.summarization.trigger_service import create_summarization_trigger_service
    from services.summarization.storage import create_summary_memory_storage
    from workers.summarization_worker import create_summarization_worker, WorkerConfig
    from api.summarization import router as summarization_router
    SUMMARIZATION_AVAILABLE = True
except ImportError as error:
    logging.warning(f"Summarization services not available: {error}")
    SUMMARIZATION_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store application state
app_state = {}

# Store summarization services
summarization_services = {
    'trigger_service': None,
    'storage_service': None,
    'worker': None,
    'initialized': False
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    app_state["startup_time"] = datetime.utcnow()
    logger.info("🚀 Onyx Core is starting up...")

    # Initialize RAG service
    try:
        await get_rag_service()
        logger.info("✅ RAG service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG service: {e}")

    # Start sync scheduler
    try:
        await start_scheduler()
        logger.info("✅ Sync scheduler started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start sync scheduler: {e}")

    # Initialize memory service
    try:
        await get_memory_service()
        logger.info("✅ Memory service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize memory service: {e}")

    # Initialize web tools services
    try:
        await web_tools_startup()
        logger.info("✅ Web tools services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize web tools services: {e}")

    # Initialize summarization pipeline
    if SUMMARIZATION_AVAILABLE:
        try:
            await initialize_summarization_services()
            logger.info("✅ Summarization pipeline initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize summarization pipeline: {e}")
    else:
        logger.info("ℹ️ Summarization pipeline not available - skipping initialization")

    yield

    # Shutdown
    logger.info("🛑 Onyx Core is shutting down...")

    # Stop sync scheduler
    try:
        await stop_scheduler()
        logger.info("✅ Sync scheduler stopped successfully")
    except Exception as e:
        logger.error(f"❌ Failed to stop sync scheduler: {e}")

    # Shutdown web tools services
    try:
        await web_tools_shutdown()
        logger.info("✅ Web tools services shut down successfully")
    except Exception as e:
        logger.error(f"❌ Failed to shutdown web tools services: {e}")

    # Shutdown summarization pipeline
    if SUMMARIZATION_AVAILABLE and summarization_services['initialized']:
        try:
            await shutdown_summarization_services()
            logger.info("✅ Summarization pipeline shut down successfully")
        except Exception as e:
            logger.error(f"❌ Failed to shutdown summarization pipeline: {e}")


# Summarization service functions
async def initialize_summarization_services():
    """Initialize the auto-summarization pipeline services."""
    global summarization_services

    if not SUMMARIZATION_AVAILABLE:
        raise ImportError("Summarization services not available")

    # Get database and Redis connections (assuming they're available in memory_service)
    try:
        from services.memory_service import get_memory_service
        memory_service = await get_memory_service()

        # Get database pool from memory service
        db_pool = getattr(memory_service, 'db_pool', None)
        redis_client = getattr(memory_service, 'redis_client', None)

        if not db_pool:
            raise ValueError("Database pool not available from memory service")
        if not redis_client:
            raise ValueError("Redis client not available from memory service")

        # Initialize trigger service
        summarization_services['trigger_service'] = await create_summarization_trigger_service(db_pool, redis_client)

        # Initialize storage service
        summarization_services['storage_service'] = create_summary_memory_storage(db_pool)

        # Initialize and start worker
        worker_config = WorkerConfig(
            concurrency=int(os.getenv('SUMMARY_WORKER_CONCURRENCY', 2)),
            max_retries=int(os.getenv('SUMMARY_WORKER_MAX_RETRIES', 3))
        )

        summarization_services['worker'] = create_summarization_worker(db_pool, redis_client, worker_config)
        await summarization_services['worker'].start()

        summarization_services['initialized'] = True

        logger.info("✅ Summarization pipeline services initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize summarization services: {e}")
        raise


async def shutdown_summarization_services():
    """Shutdown the auto-summarization pipeline services."""
    global summarization_services

    if not summarization_services['initialized']:
        return

    try:
        # Stop worker
        if summarization_services['worker']:
            await summarization_services['worker'].stop()
            summarization_services['worker'] = None
            logger.info("✅ Summarization worker stopped")

        # Close trigger service
        if summarization_services['trigger_service']:
            await summarization_services['trigger_service'].close()
            summarization_services['trigger_service'] = None
            logger.info("✅ Summarization trigger service closed")

        # Reset storage service
        summarization_services['storage_service'] = None

        summarization_services['initialized'] = False

        logger.info("✅ Summarization pipeline services shut down successfully")

    except Exception as e:
        logger.error(f"❌ Failed to shutdown summarization services: {e}")


# Create FastAPI application
app = FastAPI(
    title=os.getenv("API_TITLE", "Onyx Core API"),
    description=os.getenv("API_DESCRIPTION", "RAG and AI services for ONYX platform"),
    version=os.getenv("API_VERSION", "1.0.0"),
    docs_url=os.getenv("API_DOCS_URL", "/docs"),
    redoc_url=os.getenv("API_REDOC_URL", "/redoc"),
    lifespan=lifespan,
)

# Configure CORS
allowed_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://suna:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(google_drive_router, tags=["Google Drive"])
app.include_router(memories_router, tags=["Memories"])
app.include_router(web_tools_router, tags=["Web Tools"])

# Include summarization router if available
if SUMMARIZATION_AVAILABLE:
    try:
        app.include_router(summarization_router, tags=["Summarization"])
        logger.info("✅ Summarization API routes included")
    except Exception as e:
        logger.warning(f"Could not include summarization API routes: {e}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "onyx-core",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "startup_time": app_state.get("startup_time"),
        "endpoints": {"health": "/health", "docs": "/docs", "redoc": "/redoc"},
    }


# Search endpoint with actual RAG functionality
@app.get("/search")
async def search_documents(
    query: str,
    top_k: int = 5,
    source: Optional[str] = None,
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Search documents using RAG with permission filtering

    Args:
        query: Search query
        top_k: Number of results to return (max 20)
        source: Optional source filter (e.g., 'google_drive')
        current_user: Authenticated user from JWT token

    Returns:
        Search results filtered by user permissions
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query parameter is required")

        # Get RAG service
        rag_service = await get_rag_service()

        # Get user email for permission filtering
        user_email = current_user["email"]

        # Perform search with permission filtering
        # The RAG service will filter results based on user permissions
        results = await rag_service.search(
            query=query.strip(),
            top_k=min(top_k, 20),  # Limit to 20 max results
            source_filter=source,
            user_email=user_email,  # Add user email for permission filtering
        )

        # Convert results to response format
        search_results = [
            {
                "doc_id": result.doc_id,
                "score": float(result.score),
                "text": result.text,
                "title": result.title,
                "source": result.source,
                "metadata": result.metadata,
            }
            for result in results
        ]

        return {
            "success": True,
            "data": {
                "query": query,
                "top_k": top_k,
                "source_filter": source,
                "user_email": user_email,
                "results_count": len(search_results),
                "results": search_results,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")
        raise HTTPException(
            status_code=500, detail="Search service temporarily unavailable"
        )


# Document management endpoints
@app.post("/documents")
async def add_document(
    doc_id: str,
    text: str,
    title: str,
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Add a document to the RAG system"""
    try:
        if not all([doc_id, text, title, source]):
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: doc_id, text, title, source",
            )

        # Get RAG service
        rag_service = await get_rag_service()

        # Add document
        success = await rag_service.add_document(
            doc_id=doc_id,
            text=text,
            title=title,
            source=source,
            metadata=metadata or {},
        )

        if success:
            return {
                "success": True,
                "data": {
                    "doc_id": doc_id,
                    "message": "Document added successfully",
                    "source": source,
                },
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add document")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add document {doc_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Document service temporarily unavailable"
        )


@app.get("/documents/count")
async def get_document_count():
    """Get total number of documents in the system"""
    try:
        rag_service = await get_rag_service()
        count = await rag_service.get_document_count()

        return {"success": True, "data": {"document_count": count}}
    except Exception as e:
        logger.error(f"Failed to get document count: {e}")
        raise HTTPException(
            status_code=500, detail="Document service temporarily unavailable"
        )


# Note: Google Drive sync endpoints moved to api/google_drive.py router


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": str(exc),
            },
        },
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True if os.getenv("PYTHON_ENV") == "development" else False,
        log_level="info",
    )
