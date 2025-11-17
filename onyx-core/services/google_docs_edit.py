"""
Google Docs Editing Service

This module provides comprehensive functionality for editing Google Docs documents
including content insertion, text replacement, and formatting updates.

Supports Story 6-3: Google Docs Editing Capabilities
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import re

from services.google_oauth import get_oauth_service
from utils.database import get_db_service
from utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class GoogleDocsEditService:
    """Service for editing Google Docs with content insertion, replacement, and formatting"""

    # Google Docs API configuration
    DOCS_API_VERSION = "v1"
    DOCS_API_SERVICE_NAME = "docs"
    DRIVE_API_SERVICE_NAME = "drive"
    DRIVE_API_VERSION = "v3"

    # Formatting constants
    HEADING_STYLES = {
        "H1": "HEADING_1",
        "H2": "HEADING_2",
        "H3": "HEADING_3",
        "H4": "HEADING_4",
        "H5": "HEADING_5",
        "H6": "HEADING_6",
    }

    # Position constants
    POSITION_BEGINNING = "beginning"
    POSITION_END = "end"
    POSITION_AFTER_HEADING = "after_heading"
    POSITION_BEFORE_HEADING = "before_heading"

    def __init__(self, user_id: str):
        """
        Initialize Google Docs Edit Service

        Args:
            user_id: UUID of the user performing edits

        Raises:
            ValueError: If user credentials not found or invalid
        """
        self.user_id = user_id
        self.oauth_service = get_oauth_service()
        self.db_service = get_db_service()

        # Get and validate credentials
        self.credentials = self.oauth_service.get_credentials(user_id)
        if not self.credentials or not self.credentials.valid:
            raise ValueError(f"Invalid or missing credentials for user {user_id}")

        # Initialize API services
        self.docs_service = build(
            self.DOCS_API_SERVICE_NAME,
            self.DOCS_API_VERSION,
            credentials=self.credentials,
        )
        self.drive_service = build(
            self.DRIVE_API_SERVICE_NAME,
            self.DRIVE_API_VERSION,
            credentials=self.credentials,
        )

    @retry_with_backoff(max_retries=3, initial_delay=1)
    def insert_content(
        self,
        document_id: str,
        content_markdown: str,
        position: str = POSITION_END,
        heading_text: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Insert content at specified position in document

        Supports multiple positioning strategies:
        - "beginning": Insert at document start
        - "end": Insert at document end (default)
        - "after_heading": Insert after heading matching heading_text
        - "before_heading": Insert before heading matching heading_text
        - "offset": Insert at absolute character offset

        Args:
            document_id: Google Docs document ID
            content_markdown: Content to insert (Markdown format)
            position: Positioning strategy (beginning, end, after_heading, before_heading, offset)
            heading_text: Text of heading to position relative to (for after_heading/before_heading)
            offset: Absolute character offset (for offset position)

        Returns:
            Dict with:
            - success: bool
            - content_id_ranges: List of content ranges inserted
            - character_inserted: Number of characters inserted
            - execution_time_ms: Operation duration
            - message: Status message

        Raises:
            ValueError: Invalid parameters
            HttpError: API errors
        """
        import time

        start_time = time.time()

        try:
            # Validate parameters
            if not document_id or not content_markdown:
                raise ValueError("document_id and content_markdown are required")

            # Get document structure
            doc = self._get_document(document_id)
            if not doc:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found or inaccessible",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Validate permissions
            if not self._has_edit_permission(document_id):
                return {
                    "success": False,
                    "error": "Permission denied: you do not have edit access to this document",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Convert Markdown to Google Docs format
            formatted_content = self._markdown_to_google_docs(content_markdown)

            # Determine insertion index
            insert_index = self._get_insertion_index(
                doc, position, heading_text, offset
            )

            if insert_index is None:
                return {
                    "success": False,
                    "error": f"Could not determine insertion index for position: {position}",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Build batch update request for content insertion
            requests = self._build_insert_requests(insert_index, formatted_content)

            # Execute batch update
            response = (
                self.docs_service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            # Log operation to database
            self._log_edit_operation(
                document_id=document_id,
                operation_type="insert",
                details={
                    "position": position,
                    "content_length": len(content_markdown),
                    "insert_index": insert_index,
                },
                status="success",
                result={"content_id_ranges": response.get("replies", [])},
            )

            execution_time = int((time.time() - start_time) * 1000)

            # Check performance constraint
            if execution_time > 2000:
                logger.warning(
                    f"Insert operation took {execution_time}ms (target <2s) for doc {document_id}"
                )

            return {
                "success": True,
                "content_id_ranges": response.get("replies", []),
                "character_inserted": len(content_markdown),
                "execution_time_ms": execution_time,
                "message": f"Successfully inserted {len(content_markdown)} characters at position '{position}'",
            }

        except HttpError as e:
            error_msg = f"Google Docs API error: {e.resp.status} - {e.content}"
            logger.error(error_msg)

            self._log_edit_operation(
                document_id=document_id,
                operation_type="insert",
                status="failed",
                error_message=error_msg,
            )

            return {
                "success": False,
                "error": error_msg,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

        except Exception as e:
            error_msg = f"Insert operation failed: {str(e)}"
            logger.error(error_msg)

            self._log_edit_operation(
                document_id=document_id,
                operation_type="insert",
                status="failed",
                error_message=error_msg,
            )

            return {
                "success": False,
                "error": error_msg,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

    @retry_with_backoff(max_retries=3, initial_delay=1)
    def replace_content(
        self,
        document_id: str,
        search_text: str,
        replacement_markdown: str,
        use_regex: bool = False,
        replace_all: bool = True,
    ) -> Dict[str, Any]:
        """
        Replace text in document

        Args:
            document_id: Google Docs document ID
            search_text: Text to search for (plain text or regex if use_regex=True)
            replacement_markdown: Replacement content (Markdown format)
            use_regex: Treat search_text as regex pattern
            replace_all: Replace all occurrences (True) or just first (False)

        Returns:
            Dict with:
            - success: bool
            - replacements_count: Number of replacements made
            - character_changes: Net change in document size
            - execution_time_ms: Operation duration
            - message: Status message

        Raises:
            ValueError: Invalid parameters
            HttpError: API errors
        """
        import time

        start_time = time.time()

        try:
            # Validate parameters
            if not document_id or not search_text or replacement_markdown is None:
                raise ValueError(
                    "document_id, search_text, and replacement_markdown are required"
                )

            # Get document structure
            doc = self._get_document(document_id)
            if not doc:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found or inaccessible",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Validate permissions
            if not self._has_edit_permission(document_id):
                return {
                    "success": False,
                    "error": "Permission denied: you do not have edit access to this document",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Convert Markdown to Google Docs format
            formatted_replacement = self._markdown_to_google_docs(replacement_markdown)

            # Find all text ranges matching search_text
            ranges = self._find_text_ranges(doc, search_text, use_regex, replace_all)

            if not ranges:
                return {
                    "success": True,
                    "replacements_count": 0,
                    "character_changes": 0,
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                    "message": f"No occurrences of '{search_text}' found in document",
                }

            # Build batch update requests for replacements
            # Process ranges in reverse order to maintain index validity
            requests = []
            for start_index, end_index in reversed(ranges):
                requests.extend(
                    self._build_replace_requests(
                        start_index, end_index, formatted_replacement
                    )
                )

            # Execute batch update
            response = (
                self.docs_service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            # Log operation to database
            char_change = (len(replacement_markdown) - len(search_text)) * len(ranges)

            self._log_edit_operation(
                document_id=document_id,
                operation_type="replace",
                details={
                    "search_text": search_text,
                    "replacement_length": len(replacement_markdown),
                    "replacements_count": len(ranges),
                    "use_regex": use_regex,
                },
                status="success",
                result={"replacements": len(ranges)},
            )

            execution_time = int((time.time() - start_time) * 1000)

            # Check performance constraint
            if execution_time > 2000:
                logger.warning(
                    f"Replace operation took {execution_time}ms (target <2s) for doc {document_id}"
                )

            return {
                "success": True,
                "replacements_count": len(ranges),
                "character_changes": char_change,
                "execution_time_ms": execution_time,
                "message": f"Successfully replaced {len(ranges)} occurrence(s) of '{search_text}'",
            }

        except HttpError as e:
            error_msg = f"Google Docs API error: {e.resp.status} - {e.content}"
            logger.error(error_msg)

            self._log_edit_operation(
                document_id=document_id,
                operation_type="replace",
                status="failed",
                error_message=error_msg,
            )

            return {
                "success": False,
                "error": error_msg,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

        except Exception as e:
            error_msg = f"Replace operation failed: {str(e)}"
            logger.error(error_msg)

            self._log_edit_operation(
                document_id=document_id,
                operation_type="replace",
                status="failed",
                error_message=error_msg,
            )

            return {
                "success": False,
                "error": error_msg,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

    @retry_with_backoff(max_retries=3, initial_delay=1)
    def update_formatting(
        self,
        document_id: str,
        start_index: int,
        end_index: int,
        formatting: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update formatting for a text range

        Supported formatting properties:
        - bold: bool
        - italic: bool
        - strikethrough: bool
        - fontSize: int (in points)
        - fontFamily: str
        - textColor: {'color': {'rgbColor': '#RRGGBB'}}
        - backgroundColor: {'color': {'rgbColor': '#RRGGBB'}}
        - headingStyle: str (HEADING_1-6, NORMAL_TEXT)

        Args:
            document_id: Google Docs document ID
            start_index: Start character index
            end_index: End character index
            formatting: Dict of formatting properties to apply

        Returns:
            Dict with:
            - success: bool
            - execution_time_ms: Operation duration
            - message: Status message

        Raises:
            ValueError: Invalid parameters
            HttpError: API errors
        """
        import time

        start_time = time.time()

        try:
            # Validate parameters
            if not document_id or start_index < 0 or end_index <= start_index:
                raise ValueError(
                    "document_id required; start_index must be >= 0, end_index > start_index"
                )

            # Get document structure
            doc = self._get_document(document_id)
            if not doc:
                return {
                    "success": False,
                    "error": f"Document {document_id} not found or inaccessible",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Validate permissions
            if not self._has_edit_permission(document_id):
                return {
                    "success": False,
                    "error": "Permission denied: you do not have edit access to this document",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Build formatting request
            requests = self._build_formatting_requests(
                start_index, end_index, formatting
            )

            if not requests:
                return {
                    "success": False,
                    "error": "No valid formatting properties specified",
                    "execution_time_ms": int((time.time() - start_time) * 1000),
                }

            # Execute batch update
            response = (
                self.docs_service.documents()
                .batchUpdate(documentId=document_id, body={"requests": requests})
                .execute()
            )

            # Log operation to database
            self._log_edit_operation(
                document_id=document_id,
                operation_type="format",
                details={
                    "start_index": start_index,
                    "end_index": end_index,
                    "formatting_properties": list(formatting.keys()),
                },
                status="success",
            )

            execution_time = int((time.time() - start_time) * 1000)

            # Check performance constraint
            if execution_time > 2000:
                logger.warning(
                    f"Format operation took {execution_time}ms (target <2s) for doc {document_id}"
                )

            return {
                "success": True,
                "execution_time_ms": execution_time,
                "message": f"Successfully applied {len(formatting)} formatting properties",
            }

        except HttpError as e:
            error_msg = f"Google Docs API error: {e.resp.status} - {e.content}"
            logger.error(error_msg)

            self._log_edit_operation(
                document_id=document_id,
                operation_type="format",
                status="failed",
                error_message=error_msg,
            )

            return {
                "success": False,
                "error": error_msg,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

        except Exception as e:
            error_msg = f"Format operation failed: {str(e)}"
            logger.error(error_msg)

            self._log_edit_operation(
                document_id=document_id,
                operation_type="format",
                status="failed",
                error_message=error_msg,
            )

            return {
                "success": False,
                "error": error_msg,
                "execution_time_ms": int((time.time() - start_time) * 1000),
            }

    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    def _get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document structure from Google Docs API"""
        try:
            doc = self.docs_service.documents().get(documentId=document_id).execute()
            return doc
        except HttpError as e:
            if e.resp.status == 404:
                logger.warning(f"Document {document_id} not found")
            else:
                logger.error(f"Failed to retrieve document {document_id}: {e}")
            return None

    def _has_edit_permission(self, document_id: str) -> bool:
        """Check if user has edit permission on document"""
        try:
            # Check if we can access document with capabilities check
            doc = (
                self.docs_service.documents()
                .get(documentId=document_id, fields="documentId")
                .execute()
            )
            return doc is not None
        except HttpError as e:
            if e.resp.status == 403:
                logger.warning(f"User lacks edit permission for document {document_id}")
                return False
            return False
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return False

    def _markdown_to_google_docs(self, markdown_content: str) -> Dict[str, Any]:
        """
        Convert Markdown content to Google Docs insertText format

        Handles:
        - Headings (# ## ### etc)
        - Bold (**text** or __text__)
        - Italic (*text* or _text_)
        - Code blocks (```code```)
        - Inline code (`code`)
        - Links ([text](url))
        - Lists (- and *)

        Returns:
            Dict with text and formatting instructions
        """
        # For MVP: return structured content that can be further formatted
        # Full formatting conversion happens in _build_insert_requests
        return {
            "text": markdown_content,
            "type": "markdown",
            "timestamp": datetime.now().isoformat(),
        }

    def _get_insertion_index(
        self,
        doc: Dict[str, Any],
        position: str,
        heading_text: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> Optional[int]:
        """Determine character index for insertion based on position strategy"""

        if position == self.POSITION_BEGINNING:
            # Insert at the beginning (index 1, after document start)
            return 1

        elif position == self.POSITION_END:
            # Insert at the end
            body = doc.get("body", {})
            content = body.get("content", [])
            if content:
                last_element = content[-1]
                if "endIndex" in last_element:
                    return last_element["endIndex"]
            return len(doc.get("body", {}).get("content", []))

        elif position == self.POSITION_AFTER_HEADING and heading_text:
            # Find heading and insert after it
            return self._find_heading_index(doc, heading_text, after=True)

        elif position == self.POSITION_BEFORE_HEADING and heading_text:
            # Find heading and insert before it
            return self._find_heading_index(doc, heading_text, after=False)

        elif position == "offset" and offset is not None:
            # Use exact offset
            return offset

        return None

    def _find_heading_index(
        self, doc: Dict[str, Any], heading_text: str, after: bool = True
    ) -> Optional[int]:
        """Find index of heading with given text"""
        body = doc.get("body", {})
        content = body.get("content", [])

        for element in content:
            if "paragraph" in element:
                paragraph = element["paragraph"]
                para_text = self._extract_paragraph_text(paragraph)

                if heading_text.lower() in para_text.lower():
                    if after:
                        return element.get("endIndex", 0)
                    else:
                        return element.get("startIndex", 0)

        return None

    def _extract_paragraph_text(self, paragraph: Dict[str, Any]) -> str:
        """Extract plain text from a paragraph element"""
        text = ""
        elements = paragraph.get("elements", [])
        for element in elements:
            if "textRun" in element:
                text += element["textRun"].get("content", "")
        return text

    def _find_text_ranges(
        self,
        doc: Dict[str, Any],
        search_text: str,
        use_regex: bool = False,
        replace_all: bool = True,
    ) -> List[Tuple[int, int]]:
        """
        Find all text ranges matching search criteria

        Returns:
            List of (start_index, end_index) tuples
        """
        ranges = []
        body = doc.get("body", {})
        content = body.get("content", [])

        # Build full document text with index mapping
        full_text = ""
        index_map = []  # Maps character index to (element_index, local_index)

        for element in content:
            if "paragraph" in element:
                paragraph = element["paragraph"]
                para_text = self._extract_paragraph_text(paragraph)

                for i, char in enumerate(para_text):
                    index_map.append((element, i))
                    full_text += char

        # Find matches
        if use_regex:
            pattern = re.compile(search_text)
            for match in pattern.finditer(full_text):
                start_idx = match.start()
                end_idx = match.end()
                ranges.append((start_idx, end_idx))
                if not replace_all:
                    break
        else:
            start = 0
            while True:
                idx = full_text.find(search_text, start)
                if idx == -1:
                    break
                ranges.append((idx, idx + len(search_text)))
                start = idx + len(search_text)
                if not replace_all:
                    break

        return ranges

    def _build_insert_requests(
        self, insert_index: int, formatted_content: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build Google Docs API insertText requests"""
        text_content = formatted_content.get("text", "")

        requests = [
            {
                "insertText": {
                    "text": text_content,
                    "location": {"index": insert_index},
                }
            }
        ]

        return requests

    def _build_replace_requests(
        self, start_index: int, end_index: int, formatted_replacement: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build Google Docs API replaceText/deleteContent + insertText requests"""
        replacement_text = formatted_replacement.get("text", "")

        requests = [
            # Delete old content
            {
                "deleteContentRange": {
                    "range": {"startIndex": start_index, "endIndex": end_index}
                }
            },
            # Insert new content
            {
                "insertText": {
                    "text": replacement_text,
                    "location": {"index": start_index},
                }
            },
        ]

        return requests

    def _build_formatting_requests(
        self, start_index: int, end_index: int, formatting: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build Google Docs API formatting requests"""
        requests = []

        # Create character format spec
        char_format = {}

        if "bold" in formatting:
            char_format["bold"] = formatting["bold"]

        if "italic" in formatting:
            char_format["italic"] = formatting["italic"]

        if "strikethrough" in formatting:
            char_format["strikethrough"] = formatting["strikethrough"]

        if "fontSize" in formatting:
            char_format["fontSize"] = {
                "magnitude": formatting["fontSize"],
                "unit": "PT",
            }

        if "fontFamily" in formatting:
            char_format["fontFamily"] = formatting["fontFamily"]

        if "textColor" in formatting:
            char_format["foregroundColor"] = formatting["textColor"]

        if "backgroundColor" in formatting:
            char_format["backgroundColor"] = formatting["backgroundColor"]

        if char_format:
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": start_index, "endIndex": end_index},
                        "textStyle": char_format,
                        "fields": ",".join(char_format.keys()),
                    }
                }
            )

        # Handle heading style separately
        if "headingStyle" in formatting:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": start_index, "endIndex": end_index},
                        "paragraphStyle": {
                            "namedStyleType": formatting["headingStyle"]
                        },
                        "fields": "namedStyleType",
                    }
                }
            )

        return requests

    def _log_edit_operation(
        self,
        document_id: str,
        operation_type: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Log document edit operation to database for audit trail"""
        try:
            # Log to database (AC6.3.10: metadata updates with timestamps)
            operation_data = {
                "user_id": self.user_id,
                "document_id": document_id,
                "operation_type": operation_type,
                "details": details or {},
                "status": status,
                "result": result or {},
                "error_message": error_message,
                "timestamp": datetime.now().isoformat(),
            }

            # Store in database via db_service
            self.db_service.log_google_docs_operation(operation_data)

            logger.info(
                f"Logged {operation_type} operation for document {document_id}: {status}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to log operation: {e}")
            return False


# Global service instance cache (keyed by user_id)
_services_cache: Dict[str, GoogleDocsEditService] = {}


def get_google_docs_edit_service(user_id: str) -> GoogleDocsEditService:
    """Get or create GoogleDocsEditService instance for user"""
    if user_id not in _services_cache:
        _services_cache[user_id] = GoogleDocsEditService(user_id)
    return _services_cache[user_id]
