"""
Database Utilities for Google Drive Sync

This module provides database operations for OAuth tokens, sync state, and sync jobs.
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
except ImportError:  # pragma: no cover - executed only when dependency missing
    psycopg2 = None  # type: ignore
    RealDictCursor = Json = None  # type: ignore
    logger.warning(
        "psycopg2 is not installed. DatabaseService will raise if used. "
        "Install psycopg2-binary per onyx-core/requirements.txt."
    )


class DatabaseService:
    """Service for database operations"""

    def __init__(self):
        """Initialize database connection"""
        self.connection_string = self._build_connection_string()
        self.conn = None

    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from environment variables"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "manus")
        user = os.getenv("POSTGRES_USER", "manus")
        password = os.getenv("POSTGRES_PASSWORD", "")

        return f"host={host} port={port} dbname={database} user={user} password={password}"

    def connect(self):
        """Establish database connection"""
        if psycopg2 is None:
            raise RuntimeError(
                "psycopg2 is not installed. Install dependencies before using DatabaseService."
            )
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(self.connection_string)
                logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    # =========================================================================
    # OAuth Tokens Operations
    # =========================================================================

    def store_oauth_tokens(
        self,
        user_id: str,
        provider: str,
        encrypted_access_token: bytes,
        encrypted_refresh_token: bytes,
        token_expiry: datetime,
        scopes: List[str],
    ) -> bool:
        """
        Store encrypted OAuth tokens

        Args:
            user_id: User UUID
            provider: OAuth provider (e.g., 'google_drive')
            encrypted_access_token: Encrypted access token
            encrypted_refresh_token: Encrypted refresh token
            token_expiry: Token expiry timestamp
            scopes: List of OAuth scopes

        Returns:
            True if successful
        """
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO oauth_tokens
                    (user_id, provider, encrypted_access_token, encrypted_refresh_token, token_expiry, scopes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, provider)
                    DO UPDATE SET
                        encrypted_access_token = EXCLUDED.encrypted_access_token,
                        encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                        token_expiry = EXCLUDED.token_expiry,
                        scopes = EXCLUDED.scopes,
                        updated_at = NOW()
                    """,
                    (
                        user_id,
                        provider,
                        encrypted_access_token,
                        encrypted_refresh_token,
                        token_expiry,
                        scopes,
                    ),
                )
                self.conn.commit()
                logger.info(f"Stored OAuth tokens for user {user_id}, provider {provider}")
                return True
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def get_oauth_tokens(self, user_id: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve encrypted OAuth tokens

        Args:
            user_id: User UUID
            provider: OAuth provider

        Returns:
            Dictionary with token data or None if not found
        """
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        encrypted_access_token,
                        encrypted_refresh_token,
                        token_expiry,
                        scopes
                    FROM oauth_tokens
                    WHERE user_id = %s AND provider = %s
                    """,
                    (user_id, provider),
                )
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth tokens: {e}")
            return None

    def delete_oauth_tokens(self, user_id: str, provider: str) -> bool:
        """Delete OAuth tokens for a user"""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM oauth_tokens WHERE user_id = %s AND provider = %s",
                    (user_id, provider),
                )
                self.conn.commit()
                logger.info(f"Deleted OAuth tokens for user {user_id}, provider {provider}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete OAuth tokens: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    # =========================================================================
    # Drive Sync State Operations
    # =========================================================================

    def get_sync_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Drive sync state for a user"""
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        sync_token,
                        last_sync_at,
                        files_synced,
                        files_failed,
                        last_error
                    FROM drive_sync_state
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve sync state: {e}")
            return None

    def update_sync_state(
        self,
        user_id: str,
        sync_token: Optional[str] = None,
        files_synced: int = 0,
        files_failed: int = 0,
        last_error: Optional[str] = None,
    ) -> bool:
        """Update Drive sync state"""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO drive_sync_state
                    (user_id, sync_token, last_sync_at, files_synced, files_failed, last_error)
                    VALUES (%s, %s, NOW(), %s, %s, %s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        sync_token = COALESCE(EXCLUDED.sync_token, drive_sync_state.sync_token),
                        last_sync_at = NOW(),
                        files_synced = EXCLUDED.files_synced,
                        files_failed = EXCLUDED.files_failed,
                        last_error = EXCLUDED.last_error,
                        updated_at = NOW()
                    """,
                    (user_id, sync_token, files_synced, files_failed, last_error),
                )
                self.conn.commit()
                logger.info(f"Updated sync state for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to update sync state: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    # =========================================================================
    # Sync Jobs Operations
    # =========================================================================

    def create_sync_job(
        self, user_id: str, source_type: str = "google_drive"
    ) -> Optional[str]:
        """Create a new sync job and return its ID"""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sync_jobs (user_id, source_type, status)
                    VALUES (%s, %s, 'pending')
                    RETURNING id
                    """,
                    (user_id, source_type),
                )
                job_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Created sync job {job_id} for user {user_id}")
                return str(job_id)
        except Exception as e:
            logger.error(f"Failed to create sync job: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def update_sync_job(
        self,
        job_id: str,
        status: str,
        documents_synced: int = 0,
        documents_failed: int = 0,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update sync job status"""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                completed_at = datetime.now() if status in ["success", "failed", "cancelled"] else None

                cur.execute(
                    """
                    UPDATE sync_jobs
                    SET
                        status = %s,
                        documents_synced = %s,
                        documents_failed = %s,
                        error_message = %s,
                        error_details = %s,
                        completed_at = %s
                    WHERE id = %s
                    """,
                    (
                        status,
                        documents_synced,
                        documents_failed,
                        error_message,
                        Json(error_details) if error_details else None,
                        completed_at,
                        job_id,
                    ),
                )
                self.conn.commit()
                logger.info(f"Updated sync job {job_id} to status {status}")
                return True
        except Exception as e:
            logger.error(f"Failed to update sync job: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def get_sync_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get sync job by ID"""
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        source_type,
                        status,
                        started_at,
                        completed_at,
                        documents_synced,
                        documents_failed,
                        error_message,
                        error_details
                    FROM sync_jobs
                    WHERE id = %s
                    """,
                    (job_id,),
                )
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve sync job: {e}")
            return None

    def get_latest_sync_jobs(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest sync jobs for a user"""
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        source_type,
                        status,
                        started_at,
                        completed_at,
                        documents_synced,
                        documents_failed,
                        error_message
                    FROM sync_jobs
                    WHERE user_id = %s
                    ORDER BY started_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                results = cur.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to retrieve sync jobs: {e}")
            return []

    # =========================================================================
    # Documents Operations
    # =========================================================================

    def upsert_document(
        self,
        source_type: str,
        source_id: str,
        title: str,
        content_hash: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        owner_email: Optional[str] = None,
        sharing_status: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        modified_at: Optional[datetime] = None,
        web_view_link: Optional[str] = None,
        embedding_model: str = "text-embedding-3-small",
        chunk_count: int = 0,
    ) -> Optional[str]:
        """Upsert document metadata"""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents
                    (source_type, source_id, title, content_hash, file_size, mime_type,
                     owner_email, sharing_status, permissions, modified_at, web_view_link,
                     embedding_model, chunk_count, last_synced_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (content_hash)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        file_size = EXCLUDED.file_size,
                        mime_type = EXCLUDED.mime_type,
                        owner_email = EXCLUDED.owner_email,
                        sharing_status = EXCLUDED.sharing_status,
                        permissions = EXCLUDED.permissions,
                        modified_at = EXCLUDED.modified_at,
                        web_view_link = EXCLUDED.web_view_link,
                        chunk_count = EXCLUDED.chunk_count,
                        last_synced_at = NOW()
                    RETURNING id
                    """,
                    (
                        source_type,
                        source_id,
                        title,
                        content_hash,
                        file_size,
                        mime_type,
                        owner_email,
                        sharing_status,
                        Json(permissions) if permissions else None,
                        modified_at,
                        web_view_link,
                        embedding_model,
                        chunk_count,
                    ),
                )
                doc_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Upserted document {doc_id}: {title}")
                return str(doc_id)
        except Exception as e:
            logger.error(f"Failed to upsert document: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def get_document_by_source_id(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get document by source ID (e.g., Google Drive file ID)"""
        try:
            self.connect()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        source_type,
                        source_id,
                        title,
                        content_hash,
                        modified_at,
                        last_synced_at
                    FROM documents
                    WHERE source_id = %s
                    """,
                    (source_id,),
                )
                result = cur.fetchone()
                if result:
                    return dict(result)
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve document: {e}")
            return None


# Global database service instance
_db_service = None


def get_db_service() -> DatabaseService:
    """Get or create database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
