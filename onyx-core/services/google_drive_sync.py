"""
Google Drive Sync Service

This module handles synchronization of Google Drive files to the RAG system.
Implements incremental sync, permission-aware indexing, and content extraction.
"""

import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from services.google_oauth import get_oauth_service
from services.content_extractor import create_content_extractor
from rag_service import get_rag_service
from utils.database import get_db_service
from utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class GoogleDriveSync:
    """Service for syncing Google Drive files to RAG system"""

    def __init__(self, user_id: str):
        """
        Initialize Google Drive sync service

        Args:
            user_id: User UUID
        """
        self.user_id = user_id
        self.drive_service = None
        self.content_extractor = None
        self.oauth_service = get_oauth_service()
        self.db_service = get_db_service()
        self.rag_service = None  # Will be initialized async

        # Sync statistics
        self.stats = {
            "files_processed": 0,
            "files_indexed": 0,
            "files_updated": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "errors": [],
        }

    async def initialize(self):
        """Initialize services (async)"""
        try:
            # Initialize Drive API service
            creds = self.oauth_service.get_credentials(self.user_id)
            if not creds:
                raise ValueError(f"No OAuth credentials found for user {self.user_id}")

            self.drive_service = build("drive", "v3", credentials=creds)
            self.content_extractor = create_content_extractor(self.drive_service)

            # Initialize RAG service
            self.rag_service = await get_rag_service()
            await self.rag_service.ensure_collection_exists()

            logger.info(f"Initialized Google Drive sync for user {self.user_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Drive sync service: {e}")
            raise

    async def sync(
        self, full_sync: bool = False, max_files: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform Google Drive synchronization

        Args:
            full_sync: If True, perform full sync; if False, incremental sync
            max_files: Optional limit on number of files to process

        Returns:
            Sync statistics dictionary
        """
        try:
            await self.initialize()

            # Get sync state
            sync_state = self.db_service.get_sync_state(self.user_id)
            sync_token = sync_state.get("sync_token") if sync_state and not full_sync else None

            logger.info(
                f"Starting {'full' if full_sync else 'incremental'} sync for user {self.user_id}"
            )

            # List files from Google Drive
            files, new_sync_token = self._list_files(
                sync_token=sync_token, max_results=max_files
            )

            logger.info(f"Found {len(files)} files to process")

            # Process each file
            for file_metadata in files:
                try:
                    await self._process_file(file_metadata)
                    self.stats["files_processed"] += 1
                except Exception as e:
                    self.stats["files_failed"] += 1
                    error_info = {
                        "file_id": file_metadata.get("id"),
                        "file_name": file_metadata.get("name"),
                        "error": str(e),
                    }
                    self.stats["errors"].append(error_info)
                    logger.error(f"Failed to process file {file_metadata.get('name')}: {e}")
                    # Continue with next file (partial success)

            # Update sync state
            self.db_service.update_sync_state(
                user_id=self.user_id,
                sync_token=new_sync_token,
                files_synced=self.stats["files_indexed"] + self.stats["files_updated"],
                files_failed=self.stats["files_failed"],
                last_error=self.stats["errors"][-1]["error"] if self.stats["errors"] else None,
            )

            logger.info(f"Sync completed: {self.stats}")
            return self.stats

        except Exception as e:
            logger.error(f"Sync failed for user {self.user_id}: {e}")
            # Update sync state with error
            self.db_service.update_sync_state(
                user_id=self.user_id,
                files_synced=0,
                files_failed=0,
                last_error=str(e),
            )
            raise

    def _list_files(
        self, sync_token: Optional[str] = None, max_results: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        List files from Google Drive using Changes API for incremental sync

        Args:
            sync_token: Sync token for incremental changes (from previous sync)
            max_results: Maximum number of files to retrieve

        Returns:
            Tuple of (files list, new sync token)
        """
        files = []
        new_sync_token = None

        try:
            if sync_token:
                # Use Changes API for incremental sync
                files, new_sync_token = self._list_changes(sync_token, max_results)
                logger.info(
                    f"Incremental sync: Listed {len(files)} changed files from Google Drive"
                )
            else:
                # Use Files API for full sync (first time)
                files, new_sync_token = self._list_all_files(max_results)
                logger.info(
                    f"Full sync: Listed {len(files)} files from Google Drive"
                )

            return files, new_sync_token

        except HttpError as e:
            logger.error(f"Failed to list files from Google Drive: {e}")
            raise

    def _list_all_files(
        self, max_results: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        List all files using Files API (for full sync)

        Args:
            max_results: Maximum number of files to retrieve

        Returns:
            Tuple of (files list, new sync token)
        """
        files = []
        page_token = None
        new_sync_token = None

        while True:
            # Build request parameters
            request_params = {
                "pageSize": min(1000, max_results or 1000),
                "fields": (
                    "nextPageToken, newStartPageToken, "
                    "files(id, name, mimeType, modifiedTime, createdTime, "
                    "owners, permissions, size, webViewLink, capabilities)"
                ),
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
                "q": "trashed=false",  # Exclude trashed files
            }

            if page_token:
                request_params["pageToken"] = page_token

            # Execute request with retry logic
            @retry_with_backoff(max_retries=3, backoff_delays=[1, 5, 30])
            def execute_list_request():
                return self.drive_service.files().list(**request_params).execute()

            response = execute_list_request()

            # Collect files
            batch_files = response.get("files", [])
            files.extend(batch_files)

            # Get sync token for next incremental sync
            if "newStartPageToken" in response:
                new_sync_token = response["newStartPageToken"]

            # Check for next page
            page_token = response.get("nextPageToken")

            # Stop if no more pages or reached max_results
            if not page_token:
                break
            if max_results and len(files) >= max_results:
                files = files[:max_results]
                break

        return files, new_sync_token

    def _list_changes(
        self, page_token: str, max_results: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        List file changes using Changes API (for incremental sync)

        Args:
            page_token: Token from previous sync (this is the sync token)
            max_results: Maximum number of changes to retrieve

        Returns:
            Tuple of (changed files list, new sync token)
        """
        files = []
        new_page_token = page_token

        while True:
            # Build request parameters for Changes API
            request_params = {
                "pageToken": new_page_token,
                "pageSize": min(1000, max_results or 1000),
                "fields": (
                    "nextPageToken, newStartPageToken, "
                    "changes(fileId, removed, file(id, name, mimeType, modifiedTime, "
                    "createdTime, owners, permissions, size, webViewLink, capabilities, trashed))"
                ),
                "supportsAllDrives": True,
                "includeItemsFromAllDrives": True,
            }

            # Execute Changes API request with retry logic
            @retry_with_backoff(max_retries=3, backoff_delays=[1, 5, 30])
            def execute_changes_request():
                return self.drive_service.changes().list(**request_params).execute()

            response = execute_changes_request()

            # Process changes
            changes = response.get("changes", [])
            for change in changes:
                # Skip removed files or files moved to trash
                if change.get("removed") or change.get("file", {}).get("trashed"):
                    # TODO: Handle deleted files - remove from index
                    logger.debug(
                        f"File removed or trashed: {change.get('fileId')}"
                    )
                    continue

                # Add file to list if it exists and not trashed
                if "file" in change:
                    files.append(change["file"])

            # Update page token for next iteration or next sync
            new_page_token = response.get("nextPageToken")
            if "newStartPageToken" in response:
                new_page_token = response["newStartPageToken"]

            # Stop if no more pages or reached max_results
            if not response.get("nextPageToken"):
                break
            if max_results and len(files) >= max_results:
                files = files[:max_results]
                break

        return files, new_page_token

    async def _process_file(self, file_metadata: Dict[str, Any]):
        """
        Process a single file: extract content, index, and store metadata

        Args:
            file_metadata: File metadata from Google Drive API
        """
        file_id = file_metadata["id"]
        file_name = file_metadata["name"]
        mime_type = file_metadata["mimeType"]

        logger.debug(f"Processing file: {file_name} ({mime_type})")

        # Skip Google Apps folders and shortcuts
        if mime_type in [
            "application/vnd.google-apps.folder",
            "application/vnd.google-apps.shortcut",
        ]:
            logger.debug(f"Skipping folder/shortcut: {file_name}")
            self.stats["files_skipped"] += 1
            return

        # Check if user has access (basic check - file is in their drive)
        if not self._user_has_access(file_metadata):
            logger.warning(f"User lacks access to file: {file_name}")
            self.stats["files_skipped"] += 1
            return

        # Check if file already indexed and up-to-date
        existing_doc = self.db_service.get_document_by_source_id(file_id)
        if existing_doc:
            # Compare modified times
            file_modified = datetime.fromisoformat(
                file_metadata["modifiedTime"].replace("Z", "+00:00")
            )
            db_modified = existing_doc.get("modified_at")

            if db_modified and file_modified <= db_modified:
                logger.debug(f"File already up-to-date: {file_name}")
                self.stats["files_skipped"] += 1
                return

        # Extract content with retry logic for transient failures
        @retry_with_backoff(max_retries=3, backoff_delays=[1, 5, 30])
        def extract_with_retry():
            return self.content_extractor.extract_content(file_id, mime_type, file_name)

        try:
            content = extract_with_retry()
        except Exception as e:
            logger.error(f"Failed to extract content from {file_name} after retries: {e}")
            self.stats["files_failed"] += 1
            raise

        if not content or len(content.strip()) == 0:
            logger.warning(f"No content extracted from {file_name}, skipping")
            self.stats["files_skipped"] += 1
            return

        # Extract permissions
        permissions = self._extract_permissions(file_metadata)

        # Generate content hash for deduplication
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Store metadata in PostgreSQL
        file_size = int(file_metadata.get("size", 0)) if "size" in file_metadata else None
        modified_at = datetime.fromisoformat(
            file_metadata["modifiedTime"].replace("Z", "+00:00")
        )

        owner_email = None
        if file_metadata.get("owners"):
            owner_email = file_metadata["owners"][0].get("emailAddress")

        sharing_status = self._determine_sharing_status(file_metadata)

        # Chunk content (500 chars per chunk with 50 char overlap)
        chunks = self._chunk_content(content, chunk_size=500, overlap=50)

        doc_id = self.db_service.upsert_document(
            source_type="google_drive",
            source_id=file_id,
            title=file_name,
            content_hash=content_hash,
            file_size=file_size,
            mime_type=mime_type,
            owner_email=owner_email,
            sharing_status=sharing_status,
            permissions=permissions,
            modified_at=modified_at,
            web_view_link=file_metadata.get("webViewLink"),
            chunk_count=len(chunks),
        )

        if not doc_id:
            logger.error(f"Failed to store document metadata for {file_name}")
            raise Exception("Failed to store document metadata")

        # Index chunks in Qdrant
        for idx, chunk_text in enumerate(chunks):
            try:
                # Create unique chunk ID
                chunk_id = f"{file_id}-chunk-{idx}"

                # Prepare metadata for Qdrant payload
                metadata = {
                    "doc_id": doc_id,
                    "source_id": file_id,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                    "owner_email": owner_email,
                    "permissions": permissions,
                    "mime_type": mime_type,
                    "web_view_link": file_metadata.get("webViewLink"),
                    "modified_at": modified_at.isoformat(),
                }

                # Index in Qdrant
                await self.rag_service.add_document(
                    doc_id=chunk_id,
                    text=chunk_text,
                    title=file_name,
                    source="google_drive",
                    metadata=metadata,
                )

            except Exception as e:
                logger.error(f"Failed to index chunk {idx} of {file_name}: {e}")
                raise

        # Update statistics
        if existing_doc:
            self.stats["files_updated"] += 1
            logger.info(f"Updated file: {file_name} ({len(chunks)} chunks)")
        else:
            self.stats["files_indexed"] += 1
            logger.info(f"Indexed new file: {file_name} ({len(chunks)} chunks)")

    def _user_has_access(self, file_metadata: Dict[str, Any]) -> bool:
        """
        Check if user has read access to file

        Args:
            file_metadata: File metadata from Drive API

        Returns:
            True if user has access
        """
        # Simplified check: if file appears in user's Drive listing, they have access
        # Google Drive API only returns files the user can access
        capabilities = file_metadata.get("capabilities", {})
        return capabilities.get("canDownload", False) or capabilities.get("canCopy", False)

    def _extract_permissions(self, file_metadata: Dict[str, Any]) -> List[str]:
        """
        Extract list of user emails with access to the file

        Args:
            file_metadata: File metadata from Drive API

        Returns:
            List of user email addresses (or ['*'] for public files)
        """
        permissions = file_metadata.get("permissions", [])
        user_emails = []

        for perm in permissions:
            perm_type = perm.get("type")
            if perm_type == "user" and perm.get("emailAddress"):
                user_emails.append(perm["emailAddress"])
            elif perm_type == "anyone":
                # Public file - accessible to all
                return ["*"]
            elif perm_type == "domain":
                # Domain-wide sharing - mark as domain accessible
                user_emails.append(f"@{perm.get('domain', 'domain')}")

        return user_emails if user_emails else []

    def _determine_sharing_status(self, file_metadata: Dict[str, Any]) -> str:
        """
        Determine sharing status of file

        Args:
            file_metadata: File metadata from Drive API

        Returns:
            'public', 'shared', or 'private'
        """
        permissions = file_metadata.get("permissions", [])

        for perm in permissions:
            if perm.get("type") == "anyone":
                return "public"

        if len(permissions) > 1:  # More than just owner
            return "shared"

        return "private"

    def _chunk_content(
        self, content: str, chunk_size: int = 500, overlap: int = 50
    ) -> List[str]:
        """
        Split content into overlapping chunks

        Args:
            content: Full text content
            chunk_size: Target size of each chunk (in characters)
            overlap: Overlap between consecutive chunks

        Returns:
            List of text chunks
        """
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]

            # Try to break at sentence boundary
            if end < len(content):
                # Look for period, question mark, or exclamation within last 100 chars
                last_period = max(
                    chunk.rfind(". "),
                    chunk.rfind("? "),
                    chunk.rfind("! "),
                )
                if last_period > chunk_size - 100:
                    end = start + last_period + 2
                    chunk = content[start:end]

            chunks.append(chunk.strip())

            # Move start position with overlap
            start = end - overlap

        logger.debug(f"Split content into {len(chunks)} chunks")
        return chunks


# Convenience function
async def sync_google_drive(
    user_id: str, full_sync: bool = False, max_files: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function to sync Google Drive for a user

    Args:
        user_id: User UUID
        full_sync: If True, perform full sync
        max_files: Optional limit on files to process

    Returns:
        Sync statistics
    """
    sync_service = GoogleDriveSync(user_id)
    return await sync_service.sync(full_sync=full_sync, max_files=max_files)
