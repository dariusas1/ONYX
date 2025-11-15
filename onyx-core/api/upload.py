"""
File Upload API Endpoints

This module provides REST API endpoints for file upload, validation,
parsing, and indexing into the vector database.
"""

import os
import tempfile
import shutil
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rag_service import get_rag_service
from file_parsers.parser_factory import ParserFactory
from services.embedding_service import get_embedding_service
from utils.auth import require_authenticated_user

logger = logging.getLogger(__name__)

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_REQUEST = 10
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")

# Create upload router
router = APIRouter(prefix="/api/upload", tags=["File Upload"])


# Request/Response Models
class FileUploadRequest(BaseModel):
    """Request model for file upload"""
    pass


class FileValidationResult(BaseModel):
    """Result of file validation"""
    filename: str
    is_valid: bool
    file_size: int
    file_type: str
    error_message: Optional[str] = None
    detected_format: Optional[str] = None


class FileProcessingResult(BaseModel):
    """Result of file processing"""
    filename: str
    status: str  # 'success', 'error', 'processing'
    chunks_count: Optional[int] = None
    doc_id: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FileUploadResponse(BaseModel):
    """Response model for file upload"""
    success: bool
    message: str
    results: List[FileProcessingResult]
    total_files: int
    successful_files: int
    failed_files: int
    processing_stats: Optional[Dict[str, Any]] = None


# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_upload_file(file: UploadFile) -> FileValidationResult:
    """
    Validate uploaded file for format, size, and security

    Args:
        file: UploadFile object

    Returns:
        FileValidationResult with validation status
    """
    try:
        # Check filename
        if not file.filename:
            return FileValidationResult(
                filename="unknown",
                is_valid=False,
                file_size=0,
                file_type="unknown",
                error_message="No filename provided"
            )

        # Create temporary file for validation
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        try:
            # Use ParserFactory to validate file
            validation = ParserFactory.validate_file(temp_file_path)

            return FileValidationResult(
                filename=file.filename,
                is_valid=validation.is_valid,
                file_size=validation.file_size or 0,
                file_type=validation.detected_format or "unknown",
                error_message=validation.error_message,
                detected_format=validation.detected_format
            )

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

    except Exception as e:
        logger.error(f"File validation error for {file.filename}: {e}")
        return FileValidationResult(
            filename=file.filename,
            is_valid=False,
            file_size=0,
            file_type="unknown",
            error_message=f"Validation error: {str(e)}"
        )


async def process_uploaded_file(
    file: UploadFile,
    user_id: str,
    doc_id_prefix: str = "upload"
) -> FileProcessingResult:
    """
    Process uploaded file: parse, generate embeddings, and index

    Args:
        file: UploadFile object
        user_id: User ID for permission metadata
        doc_id_prefix: Prefix for document ID

    Returns:
        FileProcessingResult with processing status
    """
    start_time = datetime.now()

    try:
        # Reset file pointer
        await file.seek(0)

        # Save to temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        try:
            # Parse file using appropriate parser
            parse_result = ParserFactory.parse_file(temp_file_path, user_id)

            if not parse_result.success:
                return FileProcessingResult(
                    filename=file.filename,
                    status="error",
                    error_message=parse_result.error_message
                )

            # Generate embeddings
            embedding_service = await get_embedding_service()
            embedding_result = await embedding_service.generate_embeddings(
                content=parse_result.content,
                doc_metadata=parse_result.metadata or {}
            )

            if not embedding_result.success:
                return FileProcessingResult(
                    filename=file.filename,
                    status="error",
                    error_message=f"Embedding generation failed: {embedding_result.error_message}"
                )

            # Index chunks in vector database
            rag_service = await get_rag_service()
            doc_id = f"{doc_id_prefix}_{int(start_time.timestamp())}_{file.filename.replace('.', '_')}"

            indexed_chunks = 0
            for i, chunk in enumerate(embedding_result.chunks):
                chunk_metadata = {
                    "chunk_index": chunk.metadata.chunk_index,
                    "total_chunks": chunk.metadata.total_chunks,
                    "token_count": chunk.metadata.token_count,
                    "start_char": chunk.metadata.start_char,
                    "end_char": chunk.metadata.end_char,
                    "chunk_hash": chunk.metadata.chunk_hash,
                }

                # Combine with document metadata
                combined_metadata = {
                    **(parse_result.metadata or {}),
                    **chunk_metadata
                }

                # Add document to vector database
                success = await rag_service.add_document(
                    doc_id=f"{doc_id}_chunk_{i}",
                    text=chunk.text,
                    title=file.filename,
                    source="local_upload",
                    metadata=combined_metadata
                )

                if success:
                    indexed_chunks += 1

            processing_time = (datetime.now() - start_time).total_seconds()

            if indexed_chunks == len(embedding_result.chunks):
                return FileProcessingResult(
                    filename=file.filename,
                    status="success",
                    chunks_count=len(embedding_result.chunks),
                    doc_id=doc_id,
                    processing_time=processing_time,
                    metadata={
                        "parse_result": parse_result.metadata,
                        "embedding_stats": embedding_result.stats,
                        "indexed_chunks": indexed_chunks,
                        "total_chunks": len(embedding_result.chunks)
                    }
                )
            else:
                return FileProcessingResult(
                    filename=file.filename,
                    status="error",
                    chunks_count=len(embedding_result.chunks),
                    error_message=f"Only {indexed_chunks}/{len(embedding_result.chunks)} chunks were indexed",
                    processing_time=processing_time
                )

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"File processing error for {file.filename}: {e}")
        return FileProcessingResult(
            filename=file.filename,
            status="error",
            processing_time=processing_time,
            error_message=f"Processing error: {str(e)}"
        )


@router.post("/files", response_model=FileUploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(require_authenticated_user)
):
    """
    Upload and process multiple files

    Args:
        files: List of files to upload
        current_user: Authenticated user from JWT token

    Returns:
        FileUploadResponse with processing results
    """
    try:
        # Check number of files
        if len(files) > MAX_FILES_PER_REQUEST:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {MAX_FILES_PER_REQUEST} files allowed per request"
            )

        # Get user ID for permissions
        user_id = current_user.get("email", current_user.get("sub", "unknown"))

        results = []
        successful_count = 0
        failed_count = 0
        total_processing_time = 0

        # Validate all files first
        validation_results = []
        for file in files:
            validation = validate_upload_file(file)
            validation_results.append(validation)

            if not validation.is_valid:
                results.append(FileProcessingResult(
                    filename=validation.filename,
                    status="error",
                    error_message=validation.error_message
                ))
                failed_count += 1
            else:
                # Check file size limit
                if validation.file_size > MAX_FILE_SIZE:
                    results.append(FileProcessingResult(
                        filename=validation.filename,
                        status="error",
                        error_message=f"File size exceeds {MAX_FILE_SIZE / (1024*1024):.1f}MB limit"
                    ))
                    failed_count += 1
                else:
                    # File is valid, proceed with processing
                    pass

        # Process valid files
        for i, file in enumerate(files):
            if i < len(validation_results) and validation_results[i].is_valid:
                processing_result = await process_uploaded_file(file, user_id)
                results.append(processing_result)

                if processing_result.status == "success":
                    successful_count += 1
                    total_processing_time += processing_result.processing_time or 0
                else:
                    failed_count += 1

        # Calculate processing statistics
        processing_stats = {
            "total_files": len(files),
            "successful_files": successful_count,
            "failed_files": failed_count,
            "total_processing_time": total_processing_time,
            "average_processing_time": total_processing_time / successful_count if successful_count > 0 else 0,
            "supported_formats": ParserFactory.get_supported_extensions(),
            "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        }

        return FileUploadResponse(
            success=successful_count > 0,
            message=f"Processed {successful_count} of {len(files)} files successfully",
            results=results,
            total_files=len(files),
            successful_files=successful_count,
            failed_files=failed_count,
            processing_stats=processing_stats
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )


@router.get("/formats", response_model=Dict[str, Any])
async def get_supported_formats():
    """
    Get list of supported file formats and upload limits

    Returns:
        Dictionary with supported formats and limits
    """
    return {
        "supported_extensions": ParserFactory.get_supported_extensions(),
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "max_files_per_request": MAX_FILES_PER_REQUEST,
        "upload_timeout_seconds": 300,  # 5 minutes
        "supported_categories": {
            "documents": [".md", ".pdf", ".txt"],
            "structured_data": [".csv", ".json"],
            "images": [".png", ".jpg", ".jpeg"]
        }
    }


@router.post("/validate", response_model=List[FileValidationResult])
async def validate_files(
    files: List[UploadFile] = File(...)
):
    """
    Validate files without processing them

    Args:
        files: List of files to validate

    Returns:
        List of validation results
    """
    try:
        validation_results = []
        for file in files:
            validation = validate_upload_file(file)
            validation_results.append(validation)

        return validation_results

    except Exception as e:
        logger.error(f"File validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"File validation failed: {str(e)}"
        )


@router.get("/status")
async def get_upload_status():
    """
    Get upload service status and statistics

    Returns:
        Dictionary with service status
    """
    try:
        # Check upload directory
        upload_dir_exists = os.path.exists(UPLOAD_DIR)
        upload_dir_writable = os.access(UPLOAD_DIR, os.W_OK) if upload_dir_exists else False

        # Get RAG service status
        rag_service = await get_rag_service()
        rag_health = await rag_service.health_check()

        # Get embedding service info
        embedding_service = await get_embedding_service()
        embedding_info = embedding_service.get_model_info()

        return {
            "status": "healthy",
            "upload_directory": {
                "path": UPLOAD_DIR,
                "exists": upload_dir_exists,
                "writable": upload_dir_writable
            },
            "rag_service": rag_health,
            "embedding_service": {
                "model": embedding_info["model"],
                "dimensions": embedding_info["dimensions"],
                "batch_size": embedding_info["batch_size"],
                "tokenizer_available": embedding_info["tokenizer_available"]
            },
            "supported_formats": ParserFactory.get_supported_extensions(),
            "limits": {
                "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
                "max_files_per_request": MAX_FILES_PER_REQUEST
            }
        }

    except Exception as e:
        logger.error(f"Upload status check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "upload_directory": {"path": UPLOAD_DIR, "exists": False, "writable": False}
        }


@router.get("/docs", include_in_schema=False)
async def custom_docs():
    """
    Custom documentation for upload endpoints
    """
    return {
        "title": "File Upload API",
        "description": "API endpoints for uploading files to the RAG system",
        "endpoints": {
            "/api/upload/files": "Upload and process multiple files",
            "/api/upload/formats": "Get supported file formats",
            "/api/upload/validate": "Validate files without processing",
            "/api/upload/status": "Get upload service status"
        },
        "supported_formats": ParserFactory.get_supported_extensions(),
        "usage_examples": {
            "upload_files": """
                POST /api/upload/files
                Content-Type: multipart/form-data

                curl -X POST "http://localhost:8080/api/upload/files" \
                  -H "Authorization: Bearer <token>" \
                  -F "files=@document.pdf" \
                  -F "files=@data.csv"
            """,
            "get_formats": """
                GET /api/upload/formats
                Accept: application/json
            """
        }
    }